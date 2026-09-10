import asyncio
import os
from pathlib import Path

import asyncpg
import boto3
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

url = os.getenv("DATABASE_URL", "").strip().strip('"').replace("postgresql+asyncpg://", "postgresql://")


async def wipe_database():
    conn = await asyncpg.connect(url, statement_cache_size=0, ssl="require")
    tables = ["payments", "broadcasts", "otp_codes", "collector_profiles", "users", "collector_groups"]
    await conn.execute(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE")
    for t in tables:
        count = await conn.fetchval(f"select count(*) from {t}")
        print(f"DB {t}: {count} rows remaining")
    await conn.close()


def wipe_r2():
    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    bucket = os.getenv("R2_BUCKET_NAME")
    if not (account_id and access_key and secret_key and bucket):
        print("R2: not configured, skipping")
        return
    endpoint = os.getenv("R2_ENDPOINT") or f"https://{account_id}.r2.cloudflarestorage.com"
    client = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=access_key,
                          aws_secret_access_key=secret_key, region_name="auto")
    deleted = 0
    paginator = client.get_paginator("list_objects_v2")
    to_delete = []
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            to_delete.append({"Key": obj["Key"]})
            if len(to_delete) == 1000:
                client.delete_objects(Bucket=bucket, Delete={"Objects": to_delete})
                deleted += len(to_delete)
                to_delete = []
    if to_delete:
        client.delete_objects(Bucket=bucket, Delete={"Objects": to_delete})
        deleted += len(to_delete)
    remaining = sum(1 for page in paginator.paginate(Bucket=bucket) for _ in page.get("Contents", []))
    print(f"R2: deleted {deleted} objects, {remaining} remaining")


def wipe_local_uploads():
    base = Path(__file__).resolve().parent / "uploads"
    removed = 0
    if base.exists():
        for f in base.rglob("*"):
            if f.is_file():
                f.unlink()
                removed += 1
    print(f"LOCAL: deleted {removed} files from {base}")


asyncio.run(wipe_database())
wipe_r2()
wipe_local_uploads()
print("ALL_DATA_REMOVED")
