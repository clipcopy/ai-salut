# Author: github.com/clipcopy
# 10-27-26

"""
TEXTSCOPE - Advanced Word & Character Counter
-----------------------------------------------
One file, no installs, Python 3.8+.

Standout feature: CUT-LINE PREVIEW + PLATFORM FIT RADAR
  * Instead of only saying "you are 40 characters over", it shows the
    EXACT spot where each platform would chop your text off, so you can
    see what your readers would actually get.
  * Checks X/Twitter (URLs count as 23, CJK and emoji count double),
    Instagram, LinkedIn, YouTube titles, SEO titles, meta descriptions,
    SMS (GSM-7 vs Unicode, multi-part segments) and your own custom limit.
  * Platform limits change over time, so treat them as a good guide and
    edit the PLATFORMS list at the top if one gets updated.
"""

import math
import re
from collections import Counter
from pathlib import Path

# ----------------------------------------------------------------------
# Settings and state (changeable from the menu while the program runs)
# ----------------------------------------------------------------------
settings = {
    "ignore_common_words": True,   # hide words like "the" and "and" in the top list
    "top_words": 8,                # how many words to show in the top list
    "reading_wpm": 238,            # average silent reading speed
    "speaking_wpm": 150,           # average speaking speed
}

state = {"text": ""}               # the text currently loaded

# (name, limit, how it is counted)
PLATFORMS = [
    ("X / Twitter post", 280, "x"),
    ("Instagram caption", 2200, "chars"),
    ("LinkedIn post", 3000, "chars"),
    ("YouTube title", 100, "chars"),
    ("SEO page title", 60, "chars"),
    ("Meta description", 160, "chars"),
]

STOPWORDS = set("""
a an and are as at be but by for from has have he her his i if in is it its me my
no not of on or our she so that the their them they this to us was we were what
when which who will with you your
""".split())

# ----------------------------------------------------------------------
# Colors and display helpers
# ----------------------------------------------------------------------
RESET, BOLD, CYAN, GREEN, YELLOW, RED, DIM = (
    "\033[0m", "\033[1m", "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[2m",
)

BANNER_ART = r"""
  ____ ___  _   _ _   _ _____
 / ___/ _ \| | | | \ | |_   _|
| |  | | | | | | |  \| | | |
| |__| |_| | |_| | |\  | | |
 \____\___/ \___/|_| \_| |_|
"""


def show_banner():
    print(CYAN + BOLD + BANNER_ART + RESET)
    print(f"{DIM}   TEXTSCOPE  |  Word & Character Counter  |  github.com/clipcopy{RESET}\n")


def show_menu():
    print(f"{BOLD}  [1]{RESET} Type or paste text       {BOLD}[4]{RESET} Platform fit + cut-line")
    print(f"{BOLD}  [2]{RESET} Load from file           {BOLD}[5]{RESET} Keyword finder")
    print(f"{BOLD}  [3]{RESET} X-Ray report             {BOLD}[6]{RESET} Settings")
    print(f"{BOLD}  [0]{RESET} Exit")
    text = state["text"]
    if text:
        print(f"{DIM}  Loaded: {len(WORD_RE.findall(text)):,} words, {len(text):,} characters{RESET}\n")
    else:
        print(f"{DIM}  Loaded: nothing yet (start with option 1 or 2){RESET}\n")


def ask(prompt, default=None):
    """Ask for input; return the default when the user just presses Enter."""
    hint = f" [{default}]" if default is not None else ""
    answer = input(f"{CYAN}>{RESET} {prompt}{hint}: ").strip()
    return answer if answer else default


def ask_int(prompt, default, low, high):
    try:
        value = int(ask(prompt, default))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


def bar(part, whole, width=20):
    """Text bar chart."""
    filled = int(width * min(part / whole, 1)) if whole else 0
    return "#" * filled + "." * (width - filled)


def row(label, value):
    print(f"  {label:<28}{BOLD}{value}{RESET}")


def one_line(text):
    """Make text safe to show on one line (newlines become a return arrow)."""
    return text.replace("\n", "↵").replace("\r", "")


def need_text():
    """Return True if text is loaded, otherwise explain what to do."""
    if state["text"].strip():
        return True
    print(f"\n  {YELLOW}No text loaded yet. Use option 1 or 2 first.{RESET}\n")
    return False


