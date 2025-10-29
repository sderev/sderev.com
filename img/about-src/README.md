# About Page Image Source Files

This directory contains the source images that rotate daily on the About page.

## Adding New Images

1. **Place your source images here** as JPG or JPEG files
   - Any orientation works: portrait, landscape, or square
   - The workflow preserves aspect ratios (no cropping or distortion)
   - Recommended minimum: 1024px on the longest dimension
   - Quality: high-quality source files (optimization happens automatically)

2. **Automatic optimization**
   - The GitHub Action runs `rotate-image.py` (Python script)
   - Converts JPG → AVIF format using Pillow
   - Downsizes large images to max 1024px width (Q=80 quality)
   - Preserves small images at original resolution
   - Strips metadata for privacy and smaller file size
   - Output: `/img/about/image.avif` on the `gh-pages` branch

3. **No further action needed**
   - Images are automatically included in rotation after pushing to `main`
   - The rotation cycle updates daily at midnight (Europe/Paris)

## How Rotation Works

The rotation uses a **deterministic shuffle** algorithm:

* All source images are discovered and sorted alphabetically
* Python's `random.shuffle()` with a fixed integer seed creates a global permutation
* Each day selects: `permutation[Paris_day_of_year % total_images]`
* **Result**: Non-repeating cycle showing each image once before repeating

**Key features:**
* No database or state file needed
* Same image shows every 24 hours (predictable for a given date)
* No repeats until all images have been displayed
* Order appears random but is deterministic and reproducible

## Testing Locally

Before pushing changes, you can test the rotation logic locally using `uv`:

```bash
# Dry-run mode (shows selection without saving)
uv run rotate-image.py --dry-run

# Preview next 7 days of rotation
uv run rotate-image.py --dry-run --preview 7

# Test with actual optimization (creates img/about/image.avif)
uv run rotate-image.py

# Generate and view tomorrow's image
uv run rotate-image.py --day-offset 1

# Test rotation for any future date (e.g., 7 days from now)
uv run rotate-image.py --day-offset 7
```

The script uses PEP 723 inline dependencies, so `uv` automatically manages the required packages (Pillow and pillow-avif-plugin). The algorithm is identical to the GitHub Action, guaranteeing consistent results.

**Note:** The `--day-offset` parameter is for testing only - it simulates future dates to verify the rotation cycle works correctly before pushing changes.

## Reshuffling the Global Order

To create a completely new rotation sequence:

1. Edit `rotate-image.py`
2. Find the line: `default="about-rotation-v1"`
3. Change to a new value: `default="about-rotation-v2"` (or any unique string)
4. Also update `.github/workflows/rotate-about-image.yml` to pass `--salt about-rotation-v2`
5. Commit and push to `main`

This generates a new permutation while keeping the non-repeating property.

## File Naming

Files are sorted alphabetically, so naming affects discovery order (not display order, which is shuffled):

* `artwork-001.jpg`, `artwork-002.jpg`, etc. (organized)
* `painting-monet.jpg`, `sketch-2024.jpg` (descriptive)

Choose any naming scheme that helps you organize your collection.
