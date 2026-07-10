import os

from direct_download import download_from_url
from uploader import upload_file


def get_urls():

    urls = []

    #
    # Multiple URLs from GitHub Actions:
    #
    # DIRECT_URLS:
    #   https://example.com/file1.mp4
    #   https://example.com/file2.mkv
    #

    direct_urls = os.getenv(
        "DIRECT_URLS",
        ""
    ).strip()

    if direct_urls:

        for line in direct_urls.splitlines():

            line = line.strip()

            if line:

                urls.append(line)

    #
    # Single URL support:
    #
    # DIRECT_URL=https://example.com/file.mp4
    #

    single = os.getenv(
        "DIRECT_URL",
        ""
    ).strip()

    if single:

        urls.append(single)

    #
    # Remove duplicates while keeping order.
    #

    seen = set()

    result = []

    for url in urls:

        if url in seen:
            continue

        seen.add(url)

        result.append(url)

    return result


def main():

    urls = get_urls()

    if not urls:

        print()

        print("No DIRECT_URL or DIRECT_URLS specified.")

        print()

        return

    print()

    print("=" * 70)

    print(f"Found {len(urls)} direct URL(s).")

    print("=" * 70)

    print()

    for index, url in enumerate(urls, 1):

        print("=" * 70)

        print(f"[{index}/{len(urls)}]")

        print(url)

        print("=" * 70)

        temp_path = download_from_url(url)

        try:

            upload_file(temp_path)

        finally:

            if os.path.exists(temp_path):

                os.remove(temp_path)

    print()

    print("Finished.")

    print()


if __name__ == "__main__":

    main()
