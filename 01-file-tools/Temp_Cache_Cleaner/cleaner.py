# Author: github.com/clipcopy
# 10-27-26

"""
SWEEPVAULT - Advanced Temp & Cache Cleaner
-------------------------------------------
One file, no installs, Python 3.8+. Works on Windows, macOS and Linux.

Standout feature: REGRET-PROOF CLEANING (Undo Vault) + SAFETY GATE
  * Nothing is deleted straight away. Cleaned files are moved into a
    quarantine vault with a manifest, so you can UNDO a whole clean with
    one menu choice (files go back to their exact original paths).
  * The vault empties itself after a retention period (default 3 days).
  * A safety gate skips files modified recently (they may be in use),
    never follows symlinks, and never touches anything outside the
    known temp/cache folders.
  * "Scan" is always a dry run with a size heatmap, so you see what will
    happen before it happens.
"""

import json
import os
import platform
import shutil
import stat
import tempfile
import time
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------
# Settings (changeable from the menu while the program runs)
# ----------------------------------------------------------------------
VAULT = Path.home() / ".sweepvault"

settings = {
    "min_age_hours": 1,        # safety gate: skip files newer than this
    "mode": "quarantine",      # "quarantine" (undoable) or "permanent"
    "retention_days": 3,       # vault batches older than this are auto-purged
    "enabled": {},             # category name -> True/False (filled in main)
}

# ----------------------------------------------------------------------
# Colors and display helpers
# ----------------------------------------------------------------------
RESET, BOLD, CYAN, GREEN, YELLOW, RED, DIM = (
    "\033[0m", "\033[1m", "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[2m",
)

BANNER_ART = r"""
 ____ __        __ _____ _____ ____
/ ___|\ \      / /| ____| ____|  _ \
\___ \ \ \ /\ / / |  _| |  _| | |_) |
 ___) | \ V  V /  | |___| |___|  __/
|____/   \_/\_/   |_____|_____|_|
"""


def show_banner():
    print(CYAN + BOLD + BANNER_ART + RESET)
    print(f"{DIM}   VAULT  |  Temp & Cache Cleaner with Undo  |  github.com/clipcopy{RESET}\n")


def show_menu():
    mode = "undoable (quarantine)" if settings["mode"] == "quarantine" else "PERMANENT delete"
    print(f"{BOLD}  [1]{RESET} Scan (dry run, safe)     {BOLD}[4]{RESET} Vault (view / purge)")
    print(f"{BOLD}  [2]{RESET} Clean                    {BOLD}[5]{RESET} Settings")
    print(f"{BOLD}  [3]{RESET} Undo last clean          {BOLD}[0]{RESET} Exit")
    print(f"{DIM}  Mode: {mode} | safety gate: {settings['min_age_hours']}h | "
          f"vault keeps: {settings['retention_days']} days{RESET}\n")


def ask(prompt, default=None):
    """Ask for input; return the default when the user just presses Enter."""
    hint = f" [{default}]" if default is not None else ""
    answer = input(f"{CYAN}>{RESET} {prompt}{hint}: ").strip()
    return answer if answer else default


def ask_int(prompt, default, low, high):
    try:
        value = int(ask(prompt, default))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


def human_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:,.0f} {unit}" if unit == "B" else f"{size:,.1f} {unit}"
        size /= 1024


def bar(part, whole, width=24):
    """Text bar chart used for the junk heatmap."""
    filled = int(width * part / whole) if whole else 0
    return "#" * filled + "." * (width - filled)


# ----------------------------------------------------------------------
# Categories: where junk lives on each operating system
# ----------------------------------------------------------------------
def get_categories():
    """Return {name: {"roots": [paths], "match": function(path) -> bool}}."""
    home = Path.home()
    system = platform.system()
    always = lambda path: True
    cats = {"Temp files": {"roots": [Path(tempfile.gettempdir())], "match": always}}

    if system == "Windows":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        windir = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        cats["Windows temp"] = {"roots": [windir / "Temp"], "match": always}
        cats["Internet cache"] = {"roots": [local / "Microsoft/Windows/INetCache"], "match": always}
        cats["Browser cache"] = {"roots": [
            local / "Google/Chrome/User Data/Default/Cache",
            local / "Microsoft/Edge/User Data/Default/Cache",
        ], "match": always}
    elif system == "Darwin":
        cats["User cache"] = {"roots": [home / "Library/Caches"], "match": always}
        cats["User logs"] = {"roots": [home / "Library/Logs"], "match": always}
    else:
        cats["User cache"] = {"roots": [home / ".cache"], "match": always}

    cats["Python bytecode (this folder)"] = {
        "roots": [Path.cwd()],
        "match": lambda path: "__pycache__" in path.parts,
    }
    return cats


CATEGORIES = get_categories()


