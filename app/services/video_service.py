import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from fastapi import UploadFile
import magic

from app.models.video import Video, ProcessedVideo, Job
from app.services.ffmpeg_service import FFmpegService
from app.config import settings
import logging


logger = logging.getLogger(__name__)


class VideoService:
    @staticmethod
    def save_upload_file(upload_file: UploadFile) -> Tuple[str, str]:
        file_extension = os.path.splitext(upload_file.filename)[1]
        iso_timestamp = datetime.utcnow().isoformat().replace(":", "-") + "Z"
        unique_filename = f"{iso_timestamp}_{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.upload_dir, unique_filename)

        os.makedirs(settings.upload_dir, exist_ok=True)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        return file_path, unique_filename

    @staticmethod
    def validate_video_file(file_path: str) -> str:
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(file_path)
        if mime_type not in settings.allowed_video_types:
            raise ValueError(f"Unsupported file type: {mime_type}")
        return mime_type

    @staticmethod
    def create_video_record(
        db: Session,
        upload_file: UploadFile,
        file_path: str,
        filename: str,
        mime_type: str,
    ) -> Video:
        try:
            video_info = FFmpegService.get_video_info(file_path)
        except Exception as e:
            logger.warning(f"Could not get video info: {e}")
            video_info = {}

        file_size = os.path.getsize(file_path)
        now = datetime.now(timezone.utc)
        video = Video(
            filename=filename,
            original_filename=upload_file.filename,
            file_path=file_path,
            file_size=file_size,
            duration=video_info.get("duration"),
            width=video_info.get("width"),
            height=video_info.get("height"),
            format=video_info.get("format"),
            mime_type=mime_type,
            upload_time=now,
            timestamp=now,
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        return video

    @staticmethod
    def get_video_by_id(db: Session, video_id: str) -> Optional[Video]:
        return db.query(Video).filter(Video.id == video_id).first()

    @staticmethod
    def list_videos(db: Session, skip: int = 0, limit: int = 100) -> Tuple[List[Video], int]:
        total = db.query(Video).count()
        videos = db.query(Video).offset(skip).limit(limit).all()
        return videos, total

    # Legacy job-related helpers (unused in sync flow) -----------------------
    @staticmethod
    def create_job(db: Session, video_id: str, job_type: str, config: Optional[dict] = None) -> Job:
        job = Job(video_id=video_id, job_type=job_type, status="completed", progress=100, config=config)
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def update_job_status(
        db: Session,
        job_id: str,
        status: str,
        progress: Optional[int] = None,
        result_file_path: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Job]:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = status
            if progress is not None:
                job.progress = progress
            if result_file_path:
                job.result_file_path = result_file_path
            if error_message:
                job.error_message = error_message
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def get_job_by_id(db: Session, job_id: str) -> Optional[Job]:
        return db.query(Job).filter(Job.id == job_id).first()

    # Synchronous processing helpers ----------------------------------------
    @staticmethod
    def record_processed_video(
        db: Session,
        video: Video,
        output_path: str,
        processing_type: str,
        processing_config: Optional[dict] = None,
        quality: Optional[str] = None,
    ) -> ProcessedVideo:
        now = datetime.now(timezone.utc)
        processed_video = ProcessedVideo(
            original_video_id=video.id,
            filename=os.path.basename(output_path),
            file_path=output_path,
            file_size=os.path.getsize(output_path) if os.path.exists(output_path) else 0,
            processing_type=processing_type,
            processing_config=processing_config or {},
            quality=quality,
            created_at=now,
            timestamp=now,
        )
        db.add(processed_video)
        db.commit()
        db.refresh(processed_video)
        return processed_video

    @staticmethod
    def get_latest_processed_for_video(db: Session, video_id: str) -> Optional[ProcessedVideo]:
        return (
            db.query(ProcessedVideo)
            .filter(ProcessedVideo.original_video_id == video_id)
            .order_by(ProcessedVideo.created_at.desc())
            .first()
        )

    @staticmethod
    def trim_and_record(db: Session, video: Video, output_path: str, start_time: float, end_time: float) -> bool:
        success = FFmpegService.trim_video(video.file_path, output_path, start_time, end_time)
        if not success:
            return False
        VideoService.record_processed_video(
            db,
            video,
            output_path,
            processing_type="trim",
            processing_config={"start_time": start_time, "end_time": end_time},
        )
        return True

    @staticmethod
    def overlay_and_record(
        db: Session,
        video: Video,
        output_path: str,
        overlay_type: str,
        content: str,
        position_x: int,
        position_y: int,
        start_time: float,
        end_time: Optional[float],
        font_size: int,
        font_color: str,
        language: str,
    ) -> bool:
        if overlay_type == "text":
            success = FFmpegService.add_text_overlay(
                video.file_path,
                output_path,
                text=content,
                position_x=position_x,
                position_y=position_y,
                start_time=start_time,
                end_time=end_time,
                font_size=font_size,
                font_color=font_color,
                language=language,
            )
        elif overlay_type == "image":
            success = FFmpegService.add_image_overlay(
                video.file_path,
                output_path,
                overlay_path=content,
                position_x=position_x,
                position_y=position_y,
                start_time=start_time,
                end_time=end_time,
            )
        else:
            raise ValueError(f"Unsupported overlay type: {overlay_type}")

        if not success:
            return False

        VideoService.record_processed_video(
            db,
            video,
            output_path,
            processing_type="overlay",
            processing_config={
                "overlay_type": overlay_type,
                "content": content,
                "position_x": position_x,
                "position_y": position_y,
                "start_time": start_time,
                "end_time": end_time,
                "font_size": font_size,
                "font_color": font_color,
                "language": language,
            },
        )
        return True

    @staticmethod
    def watermark_and_record(
        db: Session,
        video: Video,
        output_path: str,
        watermark_path: str,
        position: str,
        opacity: float,
    ) -> bool:
        success = FFmpegService.add_watermark(
            video.file_path,
            output_path,
            watermark_path=watermark_path,
            position=position,
            opacity=opacity,
        )
        if not success:
            return False
        VideoService.record_processed_video(
            db,
            video,
            output_path,
            processing_type="watermark",
            processing_config={"watermark_path": watermark_path, "position": position, "opacity": opacity},
        )
        return True

    @staticmethod
    def quality_and_record(db: Session, video: Video, output_path: str, quality: str) -> bool:
        success = FFmpegService.convert_quality(video.file_path, output_path, quality)
        if not success:
            return False
        VideoService.record_processed_video(
            db,
            video,
            output_path,
            processing_type="quality",
            processing_config={"quality": quality},
            quality=quality,
        )
        return True
