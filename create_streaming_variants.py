#!/usr/bin/env python3

import sys
sys.path.append('/home/manish/projects/video-processing-backend')

from app.database import SessionLocal
from app.models.video import Video, StreamingVariant
import os

def create_streaming_variants():
    db = SessionLocal()
    try:
        # Find videos that are marked as streaming ready but don't have variants
        videos = db.query(Video).filter(Video.streaming_ready == True).all()

        for video in videos:
            # Check if variants already exist
            existing_variants = db.query(StreamingVariant).filter(StreamingVariant.video_id == video.id).all()
            if existing_variants:
                print(f"Video {video.id} already has {len(existing_variants)} variants")
                continue

            # Check if streaming directory exists
            streaming_dir = f"processed/streaming/{video.id}"
            if not os.path.exists(streaming_dir):
                print(f"Streaming directory not found for video {video.id}")
                continue

            # Look for existing HLS files
            hls_files = []
            for file in os.listdir(streaming_dir):
                if file.endswith('.m3u8') and 'master' not in file:
                    quality = file.split('_')[-1].replace('.m3u8', '')
                    hls_files.append((quality, file))

            if not hls_files:
                print(f"No HLS files found for video {video.id}")
                continue

            # Create StreamingVariant records
            for quality, filename in hls_files:
                file_path = f"processed/streaming/{video.id}/{filename}"

                if not os.path.exists(file_path):
                    print(f"HLS file not found: {file_path}")
                    continue

                # Get file size
                file_size = os.path.getsize(file_path)

                # Quality settings mapping
                quality_settings = {
                    "360p": {"width": 640, "height": 360, "bitrate": "800k"},
                    "480p": {"width": 854, "height": 480, "bitrate": "1200k"},
                    "720p": {"width": 1280, "height": 720, "bitrate": "2500k"},
                    "1080p": {"width": 1920, "height": 1080, "bitrate": "5000k"},
                }

                settings = quality_settings.get(quality, {"width": 854, "height": 480, "bitrate": "1200k"})

                variant = StreamingVariant(
                    video_id=video.id,
                    quality=quality,
                    speed=1.0,
                    file_path=file_path,
                    file_size=file_size,
                    variant_type="hls",
                    width=settings["width"],
                    height=settings["height"],
                    bitrate=settings["bitrate"]
                )

                db.add(variant)
                print(f"Created StreamingVariant for video {video.id}, quality {quality}")

        db.commit()
        print("StreamingVariant creation completed")

    except Exception as e:
        print(f"Error creating streaming variants: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_streaming_variants()