# ----------------------------------------------------------------------
# Scanner with safety gate
# ----------------------------------------------------------------------
def scan_category(category):
    """Return (files, protected_count). files = [(path, size), ...]"""
    cutoff = time.time() - settings["min_age_hours"] * 3600
    vault_text = str(VAULT)
    found, protected = [], 0

    for root in category["roots"]:
        if not root.is_dir():
            continue
        for folder, dirs, files in os.walk(root, followlinks=False):
            if folder.startswith(vault_text):          # never scan our own vault
                dirs[:] = []
                continue
            for name in files:
                path = Path(folder) / name
                try:
                    info = path.lstat()
                except OSError:
                    continue
                if not stat.S_ISREG(info.st_mode):     # skips symlinks and specials
                    continue
                if not category["match"](path):
                    continue
                if info.st_mtime > cutoff:             # safety gate: maybe in use
                    protected += 1
                    continue
                found.append((path, info.st_size))
    return found, protected


def scan_all():
    """Scan every enabled category. Returns {name: (files, protected)}."""
    results, seen = {}, set()
    for name, category in CATEGORIES.items():
        if not settings["enabled"].get(name, True):
            continue
        files, protected = scan_category(category)
        unique = [(p, s) for p, s in files if p not in seen]   # avoid double counting
        seen.update(p for p, _ in unique)
        results[name] = (unique, protected)
    return results


def show_report(results):
    """Print the heatmap report and return (total_files, total_bytes)."""
    total_files = sum(len(f) for f, _ in results.values())
    total_bytes = sum(s for f, _ in results.values() for _, s in f)
    biggest_category = max((sum(s for _, s in f) for f, _ in results.values()), default=0)

    print(f"\n  {BOLD}{'Category':<30} {'Files':>7} {'Size':>10}  Heatmap{RESET}")
    for name, (files, protected) in results.items():
        size = sum(s for _, s in files)
        note = f" {DIM}(+{protected} protected){RESET}" if protected else ""
        print(f"  {name:<30} {len(files):>7} {human_size(size):>10}  "
              f"{YELLOW}{bar(size, biggest_category)}{RESET}{note}")
    print(f"  {'-' * 62}")
    print(f"  {BOLD}{'TOTAL':<30} {total_files:>7} {human_size(total_bytes):>10}{RESET}")

    everything = [item for f, _ in results.values() for item in f]
    if everything:
        print(f"\n  {BOLD}Top 5 biggest files:{RESET}")
        for path, size in sorted(everything, key=lambda x: x[1], reverse=True)[:5]:
            print(f"   {human_size(size):>10}  {DIM}{str(path)[-60:]}{RESET}")
    print()
    return total_files, total_bytes


# ----------------------------------------------------------------------
# Vault (undo system)
# ----------------------------------------------------------------------
def list_batches():
    """Return [(batch_dir, manifest_dict)] newest first."""
    batches = []
    if VAULT.is_dir():
        for folder in sorted(VAULT.iterdir(), reverse=True):
            manifest_path = folder / "manifest.json"
            if manifest_path.is_file():
                try:
                    batches.append((folder, json.loads(manifest_path.read_text())))
                except (OSError, ValueError):
                    continue
    return batches


def batch_size(manifest):
    return sum(item["size"] for item in manifest["items"])


def auto_purge():
    """Delete vault batches older than the retention period."""
    limit = time.time() - settings["retention_days"] * 86400
    freed = count = 0
    for folder, manifest in list_batches():
        if manifest["created"] < limit:
            freed += batch_size(manifest)
            shutil.rmtree(folder, ignore_errors=True)
            count += 1
    if count:
        print(f"{DIM}  Auto-purged {count} old vault batch(es), freed {human_size(freed)}.{RESET}\n")


# ----------------------------------------------------------------------
# Cleaning engine
# ----------------------------------------------------------------------
def run_clean(results):
    """Quarantine or delete scanned files. Returns (done, failed, bytes_done)."""
    files = [item for f, _ in results.values() for item in f]
    done = failed = bytes_done = 0
    quarantine = settings["mode"] == "quarantine"
    manifest = {"created": time.time(), "items": []}

    if quarantine:
        batch_dir = VAULT / datetime.now().strftime("%Y%m%d-%H%M%S")
        (batch_dir / "files").mkdir(parents=True, exist_ok=True)

    for number, (path, size) in enumerate(files, start=1):
        try:
            if quarantine:
                stored = f"{number:06d}"
                shutil.move(str(path), str(batch_dir / "files" / stored))
                manifest["items"].append({"stored": stored, "original": str(path), "size": size})
            else:
                path.unlink()
            done += 1
            bytes_done += size
        except OSError:
            failed += 1                                  # locked or no permission: skip
        if number % 200 == 0:
            print(f"\r  Working... {number}/{len(files)}", end="", flush=True)
    print("\r" + " " * 40 + "\r", end="")

    if quarantine:
        if manifest["items"]:
            (batch_dir / "manifest.json").write_text(json.dumps(manifest))
        else:
            shutil.rmtree(batch_dir, ignore_errors=True)
    return done, failed, bytes_done


