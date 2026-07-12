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

def extract_nested_headers(url_string):
    """Recursively searches for a 'headers' parameter inside a nested/encoded URL structure."""
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

def download_from_url(url, filename=None, headers=None):
    headers = headers or {}
    
    # Base browser emulation headers matching your exact fetch payload
    browser_headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "priority": "u=0, i",
        "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1"
    }
    
    # Merge browser defaults into our active headers if not overridden
    for key, value in browser_headers.items():
        if key not in headers:
            headers[key] = value

    # Extract any deeply nested query headers (Origin/Referer) and merge them too
    try:
        extracted = extract_nested_headers(url)
        if extracted:
            print("\n[✔] Extracted authentication headers from URL parameters:")
            for k, v in extracted.items():
                print(f"    -> {k}: {v}")
                headers[k] = v
    except Exception as e:
        print(f"\n[!] Warning: Nested header extraction failed: {e}")

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

    # 2. Standard HTTP download logic using the original, un-stripped proxy URL
    print(f"\nSending request to stream proxy URL: {url}")
    print(f"Headers sent: {headers}\n")
    
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
        # Fallback if filename extraction produces the long stream string
        if len(filename) > 100 or "video" in filename.lower():
            filename = "streamed_video.mp4"
        
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
        for chunk in response.iter_content(1024 * 1024):
            if not chunk:
                continue
            fp.write(chunk)
            bar.update(len(chunk))
            
    return download_path
