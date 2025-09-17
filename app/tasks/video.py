import os
from datetime import datetime
from typing import Optional
from app.celery_app import celery_app
from app.services.ffmpeg_service import FFmpegService
from app.database import SessionLocal
from app.models.video import Video
from app.services.video_service import VideoService


@celery_app.task(name="app.tasks.trim_video")
def trim_video_task(video_id: str, start_time: float, end_time: float) -> dict:
    db = SessionLocal()
    try:
        video: Optional[Video] = VideoService.get_video_by_id(db, video_id)
        if not video:
            return {"status": "error", "error": f"Video {video_id} not found"}

        iso_timestamp = datetime.utcnow().isoformat().replace(":", "-") + "Z"
        filename = f"{iso_timestamp}_trimmed_{os.path.basename(video.filename)}"
        output_path = os.path.join("processed", filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        ok = FFmpegService.trim_video(video.file_path, output_path, start_time, end_time)
        if not ok:
            return {"status": "error", "error": "trim failed"}

        processed = VideoService.record_processed_video(
            db,
            video,
            output_path,
            processing_type="trim",
            processing_config={"start_time": start_time, "end_time": end_time},
        )

        return {"status": "completed", "processed_video_id": processed.id}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.overlay_video")
def overlay_video_task(
    video_id: str,
    overlay_type: str,
    content: str,
    position_x: int = 0,
    position_y: int = 0,
    start_time: float = 0.0,
    end_time: Optional[float] = None,
    font_size: Optional[int] = None,
    font_color: str = "white",
    language: str = "en",
) -> dict:
    db = SessionLocal()
    try:
        video: Optional[Video] = VideoService.get_video_by_id(db, video_id)
        if not video:
            return {"status": "error", "error": f"Video {video_id} not found"}

        iso_timestamp = datetime.utcnow().isoformat().replace(":", "-") + "Z"
        output_filename = f"{iso_timestamp}_overlay_{os.path.basename(video.filename)}"
        output_path = os.path.join("processed", output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Construct full path for overlay file if it's an image or video overlay
        from app.config import settings

        if overlay_type in ("image", "video"):
            overlay_path = os.path.join(settings.assets_dir, content)
            # Check if overlay file exists
            if not os.path.exists(overlay_path):
                return {"status": "error", "error": f"Overlay file not found: {content}"}
            overlay_content = overlay_path
        else:
            overlay_content = content

        success = VideoService.overlay_and_record(
            db,
            video,
            output_path,
            overlay_type=overlay_type,
            content=overlay_content,
            position_x=position_x,
            position_y=position_y,
            start_time=start_time,
            end_time=end_time,
            font_size=font_size,
            font_color=font_color,
            language=language,
        )
        if not success:
            return {"status": "error", "error": "overlay failed"}

        processed = VideoService.get_latest_processed_for_video(db, video.id)
        return {"status": "completed", "processed_video_id": processed.id}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()
