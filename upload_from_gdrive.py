import json
import os
import shutil
import tempfile

import gdown
import requests
from requests_toolbelt.multipart.encoder import (
    MultipartEncoder,
    MultipartEncoderMonitor,
)
from tqdm import tqdm

TOKEN = os.environ["PW_TOKEN"]

FOLDER_URL = "https://drive.google.com/drive/folders/1SSIz5CwXskmCAEe3wU9UzZQfB2UgrH6y"

UPLOAD_URL = "https://api.penpencil.co/v1/files"

HEADERS = {
    "authorization": f"Bearer {TOKEN}"
}


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
        desc=f"Uploading {filename}",
    )

    def callback(monitor):
        bar.update(monitor.bytes_read - bar.n)

    monitor = MultipartEncoderMonitor(
        encoder,
        callback,
    )

    headers = HEADERS.copy()
    headers["Content-Type"] = monitor.content_type

    response = requests.post(
        UPLOAD_URL,
        headers=headers,
        data=monitor,
    )

    bar.close()

    response.raise_for_status()

    print(f"\n=== Uploaded {filename} ===")
    print(json.dumps(response.json(), indent=4))


def main():

    temp_dir = tempfile.mkdtemp()

    print("Downloading Google Drive folder...")
    gdown.download_folder(
        url=FOLDER_URL,
        output=temp_dir
    )

    files = []

    for root, _, filenames in os.walk(temp_dir):
        for f in filenames:
            files.append(os.path.join(root, f))

    print(f"\nFound {len(files)} files.\n")

    for path in files:
        try:
            upload(path)
        except Exception as e:
            print(f"Failed: {path}")
            print(e)

    shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()
