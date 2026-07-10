import os
import tempfile
import requests

from tqdm import tqdm


def _filename_from_response(response, url):

    cd = response.headers.get("content-disposition")

    if cd and "filename=" in cd:
        name = cd.split("filename=")[-1].strip("\"'")
        if name:
            return name

    name = url.split("?")[0].split("/")[-1]

    if name:
        return name

    return "download.bin"


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
