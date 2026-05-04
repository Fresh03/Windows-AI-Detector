from inference_sdk import InferenceHTTPClient
from database import init_db, insert_image, insert_detections
from dotenv import load_dotenv
from pathlib import Path
import cv2
import sys
import os
import numpy as np
import shutil
import json

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

init_db()
load_dotenv()
api_key = os.getenv("ROBOFLOW_API_KEY")
if not api_key:
    print("Error: ROBOFLOW_API_KEY not found in .env file")
    sys.exit(1)

client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=api_key
)

if len(sys.argv) < 2:
    print("Usage: python detect.py <image_name>")
    sys.exit(1)

image_name = sys.argv[1]
image_path = UPLOAD_DIR / image_name

if not image_path.exists():
    print(f"Error: '{image_name}' not found in uploads/ folder")
    sys.exit(1)

print(f"\nSending {image_path} to Roboflow model...")

result = client.run_workflow(
    workspace_name="fresh-qlpw7",
    workflow_id="general-segmentation-api",
    images={"image": str(image_path)},
    parameters={"classes": "Plastic, Window, Wood"},
    use_cache=True
)


# ── UTILITY FUNCTION: Clean Result ────────────────────────────────────────────
# This function truncates large strings and limits list/dict depth for easier debugging
# WHAT IT DOES: Prevents huge strings/arrays from cluttering console output by capping their display
# PARAMETERS:
#   - obj: any Python object (dict, list, string, etc.)
#   - max_str: max string length before truncating (default: 50)
# TO MODIFY OUTPUT:
#   - Increase max_str to show longer strings without truncation
#   - Change [:3] to [:N] to show more/fewer list items
#   - Add recursion depth limit if dealing with deeply nested objects
def clean_result(obj, max_str=50):
    if isinstance(obj, str) and len(obj) > max_str:
        return f"<string len={len(obj)}>"
    if isinstance(obj, dict):
        return {k: clean_result(v, max_str) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_result(i, max_str) for i in obj[:3]]  # first 3 items only - change [:3] to show more
    return obj

try:
    # ── FILTERING PARAMETERS ──────────────────────────────────────────────────────
    # These settings filter out low-quality or noise detections before processing
    # TO MODIFY FOR DIFFERENT RESULTS:
    #   - Lower MIN_CONFIDENCE to catch smaller objects (trades accuracy for recall)
    #   - Raise MIN_CONFIDENCE to be stricter (fewer false positives)
    #   - Increase MIN_WIDTH/MIN_HEIGHT to ignore tiny noise boxes
    #   - Decrease MIN_WIDTH/MIN_HEIGHT to catch smaller objects
    
    MIN_CONFIDENCE = 0.40 # 40% confidence threshold - adjust as needed
    MIN_WIDTH = 10   # pixels - to filter out tiny detections that are likely noise
    MIN_HEIGHT = 10  # pixels - to filter out tiny detections that are likely noise

    # Filter detections: keep only those meeting all three criteria
    detections = [d for d in result[0]["predictions"]["predictions"]
                if d["confidence"] >= MIN_CONFIDENCE
                and d["width"] >= MIN_WIDTH
                and d["height"] >= MIN_HEIGHT]
except (KeyError, IndexError, TypeError) as e:
    print(f"Unexpected response structure: {e}")
    sys.exit(1)

img = cv2.imread(image_path)
img_h, img_w = img.shape[:2]
img_area = img_w * img_h

