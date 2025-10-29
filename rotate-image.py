#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pillow",
#     "pillow-avif-plugin",
# ]
# ///
"""
Daily rotating image for About page.

This script implements a deterministic image rotation system:
- Discovers source images in img/about-src/
- Uses Python's random.shuffle() with fixed integer seed (deterministic, non-repeating)
- Selects today's image based on Paris timezone day-of-year
- Optimizes to AVIF format (Q=80) with metadata stripping
- Can run locally (dry-run) or in GitHub Actions (production)

Why integer seed instead of random.seed(string):
- Integer seeds are cross-platform deterministic (Python 3.2+)
- String seeds depend on PYTHONHASHSEED (non-deterministic across runs)
- SHA256 hash provides stable seed from repository name + salt
"""

import argparse
import hashlib
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from PIL import Image
    import pillow_avif  # noqa: F401 - required for AVIF support
except ImportError as e:
    print(f"Error: Missing required package: {e}", file=sys.stderr)
    print("Run with: uv run rotate-image.py", file=sys.stderr)
    print("Or install manually: pip install pillow pillow-avif-plugin", file=sys.stderr)
    sys.exit(1)


def compute_seed(repository: str, salt: str) -> int:
    """
    Compute deterministic seed from repository name and salt.

    Uses integer seed (not string) for cross-platform reproducibility.
    Python's random.seed() with integers is stable across platforms (Python 3.2+).

    Args:
        repository: GitHub repository name (e.g., "owner/repo")
        salt: Salt string for global order variation

    Returns:
        Integer seed for random.seed()
    """
    hash_input = f"{repository}-{salt}"
    hash_hex = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    return int(hash_hex, 16)


def discover_source_images(src_dir: Path) -> list[Path]:
    """
    Discover source images in directory.

    Args:
        src_dir: Source directory path

    Returns:
        Sorted list of JPG/JPEG file paths
    """
    patterns = ["*.jpg", "*.jpeg", "*.JPG", "*.JPEG"]
    files = []
    for pattern in patterns:
        files.extend(src_dir.glob(pattern))
    return sorted(files)


def optimize_image(source: Path, output: Path, max_width: int = 1024, quality: int = 80):
    """
    Optimize image to AVIF format.

    Args:
        source: Source image path
        output: Output AVIF path
        max_width: Maximum width in pixels
        quality: AVIF quality (0-100), default 80
    """
    with Image.open(source) as img:
        # Strip EXIF metadata
        if "exif" in img.info:
            del img.info["exif"]

        # Resize maintaining aspect ratio
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # Save as AVIF
        img.save(
            output,
            format="AVIF",
            quality=quality,
            speed=4,  # effort parameter (0=slowest/best, 10=fastest/worst)
        )


def main():
    parser = argparse.ArgumentParser(description="Rotate daily image for About page")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be selected without saving",
    )
    parser.add_argument(
        "--preview",
        type=int,
        metavar="DAYS",
        help="Show next N days of rotation",
    )
    parser.add_argument(
        "--repository",
        default="sderev/sderev.com",
        help="GitHub repository name (default: sderev/sderev.com)",
    )
    parser.add_argument(
        "--salt",
        default="about-rotation-v1",
        help="Salt for shuffle seed (default: about-rotation-v1)",
    )
    parser.add_argument(
        "--src-dir",
        type=Path,
        default=Path("img/about-src"),
        help="Source images directory (default: img/about-src)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("img/about/image.avif"),
        help="Output AVIF path (default: img/about/image.avif)",
    )
    parser.add_argument(
        "--day-offset",
        type=int,
        default=0,
        metavar="N",
        help="Simulate N days in the future (for testing rotation)",
    )

    args = parser.parse_args()

    # Discover source images
    if not args.src_dir.exists():
        print(f"Error: Source directory {args.src_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    files = discover_source_images(args.src_dir)
    if not files:
        print(f"Error: No JPG/JPEG files found in {args.src_dir}", file=sys.stderr)
        sys.exit(1)

    n = len(files)
    print(f"Found {n} source image(s)")

    # Compute seed and create shuffled list
    seed = compute_seed(args.repository, args.salt)
    random.seed(seed)

    # Create index list and shuffle it
    indices = list(range(n))
    random.shuffle(indices)

    if args.dry_run:
        print(f"Repository: {args.repository}")
        print(f"Salt: {args.salt}")
        print(f"Seed: {seed:#018x} ({seed})")
        print(f"Shuffled indices: {indices}")
        print()

    # Get Paris timezone date
    paris_tz = ZoneInfo("Europe/Paris")
    now_paris = datetime.now(paris_tz)

    # Apply day offset for testing
    if args.day_offset:
        now_paris += timedelta(days=args.day_offset)

    paris_date = now_paris.strftime("%Y-%m-%d")
    paris_day = int(now_paris.strftime("%j"))  # Day of year (001-366)

    # Select today's image
    cycle_idx = (paris_day - 1) % n
    chosen_idx = indices[cycle_idx]
    chosen_file = files[chosen_idx]

    print(f"Paris date: {paris_date}")
    print(f"Paris day of year: {paris_day}")
    print(f"Cycle index: {cycle_idx} (day {paris_day} mod {n} images)")
    print(f"Shuffled index: {chosen_idx}")
    print(f"Selected: {chosen_file.name}")

    # Preview mode
    if args.preview:
        print(f"\nNext {args.preview} days:")
        for offset in range(args.preview):
            future_date = datetime.now(paris_tz).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            future_date += timedelta(days=offset)
            future_day = int(future_date.strftime("%j"))
            future_cycle_idx = (future_day - 1) % n
            future_chosen_idx = indices[future_cycle_idx]
            future_file = files[future_chosen_idx].name

            marker = " ← TODAY" if offset == 0 else ""
            print(f"  {future_date.strftime('%Y-%m-%d')}: {future_file}{marker}")

    # Dry-run mode: exit without saving
    if args.dry_run:
        print("\n✓ Dry-run complete (no files modified)")
        sys.exit(0)

    # Production mode: optimize and save
    args.output.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nOptimizing {chosen_file} → {args.output}")
    optimize_image(chosen_file, args.output)

    print(f"✓ Image rotation complete")


if __name__ == "__main__":
    main()
