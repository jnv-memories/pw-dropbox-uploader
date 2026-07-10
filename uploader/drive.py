import os
import tempfile
import requests

from tqdm import tqdm

from config import (
    GDRIVE_API_KEY,
    FOLDER_ID
)


def list_files():

    files = []

    page_token = None

    while True:

        params = {

            "q": f"'{FOLDER_ID}' in parents and trashed=false",

            "fields": "nextPageToken,files(id,name,mimeType,size)",

            "pageSize": 1000,

            "key": GDRIVE_API_KEY

        }

        if page_token:

            params["pageToken"] = page_token

        response = requests.get(

            "https://www.googleapis.com/drive/v3/files",

            params=params

        )

        response.raise_for_status()

        data = response.json()

        files.extend(

            data.get("files", [])

        )

        page_token = data.get(

            "nextPageToken"

        )

        if not page_token:

            break

    return files


def download_file(file):

    url = (

        f"https://www.googleapis.com/drive/v3/files/"

        f"{file['id']}"

        f"?alt=media"

        f"&key={GDRIVE_API_KEY}"

    )

    response = requests.get(

        url,

        stream=True

    )

    response.raise_for_status()

    suffix = os.path.splitext(

        file["name"]

    )[1]

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

        desc=f"Download {file['name']}"

    ) as bar:

        for chunk in response.iter_content(

            1024 * 1024

        ):

            if not chunk:

                continue

            fp.write(chunk)

            bar.update(

                len(chunk)

            )

    return temp.name