# ── MAIN FUNCTION: Remove Nested Detections ──────────────────────────────────
# WHAT IT DOES: Filters out "nested" detections that are mostly contained within
# larger detections. This cleans up overlapping bounding boxes.
#
# PARAMETERS:
#   - detections: list of detection dictionaries (each has x, y, width, height, class, confidence)
#   - overlap_threshold: percentage of smaller box that must be inside larger box
#     to be considered "nested" and removed (default: 0.6 = 60%)
#
# HOW IT WORKS:
#   1. For each detection A, check if it's inside any larger detection B
#   2. Calculate intersection area between A and B
#   3. If intersection ≥ overlap_threshold AND B is larger, remove A (it's nested)
#   4. Return only non-nested detections
#
# TO MODIFY FOR DIFFERENT OUTCOMES:
#   - INCREASE overlap_threshold (e.g., 0.8):
#     → Be more aggressive: only remove boxes that are almost completely overlapped
#     → Result: Keep more slightly-overlapping detections
#   - DECREASE overlap_threshold (e.g., 0.3):
#     → Be more aggressive: remove boxes that have even partial overlap
#     → Result: Keep fewer overlapping detections, cleaner output
#   - To KEEP all overlaps: Set overlap_threshold = 1.0
#   - To REMOVE almost any overlap: Set overlap_threshold = 0.01
#
def remove_nested(detections, overlap_threshold=0.6):   # 60% overlap threshold - adjust as needed
    """Remove detections that are mostly inside another detection."""
    keep = []
    for i, det_a in enumerate(detections):
        # Calculate bounding box corners for detection A (from center x, y and dimensions)
        ax1 = det_a["x"] - det_a["width"] / 2
        ay1 = det_a["y"] - det_a["height"] / 2
        ax2 = det_a["x"] + det_a["width"] / 2
        ay2 = det_a["y"] + det_a["height"] / 2
        area_a = det_a["width"] * det_a["height"]

        is_nested = False
        for j, det_b in enumerate(detections):
            if i == j:
                continue  # Don't compare a detection to itself
            
            # Calculate bounding box corners for detection B
            bx1 = det_b["x"] - det_b["width"] / 2
            by1 = det_b["y"] - det_b["height"] / 2
            bx2 = det_b["x"] + det_b["width"] / 2
            by2 = det_b["y"] + det_b["height"] / 2
            area_b = det_b["width"] * det_b["height"]

            # Calculate intersection rectangle (overlapping area)
            ix1 = max(ax1, bx1)
            iy1 = max(ay1, by1)
            ix2 = min(ax2, bx2)
            iy2 = min(ay2, by2)

            if ix2 <= ix1 or iy2 <= iy1:
                continue  # no overlap between these boxes

            # Calculate intersection area
            intersection = (ix2 - ix1) * (iy2 - iy1)

            # Decision: if most of A is inside B, and B is bigger — mark A as nested (remove it)
            if intersection / area_a >= overlap_threshold and area_b > area_a:
                is_nested = True
                break

        if not is_nested:
            keep.append(det_a)

    return keep

# ── SEPARATE AND FILTER BY CLASS ──────────────────────────────────────────────
# WHAT IT DOES: 
#   1. Splits detections into "window" class and everything else
#   2. Applies nested detection removal to windows only
#   3. Other classes are kept as-is for visualization only
#
# TO MODIFY FOR DIFFERENT OUTCOMES:
#   - To apply remove_nested to other classes too:
#     Add: others = remove_nested(others)
#   - To apply different overlap thresholds per class:
#     windows = remove_nested(windows, overlap_threshold=0.5)  # stricter for windows
#     others = remove_nested(others, overlap_threshold=0.8)    # lenient for others
#   - To filter by different class names, change "window" to your class name
#   - To remove a specific class entirely, modify the filter condition

windows = [d for d in detections if d["class"].strip().lower() == "window"]
windows = remove_nested(windows)  # Remove overlapping window detections
others  = [d for d in detections if d["class"].strip().lower() != "window"]

print(f"\nImage:   {image_path}  ({img_w}x{img_h} px)")
print(f"Windows: {len(windows)}  |  Other objects: {len(others)}\n")

# ── DEFINE CLASS COLORS FOR VISUALIZATION ────────────────────────────────────
# WHAT IT DOES: Maps object class names to BGR color codes for drawing on image
#
# TO MODIFY FOR DIFFERENT OUTCOMES:
#   - Change the RGB tuple values to use different colors:
#     Example: "window": (255, 255, 0) for blue
#     Remember: OpenCV uses BGR order, not RGB
#   - Add new classes: "door": (100, 100, 200)
#   - The get(cls.lower(), (0, 255, 0)) at draw time sets default color (green) for unlisted classes

colors = {
    "window":  (0, 255, 0),     # Green
    "wood":    (0, 165, 255),   # Orange
    "plastic": (255, 0, 0),     # Blue
}

# ── SAVE TO DATABASE ──────────────────────────────────────────────────────────
# WHAT IT DOES: Stores image metadata and window detection results in the database
#
# TO MODIFY FOR DIFFERENT OUTCOMES:
#   - To save all detections instead of just windows:
#     Change: insert_detections(image_id, windows, img_w * img_h)
#     To:     insert_detections(image_id, detections, img_w * img_h)
#   - To save without database: Comment out these lines entirely

