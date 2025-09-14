#!/usr/bin/env python3
"""
Visual runner for Factorio Learning Environment with NiceGUI interface.
This module provides a web-based viewer for watching agents play Factorio in real-time.
"""

import argparse
import asyncio
import platform
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Optional, Dict, Any, List

import gym
from nicegui import ui

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


class FactorioWindowStreamer:
    """Captures and streams the Factorio window to HLS format."""

    def __init__(self, output_path="/tmp/factorio_stream.m3u8"):
        self.output_path = output_path
        self.process = None
        self.capture_thread = None
        self.is_streaming = False

    def find_factorio_window(self):
        """Find the Factorio window on macOS."""
        if platform.system() != "Darwin":
            return None

        try:
            from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID

            windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
            for window in windows:
                print(window.get('kCGWindowOwnerName', ''))
                if 'factorio' in window.get('kCGWindowOwnerName', ''):
                    return window
        except ImportError:
            print("pyobjc-framework-Quartz not installed. Install with: pip install pyobjc-framework-Quartz")
        except Exception as e:
            print(f"Error finding Factorio window: {e}")
        return None

    def start(self):
        """Use macOS screencapture utility instead of FFmpeg screen capture."""
        if self.is_streaming:
            return False

        # Clean up
        import os
        import glob
        import threading
        import time
        import tempfile

        for f in glob.glob('/tmp/factorio_stream*'):
            try:
                os.remove(f)
            except:
                pass

        print("Starting screenshot-based capture (FFmpeg screen capture not working)...")

        # Create temp directory for frames
        self.temp_dir = tempfile.mkdtemp(prefix='factorio_frames_')
        self.frame_count = 0
        self.is_streaming = True

        def capture_and_stream():
            """Capture screenshots and convert to HLS stream."""

            # Start FFmpeg to convert images to HLS
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'avfoundation', '-capture_cursor', '1', '-framerate', '30',
                '-pixel_format', 'nv12',
                # Optional but often stabilizes AVFoundation on some setups; set to your display's native res:
                # '-video_size','2560x1440',
                '-i', '2:none',
                '-vf', 'scale=1280:720:flags=bicubic,format=nv12',
                '-c:v', 'h264_videotoolbox', '-realtime', '1',
                '-b:v', '6000k', '-maxrate', '6000k', '-bufsize', '12000k',
                '-g', '30', '-tune', 'zerolatency',
                '-f', 'hls', '-hls_time', '1', '-hls_list_size', '8', '-hls_flags', 'delete_segments',
                '-hls_segment_filename', '/tmp/factorio_stream%03d.ts',
                self.output_path
            ]
            # ffmpeg_cmd = [
            #     'ffmpeg',
            #     '-f', 'image2pipe',
            #     '-i', '3',  # Device 3 = Screen 1 (secondary monitor)
            #     '-c:v', 'h264_videotoolbox',
            #     '-preset', 'ultrafast',
            #     '-vf', 'scale=1280:720',
            #     '-b:v', '2M',
            #     '-f', 'hls',
            #     '-hls_time', '2',
            #     '-hls_list_size', '5',
            #     '-hls_segment_filename', '/tmp/factorio_stream%03d.ts',
            #     '/tmp/factorio_stream.m3u8'
            # ]

            self.process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            print("FFmpeg HLS encoder started")

            # Capture loop
            while self.is_streaming:
                try:
                    # Capture screenshot to temp file
                    temp_file = os.path.join(self.temp_dir, f'frame_{self.frame_count:06d}.png')

                    # Use screencapture (works when FFmpeg screen capture doesn't)
                    result = subprocess.run(
                        ['screencapture', '-x', '-C', '-t', 'png', temp_file],
                        capture_output=True,
                        timeout=1
                    )

                    if result.returncode == 0 and os.path.exists(temp_file):
                        # Read the image and send to FFmpeg
                        with open(temp_file, 'rb') as f:
                            image_data = f.read()

                        if self.process.stdin:
                            self.process.stdin.write(image_data)
                            self.process.stdin.flush()

                        # Clean up the temp file
                        os.remove(temp_file)
                        self.frame_count += 1

                        if self.frame_count % 50 == 0:
                            segments = glob.glob('/tmp/factorio_stream*.ts')
                            print(f"Captured {self.frame_count} frames, {len(segments)} HLS segments")

                    # Control frame rate (10 FPS)
                    time.sleep(0.1)

                except BrokenPipeError:
                    print("FFmpeg pipe broken, stopping capture")
                    break
                except Exception as e:
                    print(f"Capture error: {e}")
                    time.sleep(0.1)

            # Cleanup
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Start capture thread
        self.capture_thread = threading.Thread(target=capture_and_stream)
        self.capture_thread.daemon = True
        self.capture_thread.start()

        # Verify it's working
        def verify():
            time.sleep(3)
            segments = glob.glob('/tmp/factorio_stream*.ts')
            if segments:
                print(f"✓ Streaming working with {len(segments)} segments")
            else:
                print("⚠ No segments created, screencapture may need permission")

        verify_thread = threading.Thread(target=verify)
        verify_thread.daemon = True
        verify_thread.start()

        return True

    def stop(self):
        """Stop streaming."""
        self.is_streaming = False

        if self.process:
            # Close stdin to signal FFmpeg to finish
            if self.process.stdin:
                self.process.stdin.close()

            # Wait for process to finish
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            self.process = None

        # Wait for capture thread
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=2)

        # Cleanup temp directory
        if hasattr(self, 'temp_dir'):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)


    def start_desktop_capture(self):
        """Simplified desktop capture."""
        try:
            cmd = [
                'ffmpeg',
                '-f', 'avfoundation',
                '-framerate', '15',
                '-capture_cursor', '1',
                '-i', '4:none',  # Capture screen 0
                '-vf', 'scale=1920:1080',
                '-c:v', 'h264_videotoolbox',
                '-preset', 'ultrafast',
                '-b:v', '3M',
                '-f', 'hls',
                '-hls_time', '1',
                '-hls_list_size', '3',
                '-hls_flags', 'delete_segments',
                '-hls_segment_filename', '/tmp/factorio_stream%d.ts',
                self.output_path
            ]

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.is_streaming = True
            print("Desktop capture started")
            return True
        except Exception as e:
            print(f"Failed to start desktop capture: {e}")
            return False


    def start_screen_capture(self):
        """Fallback to capture full screen if window capture fails."""
        try:
            cmd = [
                'ffmpeg',
                '-f', 'avfoundation',
                '-framerate', '30',
                '-i', '2:none',  # Main screen
                '-vf', 'scale=1280:720',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-tune', 'zerolatency',
                '-f', 'hls',
                '-hls_time', '2',
                '-hls_list_size', '5',
                '-hls_flags', 'delete_segments',
                self.output_path
            ]
            self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.is_streaming = True
            return True
        except Exception as e:
            print(f"Failed to start screen capture: {e}")
            return False




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
        self.streamer = FactorioWindowStreamer()
        self.http_server_process = None
        self.http_server_started = False  # Track if server already started

    def __del__(self):
        """Cleanup on deletion."""
        self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        self.streamer.stop()
        if self.http_server_process:
            self.http_server_process.terminate()

    def start_http_server(self):
        """Start HTTP server with CORS support for HLS files - ONLY ONCE."""
        import os
        import tempfile
        import signal

        # IMPORTANT: Only start once
        if self.http_server_started:
            print("HTTP server already started, skipping")
            return

        self.http_server_started = True

        if not os.path.exists('/tmp'):
            os.makedirs('/tmp')

        # Kill any existing process on port 8081
        try:
            result = subprocess.run(['lsof', '-ti:8081'], capture_output=True, text=True)
            if result.stdout:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    os.kill(int(pid), signal.SIGTERM)
                    print(f"Killed existing process on port 8081 (PID: {pid})")
                time.sleep(1)
        except Exception as e:
            print(f"Could not check/kill port 8081: {e}")

        # Create server script
        import textwrap
        server_code = textwrap.dedent('''
            import http.server
            import socketserver
            import os

            class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
                def end_headers(self):
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', '*')
                    self.send_header('Cache-Control', 'no-cache')
                    super().end_headers()

                def do_OPTIONS(self):
                    self.send_response(200)
                    self.end_headers()

                def log_message(self, format, *args):
                    # Suppress request logging
                    pass

            os.chdir('/tmp')
            PORT = 8081

            socketserver.TCPServer.allow_reuse_address = True

            with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
                print(f"HLS server running on port {PORT}")
                httpd.serve_forever()
        ''').strip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(server_code)
            server_script_path = f.name

        self.http_server_process = subprocess.Popen(
            ['python3', server_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        time.sleep(1)
        if self.http_server_process.poll() is not None:
            stdout, stderr = self.http_server_process.communicate()
            print(f"Server failed: {stderr.decode()}")
        else:
            print("Started HLS HTTP server on port 8081")

    def start_streaming_deferred(self):
        """Start streaming after UI is loaded."""
        try:
            print("\n=== Starting Stream ===")
            success = self.streamer.start()

            if success:
                # Wait for segments to be created
                ui.timer(5.0, self.check_and_start_video, once=True)
            else:
                print("Failed to start streaming")
        except Exception as e:
            print(f"Failed to start streaming: {e}")

    def check_and_start_video(self):
        """Check if segments exist and start video playback."""
        import glob
        segments = glob.glob('/tmp/factorio_stream*.ts')

        if segments:
            print(f"Found {len(segments)} segments, starting video player")
            ui.run_javascript('window.startStream && window.startStream()')
        else:
            print("No segments found yet, trying again...")
            # Try again in 2 seconds
            ui.timer(2.0, self.check_and_start_video, once=True)

    def check_stream_status(self):
        """Check if stream files are being created."""
        import os
        hls_file = "/tmp/factorio_stream.m3u8"
        if os.path.exists(hls_file):
            size = os.path.getsize(hls_file)
            mtime = datetime.fromtimestamp(os.path.getmtime(hls_file))
            print(f"HLS file exists: {size} bytes, last modified: {mtime}")

            # Check for segment files
            segments = [f for f in os.listdir("/tmp") if f.endswith('.ts')]
            print(f"Found {len(segments)} video segments")
        else:
            print("HLS file not found - stream may not be running")

    def create_ui(self):
        """Create the NiceGUI interface."""

        # Start HTTP server ONLY (not streaming yet)
        self.start_http_server()
        # DO NOT start streaming here - wait until UI is loaded

        # Add HLS.js and video streaming script to body
        ui.add_body_html('''
            <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
            <script>
                var hls = null;

                function updateStreamStatus(status, color) {
                    var streamStatus = document.getElementById('stream-status');
                    if (streamStatus) {
                        streamStatus.textContent = status;
                        streamStatus.style.background = color || 'rgba(0,0,0,0.7)';
                    }
                }

                function startStream(url) {
                    console.log('Starting stream connection...');
                    var video = document.getElementById('video-player');
                    var fallbackImg = document.getElementById('fallback-image');

                    if (!video || !fallbackImg) {
                        console.log('Video elements not ready, retrying...');
                        setTimeout(() => startStream(url), 1000);
                        return;
                    }

                    if (!url) url = 'http://127.0.0.1:8081/factorio_stream.m3u8';

                    // Destroy existing HLS instance
                    if (hls) {
                        hls.destroy();
                        hls = null;
                    }

                    if (Hls.isSupported()) {
                        hls = new Hls({
                            debug: false,
                            enableWorker: true,
                            lowLatencyMode: true,
                            backBufferLength: 2,
                            maxBufferLength: 10,
                            liveSyncDuration: 2,
                            liveMaxLatencyDuration: 5,
                            manifestLoadingTimeOut: 10000,
                            fragLoadingTimeOut: 10000,
                            startLevel: -1,
                        });

                        hls.loadSource(url);
                        hls.attachMedia(video);

                        hls.on(Hls.Events.MANIFEST_PARSED, function() {
                            console.log('Manifest parsed, playing video');
                            video.style.display = 'block';
                            fallbackImg.style.display = 'none';
                            video.play().catch(e => console.error('Play failed:', e));
                            updateStreamStatus('Stream connected', 'rgba(0,128,0,0.7)');
                        });

                        hls.on(Hls.Events.ERROR, function(event, data) {
                            console.error('HLS error:', data);
                            if (data.fatal) {
                                video.style.display = 'none';
                                fallbackImg.style.display = 'block';
                                updateStreamStatus('Stream error - retrying...', 'rgba(128,0,0,0.7)');

                                if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
                                    // Retry in 3 seconds
                                    setTimeout(() => startStream(url), 3000);
                                }
                            }
                        });

                        updateStreamStatus('Connecting to stream...', 'rgba(128,128,0,0.7)');
                    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                        // Native HLS support (Safari)
                        video.src = url;
                        video.addEventListener('loadedmetadata', function() {
                            video.style.display = 'block';
                            fallbackImg.style.display = 'none';
                            video.play();
                            updateStreamStatus('Stream connected (native)', 'rgba(0,128,0,0.7)');
                        });
                    }
                }

                // Expose functions globally
                window.startStream = startStream;
                window.updateGameImage = function(base64) {
                    var fallbackImg = document.getElementById('fallback-image');
                    if (fallbackImg) {
                        fallbackImg.src = 'data:image/png;base64,' + base64;
                    }
                };
            </script>
        ''')

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
                        value=tasks[0] if tasks else 'open_play'
                    ).classes('w-full')

                    # Model selector
                    self.model_select = ui.select(
                        label='Model',
                        options=['openai/gpt-4o-mini', 'anthropic/claude-3-5-sonnet-latest', 'openai/gpt-4o'],
                        value='openai/gpt-4o-mini'
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

                    # Stream Controls
                    ui.separator()
                    ui.label('Stream Settings').classes('text-lg font-bold mt-4')
                    with ui.row():
                        ui.button('Restart Stream', on_click=self.restart_stream)
                        ui.button('Check Status', on_click=lambda: self.streamer.check_stream_status())

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
                            # Video container HTML
                            ui.html('''
                                <div id="video-container" style="width: 100%; height: 600px; position: relative; background: #000;">
                                    <video id="video-player" autoplay muted playsinline 
                                           style="width: 100%; height: 100%; display: none; object-fit: contain;">
                                    </video>
                                    <img id="fallback-image" 
                                         style="width: 100%; height: 100%; object-fit: contain; display: block;" 
                                         src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" />
                                    <div id="stream-status" 
                                         style="position: absolute; top: 10px; right: 10px; 
                                                padding: 5px 10px; background: rgba(0,0,0,0.7); 
                                                color: white; border-radius: 5px; font-size: 12px;">
                                        Waiting for stream...
                                    </div>
                                </div>
                            ''').classes('w-full')

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

        # IMPORTANT: Start streaming AFTER UI is loaded
        ui.timer(3.0, self.start_streaming_deferred, once=True)

    def restart_stream(self):
        """Restart the video stream."""
        self.streamer.stop()
        time.sleep(1)
        self.streamer.start()
        time.sleep(3)  # Give more time for segments to generate

        # Debug check
        import os
        segments = [f for f in os.listdir("/tmp") if f.startswith("factorio_stream") and f.endswith('.ts')]
        if segments:
            for seg in segments[:2]:
                size = os.path.getsize(f"/tmp/{seg}")
                print(f"Segment {seg}: {size} bytes")

            # Check if first segment has actual video
            if segments and os.path.getsize(f"/tmp/{segments[0]}") < 1000:
                print("WARNING: Segments are too small - likely capturing black screen")
                print("The window might be on a different screen or coordinates are off")
        else:
            print("No segments created yet")

        ui.run_javascript('window.startStream && window.startStream()')

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
                'message': str(e),
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
        gym_env_unwrapped: FactorioGymEnv = gym_env.unwrapped
        task = gym_env_unwrapped.task
        instance = gym_env_unwrapped.instance

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
        """Update the fallback game view image."""
        if base64_image:
            ui.run_javascript(f'window.updateGameImage && window.updateGameImage("{base64_image}")')

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

    # Ensure cleanup on exit
    import atexit
    atexit.register(viewer.cleanup)

    ui.run(
        host=args.host,
        port=args.port,
        title='Factorio Learning Environment Viewer',
        favicon='🏭'
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()