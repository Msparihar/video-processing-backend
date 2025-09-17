from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, JSON
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
    duration = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    format = Column(String, nullable=True)
    mime_type = Column(String, nullable=False)
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    processed_videos = relationship("ProcessedVideo", back_populates="original_video")
    jobs = relationship("Job", back_populates="video")


class ProcessedVideo(Base):
    __tablename__ = "processed_videos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    original_video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    processing_type = Column(String, nullable=False)
    processing_config = Column(JSON, nullable=True)
    quality = Column(String, nullable=True)
    duration = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    original_video = relationship("Video", back_populates="processed_videos")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    job_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    progress = Column(Integer, default=0)
    result_file_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    video = relationship("Video", back_populates="jobs")


class Overlay(Base):
    __tablename__ = "overlays"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    processed_video_id = Column(String, ForeignKey("processed_videos.id"), nullable=False)
    overlay_type = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    start_time = Column(Float, default=0.0)
    end_time = Column(Float, nullable=True)
    font_size = Column(Integer, nullable=True)
    font_color = Column(String, nullable=True)
    language = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
