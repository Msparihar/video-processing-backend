# Video Processing Backend Implementation Plan

## Project Overview

Building a FastAPI backend for video editing platform with upload, processing (ffmpeg), trimming, overlays, watermarking, async processing, and multiple quality outputs.

## Technology Stack

- **Framework**: FastAPI
- **Package Manager**: uv
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL
- **Video Processing**: ffmpeg
- **Async Processing**: Celery + Redis
- **File Storage**: Local filesystem

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── video.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── video.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       ├── upload.py
│   │       ├── video.py
│   │       ├── processing.py
│   │       └── jobs.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── video_service.py
│   │   ├── ffmpeg_service.py
│   │   └── job_service.py
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── celery_tasks.py
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── uploads/
├── processed/
├── assets/
├── migrations/
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── README.md
└── pyproject.toml
```

## Step 1: Project Initialization

### 1.1 Create Project Directory and Initialize uv

```bash
mkdir video-processing-backend
cd video-processing-backend
uv init
```

### 1.2 Setup pyproject.toml

```toml
[project]
name = "video-processing-backend"
version = "0.1.0"
description = "FastAPI backend for video processing"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",
    "alembic>=1.13.0",
    "python-multipart>=0.0.6",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "celery>=5.3.0",
    "redis>=5.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "aiofiles>=23.2.0",
    "python-magic>=0.4.0",
    "pillow>=10.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 1.3 Install Dependencies

```bash
uv sync
```

### 1.4 Create Basic Directory Structure

```bash
mkdir -p app/{models,schemas,api/endpoints,services,tasks,utils}
mkdir -p uploads processed assets migrations
touch app/__init__.py app/models/__init__.py app/schemas/__init__.py
touch app/api/__init__.py app/api/endpoints/__init__.py app/services/__init__.py
touch app/tasks/__init__.py app/utils/__init__.py
```

## Step 2: Configuration and Database Setup

### 2.1 Create app/config.py

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # File storage
    upload_dir: str = "uploads"
    processed_dir: str = "processed"
    assets_dir: str = "assets"

    # Security
    secret_key: str = "your-secret-key-here"

    # FFmpeg
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    # Processing
    max_file_size: int = 500 * 1024 * 1024  # 500MB
    allowed_video_types: list = ["video/mp4", "video/avi", "video/mov", "video/wmv"]

    class Config:
        env_file = ".env"

settings = Settings()
```

### 2.2 Create .env.example

```env
DATABASE_URL=postgresql://username:password@localhost:5432/video_processing
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-super-secret-key-here
UPLOAD_DIR=uploads
PROCESSED_DIR=processed
ASSETS_DIR=assets
```

### 2.3 Create app/database.py

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Step 3: Database Models

### 3.1 Create app/models/video.py

```python
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid

class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    duration = Column(Float, nullable=True)  # in seconds
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    format = Column(String, nullable=True)
    mime_type = Column(String, nullable=False)
    upload_time = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    processed_videos = relationship("ProcessedVideo", back_populates="original_video")
    jobs = relationship("Job", back_populates="video")

class ProcessedVideo(Base):
    __tablename__ = "processed_videos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    original_video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    processing_type = Column(String, nullable=False)  # trim, overlay, watermark, quality
    processing_config = Column(JSON, nullable=True)
    quality = Column(String, nullable=True)  # 1080p, 720p, 480p
    duration = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    original_video = relationship("Video", back_populates="processed_videos")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    job_type = Column(String, nullable=False)  # upload, trim, overlay, watermark, quality
    status = Column(String, nullable=False, default="pending")  # pending, processing, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    result_file_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    video = relationship("Video", back_populates="jobs")

