POMODORO TIMER - Day 9
Version 1.0
Author: clipcopy

==========================================================
DESCRIPTION
==========================================================
A desktop Pomodoro timer for focused work. It alternates
focus sessions with short and long breaks, logs every
session to a CSV file, and shows today's progress.

Built with Python's standard library only (tkinter).
No installation of extra packages is needed.


==========================================================
REQUIREMENTS
==========================================================
- Python 3.8 or newer
- tkinter (included with the standard Python installer on
  Windows and macOS; on Linux install it with your package
  manager, e.g. "sudo apt install python3-tk")
- Works on Windows, macOS, and Linux


==========================================================
FILES
==========================================================
pomodoro_timer_day9.py   The application (single file)
README.txt               This file


==========================================================
HOW TO RUN
==========================================================
1. Open a terminal or Command Prompt.
2. Go to the folder that contains the file:
       cd path\to\folder            (Windows)
       cd path/to/folder            (macOS / Linux)
3. Start the program:
       python pomodoro_timer_day9.py
   (On some systems use "python3" instead of "python".)


==========================================================
FIRST-TIME SETUP
==========================================================
Open pomodoro_timer_day9.py in any text editor and change
this line near the top of the file:

       AUTHOR = "Your Name"

to your own name. The name appears in the About dialog.


==========================================================
HOW TO USE
==========================================================
1. Type what you are working on in the task box (optional).
2. Press Start (or Space) to begin a focus session.
3. When the timer reaches zero, a sound plays and the window
   comes to the front.
4. Press Start (or Space) to begin the next session.

The cycle works like this (default settings):
   Focus -> Short break -> Focus -> Short break ->
   Focus -> Short break -> Focus -> Long break -> repeat

Buttons:
   Start / Pause   Starts the timer, or pauses it while running
   Skip            Ends the current session early and moves
                   to the next one. A skipped focus session
                   is logged as "skipped".
   Reset           Stops the timer and returns to the start
                   of the current session.
   Settings        Change session lengths and options
   Open Log        Opens the folder that holds your data
   About           Shows version, author, and file locations


==========================================================
KEYBOARD SHORTCUTS
==========================================================
   Space   Start or pause
   R       Reset
   S       Skip
   Enter   Save (inside the Settings window)
   Esc     Close the Settings window

Shortcuts are disabled while you are typing in the task box.


==========================================================
SETTINGS
==========================================================
   Focus length                 1 - 180 minutes   (default 25)
   Short break                  1 - 60 minutes    (default 5)
   Long break                   1 - 120 minutes   (default 15)
   Focus sessions before        1 - 12            (default 4)
     long break
   Start next session           on / off          (default off)
     automatically
   Play alert sound             on / off          (default on)
   Keep window always on top    on / off          (default off)

Use "Defaults" in the Settings window to restore the
original values.


==========================================================
DATA AND FILES
==========================================================
All data is stored in a folder named "pomodoro_data" in
your home directory:

   Windows:  C:\Users\<your name>\pomodoro_data
   macOS:    /Users/<your name>/pomodoro_data
   Linux:    /home/<your name>/pomodoro_data

Files inside that folder:

   sessions.csv     Log of every session. Columns:
                    date, start_time, end_time, type,
                    task, minutes, status
                    (status is "completed" or "skipped")

   settings.json    Your saved settings.

   error_log.txt    Created only if an error happens. Useful
                    for troubleshooting.

You can open sessions.csv in Excel, Google Sheets, or any
spreadsheet program.


==========================================================
TROUBLESHOOTING
==========================================================
"tkinter is required" message
   Your Python installation does not include tkinter.
   Reinstall Python from python.org and tick the Tcl/Tk
   option, or on Linux install python3-tk.

No sound on Linux
   The program uses the system bell. Make sure the terminal
   bell or system sounds are enabled.

Settings will not save
   Check that your home folder is writable. Details are
   written to pomodoro_data/error_log.txt.

Timer seems to pause when the window is minimized
   This is normal on some systems that slow background
   windows. The timer uses the real clock, so the correct
   time is shown as soon as the window is restored.


==========================================================
LIMITATIONS
==========================================================
- The alert sound on macOS and Linux is the system bell,
  which may be quiet or disabled on some systems.
- Session history is kept only in the CSV file. There is
  no built-in statistics chart.


==========================================================
LICENSE
==========================================================
Free to use, copy, modify, and share for personal and
educational purposes.


==========================================================
VERSION HISTORY
==========================================================
1.0   First release. Focus and break cycle, task name,
      progress ring, session log, settings, keyboard
      shortcuts, and alert sound.