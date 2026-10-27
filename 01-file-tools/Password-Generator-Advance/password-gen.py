# Author: github.com/clipcopy
# 10-27-26

"""
VAULTSMITH - Advanced Password Generator
-----------------------------------------
One file, no installs, Python 3.8+.

Standout feature: SELF-HEALING GENERATION + PASSWORD DNA
  * Every password is audited by a weakness scanner (repeats, sequences,
    keyboard walks, common words, missing character types).
  * If a candidate fails, it is automatically "healed" (regenerated) until
    it passes. The report tells you how many heals it needed.
  * Each password gets a DNA fingerprint: a row of colored blocks you can
    recognize at a glance without ever showing the password itself.
"""

import hashlib
import math
import re
import secrets
import string

# ----------------------------------------------------------------------
# Settings (change these from the menu while the program runs)
# ----------------------------------------------------------------------
settings = {
    "length": 20,
    "lower": True,
    "upper": True,
    "digits": True,
    "symbols": True,
    "avoid_ambiguous": True,   # removes look-alikes such as O/0, l/1/I
}

AMBIGUOUS = "O0oIl1|`'\""
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.<>?/~"

# Small word list for passphrases (entropy is calculated honestly from it).
WORDS = """
able acid aged also area army away baby back ball band bank base bath bear beat
bell belt bird blue boat body bone book boot born both bowl bulb burn cafe cake
calm camp card care cash cave chef city clay club coal coat code coin cold cook
cool corn crew crop dark dash data dawn deal deep desk dial dish dive dock door
dove draw drum dust duty east easy edge epic face fact farm fast fern film fire
fish flag flow foam fork fort frog fuel gain game gate gift glow goat gold gulf
hall hand hawk heat herb hill hive home hope horn idea inch iron isle jade jazz
jump keen kind king kite lake lamp land lark leaf lime lion lock loop lunar maple
mint moon moss nest note oak ocean olive opal orbit otter palm peak pearl pine
plum pond quartz quest rain reef ridge river robin sage sand silk snow solar star
stone storm swan tide tiger torch trail vale wave wind wolf zest
""".split()

# Keyboard rows used by the keyboard-walk detector.
KEY_ROWS = ["1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm"]
COMMON_WORDS = ["password", "admin", "qwerty", "letmein", "welcome", "login", "iloveyou"]

# ----------------------------------------------------------------------
# Banner and display helpers
# ----------------------------------------------------------------------
RESET, BOLD, CYAN, GREEN, YELLOW, RED, DIM = (
    "\033[0m", "\033[1m", "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[2m",
)


def show_banner():
    print(f"""{CYAN}{BOLD}
 __     __   _   _ _     _____ ____  __  __ ___ _____ _   _
 \\ \\   / /_ _| | | | |   |_   _/ ___||  \\/  |_ _|_   _| | | |
  \\ \\ / / _` | | | | |     | | \\___ \\| |\\/| || |  | | | |_| |
   \\ V / (_| | |_| | |___  | |  ___) | |  | || |  | | |  _  |
    \\_/ \\__,_|\\___/|_____| |_| |____/|_|  |_|___| |_| |_| |_|
{RESET}{DIM}      Advanced Password Generator  |  by github.com/clipcopy{RESET}
""")


def show_menu():
    print(f"{BOLD}  [1]{RESET} Random password      {BOLD}[4]{RESET} PIN code")
    print(f"{BOLD}  [2]{RESET} Passphrase           {BOLD}[5]{RESET} Strength Lab (test your own)")
    print(f"{BOLD}  [3]{RESET} Pronounceable        {BOLD}[6]{RESET} Settings")
    print(f"{BOLD}  [0]{RESET} Exit")
    print(f"{DIM}  Current: length={settings['length']}  "
          f"lower={settings['lower']} upper={settings['upper']} "
          f"digits={settings['digits']} symbols={settings['symbols']}{RESET}\n")


def ask(prompt, default=None):
    """Ask for input; return the default when the user just presses Enter."""
    hint = f" [{default}]" if default is not None else ""
    answer = input(f"{CYAN}>{RESET} {prompt}{hint}: ").strip()
    return answer if answer else default


def ask_int(prompt, default, low, high):
    """Ask for a whole number inside a safe range."""
    try:
        value = int(ask(prompt, default))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


# ----------------------------------------------------------------------
# Generators
# ----------------------------------------------------------------------
def build_pool():
    """Return a list of the enabled character groups."""
    groups = []
    if settings["lower"]:
        groups.append(string.ascii_lowercase)
    if settings["upper"]:
        groups.append(string.ascii_uppercase)
    if settings["digits"]:
        groups.append(string.digits)
    if settings["symbols"]:
        groups.append(SYMBOLS)
    if settings["avoid_ambiguous"]:
        groups = ["".join(c for c in g if c not in AMBIGUOUS) for g in groups]
    return [g for g in groups if g]


