import csv
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image, ImageOps
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
LIVE_DATA_FILE = PROJECT_ROOT / "live_data.json"
LIVE_FRAME_FILE = PROJECT_ROOT / "live_frame.jpg"
FATIGUE_LOG_FILE = PROJECT_ROOT / "fatigue_log.csv"
SETTINGS_FILE = PROJECT_ROOT / "settings.json"
EXPORT_DIR = PROJECT_ROOT / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------
# Appearance
# ------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ------------------------------------------------------------
# Runtime state
# ------------------------------------------------------------
process = None
score_history = []
last_log_key = None
refresh_ms = 500

DEFAULT_SETTINGS = {
    "pilot_id": "AI-102",
    "flight": "AI-202",
    "aircraft": "Boeing 787",
    "route": "Mumbai → Delhi",
    "departure": "08:30",
    "arrival": "10:45",
    "refresh_ms": 500
}


def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
                saved = json.load(file)
            return {**DEFAULT_SETTINGS, **saved}
        except (OSError, json.JSONDecodeError):
            pass
    return DEFAULT_SETTINGS.copy()


settings_data = load_settings()
refresh_ms = int(settings_data.get("refresh_ms", 500))


def save_settings(data):
    global settings_data, refresh_ms
    settings_data = {**DEFAULT_SETTINGS, **data}
    refresh_ms = max(200, int(settings_data["refresh_ms"]))
    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(settings_data, file, indent=4)

    pilot_label.configure(text=f"Pilot ID : {settings_data['pilot_id']}")
    flight_label.configure(text=f"Flight : {settings_data['flight']}")
    aircraft_label.configure(text=f"Aircraft : {settings_data['aircraft']}")
    route_label.configure(text=f"Route : {settings_data['route']}")
    departure_label.configure(text=f"Departure : {settings_data['departure']}")
    arrival_label.configure(text=f"Arrival : {settings_data['arrival']}")


# ------------------------------------------------------------
# Main window
# ------------------------------------------------------------
app = ctk.CTk()
app.title("AI Pilot Fatigue Control Room")
app.geometry("1600x900")
app.minsize(1200, 760)


def on_close():
    stop_monitoring()
    app.destroy()


app.protocol("WM_DELETE_WINDOW", on_close)

# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
header = ctk.CTkFrame(app, height=70, corner_radius=10)
header.pack(fill="x", padx=10, pady=(10, 5))

title = ctk.CTkLabel(
    header,
    text="AI PILOT FATIGUE MONITORING SYSTEM",
    font=("Arial", 28, "bold")
)
title.pack(side="left", padx=20, pady=15)

status = ctk.CTkLabel(
    header,
    text="● CONTROL ROOM ONLINE",
    font=("Arial", 18, "bold"),
    text_color="lightgreen"
)
status.pack(side="right", padx=20)

# ------------------------------------------------------------
# Main layout
# ------------------------------------------------------------
main_frame = ctk.CTkFrame(app, fg_color="transparent")
main_frame.pack(fill="both", expand=True, padx=10, pady=5)

main_frame.grid_columnconfigure(0, weight=6, uniform="top")
main_frame.grid_columnconfigure(1, weight=4, uniform="top")
main_frame.grid_rowconfigure(0, weight=7)
main_frame.grid_rowconfigure(1, weight=3)

# ============================================================
# LIVE CAMERA
# ============================================================
camera_panel = ctk.CTkFrame(main_frame)
camera_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)
camera_panel.grid_rowconfigure(1, weight=1)
camera_panel.grid_columnconfigure(0, weight=1)

camera_title = ctk.CTkLabel(
    camera_panel,
    text="LIVE AI CAMERA",
    font=("Arial", 22, "bold")
)
camera_title.grid(row=0, column=0, pady=10)

camera_label = ctk.CTkLabel(
    camera_panel,
    text="Waiting for AI Camera...",
    fg_color="#111111",
    corner_radius=8
)
camera_label.grid(
    row=1, column=0, sticky="nsew",
    padx=15, pady=(0, 15)
)

# ============================================================
# RIGHT COLUMN
# ============================================================
right_panel = ctk.CTkFrame(main_frame)
right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)
right_panel.grid_columnconfigure(0, weight=1)
right_panel.grid_rowconfigure(0, weight=3)
right_panel.grid_rowconfigure(1, weight=3)
right_panel.grid_rowconfigure(2, weight=4)

