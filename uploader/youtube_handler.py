import os
import subprocess
import tempfile
from curl_cffi import requests
from tqdm import tqdm

def _strip_href_li(url):
    """Removes the href.li redirector prefix to get the raw googlevideo link."""
    if "href.li/?" in url:
        return url.split("href.li/?")[-1]
    return url

def fetch_api_data(payload_body):
    """Sends the POST request to the API to get stream links."""
    url = "https://sgm.adem.my.id/system/aee8aa08f175a1cd21b66709f5481bf4e65a8498fa81ebd263de4f72f19b40e9.php"
    headers = {
        "accept": "*/*",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "Referer": "https://pastedownload.com/"
    }

    print("[*] Contacting API for links... (This takes ~30 seconds, please wait)")
    
    # timeout=120 ensures the connection doesn't drop while waiting for the 30s response
    response = requests.post(
        url, 
        headers=headers, 
        data=payload_body, 
        timeout=120, 
        impersonate="chrome120"
    )
    response.raise_for_status()
    
    return response.json()

def download_stream(url, filepath, desc="Downloading"):
    """Downloads a single stream (audio or video) with a progress bar."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.youtube.com/",
        "Origin": "https://www.youtube.com"
    }
    
    response = requests.get(url, headers=headers, stream=True, impersonate="chrome120")
    response.raise_for_status()
    
    total = int(response.headers.get("content-length", 0))
    with open(filepath, "wb") as fp, tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        desc=desc
    ) as bar:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                fp.write(chunk)
                bar.update(len(chunk))
    return filepath

def combine_with_ffmpeg(video_path, audio_path, output_path):
    """Combines video and audio losslessly using ffmpeg."""
    print("\n[*] Combining video and audio streams using FFmpeg...")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",   # Copy video stream directly (no re-encoding)
        "-c:a", "copy",   # Copy audio stream directly
        output_path
    ]
    
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg failed to combine streams. Error:\n{process.stderr}")
    print("[+] Streams successfully merged!")

def process_youtube_payload(payload_body):
    """Main function: Fetches links, downloads both streams, combines them, and cleans up."""
    # 1. Get Links from your API
    data = fetch_api_data(payload_body)
    
    title = data.get("title", "YouTube_Video")
    # Clean the title to prevent file path errors
    safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_")
    
    links = data.get("links", [])
    
    video_url = None
    audio_url = None
    
    # 2. Parse for the M4A Audio and 1080P Video
    for link in links:
        if link.get("type") == "m4a":
            audio_url = _strip_href_li(link.get("url"))
        elif link.get("quality") == "1080P" and link.get("type") == "mp4":
            video_url = _strip_href_li(link.get("url"))
            
    # Fallback to 720p if 1080p is not available for this video
    if not video_url:
        for link in links:
            if link.get("quality") == "720P" and link.get("type") == "mp4":
                video_url = _strip_href_li(link.get("url"))
                
    if not video_url or not audio_url:
        raise ValueError("Could not extract both video and audio URLs from the API response.")

    print(f"\n[+] Title: {title}")
    
    temp_dir = tempfile.gettempdir()
    video_temp = os.path.join(temp_dir, f"{safe_title}_vid.mp4")
    audio_temp = os.path.join(temp_dir, f"{safe_title}_aud.m4a")
    final_output = os.path.join(temp_dir, f"{safe_title}.mp4")
    
    try:
        # 3. Download Streams
        download_stream(video_url, video_temp, desc="Downloading Video Stream")
        download_stream(audio_url, audio_temp, desc="Downloading Audio Stream")
        
        # 4. Combine Streams
        combine_with_ffmpeg(video_temp, audio_temp, final_output)
        
        return final_output
        
    finally:
        # 5. Cleanup raw streams to save disk space
        if os.path.exists(video_temp):
            os.remove(video_temp)
        if os.path.exists(audio_temp):
            os.remove(audio_temp)

# === TEST BLOCK ===
if __name__ == "__main__":
    # Paste your raw body payload here
    test_payload = "url=https%3A%2F%2Fyoutu.be%2FeIoSUSfl3Ks%3Fsi%3D3Y3CB0wiNOqoTzFL&token=Chrome&t1=4yj33Zlavj&t2=j4nDtNWQTf%3D%3D%3DUS&t3=rmD8byJ6wH&t4=zKSDX1cVZV"
    
    try:
        final_file = process_youtube_payload(test_payload)
        print(f"\n[✔] Process complete. Final merged file ready for upload: {final_file}")
    except Exception as e:
        print(f"Error: {e}")
