import subprocess
from pathlib import Path
import shutil


def png_to_mp4(input_dir, output_file="output.mp4", framerate=24):
    """
    Convert numbered PNG files from specified directory to MP4.
    Creates a temporary directory with renamed files to ensure continuous sequence.
    """
    input_path = Path(input_dir).resolve()
    if not input_path.is_dir():
        raise ValueError(f"Directory not found: {input_dir}")

    # Get all PNG files in specified directory
    png_files = list(input_path.glob("*.png"))
    if not png_files:
        raise ValueError(f"No PNG files found in {input_dir}")

    # Sort files numerically
    png_files.sort(key=lambda x: int(x.stem))

    # Create temporary directory for renamed files
    temp_dir = input_path / "temp_sequence"
    temp_dir.mkdir(exist_ok=True)

    try:
        # Copy and rename files to ensure continuous sequence
        for idx, file in enumerate(png_files, start=1):
            shutil.copy2(
                file,
                temp_dir / f"{idx:06d}.png",  # Use 6 digits padding
            )

        # FFmpeg command using the temporary directory
        ffmpeg_cmd = [
            "ffmpeg",
            "-framerate",
            str(framerate),
            "-i",
            str(temp_dir / "%06d.png"),  # Match the padding in rename
            "-vf",
            "scale=1920:1028:force_original_aspect_ratio=decrease,pad=1920:1028:(ow-iw)/2:(oh-ih)/2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(output_file),
        ]

        # Run the command
        subprocess.run(ffmpeg_cmd, check=True)

    finally:
        # Clean up temporary directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


# Example usage:
if __name__ == "__main__":
    import argparse

    # python screenshots_to_mp4.py ./screenshots/517/27000 -o ./screenshots/517/27000/output.mp4 -f 30

    parser = argparse.ArgumentParser(description="Convert PNG sequence to MP4")
    parser.add_argument("input_dir", help="Directory containing PNG files")
    parser.add_argument(
        "--output",
        "-o",
        default="output.mp4",
        help="Output MP4 file path (default: output.mp4)",
    )
    parser.add_argument(
        "--framerate",
        "-f",
        type=int,
        default=24,
        help="Framerate of output video (default: 24)",
    )

    args = parser.parse_args()

    if not args:
        pass
    try:
        png_to_mp4(args.input_dir, args.output, args.framerate)
        print(f"Successfully created {args.output}")
    except Exception as e:
        print(f"Error: {e}")
