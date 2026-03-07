"""Tests for wiki seeder content-filtering functions."""

from __future__ import annotations

import pytest

from seed_wiki import should_skip_title, strip_sections


# ---------------------------------------------------------------------------
# strip_sections
# ---------------------------------------------------------------------------


class TestStripSections:
    """Tests for strip_sections()."""

    def test_removes_section_at_end_of_document(self) -> None:
        md = (
            "Some intro text.\n\n"
            "## Mechanics\n\nGood content here.\n\n"
            "## Version history\n\n| Version | Changes |\n| --- | --- |\n| 0.1.0 | Introduced |\n"
        )
        result = strip_sections(md, ["version history"])
        assert "## Mechanics" in result
        assert "Good content here." in result
        assert "Version history" not in result
        assert "Introduced" not in result

    def test_removes_section_in_middle(self) -> None:
        md = (
            "## Overview\n\nFirst section.\n\n"
            "## References\n\n1. Some citation\n\n"
            "## Related skills\n\nUseful content.\n"
        )
        result = strip_sections(md, ["references"])
        assert "## Overview" in result
        assert "First section." in result
        assert "References" not in result
        assert "Some citation" not in result
        assert "## Related skills" in result
        assert "Useful content." in result

    def test_no_matching_section_passes_through(self) -> None:
        md = "## Mechanics\n\nContent about mechanics.\n\n## Related skills\n\nMore content.\n"
        result = strip_sections(md, ["version history"])
        assert result == md.strip()

    def test_case_insensitive_matching(self) -> None:
        md = "Some text.\n\n## VERSION HISTORY\n\nPatch notes.\n"
        result = strip_sections(md, ["version history"])
        assert "VERSION HISTORY" not in result
        assert "Patch notes" not in result
        assert "Some text." in result

    def test_multiple_matching_sections(self) -> None:
        md = (
            "## Mechanics\n\nGood.\n\n"
            "## See also\n\n* Link\n\n"
            "## Related items\n\nUseful.\n\n"
            "## Version history\n\nOld stuff.\n"
        )
        result = strip_sections(md, ["see also", "version history"])
        assert "## Mechanics" in result
        assert "## Related items" in result
        assert "See also" not in result
        assert "Version history" not in result

    def test_section_with_sub_headings_removed(self) -> None:
        md = (
            "## Mechanics\n\nGood.\n\n"
            "## Dialogues\n\n### Entering locations\n\nQuote 1.\n\n"
            "### Boss defeated\n\nQuote 2.\n\n"
            "## Related skills\n\nUseful.\n"
        )
        result = strip_sections(md, ["dialogues"])
        assert "## Mechanics" in result
        assert "Dialogues" not in result
        assert "Entering locations" not in result
        assert "Boss defeated" not in result
        assert "Quote 1" not in result
        assert "Quote 2" not in result
        assert "## Related skills" in result

    def test_empty_input_returns_empty(self) -> None:
        assert strip_sections("", ["version history"]) == ""

    def test_empty_headings_list_passes_through(self) -> None:
        md = "## Version history\n\nStuff.\n"
        assert strip_sections(md, []) == md

    def test_content_before_any_heading_preserved(self) -> None:
        md = (
            "Intro paragraph before any heading.\n\n"
            "## Version history\n\nPatch notes.\n"
        )
        result = strip_sections(md, ["version history"])
        assert "Intro paragraph before any heading." in result
        assert "Version history" not in result


# ---------------------------------------------------------------------------
# should_skip_title
# ---------------------------------------------------------------------------


class TestShouldSkipTitle:
    """Tests for should_skip_title()."""

    def test_version_history_skipped(self) -> None:
        assert should_skip_title("Version history") is True

    def test_version_patch_skipped(self) -> None:
        assert should_skip_title("Version 0.4.0f") is True

    def test_regular_title_not_skipped(self) -> None:
        assert should_skip_title("Armour") is False

    def test_vendor_not_skipped(self) -> None:
        assert should_skip_title("Vendor") is False

    def test_version_substring_not_skipped(self) -> None:
        assert should_skip_title("Subversion") is False
