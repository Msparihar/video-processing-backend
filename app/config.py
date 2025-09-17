from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str

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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
