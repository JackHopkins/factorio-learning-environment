#!/usr/bin/env python3
"""
Minimal overlay control panel for Factorio Learning Environment.
Designed to sit alongside the Factorio client window.
"""

import argparse
import asyncio
import base64
import random
import time
import threading
import logging
from collections import deque
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Optional, List, Dict, Any

import gym
from nicegui import ui, Client
from nicegui import events

from fle.agents.gym_agent import GymAgent
from fle.commons.db_client import create_db_client
from fle.env.gym_env.action import Action
from fle.env.gym_env.config import GymEvalConfig, GymRunConfig
from fle.env.gym_env.environment import FactorioGymEnv
from fle.env.gym_env.observation import Observation
from fle.env.gym_env.observation_formatter import BasicObservationFormatter
from fle.env.gym_env.registry import get_environment_info, list_available_environments
from fle.env.gym_env.system_prompt_formatter import SystemPromptFormatter
from fle.env.gym_env.trajectory_runner import GymTrajectoryRunner
from fle.eval.algorithms.independent import get_next_version

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('factorio_overlay.log')
    ]
)
logger = logging.getLogger(__name__)


class IconManager:
    """Manages loading and caching of Factorio sprite icons."""

    def __init__(self, sprites_path: Path = Path("/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/.fle/sprites")):
        self.sprites_path = sprites_path
        self.icon_cache = {}
        self.base64_cache = {}
        self._load_available_icons()

    def _load_available_icons(self):
        """Scan the sprites directory and cache available icons."""
        if not self.sprites_path.exists():
            logger.warning(f"Sprites directory not found: {self.sprites_path}")
            return

        for icon_file in self.sprites_path.glob("icon_*.png"):
            # Extract item name from filename (e.g., "icon-transport_belt.png" -> "transport-belt")
            item_name = icon_file.stem.replace("icon_", "").replace("_", "-")
            self.icon_cache[item_name] = icon_file
            logger.debug(f"Cached icon for {item_name}: {icon_file}")

    def get_icon_path(self, item_name: str) -> Optional[Path]:
        """Get the file path for an item's icon."""
        # Try exact match first
        if item_name in self.icon_cache:
            return self.icon_cache[item_name]

        # Try with underscores instead of hyphens
        alt_name = item_name.replace("-", "_")
        if alt_name in self.icon_cache:
            return self.icon_cache[alt_name]

        # Try to find partial matches
        for cached_name, path in self.icon_cache.items():
            if cached_name in item_name or item_name in cached_name:
                return path

        return None

    def get_icon_base64(self, item_name: str) -> Optional[str]:
        """Get base64 encoded icon for an item."""
        if item_name in self.base64_cache:
            return self.base64_cache[item_name]

        icon_path = self.get_icon_path(item_name)
        if not icon_path or not icon_path.exists():
            return None

        try:
            with open(icon_path, "rb") as f:
                icon_data = f.read()
                base64_data = base64.b64encode(icon_data).decode('utf-8')
                self.base64_cache[item_name] = f"data:image/png;base64,{base64_data}"
                return self.base64_cache[item_name]
        except Exception as e:
            logger.error(f"Error loading icon for {item_name}: {e}")
            return None

    def get_icon_url(self, item_name: str) -> str:
        """Get icon URL or fallback emoji."""
        base64_icon = self.get_icon_base64(item_name)
        if base64_icon:
            return base64_icon

        # Fallback to emoji if no icon found
        return self.get_emoji_fallback(item_name)

    def get_emoji_fallback(self, item_name: str) -> str:
        """Get emoji fallback for items without sprites."""
        icon_map = {
            'iron-ore': '🪨',
            'copper-ore': '🟤',
            'coal': '⚫',
            'stone': '🗿',
            'wood': '🪵',
            'iron-plate': '🔩',
            'copper-plate': '🟠',
            'steel-plate': '⚙️',
            'electronic-circuit': '💾',
            'advanced-circuit': '🔌',
            'processing-unit': '🖥️',
            'transport-belt': '📦',
            'inserter': '🦾',
            'assembling-machine': '🏭',
            'electric-mining-drill': '⛏️',
            'furnace': '🔥',
            'lab': '🧪',
            'science-pack': '🧬',
            'pipe': '🚰',
            'gear-wheel': '⚙️',
            'automation-science-pack': '🔴',
            'logistic-science-pack': '🟢',
            'military-science-pack': '⚫',
            'chemical-science-pack': '🔵',
            'production-science-pack': '🟣',
            'utility-science-pack': '🟡',
            'coin': '🪙',  # Add coin fallback
        }

        for key, icon in icon_map.items():
            if key in item_name.lower():
                return icon

        return '📦'


