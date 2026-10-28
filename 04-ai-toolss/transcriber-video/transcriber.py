# Author: github.com/clipcopy
# 10-27-26

"""
VOICEVAULT - Advanced Audio/Video Transcriber
-------------------------------------------------
One file. Needs: pip install openai-whisper  (and ffmpeg on your PATH)
Optimized for CPU and low RAM (8GB). English/Tagalog auto-detect, plus
any language Whisper supports.

Standout feature: RESUMABLE BATCH RUNS + SUBTITLES WITH A CONFIDENCE MAP
  * Every finished file is remembered in a small progress log, so if a
    batch run is interrupted (or you add new files later) it picks up
    exactly where it left off instead of redoing work.
  * Besides a plain .txt transcript, it can export .srt / .vtt subtitles
    with real timestamps, and a confidence map that marks which segments
    Whisper was unsure about, so you know exactly which lines to double
    check by ear instead of proofreading the whole thing blind.
"""

import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")

# ----------------------------------------------------------------------
# Settings (changeable from the menu while the program runs)
# ----------------------------------------------------------------------
settings = {
    "model": "tiny",            # tiny / base / small / medium / large
    "beam_size": 5,              # 1 = fastest, 5 = more accurate
    "language": "auto",          # "auto" or a code like "en", "tl"
    "export": {"txt": True, "srt": False, "vtt": False},
}

PROGRESS_FILE = Path(".voicevault_progress.json")
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".mkv", ".mov", ".webm"}

# ----------------------------------------------------------------------
# Colors and display helpers
# ----------------------------------------------------------------------
RESET, BOLD, CYAN, GREEN, YELLOW, RED, DIM = (
    "\033[0m", "\033[1m", "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[2m",
)

BANNER_ART = r"""
__     __    _          __     __          _ _
\ \   / /__ (_) ___ ___ \ \   / /_ _ _   _| | |_
 \ \ / / _ \| |/ __/ _ \ \ \ / / _` | | | | | __|
  \ V / (_) | | (_|  __/  \ V / (_| | |_| | | |_
   \_/ \___/|_|\___\___|   \_/ \__,_|\__,_|_|\__|
"""


def show_banner():
    print(CYAN + BOLD + BANNER_ART + RESET)
    print(f"{DIM}   VOICEVAULT  |  Audio/Video Transcriber  |  github.com/clipcopy{RESET}\n")


def show_menu():
    exports = "+".join(name for name, on in settings["export"].items() if on) or "none"
    print(f"{BOLD}  [1]{RESET} Transcribe one file      {BOLD}[4]{RESET} View a saved transcript")
    print(f"{BOLD}  [2]{RESET} Transcribe a folder      {BOLD}[5]{RESET} Progress log")
    print(f"{BOLD}  [3]{RESET} Settings                 {BOLD}[0]{RESET} Exit")
    print(f"{DIM}  model={settings['model']} beam={settings['beam_size']} "
          f"lang={settings['language']} export={exports}{RESET}\n")


def ask(prompt, default=None):
    hint = f" [{default}]" if default is not None else ""
    answer = input(f"{CYAN}>{RESET} {prompt}{hint}: ").strip()
    return answer if answer else default


def ask_int(prompt, default, low, high):
    try:
        value = int(ask(prompt, default))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


def ask_choice(prompt, default, options):
    answer = (ask(f"{prompt} ({'/'.join(options)})", default) or default).lower()
    return answer if answer in options else default


# ----------------------------------------------------------------------
# Setup checks
# ----------------------------------------------------------------------
def check_ffmpeg():
    import shutil
    if shutil.which("ffmpeg") is None:
        print(f"\n  {RED}ffmpeg was not found on your PATH.{RESET}")
        print("   Windows: https://ffmpeg.org/download.html")
        print("   Linux:   sudo apt install ffmpeg")
        print("   macOS:   brew install ffmpeg\n")
        return False
    return True


def load_whisper():
    try:
        import whisper
        import torch
        return whisper, torch
    except ImportError:
        print(f"\n  {RED}openai-whisper is not installed.{RESET}")
        print("   Run: pip install openai-whisper\n")
        return None, None


# ----------------------------------------------------------------------
# Progress log (makes batch runs resumable)
# ----------------------------------------------------------------------
def load_progress():
    if PROGRESS_FILE.is_file():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except (OSError, ValueError):
            pass
    return {}


def save_progress(progress):
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


def file_signature(path):
    """Changes if the file is replaced, so a swapped file is retranscribed."""
    info = path.stat()
    return f"{info.st_size}-{int(info.st_mtime)}"


