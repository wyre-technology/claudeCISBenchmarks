#!/usr/bin/env bash
# Upload the indexed ChromaDB vector store to DO Spaces.
# Run this once after indexing, then re-run whenever PDFs are re-indexed.
#
# Required env vars:
#   SPACES_REGION            e.g. nyc3
#   SPACES_BUCKET            bucket name
#   SPACES_ACCESS_KEY_ID     DO Spaces access key
#   SPACES_SECRET_ACCESS_KEY DO Spaces secret key
#
# Optional:
#   SPACES_PREFIX            object prefix (default: cis-benchmarks-db/)
#
# Usage:
#   SPACES_REGION=nyc3 SPACES_BUCKET=my-bucket \
#   SPACES_ACCESS_KEY_ID=xxx SPACES_SECRET_ACCESS_KEY=yyy \
#   bash scripts/upload-db-to-spaces.sh
set -euo pipefail

: "${SPACES_REGION:?Must set SPACES_REGION}"
: "${SPACES_BUCKET:?Must set SPACES_BUCKET}"
: "${SPACES_ACCESS_KEY_ID:?Must set SPACES_ACCESS_KEY_ID}"
: "${SPACES_SECRET_ACCESS_KEY:?Must set SPACES_SECRET_ACCESS_KEY}"
SPACES_PREFIX="${SPACES_PREFIX:-cis-benchmarks-db/}"

DATA_DIR="$(cd "$(dirname "$0")/.." && pwd)/mcp-server/data"

if [ ! -f "$DATA_DIR/chroma.sqlite3" ]; then
    echo "ERROR: $DATA_DIR/chroma.sqlite3 not found. Run the indexer first:"
    echo "  PDF_DIR=. DB_DIR=mcp-server/data .venv/bin/python mcp-server/indexer.py"
    exit 1
fi

echo "==> Uploading ChromaDB from $DATA_DIR to s3://$SPACES_BUCKET/$SPACES_PREFIX"

python3 - <<EOF
import boto3, os
from pathlib import Path

s3 = boto3.client(
    "s3",
    region_name="$SPACES_REGION",
    endpoint_url="https://$SPACES_REGION.digitaloceanspaces.com",
    aws_access_key_id="$SPACES_ACCESS_KEY_ID",
    aws_secret_access_key="$SPACES_SECRET_ACCESS_KEY",
)

data_dir = Path("$DATA_DIR")
prefix = "$SPACES_PREFIX"
bucket = "$SPACES_BUCKET"

for path in sorted(data_dir.rglob("*")):
    if path.is_file():
        key = prefix + str(path.relative_to(data_dir))
        print(f"  {path} → s3://{bucket}/{key}")
        s3.upload_file(str(path), bucket, key)

print("Upload complete.")
EOF
