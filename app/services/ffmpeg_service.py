import subprocess
import json
import os
from typing import Dict, Any, Optional
from app.config import settings
import logging
from app.utils.ffmpeg_runner import run_ffmpeg


logger = logging.getLogger(__name__)


class FFmpegService:
    @staticmethod
    def _sanitize_drawtext_text(text: str) -> str:
        # Escape characters significant to ffmpeg drawtext parsing
        # Order matters: backslash first
        sanitized = text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("\n", "\\n")
        return sanitized

    @staticmethod
    def _validate_time_range(start_time: float, end_time: Optional[float]) -> None:
        if start_time < 0:
            raise ValueError("start_time must be >= 0")
        if end_time is not None:
            if end_time <= 0:
                raise ValueError("end_time must be > 0 when provided")
            if end_time <= start_time:
                raise ValueError("end_time must be greater than start_time")

    @staticmethod
    def _validate_position(position_x: int, position_y: int) -> None:
        if position_x < 0 or position_y < 0:
            raise ValueError("position_x and position_y must be >= 0")

    @staticmethod
    def get_video_info(file_path: str) -> Dict[str, Any]:
        try:
            cmd = [
                settings.ffprobe_path,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                file_path,
            ]

            result = run_ffmpeg(cmd, timeout_s=20, check=True)
            data = json.loads(result["stdout"])

            video_stream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
            if not video_stream:
                raise ValueError("No video stream found")

            return {
                "duration": float(data["format"]["duration"]),
                "size": int(data["format"]["size"]),
                "width": int(video_stream["width"]),
                "height": int(video_stream["height"]),
                "format": data["format"]["format_name"],
                "codec": video_stream["codec_name"],
            }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            raise

    @staticmethod
    def trim_video(input_path: str, output_path: str, start_time: float, end_time: float) -> bool:
        try:
            FFmpegService._validate_time_range(start_time, end_time)
            duration = end_time - start_time
            cmd = [
                settings.ffmpeg_path,
                "-i",
                input_path,
                "-ss",
                str(start_time),
                "-t",
                str(duration),
                "-c",
                "copy",
                "-avoid_negative_ts",
                "make_zero",
                output_path,
                "-y",
            ]

            run_ffmpeg(cmd, timeout_s=120, check=True)
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error trimming video: {e}")
            raise

    @staticmethod
    def add_text_overlay(
        input_path: str,
        output_path: str,
        text: str,
        position_x: int = 10,
        position_y: int = 10,
        start_time: float = 0,
        end_time: Optional[float] = None,
        font_size: int = 24,
        font_color: str = "white",
        language: str = "en",
    ) -> bool:
        try:
            FFmpegService._validate_position(position_x, position_y)
            FFmpegService._validate_time_range(start_time, end_time)
            if font_size <= 0:
                raise ValueError("font_size must be > 0")
            font_paths = {
                "en": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "hi": "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
                "ta": "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
                "te": "/usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf",
            }
            font_path = font_paths.get(language, font_paths["en"])

            safe_text = FFmpegService._sanitize_drawtext_text(text)
            drawtext = (
                f"drawtext=text='{safe_text}':x={position_x}:y={position_y}:fontsize={font_size}:"
                f"fontcolor={font_color}:fontfile={font_path}"
            )
            if start_time > 0 or end_time:
                enable_condition = f"enable='between(t,{start_time},{end_time or 'inf'})'"
                drawtext += f":{enable_condition}"

            cmd = [
                settings.ffmpeg_path,
                "-i",
                input_path,
                "-vf",
                drawtext,
                "-c:a",
                "copy",
                output_path,
                "-y",
            ]

            run_ffmpeg(cmd, timeout_s=300, check=True)
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error adding text overlay: {e}")
            raise

    @staticmethod
    def add_image_overlay(
        input_path: str,
        output_path: str,
        overlay_path: str,
        position_x: int = 10,
        position_y: int = 10,
        start_time: float = 0,
        end_time: Optional[float] = None,
    ) -> bool:
        try:
            FFmpegService._validate_position(position_x, position_y)
            FFmpegService._validate_time_range(start_time, end_time)
            overlay_filter = f"[1:v]scale=-1:-1[overlay]; [0:v][overlay]overlay={position_x}:{position_y}"
            if start_time > 0 or end_time:
                enable_condition = f"enable='between(t,{start_time},{end_time or 'inf'})'"
                overlay_filter += f":{enable_condition}"

            cmd = [
                settings.ffmpeg_path,
                "-i",
                input_path,
                "-i",
                overlay_path,
                "-filter_complex",
                overlay_filter,
                "-c:a",
                "copy",
                output_path,
                "-y",
            ]

            run_ffmpeg(cmd, timeout_s=300, check=True)
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error adding image overlay: {e}")
            raise

    @staticmethod
    def add_watermark(
        input_path: str,
        output_path: str,
        watermark_path: str,
        position: str = "bottom-right",
        opacity: float = 0.8,
    ) -> bool:
        try:
            if not (0.0 <= opacity <= 1.0):
                raise ValueError("opacity must be between 0.0 and 1.0")
            positions = {
                "top-left": "10:10",
                "top-right": "main_w-overlay_w-10:10",
                "bottom-left": "10:main_h-overlay_h-10",
                "bottom-right": "main_w-overlay_w-10:main_h-overlay_h-10",
                "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2",
            }
            pos = positions.get(position, positions["bottom-right"])
            overlay_filter = (
                f"[1:v]format=rgba,colorchannelmixer=aa={opacity}[watermark]; [0:v][watermark]overlay={pos}"
            )

            cmd = [
                settings.ffmpeg_path,
                "-i",
                input_path,
                "-i",
                watermark_path,
                "-filter_complex",
                overlay_filter,
                "-c:a",
                "copy",
                output_path,
                "-y",
            ]

            run_ffmpeg(cmd, timeout_s=300, check=True)
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error adding watermark: {e}")
            raise

    @staticmethod
    def convert_quality(input_path: str, output_path: str, quality: str) -> bool:
        try:
            quality_settings = {
                "1080p": {"width": 1920, "height": 1080, "bitrate": "5M"},
                "720p": {"width": 1280, "height": 720, "bitrate": "2.5M"},
                "480p": {"width": 854, "height": 480, "bitrate": "1M"},
            }
            settings_dict = quality_settings.get(quality)
            if not settings_dict:
                raise ValueError(f"Unsupported quality: {quality}")

            cmd = [
                settings.ffmpeg_path,
                "-i",
                input_path,
                "-vf",
                f"scale={settings_dict['width']}:{settings_dict['height']}",
                "-b:v",
                settings_dict["bitrate"],
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-c:a",
                "aac",
                output_path,
                "-y",
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error converting quality: {e}")
            raise
