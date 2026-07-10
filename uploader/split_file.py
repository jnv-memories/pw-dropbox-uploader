import math
import os
import tempfile

from config import CHUNK_SIZE


def split_file(

    file_path,

    chunk_size=CHUNK_SIZE

):

    file_size = os.path.getsize(file_path)

    total_chunks = math.ceil(

        file_size /

        chunk_size

    )

    file_name = os.path.basename(file_path)

    chunks = []

    with open(file_path, "rb") as fp:

        index = 0

        while True:

            data = fp.read(chunk_size)

            if not data:

                break

            part_no = str(

                index + 1

            ).zfill(4)

            total_no = str(

                total_chunks

            ).zfill(4)

            part_name = (

                f"{file_name}"

                f".part"

                f"{part_no}"

                f"of"

                f"{total_no}"

            )

            tmp = tempfile.NamedTemporaryFile(

                delete=False,

                suffix=".part"

            )

            tmp.write(data)

            tmp.close()

            chunks.append({

                "index": index,

                "name": part_name,

                "path": tmp.name,

                "size": len(data)

            })

            index += 1

    return chunks
