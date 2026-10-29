#!/usr/bin/env python3
"""
Pomodoro Timer - Day 9
Author: Your Name  (change AUTHOR below)
Version: 1.0

A complete Pomodoro timer built with Python's standard library only (tkinter).
Works on Windows, macOS and Linux.

Features:
  - Focus / short break / long break cycle (fully configurable)
  - Start, pause, resume, reset and skip
  - Task name for each focus session
  - Circular progress ring and live countdown
  - Session log saved to CSV, plus today's statistics
  - Settings saved between runs
  - Keyboard shortcuts: Space = start/pause, R = reset, S = skip
  - Audible and visual alert when a session ends
  - Optional auto-start of the next session, optional always-on-top
  - Errors are logged to a file instead of crashing the app
"""

import csv
import datetime
import json
import math
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    print("This program needs tkinter, which comes with the standard Python installer.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Author and app information
# ---------------------------------------------------------------------------
AUTHOR = "Your Name"
APP_NAME = "Pomodoro Timer"
VERSION = "1.0"

# ---------------------------------------------------------------------------
# Storage locations
# ---------------------------------------------------------------------------
DATA_DIR = Path.home() / "pomodoro_data"
SETTINGS_FILE = DATA_DIR / "settings.json"
LOG_FILE = DATA_DIR / "sessions.csv"
ERROR_FILE = DATA_DIR / "error_log.txt"

LOG_HEADERS = ["date", "start_time", "end_time", "type", "task", "minutes", "status"]

# ---------------------------------------------------------------------------
# Defaults, limits and modes
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "work_min": 25,
    "short_break_min": 5,
    "long_break_min": 15,
    "sessions_before_long": 4,
    "auto_start_next": False,
    "sound": True,
    "always_on_top": False,
}

LIMITS = {
    "work_min": (1, 180),
    "short_break_min": (1, 60),
    "long_break_min": (1, 120),
    "sessions_before_long": (1, 12),
}

WORK, SHORT, LONG = "work", "short", "long"
MODE_LABELS = {WORK: "Focus", SHORT: "Short Break", LONG: "Long Break"}
MODE_COLORS = {WORK: "#e74c3c", SHORT: "#2ecc71", LONG: "#3498db"}

BG = "#1e1e2e"
PANEL = "#2a2a3d"
FG = "#f5f5f5"
MUTED = "#9aa0a6"
TRACK = "#3a3a52"
BUTTON = "#3d3d5c"
BUTTON_HOVER = "#4f4f75"


