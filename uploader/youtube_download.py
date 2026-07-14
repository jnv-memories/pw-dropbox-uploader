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
    # 'bestvideo+bestaudio/best' removes the extension restriction, 
    # forcing it to grab the absolute highest quality 1080p/4k/8k video stream 
    # and the highest quality audio stream, regardless of their source format.
    # 'merge_output_format': 'mp4' uses FFmpeg to stitch them into an MP4 container.
    ydl_opts = {
        'proxy': 'socks5://127.0.0.1:40000',
        'extractor_args': {'youtube': {'player_client': ['ios', 'android']}},
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': outtmpl,
        'quiet': False,
        'no_warnings': False,
    }
    
    try:
        print(f"\n[+] Downloading TRUE highest quality YouTube video via yt-dlp: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info and download
            info_dict = ydl.extract_info(url, download=True)
            
            # Get the path where yt-dlp originally downloaded the files
            downloaded_file_path = ydl.prepare_filename(info_dict)
            
            # Because we force FFmpeg to merge into an MP4, the final file 
            # will definitely end in .mp4, so we update the path string to match.
            base_path, _ = os.path.splitext(downloaded_file_path)
            mp4_path = f"{base_path}.mp4"
            
            if not os.path.exists(downloaded_file_path) and os.path.exists(mp4_path):
                downloaded_file_path = mp4_path
                
            print(f"[✔] Download and FFmpeg merge completed: {downloaded_file_path}")
            return downloaded_file_path

    except Exception as e:
        print(f"[-] An error occurred during YouTube download: {e}")
        raise