# Pilot status
status_panel = ctk.CTkFrame(right_panel)
status_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

ctk.CTkLabel(
    status_panel, text="PILOT STATUS",
    font=("Arial", 22, "bold")
).pack(pady=(14, 8))

eyes_label = ctk.CTkLabel(status_panel, text="Eyes : ---", font=("Arial", 16))
eyes_label.pack(anchor="w", padx=20, pady=4)
head_label = ctk.CTkLabel(status_panel, text="Head : ---", font=("Arial", 16))
head_label.pack(anchor="w", padx=20, pady=4)
blink_label = ctk.CTkLabel(status_panel, text="Blinks : 0", font=("Arial", 16))
blink_label.pack(anchor="w", padx=20, pady=4)
yawn_label = ctk.CTkLabel(status_panel, text="Yawns : 0", font=("Arial", 16))
yawn_label.pack(anchor="w", padx=20, pady=4)
score_label = ctk.CTkLabel(
    status_panel, text="Fatigue Score : 0", font=("Arial", 16)
)
score_label.pack(anchor="w", padx=20, pady=4)
state_label = ctk.CTkLabel(status_panel, text="Status : ---", font=("Arial", 16))
state_label.pack(anchor="w", padx=20, pady=4)
session_label = ctk.CTkLabel(status_panel, text="Session : 0 s", font=("Arial", 16))
session_label.pack(anchor="w", padx=20, pady=4)

# Flight information
flight_panel = ctk.CTkFrame(right_panel)
flight_panel.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

ctk.CTkLabel(
    flight_panel, text="FLIGHT INFORMATION",
    font=("Arial", 22, "bold")
).pack(pady=(14, 8))

pilot_label = ctk.CTkLabel(flight_panel, text="")
pilot_label.pack(anchor="w", padx=20, pady=4)
flight_label = ctk.CTkLabel(flight_panel, text="")
flight_label.pack(anchor="w", padx=20, pady=4)
aircraft_label = ctk.CTkLabel(flight_panel, text="")
aircraft_label.pack(anchor="w", padx=20, pady=4)
route_label = ctk.CTkLabel(flight_panel, text="")
route_label.pack(anchor="w", padx=20, pady=4)
departure_label = ctk.CTkLabel(flight_panel, text="")
departure_label.pack(anchor="w", padx=20, pady=4)
arrival_label = ctk.CTkLabel(flight_panel, text="")
arrival_label.pack(anchor="w", padx=20, pady=4)

# Live graph
graph_panel = ctk.CTkFrame(right_panel)
graph_panel.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
graph_panel.grid_rowconfigure(1, weight=1)
graph_panel.grid_columnconfigure(0, weight=1)

ctk.CTkLabel(
    graph_panel, text="LIVE FATIGUE GRAPH",
    font=("Arial", 20, "bold")
).grid(row=0, column=0, pady=(10, 2))

figure = Figure(figsize=(5.5, 2.4), dpi=90)
figure.patch.set_facecolor("#2b2b2b")
ax = figure.add_subplot(111)
ax.set_facecolor("#202020")
ax.set_ylim(0, 100)
ax.set_xlabel("Recent samples")
ax.set_ylabel("Score")
ax.grid(alpha=0.2)

graph_canvas = FigureCanvasTkAgg(figure, master=graph_panel)
graph_canvas.get_tk_widget().grid(
    row=1, column=0, sticky="nsew", padx=10, pady=(0, 10)
)

# ============================================================
# BOTTOM: LOGS + LIVE STATISTICS + BUTTONS
# ============================================================
bottom_panel = ctk.CTkFrame(main_frame)
bottom_panel.grid(
    row=1, column=0, columnspan=2,
    sticky="nsew", padx=0, pady=(5, 0)
)
bottom_panel.grid_columnconfigure(0, weight=3)
bottom_panel.grid_columnconfigure(1, weight=2)
bottom_panel.grid_rowconfigure(0, weight=1)
bottom_panel.grid_rowconfigure(1, weight=0)

# Logs
logs_panel = ctk.CTkFrame(bottom_panel)
logs_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)
logs_panel.grid_rowconfigure(1, weight=1)
logs_panel.grid_columnconfigure(0, weight=1)

ctk.CTkLabel(
    logs_panel, text="SYSTEM LOGS",
    font=("Arial", 20, "bold")
).grid(row=0, column=0, pady=8)

