from app.services.retrieval import RetrievedChunk, deduplicate_chunks, rrf_merge


def _chunk(
    doc_id: str = "doc1",
    filename: str = "file.md",
    content: str = "some content",
    index: int = 0,
    score: float = 0.9,
    heading: str | None = None,
) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=doc_id,
        filename=filename,
        chunk_content=content,
        chunk_index=index,
        similarity_score=score,
        section_heading=heading,
    )


class TestAdjacentMerging:
    def test_consecutive_same_doc_chunks_merged(self):
        chunks = [
            _chunk(index=0, content="Part one.", score=0.9),
            _chunk(index=1, content="Part two.", score=0.8),
        ]
        result = deduplicate_chunks(chunks, final_k=5)
        assert len(result) == 1
        assert "Part one." in result[0].chunk_content
        assert "Part two." in result[0].chunk_content

    def test_merged_chunk_keeps_highest_score(self):
        chunks = [
            _chunk(index=0, content="A.", score=0.7),
            _chunk(index=1, content="B.", score=0.95),
        ]
        result = deduplicate_chunks(chunks, final_k=5)
        assert len(result) == 1
        assert result[0].similarity_score == 0.95

    def test_non_consecutive_same_doc_not_merged(self):
        chunks = [
            _chunk(index=0, content="First chunk with unique words alpha.", score=0.9),
            _chunk(index=5, content="Fifth chunk with unique words beta.", score=0.8),
        ]
        result = deduplicate_chunks(chunks, final_k=5)
        assert len(result) == 2

    def test_different_documents_not_merged(self):
        chunks = [
            _chunk(doc_id="doc1", index=0, content="Doc one content alpha.", score=0.9),
            _chunk(doc_id="doc2", index=1, content="Doc two content beta.", score=0.8),
        ]
        result = deduplicate_chunks(chunks, final_k=5)
        assert len(result) == 2

    def test_merged_chunk_preserves_lowest_index(self):
        chunks = [
            _chunk(index=3, content="Third.", score=0.7),
            _chunk(index=4, content="Fourth.", score=0.8),
        ]
        result = deduplicate_chunks(chunks, final_k=5)
        assert result[0].chunk_index == 3


class TestOverlapFiltering:
    def test_high_overlap_drops_lower_scored(self):
        shared = "the quick brown fox jumps over the lazy dog near the river bank"
        chunks = [
            _chunk(doc_id="d1", index=0, content=shared, score=0.9),
            _chunk(doc_id="d2", index=0, content=shared + " extra", score=0.7),
        ]
        result = deduplicate_chunks(chunks, final_k=5)
        assert len(result) == 1
        assert result[0].similarity_score == 0.9

    def test_low_overlap_keeps_both(self):
        chunks = [
            _chunk(
                doc_id="d1",
                index=0,
                content="alpha bravo charlie delta echo foxtrot golf hotel india juliet",
                score=0.9,
            ),
            _chunk(
                doc_id="d2",
                index=0,
                content="kilo lima mike november oscar papa quebec romeo sierra tango",
                score=0.8,
            ),
        ]
        result = deduplicate_chunks(chunks, final_k=5)
        assert len(result) == 2


class TestSubstringDedup:
    def test_exact_substring_drops_lower_scored(self):
        full_text = "The Witch specializes in occult spells and minion summoning."
        partial = "occult spells and minion summoning"
        chunks = [
            _chunk(doc_id="d1", index=0, content=full_text, score=0.9),
            _chunk(doc_id="d2", index=0, content=partial, score=0.8),
        ]
        result = deduplicate_chunks(chunks, final_k=5)
        assert len(result) == 1
        assert result[0].chunk_content == full_text

    def test_substring_keeps_higher_scored_even_if_shorter(self):
        long_text = "The Witch is a character class in the game with many abilities."
        short_text = "The Witch is a character class"
        chunks = [
            _chunk(doc_id="d1", index=0, content=short_text, score=0.95),
            _chunk(doc_id="d2", index=0, content=long_text, score=0.6),
        ]
        result = deduplicate_chunks(chunks, final_k=5)
        assert len(result) == 1
        assert result[0].similarity_score == 0.95

    def test_non_substring_different_content_kept(self):
        chunks = [
            _chunk(doc_id="d1", index=0, content="Witch uses occult spells.", score=0.9),
            _chunk(doc_id="d2", index=0, content="Ranger uses bow skills.", score=0.8),
        ]
        result = deduplicate_chunks(chunks, final_k=5)
        assert len(result) == 2


