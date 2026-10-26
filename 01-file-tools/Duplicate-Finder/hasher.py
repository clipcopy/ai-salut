# Author: github.com/clipcopy
# 10-26-26

import argparse
import os
import sys
import shutil
from concurrent.futures import ThreadPoolExecutor

from scanner import Scanner
from hasher import Hasher
from reporter import Reporter
from config import Colors, HASH_ALGO

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