# ----------------------------------------------------------------------
# Core analysis
# ----------------------------------------------------------------------
WORD_RE = re.compile(r"[\w'’-]+", re.UNICODE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
URL_RE = re.compile(r"https?://\S+")


def count_syllables(word):
    """Rough English syllable estimate (good enough for readability scores)."""
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and not word.endswith("le") and count > 1:
        count -= 1                                   # silent final e
    return max(count, 1)


def format_duration(seconds):
    seconds = round(seconds)
    if seconds < 60:
        return f"{seconds} sec"
    return f"{seconds // 60} min {seconds % 60} sec"


def readability_label(score):
    for limit, label in ((90, "Very easy"), (80, "Easy"), (70, "Fairly easy"),
                         (60, "Standard"), (50, "Fairly hard"), (30, "Difficult")):
        if score >= limit:
            return label
    return "Very difficult"


def analyze(text):
    """Return a dictionary with every statistic the report needs."""
    words = WORD_RE.findall(text)
    sentences = [s for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    lines = [ln for ln in text.splitlines() if ln.strip()]

    total_words = len(words)
    total_sentences = max(len(sentences), 1)
    syllables = sum(count_syllables(w) for w in words)
    lowered = [w.lower().strip("'’-") for w in words]

    flesch = 0.0
    if total_words:
        flesch = (206.835 - 1.015 * (total_words / total_sentences)
                  - 84.6 * (syllables / total_words))

    return {
        "characters": len(text),
        "no_spaces": len(re.sub(r"\s", "", text)),
        "letters": sum(c.isalpha() for c in text),
        "digits": sum(c.isdigit() for c in text),
        "spaces": sum(c.isspace() for c in text),
        "words": total_words,
        "unique": len(set(lowered)),
        "sentences": total_sentences if total_words else 0,
        "paragraphs": len(paragraphs),
        "lines": len(lines),
        "avg_word": sum(len(w) for w in words) / total_words if total_words else 0,
        "avg_sentence": total_words / total_sentences if total_words else 0,
        "longest": max(words, key=len) if words else "",
        "reading": total_words / settings["reading_wpm"] * 60,
        "speaking": total_words / settings["speaking_wpm"] * 60,
        "flesch": flesch,
        "lowered": lowered,
    }


def top_words(lowered_words):
    """Most frequent words, optionally skipping very common ones."""
    pool = [w for w in lowered_words if w]
    if settings["ignore_common_words"]:
        pool = [w for w in pool if w not in STOPWORDS and len(w) > 1]
    return Counter(pool).most_common(settings["top_words"])


# ----------------------------------------------------------------------
# Platform fit and cut-line logic
# ----------------------------------------------------------------------
def x_weights(text):
    """Per-character weight the way X counts: URLs = 23, wide chars = 2, others = 1."""
    weights = []
    for index, char in enumerate(text):
        code = ord(char)
        narrow = code <= 4351 or 8192 <= code <= 8205 or 8208 <= code <= 8223 or 8242 <= code <= 8247
        weights.append(1 if narrow else 2)
    for match in URL_RE.finditer(text):               # a whole URL counts as 23
        for position in range(match.start(), match.end()):
            weights[position] = 0
        weights[match.start()] = 23
    return weights


def measure(text, mode):
    """Return (used, cut_index_function) for a platform counting mode."""
    if mode == "x":
        weights = x_weights(text)
        used = sum(weights)

        def cut_index(limit):
            total = 0
            for position, weight in enumerate(weights):
                total += weight
                if total > limit:
                    return position
            return len(text)
        return used, cut_index
    return len(text), lambda limit: min(limit, len(text))


GSM_BASIC = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
GSM_EXTENDED = set("^{}\\[~]|€")                      # these cost 2 units in GSM-7


def sms_info(text):
    """Return (encoding, units, segments, units_left_in_last_segment)."""
    if all(c in GSM_BASIC or c in GSM_EXTENDED for c in text):
        encoding, single, multi = "GSM-7", 160, 153
        units = sum(2 if c in GSM_EXTENDED else 1 for c in text)
    else:
        encoding, single, multi = "Unicode", 70, 67
        units = len(text.encode("utf-16-le")) // 2
    if units == 0:
        return encoding, 0, 0, single
    if units <= single:
        return encoding, units, 1, single - units
    segments = math.ceil(units / multi)
    return encoding, units, segments, segments * multi - units


def status_color(used, limit):
    if used > limit:
        return RED
    return YELLOW if used > limit * 0.9 else GREEN


def show_fit_row(text, name, limit, mode):
    used, cut_index = measure(text, mode)
    color = status_color(used, limit)
    left = limit - used
    verdict = f"{left:,} left" if left >= 0 else f"{-left:,} OVER"
    print(f"  {name:<20} {color}{bar(used, limit)}{RESET} {used:,}/{limit:,}  {color}{verdict}{RESET}")

    if used > limit:                                   # the cut-line preview
        cut = cut_index(limit)
        before = one_line(text[max(0, cut - 28):cut])
        after = one_line(text[cut:cut + 28])
        print(f"  {DIM}   cut-line: …{RESET}{before}{RED}{BOLD} ✂ {after}…{RESET}")


# ----------------------------------------------------------------------
# Menu actions
# ----------------------------------------------------------------------
def action_type():
    print(f"\n  {DIM}Paste or type your text. Finish with a line containing only /end{RESET}\n")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "/end":
            break
        lines.append(line)
    state["text"] = "\n".join(lines)
    words = len(WORD_RE.findall(state["text"]))
    print(f"\n  {GREEN}Loaded {words:,} words, {len(state['text']):,} characters.{RESET}\n")


def action_load():
    raw = ask("Path to a text file")
    if not raw:
        return
    path = Path(raw.strip('"\'')).expanduser()
    try:
        if path.stat().st_size > 20_000_000:
            print(f"\n  {RED}File is larger than 20 MB, please use a smaller one.{RESET}\n")
            return
        state["text"] = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        print(f"\n  {RED}Could not read file: {error.strerror or error}{RESET}\n")
        return
    words = len(WORD_RE.findall(state["text"]))
    print(f"\n  {GREEN}Loaded {path.name}: {words:,} words, {len(state['text']):,} characters.{RESET}\n")


def action_report():
    if not need_text():
        return
    s = analyze(state["text"])
    print(f"\n  {BOLD}{CYAN}=== X-RAY REPORT ==={RESET}\n")
    print(f"  {BOLD}Counts{RESET}")
    row("Characters (with spaces)", f"{s['characters']:,}")
    row("Characters (no spaces)", f"{s['no_spaces']:,}")
    row("Letters / digits / spaces", f"{s['letters']:,} / {s['digits']:,} / {s['spaces']:,}")
    row("Words", f"{s['words']:,}")
    row("Unique words", f"{s['unique']:,}")
    row("Sentences", f"{s['sentences']:,}")
    row("Paragraphs / lines", f"{s['paragraphs']:,} / {s['lines']:,}")

    print(f"\n  {BOLD}Style{RESET}")
    row("Average word length", f"{s['avg_word']:.1f} letters")
    row("Average sentence length", f"{s['avg_sentence']:.1f} words")
    row("Longest word", s["longest"][:40])
    row("Readability (Flesch, EN)", f"{s['flesch']:.0f} - {readability_label(s['flesch'])}")

    print(f"\n  {BOLD}Time{RESET}")
    row("Reading time", format_duration(s["reading"]))
    row("Speaking time", format_duration(s["speaking"]))

    words = top_words(s["lowered"])
    if words:
        print(f"\n  {BOLD}Top words{RESET}")
        highest = words[0][1]
        for word, count in words:
            print(f"   {word[:16]:<16} {YELLOW}{bar(count, highest)}{RESET} {count}")
    print()


def action_platforms():
    if not need_text():
        return
    text = state["text"]
    print(f"\n  {BOLD}{CYAN}=== PLATFORM FIT RADAR ==={RESET}\n")
    for name, limit, mode in PLATFORMS:
        show_fit_row(text, name, limit, mode)

    encoding, units, segments, left = sms_info(text)
    color = GREEN if segments <= 1 else YELLOW if segments <= 3 else RED
    print(f"  {'SMS':<20} {color}{encoding}, {units:,} units -> {segments} segment(s){RESET} "
          f"{DIM}({left} left in last){RESET}")

    custom = ask("\n  Custom character limit (Enter to skip)")
    if custom and custom.isdigit() and int(custom) > 0:
        print()
        show_fit_row(text, "Custom limit", int(custom), "chars")
    print(f"\n  {DIM}Limits change over time. Edit PLATFORMS at the top of main.py to update.{RESET}\n")


def action_keyword():
    if not need_text():
        return
    text = state["text"]
    phrase = ask("Word or phrase to find")
    if not phrase:
        return
    pattern = re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE)
    matches = list(pattern.finditer(text))
    total_words = max(len(WORD_RE.findall(text)), 1)
    phrase_words = max(len(WORD_RE.findall(phrase)), 1)
    density = len(matches) * phrase_words / total_words * 100

    print(f"\n  Found {BOLD}{len(matches)}{RESET} time(s) | keyword density {BOLD}{density:.2f}%{RESET}")
    for match in matches[:5]:
        start, end = match.span()
        before = one_line(text[max(0, start - 25):start])
        after = one_line(text[end:end + 25])
        print(f"   …{before}{YELLOW}{BOLD}{match.group()}{RESET}{after}…")
    if len(matches) > 5:
        print(f"   {DIM}...and {len(matches) - 5} more{RESET}")
    print()


def action_settings():
    print("\n  Press Enter to keep the current value.\n")
    current = "y" if settings["ignore_common_words"] else "n"
    settings["ignore_common_words"] = ask("Hide common words (the, and...) in top list (y/n)",
                                          current).lower().startswith("y")
    settings["top_words"] = ask_int("How many top words (3-20)", settings["top_words"], 3, 20)
    settings["reading_wpm"] = ask_int("Reading speed, words/min (100-500)", settings["reading_wpm"], 100, 500)
    settings["speaking_wpm"] = ask_int("Speaking speed, words/min (80-250)", settings["speaking_wpm"], 80, 250)
    print(f"  {GREEN}Settings saved.{RESET}\n")


ACTIONS = {
    "1": action_type,
    "2": action_load,
    "3": action_report,
    "4": action_platforms,
    "5": action_keyword,
    "6": action_settings,
}


# ----------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------
def main():
    show_banner()
    while True:
        show_menu()
        choice = ask("Choose an option")
        if choice == "0":
            print(f"\n{CYAN}  Write on. Goodbye!{RESET}\n")
            break
        action = ACTIONS.get(choice)
        if action is None:
            print(f"{RED}  Invalid choice, try again.{RESET}\n")
            continue
        action()
        input(f"{DIM}  Press Enter to continue...{RESET}")
        print("\n" + "=" * 62 + "\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{CYAN}  Goodbye!{RESET}\n")