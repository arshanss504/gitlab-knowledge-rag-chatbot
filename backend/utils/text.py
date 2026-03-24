"""
app/utils/text.py
Text cleaning and normalisation helpers used across the pipeline.
"""

import hashlib
import re
import unicodedata


def clean_text(text: str) -> str:
    """
    Normalise raw extracted text for embedding and storage.
    - NFKC unicode normalisation
    - Collapse excessive whitespace / blank lines
    - Strip zero-width / invisible characters
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    lines = [line.strip() for line in text.splitlines()]
    lines = [l for l in lines if len(l) > 2 or l == ""]

    return "\n".join(lines).strip()


def make_chunk_id(source_url: str, chunk_index: int) -> str:
    """Deterministic, stable chunk ID for idempotent upsert."""
    key = f"{source_url}::{chunk_index}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def content_hash(text: str) -> str:
    """SHA-256 fingerprint for incremental update detection."""
    return hashlib.sha256(text.encode()).hexdigest()
