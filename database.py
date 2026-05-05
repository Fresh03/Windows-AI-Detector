# ════════════════════════════════════════════════════════════════════════════
# DATABASE MODULE: Window Detection Storage & Retrieval
# ════════════════════════════════════════════════════════════════════════════
# This module handles all SQLite database operations for storing and retrieving
# image metadata and detection results.
#
# TO MODIFY:
#   - Change DB_PATH to use a different database file location
#   - Modify SCHEMA to add/remove fields from the tables
#   - Add new functions for custom queries
#
import sqlite3
from pathlib import Path
from datetime import datetime

# ── DATABASE CONFIGURATION ─────────────────────────────────────────────────────
# TO CHANGE: Update DB_PATH to store database in a different location
#   Example: DB_PATH = "./data/detections.db"
DB_PATH = "detections.db"

# ── DATABASE SCHEMA ────────────────────────────────────────────────────────────
# Defines the structure of the SQLite database with two tables:
#
# IMAGES TABLE: Stores metadata about each image processed
#   - id: Unique identifier (auto-incrementing)
#   - filepath: Full path to where image was stored
#   - filename: Just the filename
#   - width_px, height_px: Image dimensions (pixels)
#   - processed_at: ISO timestamp when image was processed
#
# DETECTIONS TABLE: Stores individual window detections
#   - id: Unique detection ID
#   - image_id: Foreign key linking to images table
#   - class_name: Object class ("Window", "Wood", "Plastic", etc.)
#   - confidence: Detection confidence score (0.0 to 1.0)
#   - x, y, width, height: Bounding box coordinates/dimensions
#   - rel_size_pct: Percentage of image covered by this detection
#   - timestamp: When this detection was recorded
#
# TO MODIFY SCHEMA:
#   - To add fields: Insert new columns in CREATE TABLE
#     Example: add_cost_estimate REAL to store estimated repair cost
#   - To remove fields: Delete them from CREATE TABLE
#   - To add new table: Append CREATE TABLE statement to SCHEMA
#
SCHEMA = """
CREATE TABLE IF NOT EXISTS images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath    TEXT NOT NULL,
    filename    TEXT NOT NULL,
    width_px    INTEGER,
    height_px   INTEGER,
    processed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS detections (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id     INTEGER NOT NULL,
    class_name   TEXT NOT NULL,
    confidence   REAL,
    x            INTEGER,
    y            INTEGER,
    width        INTEGER,
    height       INTEGER,
    rel_size_pct REAL,
    timestamp    TEXT NOT NULL,
    FOREIGN KEY (image_id) REFERENCES images(id)
);
"""

# ── CONNECTION FUNCTION ────────────────────────────────────────────────────────
# WHAT IT DOES: Opens a connection to the SQLite database with Row factory
# This allows accessing columns by name instead of index
# RETURNS: SQLite connection object
# TO MODIFY:
#   - To use different database type (PostgreSQL, MySQL):
#     Replace sqlite3 with the appropriate library
#   - To add connection pooling for performance:
#     Implement a connection pool instead of creating new connection each time
#
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Allow accessing columns by name
    return conn

# ── DATABASE INITIALIZATION ────────────────────────────────────────────────────
# WHAT IT DOES: Creates all database tables if they don't exist
# This is safe to call multiple times (won't drop existing data)
# RETURNS: Nothing
# TO MODIFY: Only if changing SCHEMA structure above
#
def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)  # Create tables defined in SCHEMA
    conn.commit()
    conn.close()

# ── INSERT/UPDATE IMAGE RECORD ─────────────────────────────────────────────────
# WHAT IT DOES:
#   1. Checks if image with same filename already exists in database
#   2. If exists: returns existing image_id (prevents duplicates)
#   3. If new: inserts record and returns new image_id
#
# PARAMETERS:
#   - filepath: Path object or string to the image file
#   - width_px, height_px: Image dimensions in pixels
#
# RETURNS: Image ID from database
#
# TO MODIFY FOR DIFFERENT BEHAVIOR:
#   - To ALWAYS create new record (allow duplicates):
#     Remove the "SELECT id FROM images..." check, always INSERT
#   - To use different unique identifier:
#     Change the WHERE clause from "filename =" to "filepath =" or another field
#   - To store additional metadata:
#     Add new parameters and include in INSERT VALUES tuple
#
def insert_image(filepath, width_px, height_px):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO images (filepath, filename, width_px, height_px, processed_at) VALUES (?, ?, ?, ?, ?)",
        (str(filepath), Path(filepath).name, width_px, height_px, datetime.now().isoformat())
    )
    image_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return image_id
    # File not found in database, so insert new record
    cursor = conn.execute(
        "INSERT INTO images (filepath, filename, width_px, height_px, processed_at) VALUES (?, ?, ?, ?, ?)",
        (str(filepath), Path(filepath).name, width_px, height_px, datetime.now().isoformat())
    )
    image_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return image_id

