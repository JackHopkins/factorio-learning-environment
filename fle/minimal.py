#!/usr/bin/env python3
"""
Minimal Factorio viewer for debugging streaming approaches.
Focuses on simplicity and easy iteration.
"""

import subprocess
import threading
import time
import os
import glob
from nicegui import ui
from pathlib import Path


class SimpleStreamer:
    """Dead simple screencapture-based streamer."""

    def __init__(self):
        self.is_streaming = False
        self.process = None
        self.display_number = 1  # Which display to capture (1=primary, 2=secondary)

    def start(self):
        """Start capturing and streaming."""
        if self.is_streaming:
            return False

        # Clean up old files
        for f in glob.glob('/tmp/stream*'):
            try:
                os.remove(f)
            except:
                pass

        self.is_streaming = True

        def capture_loop():
            """Simple capture loop using screencapture with temp files."""
            import tempfile
            frame_num = 0
            temp_dir = tempfile.mkdtemp(prefix='capture_')

            # Start FFmpeg to convert images to video
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'image2pipe',
                '-framerate', '10',  # Increased from 5 to 10 FPS
                '-i', '-',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-tune', 'zerolatency',  # Add zero latency tuning
                '-pix_fmt', 'yuv420p',
                '-g', '10',  # Keyframe every second at 10fps
                '-f', 'hls',
                '-hls_time', '1',  # Reduced from 2 to 1 second segments
                '-hls_list_size', '3',  # Reduced from 5 to 3 segments
                '-hls_flags', 'delete_segments+split_by_time',  # Better segment splitting
                '-hls_segment_filename', '/tmp/segment%03d.ts',
                '-flush_packets', '1',  # Flush packets immediately
                '-fflags', 'nobuffer+flush_packets',  # No buffering
                '-avioflags', 'direct',  # Direct I/O
                '-y',
                '/tmp/stream.m3u8'
            ]

            # Start with visible errors for debugging
            self.process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Monitor FFmpeg errors in background
            def monitor_ffmpeg():
                while self.is_streaming:
                    if self.process.stderr:
                        line = self.process.stderr.readline()
                        if line:
                            print(f"FFmpeg: {line.decode().strip()}")

            monitor_thread = threading.Thread(target=monitor_ffmpeg)
            monitor_thread.daemon = True
            monitor_thread.start()

            print(f"Started capture from display {self.display_number}")

            while self.is_streaming:
                try:
                    # Capture to temp file first
                    temp_file = f"{temp_dir}/frame_{frame_num:06d}.png"

                    capture_cmd = ['screencapture', '-x', '-C']
                    if self.display_number > 1:
                        capture_cmd.append(f'-D{self.display_number}')
                    capture_cmd.append(temp_file)

                    result = subprocess.run(capture_cmd, capture_output=True, timeout=1)

                    if result.returncode == 0 and os.path.exists(temp_file):
                        # Read and send to FFmpeg
                        with open(temp_file, 'rb') as f:
                            data = f.read()
                            if self.process.stdin and not self.process.stdin.closed:
                                self.process.stdin.write(data)
                                self.process.stdin.flush()
                                frame_num += 1

                                if frame_num % 25 == 0:
                                    print(f"Captured {frame_num} frames")
                                    # Check if HLS output exists
                                    if os.path.exists('/tmp/stream.m3u8'):
                                        segments = glob.glob('/tmp/segment*.ts')
                                        if segments:
                                            total_size = sum(os.path.getsize(f) for f in segments)
                                            print(f"HLS: {len(segments)} segments, {total_size:,} bytes")

                        # Clean up temp file
                        os.remove(temp_file)

                    time.sleep(0.1)  # 10 FPS

                except BrokenPipeError:
                    print("FFmpeg pipe broken")
                    break
                except Exception as e:
                    print(f"Capture error: {e}")
                    break

            # Cleanup
            if self.process:
                if self.process.stdin and not self.process.stdin.closed:
                    self.process.stdin.close()
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except:
                    self.process.kill()

            # Clean up temp dir
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

        # Start capture thread
        thread = threading.Thread(target=capture_loop)
        thread.daemon = True
        thread.start()

        return True

    def stop(self):
        """Stop streaming."""
        self.is_streaming = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            self.process = None

    def start_mjpeg(self):
        """Start MJPEG streaming for ultra-low latency."""
        if self.is_streaming:
            return False

        self.is_streaming = True
        self.stream_mode = 'mjpeg'

        def mjpeg_loop():
            import socket

            # Start simple MJPEG server
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('', 8083))
            server_socket.listen(1)
            server_socket.settimeout(0.5)

            print(f"MJPEG server listening on port 8083")
            clients = []

            frame_num = 0
            while self.is_streaming:
                # Accept new clients
                try:
                    client, addr = server_socket.accept()
                    client.sendall(b'HTTP/1.0 200 OK\r\n')
                    client.sendall(b'Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n')
                    clients.append(client)
                    print(f"MJPEG client connected from {addr}")
                except socket.timeout:
                    pass

                # Capture frame
                capture_cmd = ['screencapture', '-x', '-C', '-t', 'jpg']
                if self.display_number > 1:
                    capture_cmd.insert(3, f'-D{self.display_number}')
                capture_cmd.append('/tmp/frame.jpg')

                result = subprocess.run(capture_cmd, capture_output=True, timeout=0.5)

                if result.returncode == 0 and os.path.exists('/tmp/frame.jpg'):
                    with open('/tmp/frame.jpg', 'rb') as f:
                        frame_data = f.read()

                    # Send to all connected clients
                    for client in clients[:]:
                        try:
                            client.sendall(b'--frame\r\n')
                            client.sendall(
                                f'Content-Type: image/jpeg\r\nContent-Length: {len(frame_data)}\r\n\r\n'.encode())
                            client.sendall(frame_data)
                        except:
                            clients.remove(client)

                    frame_num += 1
                    if frame_num % 30 == 0:
                        print(f"MJPEG: Sent {frame_num} frames to {len(clients)} clients")

                time.sleep(0.033)  # 30 FPS for MJPEG

            # Cleanup
            server_socket.close()
            for client in clients:
                client.close()

        thread = threading.Thread(target=mjpeg_loop)
        thread.daemon = True
        thread.start()

        return True

    def switch_display(self, display_num):
        """Switch to a different display."""
        print(f"Switching from display {self.display_number} to {display_num}")
        self.display_number = display_num
        if self.is_streaming:
            self.stop()
            time.sleep(1)
            self.start()


