import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings

from app.api.endpoints import upload, processing
from app import models


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


# app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
# app.include_router(processing.router, prefix="/api/v1", tags=["processing"])


app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount("/processed", StaticFiles(directory=settings.processed_dir), name="processed")


@app.get("/")
def read_root():
    return {"message": "Video Processing API", "version": "1.0.0", "docs": "/docs", "redoc": "/redoc"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