# ---------------------------------------------------------------------------
# Helpers: errors, settings, session log, statistics
# ---------------------------------------------------------------------------
def ensure_data_dir():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def log_error(message):
    """Write an error to the error log. Never raises."""
    try:
        ensure_data_dir()
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(ERROR_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {message}\n")
    except Exception:
        pass


def load_settings():
    """Load settings, falling back to defaults for anything missing or invalid."""
    settings = dict(DEFAULT_SETTINGS)
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, default in DEFAULT_SETTINGS.items():
                if key not in data:
                    continue
                value = data[key]
                if isinstance(default, bool):
                    settings[key] = bool(value)
                else:
                    low, high = LIMITS[key]
                    settings[key] = min(max(int(value), low), high)
    except Exception as e:
        log_error(f"Could not read settings, using defaults: {e}")
        settings = dict(DEFAULT_SETTINGS)
    return settings


def save_settings(settings):
    try:
        ensure_data_dir()
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        log_error(f"Could not save settings: {e}")
        return False


def append_session(mode, start_dt, end_dt, task, minutes, status):
    """Append one row to the session log CSV."""
    try:
        ensure_data_dir()
        is_new = not LOG_FILE.exists()
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow(LOG_HEADERS)
            writer.writerow([
                start_dt.strftime("%Y-%m-%d"),
                start_dt.strftime("%H:%M:%S"),
                end_dt.strftime("%H:%M:%S"),
                mode,
                task,
                round(minutes, 2),
                status,
            ])
    except Exception as e:
        log_error(f"Could not write session log: {e}")


def today_stats():
    """Return (completed focus sessions today, focus minutes today)."""
    count, minutes_total = 0, 0.0
    today = datetime.date.today().strftime("%Y-%m-%d")
    try:
        if LOG_FILE.exists():
            with open(LOG_FILE, "r", newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if (row.get("date") == today and row.get("type") == WORK
                            and row.get("status") == "completed"):
                        count += 1
                        minutes_total += float(row.get("minutes") or 0)
    except Exception as e:
        log_error(f"Could not read session log: {e}")
    return count, minutes_total


def format_clock(seconds):
    seconds = max(0, int(math.ceil(seconds)))
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def make_button(parent, text, command, width=12):
    btn = tk.Button(parent, text=text, command=command, width=width,
                    bg=BUTTON, fg=FG, activebackground=BUTTON_HOVER,
                    activeforeground=FG, relief="flat", cursor="hand2",
                    font=("Segoe UI", 10, "bold"), bd=0, pady=6)
    btn.bind("<Enter>", lambda e: btn.config(bg=BUTTON_HOVER))
    btn.bind("<Leave>", lambda e: btn.config(bg=BUTTON))
    return btn


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, settings, on_save):
        super().__init__(parent)
        self.title("Settings")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.on_save = on_save
        self.vars = {}

        body = tk.Frame(self, bg=BG, padx=20, pady=16)
        body.pack(fill="both", expand=True)

        number_fields = [
            ("work_min", "Focus length (minutes)"),
            ("short_break_min", "Short break (minutes)"),
            ("long_break_min", "Long break (minutes)"),
            ("sessions_before_long", "Focus sessions before long break"),
        ]
        for row, (key, label) in enumerate(number_fields):
            tk.Label(body, text=label, bg=BG, fg=FG, anchor="w").grid(
                row=row, column=0, sticky="w", pady=6, padx=(0, 16))
            var = tk.StringVar(value=str(settings[key]))
            tk.Entry(body, textvariable=var, width=8, bg=PANEL, fg=FG,
                     insertbackground=FG, relief="flat", justify="center").grid(
                row=row, column=1, pady=6)
            self.vars[key] = var

        toggles = [
            ("auto_start_next", "Start next session automatically"),
            ("sound", "Play alert sound"),
            ("always_on_top", "Keep window always on top"),
        ]
        start_row = len(number_fields)
        for i, (key, label) in enumerate(toggles):
            var = tk.BooleanVar(value=settings[key])
            tk.Checkbutton(body, text=label, variable=var, bg=BG, fg=FG,
                           selectcolor=PANEL, activebackground=BG,
                           activeforeground=FG, highlightthickness=0).grid(
                row=start_row + i, column=0, columnspan=2, sticky="w", pady=4)
            self.vars[key] = var

        buttons = tk.Frame(body, bg=BG)
        buttons.grid(row=start_row + len(toggles), column=0, columnspan=2, pady=(16, 0))
        make_button(buttons, "Save", self.save).pack(side="left", padx=6)
        make_button(buttons, "Cancel", self.destroy).pack(side="left", padx=6)
        make_button(buttons, "Defaults", self.reset_defaults).pack(side="left", padx=6)

        self.bind("<Return>", lambda e: self.save())
        self.bind("<Escape>", lambda e: self.destroy())

    def reset_defaults(self):
        for key, value in DEFAULT_SETTINGS.items():
            if isinstance(value, bool):
                self.vars[key].set(value)
            else:
                self.vars[key].set(str(value))

    def save(self):
        new_settings = {}
        for key, default in DEFAULT_SETTINGS.items():
            if isinstance(default, bool):
                new_settings[key] = bool(self.vars[key].get())
                continue
            low, high = LIMITS[key]
            raw = self.vars[key].get().strip()
            try:
                value = int(raw)
            except ValueError:
                messagebox.showerror("Invalid value",
                                     f"Please enter a whole number for '{key.replace('_', ' ')}'.",
                                     parent=self)
                return
            if not low <= value <= high:
                messagebox.showerror("Out of range",
                                     f"'{key.replace('_', ' ')}' must be between {low} and {high}.",
                                     parent=self)
                return
            new_settings[key] = value
        self.on_save(new_settings)
        self.destroy()


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class PomodoroApp(tk.Tk):
    CANVAS_SIZE = 260
    RING_WIDTH = 14
    TICK_MS = 200

    def __init__(self):
        super().__init__()
        self.settings = load_settings()

        self.title(f"{APP_NAME} v{VERSION}")
        self.configure(bg=BG)
        self.geometry("420x700")
        self.minsize(380, 640)
        self.attributes("-topmost", self.settings["always_on_top"])

        # Timer state
        self.mode = WORK
        self.cycle_count = 0          # focus sessions completed since last long break
        self.running = False
        self.remaining = None         # seconds left when paused; None = not started
        self.end_time = 0.0           # monotonic deadline while running
        self.session_start = None     # datetime when current session began
        self.after_id = None
        self.total_sessions_today, self.minutes_today = today_stats()

        self.task_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")

        self.build_ui()
        self.bind_keys()
        self.refresh_display()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ----- UI construction -------------------------------------------------
    def build_ui(self):
        tk.Label(self, text=APP_NAME, bg=BG, fg=FG,
                 font=("Segoe UI", 16, "bold")).pack(pady=(18, 4))

        self.mode_label = tk.Label(self, text="", bg=BG, fg=MODE_COLORS[WORK],
                                   font=("Segoe UI", 12, "bold"))
        self.mode_label.pack()

        self.canvas = tk.Canvas(self, width=self.CANVAS_SIZE, height=self.CANVAS_SIZE,
                                bg=BG, highlightthickness=0)
        self.canvas.pack(pady=10)

        task_frame = tk.Frame(self, bg=BG)
        task_frame.pack(fill="x", padx=40, pady=(4, 2))
        tk.Label(task_frame, text="What are you working on?", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")
        self.task_entry = tk.Entry(task_frame, textvariable=self.task_var, bg=PANEL,
                                   fg=FG, insertbackground=FG, relief="flat",
                                   font=("Segoe UI", 11), justify="center")
        self.task_entry.pack(fill="x", ipady=6, pady=(4, 0))

        controls = tk.Frame(self, bg=BG)
        controls.pack(pady=14)
        self.start_btn = make_button(controls, "Start", self.toggle_timer)
        self.start_btn.grid(row=0, column=0, padx=5)
        make_button(controls, "Skip", self.skip).grid(row=0, column=1, padx=5)
        make_button(controls, "Reset", self.reset).grid(row=0, column=2, padx=5)

        self.stats_label = tk.Label(self, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10))
        self.stats_label.pack(pady=(4, 0))

        self.cycle_label = tk.Label(self, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.cycle_label.pack()

        footer = tk.Frame(self, bg=BG)
        footer.pack(side="bottom", fill="x", pady=10)
        make_button(footer, "Settings", self.open_settings, width=10).pack(side="left", padx=(20, 4))
        make_button(footer, "Open Log", self.open_log_folder, width=10).pack(side="left", padx=4)
        make_button(footer, "About", self.show_about, width=10).pack(side="left", padx=4)

        tk.Label(self, textvariable=self.status_var, bg=PANEL, fg=MUTED, anchor="w",
                 font=("Segoe UI", 9), padx=10).pack(side="bottom", fill="x", ipady=4)

    def bind_keys(self):
        for key, handler in (("space", self._key_toggle), ("r", self._key_reset),
                             ("R", self._key_reset), ("s", self._key_skip), ("S", self._key_skip)):
            self.bind(f"<{key}>", handler)

    def _typing_in_entry(self):
        return self.focus_get() is self.task_entry

    def _key_toggle(self, event=None):
        if not self._typing_in_entry():
            self.toggle_timer()
            return "break"

    def _key_reset(self, event=None):
        if not self._typing_in_entry():
            self.reset()
            return "break"

    def _key_skip(self, event=None):
        if not self._typing_in_entry():
            self.skip()
            return "break"

    # ----- Timer logic -----------------------------------------------------
    def duration_for(self, mode):
        key = {WORK: "work_min", SHORT: "short_break_min", LONG: "long_break_min"}[mode]
        return self.settings[key] * 60

    def elapsed_seconds(self):
        """Seconds already spent in the current session."""
        total = self.duration_for(self.mode)
        return total - self.seconds_left()

    def seconds_left(self):
        if self.running:
            return max(0.0, self.end_time - time.monotonic())
        if self.remaining is not None:
            return self.remaining
        return float(self.duration_for(self.mode))

    def toggle_timer(self):
        if self.running:
            self.pause()
        else:
            self.start()

    def start(self):
        if self.running:
            return
        try:
            if self.remaining is None:
                self.session_start = datetime.datetime.now()
                self.remaining = float(self.duration_for(self.mode))
            self.end_time = time.monotonic() + self.remaining
            self.running = True
            self.set_status(f"{MODE_LABELS[self.mode]} in progress")
            self.schedule_tick()
            self.refresh_display()
        except Exception as e:
            log_error(f"start failed: {e}\n{traceback.format_exc()}")

    def pause(self):
        if not self.running:
            return
        self.remaining = self.seconds_left()
        self.running = False
        self.cancel_tick()
        self.set_status("Paused")
        self.refresh_display()

    def reset(self):
        self.cancel_tick()
        self.running = False
        self.remaining = None
        self.session_start = None
        self.set_status("Timer reset")
        self.refresh_display()

    def skip(self):
        """Leave the current session early. A focus session skipped is logged as 'skipped'."""
        try:
            if self.mode == WORK and self.session_start is not None:
                elapsed_min = self.elapsed_seconds() / 60
                if elapsed_min > 0:
                    append_session(WORK, self.session_start, datetime.datetime.now(),
                                   self.task_var.get().strip(), elapsed_min, "skipped")
            self.cancel_tick()
            self.running = False
            self.advance_mode(completed_work=False)
            self.set_status(f"Skipped to {MODE_LABELS[self.mode]}")
            self.refresh_display()
        except Exception as e:
            log_error(f"skip failed: {e}\n{traceback.format_exc()}")

    def schedule_tick(self):
        self.cancel_tick()
        self.after_id = self.after(self.TICK_MS, self.tick)

    def cancel_tick(self):
        if self.after_id is not None:
            try:
                self.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def tick(self):
        self.after_id = None
        if not self.running:
            return
        try:
            if self.seconds_left() <= 0:
                self.session_finished()
            else:
                self.refresh_display()
                self.schedule_tick()
        except Exception as e:
            log_error(f"tick failed: {e}\n{traceback.format_exc()}")
            self.schedule_tick()

    def session_finished(self):
        self.cancel_tick()
        self.running = False
        finished_mode = self.mode
        end_dt = datetime.datetime.now()
        minutes = self.duration_for(finished_mode) / 60
        start_dt = self.session_start or (end_dt - datetime.timedelta(minutes=minutes))
        append_session(finished_mode, start_dt, end_dt, self.task_var.get().strip(),
                       minutes, "completed")

        if finished_mode == WORK:
            self.total_sessions_today += 1
            self.minutes_today += minutes

        self.advance_mode(completed_work=(finished_mode == WORK))
        self.notify(finished_mode)

        if self.settings["auto_start_next"]:
            self.start()
        else:
            self.set_status(f"{MODE_LABELS[finished_mode]} finished. Press Start for "
                            f"{MODE_LABELS[self.mode]}.")
            self.refresh_display()

    def advance_mode(self, completed_work):
        if completed_work:
            self.cycle_count += 1
            if self.cycle_count >= self.settings["sessions_before_long"]:
                self.mode = LONG
                self.cycle_count = 0
            else:
                self.mode = SHORT
        else:
            # Finished or skipped break -> back to focus.
            # Skipped focus -> go to a break (does not count toward the cycle).
            self.mode = SHORT if self.mode == WORK else WORK
        self.remaining = None
        self.session_start = None

    def notify(self, finished_mode):
        if self.settings["sound"]:
            try:
                if sys.platform.startswith("win"):
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                else:
                    for _ in range(3):
                        self.bell()
            except Exception as e:
                log_error(f"sound failed: {e}")
        headline = ("Focus done! Time for a break." if finished_mode == WORK
                    else "Break over. Back to focus.")
        self.title(f"{headline} - {APP_NAME}")
        self.after(4000, lambda: self.title(f"{APP_NAME} v{VERSION}"))
        try:
            self.deiconify()
            self.lift()
        except Exception:
            pass

    # ----- Display ---------------------------------------------------------
    def refresh_display(self):
        try:
            total = self.duration_for(self.mode)
            remaining = self.seconds_left()
            fraction = max(0.0, min(1.0, remaining / total)) if total else 0.0
            color = MODE_COLORS[self.mode]

            self.mode_label.config(text=MODE_LABELS[self.mode], fg=color)
            self.canvas.delete("all")
            pad = self.RING_WIDTH
            box = (pad, pad, self.CANVAS_SIZE - pad, self.CANVAS_SIZE - pad)
            self.canvas.create_oval(*box, outline=TRACK, width=self.RING_WIDTH)
            if fraction > 0:
                self.canvas.create_arc(*box, start=90, extent=-360 * fraction,
                                       style="arc", outline=color, width=self.RING_WIDTH)
            center = self.CANVAS_SIZE / 2
            self.canvas.create_text(center, center - 8, text=format_clock(remaining),
                                    fill=FG, font=("Segoe UI", 38, "bold"))
            if self.running:
                state = "RUNNING"
            elif self.remaining is not None:
                state = "PAUSED"
            else:
                state = "READY"
            self.canvas.create_text(center, center + 36, text=state, fill=MUTED,
                                    font=("Segoe UI", 9, "bold"))

            self.start_btn.config(text="Pause" if self.running else "Start")
            self.stats_label.config(
                text=f"Today: {self.total_sessions_today} focus session(s), "
                     f"{self.minutes_today:.0f} min focused")
            in_cycle = self.cycle_count + (1 if self.mode == WORK else 0)
            self.cycle_label.config(
                text=f"Focus {in_cycle} of {self.settings['sessions_before_long']} "
                     f"before long break")
        except Exception as e:
            log_error(f"refresh failed: {e}\n{traceback.format_exc()}")

    def set_status(self, text):
        self.status_var.set(text)

    # ----- Dialogs and menu actions ----------------------------------------
    def open_settings(self):
        SettingsDialog(self, self.settings, self.apply_settings)

    def apply_settings(self, new_settings):
        self.settings = new_settings
        save_settings(new_settings)
        self.attributes("-topmost", new_settings["always_on_top"])
        if not self.running and self.remaining is None:
            self.refresh_display()
        self.set_status("Settings saved")

    def open_log_folder(self):
        ensure_data_dir()
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(DATA_DIR))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(DATA_DIR)])
            else:
                subprocess.Popen(["xdg-open", str(DATA_DIR)])
        except Exception as e:
            log_error(f"open folder failed: {e}")
            messagebox.showinfo("Data location", f"Session log is saved at:\n{LOG_FILE}",
                                parent=self)

    def show_about(self):
        messagebox.showinfo(
            "About",
            f"{APP_NAME} v{VERSION}\n\nAuthor: {AUTHOR}\n\n"
            f"Session log: {LOG_FILE}\nSettings: {SETTINGS_FILE}",
            parent=self)

    def on_close(self):
        if self.running:
            if not messagebox.askyesno("Quit", "A session is running. Quit anyway?", parent=self):
                return
        self.cancel_tick()
        self.destroy()


def main():
    try:
        app = PomodoroApp()
        app.mainloop()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log_error(f"fatal: {e}\n{traceback.format_exc()}")
        print(f"Fatal error: {e}. Details were written to {ERROR_FILE}")
        sys.exit(1)


if __name__ == "__main__":
    main()