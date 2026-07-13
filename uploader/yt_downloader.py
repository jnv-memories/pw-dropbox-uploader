import os
import tempfile
import yt_dlp

def download_youtube_video(url):
    print(f"\n[+] YouTube URL detected. Routing to yt-dlp...")
    
    temp_dir = tempfile.gettempdir()
    
    # yt-dlp configuration: Best video + best audio, merged into mp4
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info and download
            info_dict = ydl.extract_info(url, download=True)
            
            # Prepare the expected filename
            filename = ydl.prepare_filename(info_dict)
            
            # Since we enforce mp4 merging, check if the output file is an .mp4
            base, _ = os.path.splitext(filename)
            mp4_filename = f"{base}.mp4"
            
            if os.path.exists(mp4_filename):
                return mp4_filename
                
            return filename
            
    except Exception as e:
        raise RuntimeError(f"yt-dlp failed to download the video. Error: {str(e)}")
