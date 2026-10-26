# Author: github.com/clipcopy
# 10-26-26

import os
import time

def human_readable_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"

def get_file_info(filepath):
    try:
        stat = os.stat(filepath)
        return {
            'size': stat.st_size,
            'created': time.ctime(stat.st_ctime),
            'modified': time.ctime(stat.st_mtime),
            'permissions': oct(stat.st_mode)[-3:]
        }
    except OSError:
        return None