#!/usr/bin/env python3
"""Upload Markdown documents to the backend document API.

Generic seeder: accepts a zip archive and/or a list of paths (files or
directories). All .md files from these sources are uploaded via
POST /api/documents.

Usage:
    python seed_documents.py --zip wiki_pages.zip
    python seed_documents.py --paths wiki_pages/
    python seed_documents.py --paths doc1.md doc2.md ./content/
    python seed_documents.py --zip wiki_pages.zip --paths extra/
    python seed_documents.py --zip wiki_pages.zip --dry-run
"""

from __future__ import annotations

import argparse
import logging
import zipfile
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

import httpx

logger = logging.getLogger("seed_documents")

UPLOAD_TIMEOUT = 60.0


def iter_md_from_zip(zip_path: Path) -> Iterator[tuple[str, str]]:
    """Yield (filename, content) for each .md entry in the zip."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if not name.endswith(".md"):
                continue
            try:
                content = zf.read(name).decode("utf-8")
            except (KeyError, UnicodeDecodeError) as e:
                logger.warning("Skipping %s: %s", name, e)
                continue
            # Use basename so "wiki_pages/Title.md" -> "Title.md"
            filename = Path(name).name
            yield filename, content


def iter_md_from_paths(paths: Iterable[Path]) -> Iterator[tuple[str, str]]:
    """Yield (filename, content) for each .md file in the given paths (files or dirs)."""
    seen: set[Path] = set()
    for p in paths:
        p = p.resolve()
        if p.is_file():
            if p.suffix.lower() == ".md" and p not in seen:
                seen.add(p)
                try:
                    yield p.name, p.read_text(encoding="utf-8")
                except OSError as e:
                    logger.warning("Skipping %s: %s", p, e)
        elif p.is_dir():
            for child in sorted(p.iterdir()):
                if child.is_file() and child.suffix.lower() == ".md" and child not in seen:
                    seen.add(child)
                    try:
                        yield child.name, child.read_text(encoding="utf-8")
                    except OSError as e:
                        logger.warning("Skipping %s: %s", child, e)
        else:
            logger.warning("No such path: %s", p)


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
    """Main entry point. Returns 0 on success, 1 if any upload failed."""
    sources: list[Iterator[tuple[str, str]]] = []

    if args.zip:
        zip_path = Path(args.zip)
        if not zip_path.exists():
            logger.error("Zip file not found: %s", zip_path)
            return 1
        try:
            sources.append(iter_md_from_zip(zip_path))
        except zipfile.BadZipFile as e:
            logger.error("Invalid zip %s: %s", zip_path, e)
            return 1

    if args.paths:
        path_list = [Path(p) for p in args.paths]
        sources.append(iter_md_from_paths(path_list))

    if not sources:
        logger.error("Provide at least one of --zip or --paths")
        return 1

    client = httpx.Client(timeout=UPLOAD_TIMEOUT)
    succeeded = 0
    failed = 0

    try:
        for source in sources:
            for filename, content in source:
                if args.dry_run:
                    logger.info("Would upload: %s", filename)
                    succeeded += 1
                    continue
                logger.info("Uploading: %s", filename)
                if upload_file(client, args.api_url, filename, content):
                    succeeded += 1
                else:
                    failed += 1

        logger.info("Done: %d succeeded, %d failed", succeeded, failed)
        return 0 if failed == 0 else 1
    finally:
        client.close()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload Markdown documents to the backend document API.",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--zip",
        metavar="PATH",
        help="Path to a zip archive containing .md files",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        metavar="PATH",
        default=None,
        help="Paths to .md files or directories containing .md files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List documents that would be uploaded without uploading",
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
    import sys
    sys.exit(main())
