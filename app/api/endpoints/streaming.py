from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from app.api.deps import get_db
from app.services.streaming_service import StreamingService
from app.services.video_service import VideoService
from app.config import settings
from app.schemas.video import StreamingInfoResponse, SpeedVariantRequest


router = APIRouter()


@router.post("/videos/{video_id}/prepare-streaming", response_model=dict)
def prepare_streaming(
    video_id: str,
    qualities: Optional[List[str]] = Query(["480p", "720p", "1080p"], description="Quality variants to generate"),
    db: Session = Depends(get_db),
):
    """
    Prepare video for streaming by creating HLS variants
    """
    try:
        # Check if video exists
        video = VideoService.get_video_by_id(db, video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        # Start streaming preparation
        success = StreamingService.prepare_streaming_video(db, video_id, qualities)

        if success:
            return {
                "message": "Streaming preparation started",
                "video_id": video_id,
                "qualities": qualities
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to prepare streaming")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error preparing streaming: {str(e)}")


@router.get("/videos/{video_id}/streaming-info", response_model=StreamingInfoResponse)
def get_streaming_info(video_id: str, db: Session = Depends(get_db)):
    """
    Get streaming information for a video
    """
    try:
        streaming_info = StreamingService.get_streaming_info(db, video_id)
        if not streaming_info:
            raise HTTPException(status_code=404, detail="Streaming not prepared for this video")

        return StreamingInfoResponse(**streaming_info)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting streaming info: {str(e)}")


@router.get("/videos/{video_id}/stream/{quality}.m3u8")
def get_stream_playlist(video_id: str, quality: str, db: Session = Depends(get_db)):
    """
    Serve HLS playlist for specific quality
    """
    try:
        streaming_info = StreamingService.get_streaming_info(db, video_id)
        if not streaming_info:
            raise HTTPException(status_code=404, detail="Streaming not prepared for this video")

        # Find the variant for this quality
        variant = None
        for v in streaming_info["variants"]:
            if v["quality"] == quality and v["speed"] == 1.0:
                variant = v
                break

        if not variant or not os.path.exists(variant["file_path"]):
            raise HTTPException(status_code=404, detail=f"Quality {quality} not available")

        return FileResponse(
            path=variant["file_path"],
            media_type="application/vnd.apple.mpegurl",
            filename=f"{quality}.m3u8"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving playlist: {str(e)}")


@router.get("/videos/{video_id}/stream/{quality}_{segment}.ts")
def get_stream_segment(video_id: str, quality: str, segment: str, db: Session = Depends(get_db)):
    """
    Serve HLS video segments
    """
    try:
        streaming_info = StreamingService.get_streaming_info(db, video_id)
        if not streaming_info:
            raise HTTPException(status_code=404, detail="Streaming not prepared for this video")

        # Find the variant for this quality
        variant = None
        for v in streaming_info["variants"]:
            if v["quality"] == quality and v["speed"] == 1.0:
                variant = v
                break

        if not variant:
            raise HTTPException(status_code=404, detail=f"Quality {quality} not available")

        # Construct segment path
        segment_dir = os.path.dirname(variant["file_path"])
        segment_path = os.path.join(segment_dir, f"{os.path.basename(variant['file_path']).replace('.m3u8', '')}_{segment}.ts")

        if not os.path.exists(segment_path):
            raise HTTPException(status_code=404, detail="Segment not found")

        return FileResponse(
            path=segment_path,
            media_type="video/mp2t",
            filename=f"{segment}.ts"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving segment: {str(e)}")


@router.post("/videos/{video_id}/speed-variant", response_model=dict)
def create_speed_variant(
    video_id: str,
    request: SpeedVariantRequest,
    db: Session = Depends(get_db),
):
    """
    Create a speed-adjusted variant of the video
    """
    try:
        # Check if video exists
        video = VideoService.get_video_by_id(db, video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        # Validate speed
        if not (0.25 <= request.speed <= 4.0):
            raise HTTPException(status_code=400, detail="Speed must be between 0.25x and 4.0x")

        # Create speed variant
        variant = StreamingService.create_speed_variant(
            db, video_id, request.speed, request.quality
        )

        if variant:
            return {
                "message": "Speed variant created",
                "variant_id": variant.id,
                "speed": request.speed,
                "quality": request.quality,
                "file_path": variant.file_path
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create speed variant")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating speed variant: {str(e)}")


@router.get("/videos/{video_id}/speed-variant/{variant_id}/download")
def download_speed_variant(video_id: str, variant_id: str, db: Session = Depends(get_db)):
    """
    Download a speed-adjusted variant
    """
    try:
        variant = StreamingService.get_streaming_variant(db, variant_id)
        if not variant or str(variant.video_id) != video_id:
            raise HTTPException(status_code=404, detail="Variant not found")

        if not os.path.exists(variant.file_path):
            raise HTTPException(status_code=404, detail="Variant file not found")

        return FileResponse(
            path=variant.file_path,
            media_type="video/mp4",
            filename=f"speed_{variant.speed}x_{variant.quality}_{os.path.basename(variant.file_path)}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading variant: {str(e)}")


@router.get("/videos/{video_id}/master.m3u8")
def get_master_playlist(video_id: str, db: Session = Depends(get_db)):
    """
    Serve HLS master playlist
    """
    try:
        streaming_info = StreamingService.get_streaming_info(db, video_id)
        if not streaming_info or not streaming_info.get("master_playlist"):
            raise HTTPException(status_code=404, detail="Master playlist not found")

        master_path = streaming_info["master_playlist"]
        if not os.path.exists(master_path):
            raise HTTPException(status_code=404, detail="Master playlist file not found")

        return FileResponse(
            path=master_path,
            media_type="application/vnd.apple.mpegurl",
            filename="master.m3u8"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving master playlist: {str(e)}")