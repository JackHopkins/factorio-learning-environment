#!/usr/bin/env python3
"""
Optimized sprite downloader with parallel downloads and compression support
"""

import os
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Optional
import concurrent.futures
from functools import partial
from tqdm import tqdm
from huggingface_hub import hf_hub_download, list_repo_files, snapshot_download
import threading

from fle.agents.data.sprites.extractors.alerts import AlertSpriteExtractor
from fle.agents.data.sprites.extractors.icons import IconSpriteExtractor


class OptimizedSpriteDownloader:
    def __init__(self, repo_id: str = "Noddybear/fle_images", num_workers: int = 10):
        self.repo_id = repo_id
        self.num_workers = num_workers
        self.download_lock = threading.Lock()
        self.progress_lock = threading.Lock()
        self.completed_files = 0
        self.total_files = 0

    def download_file_parallel(
        self, file_path: str, output_path: Path, pbar: tqdm
    ) -> Optional[Path]:
        """Download a single file with progress tracking"""
        try:
            # Download to cache
            local_file = hf_hub_download(
                repo_id=self.repo_id,
                filename=file_path,
                repo_type="dataset",
                cache_dir=output_path / ".cache",
                force_filename=file_path,  # Keep original structure
            )

            # Copy to final location
            rel_path = Path(file_path)
            dest_path = output_path / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Use hard link if possible (instant, no copy)
            try:
                os.link(local_file, dest_path)
            except (OSError, AttributeError):
                # Fall back to copy if hard link fails
                shutil.copy2(local_file, dest_path)

            # Update progress
            with self.progress_lock:
                self.completed_files += 1
                pbar.update(1)

            return dest_path

        except Exception as e:
            print(f"\nError downloading {file_path}: {e}")
            with self.progress_lock:
                pbar.update(1)
            return None


def download_sprites_from_hf(
    repo_id: str = "Noddybear/fle_images",
    output_dir: str = ".fle/spritemaps",
    force: bool = False,
    num_workers: int = 10,
    use_snapshot: bool = True,
    archive_name: Optional[str] = None,
) -> bool:
    """
    Optimized sprite download with multiple strategies

    Args:
        repo_id: Hugging Face dataset repository ID
        output_dir: Directory to save sprites
        force: Force re-download even if files exist
        num_workers: Number of parallel download workers
        use_snapshot: Use snapshot_download for faster bulk download
        archive_name: If sprites are in a single archive file, specify its name

    Returns:
        True if successful, False otherwise
    """
    output_path = Path(output_dir)

    # Check if already downloaded
    if output_path.exists() and not force:
        if any(output_path.iterdir()):
            print(
                f"Sprites already exist in {output_path}. Use --force to re-download."
            )
            return True

    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # Strategy 1: Check if sprites are in a single archive
        if archive_name or check_for_archive(repo_id):
            return download_archive_strategy(repo_id, output_path, archive_name)

        # Strategy 2: Use snapshot_download for bulk download (fastest for many files)
        if use_snapshot:
            return download_snapshot_strategy(repo_id, output_path)

        # Strategy 3: Parallel individual downloads
        return download_parallel_strategy(repo_id, output_path, num_workers)

    except Exception as e:
        print(f"Error downloading sprites: {e}")
        return False


def check_for_archive(repo_id: str) -> Optional[str]:
    """Check if repository contains an archive file with all sprites"""
    try:
        files = list_repo_files(repo_id, repo_type="dataset")

        # Look for common archive formats
        archive_extensions = [".tar.gz", ".tar.bz2", ".tar", ".zip", ".7z"]
        archives = [
            f for f in files if any(f.endswith(ext) for ext in archive_extensions)
        ]

        # Look for files that might contain sprites
        sprite_archives = [
            a
            for a in archives
            if any(
                keyword in a.lower()
                for keyword in ["sprite", "image", "all", "complete"]
            )
        ]

        if sprite_archives:
            # Return the largest archive (likely the complete set)
            return max(sprite_archives, key=lambda x: len(x))

        # If there's only one archive, it's probably what we want
        if len(archives) == 1:
            return archives[0]

    except Exception:
        pass

    return None


