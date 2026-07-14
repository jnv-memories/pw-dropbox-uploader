import os
import tempfile
import yt_dlp

def download_youtube_video(url, filename=None):
    temp_dir = tempfile.gettempdir()
    
    if filename:
        base, _ = os.path.splitext(filename)
        outtmpl = os.path.join(temp_dir, f"{base}.%(ext)s")
    else:
        outtmpl = os.path.join(temp_dir, '%(title)s.%(ext)s')

    # We removed the player_client restriction. yt-dlp will now use the 
    # default web clients so that it can successfully pass the cookies.
    ydl_opts = {
        'proxy': 'socks5://127.0.0.1:40000',
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': outtmpl,
        'quiet': False,
        'no_warnings': False,
    }
    
    # Attach the cookies from the workflow
    if os.path.exists("youtube_cookies.txt"):
        ydl_opts['cookiefile'] = "youtube_cookies.txt"
    elif os.path.exists("uploader/youtube_cookies.txt"):
        ydl_opts['cookiefile'] = "uploader/youtube_cookies.txt"
        
    try:
        print(f"\n[+] Downloading YouTube video using Authenticated Cookies & JS Runtime: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_file_path = ydl.prepare_filename(info_dict)
            
            base_path, _ = os.path.splitext(downloaded_file_path)
            mp4_path = f"{base_path}.mp4"
            
            if not os.path.exists(downloaded_file_path) and os.path.exists(mp4_path):
                downloaded_file_path = mp4_path
                
            print(f"[✔] Download and FFmpeg merge completed: {downloaded_file_path}")
            return downloaded_file_path

    except Exception as e:
        print(f"[-] An error occurred during YouTube download: {e}")
        raise
