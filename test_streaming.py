#!/usr/bin/env python3
"""
Test script for video streaming functionality
"""
import requests
import time
import json
import os
from typing import Optional

BASE_URL = "http://localhost:8000/api/v1"
TEST_VIDEO_PATH = "assets/assigment/Base video/A-roll.mp4"  # Update this path as needed


def log_time(action: str):
    """Log timestamp for action."""
    print(f"{action} started at {time.strftime('%H:%M:%S.%f')}")


def upload_test_video() -> Optional[str]:
    """Upload a test video and return video_id."""
    if not os.path.exists(TEST_VIDEO_PATH):
        print(f"Test video not found at {TEST_VIDEO_PATH}")
        print("Please update TEST_VIDEO_PATH in the script")
        return None

    log_time("Upload test video")
    start_time = time.time()

    with open(TEST_VIDEO_PATH, "rb") as f:
        files = {"file": f}
        response = requests.post(f"{BASE_URL}/upload", files=files)

    duration = time.time() - start_time
    if response.status_code == 200:
        video_data = response.json()
        video_id = video_data["id"]
        print(".2f")
        return video_id
    else:
        print(f"Upload failed: {response.text}")
        return None


def prepare_streaming(video_id: str):
    """Prepare video for streaming."""
    log_time("Prepare streaming")
    start_time = time.time()

    payload = {
        "qualities": ["360p", "480p", "720p", "1080p"]
    }

    response = requests.post(
        f"{BASE_URL}/videos/{video_id}/prepare-streaming",
        json=payload
    )

    duration = time.time() - start_time
    if response.status_code == 200:
        result = response.json()
        print(".2f")
        return True
    else:
        print(f"Streaming preparation failed: {response.text}")
        return False


def check_streaming_status(video_id: str):
    """Check streaming preparation status."""
    log_time("Check streaming status")

    response = requests.get(f"{BASE_URL}/videos/{video_id}/streaming-info")

    if response.status_code == 200:
        streaming_info = response.json()
        print("Streaming Info:")
        print(json.dumps(streaming_info, indent=2))
        return streaming_info
    else:
        print(f"Failed to get streaming info: {response.text}")
        return None


def test_master_playlist(video_id: str):
    """Test accessing master playlist."""
    log_time("Test master playlist")

    response = requests.get(f"{BASE_URL}/videos/{video_id}/master.m3u8")

    if response.status_code == 200:
        print("Master playlist content:")
        print(response.text[:500] + "..." if len(response.text) > 500 else response.text)
        return True
    else:
        print(f"Failed to get master playlist: {response.text}")
        return False


def create_speed_variant(video_id: str, speed: float = 1.5):
    """Create a speed variant."""
    log_time(f"Create {speed}x speed variant")

    payload = {
        "speed": speed,
        "quality": "720p"
    }

    response = requests.post(
        f"{BASE_URL}/videos/{video_id}/speed-variant",
        json=payload
    )

    if response.status_code == 200:
        result = response.json()
        print(f"Speed variant created: {result}")
        return result
    else:
        print(f"Failed to create speed variant: {response.text}")
        return None


def test_player_page():
    """Test the player page."""
    log_time("Test player page")

    response = requests.get("http://localhost:8000/player")

    if response.status_code == 200:
        print("Player page loaded successfully")
        print(f"Page size: {len(response.content)} bytes")
        return True
    else:
        print(f"Failed to load player page: {response.text}")
        return False


def main():
    """Main test function."""
    print("=== Video Streaming Test ===")
    print()

    # Test player page first
    print("1. Testing player page...")
    if not test_player_page():
        print("Player page test failed!")
        return

    print()

    # Upload test video
    print("2. Uploading test video...")
    video_id = upload_test_video()
    if not video_id:
        print("Video upload failed!")
        return

    print()

    # Prepare for streaming
    print("3. Preparing video for streaming...")
    if not prepare_streaming(video_id):
        print("Streaming preparation failed!")
        return

    print("Waiting for streaming preparation to complete...")
    time.sleep(10)  # Wait a bit for processing

    print()

    # Check streaming status
    print("4. Checking streaming status...")
    streaming_info = check_streaming_status(video_id)
    if not streaming_info:
        print("Failed to get streaming info!")
        return

    print()

    # Test master playlist
    print("5. Testing master playlist access...")
    if not test_master_playlist(video_id):
        print("Master playlist test failed!")
        return

    print()

    # Create speed variant
    print("6. Creating speed variant...")
    speed_result = create_speed_variant(video_id, 1.25)
    if not speed_result:
        print("Speed variant creation failed!")
        return

    print()

    print("=== All tests completed successfully! ===")
    print(f"Video ID: {video_id}")
    print("You can now:")
    print("1. Open http://localhost:8000/player in your browser")
    print(f"2. Enter video ID: {video_id}")
    print("3. Click 'Load Video' to test streaming")
    print("4. Try different qualities and speeds")


if __name__ == "__main__":
    main()