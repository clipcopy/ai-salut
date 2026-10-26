# Author: github.com/clipcopy
# 10-26-26

import os
from collections import defaultdict
from .config import DEFAULT_EXCLUDES

class Scanner:
    def __init__(self, paths, exclude_patterns=None, min_size=0, max_size=None):
        self.paths = paths
        self.excludes = set(exclude_patterns or DEFAULT_EXCLUDES)
        self.min_size = min_size
        self.max_size = max_size

    def _should_exclude(self, name):
        return any(ex in name for ex in self.excludes)

    def scan(self, progress_callback=None):
        # Group by size first to minimize hashing overhead
        size_map = defaultdict(list)
        total_files = 0

        for base_path in self.paths:
            if not os.path.isdir(base_path):
                print(f"Warning: {base_path} is not a directory. Skipping.")
                continue

            for root, dirs, files in os.walk(base_path):
                dirs[:] = [d for d in dirs if not self._should_exclude(d)]
                
                for file in files:
                    if self._should_exclude(file):
                        continue
                        
                    filepath = os.path.join(root, file)
                    try:
                        size = os.path.getsize(filepath)
                        
                        if size < self.min_size:
                            continue
                        if self.max_size is not None and size > self.max_size:
                            continue

                        size_map[size].append(filepath)
                        total_files += 1
                        
                        if progress_callback and total_files % 100 == 0:
                            progress_callback(total_files)
                            
                    except OSError:
                        continue # Skip inaccessible files
        
        if progress_callback:
            progress_callback(total_files, force=True)
            
        # Filter out sizes with only one file
        candidates = {size: paths for size, paths in size_map.items() if len(paths) > 1}
        return candidates, total_files