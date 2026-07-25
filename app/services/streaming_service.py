import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.video import Video, StreamingVariant
from app.services.ffmpeg_service import FFmpegService
from app.config import settings
import logging


logger = logging.getLogger(__name__)


class StreamingService:
    @staticmethod
    def prepare_streaming_video(db: Session, video_id: str, qualities: Optional[List[str]] = None) -> bool:
        """
        Prepare video for streaming by creating HLS variants
        """
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")

            if qualities is None:
                qualities = ["480p", "720p", "1080p"]

            # Create streaming directory
            streaming_dir = os.path.join(settings.processed_dir, "streaming", video_id)
            os.makedirs(streaming_dir, exist_ok=True)

            # Generate unique base name for this streaming session
            base_name = f"stream_{uuid.uuid4().hex[:8]}"

            # Create HLS stream
            success = FFmpegService.create_hls_stream(
                input_path=str(video.file_path),
                output_dir=streaming_dir,
                base_name=base_name,
                qualities=qualities
            )

            if success:
                # Update video record
                master_playlist = os.path.join(streaming_dir, f"{base_name}_master.m3u8")
                db.query(Video).filter(Video.id == video_id).update({
                    "streaming_ready": True,
                    "streaming_path": master_playlist,
                    "streaming_qualities": qualities
                })

                # Create streaming variant records
                for quality in qualities:
                    variant_path = os.path.join(streaming_dir, f"{base_name}_{quality}.m3u8")
                    if os.path.exists(variant_path):
                        variant = StreamingVariant(
                            video_id=video_id,
                            quality=quality,
                            speed=1.0,
                            file_path=variant_path,
                            variant_type="hls",
                            width=StreamingService._get_quality_resolution(quality)[0],
                            height=StreamingService._get_quality_resolution(quality)[1],
                            bitrate=StreamingService._get_quality_bitrate(quality)
                        )
                        db.add(variant)

                db.commit()
                logger.info(f"Successfully prepared streaming for video {video_id}")
                return True
            else:
                logger.error(f"Failed to create HLS stream for video {video_id}")
                return False

        except Exception as e:
            logger.error(f"Error preparing streaming video: {e}")
            db.rollback()
            raise

    @staticmethod
    def create_speed_variant(db: Session, video_id: str, speed: float, quality: str = "720p") -> Optional[StreamingVariant]:
        """
        Create a speed-adjusted variant of the video
        """
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")

            # Create speed variant directory
            speed_dir = os.path.join(settings.processed_dir, "streaming", video_id, "speed")
            os.makedirs(speed_dir, exist_ok=True)

            # Generate output filename
            speed_str = f"{speed}x".replace(".", "_")
            output_filename = f"{video.filename.rsplit('.', 1)[0]}_{quality}_{speed_str}.mp4"
            output_path = os.path.join(speed_dir, output_filename)

            # Create speed variant
            success = FFmpegService.create_speed_variant(str(video.file_path), output_path, speed)

            if success:
                # Create streaming variant record
                variant = StreamingVariant(
                    video_id=video_id,
                    quality=quality,
                    speed=speed,
                    file_path=output_path,
                    file_size=os.path.getsize(output_path),
                    variant_type="mp4",
                    width=StreamingService._get_quality_resolution(quality)[0],
                    height=StreamingService._get_quality_resolution(quality)[1],
                    bitrate=StreamingService._get_quality_bitrate(quality)
                )
                db.add(variant)
                db.commit()
                db.refresh(variant)

                logger.info(f"Created speed variant {speed}x for video {video_id}")
                return variant
            else:
                logger.error(f"Failed to create speed variant for video {video_id}")
                return None

        except Exception as e:
            logger.error(f"Error creating speed variant: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_streaming_info(db: Session, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get streaming information for a video
        """
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video or not bool(video.streaming_ready):
                return None

            variants = db.query(StreamingVariant).filter(
                StreamingVariant.video_id == video_id
            ).all()

            return {
                "video_id": video_id,
                "streaming_ready": video.streaming_ready,
                "master_playlist": video.streaming_path,
                "qualities": video.streaming_qualities or [],
                "variants": [
                    {
                        "id": variant.id,
                        "quality": variant.quality,
                        "speed": variant.speed,
                        "file_path": variant.file_path,
                        "width": variant.width,
                        "height": variant.height,
                        "bitrate": variant.bitrate,
                        "variant_type": variant.variant_type
                    }
                    for variant in variants
                ]
            }

        except Exception as e:
            logger.error(f"Error getting streaming info: {e}")
            raise

    @staticmethod
    def get_streaming_variant(db: Session, variant_id: str) -> Optional[StreamingVariant]:
        """
        Get a specific streaming variant
        """
        return db.query(StreamingVariant).filter(StreamingVariant.id == variant_id).first()

    @staticmethod
    def _get_quality_resolution(quality: str) -> tuple:
        """Get resolution for quality"""
        resolutions = {
            "360p": (640, 360),
            "480p": (854, 480),
            "720p": (1280, 720),
            "1080p": (1920, 1080)
        }
        return resolutions.get(quality, (854, 480))

    @staticmethod
    def _get_quality_bitrate(quality: str) -> str:
        """Get bitrate for quality"""
        bitrates = {
            "360p": "800k",
            "480p": "1200k",
            "720p": "2500k",
            "1080p": "5000k"
        }
        return bitrates.get(quality, "1200k")

    @staticmethod
    def generate_thumbnail(db: Session, video_id: str) -> Optional[str]:
        """
        Generate and return thumbnail URL for a video
        """
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                return None

            # Create thumbnail directory if it doesn't exist
            thumbnail_dir = os.path.join(settings.processed_dir, "thumbnails")
            os.makedirs(thumbnail_dir, exist_ok=True)

            # Generate thumbnail filename
            thumbnail_filename = f"{video_id}.jpg"
            thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)

            # Generate thumbnail at 1 second mark
            success = FFmpegService.generate_thumbnail(str(video.file_path), thumbnail_path, 1.0)

            if success:
                return f"/static/thumbnails/{thumbnail_filename}"
            else:
                return None

        except Exception as e:
            logger.error(f"Error generating thumbnail for video {video_id}: {e}")
            return None