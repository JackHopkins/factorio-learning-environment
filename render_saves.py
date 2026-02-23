#!/usr/bin/env python3
"""
Standalone batch renderer for Factorio saves -> PNG screenshots -> MP4 video.
No FLE imports - just subprocess calls to Factorio --benchmark-graphics.

Usage:
    python render_saves.py /tmp/fle-run-saves/v9 .fle/run_screenshots/v9
"""
import os
import sys
import time
import shutil
import subprocess
import tempfile
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

FACTORIO_BINARY = Path("/tmp/factorio/bin/x64/factorio")
FACTORIO_DATA = Path("/tmp/factorio/data")
MAX_PARALLEL = int(os.getenv("RENDER_MAX_PARALLEL", "1"))
RENDER_TIMEOUT = int(os.getenv("RENDER_TIMEOUT", "420"))  # seconds per render
RENDER_RETRIES = int(os.getenv("RENDER_RETRIES", "2"))  # retries per save
RENDER_TICKS = int(os.getenv("RENDER_TICKS", "60"))

_SCREENSHOT_MOD_INFO = """{
  "name": "fle_screenshot",
  "version": "1.0.0",
  "title": "FLE Screenshot Renderer",
  "author": "FLE",
  "factorio_version": "1.1"
}"""

_SCREENSHOT_MOD_CONTROL = r"""
local EX = {
    ["character"] = true,
    ["entity-ghost"] = true,
    ["tile-ghost"] = true,
    ["electric-energy-interface"] = true,
    ["resource"] = true,
}

local function take_factory_screenshot()
    local s = game.surfaces[1]
    local raw = s.find_entities_filtered{force = "player"}
    local es = {}
    for _, e in pairs(raw) do
        if not EX[e.type] then es[#es + 1] = e end
    end

    local cx, cy, zoom = 0, 0, 0.5
    if #es > 0 then
        local xs, ys = {}, {}
        for _, e in pairs(es) do
            xs[#xs + 1] = e.position.x
            ys[#ys + 1] = e.position.y
        end
        table.sort(xs)
        table.sort(ys)
        local mid = math.floor(#xs / 2) + 1
        local mx, my = xs[mid], ys[mid]

        local da, db = {}, {}
        for i, x in ipairs(xs) do da[i] = math.abs(x - mx) end
        for i, y in ipairs(ys) do db[i] = math.abs(y - my) end
        table.sort(da)
        table.sort(db)
        local ma = math.max(da[mid], 5)
        local mb = math.max(db[mid], 5)
        local tx, ty = ma * 5, mb * 5

        local nb = {}
        for _, e in pairs(es) do
            if math.abs(e.position.x - mx) <= tx and math.abs(e.position.y - my) <= ty then
                nb[#nb + 1] = e
            end
        end
        if #nb == 0 then nb = es end

        local x1, y1, x2, y2 = math.huge, math.huge, -math.huge, -math.huge
        for _, e in pairs(nb) do
            local b = e.bounding_box
            if b.left_top.x < x1 then x1 = b.left_top.x end
            if b.left_top.y < y1 then y1 = b.left_top.y end
            if b.right_bottom.x > x2 then x2 = b.right_bottom.x end
            if b.right_bottom.y > y2 then y2 = b.right_bottom.y end
        end
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        local w = x2 - x1 + 6
        local h = y2 - y1 + 6
        zoom = math.min(1920 / (w * 32), 1080 / (h * 32), 2)
        zoom = math.max(zoom, 0.125)
    end

    game.forces["player"].chart(s, {{cx - 200, cy - 200}, {cx + 200, cy + 200}})
    s.always_day = true
    s.daytime = 0
    s.freeze_daytime = true
    rendering.clear()

    game.take_screenshot{
        surface = s,
        position = {cx, cy},
        resolution = {1920, 1080},
        zoom = zoom,
        path = "factory.png",
        show_entity_info = true,
        show_gui = false,
        force_render = true,
    }
end

local function capture_once()
    local ok, err = pcall(take_factory_screenshot)
    log("FLE_SCREENSHOT config_changed ok=" .. tostring(ok) .. " err=" .. tostring(err))
end

-- --benchmark-graphics reliably runs this hook when an extra mod is injected.
-- on_load/on_init screenshot calls can crash this Factorio build for some saves.
script.on_configuration_changed(capture_once)
"""


