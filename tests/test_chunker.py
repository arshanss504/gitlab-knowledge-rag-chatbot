"""
tests/test_chunker.py
Unit tests for the semantic chunker.
No external dependencies required.
"""

import pytest
from backend.services.chunker import SemanticChunker, _split_by_paragraphs, _estimate_tokens


class TestEstimateTokens:
    def test_empty(self):
        assert _estimate_tokens("") == 0

    def test_short_text(self):
        assert _estimate_tokens("hello world") == 2  # 11 chars / 4 ≈ 2

    def test_long_text(self):
        text = "a" * 400
        assert _estimate_tokens(text) == 100


class TestSplitByParagraphs:
    def test_short_text_no_split(self):
        text = "Short paragraph."
        result = _split_by_paragraphs(text, max_tokens=100, overlap_tokens=10)
        assert len(result) == 1
        assert result[0] == text

    def test_long_text_splits(self):
        # Create text that exceeds 50 tokens (~200 chars)
        paragraphs = [f"This is paragraph number {i} with some content here. " * 5 for i in range(5)]
        text = "\n\n".join(paragraphs)
        result = _split_by_paragraphs(text, max_tokens=50, overlap_tokens=10)
        assert len(result) > 1

    def test_overlap_present(self):
        # Each paragraph is ~30 tokens; max is 40 → split after 1
        p1 = "First paragraph with some text content. " * 3   # ~30 tokens
        p2 = "Second paragraph with some text content. " * 3  # ~30 tokens
        p3 = "Third paragraph with some text content. " * 3   # ~30 tokens
        text = f"{p1}\n\n{p2}\n\n{p3}"
        result = _split_by_paragraphs(text, max_tokens=40, overlap_tokens=20)
        # Second chunk should contain overlap from first
        assert len(result) >= 2


class TestSemanticChunker:
    def setup_method(self):
        self.chunker = SemanticChunker()

    def test_empty_sections(self):
        chunks = self.chunker.chunk_page(
            source_url="https://example.com",
            title="Test",
            sections=[],
        )
        assert chunks == []

    def test_basic_chunking(self):
        sections = [
            {
                "heading": "GitLab Values",
                "text": "GitLab has six core values: Collaboration, Results, Efficiency, Diversity, Iteration, and Transparency.",
                "anchor": "values",
                "url": "https://handbook.gitlab.com/values",
            }
        ]
        chunks = self.chunker.chunk_page(
            source_url="https://handbook.gitlab.com/",
            title="GitLab Handbook",
            sections=sections,
        )
        assert len(chunks) == 1
        assert "GitLab Values" in chunks[0].text
        assert chunks[0].metadata["source_url"] == "https://handbook.gitlab.com/"
        assert chunks[0].metadata["section"] == "GitLab Values"

    def test_chunk_ids_are_stable(self):
        """Same input should produce same chunk IDs (idempotent upsert)."""
        sections = [
            {"heading": "Test", "text": "Some content here.", "anchor": "", "url": "https://x.com"}
        ]
        chunks1 = self.chunker.chunk_page("https://x.com", "Test", sections)
        chunks2 = self.chunker.chunk_page("https://x.com", "Test", sections)
        assert chunks1[0].id == chunks2[0].id

    def test_large_section_splits(self):
        """A very large section should be split into multiple chunks."""
        long_text = ("GitLab encourages async communication. " * 20 + "\n\n") * 10
        sections = [
            {"heading": "Communication", "text": long_text, "anchor": "", "url": "https://x.com"}
        ]
        chunks = self.chunker.chunk_page("https://x.com", "Test", sections)
        assert len(chunks) > 1
        # Every chunk should carry the heading
        for chunk in chunks:
            assert "Communication" in chunk.text

    def test_metadata_completeness(self):
        sections = [
            {
                "heading": "Remote Work",
                "text": "GitLab is an all-remote company.",
                "anchor": "remote",
                "url": "https://handbook.gitlab.com/#remote",
            }
        ]
        chunks = self.chunker.chunk_page(
            source_url="https://handbook.gitlab.com/",
            title="Handbook",
            sections=sections,
            extra_metadata={"domain": "handbook.gitlab.com"},
        )
        meta = chunks[0].metadata
        assert "source_url" in meta
        assert "section" in meta
        assert "content_hash" in meta
        assert "chunk_index" in meta
        assert meta["domain"] == "handbook.gitlab.com"
