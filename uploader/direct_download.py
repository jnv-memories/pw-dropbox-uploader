import os
import re
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


def download_from_url(url, filename=None, headers=None):
    headers = headers or {}

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