# ----------------------------------------------------------------------
# Transcription
# ----------------------------------------------------------------------
_model_cache = {}


def get_model(whisper, torch, name, threads):
    if name not in _model_cache:
        torch.set_num_threads(threads)
        print(f"  {DIM}Loading '{name}' model (first time only, this can take a moment)...{RESET}")
        _model_cache[name] = whisper.load_model(name)
    return _model_cache[name]


def transcribe_file(whisper, torch, path, threads):
    model = get_model(whisper, torch, settings["model"], threads)
    language = None if settings["language"] == "auto" else settings["language"]
    beam = settings["beam_size"]
    result = model.transcribe(
        str(path),
        language=language,
        task="transcribe",
        fp16=torch.cuda.is_available(),
        beam_size=beam,
        best_of=beam if beam > 1 else None,
        word_timestamps=False,
    )
    return result


# ----------------------------------------------------------------------
# Export formats
# ----------------------------------------------------------------------
def format_timestamp(seconds, comma=False):
    whole = int(seconds)
    hours, remainder = divmod(whole, 3600)
    minutes, secs = divmod(remainder, 60)
    millis = int((seconds - whole) * 1000)
    sep = "," if comma else "."
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{millis:03d}"


def write_txt(path, result):
    path.write_text(result["text"].strip() + "\n", encoding="utf-8")


