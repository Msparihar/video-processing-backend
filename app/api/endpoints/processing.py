from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
from datetime import datetime
from app.models.video import ProcessedVideo

from app.api.deps import get_db
from app.services.video_service import VideoService
from app.schemas.video import (
    TrimRequest,
    OverlayRequest,
    WatermarkRequest,
    QualityRequest,
    ProcessedVideoResponse,
    CeleryOverlayRequest,
)
from app.config import settings
from app.tasks.echo import echo
from app.tasks.video import trim_video_task, overlay_video_task

router = APIRouter()


@router.post("/trim", response_model=ProcessedVideoResponse)
def trim_video(request: TrimRequest, db: Session = Depends(get_db)):
    video = VideoService.get_video_by_id(db, request.video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if request.start_time >= request.end_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End time must be greater than start time")
    if video.duration and request.end_time > video.duration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"End time cannot exceed video duration ({video.duration}s)"
        )

    iso_timestamp = datetime.utcnow().isoformat().replace(":", "-") + "Z"
    output_filename = f"{iso_timestamp}_trimmed_{os.path.basename(video.filename)}"
    output_path = os.path.join(settings.processed_dir, output_filename)
    os.makedirs(settings.processed_dir, exist_ok=True)

    success = VideoService.trim_and_record(db, video, output_path, request.start_time, request.end_time)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to trim video")

    processed = VideoService.get_latest_processed_for_video(db, video.id)
    return ProcessedVideoResponse.model_validate(processed, from_attributes=True)


@router.post("/overlay", response_model=ProcessedVideoResponse)
def add_overlay(request: OverlayRequest, db: Session = Depends(get_db)):
    video = VideoService.get_video_by_id(db, request.video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if request.overlay_type in ("image", "video"):
        overlay_path = os.path.join(settings.assets_dir, request.content)
        if not os.path.exists(overlay_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Overlay file not found: {request.content}"
            )
        overlay_content = overlay_path
    else:
        overlay_content = request.content

    os.makedirs(settings.processed_dir, exist_ok=True)
    iso_timestamp = datetime.utcnow().isoformat().replace(":", "-") + "Z"
    output_filename = f"{iso_timestamp}_overlay_{os.path.basename(video.filename)}"
    output_path = os.path.join(settings.processed_dir, output_filename)

    success = VideoService.overlay_and_record(
        db,
        video,
        output_path,
        overlay_type=request.overlay_type,
        content=overlay_content,
        position_x=request.position_x,
        position_y=request.position_y,
        start_time=request.start_time,
        end_time=request.end_time,
        font_size=request.font_size or 24,
        font_color=request.font_color or "white",
        language=request.language or "en",
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add overlay")

    processed = VideoService.get_latest_processed_for_video(db, video.id)
    return ProcessedVideoResponse.model_validate(processed, from_attributes=True)


@router.post("/watermark", response_model=ProcessedVideoResponse)
def add_watermark(request: WatermarkRequest, db: Session = Depends(get_db)):
    video = VideoService.get_video_by_id(db, request.video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    watermark_path = os.path.join(settings.assets_dir, request.watermark_path)
    if not os.path.exists(watermark_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Watermark file not found: {request.watermark_path}"
        )

    os.makedirs(settings.processed_dir, exist_ok=True)
    iso_timestamp = datetime.utcnow().isoformat().replace(":", "-") + "Z"
    output_filename = f"{iso_timestamp}_watermarked_{os.path.basename(video.filename)}"
    output_path = os.path.join(settings.processed_dir, output_filename)

    success = VideoService.watermark_and_record(
        db,
        video,
        output_path,
        watermark_path=watermark_path,
        position=request.position,
        opacity=request.opacity,
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add watermark")

    processed = VideoService.get_latest_processed_for_video(db, video.id)
    return ProcessedVideoResponse.model_validate(processed, from_attributes=True)


@router.post("/quality", response_model=ProcessedVideoResponse)
def convert_quality(request: QualityRequest, db: Session = Depends(get_db)):
    video = VideoService.get_video_by_id(db, request.video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    valid_qualities = ["1080p", "720p", "480p"]
    invalid = [q for q in request.qualities if q not in valid_qualities]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid qualities: {invalid}. Valid options: {valid_qualities}",
        )

    target_quality = request.qualities[0]

    os.makedirs(settings.processed_dir, exist_ok=True)
    iso_timestamp = datetime.utcnow().isoformat().replace(":", "-") + "Z"
    output_filename = f"{iso_timestamp}_{target_quality}_{os.path.basename(video.filename)}"
    output_path = os.path.join(settings.processed_dir, output_filename)

    success = VideoService.quality_and_record(db, video, output_path, target_quality)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to convert to {target_quality}"
        )

    processed = VideoService.get_latest_processed_for_video(db, video.id)
    return ProcessedVideoResponse.model_validate(processed, from_attributes=True)


# ---------------------- Celery-backed sample endpoints ----------------------


class CeleryEchoRequest(BaseModel):
    message: str


@router.post("/celery/echo", tags=["celery"])
def celery_echo(req: CeleryEchoRequest):
    task = echo.delay(req.message)
    return {"task_id": task.id}


class CeleryTrimRequest(BaseModel):
    video_id: str
    start_time: float
    end_time: float


@router.post("/celery/trim", tags=["celery"])
def celery_trim(req: CeleryTrimRequest):
    task = trim_video_task.delay(req.video_id, req.start_time, req.end_time)
    return {"task_id": task.id}


@router.get("/celery/status/{task_id}", tags=["celery"])
def celery_status(task_id: str):
    from celery.result import AsyncResult
    from app.celery_app import celery_app

    res = AsyncResult(task_id, app=celery_app)
    payload = {
        "task_id": task_id,
        "state": res.state,
        "successful": res.successful() if res.state in {"SUCCESS", "FAILURE"} else None,
        "result": res.result if res.ready() else None,
    }
    return payload


@router.post("/celery/overlay", tags=["celery"])
def celery_overlay(req: CeleryOverlayRequest):
    task = overlay_video_task.delay(
        req.video_id,
        req.overlay_type,
        req.content,
        req.position_x,
        req.position_y,
        req.start_time,
        req.end_time,
        req.font_size,
        req.font_color or "white",
        req.language or "en",
    )
    return {"task_id": task.id}


@router.get("/processed/{processed_id}/download")
def download_processed(processed_id: str, db: Session = Depends(get_db)):
    processed = db.query(ProcessedVideo).filter(ProcessedVideo.id == processed_id).first()
    if not processed or not os.path.exists(processed.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processed video not found")
    return FileResponse(
        path=processed.file_path,
        filename=processed.filename,
        media_type='application/octet-stream',
        headers={"Content-Disposition": f"attachment; filename={processed.filename}"}
    )
