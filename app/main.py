import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.utils.ffmpeg_runner import run_ffmpeg

from app.api.endpoints import upload, processing
from app.database import engine, Base


os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.processed_dir, exist_ok=True)
os.makedirs(settings.assets_dir, exist_ok=True)


app = FastAPI(title="Video Processing API", description="FastAPI backend for video editing platform", version="1.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(processing.router, prefix="/api/v1", tags=["processing"])


app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount("/processed", StaticFiles(directory=settings.processed_dir), name="processed")


@app.get("/")
def read_root():
    return {"message": "Video Processing API", "version": "1.0.1", "docs": "/docs", "redoc": "/redoc"}


@app.get("/health")
def health_check():
    try:
        ffmpeg_info = run_ffmpeg([settings.ffmpeg_path, "-version"], timeout_s=5, check=True)
        ffprobe_info = run_ffmpeg([settings.ffprobe_path, "-version"], timeout_s=5, check=True)
        return {
            "status": "healthy",
            "ffmpeg": ffmpeg_info["stdout"].splitlines()[0] if ffmpeg_info["stdout"] else "ok",
            "ffprobe": ffprobe_info["stdout"].splitlines()[0] if ffprobe_info["stdout"] else "ok",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"status": "unhealthy", "error": str(exc)})


@app.on_event("startup")
def on_startup() -> None:
    # Auto-create tables if they don't exist
    Base.metadata.create_all(bind=engine)
