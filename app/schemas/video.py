from pydantic import BaseModel, Field
from typing import Optional, List
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
    timestamp: datetime

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
    overlay_type: str = Field(..., pattern=r"^(text|image|video)$")
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
    position: str = Field(default="bottom-right", pattern=r"^(top-left|top-right|bottom-left|bottom-right|center)$")
    opacity: float = Field(default=0.8, ge=0.1, le=1.0)


class QualityRequest(BaseModel):
    video_id: str
    qualities: List[str] = Field(default=["1080p", "720p", "480p"])


class CeleryOverlayRequest(BaseModel):
    video_id: str
    overlay_type: str = Field(..., pattern=r"^(text|image|video)$")
    content: str
    position_x: int = Field(default=0, ge=0)
    position_y: int = Field(default=0, ge=0)
    start_time: float = Field(default=0.0, ge=0)
    end_time: Optional[float] = Field(None, gt=0)
    font_size: Optional[int] = Field(None, gt=0)
    font_color: Optional[str] = None
    language: Optional[str] = None


class ProcessedVideoResponse(BaseModel):
    id: str
    original_video_id: str
    filename: str
    file_path: str
    file_size: int
    processing_type: str
    quality: Optional[str] = None
    created_at: datetime
    timestamp: datetime

    class Config:
        from_attributes = True
