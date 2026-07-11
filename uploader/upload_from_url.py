import os
import traceback

from direct_download import download_from_url
from uploader import upload_file

from firebase_db import (
    get_pending_jobs,
    update_download_job
)


def main():

    jobs = get_pending_jobs()

    if not jobs:

        print()
        print("No pending download jobs.")
        print()

        return

    print()
    print("=" * 70)
    print(f"Found {len(jobs)} pending job(s).")
    print("=" * 70)
    print()

    for index, job in enumerate(jobs, 1):

        job_id = job["jobId"]
        url = job["url"]
        folder_id = job.get("folderId")

        print("=" * 70)
        print(f"[{index}/{len(jobs)}]")
        print(url)
        print("=" * 70)

        update_download_job(
            job_id,
            {
                "status": "downloading"
            }
        )

        temp_path = None

        try:

            temp_path = download_from_url(url)

            update_download_job(
                job_id,
                {
                    "status": "uploading"
                }
            )

            upload_file(
                temp_path,
                folder_id
            )

            update_download_job(
                job_id,
                {
                    "status": "completed"
                }
            )

        except Exception:

            traceback.print_exc()

            update_download_job(
                job_id,
                {
                    "status": "failed"
                }
            )

        finally:

            if temp_path and os.path.exists(temp_path):

                os.remove(temp_path)

    print()
    print("Finished.")
    print()


if __name__ == "__main__":

    main()