def download_archive_strategy(
    repo_id: str, output_path: Path, archive_name: Optional[str]
) -> bool:
    """Download and extract archive file (fastest method)"""
    print("Using archive download strategy...")

    try:
        if not archive_name:
            archive_name = check_for_archive(repo_id)
            if not archive_name:
                print("No archive found, falling back to parallel downloads")
                return False

        print(f"Downloading archive: {archive_name}")

        # Download the archive
        archive_path = hf_hub_download(
            repo_id=repo_id,
            filename=archive_name,
            repo_type="dataset",
            cache_dir=output_path / ".cache",
        )

        # Extract based on file type
        print("Extracting sprites...")

        if archive_name.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zf:
                # Extract with progress bar
                members = zf.namelist()
                with tqdm(total=len(members), desc="Extracting") as pbar:
                    for member in members:
                        zf.extract(member, output_path)
                        pbar.update(1)

        elif archive_name.endswith((".tar.gz", ".tar.bz2", ".tar")):
            mode = (
                "r:gz"
                if archive_name.endswith(".gz")
                else "r:bz2"
                if archive_name.endswith(".bz2")
                else "r"
            )
            with tarfile.open(archive_path, mode) as tf:
                # Extract with progress bar
                members = tf.getmembers()
                with tqdm(total=len(members), desc="Extracting") as pbar:
                    for member in members:
                        tf.extract(member, output_path)
                        pbar.update(1)
        else:
            print(f"Unsupported archive format: {archive_name}")
            return False

        # Clean up cache
        cache_dir = output_path / ".cache"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)

        print(f"Successfully extracted sprites to {output_path}")
        return True

    except Exception as e:
        print(f"Error with archive strategy: {e}")
        return False


def download_snapshot_strategy(repo_id: str, output_path: Path) -> bool:
    """Use HF snapshot_download for efficient bulk download"""
    print("Using snapshot download strategy (recommended for many files)...")

    try:
        # snapshot_download is optimized for downloading entire repos
        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            cache_dir=output_path / ".cache",
            local_dir=output_path,
            local_dir_use_symlinks=False,  # Copy files instead of symlinks
            ignore_patterns=["*.md", "*.txt", ".git*"],  # Skip non-image files
        )

        # Clean up cache
        cache_dir = output_path / ".cache"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)

        print(f"Successfully downloaded sprites to {output_path}")
        return True

    except Exception as e:
        print(f"Error with snapshot strategy: {e}")
        return False


def download_parallel_strategy(
    repo_id: str, output_path: Path, num_workers: int
) -> bool:
    """Parallel download of individual files"""
    print(f"Using parallel download strategy with {num_workers} workers...")

    try:
        downloader = OptimizedSpriteDownloader(repo_id, num_workers)

        # List all files
        files = list_repo_files(repo_id, repo_type="dataset")
        image_files = [f for f in files if f.endswith((".png", ".jpg", ".jpeg"))]

        if not image_files:
            print("No image files found in the repository.")
            return False

        downloader.total_files = len(image_files)
        print(f"Found {len(image_files)} sprite files to download.")

        # Create progress bar
        with tqdm(total=len(image_files), desc="Downloading sprites") as pbar:
            # Use ThreadPoolExecutor for parallel downloads
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=num_workers
            ) as executor:
                # Create partial function with fixed arguments
                download_func = partial(
                    downloader.download_file_parallel,
                    output_path=output_path,
                    pbar=pbar,
                )

                # Submit all downloads
                futures = {
                    executor.submit(download_func, file_path): file_path
                    for file_path in image_files
                }

                # Wait for completion
                for future in concurrent.futures.as_completed(futures):
                    future.result()
                    # Result handling is done in download_file_parallel

        # Clean up cache
        cache_dir = output_path / ".cache"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)

        print(
            f"Successfully downloaded {downloader.completed_files}/{downloader.total_files} sprites"
        )
        return downloader.completed_files > 0

    except Exception as e:
        print(f"Error with parallel strategy: {e}")
        return False


