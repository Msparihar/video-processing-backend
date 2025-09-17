import requests
import time
import json
import re
import os
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/v1"
FILES_DIR = "assets/assigment/Base video"
OVERLAY_DIR = "assets/assigment/Overlay assets _"
VIDEO_FILE = "A-roll.mp4"
OVERLAY_FILE = "assigment/Overlay assets _/Image Overlay.png"  # Use image overlay for test


def log_time(action: str):
    """Log timestamp for action."""
    print(f"{action} started at {time.strftime('%H:%M:%S.%f')}")


def upload_video() -> str:
    """Upload base video and return video_id."""
    log_time("Upload video")
    start_time = time.time()
    with open(f"{FILES_DIR}/{VIDEO_FILE}", "rb") as f:
        files = {"file": f}
        response = requests.post(f"{BASE_URL}/upload", files=files)
    duration = time.time() - start_time
    if response.status_code == 200:
        video_id = response.json()["id"]
        print(f"Upload completed in {duration:.2f}s, video_id: {video_id}")
        return video_id
    else:
        raise Exception(f"Upload failed: {response.text}")


def test_sync_overlay(video_id: str):
    """Test synchronous overlay."""
    log_time("Sync overlay")
    start_time = time.time()
    payload = {
        "video_id": video_id,
        "overlay_type": "image",
        "content": OVERLAY_FILE,
        "position_x": 100,
        "position_y": 100,
        "start_time": 0.0,
        "font_size": None,
        "font_color": None,
        "language": None,
    }
    response = requests.post(f"{BASE_URL}/overlay", json=payload)
    duration = time.time() - start_time
    if response.status_code == 200:
        result = response.json()
        print(f"Sync overlay completed in {duration:.2f}s, filename: {result['filename']}")
        return result
    else:
        raise Exception(f"Sync overlay failed: {response.text}")


def test_celery_overlay(video_id: str) -> str:
    """Test Celery overlay with polling and return processed_id."""
    log_time("Celery overlay queue")
    queue_start = time.time()
    payload = {
        "video_id": video_id,
        "overlay_type": "image",
        "content": OVERLAY_FILE,
        "position_x": 100,
        "position_y": 100,
        "start_time": 0.0,
        "end_time": None,
        "font_size": None,
        "font_color": None,
        "language": None,
    }
    response = requests.post(f"{BASE_URL}/celery/overlay", json=payload)
    queue_duration = time.time() - queue_start
    if response.status_code == 200:
        task_id = response.json()["task_id"]
        print(f"Celery overlay queued in {queue_duration:.2f}s, task_id: {task_id}")
    else:
        raise Exception(f"Celery queue failed: {response.text}")

    # Poll status
    poll_start = time.time()
    while True:
        status_response = requests.get(f"{BASE_URL}/celery/status/{task_id}")
        status = status_response.json()
        print(f"Status poll at {time.strftime('%H:%M:%S.%f')}: {status['state']}")
        if status["state"] in ["SUCCESS", "FAILURE"]:
            total_duration = time.time() - poll_start + queue_duration
            if status["successful"]:
                print(f"Celery overlay completed in {total_duration:.2f}s, result: {status['result']}")
                return status["result"]["processed_video_id"]
            else:
                print(f"Celery overlay failed: {status['result']}")
                raise Exception(f"Celery overlay failed: {status['result']}")
        time.sleep(2)  # Poll every 2s


def download_and_verify(url: str, save_filename: str):
    """Download file, save to disk, and verify timestamp in header."""
    log_time(f"Download to {save_filename}")
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_filename, "wb") as f:
            f.write(response.content)
        file_size = len(response.content)
        print(f"{save_filename} saved (size: {file_size} bytes)")

        content_disposition = response.headers.get("Content-Disposition", "")
        if "attachment; filename=" in content_disposition:
            header_filename = content_disposition.split("filename=")[1].strip('"')
            timestamp_match = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.\d+Z", header_filename)
            if timestamp_match:
                print(f"Header filename with timestamp: {header_filename}")
            else:
                print(f"Header filename missing timestamp: {header_filename}")
        else:
            print("No Content-Disposition header")
        return file_size > 0
    else:
        print(f"{save_filename} download failed: {response.status_code} - {response.text}")
        return False


if __name__ == "__main__":
    print("Testing overlay functionality...")
    try:
        video_id = upload_video()

        # Download original
        original_url = f"{BASE_URL}/videos/{video_id}/download"
        if not download_and_verify(original_url, "downloaded_original.mp4"):
            raise Exception("Original download failed")

        sync_result = test_sync_overlay(video_id)
        print("Sync test result:", json.dumps(sync_result, indent=2))

        # Download sync processed
        sync_processed_id = sync_result["id"]
        sync_url = f"{BASE_URL}/processed/{sync_processed_id}/download"
        if not download_and_verify(sync_url, "downloaded_sync.mp4"):
            raise Exception("Sync processed download failed")

        celery_processed_id = test_celery_overlay(video_id)

        # Download celery processed
        celery_url = f"{BASE_URL}/processed/{celery_processed_id}/download"
        if not download_and_verify(celery_url, "downloaded_celery.mp4"):
            raise Exception("Celery processed download failed")

        print("All tests completed successfully, files saved.")
    except Exception as e:
        print(f"Test failed: {e}")
