"""
app/services/chunker.py
Semantic chunking strategy for RAG.
"""

from dataclasses import dataclass
from typing import List

from backend.core.logging import get_logger
from backend.utils.text import content_hash, make_chunk_id

logger = get_logger(__name__)

_CHARS_PER_TOKEN = 4
_CHUNK_SIZE_TOKENS = 800
_CHUNK_OVERLAP_TOKENS = 80


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict


def _estimate_tokens(text: str) -> int:
    return len(text) // _CHARS_PER_TOKEN


def _split_by_paragraphs(text: str, max_tokens: int, overlap_tokens: int) -> List[str]:
    """
    Split text into token-bounded chunks at paragraph boundaries.
    Adds one paragraph of overlap between consecutive chunks.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_parts: List[str] = []
    current_tokens = 0
    overlap_buffer: List[str] = []

    for para in paragraphs:
        para_tokens = _estimate_tokens(para)

        if para_tokens > max_tokens:
            if current_parts:
                chunks.append("\n\n".join(current_parts))
                overlap_buffer = current_parts[-1:]
                current_parts = list(overlap_buffer)
                current_tokens = sum(_estimate_tokens(p) for p in current_parts)

            sentences = _split_by_sentences(para, max_tokens)
            chunks.extend(sentences[:-1])
            if sentences:
                current_parts = [sentences[-1]]
                current_tokens = _estimate_tokens(sentences[-1])
            continue

        if current_tokens + para_tokens > max_tokens and current_parts:
            chunks.append("\n\n".join(current_parts))
            overlap_buffer = current_parts[-1:] if current_parts else []
            current_parts = list(overlap_buffer) + [para]
            current_tokens = sum(_estimate_tokens(p) for p in current_parts)
        else:
            current_parts.append(para)
            current_tokens += para_tokens

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return [c for c in chunks if c.strip()]


def _split_by_sentences(text: str, max_tokens: int) -> List[str]:
    """Fallback sentence-level splitter for very long paragraphs."""
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = []
    current_tokens = 0
    for sent in sentences:
        t = _estimate_tokens(sent)
        if current_tokens + t > max_tokens and current:
            chunks.append(" ".join(current))
            current = [sent]
            current_tokens = t
        else:
            current.append(sent)
            current_tokens += t
    if current:
        chunks.append(" ".join(current))
    return chunks


class SemanticChunker:
    def __init__(self):
        self._max_tokens = _CHUNK_SIZE_TOKENS
        self._overlap_tokens = _CHUNK_OVERLAP_TOKENS

    def chunk_page(
        self,
        source_url: str,
        title: str,
        sections: list[dict],
        extra_metadata: dict | None = None,
    ) -> List[Chunk]:
        chunks: List[Chunk] = []
        global_index = 0

        for section in sections:
            heading = section.get("heading", "")
            body = section.get("text", "")
            anchor = section.get("anchor", "")
            section_url = section.get("url", source_url)

            if not body.strip():
                continue

            headed_text = f"{heading}\n\n{body}" if heading else body

            if _estimate_tokens(headed_text) <= self._max_tokens:
                text_chunks = [headed_text]
            else:
                body_chunks = _split_by_paragraphs(
                    body, self._max_tokens - _estimate_tokens(heading) - 2,
                    self._overlap_tokens,
                )
                text_chunks = [
                    f"{heading}\n\n{bc}" if heading else bc
                    for bc in body_chunks
                ]

            for chunk_text in text_chunks:
                chunk_text = chunk_text.strip()
                if not chunk_text:
                    continue

                chunk_id = make_chunk_id(source_url, global_index)
                metadata = {
                    "source_url": source_url,
                    "section_url": section_url,
                    "title": title,
                    "section": heading,
                    "anchor": anchor,
                    "chunk_index": global_index,
                    "content_hash": content_hash(chunk_text),
                    **(extra_metadata or {}),
                }

                chunks.append(Chunk(id=chunk_id, text=chunk_text, metadata=metadata))
                global_index += 1

        logger.debug(
            "Chunked page", url=source_url, sections=len(sections), chunks=len(chunks)
        )
        return chunks
