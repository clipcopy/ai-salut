# Author: github.com/clipcopy
# 10-26-26

import argparse
import os
import sys
import shutil
from concurrent.futures import ThreadPoolExecutor

from .scanner import Scanner
from .hasher import Hasher
from .reporter import Reporter
from .config import Colors, HASH_ALGO

def print_summary(duplicates, total_files, wasted_space):
    print(f"\n{Colors.HEADER}=== Scan Complete ==={Colors.ENDC}")
    print(f"Total Files Scanned: {total_files}")
    print(f"Duplicate Groups:    {len(duplicates)}")
    print(f"Space Wasted:        {Colors.WARNING}{wasted_space}{Colors.ENDC}\n")

def interactive_delete(duplicates, hasher):
    print(f"\n{Colors.WARNING}INTERACTIVE DELETION MODE{Colors.ENDC}")
    for idx, (hash_val, files) in enumerate(duplicates.items(), 1):
        print(f"\nGroup {idx} - {len(files)} copies:")
        for i, file in enumerate(files, 1):
            print(f"  [{i}] {file}")
        
        choice = input(f"Keep which file? (1-{len(files)}) [Enter to skip]: ").strip()
        if not choice:
            continue
            
        try:
            keep_idx = int(choice) - 1
            if keep_idx < 0 or keep_idx >= len(files):
                print("Invalid selection. Skipping group.")
                continue
            
            for i, file in enumerate(files):
                if i != keep_idx:
                    os.remove(file)
                    print(f"  {Colors.FAIL}Deleted: {file}{Colors.ENDC}")
            print(f"  {Colors.OKGREEN}Kept: {files[keep_idx]}{Colors.ENDC}")
            
        except ValueError:
            print("Invalid input. Skipping group.")

def main():
    parser = argparse.ArgumentParser(description="Duplicate File Finder Tool")
    parser.add_argument("paths", nargs="+", help="Directory paths to scan")
    parser.add_argument("-o", "--output", default="duplicate_report", help="Output filename (no extension)")
    parser.add_argument("--min-size", type=int, default=0, help="Minimum file size in bytes")
    parser.add_argument("--max-size", type=int, default=None, help="Maximum file size in bytes")
    parser.add_argument("--interactive", action="store_true", help="Interactively select files to delete")
    parser.add_argument("--delete-all", action="store_true", help="Auto-delete all but the oldest duplicate")
    
    args = parser.parse_args()

    # 1. Scan
    print(f"{Colors.OKCYAN}Scanning directories...{Colors.ENDC}")
    scanner = Scanner(args.paths, min_size=args.min_size, max_size=args.max_size)
    
    def progress(count, force=False):
        sys.stdout.write(f"\rFiles found: {count}")
        sys.stdout.flush()
        
    size_candidates, total_files = scanner.scan(progress_callback=progress)
    print() # New line after progress

    if not size_candidates:
        print(f"{Colors.OKGREEN}No potential duplicates found by size.{Colors.ENDC}")
        return

    # 2. Hash Candidates
    print(f"{Colors.OKCYAN}Hashing {sum(len(v) for v in size_candidates.values())} candidate files...{Colors.ENDC}")
    hasher = Hasher()
    duplicates = {}
    
    def process_group(file_group):
        local_dupes = {}
        for file in file_group:
            h = hasher.hash_file(file)
            if h:
                local_dupes.setdefault(h, []).append(file)
        return local_dupes

    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        results = executor.map(process_group, size_candidates.values())

    # Merge results
    for result in results:
        for h, files in result.items():
            if len(files) > 1:
                duplicates[h] = files

    if not duplicates:
        print(f"{Colors.OKGREEN}No duplicates found.{Colors.ENDC}")
        return

    # 3. Calculate Wasted Space
    wasted_bytes = 0
    for files in duplicates.values():
        wasted_bytes += os.path.getsize(files[0]) * (len(files) - 1)
    
    wasted_str = f"{wasted_bytes / (1024*1024):.2f} MB"
    print_summary(duplicates, total_files, wasted_str)

    # 4. Report
    txt_file = f"{args.output}.txt"
    csv_file = f"{args.output}.csv"
    Reporter.generate_txt(duplicates, total_files, wasted_bytes, txt_file)
    Reporter.generate_csv(duplicates, csv_file)
    print(f"{Colors.OKGREEN}Reports saved: {txt_file}, {csv_file}{Colors.ENDC}")

    # 5. Actions
    if args.interactive:
        interactive_delete(duplicates, hasher)
    elif args.delete_all:
        confirm = input(f"{Colors.FAIL}WARNING: Delete all duplicates (keep oldest in each group)? (y/N): {Colors.ENDC}").strip().lower()
        if confirm == 'y':
            for files in duplicates.values():
                # Sort by creation time, keep oldest
                files_sorted = sorted(files, key=lambda x: os.path.getctime(x))
                for file in files_sorted[1:]:
                    try:
                        os.remove(file)
                        print(f"Deleted: {file}")
                    except OSError as e:
                        print(f"Failed to delete {file}: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Operation cancelled by user.{Colors.ENDC}")
        sys.exit(1)