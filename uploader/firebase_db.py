import firebase_admin

from firebase_admin import credentials

from firebase_admin import firestore

from config import FIREBASE_CREDENTIALS


if not firebase_admin._apps:

    cred = credentials.Certificate(
        FIREBASE_CREDENTIALS
    )

    firebase_admin.initialize_app(cred)


db = firestore.client()


UPLOADS = "uploadedFiles"

SESSIONS = "uploadSessions"


def add_file(file_data):

    db.collection(

        UPLOADS

    ).add(file_data)



def get_upload_session(session_id):

    doc = db.collection(

        SESSIONS

    ).document(

        session_id

    ).get()

    if doc.exists:

        return doc.to_dict()

    return None



def create_upload_session(session):

    db.collection(

        SESSIONS

    ).document(

        session["sessionId"]

    ).set(session)



def update_upload_session(

    session_id,

    updates

):

    ref = db.collection(

        SESSIONS

    ).document(

        session_id

    )

    doc = ref.get()

    if not doc.exists:

        return

    data = doc.to_dict()

    data.update(updates)

    ref.set(data)



def delete_upload_session(

    session_id

):

    db.collection(

        SESSIONS

    ).document(

        session_id

    ).delete()



def get_all_sessions():

    docs = db.collection(

        SESSIONS

    ).stream()

    return [

        doc.to_dict()

        for doc in docs

    ]
