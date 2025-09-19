# Database Schema Documentation

## Overview

This document describes the database schema for the Video Processing Backend application. The system uses PostgreSQL as the primary database with SQLAlchemy ORM for data modeling and Alembic for migrations.

## Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│    Video    │──────▷│ ProcessedVideo  │       │     Job     │
│             │       │                 │       │             │
│ - id (PK)   │       │ - id (PK)       │       │ - id (PK)   │
│ - filename  │       │ - original_     │       │ - video_id  │
│ - file_path │       │   video_id (FK) │       │   (FK)      │
│ - file_size │       │ - filename      │       │ - job_type  │
│ - duration  │       │ - file_path     │       │ - status    │
│ - width     │       │ - processing_   │       │ - progress  │
│ - height    │       │   type          │       │ - config    │
│ - format    │       │ - quality       │       └─────────────┘
│ - mime_type │       │ - duration      │              │
│ - upload_   │       │ - width         │              │
│   time      │       │ - height        │              │
│ - timestamp │       │ - created_at    │              │
└─────────────┘       │ - timestamp     │              │
       │              └─────────────────┘              │
       │                       │                       │
       └───────────────────────┼───────────────────────┘
                               │
                    ┌─────────────────┐
                    │    Overlay      │
                    │                 │
                    │ - id (PK)       │
                    │ - processed_    │
                    │   video_id (FK) │
                    │ - overlay_type  │
                    │ - content       │
                    │ - position_x    │
                    │ - position_y    │
                    │ - start_time    │
                    │ - end_time      │
                    │ - font_size     │
                    │ - font_color    │
                    │ - language      │
                    │ - created_at    │
                    └─────────────────┘