def random_password(length):
    """Random password that always contains at least one char of each group."""
    groups = build_pool()
    if not groups:
        raise ValueError("Enable at least one character type in Settings.")
    length = max(length, len(groups))
    chars = [secrets.choice(g) for g in groups]            # guarantee each type
    everything = "".join(groups)
    chars += [secrets.choice(everything) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)                   # hide the guaranteed ones
    return "".join(chars), len(everything)


def passphrase(word_count, separator="-"):
    """Words + a random number, e.g. Moon-river-Oak-42."""
    words = [secrets.choice(WORDS) for _ in range(word_count)]
    words[secrets.randbelow(word_count)] = words[secrets.randbelow(word_count)].upper()
    words = [w.capitalize() if secrets.randbelow(2) else w for w in words]
    text = separator.join(words) + separator + str(secrets.randbelow(100)).zfill(2)
    bits = word_count * math.log2(len(WORDS)) + word_count + math.log2(100)
    return text, bits


def pronounceable(syllables):
    """Easy to say and remember: consonant + vowel pairs, digits, a symbol."""
    consonants, vowels = "bcdfghjklmnprstvwz", "aeiou"
    text = "".join(secrets.choice(consonants) + secrets.choice(vowels) for _ in range(syllables))
    text = "".join(c.upper() if secrets.randbelow(3) == 0 else c for c in text)
    text += str(secrets.randbelow(900) + 100) + secrets.choice("!@#$%&*?")
    bits = syllables * math.log2(len(consonants) * len(vowels) * 4) + math.log2(900 * 8)
    return text, bits


def pin_code(length):
    return "".join(secrets.choice(string.digits) for _ in range(length)), length * math.log2(10)


# ----------------------------------------------------------------------
# Weakness scanner (the "self-healing" brain)
# ----------------------------------------------------------------------
def find_weaknesses(password):
    """Return a list of human-readable problems. Empty list = clean."""
    problems = []
    lowered = password.lower()

    if re.search(r"(.)\1\1", password):
        problems.append("same character repeated 3+ times")

    for i in range(len(password) - 3):                      # abcd / 4321 style runs
        chunk = [ord(c) for c in password[i:i + 4]]
        steps = {chunk[j + 1] - chunk[j] for j in range(3)}
        if steps == {1} or steps == {-1}:
            problems.append("sequential run (like abcd or 4321)")
            break

    for row in KEY_ROWS:                                    # qwer / ytrewq style walks
        for i in range(len(row) - 3):
            piece = row[i:i + 4]
            if piece in lowered or piece[::-1] in lowered:
                problems.append("keyboard walk (like qwer or 1234)")
                break
        else:
            continue
        break

    for word in COMMON_WORDS:
        if word in lowered:
            problems.append(f"contains common word '{word}'")

    return problems


def self_heal(generate, max_attempts=200):
    """Call `generate()` until the result passes the scanner."""
    heals = 0
    result = generate()
    while find_weaknesses(result[0]) and heals < max_attempts:
        heals += 1
        result = generate()
    return result, heals


# ----------------------------------------------------------------------
# Strength analysis
# ----------------------------------------------------------------------
def estimate_entropy(password):
    """Entropy estimate for a password we did not generate ourselves."""
    pool = 0
    if re.search(r"[a-z]", password):
        pool += 26
    if re.search(r"[A-Z]", password):
        pool += 26
    if re.search(r"\d", password):
        pool += 10
    if re.search(r"[^a-zA-Z0-9]", password):
        pool += 32
    bits = len(password) * math.log2(pool) if pool else 0
    bits -= 6 * len(find_weaknesses(password))              # penalty for patterns
    return max(bits, 0)


def crack_time(bits, guesses_per_second=1e11):
    """Average time to crack by brute force (offline attack on a fast hash)."""
    seconds = (2 ** bits) / 2 / guesses_per_second
    for name, size in (("years", 31_557_600), ("days", 86_400),
                       ("hours", 3_600), ("minutes", 60)):
        if seconds >= size:
            value = seconds / size
            return f"{value:.1e} {name}" if value >= 1e6 else f"{value:,.0f} {name}"
    return "less than a minute" if seconds >= 1 else "instantly"


