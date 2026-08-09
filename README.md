# AI Pilot Fatigue and Attention Monitoring System

An AI/computer-vision based prototype for monitoring pilot fatigue indicators from a webcam and presenting the results in a control-room dashboard.

## 1. Python version

Use **Python 3.10.x** for the most predictable setup with the current MediaPipe/OpenCV code.

Check your version:

```powershell
python --version
```

You should see Python 3.10.x.

## 2. Create a virtual environment

From the project root:

### Windows PowerShell

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can run the interpreter directly:

```powershell
venv\Scripts\python.exe --version
```

## 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The main libraries are:

- Python
- OpenCV
- MediaPipe
- NumPy
- CustomTkinter
- Pillow
- Matplotlib
- ReportLab

## 4. Run the Control Room Dashboard

From the project root:

```powershell
python control_room_dashboard.py
```

Then click **START** in the dashboard.

The dashboard starts `detection/eye_detection.py` using the same Python interpreter that launched the dashboard, so the virtual environment is used consistently.

## 5. Stop the system

Click **STOP**, or close the dashboard with **EXIT**.

The detection program also supports `q` to stop the OpenCV camera window.

## 6. What the system records

During monitoring, the detector continuously creates `live_data.json` for the dashboard.

Example structure:

```json
{
    "timestamp": "2026-08-08T21:30:45+05:30",
    "session_time": 120,
    "eyes": "OPEN",
    "head": "STRAIGHT",
    "blinks": 6,
    "yawns": 1,
    "fatigue_score": 20,
    "status": "ACTIVE"
}
```

The timestamp uses **ISO 8601**, which is a standard date/time representation.

At the end of a monitoring session, `fatigue_log.csv` is updated with the session summary.

These runtime files are intentionally ignored by Git because they are generated data.

## 7. Control Room buttons

- **START** – starts the AI camera/detection process.
- **STOP** – stops the detection process.
- **RESET** – clears the dashboard graph, logs and live statistics view.
- **EXPORT PDF** – creates a session report in the `exports/` folder.
- **EXPORT CSV** – creates a timestamped CSV export in the `exports/` folder.
- **SETTINGS** – opens editable pilot/flight information and dashboard refresh settings.
- **EXIT** – stops monitoring and closes the control room.

## 8. Project structure

```text
pilot-fatigue-project(new)/
│
├── control_room_dashboard.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── detection/
│   ├── eye_detection.py
│   ├── face_detection.py
│   ├── landmark_detection.py
│   └── webcam_test.py
│
└── logic/
    ├── __init__.py
    ├── alert_system.py
    ├── fatigue_logic.py
    ├── face_metrics.py
    └── timer_system.py
```

## 9. Code organisation

`calculate_mar()` is stored once in:

```text
logic/face_metrics.py
```

Both `eye_detection.py` and `landmark_detection.py` import this shared function instead of maintaining duplicate implementations.

## 10. Privacy / public repository

The runtime `live_frame.jpg` file is not part of the repository. It is generated locally while the dashboard is running and is ignored by Git.

Do not commit personal photographs, addresses, phone numbers, private logs or other personally identifiable information to a public repository.

## 11. Notes

This is a software prototype intended for academic/internship demonstration. It should not be treated as an aviation-certified safety system without extensive validation, testing and certification work.
