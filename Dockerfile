FROM python:3.11

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
	ffmpeg \
	libmagic1 \
	fonts-noto \
	&& rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY . .

# Install dependencies
RUN uv sync

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
