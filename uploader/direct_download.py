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

def extract_nested_target(url_string):
    """
    Recursively searches for a 'headers' parameter and extracts the final, 
    deepest nested destination URL.
    Returns a tuple: (final_url, extracted_headers_dict)
    """
    current_url = url_string
    extracted_headers = {}
    
    # Loop up to 4 times to unwrap nested parameters safely
    for _ in range(4):
        parsed = urlparse(current_url)
        params = parse_qs(parsed.query)
        
        # 1. Direct match check for headers
        if 'headers' in params:
            try:
                header_data = json.loads(params['headers'][0])
                if isinstance(header_data, dict):
                    extracted_headers = header_data
            except Exception:
                pass
                
        # 2. Check if there's an inner URL parameter we need to dig into next
        inner_url_key = next((k for k in params if k.lower() == 'url'), None)
        if inner_url_key:
            current_url = unquote(params[inner_url_key][0])
        else:
            # If there's no nested 'url' parameter left, try unquoting the entire query raw string
            decoded_query = unquote(parsed.query)
            if 'headers=' in decoded_query:
                match = re.search(r'headers=(.*?)(?:&|$)', decoded_query)
                if match:
                    try:
                        extracted_headers = json.loads(match.group(1))
                    except Exception:
                        pass
            break
            
    return current_url, extracted_headers

def download_from_url(url, filename=None, headers=None):
    headers = headers or {}
    
    # Standard modern browser User-Agent
    if "User-Agent" not in headers:
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    # --- RECURSIVE DECODE FOR EMBEDDED URL & HEADERS ---
    try:
        target_url, extracted_headers = extract_nested_target(url)
        if target_url != url:
            print(f"\n[✔] Extracted True Target URL: {target_url}")
            url = target_url  # Update the main URL to point to the actual stream file
            
        if extracted_headers:
            print("[✔] Successfully extracted authentication headers:")
            for k, v in extracted_headers.items():
                print(f"    -> {k}: {v}")
                headers[k] = v
        else:
            print("\n[!] No embedded headers object detected in the URL parameters.")
    except Exception as e:
        print(f"\n[!] Warning: Nested extraction failed: {e}")
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
    print(f"Sending request to target with headers: {headers}")
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
