"""File upload endpoints"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from src.api.deps import get_current_user
from src.core.storage import save_image, save_video, save_document, save_file
from src.models.user import User

router = APIRouter()


class UploadResponse(BaseModel):
    """Response model for file uploads"""

    file_path: str
    message: str


@router.post("/images", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload an image file (jpg, png, gif, webp). Max size: 10MB"""
    try:
        file_path = await save_image(file)
        return UploadResponse(
            file_path=file_path, message="Image uploaded successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.post("/videos", response_model=UploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a video file (mp4, webm, mov, avi). Max size: 100MB"""
    try:
        file_path = await save_video(file)
        return UploadResponse(
            file_path=file_path, message="Video uploaded successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.post("/documents", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a document file (pdf, doc, docx, ppt, pptx, xls, xlsx). Max size: 20MB"""
    try:
        file_path = await save_document(file)
        return UploadResponse(
            file_path=file_path, message="Document uploaded successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.post("/files", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload any file type. Max size: 50MB"""
    try:
        file_path = await save_file(file)
        return UploadResponse(
            file_path=file_path, message="File uploaded successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.post("/images/bulk", response_model=list[UploadResponse])
async def upload_multiple_images(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload multiple images at once. Max 5 files, each max 10MB"""
    if len(files) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 images allowed per upload",
        )

    results = []
    for file in files:
        try:
            file_path = await save_image(file)
            results.append(
                UploadResponse(
                    file_path=file_path, message="Image uploaded successfully"
                )
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error uploading {file.filename}: {str(e)}",
            )

    return results
