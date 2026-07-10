from firebase_db import (
    create_upload_session,
    get_upload_session,
    update_upload_session,
    delete_upload_session
)


def get_session_id(file_path):

    import os

    stat = os.stat(file_path)

    return "_".join([

        os.path.basename(file_path),

        str(stat.st_size),

        str(int(stat.st_mtime))

    ])


def load_or_create_session(

    file_path,

    chunks,

    multipart

):

    import os
    from datetime import datetime

    session_id = get_session_id(file_path)

    session = get_upload_session(session_id)

    if session:

        return session

    stat = os.stat(file_path)

    session = {

        "sessionId": session_id,

        "status": "uploading",

        "multipart": multipart,

        "name": os.path.basename(file_path),

        "size": stat.st_size,

        "lastModified": int(stat.st_mtime),

        "chunkSize": chunks[0]["size"] if multipart else stat.st_size,

        "totalChunks": len(chunks),

        "nextChunk": 0,

        "parts": [],

        "createdAt": datetime.utcnow().isoformat()

    }

    create_upload_session(session)

    return session


def save_uploaded_part(

    session,

    index,

    server_id,

    url,

    size

):

    session["parts"].append({

        "index": index,

        "_id": server_id,

        "url": url,

        "size": size

    })

    session["nextChunk"] = index + 1

    update_upload_session(

        session["sessionId"],

        {

            "parts": session["parts"],

            "nextChunk": session["nextChunk"]

        }

    )


def finish_session(session):

    delete_upload_session(

        session["sessionId"]

    )


def uploaded_bytes(session):

    return sum(

        part["size"]

        for part in session["parts"]

    )
