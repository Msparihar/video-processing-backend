# Video Processing Backend

## Overview

This is a FastAPI-based backend for video processing using FFmpeg, with Celery for asynchronous tasks, Redis as broker/result backend, and PostgreSQL as the database. It supports video uploads, synchronous and asynchronous processing (trim, overlay, watermark, quality conversion), and includes timestamped file storage to prevent overwrites and download APIs for originals and processed videos.

## Features

- **Upload Videos**: POST /api/v1/upload - Upload videos to /uploads with timestamped UUID filenames (e.g., "2024-09-17T19-25-07Z_abc123.mp4").
- **Synchronous Processing**:
  - POST /api/v1/trim - Trim videos with start/end times, output to /processed with timestamp (e.g., "2024-09-17T19-25-07Z_trimmed_video.mp4").
  - POST /api/v1/overlay - Add text/image/video overlays at positions, with timestamped output.
  - POST /api/v1/watermark - Add watermark at position with opacity.
  - POST /api/v1/quality - Convert to specified qualities (1080p, 720p, 480p).
- **Asynchronous Processing (Celery)**:
  - POST /api/v1/celery/trim - Queue trim task.
  - POST /api/v1/celery/overlay - Queue overlay task.
  - GET /api/v1/celery/status/{task_id} - Poll task status.
- **Download APIs**:
  - GET /api/v1/videos/{video_id}/download - Download original video with attachment header.
  - GET /api/v1/processed/{processed_id}/download - Download processed video with attachment header.

## Timestamped Storage

All uploaded and processed files now include an ISO8601 timestamp prefix in filenames (e.g., "2024-09-17T19-25-07Z") to ensure uniqueness and prevent overwrites. The DB stores the timestamp in a 'timestamp' field for metadata.

## Quick Start

### Using Docker (Recommended)

```bash
# 1. Clone and setup
git clone <repository-url>
cd video-processing-backend
mkdir -p uploads processed data assets

# 2. Start all services
docker compose up -d

# 3. Run database migrations
docker compose exec web alembic upgrade head

# 4. Test the API
curl http://localhost:8000/docs
```

### Local Development

```bash
# 1. Install dependencies
uv sync

# 2. Setup PostgreSQL and Redis
docker run -d --name postgres -e POSTGRES_DB=video_processing -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:15-alpine
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Run migrations
uv run alembic upgrade head

# 5. Start services
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# In another terminal:
uv run celery -A app.celery_app worker --loglevel=info
```

## Documentation

- **API Docs**: <http://localhost:8000/docs> (Swagger UI)
- **Database Schema**: [SCHEMA.md](SCHEMA.md)
- **OpenAPI Spec**: <http://localhost:8000/openapi.json>

## Architecture

- **FastAPI**: REST API framework
- **PostgreSQL**: Primary database
- **Redis**: Message broker and result backend
- **Celery**: Asynchronous task processing
- **FFmpeg**: Video processing engine
- **Docker**: Containerization

## Configuration

Key environment variables (see `.env.example`):

- `DATABASE_URL`: PostgreSQL connection string
- `CELERY_BROKER_URL`: Redis URL for Celery broker
- `MAX_FILE_SIZE`: Maximum upload size (default: 500MB)
- `UPLOAD_DIR`: Directory for uploaded files
- `PROCESSED_DIR`: Directory for processed files
