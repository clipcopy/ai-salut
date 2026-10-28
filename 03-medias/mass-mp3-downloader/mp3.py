import os
import time
import re
from youtubesearchpython import VideosSearch
import yt_dlp

# ========== CONFIGURATION ==========
INPUT_FILE = "songs.txt"          # Your song list (Artist — Title format)
OUTPUT_DIR = "downloads"          # Where MP3s will be saved
FAILED_LOG = "failed_songs.txt"   # Songs that couldn't be found/downloaded
RETRY_COUNT = 3                   # Number of retries per song
RETRY_DELAY = 2                   # Seconds between retries
# ===================================

def parse_song_list(file_path):
    """Read song list. Expected format: 'ARTIST — TITLE' or 'TITLE — ARTIST'"""
    songs = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Split by " — " (em dash) or " - " (hyphen)
            if ' — ' in line:
                parts = line.split(' — ', 1)
            elif ' - ' in line:
                parts = line.split(' - ', 1)
            else:
                # If no separator, treat whole line as title only
                songs.append(('', line))
                continue
            
            # First part could be artist or title. We'll assume "Artist — Title"
            artist, title = parts[0].strip(), parts[1].strip()
            songs.append((artist, title))
    return songs

def search_youtube_url(artist, title, max_retries=RETRY_COUNT):
    """Search YouTube for a song and return the best matching URL."""
    query = f"{title} {artist}" if artist else title
    for attempt in range(max_retries):
        try:
            search = VideosSearch(query, limit=3)
            results = search.result()
            if results['result']:
                # Return the first result (most relevant)
                return results['result'][0]['link']
            else:
                print(f"  No results found (attempt {attempt+1}/{max_retries})")
        except Exception as e:
            print(f"  Search error: {e} (attempt {attempt+1}/{max_retries})")
        time.sleep(RETRY_DELAY)
    return None

def download_mp3(url, output_dir, song_name):
    """Download audio from YouTube URL as MP3."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, f'{song_name}.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'ignoreerrors': True,
        'retries': 10,
        'fragment_retries': 10,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        print(f"  Download error: {e}")
        return False

def sanitize_filename(name):
    """Remove invalid characters from filename."""
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def main():
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Parse song list
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found. Create a file with one song per line.")
        return
    
    songs = parse_song_list(INPUT_FILE)
    print(f"Found {len(songs)} songs to process.\n")
    
    failed = []
    
    for idx, (artist, title) in enumerate(songs, 1):
        print(f"[{idx}/{len(songs)}] Processing: {artist} — {title}")
        
        # Create a safe filename
        safe_title = sanitize_filename(f"{artist} - {title}" if artist else title)
        mp3_path = os.path.join(OUTPUT_DIR, f"{safe_title}.mp3")
        
        # Skip if already downloaded
        if os.path.exists(mp3_path):
            print("  Already downloaded. Skipping.")
            continue
        
        # Search for YouTube URL
        url = search_youtube_url(artist, title)
        if not url:
            print(f"  FAILED: Could not find YouTube URL after {RETRY_COUNT} attempts.")
            failed.append(f"{artist} — {title} (no URL found)")
            continue
        
        print(f"  Found URL: {url}")
        
        # Download as MP3
        success = download_mp3(url, OUTPUT_DIR, safe_title)
        if success:
            print("  Download complete.")
        else:
            print("  FAILED: Download error.")
            failed.append(f"{artist} — {title} (download error)")
        
        # Be nice to YouTube (delay between songs)
        time.sleep(1)
    
    # Save failed songs
    if failed:
        with open(FAILED_LOG, 'w', encoding='utf-8') as f:
            f.write("\n".join(failed))
        print(f"\n⚠️ {len(failed)} songs failed. Check '{FAILED_LOG}' for manual download.")
    else:
        print("\n✅ All songs downloaded successfully!")

if __name__ == "__main__":
    main()
