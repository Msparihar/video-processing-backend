#!/usr/bin/env python3

import sys
sys.path.append('/home/manish/projects/video-processing-backend')

from app.database import SessionLocal
from app.models.video import Video

def update_video_streaming():
    db = SessionLocal()
    try:
        video_id = "d2e2ebff-6d97-4baf-8c37-d83dfc286701"
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.streaming_ready = True
            video.streaming_path = "processed/streaming/d2e2ebff-6d97-4baf-8c37-d83dfc286701/master.m3u8"
            video.streaming_qualities = ["480p"]
            db.commit()
            print(f"Updated video {video_id} for streaming")
        else:
            print(f"Video {video_id} not found")
    except Exception as e:
        print(f"Error updating video: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_video_streaming()