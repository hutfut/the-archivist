#!/usr/bin/env python3
"""Fetch and clean Path of Exile 2 wiki pages; write Markdown to disk.

POE-wiki-specific retrieval: discovers pages from the wiki, fetches HTML
via the MediaWiki API, converts to Markdown with wiki-specific cleanup
(strip navboxes, version history, etc.), and writes .md files to an
output directory. Does not upload; use seed_documents.py to upload.

Usage:
    python fetch_poe_wiki.py --output-dir ./wiki_pages
    python fetch_poe_wiki.py --output-dir ./wiki_pages --delay 0.5
    python fetch_poe_wiki.py --output-dir ./wiki_pages --dry-run
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from collections.abc import Sequence
from pathlib import Path

import httpx
from bs4 import BeautifulSoup, Tag
from markdownify import markdownify

logger = logging.getLogger("fetch_poe_wiki")

WIKI_API = "https://www.poe2wiki.net/api.php"
MAIN_PAGE = "Path_of_Exile_2_Wiki"
USER_AGENT = "poe2-wiki-fetcher/1.0 (notebooklm assessment project)"
REQUEST_TIMEOUT = 30.0

_SKIP_TITLE_PREFIXES = ["Version"]

_STRIP_SECTION_HEADINGS = [
    "version history",
    "references",
    "see also",
    "dialogues",
    "gallery",
    "gameplay video",
]

_REMOVE_SELECTORS = [
    ".mw-editsection",
    "#toc",
    ".toc",
    ".catlinks",
    ".navbox",
    ".navbox-container",
    ".noprint",
    ".mw-empty-elt",
    ".hoverbox__display",
    ".c-tooltip__display",
    "style",
    "script",
]


def discover_page_titles(client: httpx.Client) -> list[str]:
    """Return titles of all namespace-0 pages linked from the main wiki page."""
    resp = client.get(
        WIKI_API,
        params={
            "action": "parse",
            "page": MAIN_PAGE,
            "prop": "links",
            "format": "json",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    links = data["parse"]["links"]
    titles = [
        link["*"]
        for link in links
        if link.get("ns") == 0 and "exists" in link
    ]
    logger.info("Discovered %d page titles from main page", len(titles))
    return sorted(set(titles))


def fetch_page_html(client: httpx.Client, title: str) -> str | None:
    """Fetch rendered HTML for a single wiki page. Returns None on failure."""
    try:
        resp = client.get(
            WIKI_API,
            params={
                "action": "parse",
                "page": title,
                "prop": "text",
                "format": "json",
            },
        )
    except httpx.RequestError as exc:
        logger.warning("Request failed for '%s': %s", title, exc)
        return None
    if resp.status_code != 200:
        logger.warning("HTTP %d fetching page '%s'", resp.status_code, title)
        return None
    try:
        data = resp.json()
    except ValueError:
        logger.warning("Invalid JSON for '%s' (len=%d)", title, len(resp.content))
        return None
    if "error" in data:
        logger.warning("API error for '%s': %s", title, data["error"].get("info"))
        return None
    return data["parse"]["text"]["*"]


def clean_html(html: str) -> str:
    """Strip wiki chrome from parsed HTML, keeping article content."""
    soup = BeautifulSoup(html, "html.parser")
    for selector in _REMOVE_SELECTORS:
        for el in soup.select(selector):
            el.decompose()
    for el in soup.find_all(class_=re.compile(r"hoverbox_+display|c-tooltip_+display")):
        if isinstance(el, Tag):
            el.decompose()
    for img in soup.find_all("img"):
        if isinstance(img, Tag):
            img.decompose()
    return str(soup)


def should_skip_title(title: str) -> bool:
    """Return True if a wiki page title should be excluded."""
    return any(title.startswith(prefix) for prefix in _SKIP_TITLE_PREFIXES)


def strip_sections(md: str, headings: Sequence[str]) -> str:
    """Remove ##-level sections whose heading matches any entry in *headings* (case-insensitive)."""
    if not md or not headings:
        return md
    headings_lower = set(headings)
    fragments = re.split(r"^(?=## )", md, flags=re.MULTILINE)
    kept: list[str] = []
    for fragment in fragments:
        first_line = fragment.split("\n", 1)[0]
        heading_match = re.match(r"^## (.+)$", first_line)
        if heading_match and heading_match.group(1).strip().lower() in headings_lower:
            continue
        kept.append(fragment)
    return "".join(kept).strip()


def html_to_markdown(html: str, title: str) -> str:
    """Convert cleaned HTML to Markdown with a title header."""
    cleaned = clean_html(html)
    md: str = markdownify(cleaned, heading_style="ATX", strip=["img"])
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r"[ \t]+$", "", md, flags=re.MULTILINE)
    md = md.strip()
    md = strip_sections(md, _STRIP_SECTION_HEADINGS)
    return f"# {title}\n\n{md}\n"


def sanitize_filename(title: str) -> str:
    """Convert a wiki page title to a safe filename."""
    name = title.replace("/", "_").replace("\\", "_")
    name = re.sub(r'[<>:"|?*]', "", name)
    name = name.strip(". ")
    return f"{name}.md"


def run(args: argparse.Namespace) -> int:
    """Main entry point. Returns 0 on success, 1 if any fetch failed."""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    try:
        titles = discover_page_titles(client)
        if not titles:
            logger.error("No pages discovered — nothing to do")
            return 1

        succeeded = 0
        failed = 0
        skipped = 0

        for i, title in enumerate(titles, 1):
            if should_skip_title(title):
                logger.info("[%d/%d] %s — skipped (title excluded)", i, len(titles), title)
                skipped += 1
                continue

            filename = sanitize_filename(title)
            out_path = output_dir / filename
            log_prefix = f"[{i}/{len(titles)}] {title}"

            if out_path.exists():
                logger.info("%s — cached on disk, skipping fetch", log_prefix)
                skipped += 1
                continue

            logger.info("%s — fetching", log_prefix)
            html = fetch_page_html(client, title)
            if html is None:
                failed += 1
                continue

            content = html_to_markdown(html, title)
            if not args.dry_run:
                out_path.write_text(content, encoding="utf-8")
            succeeded += 1

            if i < len(titles):
                time.sleep(args.delay)

        logger.info("Done: %d written, %d failed, %d skipped (cached)", succeeded, failed, skipped)
        return 0 if failed == 0 else 1
    finally:
        client.close()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Path of Exile 2 wiki pages and write Markdown to disk.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        metavar="DIR",
        help="Directory to write .md files to (used as cache for re-runs)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover and fetch but do not write files",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds between wiki API requests (default: 1.0)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    return run(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
