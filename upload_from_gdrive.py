import os
import json
import tempfile
import requests

from tqdm import tqdm
from requests_toolbelt.multipart.encoder import (
    MultipartEncoder,
    MultipartEncoderMonitor,
)

PW_TOKEN = os.environ["PW_TOKEN"]
GDRIVE_API_KEY = os.environ["GDRIVE_API_KEY"]

FOLDER_ID = "1ZE68tiDDDsBn5esiPsr75bCm7BE9Aok_nYXAqPvYHCf5KUZLMaXWwTCowUW9foNPtxTkg4TR"

UPLOAD_URL = "https://api.penpencil.co/v1/files"

HEADERS = {
    "authorization": f"Bearer {PW_TOKEN}"
}


def list_files():
    files = []
    page_token = None

    while True:
        params = {
            "q": f"'{FOLDER_ID}' in parents and trashed=false",
            "fields": "nextPageToken,files(id,name,mimeType,size)",
            "pageSize": 1000,
            "key": GDRIVE_API_KEY,
        }

        if page_token:
            params["pageToken"] = page_token

        r = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            params=params,
        )
        r.raise_for_status()

        data = r.json()

        files.extend(data.get("files", []))
        page_token = data.get("nextPageToken")

        if not page_token:
            break

    return files


def download_file(file):
    url = f"https://www.googleapis.com/drive/v3/files/{file['id']}?alt=media&key={GDRIVE_API_KEY}"

    r = requests.get(url, stream=True)
    r.raise_for_status()

    suffix = os.path.splitext(file["name"])[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

    total = int(r.headers.get("content-length", 0))

    with open(tmp.name, "wb") as f, tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        desc=f"Download {file['name']}",
    ) as bar:

        for chunk in r.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))

    return tmp.name


def upload_file(path, original_name):
    with open(path, "rb") as fp:

        encoder = MultipartEncoder(
            fields={
                "image": (
                    original_name,
                    fp,
                    "application/octet-stream",
                )
            }
        )

        progress = tqdm(
            total=encoder.len,
            unit="B",
            unit_scale=True,
            desc=f"Upload {original_name}",
        )

        def callback(monitor):
            progress.update(monitor.bytes_read - progress.n)

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

        progress.close()

    response.raise_for_status()

    print("\nResponse:")
    print(json.dumps(response.json(), indent=4))


def main():

    print("Fetching Google Drive file list...\n")

    files = list_files()

    print(f"Found {len(files)} files.\n")

    for index, file in enumerate(files, start=1):

        print("=" * 70)
        print(f"[{index}/{len(files)}] {file['name']}")
        print("=" * 70)

        temp_path = download_file(file)

        try:
            upload_file(temp_path, file["name"])
        except Exception as e:
            print(f"❌ Failed: {e}")
        finally:
            os.remove(temp_path)

    print("\nAll files processed.")


if __name__ == "__main__":
    main()