logs_box = ctk.CTkTextbox(logs_panel, height=120)
logs_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
logs_box.insert("end", f"{datetime.now().strftime('%H:%M:%S')}  Control Room Started\n")
logs_box.configure(state="disabled")

# Statistics
stats_panel = ctk.CTkFrame(bottom_panel)
stats_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)
stats_panel.grid_columnconfigure(0, weight=1)
stats_panel.grid_columnconfigure(1, weight=1)

ctk.CTkLabel(
    stats_panel, text="LIVE STATISTICS",
    font=("Arial", 20, "bold")
).grid(row=0, column=0, columnspan=2, pady=8)

blink_rate_label = ctk.CTkLabel(stats_panel, text="Blink Rate : --/min")
blink_rate_label.grid(row=1, column=0, sticky="w", padx=15, pady=3)
yawn_rate_label = ctk.CTkLabel(stats_panel, text="Yawn Rate : --/hr")
yawn_rate_label.grid(row=1, column=1, sticky="w", padx=15, pady=3)
avg_score_label = ctk.CTkLabel(stats_panel, text="Average Score : --")
avg_score_label.grid(row=2, column=0, sticky="w", padx=15, pady=3)
max_score_label = ctk.CTkLabel(stats_panel, text="Maximum Score : --")
max_score_label.grid(row=2, column=1, sticky="w", padx=15, pady=3)
fps_label = ctk.CTkLabel(stats_panel, text="Camera FPS : --")
fps_label.grid(row=3, column=0, sticky="w", padx=15, pady=3)

# Buttons
buttons_frame = ctk.CTkFrame(bottom_panel, fg_color="transparent")
buttons_frame.grid(
    row=1, column=0, columnspan=2,
    sticky="ew", padx=0, pady=(2, 5)
)

for i in range(7):
    buttons_frame.grid_columnconfigure(i, weight=1)

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def add_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    logs_box.configure(state="normal")
    logs_box.insert("end", f"{timestamp}  {message}\n")
    logs_box.see("end")
    logs_box.configure(state="disabled")


def update_camera():
    if LIVE_FRAME_FILE.exists():
        try:
            with Image.open(LIVE_FRAME_FILE) as source:
                image = source.convert("RGB")
                width = max(camera_label.winfo_width() - 20, 320)
                height = max(camera_label.winfo_height() - 20, 240)
                fitted = ImageOps.contain(image, (width, height))
                ctk_image = ctk.CTkImage(
                    light_image=fitted,
                    dark_image=fitted,
                    size=fitted.size
                )
                camera_label.configure(image=ctk_image, text="")
                camera_label.image = ctk_image
        except (OSError, ValueError):
            pass

    app.after(100, update_camera)


def update_statistics(data):
    try:
        session_seconds = max(float(data.get("session_time", 0)), 1)
        blinks = int(data.get("blinks", 0))
        yawns = int(data.get("yawns", 0))

        blink_rate = blinks * 60 / session_seconds
        yawn_rate = yawns * 3600 / session_seconds

        blink_rate_label.configure(text=f"Blink Rate : {blink_rate:.1f}/min")
        yawn_rate_label.configure(text=f"Yawn Rate : {yawn_rate:.1f}/hr")

        if score_history:
            avg_score_label.configure(
                text=f"Average Score : {sum(score_history)/len(score_history):.1f}"
            )
            max_score_label.configure(
                text=f"Maximum Score : {max(score_history)}"
            )

        fps_label.configure(text="Camera FPS : ~30")
    except (TypeError, ValueError, ZeroDivisionError):
        pass


