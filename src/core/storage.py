"""File storage utilities for handling uploads"""
import os
import uuid
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile

# Base upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Subdirectories for different file types
IMAGES_DIR = UPLOAD_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)

VIDEOS_DIR = UPLOAD_DIR / "videos"
VIDEOS_DIR.mkdir(exist_ok=True)

DOCUMENTS_DIR = UPLOAD_DIR / "documents"
DOCUMENTS_DIR.mkdir(exist_ok=True)

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".avi"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}

# Max file sizes (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20 MB


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return Path(filename).suffix.lower()


def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename preserving extension"""
    ext = get_file_extension(original_filename)
    unique_name = f"{uuid.uuid4()}{ext}"
    return unique_name


async def save_upload_file(upload_file: UploadFile, destination: Path) -> str:
    """Save uploaded file to destination and return relative path"""
    try:
        content = await upload_file.read()
        with open(destination, "wb") as f:
            f.write(content)

        # Return relative path from uploads directory
        return str(destination.relative_to(UPLOAD_DIR.parent))
    finally:
        await upload_file.close()


async def save_image(upload_file: UploadFile) -> str:
    """
    Save uploaded image file
    Returns: relative path to saved file
    Raises: ValueError if file is invalid
    """
    # Validate extension
    ext = get_file_extension(upload_file.filename or "")
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Invalid image format. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # Validate size
    content = await upload_file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise ValueError(f"Image too large. Max size: {MAX_IMAGE_SIZE / 1024 / 1024}MB")

    # Reset file pointer
    await upload_file.seek(0)

    # Generate unique filename
    filename = generate_unique_filename(upload_file.filename or "image.jpg")
    destination = IMAGES_DIR / filename

    # Save file
    return await save_upload_file(upload_file, destination)


async def save_video(upload_file: UploadFile) -> str:
    """
    Save uploaded video file
    Returns: relative path to saved file
    Raises: ValueError if file is invalid
    """
    # Validate extension
    ext = get_file_extension(upload_file.filename or "")
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValueError(
            f"Invalid video format. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )

    # Validate size
    content = await upload_file.read()
    if len(content) > MAX_VIDEO_SIZE:
        raise ValueError(f"Video too large. Max size: {MAX_VIDEO_SIZE / 1024 / 1024}MB")

    # Reset file pointer
    await upload_file.seek(0)

    # Generate unique filename
    filename = generate_unique_filename(upload_file.filename or "video.mp4")
    destination = VIDEOS_DIR / filename

    # Save file
    return await save_upload_file(upload_file, destination)


async def save_document(upload_file: UploadFile) -> str:
    """
    Save uploaded document file
    Returns: relative path to saved file
    Raises: ValueError if file is invalid
    """
    # Validate extension
    ext = get_file_extension(upload_file.filename or "")
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValueError(
            f"Invalid document format. Allowed: {', '.join(ALLOWED_DOCUMENT_EXTENSIONS)}"
        )

    # Validate size
    content = await upload_file.read()
    if len(content) > MAX_DOCUMENT_SIZE:
        raise ValueError(f"Document too large. Max size: {MAX_DOCUMENT_SIZE / 1024 / 1024}MB")

    # Reset file pointer
    await upload_file.seek(0)

    # Generate unique filename
    filename = generate_unique_filename(upload_file.filename or "document.pdf")
    destination = DOCUMENTS_DIR / filename

    # Save file
    return await save_upload_file(upload_file, destination)


def delete_file(file_path: str) -> bool:
    """Delete file by path. Returns True if deleted, False if not found.

    Only deletes files inside UPLOAD_DIR.parent - resolves the path first so
    "../" segments can't be used to escape the uploads directory.
    """
    try:
        base_dir = UPLOAD_DIR.parent.resolve()
        path = (base_dir / file_path).resolve()
        if base_dir not in path.parents:
            return False
        if path.exists() and path.is_file():
            path.unlink()
            return True
        return False
    except Exception:
        return False
