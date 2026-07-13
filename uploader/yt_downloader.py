import os
import tempfile
import yt_dlp

def download_youtube_video(url):
    print(f"\n[+] YouTube URL detected. Routing to yt-dlp...")
    
    temp_dir = tempfile.gettempdir()
    
    # BULLETPROOF PATH: Get the exact directory this python file is inside (/uploader/)
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_path = os.path.join(current_script_dir, 'youtube_cookies.txt')
    
    # Debugging: Print exactly what is happening so we can see it in GitHub Actions logs
    print(f"    -> Looking for cookies at: {cookie_path}")
    if os.path.exists(cookie_path):
        print("    -> [✔] Cookie file FOUND! Passing to yt-dlp.")
        active_cookie_path = cookie_path
    else:
        print("    -> [!] Cookie file NOT FOUND! yt-dlp will try without authentication.")
        active_cookie_path = None
    
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': True,
        'cookiefile': active_cookie_path,
        'extractor_args': {'youtube': {'player_client': ['web']}},
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            raw_filename = ydl.prepare_filename(info_dict)
            base, _ = os.path.splitext(raw_filename)
            mp4_filename = f"{base}.mp4"
            
            if os.path.exists(mp4_filename):
                return mp4_filename
                
            return raw_filename
            
    except Exception as e:
        raise RuntimeError(f"yt-dlp failed to download the video. Error: {str(e)}")
