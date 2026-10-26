# Author: github.com/clipcopy
# 10-26-26

import os
import sys

# Hashing
HASH_ALGO = 'sha256'
CHUNK_SIZE = 8192

# Colors for console output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Ignore patterns
DEFAULT_EXCLUDES = ['.git', '__pycache__', 'node_modules', '.venv', 'venv']

if os.name == 'nt':
    os.system('color')