class VisualTrajectoryRunner(GymTrajectoryRunner):
    """Extended trajectory runner with visual updates."""

    def __init__(self, *args, update_queue: Optional[Queue] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_queue = update_queue
        self.render_tool = None
        logger.info("VisualTrajectoryRunner initialized with update_queue: %s", update_queue is not None)

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
        logger.info("Starting VisualTrajectoryRunner.run()")
        try:
            # Initialize state
            max_steps = self.config.task.trajectory_length
            logger.debug("Max steps: %d", max_steps)

            current_state, agent_steps = await self._initialize_trajectory_state()
            logger.info("Trajectory state initialized, agent_steps: %s", agent_steps)

            # Save system prompts
            for agent_idx, agent in enumerate(self.agents):
                self.logger.save_system_prompt(agent, agent_idx)
                logger.debug("Saved system prompt for agent %d", agent_idx)

            # Send initial update
            if self.update_queue:
                init_msg = {
                    'type': 'init',
                    'task': self.config.task.goal_description,
                    'max_steps': max_steps,
                    'num_agents': len(self.agents),
                    'image': self._get_rendered_image()
                }
                self.update_queue.put(init_msg)
                logger.info("Sent init message to update_queue")

            # Run trajectory
            from itertools import product
            for step_num, agent_idx in product(range(max_steps), range(len(self.agents))):
                logger.debug("Processing step %d for agent %d", step_num, agent_idx)
                agent = self.agents[agent_idx]
                iteration_start = time.time()
                agent_completed = False

                try:
                    while not agent_completed and agent_steps[agent_idx] < max_steps:
                        # Generate policy
                        logger.debug("Generating policy for agent %d at step %d", agent_idx, agent_steps[agent_idx])
                        policy = await agent.generate_policy()
                        agent_steps[agent_idx] += 1

                        if not policy:
                            logger.warning("Policy generation failed for agent %d", agent_idx)
                            print(f"Policy generation failed for agent {agent_idx}")
                            break

                        logger.debug("Policy generated successfully, executing action")

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

                        logger.debug("Step executed - reward: %f, terminated: %s, truncated: %s",
                                     reward, terminated, truncated)

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

                        # Send visual update with production data
                        if self.update_queue:
                            update_msg = {
                                'type': 'update',
                                'agent_idx': agent_idx,
                                'step': agent_steps[agent_idx],
                                'reward': reward,
                                'score': program.value,
                                'output': obs_dict["raw_text"][:500],  # First 500 chars
                                'error': info["error_occurred"],
                                'image': self._get_rendered_image(agent_idx),
                                'observation': self._format_observation_summary(observation),
                                'inventory': observation.inventory,
                                'production_flows': observation.flows.to_dict() if observation.flows else None
                            }
                            self.update_queue.put(update_msg)
                            logger.debug("Sent update message for step %d", agent_steps[agent_idx])

                        # Check completion
                        agent_completed, update_state = agent.check_step_completion(observation)
                        if update_state:
                            current_state = output_game_state
                            logger.debug("Updated game state")

                        # Check if done
                        if done and self.config.exit_on_task_success:
                            logger.info("Task completed successfully at step %d", agent_steps[agent_idx])
                            if self.update_queue:
                                self.update_queue.put({
                                    'type': 'complete',
                                    'success': True,
                                    'final_step': agent_steps[agent_idx]
                                })
                            return

                except Exception as e:
                    logger.error("Error in trajectory runner loop: %s", e, exc_info=True)
                    print(f"Error in trajectory runner: {e}")
                    if self.update_queue:
                        self.update_queue.put({
                            'type': 'error',
                            'message': str(e)
                        })
                    continue

            # Send completion update
            logger.info("Trajectory completed, max steps reached")
            if self.update_queue:
                self.update_queue.put({
                    'type': 'complete',
                    'success': False,
                    'final_step': max(agent_steps)
                })

        except Exception as e:
            logger.error("Fatal error in VisualTrajectoryRunner.run(): %s", e, exc_info=True)
            raise

    def _format_observation_summary(self, observation: Observation) -> Dict[str, Any]:
        """Format observation into a summary for display."""
        return {
            'inventory_count': len(observation.inventory),
            'entities_count': len(observation.entities),
            'score': observation.score,
            'game_tick': observation.game_info.tick,
            'research_progress': observation.research.research_progress if observation.research.current_research else 0
        }


import asyncio
import json
from queue import Queue
import threading
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import websocket
import json


class FactorioControlPanel:
    """Minimal control panel for Factorio agent gameplay."""

    def __init__(self, env_id: str = None,
                 model: str = None,
                 mcp_server_path: str = "fle/env/protocols/mcp/server.py",
                 websocket_url: str = "ws://localhost:8000/ws"):
        logger.info("Initializing FactorioControlPanel")

        self.ws_url = websocket_url
        self.ws = None

        self.mcp_server_path = mcp_server_path or "fle/env/protocols/mcp/server.py"
        self.mcp_session = None

        self.update_queue = Queue()
        self.runner_thread = None
        self.current_step = 0
        self.max_steps = 100
        self.is_running = False

        # Fixed configuration
        self.env_id = env_id or 'steel_plate_throughput'
        self.model = model or 'openai/gpt-5-mini'
        logger.info("Configuration - env_id: %s, model: %s", self.env_id, self.model)

        # Initialize icon manager
        self.icon_manager = IconManager()

        # Inventory data
        self.inventory_items = {}

        # Score tracking for delta display
        self.last_score = 0
        self.score_delta = 0

        # Production chart data
        self.production_history = {
            'timestamps': deque(maxlen=50),
            'data': {}  # Will store production outputs
        }
        self.chart = None

        # UI elements (will be initialized in create_ui)
        self.coin_icon = None
        self.score_label = None

        # Start run automatically
        self.auto_start = True
        logger.info("Auto-start enabled: %s", self.auto_start)

    def connect_to_bridge(self):
        """Connect to the MCP bridge via WebSocket"""
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

        # Run in background thread
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()

    def on_message(self, ws, message):
        """Handle incoming game state updates"""
        update = json.loads(message)
        self.update_queue.put(update)


    async def connect_to_mcp(self):
        """Connect to the MCP server"""
        server_params = StdioServerParameters(
            command="python",
            args=[self.mcp_server_path],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.mcp_session = session
                await session.initialize()

                # Subscribe to state updates
                await self._subscribe_to_updates()

    async def _subscribe_to_updates(self):
        """Subscribe to game state updates from MCP"""
        # Poll for updates periodically
        while True:
            try:
                # Get current game state via MCP tools
                result = await self.mcp_session.call_tool(
                    "get_game_state",
                    arguments={}
                )

                # Convert to update format expected by UI
                update = self._convert_mcp_to_ui_update(result)
                self.update_queue.put(update)

                await asyncio.sleep(0.5)  # Update frequency
            except Exception as e:
                print(f"Error getting updates: {e}")

    def _convert_mcp_to_ui_update(self, mcp_result):
        """Convert MCP response to UI update format"""
        # Parse the MCP result and format for your UI
        return {
            'type': 'update',
            'inventory': mcp_result.get('inventory', {}),
            'score': mcp_result.get('score', 0),
            'entities_count': mcp_result.get('entities_count', 0),
            # ... other fields
        }

    def update_inventory_display(self):
        """Update the inventory grid display with sprite icons."""
        self.inventory_grid.clear()

        with self.inventory_grid:
            # Sort items by count (descending)
            sorted_items = sorted(self.inventory_items.items(), key=lambda x: x[1], reverse=True)

            for item_name, count in sorted_items[:20]:  # Show top 20 items
                with ui.card().classes('w-16 h-16 bg-gray-700 p-1 relative overflow-hidden'):
                    # Try to get sprite icon
                    icon_data = self.icon_manager.get_icon_base64(item_name)

                    if icon_data:
                        # Use actual sprite icon
                        ui.image(icon_data).classes(
                            'absolute inset-0 w-full h-full object-contain p-1'
                        )
                    else:
                        # Fallback to emoji
                        emoji = self.icon_manager.get_emoji_fallback(item_name)
                        ui.label(emoji).classes(
                            'text-2xl absolute top-1 left-1/2 transform -translate-x-1/2'
                        )

                    # Count badge
                    ui.label(str(count)).classes(
                        'text-sm text-white absolute bottom-0 right-1 bg-gray-900 px-1 rounded font-bold'
                    )
                    # Tooltip with item name
                    ui.tooltip(item_name)

    def update_production_chart(self, production_flows: Dict[str, Any]):
        """Update the production chart with new data."""
        if not production_flows:
            return

        # Add timestamp
        self.production_history['timestamps'].append(time.time())

        # Track production outputs
        outputs = production_flows.get('output', {})
        for item, amount in outputs.items():
            if item not in self.production_history['data']:
                self.production_history['data'][item] = deque(maxlen=50)
            self.production_history['data'][item].append(amount)

        # Pad shorter series with zeros
        max_len = len(self.production_history['timestamps'])
        for series in self.production_history['data'].values():
            while len(series) < max_len:
                series.appendleft(0)

        # Update chart
        if self.chart:
            self.update_chart_display()

    def update_chart_display(self):
        """Update the chart visualization with icon legends."""
        if not self.chart:
            return

        # Prepare data for ECharts
        x_data = list(range(len(self.production_history['timestamps'])))

        # Colors for different production lines
        colors = [
            '#FF6384',
            '#36A2EB',
            '#FFCE56',
            '#4BC0C0',
            '#9966FF',
            '#FF9F40'
        ]

        # Add top 5 production items
        top_items = sorted(
            self.production_history['data'].items(),
            key=lambda x: sum(x[1]) if x[1] else 0,
            reverse=True
        )[:5]

        series = []
        legend_data = []

        for i, (item_name, values) in enumerate(top_items):
            color = colors[i % len(colors)]

            # Format legend with icon if available
            icon_data = self.icon_manager.get_icon_base64(item_name)
            legend_name = item_name[:20]  # Truncate long names

            series.append({
                'name': legend_name,
                'type': 'line',
                'data': list(values),
                'smooth': True,
                'lineStyle': {'color': color, 'width': 2},
                'itemStyle': {'color': color},
                'symbol': 'circle',
                'symbolSize': 6
            })

            # Add to legend with icon if available
            if icon_data:
                legend_data.append({
                    'name': legend_name,
                    'icon': f'image://{icon_data}'
                })
            else:
                legend_data.append(legend_name)

        # Update chart options
        chart_options = {
            'backgroundColor': 'transparent',
            'xAxis': {
                'type': 'category',
                'data': x_data,
                'axisLabel': {'color': 'rgba(255, 255, 255, 0.7)'},
                'axisLine': {'lineStyle': {'color': 'rgba(255, 255, 255, 0.3)'}}
            },
            'yAxis': {
                'type': 'value',
                'axisLabel': {'color': 'rgba(255, 255, 255, 0.7)'},
                'splitLine': {'lineStyle': {'color': 'rgba(255, 255, 255, 0.1)'}}
            },
            'series': series,
            'legend': {
                'data': legend_data if isinstance(legend_data[0], str) else [item['name'] for item in legend_data],
                'textStyle': {'color': 'rgba(255, 255, 255, 0.7)'},
                'itemWidth': 20,
                'itemHeight': 20,
                'top': 0
            },
            'grid': {
                'left': '5%',
                'right': '5%',
                'bottom': '5%',
                'top': '15%',
                'containLabel': True
            },
            'tooltip': {
                'trigger': 'axis',
                'backgroundColor': 'rgba(0, 0, 0, 0.8)',
                'borderColor': '#333',
                'textStyle': {'color': '#fff'}
            }
        }

        # Update chart with new options using the update method
        self.chart.options['series'] = chart_options['series']
        self.chart.options['xAxis']['data'] = chart_options['xAxis']['data']
        self.chart.options['legend']['data'] = chart_options['legend']['data']
        self.chart.update()

    def process_updates(self):
        """Process updates from the runner."""
        while not self.update_queue.empty():
            update = self.update_queue.get()

            if update['type'] == 'init':
                self.max_steps = update.get('max_steps', 100)
                self.step_label.set_text(f'Step: 0 / {self.max_steps}')
                self.status_label.set_text('🟢 Running')

                # Set the coin icon once at initialization
                coin_icon_data = self.icon_manager.get_icon_base64('coin')
                if coin_icon_data and self.coin_icon:
                    self.coin_icon.set_source(coin_icon_data)
                elif self.coin_icon:
                    # Use emoji fallback if no icon found
                    self.coin_icon.set_source('')
                    self.coin_icon.classes('hidden')  # Hide image element
                    # Create emoji fallback (would need to modify UI structure for this)

            elif update['type'] == 'update':
                self.current_step = update['step']
                self.progress_bar.set_value(self.current_step / self.max_steps)
                self.step_label.set_text(f'Step: {self.current_step} / {self.max_steps}')

                # Update score with delta
                new_score = update.get("score", 0)
                reward = update.get("reward", 0)

                # Build score text with reward indicator
                score_text = f'{new_score:.2f}'

                # Add reward indicator (green with + or -)
                if reward != 0:
                    if reward > 0:
                        reward_text = f'<span style="color: #10b981; font-size: 0.8em; vertical-align: super;">+{reward:.3f}</span>'
                    else:
                        reward_text = f'<span style="color: #ef4444; font-size: 0.8em; vertical-align: super;">{reward:.3f}</span>'
                    self.score_label.set_content(score_text + ' ' + reward_text)
                else:
                    self.score_label.set_content(score_text)

                self.last_score = new_score

                if 'observation' in update:
                    obs = update['observation']
                    self.entities_label.set_text(f'Entities: {obs.get("entities_count", 0)}')
                    self.tick_label.set_text(f'Tick: {obs.get("game_tick", 0):,}')
                    research_pct = obs.get("research_progress", 0) * 100
                    self.research_label.set_text(f'Research: {research_pct:.1f}%')

                # Update inventory
                if 'inventory' in update and update['inventory']:
                    self.inventory_items = update['inventory']
                    self.update_inventory_display()

                # Update production chart
                if 'production_flows' in update:
                    self.update_production_chart(update['production_flows'])

            elif update['type'] == 'complete':
                self.is_running = False
                status = '✅ Complete' if update.get('success') else '⏹️ Finished'
                self.status_label.set_text(status)

            elif update['type'] == 'error':
                self.status_label.set_text('❌ Error')
                self.is_running = False

    def create_ui(self):
        """Create the minimal control panel interface with production chart on the right."""
        # Prevent duplicate UI creation
        if hasattr(self, '_ui_created'):
            logger.warning("UI already created, skipping duplicate creation")
            return
        self._ui_created = True

        # Main container with horizontal layout using flexbox
        with ui.row().classes('w-full h-screen p-4 bg-gray-900 justify-between'):

            # LEFT COLUMN - Control panel and stats
            with ui.column().classes('w-96 flex-shrink-0'):
                # Header
                with ui.card().classes('w-full bg-gray-800 text-white'):
                    ui.label('Factorio Learning Environment').classes('text-xl font-bold text-center')
                    self.status_label = ui.label('⚪ Initializing...').classes('text-sm text-center')

                    # Task (readonly)
                    ui.input(
                        label='Task',
                        value=self.env_id.split('-')[1] if '-' in self.env_id else self.env_id
                    ).props('readonly').classes('w-full text-xs')

                    # Model (readonly)
                    ui.input(
                        label='Model',
                        value=self.model.split('/')[-1] if '/' in self.model else self.model
                    ).props('readonly').classes('w-full text-xs')

                    # Progress
                    self.progress_bar = ui.linear_progress(value=0).classes('w-full')
                    with ui.row().classes('w-full justify-between'):
                        self.step_label = ui.label('Step: 0 / 100').classes('text-xs')
                        self.tick_label = ui.label('Tick: 0').classes('text-xs')

                # Stats
                with ui.card().classes('w-full bg-gray-800 text-white mt-2'):
                    ui.label('Statistics').classes('text-sm font-bold')

                    # Score with coin icon container
                    with ui.row().classes('items-center gap-1'):
                        # Coin icon (will be set during init)
                        self.coin_icon = ui.image('').classes('w-4 h-4')
                        # Score label
                        self.score_label = ui.html('0.00').classes('text-sm')

                    with ui.row().classes('w-full justify-between text-xs mt-1'):
                        self.entities_label = ui.label('Entities: 0')
                        self.research_label = ui.label('Research: 0%')

                # Inventory Grid
                with ui.card().classes('w-full bg-gray-800 text-white mt-2'):
                    ui.label('Inventory').classes('text-sm font-bold')
                    self.inventory_grid = ui.row().classes('w-full flex-wrap gap-3')
                    with self.inventory_grid:
                        # Initial placeholder
                        ui.label('No items yet').classes('text-xs text-gray-400')

            # MIDDLE SPACE - Empty area for Factorio window
            ui.element('div').classes('flex-1')  # This creates the empty middle space

            # RIGHT COLUMN - Production Chart
            with ui.column().classes('w-[500px] flex-shrink-0'):
                with ui.card().classes('w-full h-full bg-gray-800 text-white'):
                    ui.label('Production Output').classes('text-sm font-bold mb-2')
                    # Create chart container with ECharts
                    self.chart = ui.echart({
                        'backgroundColor': 'transparent',
                        'xAxis': {
                            'type': 'category',
                            'data': [],
                            'axisLabel': {'color': 'rgba(255, 255, 255, 0.7)'},
                            'axisLine': {'lineStyle': {'color': 'rgba(255, 255, 255, 0.3)'}}
                        },
                        'yAxis': {
                            'type': 'log',  # Changed to logarithmic scale
                            'logBase': 10,  # Base 10 logarithm
                            'axisLabel': {'color': 'rgba(255, 255, 255, 0.7)'},
                            'splitLine': {'lineStyle': {'color': 'rgba(255, 255, 255, 0.1)'}},
                            'min': 1  # Minimum value to avoid log(0) issues
                        },
                        'series': [],
                        'legend': {
                            'data': [],
                            'textStyle': {'color': 'rgba(255, 255, 255, 0.7)'},
                            'itemWidth': 20,
                            'itemHeight': 20
                        },
                        'grid': {
                            'left': '5%',
                            'right': '5%',
                            'bottom': '5%',
                            'top': '15%',
                            'containLabel': True
                        },
                        'tooltip': {
                            'trigger': 'axis',
                            'backgroundColor': 'rgba(0, 0, 0, 0.8)',
                            'borderColor': '#333',
                            'textStyle': {'color': '#fff'}
                        }
                    }).classes('w-full h-[500px]')

        # Set up periodic updates
        ui.timer(0.5, self.process_updates)
        logger.info("Process updates timer set up (0.5s interval)")

        # Auto-start if enabled - schedule after UI is ready
        if self.auto_start:
            logger.info("Auto-start is enabled, setting up timer to start in 2 seconds")
            # Use a timer to ensure UI is fully initialized before starting
            ui.timer(2.0, lambda: self._auto_start_callback(), once=True)
        else:
            logger.info("Auto-start is disabled")

    def _auto_start_callback(self):
        """Callback for auto-start timer."""
        logger.info("Auto-start timer triggered")
        self.start_run()

    def start_run(self):
        """Start a new run automatically."""
        logger.info("start_run() called - is_running: %s", self.is_running)
        if not self.is_running:
            self.is_running = True
            self.status_label.set_text('🟡 Starting...')
            self.current_step = 0
            self.cumulative_score = 0  # Reset cumulative score
            if hasattr(self, 'score_history'):
                self.score_history.clear()  # Clear score history
            else:
                self.score_history = deque(maxlen=50)  # Initialize if not exists
            self.inventory_items = {}
            self.production_history = {
                'timestamps': deque(maxlen=50),
                'data': {}
            }
            logger.info("Starting trajectory runner thread")

            # Start runner in background thread
            self.runner_thread = threading.Thread(target=self._run_trajectory)
            self.runner_thread.daemon = True
            self.runner_thread.start()
            logger.info("Trajectory runner thread started - thread alive: %s", self.runner_thread.is_alive())
        else:
            logger.warning("start_run() called but already running")

    def _run_trajectory(self):
        """Run the trajectory in a background thread."""
        logger.info("_run_trajectory thread started")
        try:
            logger.info("Starting asyncio.run for _async_run_trajectory")
            asyncio.run(self._async_run_trajectory())
            logger.info("_async_run_trajectory completed successfully")
        except Exception as e:
            logger.error("Exception in _run_trajectory: %s", e, exc_info=True)
            self.update_queue.put({
                'type': 'error',
                'message': str(e),
            })

    async def _async_run_trajectory(self):
        """Async trajectory runner."""
        logger.info("_async_run_trajectory started - env_id: %s, model: %s", self.env_id, self.model)

        try:
            # Get environment info
            logger.info("Getting environment info for %s", self.env_id)
            env_info = get_environment_info(self.env_id)
            if not env_info:
                logger.error("Could not get environment info for %s", self.env_id)
                self.update_queue.put({
                    'type': 'error',
                    'message': f'Could not get environment info for {self.env_id}'
                })
                return
            logger.info("Environment info retrieved successfully")

            # Create database client
            logger.info("Creating database client")
            db_client = await create_db_client()
            logger.info("Database client created")

            # Create gym environment
            logger.info("Creating gym environment")
            gym_env = gym.make(self.env_id)
            gym_env_unwrapped: FactorioGymEnv = gym_env.unwrapped
            task = gym_env_unwrapped.task
            instance = gym_env_unwrapped.instance
            logger.info("Gym environment created - task: %s", task.task_key if task else "None")

            # Create agent
            logger.info("Creating agent with model %s", self.model)
            system_prompt = instance.get_system_prompt(0)
            agent = GymAgent(
                model=self.model,
                system_prompt=system_prompt,
                task=task,
                agent_idx=0,
                observation_formatter=BasicObservationFormatter(include_research=False),
                system_prompt_formatter=SystemPromptFormatter()
            )
            logger.info("Agent created successfully")

            # Get version
            logger.info("Getting next version")
            base_version = await get_next_version()
            logger.info("Version: %s", base_version)

            # Create eval config
            logger.info("Creating eval config")
            config = GymEvalConfig(
                agents=[agent],
                version=base_version,
                version_description=f"model:{self.model}\ntype:{task.task_key}",
                task=task,
                agent_cards=[agent.get_agent_card()],
                env_id=self.env_id
            )
            logger.info("Eval config created")

            # Create visual runner
            log_dir = Path("../.fle/trajectory_logs") / f"v{config.version}"
            logger.info("Creating VisualTrajectoryRunner with log_dir: %s", log_dir)
            runner = VisualTrajectoryRunner(
                config=config,
                gym_env=gym_env,
                db_client=db_client,
                log_dir=str(log_dir),
                process_id=0,
                update_queue=self.update_queue
            )
            logger.info("VisualTrajectoryRunner created")

            # Run trajectory
            logger.info("Starting trajectory run")
            await runner.run()
            logger.info("Trajectory run completed")

            await db_client.cleanup()
            logger.info("Database client cleaned up")

        except Exception as e:
            logger.error("Fatal error in _async_run_trajectory: %s", e, exc_info=True)
            self.update_queue.put({
                'type': 'error',
                'message': f'Fatal error: {str(e)}'
            })
            raise


def main():
    """Main entry point for minimal control panel."""
    logger.info("=== Starting Factorio Control Panel ===")

    parser = argparse.ArgumentParser(description='Minimal control panel for Factorio Learning Environment')
    parser.add_argument('--port', type=int, default=8080, help='Port for web interface')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host for web interface')
    parser.add_argument('--env', type=str, default='steel_plate_throughput', help='Environment ID')
    parser.add_argument('--model', type=str, default='openai/gpt-5-mini', help='Model to use')
    args = parser.parse_args()

    logger.info("Command line args - host: %s, port: %d, env: %s, model: %s",
                args.host, args.port, args.env, args.model)

    # Create control panel with specified configuration
    panel = FactorioControlPanel(env_id=args.env, model=args.model)
    logger.info("FactorioControlPanel instance created")

    @ui.page('/')
    def index():
        logger.info("Index page accessed")
        # Set dark theme and compact layout
        ui.dark_mode().enable()
        logger.info("Creating UI")
        panel.create_ui()
        logger.info("UI created successfully")

    logger.info("Starting NiceGUI server on %s:%d", args.host, args.port)
    ui.run(
        host=args.host,
        port=args.port,
        title='Factorio Monitor',
        favicon='🏭',
        dark=True,
        reload=False
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()