image_id = insert_image(image_path, img_w, img_h)
insert_detections(image_id, windows, img_w * img_h)
print(f"Saved to database (image_id={image_id})")

# ── PRINT WINDOW DETECTIONS TABLE & DRAW ON IMAGE ───────────────────────────
# WHAT IT DOES: 
#   1. Prints a formatted table of all window detections with metadata
#   2. Draws bounding boxes or polygon masks on the image
#   3. Labels each detection with confidence percentage
#
# TABLE COLUMNS: Index | Class | Confidence | X,Y Position | Width,Height | Coverage%
#
# TO MODIFY FOR DIFFERENT OUTCOMES:
#   - To change table formatting: modify the print() strings and f-string format
#   - To add more columns to table: calculate new values and add to print format
#   - To use different drawing colors: modify the color lookup or override color variable
#   - To change box thickness: modify thickness=2 parameter in cv2.rectangle/polylines
#   - To disable table: comment out the entire if windows: block
#   - To use bounding boxes instead of polygons: remove the if "points" condition
#   - To change polygon transparency: modify the alpha value in addWeighted (0.25 = 25% opacity)

if windows:
    print(f"{'#':<4} {'Class':<10} {'Conf':>6} {'X':>6} {'Y':>6} {'W':>6} {'H':>6} {'Cover%':>7}")
    print("-" * 55)
    for i, det in enumerate(windows):
        cls  = det["class"].strip()
        conf = det["confidence"]
        x, y = int(det["x"]), int(det["y"])
        w, h = int(det["width"]), int(det["height"])
        rel  = (w * h) / img_area * 100  # Calculate percentage of image covered
        print(f"{i+1:<4} {cls:<10} {conf:>6.1%} {x:>6} {y:>6} {w:>6} {h:>6} {rel:>6.1f}%")

        color = colors.get(cls.lower(), (0, 255, 0))
        
        # If polygon points are available, draw filled + outlined polygon
        if "points" in det and det["points"]:
            pts = np.array([[int(p["x"]), int(p["y"])] for p in det["points"]], np.int32)
            overlay = img.copy()
            cv2.fillPoly(overlay, [pts], color)
            # Blend filled polygon with original image (0.25 = 25% opacity for fill)
            cv2.addWeighted(overlay, 0.25, img, 0.75, 0, img)
            cv2.polylines(img, [pts], isClosed=True, color=color, thickness=2)
        # Otherwise, draw rectangle bounding box
        else:
            x1, y1 = x - w//2, y - h//2
            x2, y2 = x + w//2, y + h//2
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

        # Add text label with confidence
        lx = int(det["x"]) - int(det["width"]) // 2
        ly = int(det["y"]) - int(det["height"]) // 2 - 8
        cv2.putText(img, f"Window {conf:.0%}", (lx, max(ly, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

# ── DRAW OTHER CLASSES (Wood, Plastic, etc.) ──────────────────────────────────
# WHAT IT DOES: 
#   Draws the non-window detections on the image as thin polygon outlines
#   (No table, no labels—just visual reference)
#
# TO MODIFY FOR DIFFERENT OUTCOMES:
#   - To disable drawing other classes: comment out this entire block
#   - To add labels to other classes: insert cv2.putText similar to windows section
#   - To draw as rectangles instead of polygons:
#     Replace the polylines section with rectangle drawing (see windows section)
#   - To change line thickness: modify thickness=1 in cv2.polylines

for det in others:
    cls   = det["class"].strip()
    color = colors.get(cls.lower(), (200, 200, 200))  # Default gray if class not in colors dict
    if "points" in det and det["points"]:
        pts = np.array([[int(p["x"]), int(p["y"])] for p in det["points"]], np.int32)
        cv2.polylines(img, [pts], isClosed=True, color=color, thickness=1)

# ── SAVE ANNOTATED IMAGE ───────────────────────────────────────────────────────
# WHAT IT DOES: Writes the image with all drawn detections to the outputs folder
#
# TO MODIFY FOR DIFFERENT OUTCOMES:
#   - To save to different location: change OUTPUT_DIR
#   - To change output filename format: modify the f-string (e.g., add timestamp)
#   - To save as PNG instead of JPG: change "_detected.jpg" to "_detected.png"
#   - To not save output: comment out this section

output_path = OUTPUT_DIR / (Path(image_path).stem + "_detected.jpg")
cv2.imwrite(str(output_path), img)
print(f"\nAnnotated image saved → {output_path}")