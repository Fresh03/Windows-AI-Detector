# ════════════════════════════════════════════════════════════════════════════
# GUI APPLICATION: Window Detection Interface
# ════════════════════════════════════════════════════════════════════════════
# This is the main graphical user interface (GUI) for the window detection system.
# It provides:
#   - Image upload capability
#   - Real-time detection via Roboflow API
#   - Results display with detailed tables
#   - History of processed images
#   - Visual annotations on detected images
#
# TECHNOLOGY: Uses CustomTkinter for modern dark-themed GUI
# USAGE: python gui.py
#

# ── IMPORTS ────────────────────────────────────────────────────────────────────
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageTk
import shutil
import threading
from pathlib import Path
from database import init_db, get_all_images, get_detections_for_image
import subprocess
import sys

# ── THEME SETUP ────────────────────────────────────────────────────────────────
# WHAT IT DOES: Configures the appearance and color scheme for the GUI
#
# TO MODIFY:
#   - To use light theme instead: Change "dark" to "light"
#     ctk.set_appearance_mode("light")
#   - To change accent color: Replace "blue" with another color
#     Available: "blue", "green", "dark-blue", "red", "orange"
#     ctk.set_default_color_theme("green")
#
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Initialize database on startup
init_db()

# ════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION CLASS
# ════════════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    """MAIN APPLICATION CLASS
    WHAT IT DOES: Manages the entire GUI application including:
      - Window setup and layout
      - User interactions (buttons, uploads, etc.)
      - Detection workflow
      - Results display and history
    """
    def __init__(self):
        """
        CONSTRUCTOR - Initialize the GUI application
        WHAT IT DOES:
          1. Creates main window with title and size
          2. Sets up sidebar and main content area
          3. Initializes variables for tracking current image
          4. Builds all UI components
          5. Loads history from database
        
        TO MODIFY WINDOW:
          - Change title: Replace "Window Detector" with your app name
          - Change size: Modify "1300x800" to desired resolution
          - To allow resizing: Change resizable(False, False) to (True, True)
        """
        super().__init__()
        self.title("Window Detector")
        self.geometry("1300x800")
        self.resizable(False, False)
        self.current_image = None
        self.current_image_id = None
        self._build_ui()
        self._load_history()

    # ── OPEN ALL DETECTIONS TAB ──────────────────────────────────────
    # WHAT IT DOES: Switches to "All Detections" tab and refreshes the table
    # TO MODIFY: Change tab name to access different tab by default
    def _open_all_table(self):
        self._refresh_all_table()
        self.tabs.set("All Detections")

    # ── BUILD USER INTERFACE ─────────────────────────────────────────
    # WHAT IT DOES:
    #   1. Creates left sidebar with buttons and history
    #   2. Creates right main area with tabs (Image, Detected, Detections, All)
    #   3. Creates stats bar showing current image info
    #   4. Sets up all interactive elements
    #
    # LAYOUT STRUCTURE:
    #   ┌─────────────────────────────────────────────────┐
    #   │   LEFT SIDEBAR      │    STATS BAR              │
    #   │   - Buttons         │  File  Size  Windows Conf │
    #   │   - History         │────────────────────────────│
    #   │                     │    TABBED INTERFACE       │
    #   │                     │ - Image view              │
    #   │                     │ - Detected image          │
    #   │                     │ - Detection table         │
    #   │                     │ - All detections table    │
    #   └─────────────────────────────────────────────────┘
    #
    # TO MODIFY LAYOUT:
    #   - To change sidebar width: Modify width=280 in CTkFrame
    #   - To add new buttons: Insert new CTkButton in left frame
    #   - To add new tabs: Insert self.tabs.add("New Tab")
    #   - To change window title styling: Modify font size/weight
    def _build_ui(self):
        # Left sidebar
        self.left = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.left.pack(side="left", fill="y")
        self.left.pack_propagate(False)

        ctk.CTkLabel(self.left, text="WINDOW DETECTOR",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(25,3))
        ctk.CTkLabel(self.left, text="AI-Powered Detection",
                     text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=(0,20))

        ctk.CTkButton(self.left, text="Upload & Detect", height=42,
                      command=self._upload).pack(padx=15, pady=4, fill="x")
        self.detect_btn = ctk.CTkButton(self.left, text="Detect Windows", height=42,
                fg_color="#1f6aa5", state="disabled",
                command=self._detect)
        self.detect_btn.pack(padx=15, pady=4, fill="x")

        ctk.CTkButton(self.left, text="Show Detected Image", height=42,
                fg_color="#2b2b2b", hover_color="#3b3b3b",
                command=self._show_detected).pack(padx=15, pady=4, fill="x")
        
        self.progress = ctk.CTkProgressBar(self.left, mode="indeterminate")
        self.progress.pack(padx=15, pady=(0,4), fill="x")
        self.progress.pack_forget()  # hidden by default

        ctk.CTkLabel(self.left, text="HISTORY",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray").pack(pady=(25,5), padx=15, anchor="w")

        self.history_frame = ctk.CTkScrollableFrame(self.left)
        self.history_frame.pack(padx=8, pady=4, fill="both", expand=True)

        # Right main area
        self.right = ctk.CTkFrame(self, corner_radius=0, fg_color="#1a1a1a")
        self.right.pack(side="right", fill="both", expand=True)

        # Stats bar
        self.stats_bar = ctk.CTkFrame(self.right, height=65, fg_color="#111111")
        self.stats_bar.pack(fill="x")
        self.stats_bar.pack_propagate(False)

        self.stat_file = self._stat_label(self.stats_bar, "FILE", "—")
        self.stat_size = self._stat_label(self.stats_bar, "SIZE", "—")
        self.stat_wins = self._stat_label(self.stats_bar, "WINDOWS", "—")
        self.stat_conf = self._stat_label(self.stats_bar, "AVG CONF", "—")

        # Tabs
        self.tabs = ctk.CTkTabview(self.right)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=8)
        self.tabs.add("Image")
        self.tabs.add("Detected")
        self.tabs.add("Detections")
        self.tabs.add("All Detections")
        self.all_table_frame = ctk.CTkScrollableFrame(self.tabs.tab("All Detections"))
        self.all_table_frame.pack(fill="both", expand=True)
        self._build_all_table_header()

        self.image_label = ctk.CTkLabel(self.tabs.tab("Image"),
                                        text="Upload an image to get started",
                                        text_color="gray",
                                        font=ctk.CTkFont(size=14))
        self.image_label.pack(expand=True)

        self.detected_label = ctk.CTkLabel(self.tabs.tab("Detected"),
                                    text="No detected image yet",
                                    text_color="gray",
                                    font=ctk.CTkFont(size=14))
        self.detected_label.pack(expand=True)

        self.table_frame = ctk.CTkScrollableFrame(self.tabs.tab("Detections"))
        self.table_frame.pack(fill="both", expand=True)
        self._build_table_header()

        self.status = ctk.CTkLabel(self.right, text="Ready",
                                   text_color="gray",
                                   font=ctk.CTkFont(size=11))
        self.status.pack(pady=6)

    def _show_detected(self):
        """DISPLAY DETECTED/ANNOTATED IMAGE
        WHAT IT DOES:
          1. Looks for annotated image in outputs folder (with "_detected.jpg" suffix)
          2. Loads and displays the image with drawn detections
          3. Switches to "Detected" tab
        
        REQUIREMENTS: Must have run detection first to generate annotated image
        
        TO MODIFY:
          - To look for different output format: Change "_detected.jpg" suffix
          - To show original image if annotated not found: Remove fallback check
          - To open in external viewer: Use subprocess to open with Windows Photos app
        """
        if self.current_image is None:
            self.status.configure(text="No image loaded.")
            return
        out_path = Path("outputs") / (self.current_image.stem + "_detected.jpg")
        print(f"Looking for: {out_path}, exists: {out_path.exists()}")
        if not out_path.exists():
            self.status.configure(text=f"No detected image found: {out_path}")
            return
        img = Image.open(out_path)
        img.thumbnail((920, 620))
        photo = ImageTk.PhotoImage(img)
        self.detected_label.configure(image=photo, text="")
        self.detected_label.image = photo
        self.tabs.set("Detected")

    def _stat_label(self, parent, title, value):
        """CREATE STAT DISPLAY WIDGET
        WHAT IT DOES: Creates a labeled stat box (title above value) for the stats bar
        
        PARAMETERS:
          - parent: Frame to add this widget to
          - title: Label text (e.g., "FILE", "WINDOWS")
          - value: Value to display (e.g., filename, count)
        
        RETURNS: Reference to the value label (for updating later)
        
        TO MODIFY:
          - To change font size: Modify font=ctk.CTkFont(size=...)
          - To change alignment: Modify anchor parameter
          - To add icons: Add emoji or symbol before text
        """
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=22, pady=8)
        ctk.CTkLabel(f, text=title, text_color="gray",
                     font=ctk.CTkFont(size=10)).pack()
        val = ctk.CTkLabel(f, text=value,
                           font=ctk.CTkFont(size=15, weight="bold"))
        val.pack()
        return val

    # ── TABLE BUILDING & DISPLAY ─────────────────────────────────────
    def _build_table_header(self):
        """BUILD TABLE HEADER FOR CURRENT IMAGE DETECTIONS
        WHAT IT DOES: Creates column headers for the detections table
        
        COLUMNS: # | Class | Confidence | X | Y | Width | Height | Cover%
        
        TO MODIFY COLUMNS:
          - Add new column: Insert new name in cols list
          - Change column order: Rearrange cols list
          - Change column width: Modify widths list value
          - Example: To add "Area" column:
            cols = [..., "Area"]
            widths = [..., 70]
        """
        cols   = ["#", "Class", "Confidence", "X", "Y", "Width", "Height", "Cover%"]
        widths = [30, 80, 90, 55, 55, 65, 65, 65]
        h = ctk.CTkFrame(self.table_frame, fg_color="#111111")
        h.pack(fill="x", pady=(0,2))
        for c, w in zip(cols, widths):
            ctk.CTkLabel(h, text=c, width=w,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="gray").pack(side="left", padx=2, pady=5)
            
    def _build_all_table_header(self):
        """BUILD TABLE HEADER FOR ALL DETECTIONS ACROSS ALL IMAGES
        WHAT IT DOES: Creates column headers for the global detections table
        
        COLUMNS: ID | Image | Confidence | X | Y | W | H | Cover% | Date
        
        TO MODIFY: Same as _build_table_header - modify cols and widths lists
        """
        cols   = ["ID", "Image", "Confidence", "X", "Y", "W", "H", "Cover%", "Date"]
        widths = [40, 180, 85, 55, 55, 55, 55, 65, 110]
        h = ctk.CTkFrame(self.all_table_frame, fg_color="#111111")
        h.pack(fill="x", pady=(0,2))
        for c, w in zip(cols, widths):
            ctk.CTkLabel(h, text=c, width=w,
                        font=ctk.CTkFont(size=11, weight="bold"),
                        text_color="gray").pack(side="left", padx=2, pady=5)
            
    def _refresh_all_table(self):
        """REFRESH ALL DETECTIONS TABLE (GLOBAL VIEW)
        WHAT IT DOES:
          1. Clears all existing rows from the table
          2. Queries database for all images and their detections
          3. Rebuilds table with all window detections across all images
          4. Alternates row colors (striped effect) for readability
        
        TO MODIFY:
          - To show all classes (not just windows): Remove class_name filter
          - To show only high-confidence: Add confidence threshold check
          - To limit results: Add slicing: for img_record in images[:50]
          - To sort by column: Sort images or dets before displaying
        """
        for w in self.all_table_frame.winfo_children()[1:]:
            w.destroy()  # Clear old rows (keep header)
        images = get_all_images()
        i = 0
        for img_record in images:
            dets = get_detections_for_image(img_record["id"])
            img_area = img_record["width_px"] * img_record["height_px"]
            for det in dets:
                if det["class_name"].strip().lower() != "window":
                    continue
                cover = round((det["width"] * det["height"]) / img_area * 100, 1)
                values = [
                    str(det["id"]),
                    img_record["filename"],
                    f"{det['confidence']:.1%}",
                    str(det["x"]), str(det["y"]),
                    str(det["width"]), str(det["height"]),
                    f"{cover}%",
                    det["timestamp"][:10]
                ]
                row = ctk.CTkFrame(self.all_table_frame,
                                fg_color="#2b2b2b" if i % 2 == 0 else "#222222")
                row.pack(fill="x", pady=1)
                widths = [40, 180, 85, 55, 55, 55, 55, 65, 110]
                for val, w in zip(values, widths):
                    ctk.CTkLabel(row, text=val, width=w,
                                font=ctk.CTkFont(size=11)).pack(side="left", padx=2, pady=4)
                i += 1

    def _update_table(self, image_id, img_area):
        """REFRESH DETECTIONS TABLE FOR CURRENT IMAGE
        WHAT IT DOES:
          1. Clears old table rows
          2. Queries database for detections of current image
          3. Displays only window detections (filters others)
          4. Shows bounding box info and coverage percentage
        
        PARAMETERS:
          - image_id: ID of image to show detections for
          - img_area: Total image area (width * height) for calculating coverage
        
        TO MODIFY:
          - To show all classes: Remove the class_name != "window" check
          - To show different columns: Modify values list and widths
          - To add clickable rows: Bind mouse events to zoom/highlight detections
        """
        for w in self.table_frame.winfo_children()[1:]:
            w.destroy()  # Clear old rows
        detections = get_detections_for_image(image_id)
        widths = [30, 80, 90, 55, 55, 65, 65, 65]
        i = 0
        for det in detections:
            if det["class_name"].strip().lower() != "window":
                continue
            cover = round((det["width"] * det["height"]) / img_area * 100, 1)
            values = [
                str(i + 1),
                det["class_name"].strip(),
                f"{det['confidence']:.1%}",
                str(det["x"]), str(det["y"]),
                str(det["width"]), str(det["height"]),
                f"{cover}%"
            ]
            row = ctk.CTkFrame(self.table_frame,
                               fg_color="#2b2b2b" if i % 2 == 0 else "#222222")
            row.pack(fill="x", pady=1)
            for val, w in zip(values, widths):
                ctk.CTkLabel(row, text=val, width=w,
                             font=ctk.CTkFont(size=11)).pack(side="left", padx=2, pady=4)
            i += 1

    # ── HISTORY MANAGEMENT ────────────────────────────────────────────
    def _load_history(self):
        """LOAD PROCESSED IMAGES FROM HISTORY
        WHAT IT DOES:
          1. Clears history sidebar
          2. Queries database for all processed images
          3. Creates clickable history entries (newest first)
          4. Each entry shows filename, window count, and date
          5. Clicking loads that image
        
        TO MODIFY:
          - To limit history items: Add slicing: for img in get_all_images()[:20]
          - To sort differently: Sort images before loop
          - To hide old images: Filter by date: if img['processed_at'] > threshold
        """
        for w in self.history_frame.winfo_children():
            w.destroy()  # Clear old history
        for img in get_all_images():
            row = ctk.CTkFrame(self.history_frame, fg_color="#2b2b2b",
                               corner_radius=8, cursor="hand2")
            row.pack(fill="x", pady=3, padx=3)
            ctk.CTkLabel(row, text=img["filename"],
                         font=ctk.CTkFont(size=12, weight="bold"),
                         anchor="w").pack(padx=10, pady=(8,2), fill="x")
            ctk.CTkLabel(row,
                         text=f"{img['window_count']} windows  •  {img['processed_at'][:10]}",
                         text_color="gray",
                         font=ctk.CTkFont(size=11), anchor="w").pack(padx=10, pady=(0,8), fill="x")
            # Make entire row clickable
            row.bind("<Button-1>", lambda e, i=img: self._load_from_history(i))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, i=img: self._load_from_history(i))

    def _load_from_history(self, img_record):
        """LOAD PREVIOUSLY PROCESSED IMAGE FROM HISTORY
        WHAT IT DOES:
          1. Loads both original and annotated images if they exist
          2. Displays original image in main tab
          3. Displays annotated (detected) image if available
          4. Updates stats (file name, size, window count, confidence)
          5. Refreshes detection table
        
        PARAMETERS:
          - img_record: Database record for the image
        
        TO MODIFY:
          - To always show annotated version: Remove the original_path exists check
          - To update different stats: Add/remove stat_*.configure() calls
        """
        # Try annotated first, fall back to original
        out_path = Path("outputs") / (Path(img_record["filename"]).stem + "_detected.jpg")
        orig_path = Path("uploads") / img_record["filename"]
        display = out_path if out_path.exists() else orig_path
        if not display.exists():
            self.status.configure(text="Image file not found on disk.")
            return
        self.current_image = orig_path
        self._show_detected()

        orig_path = Path("uploads") / img_record["filename"]
        if orig_path.exists():
            self._show_image(orig_path)
        else:
            self._show_image(display)
        self.stat_file.configure(text=img_record["filename"])
        self.stat_size.configure(text=f"{img_record['width_px']}x{img_record['height_px']}")
        self.stat_wins.configure(text=str(img_record["window_count"]))

        img_area = img_record["width_px"] * img_record["height_px"]
        self.current_image_id = img_record["id"]
        self._update_table(img_record["id"], img_area)

        dets = get_detections_for_image(img_record["id"])
        confs = [d["confidence"] for d in dets if d["class_name"].strip().lower() == "window"]
        self.stat_conf.configure(
            text=f"{sum(confs)/len(confs):.1%}" if confs else "—")
        self.status.configure(text=f"Loaded: {img_record['filename']}")
        self.tabs.set("Image")

    def _detect(self):
        """START DETECTION PROCESS (IN BACKGROUND)
        WHAT IT DOES:
          1. Shows progress bar
          2. Launches detection script in separate thread
          3. Prevents UI from freezing during detection
        
        TO MODIFY:
          - To change progress bar style: Modify progress bar mode
          - To add timeout: Add thread timeout logic
        """
        self.progress.pack(padx=15, pady=(0,4), fill="x")
        self.progress.start()
        self.status.configure(text="Running detection...")
        threading.Thread(target=self._run_detection, daemon=True).start()

    # ── UPLOAD & DETECTION WORKFLOW ───────────────────────────────────
    def _upload(self):
        """UPLOAD AND SELECT IMAGE FOR DETECTION
        WHAT IT DOES:
          1. Opens file dialog to select image
          2. Copies selected image to uploads folder
          3. Displays the selected image
          4. Updates stats
          5. Enables the "Detect Windows" button
        
        SUPPORTED FORMATS: JPG, JPEG, PNG, WEBP, BMP
        
        TO MODIFY:
          - To support other formats: Add to filetypes filter
          - To skip copying (use original location): Remove shutil.copy()
          - To prompt for image description: Add dialog input
        """
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.bmp")])
        if not path:
            return
        dest = Path("uploads") / Path(path).name
        Path("uploads").mkdir(exist_ok=True)
        if Path(path).resolve() != dest.resolve():
            shutil.copy(path, dest)
        self.current_image = dest
        self._show_image(dest)
        self.tabs.set("Image")
        img = Image.open(dest)
        self.stat_file.configure(text=Path(path).name)
        self.stat_size.configure(text=f"{img.width}x{img.height}")
        self.stat_wins.configure(text="—")
        self.stat_conf.configure(text="—")
        self.status.configure(text="Running detection...")
        self.update()
        # enable detect button
        for w in self.left.winfo_children():
            if isinstance(w, ctk.CTkButton) and "Detect" in str(w.cget("text")):
                w.configure(state="normal")
        self.status.configure(text="Image loaded — click Detect Windows")

    def _run_detection(self):
        """EXECUTE DETECTION SCRIPT (RUNS IN BACKGROUND THREAD)
        WHAT IT DOES:
          1. Calls detect.py script with current image filename
          2. Captures output from detection
          3. Sends results back to main thread via self.after()
        
        SCRIPT: detect.py
        OUTPUT: Prints detection results to stdout
        
        TO MODIFY:
          - To use different detection script: Change "detect.py"
          - To pass different parameters: Modify arguments list
          - To change working directory: Modify cwd parameter
        """
        result = subprocess.run(
            [sys.executable, "detect.py", self.current_image.name],
            capture_output=True, text=True,
            cwd=Path(__file__).parent
        )
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        print("Return code:", result.returncode)
        self.after(0, self._on_detection_done, result.stdout)

    def _on_detection_done(self, output):
        """HANDLE DETECTION COMPLETION (RUNS IN MAIN THREAD)
        WHAT IT DOES:
          1. Hides progress bar
          2. Displays annotated image with detections
          3. Parses detection output to extract window counts and confidences
          4. Updates stats with results
          5. Refreshes history and tables
          6. Shows completion popup
        
        PARAMETERS:
          - output: Stdout from detect.py script
        
        TO MODIFY OUTPUT PARSING:
          - To extract different info: Parse output differently
          - To show different stats: Modify stat_*.configure() calls
          - To skip popup: Remove _show_popup() call
        """
        self.progress.stop()
        self.progress.pack_forget()
        stem = self.current_image.stem
        out_path = Path("outputs") / f"{stem}_detected.jpg"
        if out_path.exists():
            self._show_detected()

        lines = output.strip().split("\n")
        wins, confs = [], []
        for line in lines:
            if line and line[0].isdigit():
                parts = line.split()
                if len(parts) >= 3 and "%" in parts[2]:
                    try:
                        confs.append(float(parts[2].replace("%", "")))
                        wins.append(1)
                    except:
                        pass

        self.stat_wins.configure(text=str(len(wins)))
        self.stat_conf.configure(
            text=f"{sum(confs)/len(confs):.1f}%" if confs else "—")

        images = get_all_images()
        if images:
            latest = images[0]
            img = Image.open(self.current_image)
            self._update_table(latest["id"], img.width * img.height)

        self.status.configure(text="Detection complete")
        self._load_history()
        self._show_popup(len(wins))
        self.tabs.set("Detections")
        self._refresh_all_table()

    # ── POPUP DIALOGS ─────────────────────────────────────────────────
    def _show_popup(self, window_count):
        """SHOW COMPLETION POPUP DIALOG
        WHAT IT DOES: Displays a popup message showing how many windows were detected
        
        PARAMETERS:
          - window_count: Number of windows found
        
        TO MODIFY:
          - To change popup title: Modify popup.title()
          - To change message: Modify CTkLabel text
          - To add more options: Add buttons with different commands
          - To change popup size: Modify popup.geometry()
        """
        popup = ctk.CTkToplevel(self)
        popup.title("Detection Complete")
        popup.geometry("280x160")
        popup.resizable(False, False)
        popup.grab_set()
        ctk.CTkLabel(popup, text="✓ Detection Complete",
                    font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(30,8))
        ctk.CTkLabel(popup, text=f"{window_count} window(s) detected",
                    text_color="gray").pack()
        ctk.CTkButton(popup, text="OK", width=100,
                    command=popup.destroy).pack(pady=20)

    # ── HELPER FUNCTIONS ──────────────────────────────────────────────
    def _show_image(self, path):
        """DISPLAY IMAGE IN GUI
        WHAT IT DOES:
          1. Loads image file
          2. Resizes to fit display area (maintaining aspect ratio)
          3. Converts to PhotoImage format for Tkinter
          4. Displays in image_label widget
        
        PARAMETERS:
          - path: Path to image file
        
        MAX DISPLAY SIZE: 920x620 pixels
        
        TO MODIFY:
          - To change max size: Modify thumbnail() size
          - To change display quality: Add resample parameter to thumbnail()
        """
        img = Image.open(path)
        img.thumbnail((920, 620))
        photo = ImageTk.PhotoImage(img)
        self.image_label.configure(image=photo, text="")
        self.image_label.image = photo

# ── MAIN EXECUTION ────────────────────────────────────────────────────────────
# WHAT IT DOES: Checks if script is run directly (not imported)
#   - Creates an instance of the App class
#   - Starts the GUI event loop (waits for user interactions)
#
# TO MODIFY:
#   - To run additional setup before GUI: Add code before app = App()
#   - To run cleanup code after GUI closes: Add code after mainloop()

if __name__ == "__main__":
    app = App()
    app.mainloop()