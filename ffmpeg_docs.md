📘 Using subprocess with FFmpeg in FastAPI

FFmpeg is installed in WSL (/usr/bin/ffmpeg) and can be called from Python using the subprocess module. This allows us to run any FFmpeg command programmatically.

1. Import subprocess
import subprocess

2. Running a simple FFmpeg command

Example: Convert input.mp4 to output.webm.

cmd = [
    "ffmpeg",
    "-i", "input.mp4",   # input file
    "output.webm"        # output file
]

result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode != 0:
    print("❌ FFmpeg failed:", result.stderr)
else:
    print("✅ Conversion successful")

3. Using in FastAPI (blocking mode)
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import subprocess
import uuid, os

app = FastAPI()

@app.post("/convert/")
async def convert_video(file: UploadFile = File(...)):
    input_path = f"tmp/{uuid.uuid4()}_{file.filename}"
    output_path = input_path.rsplit(".", 1)[0] + ".mp4"

    # Save upload
    with open(input_path, "wb") as f:
        f.write(await file.read())

    # Run FFmpeg
    cmd = ["ffmpeg", "-i", input_path, "-c:v", "libx264", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr)

    return FileResponse(output_path, media_type="video/mp4", filename=os.path.basename(output_path))

4. Non-blocking / Background mode

If the conversion is long, don’t block the request. Use Popen or FastAPI background tasks:

process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


This starts FFmpeg and immediately returns. You can store the process.pid to manage it (stop/restart later).

5. Best Practices

Always use lists, not strings (["ffmpeg", "-i", "input.mp4", "out.mp4"] instead of "ffmpeg -i input.mp4 out.mp4") to avoid shell-injection risks.

Check returncode to know if FFmpeg succeeded.

Log stderr because FFmpeg writes all progress/errors there.

Use capture_output=True, text=True to capture logs as strings.

For long streams, prefer Popen and stream stdout in chunks.