def update_dashboard():
    global last_log_key

    if LIVE_DATA_FILE.exists():
        try:
            with open(LIVE_DATA_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)

            eyes = data.get("eyes", "---")
            head = data.get("head", "---")
            blinks = int(data.get("blinks", 0))
            yawns = int(data.get("yawns", 0))
            score = int(data.get("fatigue_score", 0))
            state = data.get("status", "---")
            session_time = int(data.get("session_time", 0))

            eyes_label.configure(text=f"Eyes : {eyes}")
            head_label.configure(text=f"Head : {head}")
            blink_label.configure(text=f"Blinks : {blinks}")
            yawn_label.configure(text=f"Yawns : {yawns}")
            score_label.configure(text=f"Fatigue Score : {score}")
            state_label.configure(text=f"Status : {state}")
            session_label.configure(text=f"Session : {session_time} s")

            if score_history and score == score_history[-1]:
                pass
            else:
                score_history.append(score)

            if len(score_history) > 60:
                score_history.pop(0)

            ax.clear()
            ax.set_facecolor("#202020")
            ax.plot(score_history, linewidth=2.5)
            ax.set_ylim(0, 100)
            ax.set_xlabel("Recent samples")
            ax.set_ylabel("Score")
            ax.set_title("Fatigue Score", color="white")
            ax.grid(alpha=0.2)
            graph_canvas.draw_idle()

            if score >= 70:
                state_label.configure(text_color="#ff4d4d")
            elif score >= 40:
                state_label.configure(text_color="#ffb020")
            else:
                state_label.configure(text_color="#65e765")

            log_key = (data.get("timestamp"), state, score)
            if log_key != last_log_key:
                add_log(f"AI Status: {state} | Score: {score}")
                last_log_key = log_key

            update_statistics(data)

        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

    app.after(refresh_ms, update_dashboard)


# ------------------------------------------------------------
# Monitoring controls
# ------------------------------------------------------------
def start_monitoring():
    global process

    if process is not None and process.poll() is None:
        add_log("Monitoring is already running.")
        return

    try:
        process = subprocess.Popen(
            [sys.executable, str(PROJECT_ROOT / "detection" / "eye_detection.py")],
            cwd=str(PROJECT_ROOT)
        )
        status.configure(text="● MONITORING ACTIVE", text_color="#65e765")
        add_log("AI Camera started.")
    except OSError as error:
        messagebox.showerror("Start Error", f"Could not start camera:\n{error}")


def stop_monitoring():
    global process

    if process is None:
        add_log("Monitoring is already stopped.")
        return

    try:
        process.terminate()
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
    except OSError:
        pass
    finally:
        process = None

    status.configure(text="● CONTROL ROOM ONLINE", text_color="lightgreen")
    add_log("AI Camera stopped.")


def reset_dashboard():
    global last_log_key

    score_history.clear()
    last_log_key = None
    ax.clear()
    ax.set_facecolor("#202020")
    ax.set_ylim(0, 100)
    ax.set_xlabel("Recent samples")
    ax.set_ylabel("Score")
    ax.grid(alpha=0.2)
    graph_canvas.draw_idle()

    logs_box.configure(state="normal")
    logs_box.delete("1.0", "end")
    logs_box.configure(state="disabled")

    blink_rate_label.configure(text="Blink Rate : --/min")
    yawn_rate_label.configure(text="Yawn Rate : --/hr")
    avg_score_label.configure(text="Average Score : --")
    max_score_label.configure(text="Maximum Score : --")
    add_log("Dashboard view reset.")


def open_csv():
    # Make the button an actual export operation.
    EXPORT_DIR.mkdir(exist_ok=True)
    target = EXPORT_DIR / f"fatigue_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    if FATIGUE_LOG_FILE.exists():
        shutil.copy2(FATIGUE_LOG_FILE, target)
    else:
        with open(target, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Date", "Session Time", "Blink Count", "Yawns", "Fatigue Score"])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d"),
                "Current session",
                blink_label.cget("text").replace("Blinks : ", ""),
                yawn_label.cget("text").replace("Yawns : ", ""),
                score_label.cget("text").replace("Fatigue Score : ", "")
            ])

    try:
        os.startfile(EXPORT_DIR)
    except AttributeError:
        pass

    add_log(f"CSV exported: {target.name}")
    messagebox.showinfo("CSV Export", f"CSV exported successfully:\n{target}")