class MinimalViewer:
    """Minimal viewer for testing."""

    def __init__(self):
        self.streamer = SimpleStreamer()
        self.current_frame = 0
        self.image_mode_active = False
        self.http_server = None

    def start_video_server(self):
        """Start HTTP server to serve video files."""
        import http.server
        import socketserver

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory='/tmp', **kwargs)

            def end_headers(self):
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache')
                super().end_headers()

            def log_message(self, format, *args):
                pass  # Suppress logs

        if not self.http_server:
            self.http_server = socketserver.TCPServer(('', 8081), Handler)
            thread = threading.Thread(target=self.http_server.serve_forever)
            thread.daemon = True
            thread.start()
            self.add_debug("Started video server on port 8081")

    def create_ui(self):
        """Create minimal UI."""

        with ui.header().classes('bg-blue-900 text-white p-4'):
            ui.label('Minimal Factorio Streamer Test').classes('text-2xl')

        with ui.column().classes('p-4'):
            # Controls
            with ui.card().classes('mb-4'):
                ui.label('Stream Controls').classes('text-lg font-bold mb-2')

                with ui.row():
                    ui.button('Start Stream', on_click=self.start_stream)
                    ui.button('Stop Stream', on_click=self.stop_stream)
                    ui.button('Test Capture', on_click=self._test_capture)

                ui.separator()

                ui.label('Display Selection')
                with ui.row():
                    ui.button('Display 1', on_click=lambda: self.streamer.switch_display(1))
                    ui.button('Display 2', on_click=lambda: self.streamer.switch_display(2))
                    ui.button('Display 3', on_click=lambda: self.streamer.switch_display(3))

                ui.separator()

                ui.label('Simple Image Mode (Fallback)')
                with ui.row():
                    ui.button('Start Image Updates', on_click=self.start_image_mode)
                    ui.button('Stop Image Updates', on_click=self.stop_image_mode)

                self.status = ui.label('Status: Ready')

            # Video display
            with ui.card():
                ui.label('Video Output').classes('text-lg font-bold mb-2')

                # Simple video element
                self.video_html = ui.html('''
                    <div style="width: 100%; height: 500px; background: #000; position: relative;">
                        <video id="video" style="width: 100%; height: 100%;" controls autoplay muted>
                            Your browser does not support video
                        </video>
                        <div style="position: absolute; top: 10px; left: 10px; color: white; background: rgba(0,0,0,0.5); padding: 5px;">
                            <span id="video-status">No stream</span>
                        </div>
                    </div>
                ''')

                # Alternative: Image display for debugging
                self.image = ui.image('').classes('w-full h-96 object-contain bg-black')
                self.image.set_source(
                    'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')

            # Debug info
            with ui.card().classes('mt-4'):
                ui.label('Debug Info').classes('text-lg font-bold mb-2')
                self.debug_text = ui.textarea('Debug output will appear here...').props('readonly rows=10').classes(
                    'w-full font-mono text-xs')

        # Update timer
        ui.timer(1.0, self.update_status)

    def start_stream(self):
        """Start streaming."""
        self.add_debug("Starting stream...")

        # Start HTTP server first
        self.start_video_server()

        if self.streamer.start():
            self.status.set_text('Status: Streaming')
            self.add_debug("Stream started successfully")

            # Update video source after a delay
            ui.timer(3.0, self.update_video_source, once=True)
        else:
            self.add_debug("Failed to start stream")

    def start_mjpeg_stream(self):
        """Start ultra-low latency MJPEG streaming."""
        self.add_debug("Starting MJPEG stream (ultra-low latency)...")

        if self.streamer.start_mjpeg():
            self.status.set_text('Status: MJPEG Streaming')
            self.add_debug("MJPEG stream started on port 8083")

            # Set video source to MJPEG
            ui.timer(1.0, self.set_mjpeg_source, once=True)
        else:
            self.add_debug("Failed to start MJPEG stream")

    def set_mjpeg_source(self):
        """Set video element to MJPEG stream."""
        self.add_debug("Connecting to MJPEG stream...")
        ui.run_javascript('''
            var video = document.getElementById('video');
            if (video) {
                // For MJPEG, we use an img tag instead of video
                var container = video.parentElement;
                container.innerHTML = '<img id="mjpeg" src="http://localhost:8083" style="width: 100%; height: 100%;" />';
                document.getElementById('video-status').textContent = 'MJPEG Stream (< 500ms latency)';
            }
        ''')

    def stop_stream(self):
        """Stop streaming."""
        self.add_debug("Stopping stream...")
        self.streamer.stop()
        self.status.set_text('Status: Stopped')

    def _test_capture(self):
        """Test a single capture."""
        self.add_debug("Testing capture...")

        # Try to capture a single frame
        cmd = ['screencapture', '-x', '-C']
        if self.streamer.display_number > 1:
            cmd.append(f'-D{self.streamer.display_number}')
        cmd.extend(['/tmp/test.png'])

        result = subprocess.run(cmd, capture_output=True)

        if result.returncode == 0 and os.path.exists('/tmp/test.png'):
            size = os.path.getsize('/tmp/test.png')
            self.add_debug(f"✓ Captured test.png ({size:,} bytes) from display {self.streamer.display_number}")

            # Show the captured image
            with open('/tmp/test.png', 'rb') as f:
                import base64
                data = base64.b64encode(f.read()).decode()
                self.image.set_source(f'data:image/png;base64,{data}')

            # Also test if FFmpeg can read this image
            test_cmd = [
                'ffmpeg', '-i', '/tmp/test.png',
                '-c:v', 'libx264', '-y', '/tmp/test.mp4'
            ]
            result = subprocess.run(test_cmd, capture_output=True)
            if result.returncode == 0:
                self.add_debug("✓ FFmpeg can encode captured images")
            else:
                self.add_debug(f"✗ FFmpeg encoding failed: {result.stderr.decode()[:200]}")
        else:
            self.add_debug(f"✗ Capture failed: {result.stderr.decode() if result.stderr else 'Unknown error'}")

    def update_video_source(self):
        """Update video element source."""
        if os.path.exists('/tmp/stream.m3u8'):
            # Check if segments exist
            segments = glob.glob('/tmp/segment*.ts')
            if segments:
                self.add_debug(f"HLS playlist ready with {len(segments)} segments")

                # Use HLS.js for playback
                ui.run_javascript('''
                    // Load HLS.js if not already loaded
                    if (!window.Hls) {
                        var script = document.createElement('script');
                        script.src = 'https://cdn.jsdelivr.net/npm/hls.js@latest';
                        script.onload = function() {
                            startHLS();
                        };
                        document.head.appendChild(script);
                    } else {
                        startHLS();
                    }

                    function startHLS() {
                        var video = document.getElementById('video');
                        var videoSrc = 'http://localhost:8081/stream.m3u8';

                        if (Hls.isSupported()) {
                            var hls = new Hls({
                                debug: false,
                                lowLatencyMode: true,
                                backBufferLength: 0,  // No back buffer
                                maxBufferLength: 1,  // Minimum buffer (1 second)
                                maxMaxBufferLength: 2,  // Max 2 seconds
                                liveSyncDurationCount: 1,  // Stay close to live edge
                                liveMaxLatencyDurationCount: 3,  // Max 3 segments behind
                                liveDurationInfinity: true,
                                highBufferWatchdogPeriod: 1,
                                nudgeMaxRetry: 5,
                                maxFragLookUpTolerance: 0.1,
                                startFragPrefetch: true,
                                testBandwidth: false,  // Skip bandwidth test
                                startLevel: -1,
                                fragLoadingTimeOut: 2000,
                                fragLoadingMaxRetry: 1,
                                progressive: true
                            });
                            hls.loadSource(videoSrc);
                            hls.attachMedia(video);
                            hls.on(Hls.Events.MANIFEST_PARSED, function() {
                                video.play();
                                document.getElementById('video-status').textContent = 'Low-latency HLS playing';
                            });
                            hls.on(Hls.Events.ERROR, function(event, data) {
                                if (data.fatal) {
                                    document.getElementById('video-status').textContent = 'HLS Error: ' + data.type;
                                }
                            });
                        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                            // Native HLS support (Safari)
                            video.src = videoSrc;
                            video.play();
                            document.getElementById('video-status').textContent = 'Native HLS playing';
                        } else {
                            document.getElementById('video-status').textContent = 'HLS not supported';
                        }
                    }
                ''')
            else:
                self.add_debug("Waiting for segments...")
                # Try again in a moment
                ui.timer(2.0, self.update_video_source, once=True)
        else:
            self.add_debug("HLS playlist not found yet...")
            # Try again
            ui.timer(2.0, self.update_video_source, once=True)

    def update_status(self):
        """Update status display."""
        if self.streamer.is_streaming:
            # Check HLS files
            if os.path.exists('/tmp/stream.m3u8'):
                segments = glob.glob('/tmp/segment*.ts')
                if segments:
                    total_size = sum(os.path.getsize(f) for f in segments)
                    self.status.set_text(f'Status: Streaming ({len(segments)} segments, {total_size:,} bytes)')

    def add_debug(self, message):
        """Add debug message."""
        timestamp = time.strftime('%H:%M:%S')
        current = self.debug_text.value
        self.debug_text.set_value(f"{current}\n[{timestamp}] {message}".strip())

    def start_image_mode(self):
        """Simple mode that just updates images rapidly."""
        self.image_mode_active = True
        self.add_debug("Starting image update mode...")

        def update_loop():
            frame = 0
            while self.image_mode_active:
                try:
                    # Capture to temp file
                    cmd = ['screencapture', '-x', '-C']
                    if self.streamer.display_number > 1:
                        cmd.append(f'-D{self.streamer.display_number}')
                    cmd.append('/tmp/live.png')

                    result = subprocess.run(cmd, capture_output=True, timeout=1)

                    if result.returncode == 0 and os.path.exists('/tmp/live.png'):
                        # Update image
                        with open('/tmp/live.png', 'rb') as f:
                            import base64
                            data = base64.b64encode(f.read()).decode()
                            # Use JavaScript to update image to avoid flickering
                            ui.run_javascript(f'''
                                var img = document.querySelector('img.nicegui-image');
                                if (img) {{
                                    img.src = 'data:image/png;base64,{data}';
                                }}
                            ''')

                        frame += 1
                        if frame % 10 == 0:
                            self.status.set_text(f'Image Mode: {frame} frames')

                    time.sleep(0.5)  # 2 FPS for image mode

                except Exception as e:
                    print(f"Image update error: {e}")
                    break

        thread = threading.Thread(target=update_loop)
        thread.daemon = True
        thread.start()

    def stop_image_mode(self):
        """Stop image update mode."""
        self.image_mode_active = False
        self.add_debug("Stopped image update mode")
        self.status.set_text('Status: Ready')


