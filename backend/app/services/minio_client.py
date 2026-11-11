import io
from minio import Minio
from minio.error import S3Error
from app.core.config import get_settings
from functools import lru_cache

settings = get_settings()


@lru_cache()
def get_minio_client() -> Minio:
    """Get MinIO client instance."""
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def get_bucket_name(org_id: str, bucket_type: str = "documents") -> str:
    """Generate bucket name for organization."""
    return f"org-{org_id}-{bucket_type}"


def ensure_bucket_exists(client: Minio, bucket_name: str) -> None:
    """Create bucket if it doesn't exist."""
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)


def upload_file(
    client: Minio,
    bucket_name: str,
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload bytes to MinIO and return object name."""
    ensure_bucket_exists(client, bucket_name)
    client.put_object(
        bucket_name,
        object_name,
        io.BytesIO(data),
        len(data),
        content_type=content_type,
    )
    return object_name


def download_file(client: Minio, bucket_name: str, object_name: str) -> bytes:
    """Download file from MinIO."""
    response = client.get_object(bucket_name, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def get_presigned_url(
    client: Minio,
    bucket_name: str,
    object_name: str,
    expires_seconds: int = 3600,
) -> str:
    """Generate presigned URL for download."""
    from datetime import timedelta
    return client.presigned_get_object(bucket_name, object_name, expires=timedelta(seconds=expires_seconds))


def delete_file(client: Minio, bucket_name: str, object_name: str) -> None:
    """Delete file from MinIO."""
    client.remove_object(bucket_name, object_name)


import io