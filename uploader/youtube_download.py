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

    # UPDATED LOGIC:
    # 1. Removed all forced player_clients (tv, web, ios). 
    #    The master branch of yt-dlp will now auto-negotiate to avoid DRM/PO blocks.
    # 2. Maintained the local WARP proxy to bypass GitHub datacenter IP bans.
    # 3. Requesting bestvideo + bestaudio and merging via system FFmpeg.
    ydl_opts = {
        'proxy': 'socks5://127.0.0.1:40000',
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': outtmpl,
        'quiet': False,
        'no_warnings': False,
    }
    
    try:
        print(f"\n[+] Downloading TRUE highest quality YouTube video via yt-dlp: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_file_path = ydl.prepare_filename(info_dict)
            
            base_path, _ = os.path.splitext(downloaded_file_path)
            mp4_path = f"{base_path}.mp4"
            
            # Ensure we return the path to the merged .mp4 file
            if not os.path.exists(downloaded_file_path) and os.path.exists(mp4_path):
                downloaded_file_path = mp4_path
                
            print(f"[✔] Download and FFmpeg merge completed: {downloaded_file_path}")
            return downloaded_file_path

    except Exception as e:
        print(f"[-] An error occurred during YouTube download: {e}")
        raise
