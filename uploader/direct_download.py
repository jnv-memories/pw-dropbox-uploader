import os
import re
import json
import subprocess
import tempfile
from urllib.parse import unquote, urlparse, parse_qs
from curl_cffi import requests
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

def download_hls_stream(url, download_path, headers=None):
    print(f"\n[+] HLS stream detected. Downloading via FFmpeg to {download_path}...")
    
    cmd = ["ffmpeg", "-y"]
    
    if headers:
        # Strip encoding headers to prevent FFmpeg decoding errors
        safe_headers = {k: v for k, v in headers.items() if k.lower() not in ['accept-encoding']}
        header_str = "".join([f"{k}: {v}\r\n" for k, v in safe_headers.items()])
        cmd.extend(["-headers", header_str])
        
    cmd.extend([
        "-analyzeduration", "30000000",
        "-probesize", "30000000",
        "-i", url,
        "-c:v", "copy",
        "-c:a", "aac",
        "-ar", "44100",
        "-ac", "2",
        "-bsf:a", "aac_adtstoasc",
        download_path
    ])
    
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg failed to download stream. Error:\n{process.stderr}")

def extract_nested_headers(url_string):
    current_url = url_string
    
    for _ in range(4):
        parsed = urlparse(current_url)
        params = parse_qs(parsed.query)
        
        if 'headers' in params:
            try:
                header_data = json.loads(params['headers'][0])
                if isinstance(header_data, dict):
                    return header_data
            except Exception:
                pass
                
        inner_url_key = next((k for k in params if k.lower() == 'url'), None)
        if inner_url_key:
            current_url = unquote(params[inner_url_key][0])
        else:
            decoded_query = unquote(parsed.query)
            if 'headers=' in decoded_query:
                match = re.search(r'headers=(.*?)(?:&|$)', decoded_query)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except Exception:
                        pass
            break
            
    return {}

def is_youtube_url(url):
    """Helper function to detect YouTube and direct Google Video domains."""
    return any(domain in url.lower() for domain in ['youtube.com', 'youtu.be', 'googlevideo.com'])

def download_from_url(url, filename=None, headers=None):
    headers = headers or {}
    
    # Let curl_cffi handle all complex browser headers dynamically.
    # Only supply basic fallbacks if they don't exist.
    base_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    for key, value in base_headers.items():
        if key.lower() not in [k.lower() for k in headers.keys()]:
            headers[key] = value

    try:
        extracted = extract_nested_headers(url)
        if extracted:
            print("\n[✔] Extracted authentication headers from URL parameters.")
            for k, v in extracted.items():
                headers[k] = v
    except Exception:
        pass

    # Inject required auth context for raw YouTube/GoogleVideo streams
    if is_youtube_url(url):
        if not any(k.lower() == 'referer' for k in headers.keys()):
            headers['Referer'] = 'https://www.youtube.com/'
        if not any(k.lower() == 'origin' for k in headers.keys()):
            headers['Origin'] = 'https://www.youtube.com'

    # 2. ROUTE: HLS/m3u8 Stream Downloader (Requires FFmpeg)
    if ".m3u8" in url.lower() or "manifest" in url.lower():
        if filename is None:
            clean_url = url.split("?", 1)[0]
            base_name = os.path.basename(clean_url)
            base_name = base_name.replace(".m3u8", "").replace(".mkv", "")
            filename = f"{base_name or 'video'}.mp4"
            
        download_path = os.path.join(tempfile.gettempdir(), filename)
        
        if not download_path.lower().endswith('.mp4'):
            base, _ = os.path.splitext(download_path)
            download_path = f"{base}.mp4"
        
        base, ext = os.path.splitext(download_path)
        counter = 1
        while os.path.exists(download_path):
            download_path = f"{base} ({counter}){ext}"
            counter += 1
            
        download_hls_stream(url, download_path, headers)
        return download_path

    # 3. ROUTE: Standard File Download (No FFmpeg Required)
    print(f"\n[+] Standard file detected. Sending request to URL...")
    
    response = requests.get(
        url,
        headers=headers,
        stream=True,
        allow_redirects=True,
        timeout=None,
        impersonate="chrome120"
    )
    response.raise_for_status()
    
    if filename is None:
        filename = _filename_from_response(response, response.url)
        filename = filename.replace(".mkv", "") 
        
        # Ensure raw YouTube stream files receive a proper extension
        if "videoplayback" in filename and "." not in filename:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            if "mime" in qs and "audio" in qs["mime"][0]:
                filename += ".m4a"
            else:
                filename += ".mp4"

        if len(filename) > 100:
            ext = os.path.splitext(filename)[1] or ".bin"
            filename = f"downloaded_file{ext}"
        
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
        desc=f"Downloading {filename}"
    ) as bar:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                fp.write(chunk)
                bar.update(len(chunk))
            
    return download_path
