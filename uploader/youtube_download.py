import os
import subprocess
import tempfile
import uuid
from pytubefix import YouTube
from pytubefix.cli import on_progress

def download_youtube_video(url, filename=None):
    try:
        yt = YouTube(url, 'WEB', on_progress_callback=on_progress)
        print(f"\n[+] Downloading YouTube video: {yt.title}")

        video_stream = yt.streams.get_highest_resolution(False)
        print(f"Selected video stream: {video_stream.resolution} ({video_stream.fps}fps)")

        temp_dir = tempfile.gettempdir()
        
        # Sanitize title for filename if none is provided
        if not filename:
            safe_title = "".join(c for c in yt.title if c.isalnum() or c in " ._-").rstrip()
            filename = f"{safe_title}.mp4"
            
        output_path = os.path.join(temp_dir, filename)

        # Ensure unique filename if it already exists
        base, ext = os.path.splitext(output_path)
        counter = 1
        while os.path.exists(output_path):
            output_path = f"{base} ({counter}){ext}"
            counter += 1

        if not video_stream.is_progressive:
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            if not audio_stream:
                raise Exception('No suitable audio stream found.')

            print(f"Selected audio stream: {audio_stream.abr}")

            # Use UUIDs to prevent file collisions if multiple jobs run
            uid = uuid.uuid4().hex
            video_temp_name = f"temp_video_{uid}.mp4"
            audio_temp_name = f"temp_audio_{uid}.mp4"

            video_path = video_stream.download(output_path=temp_dir, filename=video_temp_name)
            audio_path = audio_stream.download(output_path=temp_dir, filename=audio_temp_name)

            print("Combining video and audio streams with ffmpeg...")
            subprocess.run([
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-strict', 'experimental',
                output_path
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Clean up temporary streams
            os.remove(video_path)
            os.remove(audio_path)
            
            print(f"[✔] Download and merge completed: {output_path}")
        else:
            video_stream.download(output_path=temp_dir, filename=os.path.basename(output_path))
            print(f"[✔] Download completed: {output_path}")
            
        return output_path

    except Exception as e:
        print(f"[-] An error occurred during YouTube download: {e}")
        raise
