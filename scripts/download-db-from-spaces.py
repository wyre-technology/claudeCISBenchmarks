"""
Download the ChromaDB vector store from DO Spaces on container startup.

Required env vars:
  SPACES_REGION          e.g. nyc3
  SPACES_BUCKET          bucket name
  SPACES_ACCESS_KEY_ID   DO Spaces access key
  SPACES_SECRET_ACCESS_KEY DO Spaces secret key

Optional:
  SPACES_PREFIX          object prefix (default: cis-benchmarks-db/)
  DB_DIR                 local destination (default: /app/mcp-server/data)
"""

import os
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

REGION = os.environ["SPACES_REGION"]
BUCKET = os.environ["SPACES_BUCKET"]
ACCESS_KEY = os.environ["SPACES_ACCESS_KEY_ID"]
SECRET_KEY = os.environ["SPACES_SECRET_ACCESS_KEY"]
PREFIX = os.environ.get("SPACES_PREFIX", "cis-benchmarks-db/")
DATA_DIR = Path(os.environ.get("DB_DIR", "/app/mcp-server/data"))

s3 = boto3.client(
    "s3",
    region_name=REGION,
    endpoint_url=f"https://{REGION}.digitaloceanspaces.com",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
)

DATA_DIR.mkdir(parents=True, exist_ok=True)

paginator = s3.get_paginator("list_objects_v2")
total = 0
for page in paginator.paginate(Bucket=BUCKET, Prefix=PREFIX):
    for obj in page.get("Contents", []):
        key = obj["Key"]
        relative = key[len(PREFIX):]
        if not relative:
            continue
        local = DATA_DIR / relative
        local.parent.mkdir(parents=True, exist_ok=True)
        print(f"  {key} → {local}")
        s3.download_file(BUCKET, key, str(local))
        total += 1

if total == 0:
    raise RuntimeError(
        f"No objects found at s3://{BUCKET}/{PREFIX} — "
        "run scripts/upload-db-to-spaces.sh first."
    )

print(f"Downloaded {total} files to {DATA_DIR}")
