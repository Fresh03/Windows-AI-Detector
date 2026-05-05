import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageTk
import shutil
import threading
import sqlite3
from pathlib import Path
from database import init_db, get_all_images, get_detections_for_image
import subprocess
import sys

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

init_db()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Window Detector")
        self.geometry("1300x800")
        self.resizable(True, True)
        self.current_image = None
        self.current_image_id = None
        self._build_ui()
        self._load_history()

    def _open_all_table(self):
        self._refresh_all_table()
        self.tabs.set("All Detections")

    def _build_ui(self):
        self.left = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.left.pack(side="left", fill="y")
        self.left.pack_propagate(False)

        ctk.CTkLabel(self.left, text="WINDOW DETECTOR",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(25,3))
        ctk.CTkLabel(self.left, text="AI-Powered Detection",
                     text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=(0,20))

        ctk.CTkButton(self.left, text="Upload Image", height=42,
                      command=self._upload).pack(padx=15, pady=4, fill="x")

        self.detect_btn = ctk.CTkButton(self.left, text="Detect Windows", height=42,
                      fg_color="#1f6aa5", state="disabled",
                      command=self._detect)
        self.detect_btn.pack(padx=15, pady=4, fill="x")

        # ctk.CTkButton(self.left, text="Show Detected Image", height=42,
        #               fg_color="#2b2b2b", hover_color="#3b3b3b",
        #               command=self._show_detected).pack(padx=15, pady=4, fill="x")

        self.progress = ctk.CTkProgressBar(self.left, mode="indeterminate")
        self.progress.pack(padx=15, pady=(0,4), fill="x")
        self.progress.pack_forget()

        ctk.CTkLabel(self.left, text="DELETE",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray").pack(pady=(20,5), padx=15, anchor="w")

        ctk.CTkButton(self.left, text="Delete This Image", height=38,
                      fg_color="#8b0000", hover_color="#a00000",
                      command=self._delete_current_image).pack(padx=15, pady=3, fill="x")

        ctk.CTkButton(self.left, text="Delete This Image's Detections", height=38,
                      fg_color="#5a0000", hover_color="#700000",
                      command=self._delete_current_detections).pack(padx=15, pady=3, fill="x")

        ctk.CTkButton(self.left, text="Delete All Detections", height=38,
                      fg_color="#3a0000", hover_color="#500000",
                      command=self._delete_all_detections).pack(padx=15, pady=3, fill="x")

        ctk.CTkLabel(self.left, text="HISTORY",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray").pack(pady=(25,5), padx=15, anchor="w")

        self.history_frame = ctk.CTkScrollableFrame(self.left)
        self.history_frame.pack(padx=8, pady=4, fill="both", expand=True)

        self.right = ctk.CTkFrame(self, corner_radius=0, fg_color="#1a1a1a")
        self.right.pack(side="right", fill="both", expand=True)

        self.stats_bar = ctk.CTkFrame(self.right, height=65, fg_color="#111111")
        self.stats_bar.pack(fill="x")
        self.stats_bar.pack_propagate(False)

        self.stat_file = self._stat_label(self.stats_bar, "FILE", "-")
        self.stat_size = self._stat_label(self.stats_bar, "SIZE", "-")
        self.stat_wins = self._stat_label(self.stats_bar, "WINDOWS", "-")
        self.stat_conf = self._stat_label(self.stats_bar, "AVG CONF", "-")

        self.tabs = ctk.CTkTabview(self.right)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=8)
        self.tabs.add("Image")
        self.tabs.add("Detected")
        self.tabs.add("Detections")
        self.tabs.add("All Detections")

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

        self.all_table_frame = ctk.CTkScrollableFrame(self.tabs.tab("All Detections"))
        self.all_table_frame.pack(fill="both", expand=True)
        self._build_all_table_header()

        self.status = ctk.CTkLabel(self.right, text="Ready",
                                   text_color="gray",
                                   font=ctk.CTkFont(size=11))
        self.status.pack(pady=6)

    def _stat_label(self, parent, title, value):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=22, pady=8)
        ctk.CTkLabel(f, text=title, text_color="gray",
                     font=ctk.CTkFont(size=10)).pack()
        val = ctk.CTkLabel(f, text=value,
                           font=ctk.CTkFont(size=15, weight="bold"))
        val.pack()
        return val

    def _build_table_header(self):
        cols   = ["#", "Class", "Confidence", "X", "Y", "Width", "Height", "Cover%"]
        widths = [30, 80, 90, 55, 55, 65, 65, 65]
        h = ctk.CTkFrame(self.table_frame, fg_color="#111111")
        h.pack(fill="x", pady=(0,2))
        for c, w in zip(cols, widths):
            ctk.CTkLabel(h, text=c, width=w,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="gray").pack(side="left", padx=2, pady=5)

    def _build_all_table_header(self):
        cols   = ["ID", "Image", "Confidence", "X", "Y", "W", "H", "Cover%", "Date"]
        widths = [40, 180, 85, 55, 55, 55, 55, 65, 110]
        h = ctk.CTkFrame(self.all_table_frame, fg_color="#111111")
        h.pack(fill="x", pady=(0,2))
        for c, w in zip(cols, widths):
            ctk.CTkLabel(h, text=c, width=w,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="gray").pack(side="left", padx=2, pady=5)

    def _refresh_all_table(self):
        for w in self.all_table_frame.winfo_children()[1:]:
            w.destroy()
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
                ctk.CTkButton(row, text="X", width=28, height=24,
                              fg_color="#8b0000", hover_color="#a00000",
                              font=ctk.CTkFont(size=11),
                              command=lambda did=det["id"], iid=img_record["id"], ia=img_area: self._delete_single_detection(did, iid, ia)
                              ).pack(side="left", padx=4)
                i += 1

    def _update_table(self, image_id, img_area):
        for w in self.table_frame.winfo_children()[1:]:
            w.destroy()
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
            ctk.CTkButton(row, text="X", width=28, height=24,
                          fg_color="#8b0000", hover_color="#a00000",
                          font=ctk.CTkFont(size=11),
                          command=lambda did=det["id"], iid=image_id, ia=img_area: self._delete_single_detection(did, iid, ia)
                          ).pack(side="left", padx=4)
            i += 1

    def _load_history(self):
        for w in self.history_frame.winfo_children():
            w.destroy()
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
            row.bind("<Button-1>", lambda e, i=img: self._load_from_history(i))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, i=img: self._load_from_history(i))

    def _load_from_history(self, img_record):
        orig_path = Path("uploads") / img_record["filename"]
        out_path  = Path("outputs") / (Path(img_record["filename"]).stem + "_detected.jpg")
        if not orig_path.exists() and not out_path.exists():
            self.status.configure(text="Image file not found on disk.")
            return
        self.current_image = orig_path
        if orig_path.exists():
            self._show_image(orig_path)
        self._show_detected()
        self.stat_file.configure(text=img_record["filename"])
        self.stat_size.configure(text=f"{img_record['width_px']}x{img_record['height_px']}")
        self.stat_wins.configure(text=str(img_record["window_count"]))
        img_area = img_record["width_px"] * img_record["height_px"]
        self.current_image_id = img_record["id"]
        self._update_table(img_record["id"], img_area)
        dets = get_detections_for_image(img_record["id"])
        confs = [d["confidence"] for d in dets if d["class_name"].strip().lower() == "window"]
        self.stat_conf.configure(
            text=f"{sum(confs)/len(confs):.1%}" if confs else "-")
        self.status.configure(text=f"Loaded: {img_record['filename']}")
        self.tabs.set("Image")

    def _upload(self):
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
        self.stat_wins.configure(text="-")
        self.stat_conf.configure(text="-")
        self.detect_btn.configure(state="normal")
        self.status.configure(text="Image loaded - click Detect Windows")

    def _detect(self):
        self.progress.pack(padx=15, pady=(0,4), fill="x")
        self.progress.start()
        self.status.configure(text="Running detection...")
        threading.Thread(target=self._run_detection, daemon=True).start()

    def _run_detection(self):
        result = subprocess.run(
            [sys.executable, "detect.py", self.current_image.name],
            capture_output=True, text=True,
            cwd=Path(__file__).parent
        )
        self.after(0, self._on_detection_done, result.stdout)

    def _on_detection_done(self, output):
        self.progress.stop()
        self.progress.pack_forget()
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
            text=f"{sum(confs)/len(confs):.1f}%" if confs else "-")
        images = get_all_images()
        if images:
            latest = images[0]
            img = Image.open(self.current_image)
            self._update_table(latest["id"], img.width * img.height)
        self.status.configure(text="Detection complete")
        self._load_history()
        self._refresh_all_table()
        self._show_popup(len(wins))
        self.tabs.set("Detected")

    def _show_popup(self, window_count):
        popup = ctk.CTkToplevel(self)
        popup.title("Detection Complete")
        popup.geometry("280x160")
        popup.resizable(False, False)
        popup.grab_set()
        ctk.CTkLabel(popup, text="Detection Complete",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(30,8))
        ctk.CTkLabel(popup, text=f"{window_count} window(s) detected",
                     text_color="gray").pack()
        ctk.CTkButton(popup, text="OK", width=100,
                      command=popup.destroy).pack(pady=20)

    def _show_image(self, path):
        img = Image.open(path)
        img.thumbnail((920, 620))
        photo = ImageTk.PhotoImage(img)
        self.image_label.configure(image=photo, text="")
        self.image_label.image = photo

    def _show_detected(self):
        if self.current_image is None:
            return
        out_path = Path("outputs") / (self.current_image.stem + "_detected.jpg")
        if not out_path.exists():
            return
        img = Image.open(out_path)
        img.thumbnail((920, 620))
        photo = ImageTk.PhotoImage(img)
        self.detected_label.configure(image=photo, text="")
        self.detected_label.image = photo

    # ── DELETE METHODS ────────────────────────────────────────────────
    def _delete_current_image(self):
        if self.current_image is None:
            return
        popup = ctk.CTkToplevel(self)
        popup.title("Confirm Delete")
        popup.geometry("300x160")
        popup.resizable(False, False)
        popup.grab_set()
        ctk.CTkLabel(popup, text="Delete this image?",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(25,5))
        ctk.CTkLabel(popup, text="Removes image files and all its detections.",
                     text_color="gray", font=ctk.CTkFont(size=11)).pack()
        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Cancel", width=100,
                      fg_color="#2b2b2b", hover_color="#3b3b3b",
                      command=popup.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Delete", width=100,
                      fg_color="#8b0000", hover_color="#a00000",
                      command=lambda: self._confirm_delete_image(popup)).pack(side="left", padx=8)

    def _confirm_delete_image(self, popup):
        popup.destroy()
        conn = sqlite3.connect("detections.db")
        conn.row_factory = sqlite3.Row
        img_row = conn.execute("SELECT id FROM images WHERE filename = ?",
                               (self.current_image.name,)).fetchone()
        if img_row:
            conn.execute("DELETE FROM detections WHERE image_id = ?", (img_row["id"],))
            conn.execute("DELETE FROM images WHERE id = ?", (img_row["id"],))
            conn.commit()
        conn.close()
        orig = Path("uploads") / self.current_image.name
        out  = Path("outputs") / (self.current_image.stem + "_detected.jpg")
        if orig.exists(): orig.unlink()
        if out.exists():  out.unlink()
        self.current_image = None
        self.current_image_id = None
        self.image_label.configure(image="", text="Upload an image to get started")
        self.detected_label.configure(image="", text="No detected image yet")
        self.stat_file.configure(text="-")
        self.stat_size.configure(text="-")
        self.stat_wins.configure(text="-")
        self.stat_conf.configure(text="-")
        self.status.configure(text="Image deleted.")
        self._load_history()
        self._refresh_all_table()

    def _delete_current_detections(self):
        if self.current_image is None:
            return
        popup = ctk.CTkToplevel(self)
        popup.title("Confirm Delete")
        popup.geometry("300x170")
        popup.resizable(False, False)
        popup.grab_set()
        ctk.CTkLabel(popup, text="Delete detections for this image?",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(25,5))
        ctk.CTkLabel(popup, text="Image files are kept, only detection data is removed.",
                     text_color="gray", font=ctk.CTkFont(size=11),
                     wraplength=260).pack()
        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Cancel", width=100,
                      fg_color="#2b2b2b", hover_color="#3b3b3b",
                      command=popup.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Delete", width=100,
                      fg_color="#8b0000", hover_color="#a00000",
                      command=lambda: self._confirm_delete_detections(popup)).pack(side="left", padx=8)

    def _confirm_delete_detections(self, popup):
        popup.destroy()
        conn = sqlite3.connect("detections.db")
        conn.row_factory = sqlite3.Row
        img_row = conn.execute("SELECT id FROM images WHERE filename = ?",
                               (self.current_image.name,)).fetchone()
        if img_row:
            conn.execute("DELETE FROM detections WHERE image_id = ?", (img_row["id"],))
            conn.commit()
        conn.close()
        self.stat_wins.configure(text="0")
        self.stat_conf.configure(text="-")
        if img_row:
            self._update_table(img_row["id"], 1)
        self.status.configure(text="Detections deleted.")
        self._load_history()
        self._refresh_all_table()

    def _delete_all_detections(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Confirm Delete All")
        popup.geometry("300x160")
        popup.resizable(False, False)
        popup.grab_set()
        ctk.CTkLabel(popup, text="Delete ALL detections?",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(25,5))
        ctk.CTkLabel(popup, text="This clears every detection from every image.",
                     text_color="gray", font=ctk.CTkFont(size=11)).pack()
        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Cancel", width=100,
                      fg_color="#2b2b2b", hover_color="#3b3b3b",
                      command=popup.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Delete All", width=100,
                      fg_color="#8b0000", hover_color="#a00000",
                      command=lambda: self._confirm_delete_all(popup)).pack(side="left", padx=8)

    def _confirm_delete_all(self, popup):
        popup.destroy()
        conn = sqlite3.connect("detections.db")
        conn.execute("DELETE FROM detections")
        conn.commit()
        conn.close()
        self.stat_wins.configure(text="-")
        self.stat_conf.configure(text="-")
        self.status.configure(text="All detections deleted.")
        self._load_history()
        self._refresh_all_table()

    def _redraw_detected_image(self):
        if self.current_image is None:
            return
        import cv2
        import numpy as np
        from database import get_detections_for_image, get_all_images

        # find image_id
        conn = sqlite3.connect("detections.db")
        conn.row_factory = sqlite3.Row
        img_row = conn.execute("SELECT id, width_px, height_px FROM images WHERE filename = ?",
                              (self.current_image.name,)).fetchone()
        conn.close()
        if not img_row:
            return

        img = cv2.imread(str(self.current_image))
        if img is None:
            return

        dets = get_detections_for_image(img_row["id"])

        for det in dets:
            if det["class_name"].strip().lower() != "window":
                continue
            if not det["points"] if "points" in det.keys() else True:
                x1 = det["x"] - det["width"] // 2
                y1 = det["y"] - det["height"] // 2
                x2 = det["x"] + det["width"] // 2
                y2 = det["y"] + det["height"] // 2
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, f"Window {det['confidence']:.0%}",
                        (det["x"] - det["width"]//2, max(det["y"] - det["height"]//2 - 8, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        out_path = Path("outputs") / (self.current_image.stem + "_detected.jpg")
        cv2.imwrite(str(out_path), img)
        self._show_detected()

    def _delete_single_detection(self, detection_id, image_id, img_area):
        conn = sqlite3.connect("detections.db")
        conn.execute("DELETE FROM detections WHERE id = ?", (detection_id,))
        conn.commit()
        conn.close()

        self._update_table(image_id, img_area)
        self._refresh_all_table()
        self._load_history()

        # update stats
        dets = get_detections_for_image(image_id)
        wins = [d for d in dets if d["class_name"].strip().lower() == "window"]
        self.stat_wins.configure(text=str(len(wins)))
        confs = [d["confidence"] for d in wins]
        self.stat_conf.configure(
            text=f"{sum(confs)/len(confs):.1%}" if confs else "-")

        # redraw the annotated image
        self._redraw_detected_image()
        self.status.configure(text=f"Detection {detection_id} deleted.")


if __name__ == "__main__":
    app = App()
    app.mainloop()