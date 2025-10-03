"""
Rollout to Videos - A class-based system for generating videos from Factorio program rollouts.

This module replicates the functionality of continuous_runtime_to_cinema.py but uses
the new CinematicInstance class for cleaner, more maintainable code.

Key features:
- Class-based architecture for better organization
- Integration with CinematicInstance for automatic cutscene generation
- Database-driven program retrieval and processing
- Automatic video rendering with configurable settings
- Clean file management and output organization
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from dotenv import load_dotenv

from fle.eval.analysis.cinematic_instance import (
    CinematicInstance,
    create_cinematic_instance,
)
from fle.eval.analysis.subtitle_tracker import SubtitleTracker
from fle.commons.models.program import Program
from fle.commons.cluster_ips import get_local_container_ips

load_dotenv()


class GracefulExitHandler:
    """Handles graceful exit on SIGINT (Ctrl+C) signals."""

    def __init__(self):
        self.interrupt_count = 0
        self.max_interrupts = 2
        self.should_exit = False
        self.exit_reason = None

    def signal_handler(self, signum, frame):
        """Handle SIGINT signals."""
        self.interrupt_count += 1

        if self.interrupt_count == 1:
            print(f"\n{'=' * 60}")
            print("INTERRUPT RECEIVED - Preparing for graceful exit...")
            print("Press Ctrl+C again to force exit immediately")
            print(f"{'=' * 60}")
            self.should_exit = True
            self.exit_reason = "graceful_exit"
        else:
            print(f"\n{'=' * 60}")
            print("FORCE EXIT REQUESTED - Exiting immediately!")
            print(f"{'=' * 60}")
            self.exit_reason = "force_exit"
            sys.exit(1)

    def register(self):
        """Register the signal handler."""
        signal.signal(signal.SIGINT, self.signal_handler)

    def reset(self):
        """Reset the interrupt count."""
        self.interrupt_count = 0
        self.should_exit = False
        self.exit_reason = None


@dataclass
class ProcessingConfig:
    """Configuration for video processing."""

    output_dir: str = "rollout_videos"
    max_steps: int = 1000
    address: str = "localhost"
    tcp_port: int = 27000
    capture_enabled: bool = True
    script_output_dir: Optional[str] = None
    render_enabled: bool = True
    render_fps: int = 24
    render_crf: int = (
        28  # Lower CRF = better quality (18-28 is good range, 28 for smaller files)
    )
    render_preset: str = "slow"  # "slow" provides better compression than "ultrafast"
    speed: float = 4.0
    target_max_bitrate: str = "2M"  # Max bitrate for size control
    target_buffer_size: str = "4M"  # Buffer size (2x max bitrate)
    cleanup_after: bool = True
    debug: bool = False  # If True, raise exceptions instead of continuing
    subtitles_enabled: bool = True  # Generate WebVTT subtitle files
    linger_seconds: float = 3.0  # How long to linger on final relevant entity
    max_steps_explicit: bool = False  # Whether max_steps was explicitly set by user


@dataclass
class ProgramData:
    """Data structure for a single program."""

    program_id: int
    created_at: datetime
    code: str
    state: Optional[Dict[str, Any]] = None
    actions: List[Dict[str, Any]] = field(default_factory=list)
    execution_result: Optional[Tuple[Any, Any, Any]] = None  # (result, prints, errors)
    shots_generated: int = 0
    processing_time: float = 0.0


@dataclass
class ProcessingReport:
    """Report of the processing session."""

    version: int
    programs_processed: int = 0
    total_actions: int = 0
    total_shots: int = 0
    total_frames: int = 0
    processing_time: float = 0.0
    programs: List[ProgramData] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    output_directory: Optional[str] = None


class DatabaseManager:
    """Manages database connections and queries."""

    def __init__(self):
        self.conn = None

    def connect(self) -> None:
        """Establish database connection."""
        self.conn = psycopg2.connect(
            host=os.getenv("SKILLS_DB_HOST"),
            port=os.getenv("SKILLS_DB_PORT"),
            dbname=os.getenv("SKILLS_DB_NAME"),
            user=os.getenv("SKILLS_DB_USER"),
            password=os.getenv("SKILLS_DB_PASSWORD"),
        )

    def get_program_chain(
        self, version: int, limit: int = 3000
    ) -> List[Tuple[int, datetime]]:
        """Get all programs for a specific version ordered by time."""
        query = """
        SELECT id, created_at FROM programs
        WHERE version = %s
        AND state_json IS NOT NULL
        ORDER BY created_at ASC
        LIMIT %s
        """

        with self.conn.cursor() as cur:
            cur.execute(query, (version, limit))
            return cur.fetchall()

    def get_program_state(self, program_id: int) -> Optional[Program]:
        """Fetch a single program's full state by ID."""
        query = """
        SELECT * FROM programs WHERE id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (program_id,))
            row = cur.fetchone()
            if not row:
                return None

            col_names = [desc[0] for desc in cur.description]
            return Program.from_row(dict(zip(col_names, row)))

    def get_task_info(self, version: int) -> Optional[str]:
        """Get task information from the first program's metadata."""
        query = """
        SELECT meta, version_description FROM programs
        WHERE version = %s
        AND meta IS NOT NULL
        ORDER BY created_at ASC
        LIMIT 1
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (version,))
            row = cur.fetchone()
            if not row:
                return None

            meta, version_description = row

            # Try to extract task from version_description (same as run_to_mp4.py)
            if version_description and "type:" in version_description:
                try:
                    task_key = (
                        version_description.split("type:")[1].split("\n")[0].strip()
                    )
                    return task_key
                except (IndexError, AttributeError):
                    pass

            # Fallback to meta if available
            if meta and isinstance(meta, dict):
                return meta.get("task")

            return None

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()


class VideoRenderer:
    """Handles video rendering from PNG frames."""

    def __init__(self, config: ProcessingConfig):
        self.config = config

    def render_video(self, frames_dir: Path, output_dir: Path) -> Dict[str, Any]:
        """Render video from PNG frames using ffmpeg."""
        if not frames_dir.exists():
            return {
                "ok": False,
                "error": f"Frames directory {frames_dir} does not exist",
            }

        # Count PNG files
        png_files = list(frames_dir.glob("*.png"))
        if not png_files:
            return {"ok": False, "error": "No PNG files found in frames directory"}

        # Create videos output directory
        videos_dir = output_dir / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)

        # Generate output video path
        output_video = videos_dir / f"{output_dir.name}.mp4"

        # Build ffmpeg command with speed control using setpts filter
        # This correctly speeds up the video by manipulating presentation timestamps
        input_fps = self.config.render_fps
        speed_multiplier = self.config.speed

        # setpts filter: smaller values = faster video
        # For 4x speed: setpts=0.25*PTS (because 1/4 = 0.25)
        setpts_value = 1.0 / speed_multiplier

        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output files
            "-framerate",
            str(input_fps),  # Input framerate (actual capture rate)
            "-pattern_type",
            "glob",
            "-i",
            str(frames_dir / "*.png"),
            "-vf",
            f"setpts={setpts_value}*PTS,scale=1280:720",  # Speed up + downscale to 720p for smaller size
            "-c:v",
            "libx264",  # H.264 video codec
            "-profile:v",
            "main",  # "main" profile for better compatibility and smaller size
            "-level",
            "4.0",  # H.264 level
            "-crf",
            str(self.config.render_crf),
            "-maxrate",
            self.config.target_max_bitrate,  # Maximum bitrate
            "-bufsize",
            self.config.target_buffer_size,  # Buffer size for rate control
            "-preset",
            self.config.render_preset,
            "-pix_fmt",
            "yuv420p",  # Pixel format for compatibility
            "-movflags",
            "+faststart",  # Optimize for web streaming (move moov atom to start)
            "-f",
            "mp4",  # Force MP4 container format
            str(output_video),
        ]

        try:
            print(f"Rendering video: {output_video}")
            print(f"Input FPS: {input_fps} (capture rate)")
            print(f"Speed multiplier: {speed_multiplier}x (setpts={setpts_value})")
            print(f"Command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                return {
                    "ok": True,
                    "output": str(output_video),
                    "command": " ".join(cmd),
                    "frames_processed": len(png_files),
                }
            else:
                return {
                    "ok": False,
                    "error": f"ffmpeg failed with return code {result.returncode}",
                    "stderr": result.stderr,
                    "command": " ".join(cmd),
                }

        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": "ffmpeg timed out after 5 minutes",
                "command": " ".join(cmd),
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"ffmpeg execution failed: {e}",
                "command": " ".join(cmd),
            }


class FileManager:
    """Manages file operations and directory structure."""

    def __init__(self, config: ProcessingConfig):
        self.config = config

    def setup_output_directory(self, version: int) -> Path:
        """Set up the output directory structure for a version."""
        output_base = Path(self.config.output_dir)
        version_dir = output_base / str(version)

        # Clean existing directory if it exists
        if version_dir.exists():
            try:
                shutil.rmtree(version_dir)
                print(f"Cleaned existing output directory: {version_dir}")
            except Exception as e:
                print(f"Warning: Failed to clean output directory {version_dir}: {e}")
                # If rmtree fails, try to at least clean the frames directory
                frames_dir = version_dir / "frames"
                if frames_dir.exists():
                    try:
                        for png_file in frames_dir.glob("*.png"):
                            png_file.unlink()
                        print(f"Cleaned PNG files from {frames_dir}")
                    except Exception as e2:
                        print(f"Warning: Failed to clean PNG files: {e2}")

        # Create directory structure
        version_dir.mkdir(parents=True, exist_ok=True)
        (version_dir / "frames").mkdir(exist_ok=True)
        (version_dir / "videos").mkdir(exist_ok=True)

        return version_dir

    def setup_capture_directory(self, version: int) -> Path:
        """Set up the capture directory for screenshots."""
        if not self.config.script_output_dir:
            # Use default Factorio script-output path
            script_output = (
                Path.home()
                / "Library"
                / "Application Support"
                / "factorio"
                / "script-output"
            )
        else:
            script_output = Path(self.config.script_output_dir)

        capture_dir = script_output / f"v{version}"

        # Clean existing capture directory
        if capture_dir.exists():
            try:
                shutil.rmtree(capture_dir)
                print(f"Cleaned existing capture directory: {capture_dir}")
            except Exception as e:
                print(f"Warning: Failed to clean capture directory {capture_dir}: {e}")

        capture_dir.mkdir(parents=True, exist_ok=True)
        return capture_dir

    def move_frames_to_output(
        self, capture_dir: Path, output_dir: Path
    ) -> Dict[str, Any]:
        """Move captured frames from script-output to output directory."""
        frames_dir = output_dir / "frames"

        if not capture_dir.exists():
            return {
                "moved": 0,
                "error": f"Capture directory {capture_dir} does not exist",
            }

        # Sort files by name to ensure chronological order (filenames are zero-padded tick+frame)
        src_files = sorted(capture_dir.glob("*.png"))
        if not src_files:
            return {"moved": 0, "error": "No PNG files found in capture directory"}

        try:
            # Move files
            moved_count = 0
            for src_file in src_files:
                dst_file = frames_dir / src_file.name
                # Overwrite if destination exists (shouldn't happen with proper cleanup)
                if dst_file.exists():
                    dst_file.unlink()
                shutil.move(str(src_file), str(dst_file))
                moved_count += 1

            # Aggressively clean capture directory
            try:
                # Remove any remaining files (non-PNG)
                for remaining_file in capture_dir.iterdir():
                    try:
                        remaining_file.unlink()
                    except Exception:
                        pass
                capture_dir.rmdir()
                print(f"Cleaned up capture directory: {capture_dir}")
            except OSError as e:
                print(f"Warning: Could not fully clean capture directory: {e}")

            return {
                "moved": moved_count,
                "source_dir": str(capture_dir),
                "destination_dir": str(frames_dir),
            }

        except Exception as e:
            return {
                "moved": 0,
                "error": f"Failed to move frames: {e}",
                "source_dir": str(capture_dir),
                "destination_dir": str(frames_dir),
            }


class RolloutToVideos:
    """
    Main class for processing Factorio program rollouts into videos.

    This class orchestrates the entire process:
    1. Database connection and program retrieval
    2. CinematicInstance creation and configuration
    3. Program execution with automatic cutscene generation
    4. File management and video rendering
    5. Cleanup and reporting
    """

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.db_manager = DatabaseManager()
        self.file_manager = FileManager(config)
        self.video_renderer = VideoRenderer(config)
        self.cinematic_instance: Optional[CinematicInstance] = None
        self.subtitle_tracker: Optional[SubtitleTracker] = None
        self.report: Optional[ProcessingReport] = None
        self.exit_handler = GracefulExitHandler()
        self.current_output_dir: Optional[Path] = None
        self.current_capture_dir: Optional[Path] = None
        self.task_throughput_item: Optional[str] = None

    def process_version(self, version: int) -> ProcessingReport:
        """Process a single version and generate videos."""
        print(f"\n{'=' * 60}")
        print(f"Processing version {version}")
        if self.config.debug:
            print("DEBUG MODE ENABLED - Will raise exceptions instead of continuing")
        print(f"{'=' * 60}")

        start_time = time.time()

        # Register signal handler for graceful exit
        self.exit_handler.register()

        # Initialize report
        self.report = ProcessingReport(version=version)

        try:
            # Setup directories
            output_dir = self.file_manager.setup_output_directory(version)
            capture_dir = self.file_manager.setup_capture_directory(version)
            self.report.output_directory = str(output_dir)
            self.current_output_dir = output_dir
            self.current_capture_dir = capture_dir

            # Connect to database
            self.db_manager.connect()

            # Get task info for lingering at end
            task_key = self.db_manager.get_task_info(version)
            if task_key:
                print(f"Detected task: {task_key}")
                self.task_throughput_item = self._extract_throughput_item(task_key)
                if self.task_throughput_item:
                    print(f"Target throughput item: {self.task_throughput_item}")

            # Get program chain
            programs = self.db_manager.get_program_chain(version, self.config.max_steps)
            if not programs:
                print(f"No programs found for version {version}")
                return self.report

            print(f"Found {len(programs)} programs to process")

            # Create cinematic instance
            self._create_cinematic_instance()

            # Process programs
            self._process_programs(programs, capture_dir)

            # Handle graceful exit if requested
            if self.exit_handler.should_exit:
                self._handle_graceful_exit()
            else:
                # Move frames and render video normally
                self._finalize_video_generation(output_dir, capture_dir)

            # Generate final report
            self.report.processing_time = time.time() - start_time
            self._save_report(output_dir)

            # Update report with exit reason
            if self.exit_handler.exit_reason:
                self.report.errors.append(
                    f"Exit reason: {self.exit_handler.exit_reason}"
                )

            print(f"\nProcessing complete for version {version}")
            print(f"Total time: {self.report.processing_time:.2f} seconds")
            print(f"Programs processed: {self.report.programs_processed}")
            print(f"Total shots: {self.report.total_shots}")
            print(f"Total frames: {self.report.total_frames}")
            print(f"Output directory: {output_dir}")

            if self.exit_handler.exit_reason:
                print(f"Exit reason: {self.exit_handler.exit_reason}")

        except Exception as e:
            error_msg = f"Error processing version {version}: {e}"
            print(error_msg)
            self.report.errors.append(error_msg)
            if self.config.debug:
                raise  # Always re-raise in debug mode
            raise  # Always re-raise for top-level version processing errors

        finally:
            self._cleanup()

        return self.report

    def _create_cinematic_instance(self) -> None:
        """Create and configure the cinematic instance."""
        print("Creating cinematic instance...")

        # Get container IPs
        ips, udp_ports, tcp_ports = get_local_container_ips()

        # Create instance
        self.cinematic_instance = create_cinematic_instance(
            address=ips[-1],  # Use last instance
            tcp_port=tcp_ports[-1],
            fast=True,
            cache_scripts=True,
            inventory={},
            all_technologies_researched=False,
        )

        # Enable admin tools for cutscene functionality
        self.cinematic_instance.first_namespace.enable_admin_tools_in_runtime(True)

        # Register cinematic hooks for automatic camera positioning
        self.cinematic_instance.register_cinematic_hooks()

        # Initialize subtitle tracker if enabled
        if self.config.subtitles_enabled:
            self.subtitle_tracker = SubtitleTracker(
                self.cinematic_instance, speed=self.config.speed
            )
            self.subtitle_tracker.register_hooks()
            print("Subtitle tracking enabled")

        # Configure capture settings
        if self.config.capture_enabled:
            self.cinematic_instance.capture_enabled = True
            self.cinematic_instance.capture_dir = f"v{self.report.version}"

        print("Cinematic instance created and configured with hooks")

    def _process_programs(
        self, programs: List[Tuple[int, datetime]], capture_dir: Path
    ) -> None:
        """Process all programs for the version."""
        run_slug = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Start recording when first program begins
        if self.config.capture_enabled and self.cinematic_instance.cutscene:
            print("Starting continuous screenshot recording...")
            try:
                result = self.cinematic_instance.cutscene.start_recording(
                    player=1,
                    session_id=f"v{self.report.version}",
                    capture_dir=f"v{self.report.version}",
                )
                if result.get("ok"):
                    print(
                        f"Continuous recording started: session {result.get('session_id')}"
                    )
                else:
                    print(f"Warning: Failed to start recording: {result.get('error')}")
            except Exception as e:
                print(f"Error starting recording: {e}")
                if self.config.debug:
                    raise

        for idx, (program_id, created_at) in enumerate(programs):
            # Check for graceful exit
            if self.exit_handler.should_exit:
                print(f"\n{'=' * 60}")
                print("GRACEFUL EXIT REQUESTED - Stopping program processing")
                print(f"{'=' * 60}")
                break

            if self.report.programs_processed >= self.config.max_steps:
                print(
                    f"Reached maximum steps limit ({self.config.max_steps}), stopping"
                )
                break

            print(
                f"\n--- Processing program {self.report.programs_processed + 1}/{len(programs)}: {program_id} ---"
            )

            try:
                program_data = self._process_single_program(
                    program_id, created_at, run_slug
                )
                self.report.programs.append(program_data)
                self.report.programs_processed += 1
                # Note: actions/shots are handled transparently by hooks
                self.report.total_actions += (
                    0  # Not tracking individual actions anymore
                )
                self.report.total_shots += 0  # Shots happen automatically via hooks

            except Exception as e:
                error_msg = f"Error processing program {program_id}: {e}"
                print(error_msg)
                self.report.errors.append(error_msg)
                if self.config.debug:
                    raise  # Re-raise in debug mode
                continue

            # Small delay between programs
            time.sleep(0.5)

    def _process_single_program(
        self, program_id: int, created_at: datetime, run_slug: str
    ) -> ProgramData:
        """Process a single program."""
        start_time = time.time()

        # Get program from database
        program = self.db_manager.get_program_state(program_id)
        if not program or not program.code:
            raise ValueError(f"No code available for program {program_id}")

        print(f"Code preview: {program.code[:100]}...")

        # Create program data
        program_data = ProgramData(
            program_id=program_id,
            created_at=created_at,
            code=program.code,
            state=program.state,
        )

        # Pause recording during state reset to avoid capturing reset frames
        if (
            program.state
            and self.config.capture_enabled
            and self.cinematic_instance.cutscene
        ):
            print("Pausing recording for environment reset...")
            pause_result = self.cinematic_instance.cutscene.pause_recording()
            if not pause_result.get("ok"):
                print(
                    f"Warning: Failed to pause recording: {pause_result.get('error')}"
                )

        # Reset environment if state available
        if program.state:
            # Mark reset for subtitle tracker BEFORE resetting (captures current tick)
            if self.subtitle_tracker:
                self.subtitle_tracker.mark_reset()

            print("Resetting environment with program state")
            self.cinematic_instance.reset(program.state)

        # Notify subtitle tracker of program start AFTER reset
        if self.subtitle_tracker:
            self.subtitle_tracker.start_program(program_id, code_preview=program.code)

        # Resume recording before program execution
        if (
            program.state
            and self.config.capture_enabled
            and self.cinematic_instance.cutscene
        ):
            print("Resuming recording for program execution...")
            resume_result = self.cinematic_instance.cutscene.resume_recording()
            if not resume_result.get("ok"):
                print(
                    f"Warning: Failed to resume recording: {resume_result.get('error')}"
                )

        # Execute program - hooks will automatically position camera before each action
        print("Executing program (hooks will handle camera positioning)...")
        execution_result = self.cinematic_instance.eval(program.code)
        program_data.execution_result = execution_result

        # Log execution results
        if execution_result[2]:  # errors
            print(f"Execution errors: {execution_result[2]}")
        if execution_result[1]:  # prints
            print(f"Program output: {execution_result[1]}")

        # Mark program end for subtitle tracker
        if self.subtitle_tracker:
            self.subtitle_tracker.end_program()

        # No need to generate shots - hooks did it automatically during execution
        program_data.shots_generated = 0  # Hooks handle this transparently

        program_data.processing_time = time.time() - start_time
        print(
            f"Program {program_id} processed in {program_data.processing_time:.2f} seconds"
        )

        return program_data

    def _finalize_video_generation(self, output_dir: Path, capture_dir: Path) -> None:
        """Move frames and render final video."""
        print("\nFinalizing video generation...")

        # Linger on relevant entity if conditions are met
        should_linger = (
            not self.config.max_steps_explicit
            and self.task_throughput_item
            and self.config.linger_seconds > 0
            and self.cinematic_instance
        )

        if should_linger:
            print(
                f"\nLingering on relevant entity for {self.config.linger_seconds}s..."
            )
            try:
                self._linger_on_relevant_entity()
            except Exception as e:
                print(f"Warning: Failed to linger on entity: {e}")
                if self.config.debug:
                    raise

        # Move frames from capture directory to output directory
        move_result = self.file_manager.move_frames_to_output(capture_dir, output_dir)
        if move_result.get("error"):
            print(f"Warning: {move_result['error']}")
        else:
            print(f"Moved {move_result['moved']} frames to output directory")
            self.report.total_frames = move_result["moved"]

        # Render video if enabled and we have enough frames
        if self.config.render_enabled and self.report.total_frames > 0:
            self._render_video_from_frames(output_dir)
        else:
            print("Video rendering disabled or no frames available")

        # Generate subtitle file if enabled
        if self.subtitle_tracker and self.report.total_frames > 0:
            self._generate_subtitle_file(output_dir)

    def _render_video_from_frames(self, output_dir: Path) -> None:
        """Render video from existing frames."""
        frames_dir = output_dir / "frames"

        if not frames_dir.exists():
            print("No frames directory found for video rendering")
            return

        # Count existing frames
        existing_frames = list(frames_dir.glob("*.png"))
        frame_count = len(existing_frames)

        if frame_count == 0:
            print("No PNG frames found for video rendering")
            return

        print(f"Found {frame_count} frames for video rendering")

        # Check if we have enough frames for a meaningful video
        min_frames_for_video = 10  # Minimum frames to create a video
        if frame_count < min_frames_for_video:
            print(
                f"Only {frame_count} frames available (minimum {min_frames_for_video} required)"
            )
            print("Skipping video rendering")
            return

        # Render video
        render_result = self.video_renderer.render_video(frames_dir, output_dir)

        if render_result.get("ok"):
            print(f"Video rendered successfully: {render_result['output']}")
            print(
                f"Processed {render_result.get('frames_processed', frame_count)} frames"
            )
        else:
            error_msg = f"Video rendering failed: {render_result.get('error')}"
            print(error_msg)
            self.report.errors.append(error_msg)

    def _generate_subtitle_file(self, output_dir: Path) -> None:
        """Generate WebVTT subtitle file for the video."""
        try:
            subtitle_path = output_dir / "videos" / f"{output_dir.name}.vtt"
            self.subtitle_tracker.generate_webvtt(subtitle_path)

            # Get and log statistics
            stats = self.subtitle_tracker.get_statistics()
            print("Subtitle statistics:")
            print(f"  Total events: {stats['total_events']}")
            print(f"  Tool counts: {stats.get('tool_counts', {})}")

        except Exception as e:
            error_msg = f"Failed to generate subtitles: {e}"
            print(error_msg)
            self.report.errors.append(error_msg)
            if self.config.debug:
                raise

    def _handle_graceful_exit(self) -> None:
        """Handle graceful exit by creating video from existing frames."""
        if not self.exit_handler.should_exit:
            return

        print(f"\n{'=' * 60}")
        print("HANDLING GRACEFUL EXIT")
        print(f"{'=' * 60}")

        if self.current_output_dir and self.current_capture_dir:
            print("Attempting to create video from existing frames...")

            # Stop any active recording first
            if self.cinematic_instance and self.cinematic_instance.cutscene:
                try:
                    self.cinematic_instance.cutscene.stop_recording()
                    print("Stopped active recording session")
                except Exception as e:
                    print(f"Warning: Could not stop recording: {e}")

            # Try to move any existing frames
            try:
                move_result = self.file_manager.move_frames_to_output(
                    self.current_capture_dir, self.current_output_dir
                )

                if move_result.get("moved", 0) > 0:
                    print(f"Moved {move_result['moved']} frames during graceful exit")
                    self.report.total_frames = move_result["moved"]

                    # Try to render video from existing frames
                    self._render_video_from_frames(self.current_output_dir)

                    # Try to generate subtitles from captured events
                    if self.subtitle_tracker:
                        self._generate_subtitle_file(self.current_output_dir)
                else:
                    print("No frames available for video creation")

            except Exception as e:
                print(f"Error during graceful exit video creation: {e}")
                self.report.errors.append(f"Graceful exit error: {e}")
                if self.config.debug:
                    raise  # Re-raise in debug mode

        print("Graceful exit completed")

    def _save_report(self, output_dir: Path) -> None:
        """Save processing report to output directory."""
        report_data = {
            "version": self.report.version,
            "programs_processed": self.report.programs_processed,
            "total_actions": self.report.total_actions,
            "total_shots": self.report.total_shots,
            "total_frames": self.report.total_frames,
            "processing_time": self.report.processing_time,
            "output_directory": self.report.output_directory,
            "errors": self.report.errors,
            "programs": [
                {
                    "program_id": p.program_id,
                    "created_at": p.created_at.isoformat(),
                    "code": p.code,
                    "shots_generated": p.shots_generated,
                    "processing_time": p.processing_time,
                }
                for p in self.report.programs
            ],
        }

        report_file = output_dir / "processing_report.json"
        with report_file.open("w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        print(f"Processing report saved to: {report_file}")

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self.cinematic_instance:
            try:
                # Stop recording - cinematic_instance.cleanup() also does this,
                # but we do it here first with explicit error handling
                if self.cinematic_instance.cutscene:
                    try:
                        result = self.cinematic_instance.cutscene.stop_recording()
                        if result.get("ok"):
                            print(f"Recording stopped: {result.get('session_id')}")
                    except Exception as e:
                        print(f"Warning: Could not stop recording: {e}")

                # Give server a moment to process the stop command before full cleanup
                time.sleep(0.5)

                # Let parent cleanup handle everything else
                # Admin tools don't need to be disabled - we're shutting down anyway
                self.cinematic_instance.cleanup()
                print("Cinematic instance cleaned up")
            except Exception as e:
                print(f"Warning: Failed to cleanup cinematic instance: {e}")

        # Aggressively clean ALL PNGs from script-output
        self._cleanup_all_script_output_pngs()

        self.db_manager.close()

    def _cleanup_all_script_output_pngs(self) -> None:
        """Remove ALL PNG files from Factorio script-output directory."""
        try:
            if not self.config.script_output_dir:
                script_output = (
                    Path.home()
                    / "Library"
                    / "Application Support"
                    / "factorio"
                    / "script-output"
                )
            else:
                script_output = Path(self.config.script_output_dir)

            if not script_output.exists():
                return

            # Find and remove ALL PNG files recursively
            png_count = 0
            for png_file in script_output.rglob("*.png"):
                try:
                    png_file.unlink()
                    png_count += 1
                except Exception as e:
                    print(f"Warning: Could not delete {png_file}: {e}")

            if png_count > 0:
                print(f"Cleaned up {png_count} PNG files from script-output")

            # Try to remove empty directories
            for dirpath in sorted(
                script_output.rglob("*"), key=lambda p: len(p.parts), reverse=True
            ):
                if dirpath.is_dir():
                    try:
                        dirpath.rmdir()  # Only removes if empty
                    except OSError:
                        pass  # Directory not empty or can't be removed

        except Exception as e:
            print(f"Warning: Failed to cleanup script-output PNGs: {e}")

    def _extract_throughput_item(self, task_key: str) -> Optional[str]:
        """Extract the throughput item name from a task key.

        E.g., 'iron_plate_throughput_16' -> 'iron-plate'
              'automation_science_pack_throughput' -> 'automation-science-pack'
        """
        if not task_key:
            return None

        task_lower = task_key.lower()

        # Remove trailing numbers first (e.g., _16, _32)
        parts = task_lower.split("_")
        if parts and parts[-1].isdigit():
            parts = parts[:-1]
            task_lower = "_".join(parts)

        # Remove common suffixes
        for suffix in ["_throughput_unbounded", "_throughput", "_unbounded"]:
            if task_lower.endswith(suffix):
                task_lower = task_lower[: -len(suffix)]
                break

        # Convert underscores to hyphens (Factorio naming convention)
        item_name = task_lower.replace("_", "-")

        return item_name if item_name else None

    def _linger_on_relevant_entity(self) -> None:
        """Find and focus camera on an assembler producing the target item."""
        if not self.cinematic_instance or not self.task_throughput_item:
            return

        # Find assembler with matching recipe using RCON
        lua_script = f"""
        local target_item = "{self.task_throughput_item}"
        local surface = game.surfaces[1]
        local assemblers = surface.find_entities_filtered{{
            type = "assembling-machine",
            force = "player"
        }}
        
        local best_assembler = nil
        local best_score = -1
        
        for _, asm in ipairs(assemblers) do
            local recipe = asm.get_recipe()
            if recipe then
                -- Check if this recipe produces our target item
                for _, product in ipairs(recipe.products) do
                    if product.name == target_item then
                        -- Prefer working assemblers
                        local score = 0
                        if asm.status == defines.entity_status.working then
                            score = 2
                        elseif asm.status == defines.entity_status.normal then
                            score = 1
                        end
                        
                        if score > best_score then
                            best_score = score
                            best_assembler = asm
                        end
                        break
                    end
                end
            end
        end
        
        if best_assembler then
            rcon.print(string.format("%.2f,%.2f", best_assembler.position.x, best_assembler.position.y))
        else
            rcon.print("")
        end
        """

        try:
            result = self.cinematic_instance.rcon_client.send_command(
                f"/sc {lua_script}"
            )

            if result and "," in result:
                # Parse position
                x_str, y_str = result.strip().split(",")
                target_x = float(x_str)
                target_y = float(y_str)

                print(f"Found relevant assembler at ({target_x:.1f}, {target_y:.1f})")

                # Pan camera to the assembler with a close zoom
                # zoom = 1.2  # Close-up view

                # Use cutscene's set_camera_state if available, otherwise use RCON
                if (
                    hasattr(self.cinematic_instance, "cutscene")
                    and self.cinematic_instance.cutscene
                ):
                    # Set camera position via RCON for smooth view
                    camera_cmd = f"""
                    /sc game.players[1].teleport({{x={target_x}, y={target_y}}})
                    """
                    self.cinematic_instance.rcon_client.send_command(camera_cmd)

                # Wait and let frames capture while focused on this entity
                time.sleep(self.config.linger_seconds)

                print(f"Lingered for {self.config.linger_seconds}s")
            else:
                print(f"No assembler found producing {self.task_throughput_item}")

        except Exception as e:
            print(f"Error during linger: {e}")
            if self.config.debug:
                raise


def main():
    """Main entry point for the rollout to videos script."""
    parser = argparse.ArgumentParser(
        description="Generate videos from Factorio program rollouts using CinematicInstance"
    )
    parser.add_argument(
        "versions", nargs="+", type=int, help="Version numbers to process"
    )
    parser.add_argument(
        "--output-dir", "-o", default="rollout_videos", help="Output directory"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=1000,
        help="Maximum programs to process per version",
    )
    parser.add_argument(
        "--address",
        default=os.getenv("FACTORIO_SERVER_ADDRESS", "localhost"),
        help="Factorio server address",
    )
    parser.add_argument(
        "--tcp-port",
        type=int,
        default=int(os.getenv("FACTORIO_SERVER_PORT", "27000")),
        help="Factorio server port",
    )
    parser.add_argument(
        "--no-capture", action="store_true", help="Disable screenshot capture"
    )
    parser.add_argument(
        "--script-output-dir", help="Override Factorio script-output directory"
    )
    parser.add_argument("--no-render", action="store_true", help="Skip video rendering")
    parser.add_argument(
        "--render-fps",
        type=int,
        default=int(os.getenv("CINEMA_RENDER_FPS", "24")),
        help="Video framerate for rendering (default: 24 fps)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=4.0,
        help="Playback speed multiplier (default: 4.0x)",
    )
    parser.add_argument(
        "--render-crf",
        type=int,
        default=int(os.getenv("CINEMA_RENDER_CRF", "28")),
        help="Video quality CRF (lower = higher quality, 18-28 recommended, default: 28)",
    )
    parser.add_argument(
        "--render-preset",
        default=os.getenv("CINEMA_RENDER_PRESET", "slow"),
        help="FFmpeg preset (slow = better compression, default: slow)",
    )
    parser.add_argument(
        "--max-bitrate",
        default="2M",
        help="Maximum video bitrate for size control (default: 2M)",
    )
    parser.add_argument(
        "--buffer-size",
        default="4M",
        help="Video buffer size for rate control (default: 4M)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (raise exceptions instead of continuing)",
    )
    parser.add_argument(
        "--no-subtitles",
        action="store_true",
        help="Disable subtitle generation",
    )
    parser.add_argument(
        "--linger-seconds",
        type=float,
        default=3.0,
        help="How long to linger on final relevant entity (default: 3.0 seconds, only when max-steps not explicitly set)",
    )
    parser.add_argument(
        "--no-linger",
        action="store_true",
        help="Disable lingering on final entity at end",
    )

    args = parser.parse_args()

    # Detect if max_steps was explicitly set by checking if it differs from default
    import sys

    max_steps_explicit = "--max-steps" in sys.argv or "-m" in sys.argv

    # Create configuration
    config = ProcessingConfig(
        output_dir=args.output_dir,
        max_steps=args.max_steps,
        address=args.address,
        tcp_port=args.tcp_port,
        capture_enabled=not args.no_capture,
        script_output_dir=args.script_output_dir,
        render_enabled=not args.no_render,
        render_fps=args.render_fps,
        speed=args.speed,
        render_crf=args.render_crf,
        render_preset=args.render_preset,
        target_max_bitrate=args.max_bitrate,
        target_buffer_size=args.buffer_size,
        debug=args.debug,
        subtitles_enabled=not args.no_subtitles,
        linger_seconds=0.0 if args.no_linger else args.linger_seconds,
        max_steps_explicit=max_steps_explicit,
    )

    # Process each version
    for version in args.versions:
        try:
            processor = RolloutToVideos(config)
            report = processor.process_version(version)

            print(f"\nVersion {version} completed:")
            print(f"  Programs processed: {report.programs_processed}")
            print(f"  Total shots: {report.total_shots}")
            print(f"  Total frames: {report.total_frames}")
            print(f"  Processing time: {report.processing_time:.2f}s")
            if report.errors:
                print(f"  Errors: {len(report.errors)}")
                for error in report.errors:
                    print(f"    - {error}")

            # Check if we should exit gracefully
            if processor.exit_handler.exit_reason == "graceful_exit":
                print(f"\n{'=' * 60}")
                print("GRACEFUL EXIT COMPLETED")
                print("Video created from available frames")
                print(f"{'=' * 60}")
                break
            elif processor.exit_handler.exit_reason == "force_exit":
                print(f"\n{'=' * 60}")
                print("FORCE EXIT - No video created")
                print(f"{'=' * 60}")
                break

        except KeyboardInterrupt:
            print(f"\n{'=' * 60}")
            print("KEYBOARD INTERRUPT - Exiting immediately")
            print(f"{'=' * 60}")
            break
        except Exception as e:
            print(f"Failed to process version {version}: {e}")
            continue

    print("\nProcessing completed!")


if __name__ == "__main__":
    main()
