# Author: github.com/clipcopy
# 10-26-26

import hashlib
import os
from .config import HASH_ALGO, CHUNK_SIZE

class Hasher:
    def __init__(self):
        self.cache = {}

    def hash_file(self, filepath):
        if filepath in self.cache:
            return self.cache[filepath]
        
        h = hashlib.new(HASH_ALGO)
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(CHUNK_SIZE):
                    h.update(chunk)
            digest = h.hexdigest()
            self.cache[filepath] = digest
            return digest
        except (OSError, PermissionError) as e:
            print(f"Error hashing {filepath}: {e}")
            return None