def export_pdf():
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ImportError:
        messagebox.showerror(
            "PDF Export",
            "ReportLab is not installed.\n\n"
            "Run:\n"
            "pip install reportlab"
        )
        return

    target = EXPORT_DIR / f"fatigue_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    current = {
        "eyes": eyes_label.cget("text").replace("Eyes : ", ""),
        "head": head_label.cget("text").replace("Head : ", ""),
        "blinks": blink_label.cget("text").replace("Blinks : ", ""),
        "yawns": yawn_label.cget("text").replace("Yawns : ", ""),
        "score": score_label.cget("text").replace("Fatigue Score : ", ""),
        "status": state_label.cget("text").replace("Status : ", ""),
        "session": session_label.cget("text").replace("Session : ", "")
    }

    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()
    story = [
        Paragraph("AI Pilot Fatigue Monitoring System", styles["Title"]),
        Paragraph("Control Room Session Report", styles["Heading2"]),
        Spacer(1, 8),
        Paragraph(
            f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
            styles["Normal"]
        ),
        Spacer(1, 12),
    ]

    flight_data = [
        ["Flight Information", "Value"],
        ["Pilot ID", settings_data["pilot_id"]],
        ["Flight", settings_data["flight"]],
        ["Aircraft", settings_data["aircraft"]],
        ["Route", settings_data["route"]],
        ["Departure", settings_data["departure"]],
        ["Arrival", settings_data["arrival"]],
    ]

    status_data = [
        ["Pilot Monitoring", "Current Value"],
        ["Eyes", current["eyes"]],
        ["Head", current["head"]],
        ["Blinks", current["blinks"]],
        ["Yawns", current["yawns"]],
        ["Fatigue Score", current["score"]],
        ["Status", current["status"]],
        ["Session", current["session"]],
    ]

    for table_data in (flight_data, status_data):
        table = Table(table_data, colWidths=[65 * mm, 105 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E4057")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

    story.append(Paragraph(
        "This report contains monitoring values captured by the local control-room dashboard. "
        "The runtime camera image is intentionally not embedded in the exported report.",
        styles["Normal"]
    ))

    doc.build(story)
    add_log(f"PDF exported: {target.name}")
    messagebox.showinfo("PDF Export", f"PDF exported successfully:\n{target}")


def settings():
    global refresh_ms

    window = ctk.CTkToplevel(app)
    window.title("Control Room Settings")
    window.geometry("500x560")
    window.resizable(False, False)
    window.grab_set()

    ctk.CTkLabel(
        window,
        text="CONTROL ROOM SETTINGS",
        font=("Arial", 22, "bold")
    ).pack(pady=18)

    fields = [
        ("Pilot ID", "pilot_id"),
        ("Flight", "flight"),
        ("Aircraft", "aircraft"),
        ("Route", "route"),
        ("Departure", "departure"),
        ("Arrival", "arrival"),
        ("Refresh interval (ms)", "refresh_ms"),
    ]

    entries = {}

    for label_text, key in fields:
        row = ctk.CTkFrame(window, fg_color="transparent")
        row.pack(fill="x", padx=25, pady=5)

        ctk.CTkLabel(
            row, text=label_text, width=170, anchor="w"
        ).pack(side="left")

        entry = ctk.CTkEntry(row, width=250)
        entry.insert(0, str(settings_data.get(key, DEFAULT_SETTINGS[key])))
        entry.pack(side="right")
        entries[key] = entry

    def apply():
        try:
            data = {key: entry.get().strip() for key, entry in entries.items()}
            data["refresh_ms"] = max(200, int(data["refresh_ms"]))
        except ValueError:
            messagebox.showerror(
                "Settings",
                "Refresh interval must be a whole number (minimum 200 ms).",
                parent=window
            )
            return

        save_settings(data)
        add_log("Settings updated.")
        window.destroy()

    ctk.CTkButton(
        window,
        text="SAVE & APPLY",
        command=apply,
        height=40
    ).pack(pady=20)

    ctk.CTkButton(
        window,
        text="CANCEL",
        fg_color="#555555",
        command=window.destroy,
        height=35
    ).pack()

# ------------------------------------------------------------
# Buttons
# ------------------------------------------------------------
buttons = [
    ("▶ START", start_monitoring, "#2E8B57"),
    ("⏹ STOP", stop_monitoring, "#D97706"),
    ("↻ RESET", reset_dashboard, "#1F6AA5"),
    ("▣ EXPORT PDF", export_pdf, "#1F6AA5"),
    ("▤ EXPORT CSV", open_csv, "#1F6AA5"),
    ("⚙ SETTINGS", settings, "#1F6AA5"),
    ("✕ EXIT", on_close, "#B22222"),
]

for index, (text, command, color) in enumerate(buttons):
    ctk.CTkButton(
        buttons_frame,
        text=text,
        command=command,
        height=34,
        fg_color=color,
        hover_color=color
    ).grid(row=0, column=index, sticky="ew", padx=5, pady=5)

# Apply saved flight information to the labels.
save_settings(settings_data)

update_camera()
update_dashboard()
app.mainloop()
