import uuid
from io import BytesIO
from app.config import settings
import filetype
from app.utils.image_utils import _get_s3_client

# filetype.guess() sniffs magic bytes, so plain text (no magic bytes) can
# never match here regardless of what's in this set - only binary formats belong.
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # .docx
    "application/vnd.oasis.opendocument.text", # .odt
    "application/vnd.ms-powerpoint", # .ppt
    "application/vnd.openxmlformats-officedocument.presentationml.presentation", # .pptx
    "application/vnd.ms-excel", # .xls
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", # .xlsx
}

def process_file(content: bytes) -> tuple[bytes, str, str]:
    kind = filetype.guess(content)

    if kind is None:
        raise ValueError("Unable to determine file type")

    mime = kind.mime

    if mime not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Unsupported file type: {mime}")

    filename = f"{uuid.uuid4().hex}{kind.extension}"

    return content, filename, mime


def _upload_to_s3(file_bytes: bytes, key: str, mime:str):
    s3 = _get_s3_client()
    
    s3.upload_fileobj(
        BytesIO(file_bytes),
        settings.s3_bucket_name,
        key,
        ExtraArgs={"ContentType": mime},
    )


def _delete_from_s3(key: str) -> None:
    s3 = _get_s3_client()
    s3.delete_object(Bucket=settings.s3_bucket_name, Key=key)


def upload_file(file_bytes: bytes, filename: str, mime: str) -> None:
    key = f"files/{filename}"
    _upload_to_s3(file_bytes, key, mime)


def delete_file(filename: str | None) -> None:
    if filename is None:
        return
    key = f"files/{filename}"
    _delete_from_s3(key)