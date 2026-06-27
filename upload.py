import os
import json
import tempfile
import requests

from tqdm import tqdm
from requests_toolbelt.multipart.encoder import (
    MultipartEncoder,
    MultipartEncoderMonitor
)

TOKEN = os.environ["PW_TOKEN"]

DROPBOX_URL = os.environ["DROPBOX_URL"]

UPLOAD_URL = "https://api.penpencil.co/v1/files"

headers = {
    "authorization": f"Bearer {TOKEN}"
}


def download_file():

    print("Downloading from Dropbox...")

    r = requests.get(DROPBOX_URL, stream=True)
    r.raise_for_status()

    total = int(r.headers.get("content-length", 0))

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")

    with open(tmp.name, "wb") as f, tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        desc="Download",
    ) as bar:

        for chunk in r.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))

    return tmp.name


def upload(path):

    filename = os.path.basename(path)

    encoder = MultipartEncoder(
        fields={
            "image": (
                filename,
                open(path, "rb"),
                "application/octet-stream",
            )
        }
    )

    bar = tqdm(
        total=encoder.len,
        unit="B",
        unit_scale=True,
        desc="Upload",
    )

    def callback(monitor):
        bar.update(monitor.bytes_read - bar.n)

    monitor = MultipartEncoderMonitor(
        encoder,
        callback,
    )

    headers["Content-Type"] = monitor.content_type

    response = requests.post(
        UPLOAD_URL,
        headers=headers,
        data=monitor,
    )

    bar.close()

    response.raise_for_status()

    result = response.json()

    print(json.dumps(result, indent=4))


def main():

    file = download_file()

    try:
        upload(file)

    finally:
        os.remove(file)


if __name__ == "__main__":
    main()
