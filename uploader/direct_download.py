import os
import tempfile
import requests
import re
from urllib.parse import unquote

from tqdm import tqdm


def _filename_from_response(response, url):
    cd = response.headers.get("content-disposition", "")

    if cd:
        # RFC 5987: filename*=UTF-8''...
        m = re.search(r"filename\*\s*=\s*([^']*)''([^;]+)", cd, re.I)
        if m:
            return unquote(m.group(2))

        # Normal filename="..."
        m = re.search(r'filename\s*=\s*"([^"]+)"', cd, re.I)
        if m:
            return m.group(1)

        # filename=...
        m = re.search(r'filename\s*=\s*([^;]+)', cd, re.I)
        if m:
            return m.group(1).strip("\"' ")

    # Fallback to URL
    name = os.path.basename(url.split("?", 1)[0])
    return name or "download.bin"


def download_from_url(
    url,
    filename=None,
    headers=None
):

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
        filename = _filename_from_response(
            response,
            url
        )

    suffix = os.path.splitext(filename)[1]

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    )

    total = int(
        response.headers.get(
            "content-length",
            0
        )
    )

    with open(temp.name, "wb") as fp, tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        desc=f"Download {filename}"
    ) as bar:

        for chunk in response.iter_content(
            1024 * 1024
        ):

            if not chunk:
                continue

            fp.write(chunk)

            bar.update(len(chunk))

    return temp.name
