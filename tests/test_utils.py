"""
tests/test_utils.py
Unit tests for text utilities.
"""

import pytest
from backend.utils.text import clean_text, content_hash, make_chunk_id


class TestCleanText:
    def test_empty_string(self):
        assert clean_text("") == ""

    def test_collapses_blank_lines(self):
        text = "line one\n\n\n\nline two"
        result = clean_text(text)
        assert "\n\n\n" not in result

    def test_strips_zero_width(self):
        text = "hello\u200bworld"
        result = clean_text(text)
        assert "\u200b" not in result

    def test_strips_leading_trailing_whitespace(self):
        text = "  hello world  "
        assert clean_text(text) == "hello world"

    def test_collapses_inline_spaces(self):
        text = "hello    world"
        result = clean_text(text)
        assert "    " not in result


class TestMakeChunkId:
    def test_deterministic(self):
        id1 = make_chunk_id("https://example.com", 0)
        id2 = make_chunk_id("https://example.com", 0)
        assert id1 == id2

    def test_different_for_different_inputs(self):
        id1 = make_chunk_id("https://example.com", 0)
        id2 = make_chunk_id("https://example.com", 1)
        id3 = make_chunk_id("https://other.com", 0)
        assert id1 != id2
        assert id1 != id3

    def test_fixed_length(self):
        id1 = make_chunk_id("https://very-long-url.example.com/handbook/path/to/page", 999)
        assert len(id1) == 32


class TestContentHash:
    def test_same_content_same_hash(self):
        assert content_hash("hello") == content_hash("hello")

    def test_different_content_different_hash(self):
        assert content_hash("hello") != content_hash("world")

    def test_returns_string(self):
        assert isinstance(content_hash("test"), str)
