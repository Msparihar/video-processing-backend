import subprocess
import time
from typing import List, Optional, Dict, Any


def run_ffmpeg(cmd: List[str], timeout_s: Optional[int] = None, check: bool = True) -> Dict[str, Any]:
    """Run an ffmpeg/ffprobe command with optional timeout and return structured result.

    Args:
        cmd: Command list, e.g. ["ffmpeg", "-i", "in.mp4", "out.mp4"].
        timeout_s: Optional timeout in seconds; None disables timeout.
        check: If True, non-zero return codes raise CalledProcessError.

    Returns:
        Dict with keys: stdout, stderr, returncode, duration_s.
    """
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, check=False)
    duration_s = time.time() - start_time
    if check and result.returncode != 0:
        # Re-raise with stderr included for context
        raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "duration_s": duration_s,
    }


def popen_ffmpeg(cmd: List[str]) -> subprocess.Popen[str]:
    """Start ffmpeg/ffprobe in background and return the Popen object (text mode)."""
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


