import os

from drive import (
    list_files,
    download_file
)

from uploader import (
    upload_file
)


def main():

    print("\nFetching Google Drive files...\n")

    files = list_files()

    print(f"Found {len(files)} files.\n")

    for index,file in enumerate(files,1):

        print("="*70)
        print(f"[{index}/{len(files)}] {file['name']}")
        print("="*70)

        temp_path = download_file(file)

        try:

            upload_file(temp_path)

        except Exception as e:

            print(f"\n❌ {file['name']}")

            print(e)

        finally:

            if os.path.exists(temp_path):

                os.remove(temp_path)

    print("\n✅ Finished")


if __name__ == "__main__":

    main()
