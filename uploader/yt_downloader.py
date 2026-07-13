import os
import tempfile
import yt_dlp

def download_youtube_video(url):
    print(f"\n[+] YouTube URL detected. Routing to yt-dlp...")
    
    temp_dir = tempfile.gettempdir()
    cookie_path = os.path.join(os.getcwd(), 'youtube_cookies.txt')
    
    ydl_opts = {
        # FIX 1: Loosen strict extension requirements. Just get the best quality available.
        'format': 'bestvideo+bestaudio/best',
        
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        
        # Merge separate video/audio streams into mp4 container
        'merge_output_format': 'mp4',
        
        'quiet': False,
        'no_warnings': True,
        'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
        'extractor_args': {'youtube': {'player_client': ['web']}},
        
        # FIX 2: Force FFmpeg to convert the final file to .mp4 just in case 
        # it downloaded a single stream that wasn't naturally an mp4.
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            
            # Figure out what the final filename is meant to be
            raw_filename = ydl.prepare_filename(info_dict)
            base, _ = os.path.splitext(raw_filename)
            
            # Because of our postprocessors, the file on disk is guaranteed to be .mp4
            mp4_filename = f"{base}.mp4"
            
            if os.path.exists(mp4_filename):
                return mp4_filename
                
            return raw_filename
            
    except Exception as e:
        raise RuntimeError(f"yt-dlp failed to download the video. Error: {str(e)}")
