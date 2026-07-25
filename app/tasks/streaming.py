import os
from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.streaming_service import StreamingService
from app.services.video_service import VideoService
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.prepare_streaming")
def prepare_streaming_task(video_id: str, qualities: list = None):
    """
    Background task to prepare video for streaming
    """
    if qualities is None:
        qualities = ["480p", "720p", "1080p"]

    db = SessionLocal()
    try:
        logger.info(f"Starting streaming preparation for video {video_id}")

        # Check if video exists
        video = VideoService.get_video_by_id(db, video_id)
        if not video:
            logger.error(f"Video {video_id} not found")
            return {"status": "error", "error": f"Video {video_id} not found"}

        # Prepare streaming
        success = StreamingService.prepare_streaming_video(db, video_id, qualities)

        if success:
            logger.info(f"Successfully prepared streaming for video {video_id}")
            return {"status": "completed", "video_id": video_id, "qualities": qualities}
        else:
            logger.error(f"Failed to prepare streaming for video {video_id}")
            return {"status": "error", "error": "Streaming preparation failed"}

    except Exception as exc:
        logger.error(f"Error preparing streaming for video {video_id}: {exc}")
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.create_speed_variant")
def create_speed_variant_task(video_id: str, speed: float, quality: str = "720p"):
    """
    Background task to create a speed-adjusted variant
    """
    db = SessionLocal()
    try:
        logger.info(f"Starting speed variant creation for video {video_id}, speed {speed}x")

        # Check if video exists
        video = VideoService.get_video_by_id(db, video_id)
        if not video:
            logger.error(f"Video {video_id} not found")
            return {"status": "error", "error": f"Video {video_id} not found"}

        # Create speed variant
        variant = StreamingService.create_speed_variant(db, video_id, speed, quality)

        if variant:
            logger.info(f"Successfully created speed variant {speed}x for video {video_id}")
            return {
                "status": "completed",
                "video_id": video_id,
                "variant_id": variant.id,
                "speed": speed,
                "quality": quality
            }
        else:
            logger.error(f"Failed to create speed variant for video {video_id}")
            return {"status": "error", "error": "Speed variant creation failed"}

    except Exception as exc:
        logger.error(f"Error creating speed variant for video {video_id}: {exc}")
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()