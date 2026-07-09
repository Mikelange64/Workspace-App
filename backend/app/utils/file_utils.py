import uuid
from io import BytesIO
from app.config import settings
import filetype
from PIL import Image, ImageOps
from app.utils.image_utils import _get_s3_client

# filetype.guess() sniffs magic bytes; plain text has none, so it's detected
# via a UTF-8 decode fallback in process_file() instead of appearing here.
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # .docx
    "application/vnd.oasis.opendocument.text", # .odt
    "application/vnd.ms-powerpoint", # .ppt
    "application/vnd.openxmlformats-officedocument.presentationml.presentation", # .pptx
    "application/vnd.ms-excel", # .xls
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", # .xlsx
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "text/plain",
}

def process_file(content: bytes, original_filename: str) -> tuple[bytes, str, str]:
    kind = filetype.guess(content)

    if kind is not None:
        mime = kind.mime
        extension = kind.extension
    else:
        # No magic bytes matched. Decoding as UTF-8 only proves the content
        # *could* be text - CSV/JSON/HTML/Markdown/source code all pass that
        # check too. Requiring a .txt extension as well keeps this to what
        # it's meant for (plain-text notes), not "any text-based format".
        if not original_filename.lower().endswith(".txt"):
            raise ValueError("Unable to determine file type")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Unable to determine file type")
        mime = "text/plain"
        extension = "txt"

    if mime not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Unsupported file type: {mime}")

    filename = f"{uuid.uuid4().hex}.{extension}"

    return content, filename, mime


MAX_IMAGE_DIMENSION = 2000

_PIL_FORMAT_BY_MIME = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


def normalize_image(content: bytes, mime: str) -> bytes:
    """Re-encode an uploaded image to strip EXIF/metadata (privacy - phone
    photos often carry GPS) and re-derive it from real pixel data (defense
    in depth against malformed/polyglot files), capping oversized photos.

    Skips GIFs: Pillow's save collapses an animated GIF to its first frame,
    so normalizing would silently destroy the animation.
    """
    if mime == "image/gif":
        return content

    with Image.open(BytesIO(content)) as original:
        img = ImageOps.exif_transpose(original)

        if max(img.size) > MAX_IMAGE_DIMENSION:
            img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)

        pil_format = _PIL_FORMAT_BY_MIME[mime]

        # JPEG has no alpha channel - flatten transparency rather than erroring.
        if pil_format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        output = BytesIO()
        img.save(output, pil_format, quality=90, optimize=True)
        output.seek(0)
        return output.read()


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