def render_screenshot(save_zip: Path, output_png: Path) -> bool:
    """Render a single screenshot from a save file."""
    attempts = RENDER_RETRIES + 1
    for attempt in range(1, attempts + 1):
        tmpdir = tempfile.mkdtemp(prefix="fle_render_")
        try:
            mod_dir = Path(tmpdir) / "mods" / "fle_screenshot"
            mod_dir.mkdir(parents=True)
            (mod_dir / "info.json").write_text(_SCREENSHOT_MOD_INFO)
            (mod_dir / "control.lua").write_text(_SCREENSHOT_MOD_CONTROL)

            config_ini = Path(tmpdir) / "config.ini"
            script_output = Path(tmpdir) / "script-output"
            script_output.mkdir()
            config_ini.write_text(
                f"[path]\n"
                f"read-data={FACTORIO_DATA}\n"
                f"write-data={tmpdir}\n"
            )

            cmd = [
                "xvfb-run", "-a", "-s", "-screen 0 1920x1080x24",
                str(FACTORIO_BINARY),
                "--benchmark-graphics", str(save_zip),
                "--benchmark-ticks", str(RENDER_TICKS),
                "--benchmark-ignore-paused",
                "--mod-directory", str(Path(tmpdir) / "mods"),
                "-c", str(config_ini),
                "--disable-audio",
                "--disable-migration-window",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=RENDER_TIMEOUT,
            )

            screenshot = script_output / "factory.png"
            if screenshot.exists() and screenshot.stat().st_size > 0:
                output_png.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(screenshot, output_png)
                return True

            if attempt < attempts:
                print(
                    f"  Retry {attempt}/{attempts - 1} for {save_zip.name} "
                    f"(no screenshot, exit={result.returncode})"
                )
            else:
                print(f"  Warning: no screenshot for {save_zip.name} (exit={result.returncode})")
                if result.stderr:
                    print(f"  Stderr: {result.stderr[-300:]}")
        except Exception as e:
            if attempt < attempts:
                print(f"  Retry {attempt}/{attempts - 1} for {save_zip.name} (error: {e})")
            else:
                print(f"  Error rendering {save_zip.name}: {e}")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    return False


def png_to_mp4(png_dir: Path, output_path: Path, seconds_per_frame: float = 3.0) -> bool:
    pngs = sorted(f for f in png_dir.glob("step_*.png"))
    if not pngs:
        print("No PNGs to convert")
        return False
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found in PATH")
        return False

    concat_file = png_dir / "_concat.txt"
    with concat_file.open("w") as f:
        for png in pngs:
            f.write(f"file '{png.resolve()}'\n")
            f.write(f"duration {seconds_per_frame}\n")
        f.write(f"file '{pngs[-1].resolve()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    print(f"\nGenerating video: {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    concat_file.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"ffmpeg error: {result.stderr[-300:]}")
        return False
    else:
        print(f"Video saved: {output_path} ({len(pngs)} frames, {seconds_per_frame}s each)")
        return True


def parse_args():
    parser = argparse.ArgumentParser(
        description="Render Factorio save zips into PNG screenshots and an MP4 video."
    )
    parser.add_argument("saves_dir", help="Directory containing save .zip files")
    parser.add_argument("output_dir", help="Directory for output step_*.png and run.mp4")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip step_*.png files that already exist in output_dir",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not delete existing step_*.png files before rendering",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    save_dir = Path(args.saves_dir)
    screenshot_dir = Path(args.output_dir)

    if not save_dir.is_dir():
        sys.exit(f"Saves directory not found: {save_dir}")
    if not FACTORIO_BINARY.is_file():
        sys.exit(f"Factorio binary not found: {FACTORIO_BINARY}")

    saves = sorted(save_dir.glob("*.zip"))
    if not saves:
        sys.exit(f"No .zip saves found in {save_dir}")

    # Clear old screenshots unless explicitly told not to.
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    if not args.no_clear:
        for f in screenshot_dir.glob("step_*.png"):
            f.unlink()

    print(
        f"Rendering {len(saves)} screenshots ({MAX_PARALLEL} parallel, "
        f"{RENDER_TIMEOUT}s timeout, skip_existing={args.skip_existing}, no_clear={args.no_clear})..."
    )
    t0 = time.time()
    success = 0
    skipped = 0

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        futures = {}
        for i, save_zip in enumerate(saves):
            output_png = screenshot_dir / f"step_{i:03d}.png"
            if args.skip_existing and output_png.exists() and output_png.stat().st_size > 0:
                skipped += 1
                print(f"  [{skipped}] Skipped existing step_{i:03d}.png")
                continue
            future = executor.submit(render_screenshot, save_zip, output_png)
            futures[future] = (i, save_zip.name)

        for future in as_completed(futures):
            idx, name = futures[future]
            try:
                ok = future.result()
                if ok:
                    success += 1
                    print(f"  [{success}/{len(saves)}] Rendered step_{idx:03d}.png")
            except Exception as e:
                print(f"  Error rendering {name}: {e}")

    dt = time.time() - t0
    attempted = len(futures)
    total_ready = success + skipped
    print(f"\nRendered {success}/{attempted} attempted in {dt:.1f}s ({skipped} skipped, {total_ready}/{len(saves)} total ready)")

    if total_ready > 0:
        video_path = screenshot_dir / "run.mp4"
        if not png_to_mp4(screenshot_dir, video_path):
            sys.exit("ERROR: failed to generate run.mp4")

    if total_ready != len(saves):
        missing = len(saves) - total_ready
        sys.exit(
            f"ERROR: missing {missing} screenshots "
            f"({total_ready}/{len(saves)} ready)."
        )

    print(f"\nDone! Screenshots: {screenshot_dir}")


if __name__ == "__main__":
    main()
