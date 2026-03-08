from app.services.embedding import EMBEDDING_DIMENSION, MockEmbeddingService
from app.services.processing import (
    DEFAULT_CHUNK_SIZE,
    ChunkWithHeading,
    build_embedding_text,
    chunk_markdown,
    chunk_text,
)


class TestChunking:
    def test_short_text_produces_single_chunk(self):
        text = "This is a short sentence."
        chunks = chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_respects_size_limit(self):
        text = "word " * 200  # 1000 characters
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)
        for chunk in chunks:
            assert len(chunk) <= 500

    def test_produces_overlap(self):
        text = ("A" * 250 + " ") * 4  # ~1004 characters in 4 segments
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)
        assert len(chunks) >= 2
        if len(chunks) >= 2:
            end_of_first = chunks[0][-50:]
            assert end_of_first in chunks[1] or chunks[1][:50] in chunks[0]

    def test_empty_text(self):
        chunks = chunk_text("")
        assert chunks == []

    def test_default_parameters_use_updated_size(self):
        assert DEFAULT_CHUNK_SIZE == 1000
        text = "Hello world. " * 200  # ~2600 characters
        chunks = chunk_text(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= DEFAULT_CHUNK_SIZE


class TestMarkdownChunking:
    def test_multi_section_produces_one_chunk_per_section(self):
        md = (
            "# Title\n\nIntro paragraph.\n\n"
            "## Section A\n\nContent of section A.\n\n"
            "## Section B\n\nContent of section B.\n"
        )
        chunks = chunk_markdown(md)
        assert len(chunks) >= 2
        assert all(isinstance(c, ChunkWithHeading) for c in chunks)

        headings = [c.section_heading for c in chunks]
        assert any(h and "Section A" in h for h in headings)
        assert any(h and "Section B" in h for h in headings)

    def test_heading_hierarchy_concatenated(self):
        md = "# Top\n\n## Middle\n\n### Deep\n\nDeep content here.\n"
        chunks = chunk_markdown(md)
        deep_chunks = [c for c in chunks if c.section_heading and "Deep" in c.section_heading]
        assert len(deep_chunks) >= 1
        assert deep_chunks[0].section_heading == "Top > Middle > Deep"

    def test_oversized_section_gets_sub_split(self):
        long_content = "This is a sentence with some words. " * 100  # ~3600 chars
        md = f"# Big Section\n\n{long_content}"
        chunks = chunk_markdown(md, chunk_size=500)
        assert len(chunks) >= 2
        for c in chunks:
            assert c.section_heading == "Big Section"
            assert len(c.content) <= 500

    def test_deep_headings_stay_within_parent(self):
        md = (
            "# Top\n\n"
            "## Parent\n\n"
            "#### Deep Sub\n\nDeep sub content.\n\n"
            "Some more parent content.\n"
        )
        chunks = chunk_markdown(md)
        for c in chunks:
            if c.content and "Deep sub content" in c.content:
                assert c.section_heading is not None
                assert "Deep Sub" not in c.section_heading

    def test_no_headers_falls_back_to_plain_chunking(self):
        text = "Just plain text without any markdown headers. " * 50
        chunks = chunk_markdown(text)
        assert len(chunks) >= 1
        assert all(c.section_heading is None for c in chunks)

    def test_empty_markdown(self):
        chunks = chunk_markdown("")
        assert chunks == []

    def test_whitespace_only_markdown(self):
        chunks = chunk_markdown("   \n\n  ")
        assert chunks == []

    def test_section_content_preserved(self):
        md = "# Title\n\nThe quick brown fox jumps over the lazy dog."
        chunks = chunk_markdown(md)
        all_content = " ".join(c.content for c in chunks)
        assert "quick brown fox" in all_content


class TestBuildEmbeddingText:
    def test_with_heading(self):
        result = build_embedding_text(
            "Specializes in occult spells.",
            "Witch.md",
            "Ascendancy classes",
        )
        assert result == "Witch > Ascendancy classes: Specializes in occult spells."

    def test_without_heading(self):
        result = build_embedding_text(
            "Some plain content.",
            "Witch.md",
        )
        assert result == "Witch: Some plain content."

    def test_strips_extension(self):
        result = build_embedding_text("Content.", "Character class.md")
        assert result.startswith("Character class:")

    def test_non_markdown_extension(self):
        result = build_embedding_text("Content.", "manual.pdf")
        assert result.startswith("manual:")

    def test_stored_content_unchanged(self):
        """Verify build_embedding_text does not mutate the input content."""
        original = "The Witch is an intelligence-oriented class."
        _ = build_embedding_text(original, "Witch.md", "Overview")
        assert original == "The Witch is an intelligence-oriented class."


class TestMockEmbeddingService:
    def test_embed_texts_returns_correct_dimensions(self):
        service = MockEmbeddingService()
        texts = ["hello world", "another text"]
        embeddings = service.embed_texts(texts)
        assert len(embeddings) == 2
        for emb in embeddings:
            assert len(emb) == EMBEDDING_DIMENSION

    def test_embed_query_returns_correct_dimensions(self):
        service = MockEmbeddingService()
        embedding = service.embed_query("test query")
        assert len(embedding) == EMBEDDING_DIMENSION

    def test_deterministic_for_same_input(self):
        service = MockEmbeddingService()
        emb1 = service.embed_query("same text")
        emb2 = service.embed_query("same text")
        assert emb1 == emb2

    def test_different_for_different_input(self):
        service = MockEmbeddingService()
        emb1 = service.embed_query("text a")
        emb2 = service.embed_query("text b")
        assert emb1 != emb2

    def test_vectors_are_normalized(self):
        service = MockEmbeddingService()
        emb = service.embed_query("normalize me")
        magnitude = sum(x * x for x in emb) ** 0.5
        assert abs(magnitude - 1.0) < 1e-6
