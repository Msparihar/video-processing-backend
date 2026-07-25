#!/usr/bin/env python3

import sys
sys.path.append('/home/manish/projects/video-processing-backend')

from app.database import SessionLocal
from app.models.video import Video

def test_db():
    db = SessionLocal()
    try:
        # Test basic query
        videos = db.query(Video).all()
        print(f"Found {len(videos)} videos")
        for video in videos:
            print(f"Video: {video.id} - {video.original_filename}")
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    test_db()