# ── INSERT DETECTION RECORDS ───────────────────────────────────────────────────
# WHAT IT DOES:
#   1. Clears all old detections for this image (prevents accumulation)
#   2. Calculates relative size percentage for each detection
#   3. Inserts all detection records at once (batch insert for efficiency)
#
# PARAMETERS:
#   - image_id: ID of the image these detections belong to
#   - detections: List of detection dictionaries (from model output)
#   - img_area: Total area of image (width * height in pixels)
#
# RETURNS: Nothing
#
# TO MODIFY FOR DIFFERENT BEHAVIOR:
#   - To KEEP old detections instead of replacing:
#     Remove the "DELETE FROM detections..." line
#     (Result: Will accumulate detections each time you run detection)
#   - To filter detections before saving:
#     Add a condition like: if det["confidence"] >= 0.5
#     (Result: Only save high-confidence detections)
#   - To calculate different metrics:
#     Modify the rel_size calculation or add new fields
#   - To save additional information:
#     Add new parameters to rows.append() tuple
#
def insert_detections(image_id, detections, img_area):
    conn = get_connection()
    # Clear old detections for this image first (to avoid accumulation)
    conn.execute("DELETE FROM detections WHERE image_id = ?", (image_id,))
    
    rows = []
    for det in detections:
        # Calculate what percentage of the image this detection covers
        rel_size = (det["width"] * det["height"]) / img_area * 100
        rows.append((
            image_id,
            det["class"].strip(),
            det["confidence"],
            int(det["x"]),
            int(det["y"]),
            int(det["width"]),
            int(det["height"]),
            round(rel_size, 2),
            datetime.now().isoformat()
        ))
    # Batch insert all detections at once (more efficient than individual INSERTs)
    conn.executemany(
        "INSERT INTO detections (image_id, class_name, confidence, x, y, width, height, rel_size_pct, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    conn.close()

# ── GET ALL IMAGES ────────────────────────────────────────────────────────────
# WHAT IT DOES: Retrieves all processed images from database with window count
#
# RETURNS: List of image records (newest first)
# Each record includes: id, filepath, filename, width_px, height_px, processed_at, window_count
#
# SQL QUERY BREAKDOWN:
#   - LEFT JOIN: Links images with their detections
#   - AND d.class_name = 'Window': Counts ONLY window detections
#   - GROUP BY: Aggregates counts per image
#   - ORDER BY DESC: Shows newest images first
#
# TO MODIFY FOR DIFFERENT BEHAVIOR:
#   - To count ALL detections (not just windows):
#     Remove the "AND d.class_name = 'Window'" condition
#   - To sort by oldest first:
#     Change "DESC" to "ASC"
#   - To sort by number of windows:
#     Change "ORDER BY i.processed_at DESC" to "ORDER BY window_count DESC"
#   - To only return recent images (last 7 days):
#     Add: WHERE i.processed_at > datetime('now', '-7 days')
#
def get_all_images():
    conn = get_connection()
    rows = conn.execute("""
        SELECT i.*, COUNT(d.id) as window_count
        FROM images i
        LEFT JOIN detections d 
            ON d.image_id = i.id 
            AND d.class_name = 'Window'
        GROUP BY i.id
        ORDER BY i.processed_at DESC
    """).fetchall()
    conn.close()
    return rows

# ── GET DETECTIONS FOR IMAGE ──────────────────────────────────────────────────
# WHAT IT DOES: Retrieves all detections (windows + other objects) for a specific image
#
# PARAMETERS:
#   - image_id: ID of the image to get detections for
#
# RETURNS: List of detection records for that image
#
# TO MODIFY FOR DIFFERENT BEHAVIOR:
#   - To get only window detections:
#     Add: WHERE class_name = 'Window' AND image_id = ?
#   - To get only high-confidence detections:
#     Add: WHERE confidence >= 0.6 AND image_id = ?
#   - To order by confidence (highest first):
#     Add: ORDER BY confidence DESC
#   - To sort by size (largest first):
#     Add: ORDER BY (width * height) DESC
#
def get_detections_for_image(image_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM detections WHERE image_id = ?", (image_id,)
    ).fetchall()
    conn.close()
    return rows