import os
from fastapi.responses import FileResponse

print("[router:upload] module import start")
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.video_service import VideoService
from app.schemas.video import VideoList, VideoResponse
from app.config import settings


print("[router:upload] creating APIRouter")
router = APIRouter()


@router.post("/upload", response_model=VideoResponse)
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    print("[router:upload] /upload handler invoked")
    if hasattr(file, "size") and file.size and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {settings.max_file_size} bytes",
        )

    try:
        file_path, filename = VideoService.save_upload_file(file)
        mime_type = VideoService.validate_video_file(file_path)
        video = VideoService.create_video_record(db, file, file_path, filename, mime_type)
        return VideoResponse.model_validate(video, from_attributes=True)
    except ValueError as e:
        if "file_path" in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        if "file_path" in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error uploading file: {str(e)}")


@router.get("/videos", response_model=VideoList)
def list_videos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    print("[router:upload] /videos handler invoked")
    videos, total = VideoService.list_videos(db, skip=skip, limit=limit)
    return VideoList(
        videos=[VideoResponse.model_validate(v, from_attributes=True) for v in videos],
        total=total,
        page=skip // limit + 1,
        limit=limit,
    )


@router.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(video_id: str, db: Session = Depends(get_db)):
    print(f"[router:upload] /videos/{video_id} handler invoked")
    video = VideoService.get_video_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return VideoResponse.model_validate(video, from_attributes=True)


@router.get("/videos/{video_id}/download")
def download_video(video_id: str, db: Session = Depends(get_db)):
    video = VideoService.get_video_by_id(db, video_id)
    if not video or not os.path.exists(video.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return FileResponse(
        path=video.file_path,
        filename=video.original_filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={video.original_filename}"},
    )


print("[router:upload] module import complete")
