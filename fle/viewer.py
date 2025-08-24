#!/usr/bin/env python3
"""
Visual runner for Factorio Learning Environment with NiceGUI interface.
This module provides a web-based viewer for watching agents play Factorio in real-time.
"""

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import threading
from queue import Queue

import gym
from nicegui import ui, app, run
from PIL import Image
import io
import base64

from fle.env.gym_env.config import GymEvalConfig, GymRunConfig
from fle.env.gym_env.observation_formatter import BasicObservationFormatter
from fle.env.gym_env.system_prompt_formatter import SystemPromptFormatter
from fle.env.gym_env.registry import get_environment_info, list_available_environments
from fle.env.gym_env.trajectory_runner import GymTrajectoryRunner
from fle.env.gym_env.observation import Observation
from fle.env.gym_env.action import Action

from fle.agents.gym_agent import GymAgent
from fle.commons.cluster_ips import get_local_container_ips
from fle.commons.db_client import create_db_client
from fle.commons.models.program import Program
from fle.commons.models.game_state import GameState
from fle.eval.algorithms.independent import get_next_version


class VisualTrajectoryRunner(GymTrajectoryRunner):
    """Extended trajectory runner with visual updates."""

    def __init__(self, *args, update_queue: Optional[Queue] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_queue = update_queue
        self.render_tool = None

    def _initialize_render_tool(self):
        """Initialize the render tool if not already done."""
        if self.render_tool is None and self.instance:
            try:
                from fle.env.tools.admin.render.client import Render
                self.render_tool = self.instance.namespaces[0]._render
            except Exception as e:
                print(f"Failed to initialize render tool: {e}")

    def _get_rendered_image(self, agent_idx: int = 0) -> Optional[str]:
        """Get rendered image of current game state as base64."""
        try:
            self._initialize_render_tool()
            if self.render_tool:
                # Render the current game state
                rendered = self.render_tool(
                    include_status=True,
                    radius=32,
                    compression_level='binary',
                    max_render_radius=32
                )
                # Convert to base64
                return rendered.to_base64()
        except Exception as e:
            print(f"Error rendering game state: {e}")
            return None

    async def run(self):
        """Run trajectory with visual updates."""
        # Initialize state
        max_steps = self.config.task.trajectory_length
        current_state, agent_steps = await self._initialize_trajectory_state()

        # Save system prompts
        for agent_idx, agent in enumerate(self.agents):
            self.logger.save_system_prompt(agent, agent_idx)

        # Send initial update
        if self.update_queue:
            self.update_queue.put({
                'type': 'init',
                'task': self.config.task.goal_description,
                'max_steps': max_steps,
                'num_agents': len(self.agents),
                'image': self._get_rendered_image()
            })

        # Run trajectory
        from itertools import product
        for _, agent_idx in product(range(max_steps), range(len(self.agents))):
            agent = self.agents[agent_idx]
            iteration_start = time.time()
            agent_completed = False

            try:
                while not agent_completed and agent_steps[agent_idx] < max_steps:
                    # Generate policy
                    policy = await agent.generate_policy()
                    agent_steps[agent_idx] += 1

                    if not policy:
                        print(f"Policy generation failed for agent {agent_idx}")
                        break

                    # Send code update
                    if self.update_queue:
                        self.update_queue.put({
                            'type': 'code',
                            'agent_idx': agent_idx,
                            'step': agent_steps[agent_idx],
                            'code': policy.code
                        })

                    # Execute step
                    action = Action(
                        agent_idx=agent_idx,
                        code=policy.code,
                        game_state=current_state
                    )
                    obs_dict, reward, terminated, truncated, info = self.gym_env.step(action)
                    observation = Observation.from_dict(obs_dict)
                    output_game_state = info['output_game_state']
                    done = terminated or truncated

                    # Create program
                    program = await self.create_program_from_policy(
                        policy=policy,
                        agent_idx=agent_idx,
                        reward=reward,
                        response=obs_dict["raw_text"],
                        error_occurred=info["error_occurred"],
                        game_state=output_game_state
                    )

                    # Update agent conversation
                    await agent.update_conversation(observation, previous_program=program)

                    # Log trajectory state
                    self._log_trajectory_state(
                        iteration_start,
                        agent,
                        agent_idx,
                        agent_steps[agent_idx],
                        program,
                        observation
                    )

                    # Send visual update
                    if self.update_queue:
                        self.update_queue.put({
                            'type': 'update',
                            'agent_idx': agent_idx,
                            'step': agent_steps[agent_idx],
                            'reward': reward,
                            'score': program.value,
                            'output': obs_dict["raw_text"][:500],  # First 500 chars
                            'error': info["error_occurred"],
                            'image': self._get_rendered_image(agent_idx),
                            'observation': self._format_observation_summary(observation)
                        })

                    # Check completion
                    agent_completed, update_state = agent.check_step_completion(observation)
                    if update_state:
                        current_state = output_game_state

                    # Check if done
                    if done and self.config.exit_on_task_success:
                        if self.update_queue:
                            self.update_queue.put({
                                'type': 'complete',
                                'success': True,
                                'final_step': agent_steps[agent_idx]
                            })
                        return

            except Exception as e:
                print(f"Error in trajectory runner: {e}")
                if self.update_queue:
                    self.update_queue.put({
                        'type': 'error',
                        'message': str(e)
                    })
                continue

        # Send completion update
        if self.update_queue:
            self.update_queue.put({
                'type': 'complete',
                'success': False,
                'final_step': max(agent_steps)
            })

    def _format_observation_summary(self, observation: Observation) -> Dict[str, Any]:
        """Format observation into a summary for display."""
        return {
            'inventory_count': len(observation.inventory),
            'entities_count': len(observation.entities),
            'score': observation.score,
            'game_tick': observation.game_info.tick,
            'research_progress': observation.research.research_progress if observation.research.current_research else 0
        }


class FactorioViewer:
    """NiceGUI-based viewer for Factorio agent gameplay."""

    def __init__(self):
        self.update_queue = Queue()
        self.runner_thread = None
        self.current_image = None
        self.logs = []
        self.current_step = 0
        self.max_steps = 100
        self.is_running = False

    def create_ui(self):
        """Create the NiceGUI interface."""
        with ui.header().classes('bg-blue-900 text-white'):
            ui.label('🏭 Factorio Learning Environment Viewer').classes('text-2xl font-bold')
            ui.space()
            self.status_label = ui.label('Status: Ready').classes('text-sm')

        with ui.splitter(value=30).classes('w-full h-screen') as splitter:
            # Left panel - Controls and info
            with splitter.before:
                with ui.card().classes('w-full'):
                    ui.label('Controls').classes('text-lg font-bold')

                    with ui.row():
                        self.start_button = ui.button('▶ Start', on_click=self.start_run)
                        self.stop_button = ui.button('⏹ Stop', on_click=self.stop_run).props('disabled')

                    # Task selector
                    tasks = self._get_available_tasks()
                    self.task_select = ui.select(
                        label='Task',
                        options=tasks,
                        value='open_play'
                    ).classes('w-full')

                    # Model selector
                    self.model_select = ui.select(
                        label='Model',
                        options=['gpt-4o-mini', 'claude-3-5-sonnet-latest', 'gpt-4o'],
                        value='gpt-4o-mini'
                    ).classes('w-full')

                    ui.separator()

                    # Progress
                    ui.label('Progress').classes('text-lg font-bold mt-4')
                    self.progress_bar = ui.linear_progress(value=0).classes('w-full')
                    self.step_label = ui.label(f'Step: 0 / {self.max_steps}')

                    # Stats
                    ui.label('Statistics').classes('text-lg font-bold mt-4')
                    with ui.column().classes('w-full'):
                        self.score_label = ui.label('Score: 0')
                        self.inventory_label = ui.label('Inventory Items: 0')
                        self.entities_label = ui.label('Entities: 0')
                        self.research_label = ui.label('Research Progress: 0%')

            # Right panel - Game view and logs
            with splitter.after:
                with ui.tabs().classes('w-full') as tabs:
                    game_tab = ui.tab('Game View')
                    code_tab = ui.tab('Current Code')
                    log_tab = ui.tab('Output Log')

                with ui.tab_panels(tabs, value=game_tab).classes('w-full h-full'):
                    # Game view tab
                    with ui.tab_panel(game_tab):
                        with ui.card().classes('w-full h-full'):
                            self.game_image = ui.image().classes('w-full')
                            self.game_image.set_source(
                                'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')

                    # Code tab
                    with ui.tab_panel(code_tab):
                        with ui.card().classes('w-full h-full'):
                            self.code_display = ui.code('# No code yet', language='python').classes('w-full h-full')

                    # Log tab
                    with ui.tab_panel(log_tab):
                        with ui.card().classes('w-full h-full'):
                            self.log_container = ui.scroll_area().classes('w-full h-full')
                            with self.log_container:
                                self.log_display = ui.column()

        # Set up periodic updates
        ui.timer(0.5, self.process_updates)

    def _get_available_tasks(self) -> List[str]:
        """Get list of available tasks from registry."""
        try:
            return list_available_environments()[:10]  # First 10 tasks
        except:
            return ['Factorio-iron_ore_throughput_16-v0']

    def start_run(self):
        """Start a new run."""
        if not self.is_running:
            self.is_running = True
            self.start_button.props('disabled')
            self.stop_button.props('disabled=false')
            self.status_label.set_text('Status: Starting...')
            self.logs = []
            self.current_step = 0

            # Start runner in background thread
            self.runner_thread = threading.Thread(target=self._run_trajectory)
            self.runner_thread.daemon = True
            self.runner_thread.start()

    def stop_run(self):
        """Stop the current run."""
        self.is_running = False
        self.start_button.props('disabled=false')
        self.stop_button.props('disabled')
        self.status_label.set_text('Status: Stopped')

    def _run_trajectory(self):
        """Run the trajectory in a background thread."""
        try:
            asyncio.run(self._async_run_trajectory())
        except Exception as e:
            self.update_queue.put({
                'type': 'error',
                'message': str(e)
            })

    async def _async_run_trajectory(self):
        """Async trajectory runner."""
        # Get configuration
        env_id = self.task_select.value
        model = self.model_select.value

        # Create run config
        run_config = GymRunConfig(
            env_id=env_id,
            model=model,
            num_agents=1
        )

        # Get environment info
        env_info = get_environment_info(env_id)
        if not env_info:
            self.update_queue.put({
                'type': 'error',
                'message': f'Could not get environment info for {env_id}'
            })
            return

        # Create database client
        db_client = await create_db_client()

        # Create gym environment
        gym_env = gym.make(env_id)
        task = gym_env.unwrapped.task
        instance = gym_env.unwrapped.instance

        # Create agent
        system_prompt = instance.get_system_prompt(0)
        agent = GymAgent(
            model=model,
            system_prompt=system_prompt,
            task=task,
            agent_idx=0,
            observation_formatter=BasicObservationFormatter(include_research=False),
            system_prompt_formatter=SystemPromptFormatter()
        )

        # Get version
        base_version = await get_next_version()

        # Create eval config
        config = GymEvalConfig(
            agents=[agent],
            version=base_version,
            version_description=f"model:{model}\ntype:{task.task_key}",
            exit_on_task_success=True,
            task=task,
            agent_cards=[agent.get_agent_card()],
            env_id=env_id
        )

        # Create visual runner
        log_dir = Path("../.fle/trajectory_logs") / f"v{config.version}"
        runner = VisualTrajectoryRunner(
            config=config,
            gym_env=gym_env,
            db_client=db_client,
            log_dir=str(log_dir),
            process_id=0,
            update_queue=self.update_queue
        )

        # Run trajectory
        await runner.run()
        await db_client.cleanup()

    def process_updates(self):
        """Process updates from the runner."""
        while not self.update_queue.empty():
            update = self.update_queue.get()

            if update['type'] == 'init':
                self.max_steps = update.get('max_steps', 100)
                self.step_label.set_text(f'Step: 0 / {self.max_steps}')
                self.status_label.set_text('Status: Running')
                if update.get('image'):
                    self.update_game_image(update['image'])

            elif update['type'] == 'code':
                self.code_display.set_content(update['code'])

            elif update['type'] == 'update':
                self.current_step = update['step']
                self.progress_bar.set_value(self.current_step / self.max_steps)
                self.step_label.set_text(f'Step: {self.current_step} / {self.max_steps}')

                # Update stats
                self.score_label.set_text(f'Score: {update.get("score", 0):.2f}')

                if 'observation' in update:
                    obs = update['observation']
                    self.inventory_label.set_text(f'Inventory Items: {obs.get("inventory_count", 0)}')
                    self.entities_label.set_text(f'Entities: {obs.get("entities_count", 0)}')
                    self.research_label.set_text(f'Research Progress: {obs.get("research_progress", 0) * 100:.1f}%')

                # Update image
                if update.get('image'):
                    self.update_game_image(update['image'])

                # Add to log
                if update.get('output'):
                    self.add_log_entry(
                        f"Step {self.current_step}",
                        update['output'],
                        is_error=update.get('error', False)
                    )

            elif update['type'] == 'complete':
                self.is_running = False
                self.start_button.props('disabled=false')
                self.stop_button.props('disabled')
                status = 'Success!' if update.get('success') else 'Completed'
                self.status_label.set_text(f'Status: {status}')

            elif update['type'] == 'error':
                self.add_log_entry('Error', update['message'], is_error=True)
                self.status_label.set_text('Status: Error')
                self.is_running = False
                self.start_button.props('disabled=false')
                self.stop_button.props('disabled')

    def update_game_image(self, base64_image: str):
        """Update the game view image."""
        self.game_image.set_source(f'data:image/png;base64,{base64_image}')

    def add_log_entry(self, title: str, content: str, is_error: bool = False):
        """Add an entry to the log display."""
        with self.log_display:
            color = 'red' if is_error else 'green'
            ui.label(f'[{datetime.now().strftime("%H:%M:%S")}] {title}').classes(f'text-{color}-600 font-bold')
            ui.label(content).classes('text-sm mb-2')

        # Auto-scroll to bottom
        self.log_container.scroll_to(percent=1.0)


def main():
    """Main entry point for visual runner."""
    parser = argparse.ArgumentParser(description='Visual runner for Factorio Learning Environment')
    parser.add_argument('--port', type=int, default=8080, help='Port for web interface')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host for web interface')
    args = parser.parse_args()

    # Create and run viewer
    viewer = FactorioViewer()

    @ui.page('/')
    def index():
        viewer.create_ui()

    ui.run(
        host=args.host,
        port=args.port,
        title='Factorio Learning Environment Viewer',
        favicon='🏭'
    )


#if __name__ == '__main__', "__mp_main__"}:
main()