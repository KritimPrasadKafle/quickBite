import io
import json
import uuid
from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile, HTTPException, status
import structlog

from core.config import settings

logger = structlog.get_logger()

# ── Client ─────────────────────────────────────────────────────────────────────
# Single client instance, reused across requests. MinIO SDK is sync (no async
# variant), but uploads are fast and IO-bound — fine inside async endpoints for
# your scale. If it ever blocks the event loop under load, wrap calls in
# asyncio.to_thread (noted in upload_image).
minio_client = Minio(
    settings.MINIO_ENDPOINT,            # "minio:9000" in Docker
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False,                       # True when behind HTTPS in prod
)

# ── Validation rules ────────────────────────────────────────────────────────────
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _ensure_bucket() -> None:
    """
    Create the bucket on first use and set a public-read policy so image URLs
    are directly accessible without signed URLs. Idempotent — safe to call on
    every upload (the existence check is a cheap HEAD request).
    """
    if minio_client.bucket_exists(settings.MINIO_BUCKET):
        return

    minio_client.make_bucket(settings.MINIO_BUCKET)

    # Public-read: anyone can GET objects, nobody can list/write without creds.
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{settings.MINIO_BUCKET}/*"],
            }
        ],
    }
    minio_client.set_bucket_policy(settings.MINIO_BUCKET, json.dumps(policy))
    logger.info("minio_bucket_created", bucket=settings.MINIO_BUCKET)


def _validate_image(file: UploadFile, data: bytes) -> str:
    """Validate content-type, size, extension. Returns the safe extension."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed: jpeg, png, webp.",
        )

    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds 5 MB limit.",
        )

    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file.",
        )

    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if ext not in ALLOWED_EXTENSIONS:
        # fall back to mapping from content-type if filename has no/odd extension
        ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[file.content_type]
    return ext


async def upload_image(file: UploadFile, folder: str) -> str:
    """
    Validate and upload an image to MinIO under the given folder prefix.
    Returns the public URL.

    Example:
        url = await upload_image(file, folder=f"restaurants/{restaurant_id}/logo")
        # → http://minio:9000/quickbite/restaurants/<id>/logo/<uuid>.jpg
    """
    data = await file.read()
    ext = _validate_image(file, data)

    object_name = f"{folder}/{uuid.uuid4()}.{ext}"

    try:
        _ensure_bucket()
        # If this ever blocks under load:
        #   await asyncio.to_thread(minio_client.put_object, ...)
        minio_client.put_object(
            settings.MINIO_BUCKET,
            object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=file.content_type,
        )
    except S3Error as e:
        logger.error("minio_upload_failed", object_name=object_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed.",
        )

    return f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{object_name}"


def delete_image(url: str) -> None:
    """
    Best-effort delete by URL. Logs failures but never raises — a missing or
    already-deleted object should not break the calling flow (e.g. replacing
    an old logo with a new one).
    """
    try:
        marker = f"/{settings.MINIO_BUCKET}/"
        if marker not in url:
            return
        object_name = url.split(marker, 1)[-1]
        minio_client.remove_object(settings.MINIO_BUCKET, object_name)
        logger.info("minio_object_deleted", object_name=object_name)
    except S3Error as e:
        logger.warning("minio_delete_failed", url=url, error=str(e))


def delete_prefix(prefix: str) -> None:
    """
    Delete all objects under a prefix. Use when removing a whole restaurant:
        delete_prefix(f"restaurants/{restaurant_id}/")
    Best-effort — logs failures.
    """
    try:
        objects = minio_client.list_objects(settings.MINIO_BUCKET, prefix=prefix, recursive=True)
        names = [obj.object_name for obj in objects]
        for name in names:
            minio_client.remove_object(settings.MINIO_BUCKET, name)
        logger.info("minio_prefix_deleted", prefix=prefix, count=len(names))
    except S3Error as e:
        logger.warning("minio_delete_prefix_failed", prefix=prefix, error=str(e))