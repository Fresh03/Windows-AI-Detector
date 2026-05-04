# ════════════════════════════════════════════════════════════════════════════
# QUERY SCRIPT: Display All Processed Images & Detections
# ════════════════════════════════════════════════════════════════════════════
# This is a simple command-line tool to view all images processed by the
# detection system. It shows a formatted table of:
#   - Image ID and filename
#   - Image dimensions (width x height)
#   - Number of windows detected
#   - When the image was processed
#
# USAGE: python query.py
# (No arguments needed)
#

# ── IMPORTS ────────────────────────────────────────────────────────────────────
from database import get_all_images, get_detections_for_image

# ── RETRIEVE ALL IMAGES ───────────────────────────────────────────────────────
# WHAT IT DOES: Queries database for all processed images with window counts
# RETURNS: List of image records
images = get_all_images()

# ── DISPLAY RESULTS ────────────────────────────────────────────────────────────
# WHAT IT DOES:
#   1. Checks if any images exist in database
#   2. If none: prints "No images" message
#   3. If found: prints formatted table of all images
#
# TABLE FORMAT:
#   ID | Filename | Size | Windows | Processed Date
#
# TO MODIFY FOR DIFFERENT OUTPUT:
#   - To add more columns: Calculate new values and add to f-string
#     Example: Add avg_confidence by querying detections
#   - To change table format: Modify print strings and column widths
#   - To sort differently: Add sorting logic to images list
#     Example: images = sorted(images, key=lambda x: x['window_count'], reverse=True)
#   - To filter results: Add conditions
#     Example: images = [i for i in images if i['window_count'] > 0]
#   - To export to CSV: Replace prints with CSV writer
#

if not images:
    print("No images in database yet.")
else:
    # Print table header with column titles
    print(f"\n{'ID':<4} {'Filename':<30} {'Size':<15} {'Windows':>7} {'Processed'}")
    print("─" * 75)
    
    # Print each image as one row
    for img in images:
        size = f"{img['width_px']}x{img['height_px']}"
        print(f"{img['id']:<4} {img['filename']:<30} {size:<15} {img['window_count']:>7}    {img['processed_at'][:19]}")