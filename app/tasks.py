import time
import os
from .celery_app import celery_app
from .db import SessionLocal
from .models import Video


@celery_app.task(bind=True)
def process_video(self, video_id: int, filepath: str):
    """
    Simulate processing. In real life you would transcode, generate thumbnails, etc.
    """
    session = SessionLocal()
    try:
        # fetch record
        video = session.get(Video, video_id)
        if not video:
            return {"error": "video record not found"}

        video.status = "processing"
        session.commit()

        # simulate a time-consuming job (replace this with real processing)
        time.sleep(8)

        # mark done
        video.status = "done"
        session.commit()
        return {"status": "done", "video_id": video_id}
    except Exception as exc:
        session.rollback()
        # mark failed (optional)
        v = session.get(Video, video_id)
        if v:
            v.status = "failed"
            session.commit()
        raise exc
    finally:
        session.close()
