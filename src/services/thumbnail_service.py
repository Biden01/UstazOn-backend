"""Thumbnail generation service for PDF/PPTX/DOC files.

Converts document pages to JPEG images using PyMuPDF.
For non-PDF formats, uses LibreOffice headless to convert to PDF first.
"""

import asyncio
import logging
import tempfile
from pathlib import Path

from src.core.storage import THUMBNAILS_DIR

logger = logging.getLogger(__name__)

# File extensions that need LibreOffice conversion to PDF first
LIBREOFFICE_FORMATS = {".pptx", ".ppt", ".docx", ".doc"}
PDF_FORMATS = {".pdf"}
SUPPORTED_FORMATS = PDF_FORMATS | LIBREOFFICE_FORMATS

# Render settings
ZOOM_FACTOR = 1.5  # ~1200x900px for standard slides
JPEG_QUALITY = 85


async def _convert_to_pdf_with_libreoffice(file_path: Path, output_dir: Path) -> Path | None:
    """Convert PPTX/DOC/etc to PDF using LibreOffice headless."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "libreoffice", "--headless", "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(file_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if proc.returncode != 0:
            logger.error("LibreOffice conversion failed: %s", stderr.decode())
            return None

        # LibreOffice outputs PDF with same stem name
        pdf_path = output_dir / f"{file_path.stem}.pdf"
        if pdf_path.exists():
            return pdf_path

        logger.error("LibreOffice output PDF not found at %s", pdf_path)
        return None
    except asyncio.TimeoutError:
        logger.error("LibreOffice conversion timed out for %s", file_path)
        return None
    except FileNotFoundError:
        logger.error("LibreOffice not installed, cannot convert %s", file_path.suffix)
        return None


def _render_pdf_pages(pdf_path: Path, output_dir: Path, base_name: str, card_id: int, max_pages: int) -> list[str]:
    """Render PDF pages to JPEG images using PyMuPDF. Returns list of relative paths."""
    import fitz  # PyMuPDF - lazy import so app starts even if not installed

    thumbnails = []
    doc = fitz.open(str(pdf_path))
    try:
        num_pages = min(len(doc), max_pages)
        mat = fitz.Matrix(ZOOM_FACTOR, ZOOM_FACTOR)

        for page_num in range(num_pages):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=mat)

            # Legacy-compatible naming: {name}_page{N}_{card_id}.jpg
            filename = f"{base_name}_page{page_num + 1}_{card_id}.jpg"
            output_path = output_dir / filename

            pix.save(str(output_path), output="jpeg", jpg_quality=JPEG_QUALITY)
            pix = None  # free memory

            # Return path relative to project root (for /media/ serving)
            rel_path = f"cards/image/{filename}"
            thumbnails.append(rel_path)
    finally:
        doc.close()

    return thumbnails


async def generate_thumbnails(file_path: str, card_id: int, max_pages: int = 5) -> list[str]:
    """Generate thumbnail images from a document file.

    Args:
        file_path: Path to the document (relative or absolute).
        card_id: Card ID for naming output files.
        max_pages: Maximum number of pages to render (default 5).

    Returns:
        List of relative paths to generated thumbnails (e.g. ["cards/image/name_page1_123.jpg", ...]).
        Empty list if generation fails.
    """
    # Skip if it looks like an external URL (not a local file)
    if file_path.startswith(("http://", "https://", "//")):
        return []

    # Resolve file path
    source = Path(file_path)
    if not source.is_absolute():
        source = Path.cwd() / source
    if not source.exists():
        # Also try under media/ prefix (legacy paths)
        alt = Path.cwd() / "media" / file_path
        if alt.exists():
            source = alt
        else:
            logger.warning("File not found for thumbnail generation: %s", source)
            return []

    ext = source.suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        return []

    # Ensure output directory exists
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

    # Base name for output files (stem of original, truncated)
    base_name = source.stem[:50]

    try:
        if ext in LIBREOFFICE_FORMATS:
            # Convert to PDF first via LibreOffice
            with tempfile.TemporaryDirectory() as tmp_dir:
                pdf_path = await _convert_to_pdf_with_libreoffice(source, Path(tmp_dir))
                if not pdf_path:
                    return []
                return await asyncio.to_thread(
                    _render_pdf_pages, pdf_path, THUMBNAILS_DIR, base_name, card_id, max_pages
                )
        else:
            # Direct PDF rendering
            return await asyncio.to_thread(
                _render_pdf_pages, source, THUMBNAILS_DIR, base_name, card_id, max_pages
            )
    except Exception:
        logger.exception("Thumbnail generation failed for %s (card %d)", file_path, card_id)
        return []