def rating(bits):
    if bits < 40:
        return f"{RED}WEAK{RESET}"
    if bits < 60:
        return f"{YELLOW}FAIR{RESET}"
    if bits < 80:
        return f"{GREEN}STRONG{RESET}"
    return f"{GREEN}{BOLD}EXCELLENT{RESET}"


def password_dna(password, blocks=10):
    """Colored fingerprint: same password always gives the same pattern."""
    digest = hashlib.sha256(password.encode()).digest()
    palette = [196, 208, 226, 46, 51, 33, 129, 201, 245, 118]
    art = "".join(f"\033[48;5;{palette[digest[i] % len(palette)]}m  {RESET}" for i in range(blocks))
    return art, digest.hex()[:8]


# ----------------------------------------------------------------------
# Result display
# ----------------------------------------------------------------------
def show_result(password, bits, heals=0):
    """heals=None hides the self-healing line (used when testing your own password)."""
    dna, short_id = password_dna(password)
    print(f"\n  {BOLD}Password :{RESET} {GREEN}{BOLD}{password}{RESET}")
    print(f"  Length   : {len(password)}")
    print(f"  Entropy  : {bits:.1f} bits   Rating: {rating(bits)}")
    print(f"  Crack time: ~{crack_time(bits)} (offline, 100 billion guesses/sec)")
    print(f"  DNA      : {dna}  {DIM}id {short_id}{RESET}")
    if heals is None:
        pass
    elif heals:
        print(f"  {YELLOW}Self-healing:{RESET} fixed {heals} weak candidate(s) before showing this one")
    else:
        print(f"  {GREEN}Self-healing:{RESET} passed the weakness scan on the first try")
    print()


# ----------------------------------------------------------------------
# Menu actions
# ----------------------------------------------------------------------
def action_random():
    length = ask_int("Length (8-128)", settings["length"], 8, 128)
    count = ask_int("How many (1-10)", 1, 1, 10)
    for _ in range(count):
        (password, pool_size), heals = self_heal(lambda: random_password(length))
        show_result(password, len(password) * math.log2(pool_size), heals)


def action_passphrase():
    words = ask_int("Number of words (3-10)", 5, 3, 10)
    sep = ask("Separator", "-")
    (text, bits), heals = self_heal(lambda: passphrase(words, sep))
    show_result(text, bits, heals)


def action_pronounceable():
    syllables = ask_int("Syllables (3-10)", 5, 3, 10)
    (text, bits), heals = self_heal(lambda: pronounceable(syllables))
    show_result(text, bits, heals)


def action_pin():
    length = ask_int("PIN length (4-12)", 6, 4, 12)
    (text, bits), heals = self_heal(lambda: pin_code(length))
    show_result(text, bits, heals)


def action_strength_lab():
    print(f"{DIM}  Your password is analyzed locally and never stored or sent anywhere.{RESET}")
    password = ask("Type a password to test")
    if not password:
        return
    problems = find_weaknesses(password)
    show_result(password, estimate_entropy(password), heals=None)
    if problems:
        print(f"  {RED}Weaknesses found:{RESET}")
        for p in problems:
            print(f"   - {p}")
        print(f"  {DIM}Tip: generate a new one with option 1.{RESET}\n")
    else:
        print(f"  {GREEN}No common weakness patterns detected.{RESET}\n")


def action_settings():
    print("\n  Press Enter to keep the current value. Answer y or n for switches.\n")
    settings["length"] = ask_int("Default length (8-128)", settings["length"], 8, 128)
    for key, label in (("lower", "Lowercase a-z"), ("upper", "Uppercase A-Z"),
                       ("digits", "Digits 0-9"), ("symbols", "Symbols !@#"),
                       ("avoid_ambiguous", "Avoid look-alikes (O/0, l/1)")):
        current = "y" if settings[key] else "n"
        settings[key] = ask(label, current).lower().startswith("y")
    if not build_pool():
        print(f"  {RED}At least one type is required. Lowercase re-enabled.{RESET}")
        settings["lower"] = True
    print(f"  {GREEN}Settings saved.{RESET}\n")


ACTIONS = {
    "1": action_random,
    "2": action_passphrase,
    "3": action_pronounceable,
    "4": action_pin,
    "5": action_strength_lab,
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
            print(f"\n{CYAN}  Stay safe. Goodbye!{RESET}\n")
            break
        action = ACTIONS.get(choice)
        if action is None:
            print(f"{RED}  Invalid choice, try again.{RESET}\n")
            continue
        try:
            action()
        except ValueError as error:
            print(f"{RED}  {error}{RESET}\n")
        input(f"{DIM}  Press Enter to continue...{RESET}")
        print("\n" + "=" * 62 + "\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{CYAN}  Goodbye!{RESET}\n")