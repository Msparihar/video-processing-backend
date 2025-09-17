import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.video_service import VideoService
from app.schemas.video import JobResponse, JobResult


router = APIRouter()


@router.get("/status/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = VideoService.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at,
        error_message=job.error_message,
    )


@router.get("/result/{job_id}", response_model=JobResult)
def get_job_result(job_id: str, db: Session = Depends(get_db)):
    job = VideoService.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResult(
        job_id=job.id,
        status=job.status,
        result_file_path=job.result_file_path,
        error_message=job.error_message,
    )


@router.get("/download/{job_id}")
def download_result(job_id: str, db: Session = Depends(get_db)):
    job = VideoService.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Job not completed. Current status: {job.status}"
        )
    if not job.result_file_path or not os.path.exists(job.result_file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result file not found")
    filename = os.path.basename(job.result_file_path)
    return FileResponse(job.result_file_path, media_type="video/mp4", filename=filename)