class Overlay(Base):
    __tablename__ = "overlays"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    processed_video_id = Column(String, ForeignKey("processed_videos.id"), nullable=False)
    overlay_type = Column(String, nullable=False)  # text, image, video
    content = Column(Text, nullable=True)  # text content or file path
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    start_time = Column(Float, default=0.0)  # seconds
    end_time = Column(Float, nullable=True)  # seconds, null means till end
    font_size = Column(Integer, nullable=True)
    font_color = Column(String, nullable=True)
    language = Column(String, nullable=True)  # for text overlays
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 3.2 Update app/models/**init**.py

```python
from .video import Video, ProcessedVideo, Job, Overlay
```

## Step 4: Database Migration Setup

### 4.1 Create alembic.ini

```ini
[alembic]
script_location = migrations
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url =

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### 4.2 Initialize Alembic

```bash
uv run alembic init migrations
```

### 4.3 Update migrations/env.py

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.database import Base
from app.models import *  # Import all models
from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 4.4 Create First Migration

```bash
uv run alembic revision --autogenerate -m "Initial migration"
uv run alembic upgrade head
```

## Step 5: Pydantic Schemas

### 5.1 Create app/schemas/video.py

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class VideoUpload(BaseModel):
    pass

class VideoResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_size: int
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    mime_type: str
    upload_time: datetime

    class Config:
        from_attributes = True

class VideoList(BaseModel):
    videos: List[VideoResponse]
    total: int
    page: int
    limit: int

class TrimRequest(BaseModel):
    video_id: str
    start_time: float = Field(..., ge=0, description="Start time in seconds")
    end_time: float = Field(..., gt=0, description="End time in seconds")

class OverlayRequest(BaseModel):
    video_id: str
    overlay_type: str = Field(..., regex="^(text|image|video)$")
    content: str
    position_x: int = Field(default=0, ge=0)
    position_y: int = Field(default=0, ge=0)
    start_time: float = Field(default=0.0, ge=0)
    end_time: Optional[float] = Field(None, gt=0)
    font_size: Optional[int] = Field(None, gt=0)
    font_color: Optional[str] = None
    language: Optional[str] = None

class WatermarkRequest(BaseModel):
    video_id: str
    watermark_path: str
    position: str = Field(default="bottom-right", regex="^(top-left|top-right|bottom-left|bottom-right|center)$")
    opacity: float = Field(default=0.8, ge=0.1, le=1.0)

class QualityRequest(BaseModel):
    video_id: str
    qualities: List[str] = Field(default=["1080p", "720p", "480p"])

class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    created_at: datetime
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class JobResult(BaseModel):
    job_id: str
    status: str
    result_file_path: Optional[str] = None
    processed_video_id: Optional[str] = None
    error_message: Optional[str] = None
```

### 5.2 Update app/schemas/**init**.py

```python
from .video import (
    VideoUpload, VideoResponse, VideoList, TrimRequest,
    OverlayRequest, WatermarkRequest, QualityRequest,
    JobResponse, JobResult
)
```

## Step 6: FFmpeg Service

### 6.1 Create app/services/ffmpeg_service.py

```python
import subprocess
import json
import os
from typing import Dict, Any, Optional, List
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class FFmpegService:

    @staticmethod
    def get_video_info(file_path: str) -> Dict[str, Any]:
        """Get video metadata using ffprobe"""
        try:
            cmd = [
                settings.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)

            # Extract video stream info
            video_stream = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)

            if not video_stream:
                raise ValueError("No video stream found")

            return {
                'duration': float(data['format']['duration']),
                'size': int(data['format']['size']),
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'format': data['format']['format_name'],
                'codec': video_stream['codec_name']
            }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            raise

    @staticmethod
    def trim_video(input_path: str, output_path: str, start_time: float, end_time: float) -> bool:
        """Trim video between start and end time"""
        try:
            duration = end_time - start_time
            cmd = [
                settings.ffmpeg_path,
                "-i", input_path,
                "-ss", str(start_time),
                "-t", str(duration),
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                output_path,
                "-y"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error trimming video: {e}")
            raise

    @staticmethod
    def add_text_overlay(input_path: str, output_path: str, text: str,
                        position_x: int = 10, position_y: int = 10,
                        start_time: float = 0, end_time: Optional[float] = None,
                        font_size: int = 24, font_color: str = "white",
                        language: str = "en") -> bool:
        """Add text overlay to video"""
        try:
            # Font path for different languages
            font_paths = {
                "en": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "hi": "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
                "ta": "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
                "te": "/usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf",
                # Add more languages as needed
            }

            font_path = font_paths.get(language, font_paths["en"])

            # Build drawtext filter
            drawtext = f"drawtext=text='{text}':x={position_x}:y={position_y}:fontsize={font_size}:fontcolor={font_color}:fontfile={font_path}"

            if start_time > 0 or end_time:
                enable_condition = f"enable='between(t,{start_time},{end_time or 'inf'})'"
                drawtext += f":{enable_condition}"

            cmd = [
                settings.ffmpeg_path,
                "-i", input_path,
                "-vf", drawtext,
                "-c:a", "copy",
                output_path,
                "-y"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error adding text overlay: {e}")
            raise

    @staticmethod
    def add_image_overlay(input_path: str, output_path: str, overlay_path: str,
                         position_x: int = 10, position_y: int = 10,
                         start_time: float = 0, end_time: Optional[float] = None) -> bool:
        """Add image overlay to video"""
        try:
            overlay_filter = f"[1:v]scale=-1:-1[overlay]; [0:v][overlay]overlay={position_x}:{position_y}"

            if start_time > 0 or end_time:
                enable_condition = f"enable='between(t,{start_time},{end_time or 'inf'})'"
                overlay_filter += f":{enable_condition}"

            cmd = [
                settings.ffmpeg_path,
                "-i", input_path,
                "-i", overlay_path,
                "-filter_complex", overlay_filter,
                "-c:a", "copy",
                output_path,
                "-y"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error adding image overlay: {e}")
            raise

    @staticmethod
    def add_watermark(input_path: str, output_path: str, watermark_path: str,
                     position: str = "bottom-right", opacity: float = 0.8) -> bool:
        """Add watermark to video"""
        try:
            # Position mapping
            positions = {
                "top-left": "10:10",
                "top-right": "main_w-overlay_w-10:10",
                "bottom-left": "10:main_h-overlay_h-10",
                "bottom-right": "main_w-overlay_w-10:main_h-overlay_h-10",
                "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
            }

            pos = positions.get(position, positions["bottom-right"])

            overlay_filter = f"[1:v]format=rgba,colorchannelmixer=aa={opacity}[watermark]; [0:v][watermark]overlay={pos}"

            cmd = [
                settings.ffmpeg_path,
                "-i", input_path,
                "-i", watermark_path,
                "-filter_complex", overlay_filter,
                "-c:a", "copy",
                output_path,
                "-y"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error adding watermark: {e}")
            raise

    @staticmethod
    def convert_quality(input_path: str, output_path: str, quality: str) -> bool:
        """Convert video to different quality"""
        try:
            quality_settings = {
                "1080p": {"width": 1920, "height": 1080, "bitrate": "5M"},
                "720p": {"width": 1280, "height": 720, "bitrate": "2.5M"},
                "480p": {"width": 854, "height": 480, "bitrate": "1M"}
            }

            settings_dict = quality_settings.get(quality)
            if not settings_dict:
                raise ValueError(f"Unsupported quality: {quality}")

            cmd = [
                settings.ffmpeg_path,
                "-i", input_path,
                "-vf", f"scale={settings_dict['width']}:{settings_dict['height']}",
                "-b:v", settings_dict['bitrate'],
                "-c:v", "libx264",
                "-preset", "medium",
                "-c:a", "aac",
                output_path,
                "-y"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error converting quality: {e}")
            raise
```

## Step 7: Video Service

### 7.1 Create app/services/video_service.py

```python
import os
import shutil
import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import UploadFile
import magic

from app.models.video import Video, ProcessedVideo, Job
from app.schemas.video import VideoResponse
from app.services.ffmpeg_service import FFmpegService
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class VideoService:

    @staticmethod
    def save_upload_file(upload_file: UploadFile) -> tuple[str, str]:
        """Save uploaded file and return file_path and filename"""
        # Generate unique filename
        file_extension = os.path.splitext(upload_file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.upload_dir, unique_filename)

        # Ensure upload directory exists
        os.makedirs(settings.upload_dir, exist_ok=True)

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        return file_path, unique_filename

    @staticmethod
    def validate_video_file(file_path: str) -> str:
        """Validate if file is a video and return MIME type"""
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(file_path)

        if mime_type not in settings.allowed_video_types:
            raise ValueError(f"Unsupported file type: {mime_type}")

        return mime_type

    @staticmethod
    def create_video_record(db: Session, upload_file: UploadFile,
                          file_path: str, filename: str, mime_type: str) -> Video:
        """Create video record in database"""
        # Get video metadata
        try:
            video_info = FFmpegService.get_video_info(file_path)
        except Exception as e:
            logger.warning(f"Could not get video info: {e}")
            video_info = {}

        # Get file size
        file_size = os.path.getsize(file_path)

        video = Video(
            filename=filename,
            original_filename=upload_file.filename,
            file_path=file_path,
            file_size=file_size,
            duration=video_info.get('duration'),
            width=video_info.get('width'),
            height=video_info.get('height'),
            format=video_info.get('format'),
            mime_type=mime_type
        )

        db.add(video)
        db.commit()

        # Update job status
        VideoService.update_job_status(db, self.request.id, "completed", 100)

        return {"status": "completed", "video_id": video_id}

    except Exception as e:
        logger.error(f"Error processing video upload: {e}")
        VideoService.update_job_status(db, self.request.id, "failed", error_message=str(e))
        raise
    finally:
        db.close()

@celery_app.task(bind=True)
def trim_video_task(self, video_id: str, start_time: float, end_time: float):
    """Trim video task"""
    db = get_db()
    try:
        VideoService.update_job_status(db, self.request.id, "processing", 20)

        video = VideoService.get_video_by_id(db, video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        # Generate output filename
        output_filename = f"trimmed_{uuid.uuid4()}.mp4"
        output_path = os.path.join(settings.processed_dir, output_filename)
        os.makedirs(settings.processed_dir, exist_ok=True)

        VideoService.update_job_status(db, self.request.id, "processing", 50)

        # Trim video
        success = FFmpegService.trim_video(
            video.file_path, output_path, start_time, end_time
        )

        if not success:
            raise Exception("Failed to trim video")

        VideoService.update_job_status(db, self.request.id, "processing", 80)

        # Create processed video record
        processed_video = ProcessedVideo(
            original_video_id=video_id,
            filename=output_filename,
            file_path=output_path,
            file_size=os.path.getsize(output_path),
            processing_type="trim",
            processing_config={
                "start_time": start_time,
                "end_time": end_time
            }
        )

        db.add(processed_video)
        db.commit()
        db.refresh(processed_video)

        # Update job status
        VideoService.update_job_status(
            db, self.request.id, "completed", 100,
            result_file_path=output_path
        )

        return {
            "status": "completed",
            "processed_video_id": processed_video.id,
            "file_path": output_path
        }

    except Exception as e:
        logger.error(f"Error trimming video: {e}")
        VideoService.update_job_status(db, self.request.id, "failed", error_message=str(e))
        raise
    finally:
        db.close()

@celery_app.task(bind=True)
def add_overlay_task(self, video_id: str, overlay_config: dict):
    """Add overlay to video task"""
    db = get_db()
    try:
        VideoService.update_job_status(db, self.request.id, "processing", 20)

        video = VideoService.get_video_by_id(db, video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        # Generate output filename
        output_filename = f"overlay_{uuid.uuid4()}.mp4"
        output_path = os.path.join(settings.processed_dir, output_filename)
        os.makedirs(settings.processed_dir, exist_ok=True)

        VideoService.update_job_status(db, self.request.id, "processing", 50)

        # Add overlay based on type
        overlay_type = overlay_config.get("overlay_type")

        if overlay_type == "text":
            success = FFmpegService.add_text_overlay(
                video.file_path, output_path,
                text=overlay_config.get("content"),
                position_x=overlay_config.get("position_x", 10),
                position_y=overlay_config.get("position_y", 10),
                start_time=overlay_config.get("start_time", 0),
                end_time=overlay_config.get("end_time"),
                font_size=overlay_config.get("font_size", 24),
                font_color=overlay_config.get("font_color", "white"),
                language=overlay_config.get("language", "en")
            )
        elif overlay_type == "image":
            success = FFmpegService.add_image_overlay(
                video.file_path, output_path,
                overlay_path=overlay_config.get("content"),
                position_x=overlay_config.get("position_x", 10),
                position_y=overlay_config.get("position_y", 10),
                start_time=overlay_config.get("start_time", 0),
                end_time=overlay_config.get("end_time")
            )
        else:
            raise ValueError(f"Unsupported overlay type: {overlay_type}")

        if not success:
            raise Exception("Failed to add overlay")

        VideoService.update_job_status(db, self.request.id, "processing", 80)

        # Create processed video record
        processed_video = ProcessedVideo(
            original_video_id=video_id,
            filename=output_filename,
            file_path=output_path,
            file_size=os.path.getsize(output_path),
            processing_type="overlay",
            processing_config=overlay_config
        )

        db.add(processed_video)
        db.commit()
        db.refresh(processed_video)

        # Update job status
        VideoService.update_job_status(
            db, self.request.id, "completed", 100,
            result_file_path=output_path
        )

        return {
            "status": "completed",
            "processed_video_id": processed_video.id,
            "file_path": output_path
        }

    except Exception as e:
        logger.error(f"Error adding overlay: {e}")
        VideoService.update_job_status(db, self.request.id, "failed", error_message=str(e))
        raise
    finally:
        db.close()

@celery_app.task(bind=True)
def add_watermark_task(self, video_id: str, watermark_config: dict):
    """Add watermark to video task"""
    db = get_db()
    try:
        VideoService.update_job_status(db, self.request.id, "processing", 20)

        video = VideoService.get_video_by_id(db, video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        # Generate output filename
        output_filename = f"watermarked_{uuid.uuid4()}.mp4"
        output_path = os.path.join(settings.processed_dir, output_filename)
        os.makedirs(settings.processed_dir, exist_ok=True)

        VideoService.update_job_status(db, self.request.id, "processing", 50)

        # Add watermark
        success = FFmpegService.add_watermark(
            video.file_path, output_path,
            watermark_path=watermark_config.get("watermark_path"),
            position=watermark_config.get("position", "bottom-right"),
            opacity=watermark_config.get("opacity", 0.8)
        )

        if not success:
            raise Exception("Failed to add watermark")

        VideoService.update_job_status(db, self.request.id, "processing", 80)

        # Create processed video record
        processed_video = ProcessedVideo(
            original_video_id=video_id,
            filename=output_filename,
            file_path=output_path,
            file_size=os.path.getsize(output_path),
            processing_type="watermark",
            processing_config=watermark_config
        )

        db.add(processed_video)
        db.commit()
        db.refresh(processed_video)

        # Update job status
        VideoService.update_job_status(
            db, self.request.id, "completed", 100,
            result_file_path=output_path
        )

        return {
            "status": "completed",
            "processed_video_id": processed_video.id,
            "file_path": output_path
        }

    except Exception as e:
        logger.error(f"Error adding watermark: {e}")
        VideoService.update_job_status(db, self.request.id, "failed", error_message=str(e))
        raise
    finally:
        db.close()

@celery_app.task(bind=True)
def convert_quality_task(self, video_id: str, qualities: list):
    """Convert video to multiple qualities task"""
    db = get_db()
    try:
        VideoService.update_job_status(db, self.request.id, "processing", 10)

        video = VideoService.get_video_by_id(db, video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        results = []
        total_qualities = len(qualities)

        for i, quality in enumerate(qualities):
            # Generate output filename
            output_filename = f"{quality}_{uuid.uuid4()}.mp4"
            output_path = os.path.join(settings.processed_dir, output_filename)
            os.makedirs(settings.processed_dir, exist_ok=True)

            # Update progress
            progress = 20 + (60 * (i + 1) // total_qualities)
            VideoService.update_job_status(db, self.request.id, "processing", progress)

            # Convert quality
            success = FFmpegService.convert_quality(
                video.file_path, output_path, quality
            )

            if not success:
                raise Exception(f"Failed to convert to {quality}")

            # Create processed video record
            processed_video = ProcessedVideo(
                original_video_id=video_id,
                filename=output_filename,
                file_path=output_path,
                file_size=os.path.getsize(output_path),
                processing_type="quality",
                quality=quality,
                processing_config={"quality": quality}
            )

            db.add(processed_video)
            db.commit()
            db.refresh(processed_video)

            results.append({
                "quality": quality,
                "processed_video_id": processed_video.id,
                "file_path": output_path
            })

        # Update job status
        VideoService.update_job_status(db, self.request.id, "completed", 100)

        return {
            "status": "completed",
            "results": results
        }

    except Exception as e:
        logger.error(f"Error converting video quality: {e}")
        VideoService.update_job_status(db, self.request.id, "failed", error_message=str(e))
        raise
    finally:
        db.close()
```

## Step 9: API Dependencies

### 9.1 Create app/api/deps.py

```python
from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import SessionLocal

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user():
    """Placeholder for user authentication"""
    # Implement your authentication logic here
    return {"user_id": "current_user"}
```

## Step 10: API Endpoints

### 10.1 Create app/api/endpoints/upload.py

```python
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.video_service import VideoService
from app.schemas.video import VideoResponse, VideoList, JobResponse
from app.tasks.celery_tasks import process_video_upload
from app.config import settings

router = APIRouter()

@router.post("/upload", response_model=JobResponse)
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a video file"""

    # Validate file size
    if hasattr(file, 'size') and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {settings.max_file_size} bytes"
        )

    try:
        # Save uploaded file
        file_path, filename = VideoService.save_upload_file(file)

        # Validate video file
        mime_type = VideoService.validate_video_file(file_path)

        # Create video record
        video = VideoService.create_video_record(
            db, file, file_path, filename, mime_type
        )

        # Create and start processing job
        job = VideoService.create_job(db, video.id, "upload")

        # Start async processing
        process_video_upload.apply_async(
            args=[video.id],
            task_id=job.id
        )

        return JobResponse(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            created_at=job.created_at
        )

    except ValueError as e:
        # Clean up file if validation fails
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Clean up file if something goes wrong
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )

@router.get("/videos", response_model=VideoList)
def list_videos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all uploaded videos"""
    videos, total = VideoService.list_videos(db, skip=skip, limit=limit)

    return VideoList(
        videos=[VideoResponse.from_orm(video) for video in videos],
        total=total,
        page=skip // limit + 1,
        limit=limit
    )

@router.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: str,
    db: Session = Depends(get_db)
):
    """Get video by ID"""
    video = VideoService.get_video_by_id(db, video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    return VideoResponse.from_orm(video)

@router.get("/videos/{video_id}/download")
def download_video(
    video_id: str,
    db: Session = Depends(get_db)
):
    """Download original video file"""
    video = VideoService.get_video_by_id(db, video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    if not os.path.exists(video.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file not found"
        )

    return FileResponse(
        video.file_path,
        media_type=video.mime_type,
        filename=video.original_filename
    )
```

### 10.2 Create app/api/endpoints/processing.py

```python
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.video_service import VideoService
from app.schemas.video import (
    TrimRequest, OverlayRequest, WatermarkRequest,
    QualityRequest, JobResponse
)
from app.tasks.celery_tasks import (
    trim_video_task, add_overlay_task,
    add_watermark_task, convert_quality_task
)
from app.config import settings

router = APIRouter()

@router.post("/trim", response_model=JobResponse)
def trim_video(
    request: TrimRequest,
    db: Session = Depends(get_db)
):
    """Trim video between start and end time"""

    # Validate video exists
    video = VideoService.get_video_by_id(db, request.video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Validate time range
    if request.start_time >= request.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be greater than start time"
        )

    if video.duration and request.end_time > video.duration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"End time cannot exceed video duration ({video.duration}s)"
        )

    # Create job
    job = VideoService.create_job(
        db, request.video_id, "trim",
        config={
            "start_time": request.start_time,
            "end_time": request.end_time
        }
    )

    # Start async processing
    trim_video_task.apply_async(
        args=[request.video_id, request.start_time, request.end_time],
        task_id=job.id
    )

    return JobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at
    )

@router.post("/overlay", response_model=JobResponse)
def add_overlay(
    request: OverlayRequest,
    db: Session = Depends(get_db)
):
    """Add overlay to video"""

    # Validate video exists
    video = VideoService.get_video_by_id(db, request.video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Validate overlay content
    if request.overlay_type == "image" or request.overlay_type == "video":
        overlay_path = os.path.join(settings.assets_dir, request.content)
        if not os.path.exists(overlay_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Overlay file not found: {request.content}"
            )

    # Create job
    overlay_config = {
        "overlay_type": request.overlay_type,
        "content": request.content,
        "position_x": request.position_x,
        "position_y": request.position_y,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "font_size": request.font_size,
        "font_color": request.font_color,
        "language": request.language
    }

    job = VideoService.create_job(
        db, request.video_id, "overlay",
        config=overlay_config
    )

    # Start async processing
    add_overlay_task.apply_async(
        args=[request.video_id, overlay_config],
        task_id=job.id
    )

    return JobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at
    )

@router.post("/watermark", response_model=JobResponse)
def add_watermark(
    request: WatermarkRequest,
    db: Session = Depends(get_db)
):
    """Add watermark to video"""

    # Validate video exists
    video = VideoService.get_video_by_id(db, request.video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Validate watermark file
    watermark_path = os.path.join(settings.assets_dir, request.watermark_path)
    if not os.path.exists(watermark_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watermark file not found: {request.watermark_path}"
        )

    # Create job
    watermark_config = {
        "watermark_path": watermark_path,
        "position": request.position,
        "opacity": request.opacity
    }

    job = VideoService.create_job(
        db, request.video_id, "watermark",
        config=watermark_config
    )

    # Start async processing
    add_watermark_task.apply_async(
        args=[request.video_id, watermark_config],
        task_id=job.id
    )

    return JobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at
    )

@router.post("/quality", response_model=JobResponse)
def convert_quality(
    request: QualityRequest,
    db: Session = Depends(get_db)
):
    """Convert video to multiple qualities"""

    # Validate video exists
    video = VideoService.get_video_by_id(db, request.video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Validate qualities
    valid_qualities = ["1080p", "720p", "480p"]
    invalid_qualities = [q for q in request.qualities if q not in valid_qualities]
    if invalid_qualities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid qualities: {invalid_qualities}. Valid options: {valid_qualities}"
        )

    # Create job
    job = VideoService.create_job(
        db, request.video_id, "quality",
        config={"qualities": request.qualities}
    )

    # Start async processing
    convert_quality_task.apply_async(
        args=[request.video_id, request.qualities],
        task_id=job.id
    )

    return JobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at
    )
```

### 10.3 Create app/api/endpoints/jobs.py

```python
import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.video_service import VideoService
from app.schemas.video import JobResponse, JobResult

router = APIRouter()

@router.get("/status/{job_id}", response_model=JobResponse)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get job status by ID"""

    job = VideoService.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return JobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at,
        error_message=job.error_message
    )

@router.get("/result/{job_id}", response_model=JobResult)
def get_job_result(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get job result by ID"""

    job = VideoService.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return JobResult(
        job_id=job.id,
        status=job.status,
        result_file_path=job.result_file_path,
        error_message=job.error_message
    )

@router.get("/download/{job_id}")
def download_result(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Download processed video result"""

    job = VideoService.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job not completed. Current status: {job.status}"
        )

    if not job.result_file_path or not os.path.exists(job.result_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result file not found"
        )

    filename = os.path.basename(job.result_file_path)
    return FileResponse(
        job.result_file_path,
        media_type="video/mp4",
        filename=filename
    )
```

## Step 11: Main Application

### 11.1 Create app/main.py

```python
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine
from app.models import video  # Import to ensure tables are created
from app.api.endpoints import upload, processing, jobs

# Create upload and processed directories
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.processed_dir, exist_ok=True)
os.makedirs(settings.assets_dir, exist_ok=True)

app = FastAPI(
    title="Video Processing API",
    description="FastAPI backend for video editing platform",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(processing.router, prefix="/api/v1", tags=["processing"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])

# Serve static files
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount("/processed", StaticFiles(directory=settings.processed_dir), name="processed")

@app.get("/")
def read_root():
    return {
        "message": "Video Processing API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Step 12: Docker and Development Setup

### 12.1 Create docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: video_processing
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./:/app
      - ./uploads:/app/uploads
      - ./processed:/app/processed
      - ./assets:/app/assets
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/video_processing
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  celery:
    build: .
    volumes:
      - ./:/app
      - ./uploads:/app/uploads
      - ./processed:/app/processed
      - ./assets:/app/assets
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/video_processing
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    command: celery -A app.tasks.celery_app worker --loglevel=info

volumes:
  postgres_data:
```

### 12.2 Create Dockerfile

```dockerfile
FROM python:3.11

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    fonts-noto \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY . .

# Install dependencies
RUN uv sync

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Step 13: README and Documentation

### 13.1 Create README.md

```markdown
# Video Processing Backend

FastAPI backend for video editing platform with upload, processing (ffmpeg), trimming, overlays, watermarking, async processing, and multiple quality outputs.

## Features

### Level 1 - Upload & Metadata
- ✅ API to upload videos
- ✅ Store metadata in PostgreSQL (filename, duration, size, upload_time)
- ✅ API to list uploaded videos

### Level 2 - Trimming API
- ✅ POST /trim endpoint with video ID + start/end timestamps
- ✅ Returns trimmed video file
- ✅ Saves trimmed video info in DB

### Level 3 - Overlays &
        db.refresh(video)

        return video

    @staticmethod
    def get_video_by_id(db: Session, video_id: str) -> Optional[Video]:
        """Get video by ID"""
        return db.query(Video).filter(Video.id == video_id).first()

    @staticmethod
    def list_videos(db: Session, skip: int = 0, limit: int = 100) -> tuple[List[Video], int]:
        """List videos with pagination"""
        total = db.query(Video).count()
        videos = db.query(Video).offset(skip).limit(limit).all()
        return videos, total

    @staticmethod
    def create_job(db: Session, video_id: str, job_type: str, config: dict = None) -> Job:
        """Create a processing job"""
        job = Job(
            video_id=video_id,
            job_type=job_type,
            config=config
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        return job

    @staticmethod
    def update_job_status(db: Session, job_id: str, status: str,
                         progress: int = None, result_file_path: str = None,
                         error_message: str = None):
        """Update job status"""
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
        """Get job by ID"""
        return db.query(Job).filter(Job.id == job_id).first()
```

## Step 8: Celery Setup

### 8.1 Create app/tasks/celery_app.py

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "video_processing",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.celery_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
```

### 8.2 Create app/tasks/celery_tasks.py

```python
import os
import uuid
from celery import current_task
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from app.tasks.celery_app import celery_app
from app.config import settings
from app.services.ffmpeg_service import FFmpegService
from app.services.video_service import VideoService
from app.models.video import Video, ProcessedVideo
import logging

logger = logging.getLogger(__name__)

# Database setup for Celery
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

@celery_app.task(bind=True)
def process_video_upload(self, video_id: str):
    """Process uploaded video to extract metadata"""
    db = get_db()
    try:
        # Update job status
        VideoService.update_job_status(db, self.request.id, "processing", 10)

        video = VideoService.get_video_by_id(db, video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        # Get video info using FFmpeg
        video_info = FFmpegService.get_video_info(video.file_path)

        # Update video record
        video.duration = video_info.get('duration')
        video.width = video_info.get('width')
        video.height = video_info.get('height')
        video.format = video_info.get('format')

        db.commit()
