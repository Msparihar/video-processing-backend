import os

print("[router:processing] module import start")
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.video_service import VideoService
from app.schemas.video import TrimRequest, OverlayRequest, WatermarkRequest, QualityRequest, ProcessedVideoResponse
from app.config import settings


print("[router:processing] creating APIRouter")
router = APIRouter()


@router.post("/trim", response_model=ProcessedVideoResponse)
def trim_video(request: TrimRequest, db: Session = Depends(get_db)):
    print("[router:processing] /trim handler invoked")
    video = VideoService.get_video_by_id(db, request.video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if request.start_time >= request.end_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End time must be greater than start time")
    if video.duration and request.end_time > video.duration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"End time cannot exceed video duration ({video.duration}s)"
        )

    output_filename = f"trimmed_{os.path.basename(video.filename)}"
    output_path = os.path.join(settings.processed_dir, output_filename)
    os.makedirs(settings.processed_dir, exist_ok=True)

    success = VideoService.trim_and_record(db, video, output_path, request.start_time, request.end_time)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to trim video")

    processed = VideoService.get_latest_processed_for_video(db, video.id)
    return ProcessedVideoResponse.model_validate(processed, from_attributes=True)


@router.post("/overlay", response_model=ProcessedVideoResponse)
def add_overlay(request: OverlayRequest, db: Session = Depends(get_db)):
    print("[router:processing] /overlay handler invoked")
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
    output_filename = f"overlay_{os.path.basename(video.filename)}"
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
    print("[router:processing] /watermark handler invoked")
    video = VideoService.get_video_by_id(db, request.video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    watermark_path = os.path.join(settings.assets_dir, request.watermark_path)
    if not os.path.exists(watermark_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Watermark file not found: {request.watermark_path}"
        )

    os.makedirs(settings.processed_dir, exist_ok=True)
    output_filename = f"watermarked_{os.path.basename(video.filename)}"
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
    print("[router:processing] /quality handler invoked")
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
    output_filename = f"{target_quality}_{os.path.basename(video.filename)}"
    output_path = os.path.join(settings.processed_dir, output_filename)

    success = VideoService.quality_and_record(db, video, output_path, target_quality)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to convert to {target_quality}"
        )

    processed = VideoService.get_latest_processed_for_video(db, video.id)
    return ProcessedVideoResponse.model_validate(processed, from_attributes=True)


print("[router:processing] module import complete")
