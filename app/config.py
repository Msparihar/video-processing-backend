from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/video_processing"

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
    allowed_video_types: list = [
        "video/mp4",
        "video/avi",
        "video/mov",
        "video/wmv",
        "video/x-matroska",  # mkv
        "video/webm",
    ]

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()
