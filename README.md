What's inside

| Tool | What it does | The feature that makes it different |

| VaultSmith · `password_generator.py` | Random, passphrase, pronounceable & PIN password generator | Self-healing generation — every password is scanned for weak patterns and auto-regenerated until it's clean, plus a color "DNA" fingerprint so you can recognize a password at a glance without ever displaying it |
| SweepVault · `temp_cleaner.py` | Finds and clears temp/cache junk across Windows, macOS & Linux | Full undo — nothing is deleted outright, it's quarantined in an Undo Vault you can restore with one menu choice, plus a safety gate that skips anything that might still be in use |
| TextScope · `word_counter.py` | Word/character counter with readability stats | Cut-line preview — shows the exact point X/Twitter, Instagram, LinkedIn, SEO titles or SMS would chop your text off, so you see what readers actually get instead of guessing |
| VoiceVault · `main.py` | Audio/video transcriber (Whisper-powered, English/Tagalog + more) | Resumable batches — interrupted halfway through 200 files? Run it again and it picks up exactly where it left off, plus subtitle export with a confidence map flagging lines worth double-checking |

Every tool shares the same DNA: a clean banner, a numbered menu, sane defaults on Enter, and code that's commented well enough to actually learn from.

Why you'd want these

- Zero setup friction. Most tools here run on the Python standard library alone. The one exception (VoiceVault) tells you exactly what to `pip install` if it's missing — it won't just crash on you.
- Built to be read, not just run. Every file is organized into clearly labeled sections with short, honest comments. If you've ever opened a "simple script" and found 400 unreadable lines, these aren't that.
- Safety-minded by default. Destructive actions ask before they act, dry-runs exist where it matters, and SweepVault literally won't let you lose a file you didn't mean to delete.
- Not a toy. These aren't "hello world" scripts dressed up — entropy math, offline-attack crack-time estimates, GSM-7 SMS segmentation, Whisper confidence scoring. The kind of detail you'd expect from a paid app, free and readable.

Quick start

```bash
git clone https://github.com/clipcopy/ai-salut.git
cd ai-salut

run whichever tool you need
python3 password_generator.py
python3 temp_cleaner.py
python3 word_counter.py
python3 main.py          # VoiceVault — needs: pip install openai-whisper, and ffmpeg on PATH
```

Each tool opens straight into a banner and a menu. No flags to memorize, no docs to read first — just pick a number.

Project structure

```
ai-salut/
├── password_generator.py   # VaultSmith
├── temp_cleaner.py         # SweepVault
├── word_counter.py         # TextScope
├── main.py                 # VoiceVault
└── README.md
```

A note on how these are built

Every tool here starts from a real request, gets built as a single readable file, and gets actually run before it's handed over — not just written and hoped for. If a tool claims a feature, that feature was tested in this repo, not assumed.