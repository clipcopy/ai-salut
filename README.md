ai-salut

A collection of simple Python tools, built with AI, for everyday tasks.

Every tool is one file. No setup steps, no config to edit first. You just run it and a menu shows up.

How to run

python3 password_generator.py
python3 temp_cleaner.py
python3 word_counter.py
python3 main.py

The last one, main.py, is the transcriber. It needs Whisper installed first. Run pip install openai-whisper, and make sure ffmpeg is installed on your computer.

What each tool does

password_generator.py
Makes passwords for you. Random passwords, passphrases made of real words, passwords you can actually pronounce, and PINs. It checks every password for weak patterns before showing it to you, so you never get something like aaaa1111 or abcd1234.

temp_cleaner.py
Finds and clears junk files like temp folders and app caches. Before deleting anything, it shows you what it found and asks for confirmation. Nothing is deleted right away either. It gets moved to a safe folder first, so you can undo a clean if you change your mind.

word_counter.py
Counts words and characters in any text. Tells you how long it takes to read or speak out loud, shows your most used words, and checks if your text fits within limits for places like X, Instagram, LinkedIn, or SMS.

main.py
Turns audio or video files into text. Works in English, Tagalog, and other languages. If you stop it partway through a big batch of files, running it again continues from where it left off instead of starting over.

Why use these

Nothing to configure before your first run.
Every file is written clearly, so you can read and understand what it does.
Nothing deletes or changes files without asking first.
Each tool was tested before being shared here.

Project files

password_generator.py
temp_cleaner.py
word_counter.py
main.py
README.md

Author

github.com/clipcopy
10-27-26