def create_sprite_archive(
    input_dir: str = ".fle/sprites",
    output_file: str = "fle_sprites.tar.gz",
    compression: str = "gz",
) -> bool:
    """
    Create a compressed archive of sprites for faster distribution

    Args:
        input_dir: Directory containing sprites
        output_file: Output archive filename
        compression: Compression type ('gz', 'bz2', 'xz', or None)
    """
    input_path = Path(input_dir)

    if not input_path.exists():
        print(f"Input directory {input_path} does not exist.")
        return False

    print(f"Creating archive {output_file}...")

    try:
        mode = f"w:{compression}" if compression else "w"

        with tarfile.open(output_file, mode) as tar:
            # Get all files to archive
            files = list(input_path.rglob("*"))
            files = [f for f in files if f.is_file()]

            with tqdm(total=len(files), desc="Archiving") as pbar:
                for file_path in files:
                    # Add file with relative path
                    arcname = file_path.relative_to(input_path)
                    tar.add(file_path, arcname=arcname)
                    pbar.update(1)

        # Get file size
        size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"Created archive: {output_file} ({size_mb:.1f} MB)")
        return True

    except Exception as e:
        print(f"Error creating archive: {e}")
        return False


def generate_sprites(
    input_dir: str = ".fle/spritemaps", output_dir: str = ".fle/sprites"
):
    """
    Generate individual sprites from spritemaps

    Args:
        input_dir: Directory containing downloaded spritemaps
        output_dir: Directory to save extracted sprites
        data_path: Path to data.json file (optional)
    """
    # Import here to avoid circular imports
    import sys
    from pathlib import Path

    # Add the sprites directory to Python path
    sprites_module_path = Path(__file__).parent.parent / "data" / "sprites"
    if sprites_module_path.exists():
        sys.path.insert(0, str(sprites_module_path))

    try:
        from fle.agents.data.sprites.extractors.entities import (
            EntitySpritesheetExtractor,
        )
        from fle.agents.data.sprites.extractors.resources import ResourceSpriteExtractor
        from fle.agents.data.sprites.extractors.terrain import TerrainSpriteExtractor
        from fle.agents.data.sprites.extractors.trees import TreeSpriteExtractor
    except ImportError:
        print("Error: Could not import extractor modules.")
        print("Make sure the extractor modules are in the correct location.")
        return False

    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.exists():
        print(
            f"Input directory {input_path} does not exist. Run 'fle sprites download' first."
        )
        return False

    print(f"Generating sprites from {input_path} to {output_path}...")

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # Check if we have a data.json in the input directory
        if (input_path / "data.json").exists():
            # Run entity extraction
            entities = EntitySpritesheetExtractor(str(input_path), str(output_path))
            entities.extract_all()

        # Check for other resources
        base_graphics = input_path / "__base__" / "graphics"

        if base_graphics.exists():
            resources_path = base_graphics / "resources"
            if resources_path.exists():
                resources = ResourceSpriteExtractor(
                    str(resources_path), str(output_path)
                )
                resources.extract_all_resources()
                resources.create_all_icons()

                trees = TreeSpriteExtractor(str(resources_path), str(output_path))
                trees.extract_all_trees()

            terrain_path = base_graphics / "terrain"
            if terrain_path.exists():
                terrain = TerrainSpriteExtractor(str(terrain_path), str(output_path))
                terrain.extract_all_resources()
                terrain.create_all_icons()

            icons_path = base_graphics / "icons"
            if icons_path.exists():
                icon = IconSpriteExtractor(str(icons_path), str(output_path))
                icon.extract_all_icons()

            alerts_path = icons_path / "alerts"
            if alerts_path.exists():
                icon = AlertSpriteExtractor(str(alerts_path), str(output_path))
                icon.extract_all_alerts()

        else:
            # Fallback: Just copy PNG files from spritemaps
            print("No __base__/graphics structure found, copying PNG files directly...")

            png_files = list(input_path.rglob("*.png"))

            if not png_files:
                print("No PNG files found in spritemaps directory.")
                return False

            from tqdm import tqdm
            import shutil

            for png_file in tqdm(png_files, desc="Copying sprites"):
                # Maintain relative path structure
                rel_path = png_file.relative_to(input_path)
                dest_path = output_path / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(png_file, dest_path)

        print(f"Successfully generated sprites in {output_path}")
        return True

    except Exception as e:
        print(f"Error generating sprites: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    download_sprites_from_hf()
    generate_sprites()