def write_srt(path, result):
    lines = []
    for index, segment in enumerate(result["segments"], start=1):
        start = format_timestamp(segment["start"], comma=True)
        end = format_timestamp(segment["end"], comma=True)
        lines.append(f"{index}\n{start} --> {end}\n{segment['text'].strip()}\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_vtt(path, result):
    lines = ["WEBVTT\n"]
    for segment in result["segments"]:
        start = format_timestamp(segment["start"])
        end = format_timestamp(segment["end"])
        lines.append(f"{start} --> {end}\n{segment['text'].strip()}\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def confidence_map(result, low=-1.0):
    """Segments Whisper itself flagged as low-confidence (avg_logprob below 'low')."""
    return [s for s in result.get("segments", []) if s.get("avg_logprob", 0) < low]


def show_confidence_map(result):
    flagged = confidence_map(result)
    total = len(result.get("segments", []))
    if not total:
        return
    if not flagged:
        print(f"  {GREEN}Confidence map: all {total} segment(s) look solid.{RESET}")
        return
    print(f"  {YELLOW}Confidence map: {len(flagged)}/{total} segment(s) worth a double check:{RESET}")
    for segment in flagged[:6]:
        start = format_timestamp(segment["start"])
        print(f"   {DIM}{start}{RESET}  {segment['text'].strip()[:70]}")
    if len(flagged) > 6:
        print(f"   {DIM}...and {len(flagged) - 6} more{RESET}")


def export_all(path, result):
    written = []
    if settings["export"]["txt"]:
        write_txt(path.with_suffix(".txt"), result)
        written.append(path.with_suffix(".txt").name)
    if settings["export"]["srt"]:
        write_srt(path.with_suffix(".srt"), result)
        written.append(path.with_suffix(".srt").name)
    if settings["export"]["vtt"]:
        write_vtt(path.with_suffix(".vtt"), result)
        written.append(path.with_suffix(".vtt").name)
    return written


# ----------------------------------------------------------------------
# One-file and batch runners
# ----------------------------------------------------------------------
def run_one(whisper, torch, path, threads, progress):
    print(f"\n  {CYAN}Transcribing:{RESET} {path.name}")
    started = time.time()
    try:
        result = transcribe_file(whisper, torch, path, threads)
    except Exception as error:
        print(f"  {RED}Failed: {error}{RESET}")
        return False

    written = export_all(path, result)
    took = time.time() - started
    detected = result.get("language", "?")
    print(f"  {GREEN}Done in {took:.1f}s{RESET}  |  detected language: {detected}  |  saved: {', '.join(written)}")
    show_confidence_map(result)

    progress[str(path.resolve())] = {
        "signature": file_signature(path),
        "model": settings["model"],
        "when": time.strftime("%Y-%m-%d %H:%M"),
    }
    save_progress(progress)
    return True


def action_one():
    if not check_ffmpeg():
        return
    whisper, torch = load_whisper()
    if whisper is None:
        return
    raw = ask("Path to an audio or video file")
    if not raw:
        return
    path = Path(raw.strip('"\''))
    if not path.is_file():
        print(f"\n  {RED}File not found: {path}{RESET}\n")
        return
    progress = load_progress()
    run_one(whisper, torch, path, threads_auto(), progress)
    print()


def action_folder():
    if not check_ffmpeg():
        return
    whisper, torch = load_whisper()
    if whisper is None:
        return
    raw = ask("Folder to scan", ".")
    folder = Path(raw.strip('"\''))
    if not folder.is_dir():
        print(f"\n  {RED}Folder not found: {folder}{RESET}\n")
        return

    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in AUDIO_EXTS)
    if not files:
        print(f"\n  {YELLOW}No audio/video files found in {folder}{RESET}\n")
        return

    progress = load_progress()
    todo, done_already = [], 0
    for path in files:
        record = progress.get(str(path.resolve()))
        if record and record["signature"] == file_signature(path) and record["model"] == settings["model"]:
            done_already += 1
        else:
            todo.append(path)

    print(f"\n  {len(files)} file(s) found | {done_already} already done (skipping) | {len(todo)} to process")
    if not todo:
        print(f"  {GREEN}Nothing left to do.{RESET}\n")
        return
    if not ask(f"Process {len(todo)} file(s) now? (y/n)", "y").lower().startswith("y"):
        print(f"  {YELLOW}Cancelled.{RESET}\n")
        return

    threads = threads_auto()
    ok = failed = 0
    for index, path in enumerate(todo, 1):
        print(f"\n  {DIM}[{index}/{len(todo)}]{RESET}", end="")
        if run_one(whisper, torch, path, threads, progress):
            ok += 1
        else:
            failed += 1

    print(f"\n  {BOLD}Batch complete:{RESET} {GREEN}{ok} done{RESET}"
          + (f", {RED}{failed} failed{RESET}" if failed else "")
          + f", {done_already} skipped (already done)\n")


def threads_auto():
    import os
    return os.cpu_count() or 2


def action_view():
    raw = ask("Path to a .txt / .srt / .vtt transcript")
    if not raw:
        return
    path = Path(raw.strip('"\''))
    if not path.is_file():
        print(f"\n  {RED}File not found: {path}{RESET}\n")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    print(f"\n  {DIM}--- {path.name} ---{RESET}")
    print(text[:3000] + ("\n  [...truncated...]" if len(text) > 3000 else ""))
    print()


def action_log():
    progress = load_progress()
    if not progress:
        print(f"\n  {YELLOW}No files transcribed yet.{RESET}\n")
        return
    print(f"\n  {BOLD}{'File':<45} {'Model':<8} When{RESET}")
    for path, record in progress.items():
        name = Path(path).name
        print(f"  {name[:43]:<45} {record['model']:<8} {record['when']}")
    print(f"\n  {len(progress)} file(s) in the log.")
    if ask("Clear the log? (y/n)", "n").lower().startswith("y"):
        PROGRESS_FILE.unlink(missing_ok=True)
        print(f"  {GREEN}Log cleared. Next run will retranscribe everything.{RESET}")
    print()


def action_settings():
    print("\n  Press Enter to keep the current value.\n")
    settings["model"] = ask_choice("Model", settings["model"], ["tiny", "base", "small", "medium", "large"])
    settings["beam_size"] = ask_int("Beam size (1=fastest, 10=most accurate)", settings["beam_size"], 1, 10)
    lang = ask("Language code, or 'auto' to detect (e.g. en, tl)", settings["language"])
    settings["language"] = lang.lower()
    print("\n  Export formats:")
    for key, label in (("txt", "Plain text (.txt)"), ("srt", "Subtitles (.srt)"), ("vtt", "Subtitles (.vtt)")):
        current = "y" if settings["export"][key] else "n"
        settings["export"][key] = ask(label, current).lower().startswith("y")
    if not any(settings["export"].values()):
        settings["export"]["txt"] = True
        print(f"  {YELLOW}At least one export format is required. .txt re-enabled.{RESET}")
    print(f"  {GREEN}Settings saved.{RESET}\n")


ACTIONS = {
    "1": action_one,
    "2": action_folder,
    "3": action_settings,
    "4": action_view,
    "5": action_log,
}


# ----------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------
def main():
    show_banner()
    while True:
        show_menu()
        choice = ask("Choose an option")
        if choice == "0":
            print(f"\n{CYAN}  Goodbye!{RESET}\n")
            break
        action = ACTIONS.get(choice)
        if action is None:
            print(f"{RED}  Invalid choice, try again.{RESET}\n")
            continue
        action()
        input(f"{DIM}  Press Enter to continue...{RESET}")
        print("\n" + "=" * 62 + "\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{CYAN}  Goodbye!{RESET}\n")