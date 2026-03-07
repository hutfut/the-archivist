#!/usr/bin/env python3
"""Upload documents to the backend document API.

Generic seeder: accepts a zip archive and/or a list of paths (files or
directories). A zip may contain any mix of API-supported types (.md, .txt,
.pdf); paths may be files or dirs of those types. All are uploaded via
POST /api/documents.

Usage:
    python seed_documents.py --zip docs.zip
    python seed_documents.py --paths wiki_pages/
    python seed_documents.py --paths doc1.md doc2.txt report.pdf ./content/
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

# Must match backend app/config.py ALLOWED_EXTENSIONS and EXTENSION_TO_CONTENT_TYPE.
ALLOWED_EXTENSIONS = frozenset({".pdf", ".txt", ".md"})
EXTENSION_TO_CONTENT_TYPE = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


def _content_type_for(filename: str) -> str:
    """Return MIME type for filename; application/octet-stream if not allowed."""
    ext = Path(filename).suffix.lower()
    return EXTENSION_TO_CONTENT_TYPE.get(ext, "application/octet-stream")


def iter_docs_from_zip(zip_path: Path) -> Iterator[tuple[str, bytes, str]]:
    """Yield (filename, content_bytes, content_type) for each API-supported file in the zip."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            ext = Path(name).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            try:
                content = zf.read(name)
            except (KeyError, zipfile.BadZipFile) as e:
                logger.warning("Skipping %s: %s", name, e)
                continue
            if not content:
                logger.warning("Skipping empty entry: %s", name)
                continue
            filename = Path(name).name
            yield filename, content, _content_type_for(filename)


def iter_docs_from_paths(paths: Iterable[Path]) -> Iterator[tuple[str, bytes, str]]:
    """Yield (filename, content_bytes, content_type) for each supported file in the given paths."""
    seen: set[Path] = set()
    for p in paths:
        p = p.resolve()
        if p.is_file():
            if p.suffix.lower() in ALLOWED_EXTENSIONS and p not in seen:
                seen.add(p)
                try:
                    content = p.read_bytes()
                    if not content:
                        logger.warning("Skipping empty file: %s", p)
                        continue
                    yield p.name, content, _content_type_for(p.name)
                except OSError as e:
                    logger.warning("Skipping %s: %s", p, e)
        elif p.is_dir():
            for child in sorted(p.iterdir()):
                if (
                    child.is_file()
                    and child.suffix.lower() in ALLOWED_EXTENSIONS
                    and child not in seen
                ):
                    seen.add(child)
                    try:
                        content = child.read_bytes()
                        if not content:
                            logger.warning("Skipping empty file: %s", child)
                            continue
                        yield child.name, content, _content_type_for(child.name)
                    except OSError as e:
                        logger.warning("Skipping %s: %s", child, e)
        else:
            logger.warning("No such path: %s", p)


def upload_file(
    client: httpx.Client,
    api_url: str,
    filename: str,
    content: bytes,
    content_type: str,
) -> bool:
    """Upload a document to the backend. Returns True on success."""
    url = f"{api_url.rstrip('/')}/api/documents"
    files = {"file": (filename, content, content_type)}
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
    sources: list[Iterator[tuple[str, bytes, str]]] = []

    if args.zip:
        zip_path = Path(args.zip)
        if not zip_path.exists():
            logger.error("Zip file not found: %s", zip_path)
            return 1
        try:
            sources.append(iter_docs_from_zip(zip_path))
        except zipfile.BadZipFile as e:
            logger.error("Invalid zip %s: %s", zip_path, e)
            return 1

    if args.paths:
        path_list = [Path(p) for p in args.paths]
        sources.append(iter_docs_from_paths(path_list))

    if not sources:
        logger.error("Provide at least one of --zip or --paths")
        return 1

    client = httpx.Client(timeout=UPLOAD_TIMEOUT)
    succeeded = 0
    failed = 0

    try:
        for source in sources:
            for filename, content, content_type in source:
                if args.dry_run:
                    logger.info("Would upload: %s", filename)
                    succeeded += 1
                    continue
                logger.info("Uploading: %s", filename)
                if upload_file(client, args.api_url, filename, content, content_type):
                    succeeded += 1
                else:
                    failed += 1

        logger.info("Done: %d succeeded, %d failed", succeeded, failed)
        return 0 if failed == 0 else 1
    finally:
        client.close()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload documents to the backend document API (.md, .txt, .pdf).",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--zip",
        metavar="PATH",
        help="Path to a zip containing any supported types (.md, .txt, .pdf)",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        metavar="PATH",
        default=None,
        help="Paths to files or directories (supported: .md, .txt, .pdf)",
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