def _test_ffmpeg_screen_capture():
    """Test if FFmpeg screen capture works at all."""
    print("\n=== Testing FFmpeg Screen Capture ===")

    # List devices
    print("Available devices:")
    result = subprocess.run(
        ['ffmpeg', '-f', 'avfoundation', '-list_devices', 'true', '-i', ''],
        capture_output=True,
        text=True
    )

    for line in result.stderr.split('\n'):
        if 'AVFoundation video devices' in line or '[' in line:
            print(line)

    # Try to capture from each screen device
    for device in ['2', '3', '4']:
        print(f"\nTesting device {device}...")
        result = subprocess.run(
            ['ffmpeg', '-f', 'avfoundation', '-i', device, '-vframes', '1', '-y', f'test_{device}.jpg'],
            capture_output=True,
            timeout=3
        )

        if result.returncode == 0:
            print(f"✓ Device {device} works")
        else:
            print(f"✗ Device {device} failed")


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Test FFmpeg capture')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()

    if args.test:
        _test_ffmpeg_screen_capture()
        return

    # Create and run viewer
    viewer = MinimalViewer()

    @ui.page('/')
    def index():
        viewer.create_ui()

    print("Starting minimal viewer on http://localhost:8080")
    print("Click 'Test Capture' to test single frame capture")
    print("Click 'Display 1/2/3' to switch monitors")
    print("Click 'Start Stream' to begin streaming")

    ui.run(port=args.port, title='Minimal Factorio Viewer')


if __name__ in {"__main__", "__mp_main__"}:
    main()