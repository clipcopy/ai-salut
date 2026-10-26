# Author: github.com/clipcopy
# 10-26-26

import csv
import json
from .utils import human_readable_size, get_file_info

class Reporter:
    @staticmethod
    def generate_txt(duplicates, total_scanned, wasted_space, filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=== Duplicate File Report ===\n")
            f.write(f"Total Files Scanned: {total_scanned}\n")
            f.write(f"Duplicate Groups: {len(duplicates)}\n")
            f.write(f"Total Space Wasted: {human_readable_size(wasted_space)}\n\n")

            for idx, (hash_val, files) in enumerate(duplicates.items(), 1):
                f.write(f"--- Group {idx} (Hash: {hash_val}) ---\n")
                for file in files:
                    info = get_file_info(file)
                    f.write(f"  Path: {file}\n")
                    if info:
                        f.write(f"  Size: {human_readable_size(info['size'])}\n")
                        f.write(f"  Modified: {info['modified']}\n")
                f.write("\n")

    @staticmethod
    def generate_csv(duplicates, filepath):
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Group', 'Hash', 'File Path', 'Size (Bytes)', 'Size (Readable)', 'Modified Date'])
            
            for idx, (hash_val, files) in enumerate(duplicates.items(), 1):
                for file in files:
                    info = get_file_info(file)
                    size = info['size'] if info else 0
                    writer.writerow([
                        idx, 
                        hash_val, 
                        file, 
                        size, 
                        human_readable_size(size), 
                        info['modified'] if info else 'Unknown'
                    ])