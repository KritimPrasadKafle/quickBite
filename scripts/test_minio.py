"""Standalone MinIO smoke test. Run inside the container."""
import asyncio
import io
from core.storage import upload_image, delete_image, delete_prefix, minio_client
from core.config import settings


class FakeUploadFile:
    """Mimics FastAPI's UploadFile for testing without HTTP."""
    def __init__(self, filename, content_type, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self._data = data

    async def read(self):
        return self._data


# A 1x1 red PNG (smallest valid PNG)
TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de0000000c4944415408d76360f8cf000000ff00ffa1b998000000004945"
    "4e44ae426082"
)


async def main():
    print(f"Endpoint: {settings.MINIO_ENDPOINT}")
    print(f"Bucket:   {settings.MINIO_BUCKET}")

    # 1. Upload
    fake = FakeUploadFile("test.png", "image/png", TINY_PNG)
    url = await upload_image(fake, folder="restaurants/test-restaurant/logo")
    print(f"✓ Uploaded → {url}")

    # 2. Verify it exists
    marker = f"/{settings.MINIO_BUCKET}/"
    object_name = url.split(marker, 1)[-1]
    stat = minio_client.stat_object(settings.MINIO_BUCKET, object_name)
    print(f"✓ Exists, size={stat.size} bytes, type={stat.content_type}")

    # 3. Reject bad type
    try:
        bad = FakeUploadFile("evil.exe", "application/x-msdownload", b"MZ")
        await upload_image(bad, folder="restaurants/test/logo")
        print("✗ Should have rejected .exe")
    except Exception as e:
        print(f"✓ Rejected bad type: {getattr(e, 'detail', e)}")

    # 4. Reject oversized
    try:
        huge = FakeUploadFile("huge.png", "image/png", b"\x00" * (6 * 1024 * 1024))
        await upload_image(huge, folder="restaurants/test/logo")
        print("✗ Should have rejected oversized")
    except Exception as e:
        print(f"✓ Rejected oversized: {getattr(e, 'detail', e)}")

    # 5. Delete single
    delete_image(url)
    print("✓ Deleted single object")

    # 6. Cleanup prefix
    delete_prefix("restaurants/test-restaurant/")
    delete_prefix("restaurants/test/")
    print("✓ Cleaned up test prefixes")


if __name__ == "__main__":
    asyncio.run(main())