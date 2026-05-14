"""
Parse CIS benchmark PDFs and index them into ChromaDB for semantic search.

Run this once (or after adding new PDFs) to populate the vector store.
Progress is printed to stdout; existing entries are upserted so re-runs are safe.
"""

import glob
import hashlib
import os
import re

import chromadb
import fitz  # PyMuPDF

PLUGIN_DIR = os.environ.get(
    "PLUGIN_DIR",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)
PDF_DIR = os.environ.get("PDF_DIR", PLUGIN_DIR)
DB_DIR = os.environ.get(
    "DB_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
)

# Matches lines like "1.1", "1.1.1", "2.3.4" at the start of a line followed by text.
# Avoids matching version numbers, IP addresses, page refs.
CONTROL_RE = re.compile(
    r"^(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\s{1,4}([A-Z][^\n]{5,120})$",
    re.MULTILINE,
)

# Lines that look like control IDs but are almost always false positives
FALSE_POSITIVE_TITLES = re.compile(
    r"^(page|figure|table|appendix|section|chapter|\d+\s*(of|/)\s*\d+)",
    re.IGNORECASE,
)


def benchmark_meta(pdf_path: str) -> dict:
    raw = os.path.basename(pdf_path)
    name = re.sub(r"\.pdf$", "", raw, flags=re.IGNORECASE)
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return {"filename": raw, "display_name": name}


def pdf_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    # Skip the first few pages (usually cover/TOC) to reduce noise
    return "\n".join(pages[3:])


def chunk_text(text: str, meta: dict) -> list[dict]:
    matches = [
        m
        for m in CONTROL_RE.finditer(text)
        if not FALSE_POSITIVE_TITLES.match(m.group(2))
    ]

    if len(matches) < 5:
        # Benchmark PDF has no parseable control structure — use 1500-char windows
        chunks = []
        for i in range(0, len(text), 1500):
            body = text[i : i + 1500].strip()
            if len(body) > 150:
                chunks.append({"text": body, "control_id": "", "control_title": "", **meta})
        return chunks

    chunks = []
    for i, m in enumerate(matches):
        control_id = m.group(1)
        control_title = m.group(2).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        if len(body) < 80:
            continue
        # Hard cap — ChromaDB embedding models have a token limit
        body = body[:3500]

        chunks.append(
            {
                "text": body,
                "control_id": control_id,
                "control_title": control_title,
                **meta,
            }
        )
    return chunks


def chunk_id(filename: str, idx: int) -> str:
    return hashlib.md5(f"{filename}:{idx}".encode()).hexdigest()


def index_all(pdf_dir: str, db_dir: str) -> None:
    os.makedirs(db_dir, exist_ok=True)
    client = chromadb.PersistentClient(path=db_dir)
    collection = client.get_or_create_collection(
        name="cis_controls", metadata={"hnsw:space": "cosine"}
    )

    pdfs = glob.glob(os.path.join(pdf_dir, "*.pdf")) + glob.glob(
        os.path.join(pdf_dir, "*.PDF")
    )
    print(f"Found {len(pdfs)} PDFs in {pdf_dir}\n")

    total = 0
    for path in sorted(pdfs):
        meta = benchmark_meta(path)
        print(f"  Indexing: {meta['display_name']}")
        try:
            text = pdf_text(path)
            chunks = chunk_text(text, meta)
            if not chunks:
                print(f"    ⚠ No chunks extracted")
                continue

            ids = [chunk_id(meta["filename"], i) for i in range(len(chunks))]
            texts = [c["text"] for c in chunks]
            metas = [
                {
                    "filename": c["filename"],
                    "display_name": c["display_name"],
                    "control_id": c["control_id"],
                    "control_title": c["control_title"],
                }
                for c in chunks
            ]

            for start in range(0, len(ids), 100):
                collection.upsert(
                    ids=ids[start : start + 100],
                    documents=texts[start : start + 100],
                    metadatas=metas[start : start + 100],
                )

            total += len(chunks)
            print(f"    ✓ {len(chunks)} chunks indexed")
        except Exception as exc:
            print(f"    ✗ Error: {exc}")

    print(f"\nDone. {total} total chunks across {len(pdfs)} benchmarks.")
    print(f"Database: {db_dir}")


if __name__ == "__main__":
    index_all(PDF_DIR, DB_DIR)
