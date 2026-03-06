from app.services.processing import chunk_text


def test_chunk_short_text_produces_single_chunk():
    text = "This is a short sentence."
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_respects_size_limit():
    text = "word " * 200  # 1000 characters
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)
    for chunk in chunks:
        assert len(chunk) <= 500


def test_chunk_text_produces_overlap():
    text = ("A" * 250 + " ") * 4  # ~1004 characters in 4 segments
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)
    assert len(chunks) >= 2
    # Overlapping chunks should share some content
    if len(chunks) >= 2:
        end_of_first = chunks[0][-50:]
        assert end_of_first in chunks[1] or chunks[1][:50] in chunks[0]


def test_chunk_empty_text():
    chunks = chunk_text("")
    assert chunks == []


def test_chunk_text_default_parameters():
    text = "Hello world. " * 100  # ~1300 characters
    chunks = chunk_text(text)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= 500
