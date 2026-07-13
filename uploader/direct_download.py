import os
import re
import json
import subprocess
import tempfile
import urllib.parse
from urllib.parse import unquote, urlparse, parse_qs
from curl_cffi import requests
from tqdm import tqdm

# ==========================================
# STANDARD & HLS HELPER FUNCTIONS
# ==========================================

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

def download_hls_stream(url, download_path, headers=None):
    print(f"\n[+] HLS stream detected. Downloading via FFmpeg to {download_path}...")
    cmd = ["ffmpeg", "-y"]
    if headers:
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

def is_youtube_url(url):
    """Detects if the incoming string is a standard YouTube link."""
    return any(domain in url.lower() for domain in ['youtube.com', 'youtu.be'])

# ==========================================
# YOUTUBE API / MERGE LOGIC
# ==========================================

def _strip_href_li(url):
    """Strips the href.li redirect wrapper to get the raw googlevideo link."""
    if "href.li/?" in url:
        return url.split("href.li/?")[-1]
    return url

def fetch_api_data(youtube_url):
    """URL-encodes the YouTube link, attaches tokens, and fetches the JSON payload."""
    api_endpoint = "https://sgm.adem.my.id/system/aee8aa08f175a1cd21b66709f5481bf4e65a8498fa81ebd263de4f72f19b40e9.php"
    
    # URL encode the user's youtube link
    encoded_url = urllib.parse.quote(youtube_url, safe='')
    
    # Construct the body with the specific tokens you provided
    payload_body = f"url={encoded_url}&token=Chrome&t1=4yj33Zlavj&t2=j4nDtNWQTf%3D%3D%3DUS&t3=rmD8byJ6wH&t4=zKSDX1cVZV"
    
    headers = {
        "accept": "*/*",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "Referer": "https://pastedownload.com/"
    }

    print("[*] Contacting PasteDownload API for links... (Waiting ~30s)")
    response = requests.post(
        api_endpoint, 
        headers=headers, 
        data=payload_body, 
        timeout=120, 
        impersonate="chrome120"
    )
    response.raise_for_status()
    return response.json()

def download_youtube_stream(url, filepath, desc="Downloading"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.youtube.com/",
        "Origin": "https://www.youtube.com"
    }
    
    response = requests.get(url, headers=headers, stream=True, impersonate="chrome120")
    response.raise_for_status()
    
    total = int(response.headers.get("content-length", 0))
    with open(filepath, "wb") as fp, tqdm(total=total, unit="B", unit_scale=True, desc=desc) as bar:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                fp.write(chunk)
                bar.update(len(chunk))
    return filepath

def combine_with_ffmpeg(video_path, audio_path, output_path):
    print("\n[*] Combining video and audio streams using FFmpeg...")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "copy",
        output_path
    ]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg failed to combine streams. Error:\n{process.stderr}")
    print("[+] Streams successfully merged!")

def process_youtube_url(youtube_url):
    """Main pipeline for processing a raw YouTube URL."""
    data = fetch_api_data(youtube_url)
    
    title = data.get("title", "YouTube_Video")
    safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_")
    
    links = data.get("links", [])
    video_url = None
    audio_url = None
    
    # Find M4A Audio and 1080p Video
    for link in links:
        if link.get("type") == "m4a":
            audio_url = _strip_href_li(link.get("url"))
        elif link.get("quality") == "1080P" and link.get("type") == "mp4":
            video_url = _strip_href_li(link.get("url"))
            
    # Fallback to 720p if 1080p doesn't exist
    if not video_url:
        for link in links:
            if link.get("quality") == "720P" and link.get("type") == "mp4":
                video_url = _strip_href_li(link.get("url"))
                
    if not video_url or not audio_url:
        raise ValueError("Could not extract both video and audio URLs from the API response.")

    print(f"\n[+] Detected YouTube Title: {title}")
    
    temp_dir = tempfile.gettempdir()
    video_temp = os.path.join(temp_dir, f"{safe_title}_vid.mp4")
    audio_temp = os.path.join(temp_dir, f"{safe_title}_aud.m4a")
    final_output = os.path.join(temp_dir, f"{safe_title}.mp4")
    
    try:
        download_youtube_stream(video_url, video_temp, desc="Downloading Video Stream")
        download_youtube_stream(audio_url, audio_temp, desc="Downloading Audio Stream")
        combine_with_ffmpeg(video_temp, audio_temp, final_output)
        return final_output
    finally:
        # Delete raw chunks to save disk space
        if os.path.exists(video_temp):
            os.remove(video_temp)
        if os.path.exists(audio_temp):
            os.remove(audio_temp)

# ==========================================
# MAIN ENTRY POINT
# ==========================================

def download_from_url(url, filename=None, headers=None):
    # 1. ROUTE: YouTube Links
    if is_youtube_url(url):
        print("\n[+] YouTube URL detected. Generating API payload and routing to custom handler...")
        return process_youtube_url(url)

    # Prepare standard headers for non-YouTube files
    headers = headers or {}
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

    # 3. ROUTE: Standard File Download
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