class TestDeduplicateChunks:
    def test_no_duplicates_returns_input_unchanged(self):
        chunks = [
            _chunk(doc_id="d1", index=0, content="Unique content alpha.", score=0.9),
            _chunk(doc_id="d2", index=0, content="Different content beta.", score=0.8),
        ]
        result = deduplicate_chunks(chunks, final_k=5)
        assert len(result) == 2

    def test_final_k_limits_output(self):
        distinct_contents = [
            "alpha bravo charlie delta echo foxtrot golf hotel india",
            "kilo lima mike november oscar papa quebec romeo sierra",
            "tango uniform victor whiskey xray yankee zulu amber bronze",
            "coral denim ebony fern garnet hazel ivory jade kelp",
            "lapis mango nectar opal pearl quartz ruby sapphire topaz",
            "umber velvet walnut xenon yarrow zinc basil cedar dusk",
            "ember flint grove heron inlet junco knoll laurel marsh",
            "narwhal otter plover quail robin shrike tern upland vole",
        ]
        chunks = [
            _chunk(doc_id=f"d{i}", index=0, content=distinct_contents[i], score=0.9 - i * 0.05)
            for i in range(8)
        ]
        result = deduplicate_chunks(chunks, final_k=3)
        assert len(result) == 3
        scores = [c.similarity_score for c in result]
        assert scores == sorted(scores, reverse=True)

    def test_single_chunk_returned_as_is(self):
        chunks = [_chunk(content="Solo.")]
        result = deduplicate_chunks(chunks, final_k=5)
        assert len(result) == 1
        assert result[0].chunk_content == "Solo."

    def test_empty_input(self):
        result = deduplicate_chunks([], final_k=5)
        assert result == []

    def test_result_ordered_by_score_descending(self):
        chunks = [
            _chunk(doc_id="d1", index=0, content="Low score content unique alpha.", score=0.5),
            _chunk(doc_id="d2", index=0, content="High score content unique beta.", score=0.95),
            _chunk(doc_id="d3", index=0, content="Mid score content unique gamma.", score=0.7),
        ]
        result = deduplicate_chunks(chunks, final_k=5)
        scores = [c.similarity_score for c in result]
        assert scores == sorted(scores, reverse=True)


class TestRRFMerge:
    def test_single_list_preserves_order(self):
        chunks = [
            _chunk(doc_id="d1", index=0, content="First", score=0.9),
            _chunk(doc_id="d2", index=0, content="Second", score=0.8),
        ]
        result = rrf_merge([chunks])
        assert result[0].document_id == "d1"
        assert result[1].document_id == "d2"

    def test_chunk_in_both_lists_scores_higher(self):
        shared = _chunk(doc_id="d1", index=0, content="Shared", score=0.9)
        only_vector = _chunk(doc_id="d2", index=0, content="Vector only", score=0.85)
        only_keyword = _chunk(doc_id="d3", index=0, content="Keyword only", score=0.8)

        vector_list = [shared, only_vector]
        keyword_list = [shared, only_keyword]

        result = rrf_merge([vector_list, keyword_list])
        assert result[0].document_id == "d1"

    def test_disjoint_lists_interleaved(self):
        vector_list = [
            _chunk(doc_id="d1", index=0, content="V1", score=0.9),
            _chunk(doc_id="d2", index=0, content="V2", score=0.8),
        ]
        keyword_list = [
            _chunk(doc_id="d3", index=0, content="K1", score=0.9),
            _chunk(doc_id="d4", index=0, content="K2", score=0.8),
        ]
        result = rrf_merge([vector_list, keyword_list])
        assert len(result) == 4

    def test_empty_lists(self):
        result = rrf_merge([[], []])
        assert result == []

    def test_rrf_scores_are_positive(self):
        chunks = [
            _chunk(doc_id="d1", index=0, content="A", score=0.9),
            _chunk(doc_id="d2", index=0, content="B", score=0.5),
        ]
        result = rrf_merge([chunks])
        for chunk in result:
            assert chunk.similarity_score > 0

    def test_dedup_by_doc_id_and_chunk_index(self):
        """Same (doc_id, chunk_index) across lists is treated as one chunk."""
        list_a = [_chunk(doc_id="d1", index=0, content="Content", score=0.9)]
        list_b = [_chunk(doc_id="d1", index=0, content="Content", score=0.7)]
        result = rrf_merge([list_a, list_b])
        assert len(result) == 1
