import os
import re
import json
import subprocess
import tempfile
from urllib.parse import unquote, urlparse, parse_qs
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
    
    cmd = [
        "ffmpeg",
        "-y",
        "-i", url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        download_path
    ]
    
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg failed to download stream. Error:\n{process.stderr}")

def download_from_url(url, filename=None, headers=None):
    # Initialize headers dictionary if not passed
    headers = headers or {}
    
    # Add a standard browser User-Agent to prevent basic bot blocking
    if "User-Agent" not in headers:
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # --- AUTO-EXTRACT EMBEDDED HEADERS FROM THE URL ---
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # Check if the URL contains a 'headers' query parameter
        if 'headers' in query_params:
            raw_headers_str = query_params['headers'][0]
            # Decode the JSON string embedded inside the URL parameter
            extracted_headers = json.loads(raw_headers_str)
            
            if isinstance(extracted_headers, dict):
                print("Extracted custom authentication headers from URL:")
                for k, v in extracted_headers.items():
                    print(f"  -> {k}: {v}")
                    headers[k] = v  # Inject them (e.g., Origin, Referer)
    except Exception as e:
        print(f"Warning: Failed to parse embedded headers from URL: {e}")
    # --------------------------------------------------

    # 1. Check if the URL is an HLS/m3u8 stream
    if ".m3u8" in url.lower() or "manifest" in url.lower():
        if filename is None:
            clean_url = url.split("?", 1)[0]
            base_name = os.path.basename(clean_url).replace(".m3u8", "")
            filename = f"{base_name or 'video'}.mp4"
            
        download_path = os.path.join(tempfile.gettempdir(), filename)
        
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
