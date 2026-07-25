import subprocess
import json
import os
import uuid
from typing import Dict, Any, Optional, List
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

            run_ffmpeg(cmd, timeout_s=300, check=True)
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error converting quality: {e}")
            raise

    @staticmethod
    def _create_single_quality_hls(input_path: str, output_dir: str, base_name: str, quality: str, settings_dict: dict) -> bool:
        """
        Create a single quality HLS variant
        """
        try:
            # Calculate appropriate dimensions based on input video aspect ratio
            input_info = FFmpegService.get_video_info(input_path)
            if not input_info:
                raise Exception("Could not get video info")

            input_width = input_info.get('width', 1920)
            input_height = input_info.get('height', 1080)

            # Calculate target dimensions maintaining aspect ratio
            target_width = settings_dict['width']
            target_height = settings_dict['height']

            # For portrait videos, adjust dimensions to maintain aspect ratio
            if input_width < input_height:  # Portrait video
                # Scale based on width, maintain aspect ratio
                scale_factor = target_width / input_width
                actual_height = int(input_height * scale_factor)
                scale_filter = f"scale={target_width}:{actual_height}"
            else:  # Landscape video
                scale_filter = f"scale={target_width}:{target_height}"

            cmd = [
                settings.ffmpeg_path,
                "-i", input_path,
                "-vf", scale_filter,
                "-c:v", "libx264",
                "-b:v", settings_dict["bitrate"],
                "-maxrate", settings_dict["bitrate"],
                "-bufsize", f"{int(settings_dict['bitrate'].replace('k', '')) * 2}k",
                "-preset", "medium",
                "-g", "48",  # GOP size
                "-sc_threshold", "0",
                "-c:a", "aac",
                "-b:a", settings_dict["audio_bitrate"],
                "-ac", "2",
                "-f", "hls",
                "-hls_time", "10",  # Segment duration
                "-hls_playlist_type", "vod",
                "-hls_segment_filename", f"{output_dir}/{base_name}_{quality}_%03d.ts",
                f"{output_dir}/{base_name}_{quality}.m3u8",
                "-y"
            ]

            run_ffmpeg(cmd, timeout_s=300, check=True)

            # Verify files were created
            playlist_path = f"{output_dir}/{base_name}_{quality}.m3u8"
            if os.path.exists(playlist_path):
                return True
            else:
                logger.error(f"HLS playlist not created: {playlist_path}")
                return False

        except Exception as e:
            logger.error(f"Error creating single quality HLS for {quality}: {e}")
            raise

    @staticmethod
    def create_hls_stream(input_path: str, output_dir: str, base_name: str, qualities: Optional[List[str]] = None) -> bool:
        """
        Create HLS stream with multiple quality variants using sequential processing
        """
        try:
            if qualities is None:
                qualities = ["480p", "720p", "1080p"]

            # Ensure qualities is a list
            if not isinstance(qualities, list):
                qualities = ["480p", "720p", "1080p"]

            quality_settings = {
                "360p": {"width": 640, "height": 360, "bitrate": "800k", "audio_bitrate": "128k"},
                "480p": {"width": 854, "height": 480, "bitrate": "1200k", "audio_bitrate": "128k"},
                "720p": {"width": 1280, "height": 720, "bitrate": "2500k", "audio_bitrate": "128k"},
                "1080p": {"width": 1920, "height": 1080, "bitrate": "5000k", "audio_bitrate": "128k"},
            }

            # Create output directory
            os.makedirs(output_dir, exist_ok=True)

            # Generate unique base name for this streaming session
            import uuid as uuid_module
            base_name = f"stream_{uuid_module.uuid4().hex[:8]}"

            # Create each quality variant sequentially
            successful_qualities = []
            for quality in qualities:
                if quality not in quality_settings:
                    logger.warning(f"Skipping unknown quality: {quality}")
                    continue

                try:
                    success = FFmpegService._create_single_quality_hls(
                        input_path, output_dir, base_name, quality, quality_settings[quality]
                    )
                    if success:
                        successful_qualities.append(quality)
                        logger.info(f"Successfully created {quality} HLS variant")
                    else:
                        logger.error(f"Failed to create {quality} HLS variant")
                except Exception as e:
                    logger.error(f"Error creating {quality} variant: {e}")
                    continue

            if not successful_qualities:
                raise Exception("Failed to create any HLS quality variants")

            # Create master playlist
            FFmpegService._create_master_playlist(output_dir, base_name, successful_qualities, quality_settings)

            logger.info(f"Successfully created HLS stream with {len(successful_qualities)} qualities")
            return True

        except Exception as e:
            logger.error(f"Error creating HLS stream: {e}")
            raise

    @staticmethod
    def _create_single_quality_hls(input_path: str, output_dir: str, base_name: str, quality: str, settings_dict: dict) -> bool:
        """
        Create a single quality HLS variant
        """
        try:
            # Calculate appropriate dimensions based on input video aspect ratio
            input_info = FFmpegService.get_video_info(input_path)
            if not input_info:
                raise Exception("Could not get video info")

            input_width = input_info.get('width', 1920)
            input_height = input_info.get('height', 1080)

            # Calculate target dimensions maintaining aspect ratio
            target_width = settings_dict['width']
            target_height = settings_dict['height']

            # For portrait videos, adjust dimensions to maintain aspect ratio
            if input_width < input_height:  # Portrait video
                # Scale based on width, maintain aspect ratio
                scale_factor = target_width / input_width
                actual_height = int(input_height * scale_factor)
                scale_filter = f"scale={target_width}:{actual_height}"
            else:  # Landscape video
                scale_filter = f"scale={target_width}:{target_height}"

            cmd = [
                settings.ffmpeg_path,
                "-i", input_path,
                "-vf", scale_filter,
                "-c:v", "libx264",
                "-b:v", settings_dict["bitrate"],
                "-maxrate", settings_dict["bitrate"],
                "-bufsize", f"{int(settings_dict['bitrate'].replace('k', '')) * 2}k",
                "-preset", "medium",
                "-g", "48",  # GOP size
                "-sc_threshold", "0",
                "-c:a", "aac",
                "-b:a", settings_dict["audio_bitrate"],
                "-ac", "2",
                "-f", "hls",
                "-hls_time", "10",  # Segment duration
                "-hls_playlist_type", "vod",
                "-hls_segment_filename", f"{output_dir}/{base_name}_{quality}_%03d.ts",
                f"{output_dir}/{base_name}_{quality}.m3u8",
                "-y"
            ]

            run_ffmpeg(cmd, timeout_s=300, check=True)

            # Verify files were created
            playlist_path = f"{output_dir}/{base_name}_{quality}.m3u8"
            if os.path.exists(playlist_path):
                return True
            else:
                logger.error(f"HLS playlist not created: {playlist_path}")
                return False

        except Exception as e:
            logger.error(f"Error creating single quality HLS for {quality}: {e}")
            raise

    @staticmethod
    def _create_master_playlist(output_dir: str, base_name: str, qualities: list, quality_settings: dict) -> None:
        """Create HLS master playlist for multi-variant streaming"""
        master_playlist_path = os.path.join(output_dir, f"{base_name}_master.m3u8")

        with open(master_playlist_path, 'w') as f:
            f.write("#EXTM3U\n")
            f.write("#EXT-X-VERSION:3\n")

            for quality in qualities:
                if quality not in quality_settings:
                    continue

                settings_dict = quality_settings[quality]
                bandwidth = int(settings_dict["bitrate"].replace("k", "000").replace("M", "000000"))

                f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},")
                f.write(f"RESOLUTION={settings_dict['width']}x{settings_dict['height']},")
                f.write(f"CODECS=\"avc1.640028,mp4a.40.2\"\n")
                f.write(f"{base_name}_{quality}.m3u8\n")

    @staticmethod
    def create_speed_variant(input_path: str, output_path: str, speed: float) -> bool:
        """
        Create a speed-adjusted variant of the video
        """
        try:
            if not (0.25 <= speed <= 4.0):
                raise ValueError("Speed must be between 0.25x and 4.0x")

            # Calculate audio pitch correction
            audio_filter = f"atempo={speed}"
            if speed != 1.0:
                # For non-unity speeds, we need to adjust pitch to maintain audio quality
                pitch_factor = 1.0 / speed
                audio_filter += f",asetrate=44100*{pitch_factor},aresample=44100"

            cmd = [
                settings.ffmpeg_path,
                "-i", input_path,
                "-filter:v", f"setpts={1/speed}*PTS",  # Adjust video speed
                "-filter:a", audio_filter,  # Adjust audio speed with pitch correction
                "-c:v", "libx264",
                "-preset", "medium",
                "-c:a", "aac",
                "-b:a", "128k",
                output_path,
                "-y"
            ]

            run_ffmpeg(cmd, timeout_s=300, check=True)
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error creating speed variant: {e}")
            raise

    @staticmethod
    def generate_thumbnail(input_path: str, output_path: str, timestamp: float = 1.0) -> bool:
        """
        Generate a thumbnail from video at specified timestamp
        """
        try:
            cmd = [
                settings.ffmpeg_path,
                "-i", input_path,
                "-ss", str(timestamp),  # Seek to timestamp
                "-vframes", "1",  # Extract one frame
                "-q:v", "2",  # Quality setting
                "-vf", "scale=320:-1",  # Scale to 320px width, maintain aspect ratio
                output_path,
                "-y"
            ]

            run_ffmpeg(cmd, timeout_s=30, check=True)
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            raise
