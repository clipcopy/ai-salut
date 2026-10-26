# Author: github.com/clipcopy
# 10-26-26


import os
import sys
import csv
import time
import hashlib
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# CONFIG & COLORS
# ==========================================
CHUNK_SIZE = 8192
HASH_ALGO = 'sha256'
DEFAULT_EXCLUDES = ['.git', '__pycache__', 'node_modules', '.venv', 'venv']

if os.name == 'nt':
    os.system('color')

class C:
    HEADER = '\033[95m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# ==========================================
# HELPERS
# ==========================================
def human_size(b):
    if b == 0: return "0B"
    names = ("B", "KB", "MB", "GB", "TB", "PB")
    i = 0
    while b >= 1024 and i < len(names) - 1:
        b /= 1024.0
        i += 1
    return f"{b:.2f} {names[i]}"

def get_hash(filepath):
    h = hashlib.new(HASH_ALGO)
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

# ==========================================
# CORE LOGIC
# ==========================================
def scan_and_hash(base_path, excludes, min_size):
    size_map = defaultdict(list)
    total_files = 0

    print(f"\n{C.OKCYAN}Scanning {base_path}...{C.ENDC}")
    
    # 1. Group by size first
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in excludes]
        for f in files:
            if f in excludes: continue
            fp = os.path.join(root, f)
            try:
                sz = os.path.getsize(fp)
                if sz >= min_size:
                    size_map[sz].append(fp)
                    total_files += 1
                    if total_files % 100 == 0:
                        sys.stdout.write(f"\rFiles found: {total_files}")
                        sys.stdout.flush()
            except OSError:
                pass
                
    print(f"\rFiles found: {total_files}")
    
    # Filter out unique sizes
    candidates = {sz: fps for sz, fps in size_map.items() if len(fps) > 1}
    
    if not candidates:
        return {}, total_files

    print(f"{C.OKCYAN}Hashing {sum(len(v) for v in candidates.values())} candidates...{C.ENDC}")
    
    # 2. Hash only candidates
    duplicates = {}
    def process_group(fps):
        local_dupes = defaultdict(list)
        for fp in fps:
            h = get_hash(fp)
            if h:
                local_dupes[h].append(fp)
        return local_dupes

    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        results = pool.map(process_group, candidates.values())
        
    for res in results:
        for h, fps in res.items():
            if len(fps) > 1:
                duplicates[h] = fps
                
    return duplicates, total_files

# ==========================================
# REPORTS & ACTIONS
# ==========================================
def save_reports(dupes, total, wasted, base_name):
    txt_file = f"{base_name}.txt"
    csv_file = f"{base_name}.csv"
    
    # TXT
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(f"Total Scanned: {total}\n")
        f.write(f"Duplicate Groups: {len(dupes)}\n")
        f.write(f"Space Wasted: {human_size(wasted)}\n\n")
        for idx, (h, fps) in enumerate(dupes.items(), 1):
            f.write(f"--- Group {idx} ---\n")
            for fp in fps:
                f.write(f"{fp} ({human_size(os.path.getsize(fp))})\n")
            f.write("\n")
            
    # CSV
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Group', 'Hash', 'Path', 'Size', 'Readable Size'])
        for idx, (h, fps) in enumerate(dupes.items(), 1):
            for fp in fps:
                sz = os.path.getsize(fp)
                w.writerow([idx, h, fp, sz, human_size(sz)])
                
    print(f"{C.OKGREEN}[+] Reports saved: {txt_file} & {csv_file}{C.ENDC}")

def interactive_delete(dupes):
    print(f"\n{C.WARNING}--- INTERACTIVE DELETION ---{C.ENDC}")
    for idx, (h, fps) in enumerate(dupes.items(), 1):
        print(f"\nGroup {idx} ({len(fps)} files):")
        for i, fp in enumerate(fps, 1):
            print(f"  [{i}] {fp}")
            
        choice = input(f"Keep which? (1-{len(fps)}) [Enter to skip]: ").strip()
        if not choice: continue
        
        try:
            keep = int(choice) - 1
            if 0 <= keep < len(fps):
                for i, fp in enumerate(fps):
                    if i != keep:
                        os.remove(fp)
                        print(f"  {C.FAIL}Deleted: {fp}{C.ENDC}")
                print(f"  {C.OKGREEN}Kept: {fps[keep]}{C.ENDC}")
        except ValueError:
            print("Invalid input. Skipping.")

# ==========================================
# MAIN
# ==========================================
def main():
    print(f"{C.HEADER}{C.BOLD}=== Duplicate File Finder ==={C.ENDC}\n")
    
    # Ask for path
    path_input = input(f"{C.OKCYAN}Enter the folder path to scan: {C.ENDC}").strip()
    
    # Clean up quotes if user drag-and-dropped a folder into CMD
    if path_input.startswith('"') and path_input.endswith('"'):
        path_input = path_input[1:-1]
        
    if not os.path.isdir(path_input):
        print(f"{C.FAIL}[-] Error: The path '{path_input}' does not exist or is not a directory.{C.ENDC}")
        return

    # Ask for reports
    output_name = input(f"{C.OKCYAN}Enter report name (default: dupes_report): {C.ENDC}").strip()
    if not output_name:
        output_name = "dupes_report"

    # Ask for interactive delete
    do_delete = input(f"{C.OKCYAN}Enable interactive deletion? (y/N): {C.ENDC}").strip().lower()

    # Run Scan
    dupes, total = scan_and_hash(path_input, DEFAULT_EXCLUDES, 0)

    if not dupes:
        print(f"{C.OKGREEN}No duplicates found.{C.ENDC}")
        return

    wasted = sum(os.path.getsize(fps[0]) * (len(fps) - 1) for fps in dupes.values())
    
    print(f"\n{C.HEADER}=== Summary ==={C.ENDC}")
    print(f"Total Files:   {total}")
    print(f"Groups Found:  {len(dupes)}")
    print(f"Space Wasted:  {C.WARNING}{human_size(wasted)}{C.ENDC}")

    save_reports(dupes, total, wasted, output_name)

    if do_delete == 'y':
        interactive_delete(dupes)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.FAIL}Cancelled.{C.ENDC}")
        sys.exit(1)