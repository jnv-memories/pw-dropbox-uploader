import os
import json
import mimetypes
import time
import requests

from tqdm import tqdm

from requests_toolbelt.multipart.encoder import (
    MultipartEncoder,
    MultipartEncoderMonitor
)

from config import (
    UPLOAD_URL,
    HEADERS,
    MULTIPART_LIMIT,
    UPLOAD_RETRY_COUNT
)

from split_file import split_file

from firebase_db import add_file

from session_manager import (
    load_or_create_session,
    save_uploaded_part,
    finish_session,
    uploaded_bytes
)

# Firestore folder document id
#FOLDER_ID = "NWCQ2SOM1yZiice05vTN"

def get_file_type(file_name):
    return (
        mimetypes.guess_type(file_name)[0]
        or
        "application/octet-stream"
    )


def upload_single_part(
    path,
    upload_name,
    progress_callback=None
):

    with open(path, "rb") as fp:

        encoder = MultipartEncoder(

            fields={
                "image":(
                    upload_name,
                    fp,
                    mimetypes.guess_type(upload_name)[0] or "application/octet-stream"
                )
            }

        )

        started = time.time()

        def callback(monitor):

            if progress_callback is None:
                return

            elapsed=max(
                time.time()-started,
                0.001
            )

            loaded=monitor.bytes_read

            total=encoder.len

            speed=loaded/elapsed

            eta=(total-loaded)/speed if speed else 0

            progress_callback(

                loaded,
                total,
                speed,
                eta

            )

        monitor=MultipartEncoderMonitor(
            encoder,
            callback
        )

        headers=HEADERS.copy()

        headers[
            "Content-Type"
        ]=monitor.content_type

        response=requests.post(

            UPLOAD_URL,

            headers=headers,

            data=monitor,

            timeout=None

        )

    response.raise_for_status()

    data=response.json()["data"]

    return {

        "_id":data["_id"],

        "url":data["baseUrl"]+data["key"],

        "createdAt":data["createdAt"]

    }



def upload_file(file_path,FOLDER_ID):

    file_size=os.path.getsize(file_path)

    file_name=os.path.basename(file_path)


    if file_size<=MULTIPART_LIMIT:

        session=load_or_create_session(

            file_path,

            [

                {

                    "size":file_size

                }

            ],

            False

        )

        bar=tqdm(

            total=file_size,

            unit="B",

            unit_scale=True,

            desc=f"Upload {file_name}"

        )

        previous=0

        def progress(

            loaded,

            total,

            speed,

            eta

        ):

            nonlocal previous

            bar.update(

                loaded-previous

            )

            previous=loaded

            bar.set_postfix(

                speed=f"{speed/1024/1024:.2f} MB/s",

                eta=f"{eta:.0f}s"

            )

        result=upload_single_part(

            file_path,

            file_name,

            progress

        )

        bar.close()

        add_file({

            "id":result["_id"],

            "_id":result["_id"],

            "multipart":False,
            "folderId":FOLDER_ID,

            "name":file_name,

            "url":result["url"],

            "createdAt":result["createdAt"],

            "size":file_size,

            "type":get_file_type(file_name)

        })

        finish_session(session)

        return


    chunks=split_file(file_path)

    session=load_or_create_session(

        file_path,

        chunks,

        True

    )

    parts=session["parts"]

    uploaded=uploaded_bytes(session)

    overall=tqdm(

        total=file_size,

        initial=uploaded,

        unit="B",

        unit_scale=True,

        desc=file_name

    )

    started=time.time()

    for i in range(

        session["nextChunk"],

        len(chunks)

    ):

        chunk=chunks[i]

        retry=0

        while True:

            try:

                previous=0

                def progress(

                    loaded,

                    total,

                    speed,

                    eta

                ):

                    nonlocal previous

                    overall.update(

                        loaded-previous

                    )

                    previous=loaded

                    uploaded_now=uploaded+loaded

                    elapsed=max(

                        time.time()-started,

                        0.001

                    )

                    overall_speed=uploaded_now/elapsed

                    remaining=file_size-uploaded_now

                    overall_eta=remaining/overall_speed if overall_speed else 0

                    overall.set_postfix(

                        speed=f"{overall_speed/1024/1024:.2f} MB/s",

                        eta=f"{overall_eta:.0f}s"

                    )

                result=upload_single_part(

                    chunk["path"],

                    chunk["name"],

                    progress

                )

                uploaded+=chunk["size"]

                save_uploaded_part(

                    session,

                    i,

                    result["_id"],

                    result["url"],

                    chunk["size"]

                )

                break

            except Exception:

                retry+=1

                if retry>UPLOAD_RETRY_COUNT:

                    raise

        os.remove(

            chunk["path"]

        )

    overall.close()

    add_file({

        "id":"virtual-"+session["sessionId"],

        "multipart":True,
        "folderId":FOLDER_ID,

        "name":file_name,

        "size":file_size,

        "type":get_file_type(file_name),

        "createdAt":session["createdAt"],

        "parts":session["parts"]

    })

    finish_session(session)
