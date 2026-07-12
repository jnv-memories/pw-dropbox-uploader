import os
import re
import subprocess
import tempfile
from urllib.parse import unquote
import requests
from tqdm import tqdm

def _filename_from_response(response, url):
    cd = response.headers.get("content-disposition", "")
    if cd:
        m = re.search(r"filename\*\s*=\s*([^']*)''([^;]+)", cd, re.I)
        if m:
            return unquote(m.group(2))
        m = re.search(r'filename\s*=\s*"([^"]+)"', cd, re.I)
        if m:
            return m.group(1)
        m = re.search(r'filename\s*=\s*([^;]+)', cd, re.I)
        if m:
            return m.group(1).strip("\"' ")
    name = os.path.basename(url.split("?", 1)[0])
    return name or "download.bin"

def download_hls_stream(url, download_path):
    """Downloads an HLS stream (.m3u8) using system FFmpeg."""
    print(f"HLS stream detected. Downloading via FFmpeg to {download_path}...")
    
    # -y overwrites the file if it somehow exists
    # -c copy copies the video/audio streams without re-encoding (very fast)
    cmd = [
        "ffmpeg",
        "-y",
        "-i", url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",  # Fixes potential audio sync issues in MP4 containers
        download_path
    ]
    
    # Run the command and redirect stderr/stdout to monitor errors if they happen
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg failed to download stream. Error:\n{process.stderr}")

def download_from_url(url, filename=None, headers=None):
    headers = headers or {}
    
    # 1. Check if the URL is an HLS/m3u8 stream
    if ".m3u8" in url.lower() or "manifest" in url.lower():
        if filename is None:
            # Strip query params to guess a decent name, default to video.mp4
            clean_url = url.split("?", 1)[0]
            base_name = os.path.basename(clean_url).replace(".m3u8", "")
            filename = f"{base_name or 'video'}.mp4"
            
        download_path = os.path.join(tempfile.gettempdir(), filename)
        
        # Handle duplicate filenames in temp folder
        base, ext = os.path.splitext(download_path)
        counter = 1
        while os.path.exists(download_path):
            download_path = f"{base} ({counter}){ext}"
            counter += 1
            
        download_hls_stream(url, download_path)
        return download_path

    # 2. Fallback to standard HTTP download logic for regular files
    response = requests.get(
        url,
        headers=headers,
        stream=True,
        allow_redirects=True,
        timeout=None
    )
    response.raise_for_status()
    
    if filename is None:
        filename = _filename_from_response(response, response.url)
        
    download_path = os.path.join(tempfile.gettempdir(), filename)
    base, ext = os.path.splitext(download_path)
    counter = 1
    while os.path.exists(download_path):
        download_path = f"{base} ({counter}){ext}"
        counter += 1
        
    total = int(response.headers.get("content-length", 0))
    with open(download_path, "wb") as fp, tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        desc=f"Download {filename}"
    ) as bar:
        for chunk in response.iter_content(1024 * 1024):
            if not chunk:
                continue
            fp.write(chunk)
            bar.update(len(chunk))
            
    return download_path