```

## Table Definitions

### 1. videos

Stores information about uploaded video files.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | VARCHAR(36) | PRIMARY KEY | UUID string identifier |
| `filename` | VARCHAR | NOT NULL | Timestamped filename (e.g., "2024-09-17T19-25-07Z_abc123.mp4") |
| `original_filename` | VARCHAR | NOT NULL | Original uploaded filename |
| `file_path` | VARCHAR | NOT NULL | Full path to the uploaded file |
| `file_size` | INTEGER | NOT NULL | File size in bytes |
| `duration` | FLOAT | NULLABLE | Video duration in seconds |
| `width` | INTEGER | NULLABLE | Video width in pixels |
| `height` | INTEGER | NULLABLE | Video height in pixels |
| `format` | VARCHAR | NULLABLE | Video format (e.g., "mp4", "avi") |
| `mime_type` | VARCHAR | NOT NULL | MIME type (e.g., "video/mp4") |
| `upload_time` | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | When the video was uploaded |
| `timestamp` | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | Additional timestamp field |

**Indexes:**

- Primary key on `id`
- Index on `upload_time` for chronological queries
- Index on `filename` for filename-based lookups

**Relationships:**

- One-to-many with `processed_videos`
- One-to-many with `jobs`

### 2. processed_videos

Stores information about processed video files (trimmed, overlaid, watermarked, etc.).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | VARCHAR(36) | PRIMARY KEY | UUID string identifier |
| `original_video_id` | VARCHAR(36) | FOREIGN KEY → videos.id, NOT NULL | Reference to original video |
| `filename` | VARCHAR | NOT NULL | Timestamped processed filename |
| `file_path` | VARCHAR | NOT NULL | Full path to the processed file |
| `file_size` | INTEGER | NOT NULL | File size in bytes |
| `processing_type` | VARCHAR | NOT NULL | Type of processing ("trim", "overlay", "watermark", "quality") |
| `processing_config` | JSON | NULLABLE | Configuration used for processing |
| `quality` | VARCHAR | NULLABLE | Output quality ("1080p", "720p", "480p") |
| `duration` | FLOAT | NULLABLE | Processed video duration in seconds |
| `width` | INTEGER | NULLABLE | Processed video width in pixels |
| `height` | INTEGER | NULLABLE | Processed video height in pixels |
| `created_at` | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | When processing was completed |
| `timestamp` | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | Additional timestamp field |

**Indexes:**

- Primary key on `id`
- Foreign key index on `original_video_id`
- Index on `processing_type` for filtering by operation type
- Index on `created_at` for chronological queries

**Relationships:**

- Many-to-one with `videos`
- One-to-many with `overlays`

### 3. jobs

Stores information about asynchronous processing jobs (Celery tasks).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | VARCHAR(36) | PRIMARY KEY | UUID string identifier (matches Celery task ID) |
| `video_id` | VARCHAR(36) | FOREIGN KEY → videos.id, NOT NULL | Reference to source video |
| `job_type` | VARCHAR | NOT NULL | Type of job ("trim", "overlay", "watermark", "quality") |
| `status` | VARCHAR | NOT NULL, DEFAULT 'pending' | Job status ("pending", "processing", "completed", "failed") |
| `progress` | INTEGER | DEFAULT 0 | Progress percentage (0-100) |
| `result_file_path` | VARCHAR | NULLABLE | Path to result file when completed |
| `error_message` | TEXT | NULLABLE | Error message if job failed |
| `config` | JSON | NULLABLE | Job configuration parameters |
| `created_at` | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | When job was created |
| `updated_at` | TIMESTAMP WITH TIME ZONE | ON UPDATE NOW() | When job was last updated |

**Indexes:**

- Primary key on `id`
- Foreign key index on `video_id`
- Index on `status` for filtering by job status
- Index on `job_type` for filtering by operation type
- Index on `created_at` for chronological queries

**Relationships:**

- Many-to-one with `videos`

### 4. overlays

Stores information about overlay elements applied to processed videos.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | VARCHAR(36) | PRIMARY KEY | UUID string identifier |
| `processed_video_id` | VARCHAR(36) | FOREIGN KEY → processed_videos.id, NOT NULL | Reference to processed video |
| `overlay_type` | VARCHAR | NOT NULL | Type of overlay ("text", "image", "video") |
| `content` | TEXT | NULLABLE | Overlay content (text or file path) |
| `position_x` | INTEGER | DEFAULT 0 | X position in pixels |
| `position_y` | INTEGER | DEFAULT 0 | Y position in pixels |
| `start_time` | FLOAT | DEFAULT 0.0 | Start time in seconds |
| `end_time` | FLOAT | NULLABLE | End time in seconds (NULL for entire duration) |
| `font_size` | INTEGER | NULLABLE | Font size for text overlays |
| `font_color` | VARCHAR | NULLABLE | Font color for text overlays |
| `language` | VARCHAR | NULLABLE | Language code for text overlays |
| `created_at` | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | When overlay was created |

**Indexes:**

- Primary key on `id`
- Foreign key index on `processed_video_id`
- Index on `overlay_type` for filtering by overlay type

**Relationships:**

- Many-to-one with `processed_videos`

## Data Types and Constraints

### UUID Generation

All primary keys use UUID v4 strings generated by Python's `uuid.uuid4()` function, converted to string format.

### Timestamps

All timestamp fields use `TIMESTAMP WITH TIME ZONE` to ensure proper timezone handling across different deployment environments.

### JSON Fields

Configuration and metadata are stored as JSON for flexibility:

- `processing_config`: Stores parameters like trim times, overlay positions, quality settings
- `config`: Stores job-specific parameters for Celery tasks

### File Paths

All file paths are stored as relative paths from the application root:

- Upload files: `uploads/2024-09-17T19-25-07Z_abc123.mp4`
- Processed files: `processed/2024-09-17T19-25-07Z_trimmed_video.mp4`

## Migration Strategy

### Initial Migration

The initial migration creates all tables with proper indexes and foreign key constraints.

### Timestamped Filenames

A migration was added to ensure all existing files have timestamped filenames for uniqueness and prevent overwrites.

### Future Migrations

Use Alembic for all schema changes:

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head
```

## Performance Considerations

### Indexes

- All foreign keys have indexes for efficient joins
- Timestamp fields are indexed for chronological queries
- Status and type fields are indexed for filtering operations

### JSON Queries

PostgreSQL's JSON operators can be used for efficient querying of configuration fields:

```sql
-- Find all trim jobs with start time > 10 seconds
SELECT * FROM jobs
WHERE job_type = 'trim'
AND config->>'start_time'::float > 10;
```

### File Storage

- Files are stored on disk with database references
- Consider implementing file cleanup jobs for orphaned files
- Monitor disk usage for large video files

## Security Considerations

### Data Validation

- All file uploads are validated for type and size
- File paths are sanitized to prevent directory traversal
- JSON configurations are validated against schemas

### File Access

- Direct file access is controlled through API endpoints
- Download endpoints include proper attachment headers
- File permissions should be set appropriately on the filesystem

## Backup and Recovery

### Database Backup

Regular PostgreSQL backups should include:

- Schema and data dumps
- Point-in-time recovery setup
- Automated backup verification

### File Backup

- Synchronize upload and processed directories
- Consider cloud storage integration for large files
- Implement retention policies for old processed files

## Monitoring and Maintenance

### Database Monitoring

- Monitor table sizes and growth rates
- Track query performance and slow queries
- Set up alerts for failed migrations

### File System Monitoring

- Monitor disk usage in upload/processed directories
- Track file creation and deletion rates
- Implement cleanup jobs for temporary files

### Job Monitoring

- Monitor Celery job success/failure rates
- Track job processing times
- Set up alerts for stuck or failed jobs
