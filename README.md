# Video Processing Backend

## Overview
This is a FastAPI-based backend for video processing using FFmpeg, with Celery for asynchronous tasks, RabbitMQ as broker, and Redis as result backend. It supports video uploads, synchronous and asynchronous processing (trim, overlay, watermark, quality conversion), and now includes timestamped file storage to prevent overwrites and download APIs for originals and processed videos.

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

## Setup
1. Install dependencies: `uv sync`
2. Run DB: `uv run create_tables.py` (or use the manual script for migrations).
3. Start services: `docker-compose up -d`
4. Test: `uv run test_overlay.py`

## API Usage
Use tools like curl or Postman. For downloads, the response will force browser download.

## Notes
- Database: SQLite (ddialog.db), shared via Docker volumes.
- Assets: Overlays in /assets/assigment/Overlay assets _/.
- Errors: Check worker logs for Celery issues.
