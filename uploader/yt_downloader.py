import os
import tempfile
import yt_dlp

def download_youtube_video(url):
    print(f"\n[+] YouTube URL detected. Routing to yt-dlp...")
    
    temp_dir = tempfile.gettempdir()
    
    # Path to the cookies file created by GitHub Actions
    cookie_path = os.path.join(os.getcwd(), 'youtube_cookies.txt')
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': True,
        # ADD THIS: Pass the cookie file to bypass bot checks
        'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
        # ADD THIS: Spoof the client to look more like a standard web user
        'extractor_args': {'youtube': {'player_client': ['web']}}
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
            
            base, _ = os.path.splitext(filename)
            mp4_filename = f"{base}.mp4"
            
            if os.path.exists(mp4_filename):
                return mp4_filename
                
            return filename
            
    except Exception as e:
        raise RuntimeError(f"yt-dlp failed to download the video. Error: {str(e)}")
