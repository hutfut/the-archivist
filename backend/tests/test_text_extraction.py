from pathlib import Path

import pytest

from app.services.text_extraction import extract_text

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_plain_text():
    text = extract_text(FIXTURES / "sample.txt", "text/plain")
    assert "sample text document" in text
    assert "multiple lines" in text


def test_extract_markdown():
    text = extract_text(FIXTURES / "sample.md", "text/markdown")
    assert "# Sample Markdown" in text
    assert "Item one" in text


def test_extract_pdf():
    text = extract_text(FIXTURES / "sample.pdf", "application/pdf")
    assert "Hello from PDF" in text


def test_extract_unsupported_content_type():
    with pytest.raises(ValueError, match="Unsupported content type"):
        extract_text(FIXTURES / "sample.txt", "application/octet-stream")


def test_extract_file_not_found():
    with pytest.raises(FileNotFoundError):
        extract_text(Path("/nonexistent/file.txt"), "text/plain")


def test_extract_empty_txt(tmp_path: Path):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("")
    text = extract_text(empty_file, "text/plain")
    assert text == ""
