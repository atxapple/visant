"""Pre-generate thumbnails for all existing captures that don't have them."""
import os
from pathlib import Path
from PIL import Image
import io

def generate_thumbnail(image_path, thumbnail_path, max_size=(400, 300), quality=85):
    """Generate a thumbnail from an image."""
    try:
        img = Image.open(image_path)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        img.save(thumbnail_path, format="JPEG", quality=quality, optimize=True)
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False

def find_images_without_thumbnails(uploads_dir="uploads"):
    """Find all images that don't have thumbnails."""
    uploads_path = Path(uploads_dir)
    images_to_process = []

    # Walk through all capture directories
    for org_dir in uploads_path.glob("*/devices/*/captures"):
        for image_file in org_dir.glob("*.jpg"):
            # Check if this is not already a thumbnail
            if not image_file.stem.endswith("_thumb"):
                # Check if thumbnail exists
                thumb_file = image_file.parent / f"{image_file.stem}_thumb.jpg"
                if not thumb_file.exists():
                    images_to_process.append((image_file, thumb_file))

    return images_to_process

def main():
    print("Scanning for images without thumbnails...")
    images_to_process = find_images_without_thumbnails()

    if not images_to_process:
        print("✓ All images already have thumbnails!")
        return

    print(f"\nFound {len(images_to_process)} images without thumbnails")
    print("Generating thumbnails...\n")

    success_count = 0
    for i, (image_path, thumb_path) in enumerate(images_to_process, 1):
        print(f"[{i}/{len(images_to_process)}] {image_path.name}")
        if generate_thumbnail(image_path, thumb_path):
            success_count += 1
            # Get file sizes
            original_size = image_path.stat().st_size
            thumb_size = thumb_path.stat().st_size
            reduction = (1 - thumb_size / original_size) * 100
            print(f"  Created: {thumb_size:,} bytes (saved {reduction:.1f}%)")
        else:
            print(f"  Failed to generate thumbnail")

    print(f"\n{'='*60}")
    print(f"Successfully generated {success_count}/{len(images_to_process)} thumbnails")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
