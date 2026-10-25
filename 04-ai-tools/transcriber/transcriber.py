#!/usr/bin/env python3
"""
Fast Transcriber for audio/video files (English/Tagalog).
Optimized for CPU and low RAM (8GB).
Usage:
    py -3 transcriber.py                # processes all .mp3 in current folder (tiny model)
    py -3 transcriber.py test.mp3       # processes only test.mp3
    py -3 transcriber.py --fast         # force tiny + beam=1
    py -3 transcriber.py --model base   # better accuracy, slower
Output: <input_basename>.txt
"""

import sys
import argparse
import shutil
import warnings
from pathlib import Path

# Suppress FP16 warning
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")

def check_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        print(
            "ERROR: ffmpeg not found.\n"
            "Please install ffmpeg:\n"
            "  - Windows: https://ffmpeg.org/download.html\n"
            "  - Linux: sudo apt install ffmpeg\n"
            "  - macOS: brew install ffmpeg",
            file=sys.stderr
        )
        sys.exit(1)

def transcribe(file_path: Path, model_name: str, beam_size: int, num_threads: int) -> str:
    try:
        import whisper
        import torch
    except ImportError:
        print("ERROR: openai-whisper not installed. Run: pip install openai-whisper", file=sys.stderr)
        sys.exit(1)

    # Use all CPU cores
    torch.set_num_threads(num_threads)

    # Load model
    model = whisper.load_model(model_name)

    # Decide FP16: only if CUDA is available
    use_fp16 = torch.cuda.is_available()
    result = model.transcribe(
        str(file_path),
        language=None,          # auto-detect English/Tagalog
        task="transcribe",
        fp16=use_fp16,
        beam_size=beam_size,
        best_of=beam_size if beam_size > 1 else None  # best_of must be >= beam_size
    )
    return result["text"]

def process_one(file_path: Path, model_name: str, beam_size: int, num_threads: int) -> None:
    output_txt = file_path.with_suffix(".txt")
    print(f"Transcribing: {file_path.name} -> {output_txt.name} (model={model_name}, beam={beam_size})", file=sys.stderr)
    text = transcribe(file_path, model_name, beam_size, num_threads)
    output_txt.write_text(text, encoding="utf-8")
    print(f"Finished: {output_txt.name}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Fast transcriber for English/Tagalog audio")
    parser.add_argument("file", nargs="?", help="Optional single file. If omitted, processes all .mp3 files.")
    parser.add_argument("--model", default="tiny", choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model (default: tiny = fastest). Larger = slower but more accurate.")
    parser.add_argument("--beam", type=int, default=5,
                        help="Beam size for decoding (default: 5). Set to 1 for ~30% speedup (slight accuracy loss).")
    parser.add_argument("--fast", action="store_true",
                        help="Alias for --model tiny --beam 1 (fastest possible).")
    parser.add_argument("--threads", type=int, default=0,
                        help="Number of CPU threads (0 = auto). Default uses all cores.")
    args = parser.parse_args()

    if args.fast:
        args.model = "tiny"
        args.beam = 1

    # Auto-detect thread count
    import os
    if args.threads <= 0:
        args.threads = os.cpu_count() or 2

    check_ffmpeg()

    # Determine files
    if args.file:
        files = [Path(args.file)]
    else:
        files = list(Path.cwd().glob("*.mp3"))
        if not files:
            print("No .mp3 files found in current directory.", file=sys.stderr)
            sys.exit(0)

    # Process each
    for f in files:
        if not f.is_file():
            print(f"ERROR: File not found - {f}", file=sys.stderr)
            continue
        try:
            process_one(f, args.model, args.beam, args.threads)
        except Exception as e:
            print(f"ERROR: Failed to transcribe {f.name} - {e}", file=sys.stderr)

    print("All done.", file=sys.stderr)

if __name__ == "__main__":
    main()
