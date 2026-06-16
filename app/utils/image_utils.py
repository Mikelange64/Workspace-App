import uuid
from io import BytesIO

import boto3
from PIL import Image, ImageOps

from app.config import settings


def _get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.s3_region,
        aws_access_key_id=(
            settings.s3_access_key_id.get_secret_value()
            if settings.s3_access_key_id
            else None
        ),
        aws_secret_access_key=(
            settings.s3_secret_access_key.get_secret_value()
            if settings.s3_secret_access_key
            else None
        ),
        endpoint_url=settings.s3_endpoint_url,
    )


def process_profile_image(content: bytes) -> tuple[bytes, str]:
    with Image.open(BytesIO(content)) as original:
        img = ImageOps.exif_transpose(original)

        # crop image to 300x300
        img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)

        # convert to RGB
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        # give it a unique uuid name
        filename = f"{uuid.uuid4().hex}.jpeg"

        output = BytesIO()

        # Now we save to the ouput, which is just bytes
        img.save(output, "JPEG", quality=85, optimize=True)

        # we reset it to the beginning so we can read from it
        output.seek(0)

        # return the filename so we can properly store it
        return output.read(), filename


def _upload_to_s3(file_bytes: bytes, key: str) -> None:
    s3 = _get_s3_client()
    s3.upload_fileobj(
        BytesIO(file_bytes),
        settings.s3_bucket_name,
        key,
        ExtraArgs={"ContentType": "image/jpeg"},
    )


def _delete_from_s3(key: str) -> None:
    s3 = _get_s3_client()
    s3.delete_object(Bucket=settings.s3_bucket_name, Key=key)


def upload_profile_image(file_bytes: bytes, filename: str) -> None:
    key = f"profile_pics/{filename}"
    _upload_to_s3(file_bytes, key)


def delete_profile_image(filename: str | None) -> None:
    if filename is None:
        return
    key = f"profile_pics/{filename}"
    _delete_from_s3(key)
