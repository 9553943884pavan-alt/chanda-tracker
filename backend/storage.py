import logging
import os
from pathlib import Path

import boto3
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def _get_client():
    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    bucket = os.getenv("R2_BUCKET_NAME")
    if not (account_id and access_key and secret_key and bucket):
        return None
    endpoint = os.getenv("R2_ENDPOINT") or f"https://{account_id}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )


def save_local_file(file_bytes: bytes, key: str) -> Path:
    file_path = UPLOADS_DIR / key
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(file_bytes)
    return file_path


def upload_file(file_bytes: bytes, key: str) -> None:
    # Always save locally first to ensure fallback availability
    save_local_file(file_bytes, key)

    client = _get_client()
    bucket = os.getenv("R2_BUCKET_NAME")
    if client and bucket:
        try:
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=file_bytes,
            )
        except Exception as exc:
            logger.warning(f"R2 upload failed for key {key}, using local fallback: {exc}")


def get_signed_url(key: str, expiry_seconds: int = 300) -> str:
    local_path = UPLOADS_DIR / key
    client = _get_client()
    bucket = os.getenv("R2_BUCKET_NAME")

    if client and bucket:
        try:
            return client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                },
                ExpiresIn=expiry_seconds,
            )
        except Exception as exc:
            logger.warning(f"Failed to generate presigned URL for key {key}: {exc}")

    # Fallback to local HTTP URL
    return f"{API_BASE_URL}/uploads/{key}"

