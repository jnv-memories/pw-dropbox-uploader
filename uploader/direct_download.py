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
        header_str = "".join([f"{k}: {v}\r\n" for k, v in headers.items()])
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
    """Helper function to detect YouTube domains."""
    return any(domain in url.lower() for domain in ['youtube.com', 'youtu.be'])

def download_from_url(url, filename=None, headers=None):

    # Prepare standard headers for normal downloads & HLS
    headers = headers or {}
    browser_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "upgrade-insecure-requests": "1"
    }
    
    for key, value in browser_headers.items():
        if key not in headers:
            headers[key] = value

    try:
        extracted = extract_nested_headers(url)
        if extracted:
            print("\n[✔] Extracted authentication headers from URL parameters.")
            for k, v in extracted.items():
                headers[k] = v
    except Exception as e:
        pass

    # 2. ROUTE: HLS/m3u8 Stream Downloader (Requires FFmpeg)
    if ".m3u8" in url.lower() or "manifest" in url.lower():
        if filename is None:
            clean_url = url.split("?", 1)[0]
            base_name = os.path.basename(clean_url)
            base_name = base_name.replace(".m3u8", "").replace(".mkv", "")
            filename = f"{base_name or 'video'}.mp4"
            
        download_path = os.path.join(tempfile.gettempdir(), filename)
        
        # Enforce .mp4 for HLS streams explicitly
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
        if len(filename) > 100:
            # Fallback for extremely long generic names
            ext = os.path.splitext(filename)[1] or ".bin"
            filename = f"downloaded_file{ext}"
        
        # [FIX]: Removed the logic forcing `.mp4` onto standard files here. 
        # Standard files (like .js, .pdf, .zip) will now retain their original extension.
        
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
