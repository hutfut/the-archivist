#!/usr/bin/env python3
"""Fetch pages from the Path of Exile 2 wiki and upload them to the backend.

Discovers all internal links on the main wiki page, fetches each page's
rendered HTML via the MediaWiki API, converts to Markdown, and uploads
as .md files through POST /api/documents.

Usage:
    python seed_wiki.py
    python seed_wiki.py --dry-run --output-dir ./wiki_pages
    python seed_wiki.py --api-url http://localhost:8000 --delay 0.5
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from bs4 import BeautifulSoup, Tag
from markdownify import markdownify

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger("seed_wiki")

WIKI_API = "https://www.poe2wiki.net/api.php"
MAIN_PAGE = "Path_of_Exile_2_Wiki"
USER_AGENT = "poe2-wiki-seeder/1.0 (notebooklm assessment project)"
REQUEST_TIMEOUT = 30.0


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
        logger.warning("Invalid JSON response for '%s' (len=%d)", title, len(resp.content))
        return None

    if "error" in data:
        logger.warning("API error for '%s': %s", title, data["error"].get("info"))
        return None

    return data["parse"]["text"]["*"]


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


def html_to_markdown(html: str, title: str) -> str:
    """Convert cleaned HTML to Markdown with a title header."""
    cleaned = clean_html(html)
    md: str = markdownify(cleaned, heading_style="ATX", strip=["img"])

    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r"[ \t]+$", "", md, flags=re.MULTILINE)
    md = md.strip()

    return f"# {title}\n\n{md}\n"


def sanitize_filename(title: str) -> str:
    """Convert a wiki page title to a safe filename."""
    name = title.replace("/", "_").replace("\\", "_")
    name = re.sub(r'[<>:"|?*]', "", name)
    name = name.strip(". ")
    return f"{name}.md"


def upload_file(
    client: httpx.Client,
    api_url: str,
    filename: str,
    content: str,
) -> bool:
    """Upload a Markdown document to the backend. Returns True on success."""
    url = f"{api_url.rstrip('/')}/api/documents"
    files = {"file": (filename, content.encode("utf-8"), "text/markdown")}

    try:
        resp = client.post(url, files=files)
    except httpx.RequestError as exc:
        logger.error("Upload failed for '%s': %s", filename, exc)
        return False

    if resp.status_code == 201:
        return True

    logger.error(
        "Upload returned %d for '%s': %s",
        resp.status_code,
        filename,
        resp.text[:200],
    )
    return False


def run(args: argparse.Namespace) -> int:
    """Main entry point. Returns 0 on success, 1 if any pages failed."""
    output_dir: Path | None = Path(args.output_dir) if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    wiki_client = httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    upload_client = httpx.Client(timeout=60.0)

    try:
        titles = discover_page_titles(wiki_client)
        if not titles:
            logger.error("No pages discovered — nothing to do")
            return 1

        succeeded = 0
        failed = 0
        skipped = 0

        for i, title in enumerate(titles, 1):
            filename = sanitize_filename(title)
            log_prefix = f"[{i}/{len(titles)}] {title}"

            if output_dir and (output_dir / filename).exists():
                logger.info("%s — cached on disk, skipping fetch", log_prefix)
                content = (output_dir / filename).read_text(encoding="utf-8")
                skipped += 1
            else:
                logger.info("%s — fetching", log_prefix)
                html = fetch_page_html(wiki_client, title)
                if html is None:
                    failed += 1
                    continue

                content = html_to_markdown(html, title)

                if output_dir:
                    (output_dir / filename).write_text(content, encoding="utf-8")

                if i < len(titles):
                    time.sleep(args.delay)

            if args.dry_run:
                logger.info("%s — dry run, skipping upload", log_prefix)
                succeeded += 1
                continue

            logger.info("%s — uploading as %s", log_prefix, filename)
            if upload_file(upload_client, args.api_url, filename, content):
                succeeded += 1
            else:
                failed += 1

        logger.info(
            "Done: %d succeeded, %d failed, %d skipped (cached)",
            succeeded,
            failed,
            skipped,
        )
        return 0 if failed == 0 else 1

    finally:
        wiki_client.close()
        upload_client.close()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the vector DB with Path of Exile 2 wiki pages.",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Save .md files to this directory (enables caching for re-runs)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and convert pages but skip uploading to the backend",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between wiki API requests (default: 1.0)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    args = parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
