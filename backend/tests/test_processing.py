from app.services.embedding import EMBEDDING_DIMENSION, MockEmbeddingService
from app.services.processing import chunk_text


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

    def test_default_parameters(self):
        text = "Hello world. " * 100  # ~1300 characters
        chunks = chunk_text(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 500


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
