# Window Detector

A Python desktop app that detects physical windows in building photos using AI, stores results in a SQLite database, and displays everything in a modern dark GUI.

> **Repo:** https://github.com/Fresh03/Windows-AI-Detector

---

## What it does

- Upload a building photo
- Sends it to a Roboflow segmentation model (detects Window / Wood / Plastic)
- Draws polygon overlays on detected windows
- Saves results to a local SQLite database
- Displays detection history and stats in a CustomTkinter GUI

---

## Requirements

- Python 3.11
- A [Roboflow](https://roboflow.com) account with access to the `general-segmentation-api` workflow

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Fresh03/Windows-AI-Detector.git
cd Windows-AI-Detector
```

### 2. Create and activate a virtual environment

```bash
py -3.11 -m venv venv
venv\Scripts\Activate.ps1   # Windows PowerShell
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your API key

Create a `.env` file in the root folder:

```
ROBOFLOW_API_KEY=your_key_here
```

You can find your API key in your [Roboflow dashboard](https://app.roboflow.com) under Settings → API Keys.

---

## Run the app

```bash
python gui.py
```

---

## Project structure

```
├── detect.py         ← detection logic (calls Roboflow, draws polygons)
├── database.py       ← SQLite operations
├── gui.py            ← CustomTkinter GUI
├── query.py          ← terminal DB viewer
├── requirements.txt
├── .env.example      ← template for your API key (copy to .env)
├── .env              ← your API key (not committed)
├── uploads/          ← original images (auto-created)
└── outputs/          ← annotated images (auto-created)
```

The `uploads/`, `outputs/`, and `detections.db` are created automatically on first run.

---

## Tuning

In `detect.py` you can adjust:

| Variable | Default | Effect |
|---|---|---|
| `MIN_CONFIDENCE` | `0.60` | Lower = catches more, Higher = stricter |
| `MIN_WIDTH` / `MIN_HEIGHT` | `20` | Filters out tiny noise detections |
| `overlap_threshold` | `0.5` | Controls nested window filtering |

---

## Tech stack

- [Roboflow inference-sdk](https://github.com/roboflow/inference) — hosted AI model
- [OpenCV](https://opencv.org/) — polygon drawing
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — dark modern GUI
- [SQLite](https://www.sqlite.org/) — local database
- [python-dotenv](https://github.com/theskumar/python-dotenv) — API key management
