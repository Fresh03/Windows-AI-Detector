# ════════════════════════════════════════════════════════════════════════════
# DEBUG SCRIPT: Test Roboflow API & Inspect Response Structure
# ════════════════════════════════════════════════════════════════════════════
# This script is useful for debugging and understanding the structure of
# responses from the Roboflow API. Use it to:
#   - Test your API connection and credentials
#   - Inspect what data the API returns
#   - Verify model is working correctly
#   - Understand response structure for parsing
#
# USAGE: python debug.py <image_path>
# EXAMPLE: python debug.py test_image.jpg
#

# ── IMPORTS & SETUP ────────────────────────────────────────────────────────────
from inference_sdk import InferenceHTTPClient
from dotenv import load_dotenv
import json
import os
import sys

# Load API key from .env file
load_dotenv()
api_key = os.getenv("ROBOFLOW_API_KEY")

# ── INITIALIZE API CLIENT ──────────────────────────────────────────────────────
# WHAT IT DOES: Creates a client to communicate with Roboflow's cloud API
#
# TO MODIFY:
#   - To use different Roboflow workspace: Change workspace_name parameter
#   - To use different model: Change workflow_id parameter
#
client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=api_key
)

# ── RUN DETECTION ON IMAGE ────────────────────────────────────────────────────
# WHAT IT DOES:
#   - Sends image to Roboflow API with specified model
#   - Requests detection for three classes: Plastic, Window, Wood
#   - Uses cache if available (faster on repeated requests)
#
# PARAMETERS:
#   - workspace_name: Your Roboflow workspace ID
#   - workflow_id: The model/workflow you want to use
#   - images: Image file to analyze
#   - parameters["classes"]: Comma-separated list of classes to detect
#   - use_cache: Whether to cache results for speed
#
# TO MODIFY FOR DIFFERENT CLASSES:
#   - Change parameters["classes"] to detect different objects
#   - Example: "Door, Window, Damaged Window"
#
result = client.run_workflow(
    workspace_name="fresh-qlpw7",
    workflow_id="general-segmentation-api",
    images={"image": sys.argv[1]},
    parameters={"classes": "Plastic, Window, Wood"},
    use_cache=True
)

# ── PRETTY-PRINT RESPONSE STRUCTURE ────────────────────────────────────────────
# WHAT IT DOES:
#   Prints the API response in a readable tree format
#   Shows data types and truncates long strings to keep output manageable
#   (Useful for understanding what fields are available)
#
# PARAMETERS:
#   - depth: Current nesting depth (for indentation)
#   - max_str: Maximum string length before truncating
#
# TO MODIFY FOR DIFFERENT OUTPUT:
#   - To see longer strings: Increase max_str parameter
#   - To limit list items shown: Change limit in "if obj:" condition
#   - To show full structure: Remove string truncation logic

def summarize(obj, depth=0):
    """Pretty-print nested object structure for debugging"""
    indent = "  " * depth
    if isinstance(obj, dict):
        # Dictionary: print each key and recurse into values
        for k, v in obj.items():
            print(f"{indent}[key] {k}:")
            summarize(v, depth + 1)
    elif isinstance(obj, list):
        # List: show length and sample first item
        print(f"{indent}[list of {len(obj)} items]")
        if obj:
            summarize(obj[0], depth + 1)
    elif isinstance(obj, str) and len(obj) > 80:
        # Long string: show length without printing full content
        print(f"{indent}[long string, len={len(obj)}]")
    else:
        # Simple values: print directly
        print(f"{indent}{repr(obj)}")

# Print the response structure
print("\n════ ROBOFLOW API RESPONSE STRUCTURE ════\n")
summarize(result)