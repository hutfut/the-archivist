import logging
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)

_CONTENT_TYPE_EXTRACTORS: dict[str, str] = {
    "application/pdf": "pdf",
    "text/plain": "plain",
    "text/markdown": "plain",
}


def extract_text(file_path: Path, content_type: str) -> str:
    """Extract plain text from a supported file format.

    Args:
        file_path: Path to the uploaded file on disk.
        content_type: MIME type of the file.

    Returns:
        The extracted text content.

    Raises:
        ValueError: If the content type is not supported.
        FileNotFoundError: If the file does not exist.
    """
    extractor = _CONTENT_TYPE_EXTRACTORS.get(content_type)
    if extractor is None:
        raise ValueError(f"Unsupported content type: {content_type}")

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if extractor == "pdf":
        return _extract_pdf(file_path)
    return _extract_plain(file_path)


def _extract_pdf(file_path: Path) -> str:
    reader = PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages).strip()
    logger.info(
        "Extracted %d characters from %d-page PDF %s",
        len(text),
        len(reader.pages),
        file_path.name,
    )
    return text


def _extract_plain(file_path: Path) -> str:
    text = file_path.read_text(encoding="utf-8").strip()
    logger.info("Extracted %d characters from %s", len(text), file_path.name)
    return text