def restore_batch(folder, manifest):
    """Move every file in a batch back to its original path."""
    restored = skipped = 0
    remaining = []
    for item in manifest["items"]:
        original = Path(item["original"])
        stored = folder / "files" / item["stored"]
        if original.exists() or not stored.exists():
            skipped += 1
            remaining.append(item)
            continue
        try:
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(stored), str(original))
            restored += 1
        except OSError:
            skipped += 1
            remaining.append(item)

    if remaining:
        manifest["items"] = remaining
        (folder / "manifest.json").write_text(json.dumps(manifest))
    else:
        shutil.rmtree(folder, ignore_errors=True)
    return restored, skipped


# ----------------------------------------------------------------------
# Menu actions
# ----------------------------------------------------------------------
def action_scan():
    print(f"\n  {DIM}Scanning (nothing will be changed)...{RESET}")
    show_report(scan_all())


def action_clean():
    print(f"\n  {DIM}Scanning first...{RESET}")
    results = scan_all()
    total_files, total_bytes = show_report(results)
    if total_files == 0:
        print(f"  {GREEN}Nothing to clean. Your system is tidy.{RESET}\n")
        return

    if settings["mode"] == "permanent":
        print(f"  {RED}{BOLD}PERMANENT mode: files will be deleted and CANNOT be restored.{RESET}")
        if ask("Type DELETE to continue") != "DELETE":
            print(f"  {YELLOW}Cancelled.{RESET}\n")
            return
    else:
        question = f"Move {total_files} files ({human_size(total_bytes)}) to the undo vault? (y/n)"
        if not ask(question, "y").lower().startswith("y"):
            print(f"  {YELLOW}Cancelled.{RESET}\n")
            return

    done, failed, bytes_done = run_clean(results)
    print(f"  {GREEN}{BOLD}Done:{RESET} {done} files handled ({human_size(bytes_done)})"
          + (f", {YELLOW}{failed} skipped (in use or no permission){RESET}" if failed else ""))
    if settings["mode"] == "quarantine":
        print(f"  {DIM}Space is fully freed when the vault is purged "
              f"(auto after {settings['retention_days']} days, or from menu 4).")
        print(f"  Changed your mind? Choose [3] Undo last clean.{RESET}")
    print()


def action_undo():
    batches = list_batches()
    if not batches:
        print(f"\n  {YELLOW}The vault is empty, nothing to undo.{RESET}\n")
        return
    folder, manifest = batches[0]
    when = datetime.fromtimestamp(manifest["created"]).strftime("%Y-%m-%d %H:%M")
    print(f"\n  Latest clean: {when} | {len(manifest['items'])} files | {human_size(batch_size(manifest))}")
    if not ask("Restore these files to their original places? (y/n)", "y").lower().startswith("y"):
        print(f"  {YELLOW}Cancelled.{RESET}\n")
        return
    restored, skipped = restore_batch(folder, manifest)
    print(f"  {GREEN}{BOLD}Restored {restored} files.{RESET}"
          + (f" {YELLOW}{skipped} skipped (original path already exists).{RESET}" if skipped else "") + "\n")


def action_vault():
    batches = list_batches()
    if not batches:
        print(f"\n  {YELLOW}The vault is empty.{RESET}\n")
        return
    print(f"\n  {BOLD}Vault contents{RESET}")
    total = 0
    for folder, manifest in batches:
        when = datetime.fromtimestamp(manifest["created"]).strftime("%Y-%m-%d %H:%M")
        total += batch_size(manifest)
        print(f"   {when} | {len(manifest['items']):>6} files | {human_size(batch_size(manifest)):>10}")
    print(f"   {'-' * 40}\n   Total held: {BOLD}{human_size(total)}{RESET}\n")
    if ask("Permanently purge the whole vault? This frees the space. (y/n)", "n").lower().startswith("y"):
        for folder, _ in batches:
            shutil.rmtree(folder, ignore_errors=True)
        print(f"  {GREEN}Vault purged. {human_size(total)} freed.{RESET}\n")


def action_settings():
    print("\n  Press Enter to keep the current value.\n")
    settings["min_age_hours"] = ask_int("Safety gate: skip files newer than (hours, 0-720)",
                                        settings["min_age_hours"], 0, 720)
    mode = ask("Mode: [q]uarantine (undoable) or [p]ermanent", settings["mode"][0]).lower()
    settings["mode"] = "permanent" if mode.startswith("p") else "quarantine"
    settings["retention_days"] = ask_int("Vault keeps files for (days, 1-60)",
                                         settings["retention_days"], 1, 60)
    print("\n  Choose which categories to clean:")
    for name in CATEGORIES:
        current = "y" if settings["enabled"].get(name, True) else "n"
        settings["enabled"][name] = ask(f"{name} (y/n)", current).lower().startswith("y")
    print(f"  {GREEN}Settings saved.{RESET}\n")


ACTIONS = {
    "1": action_scan,
    "2": action_clean,
    "3": action_undo,
    "4": action_vault,
    "5": action_settings,
}


# ----------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------
def main():
    settings["enabled"] = {name: True for name in CATEGORIES}
    show_banner()
    auto_purge()
    while True:
        show_menu()
        choice = ask("Choose an option")
        if choice == "0":
            print(f"\n{CYAN}  Stay clean. Goodbye!{RESET}\n")
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