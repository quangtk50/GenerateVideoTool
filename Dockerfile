FROM python:3.12-slim

# FFmpeg (có libass cho phụ đề), font hỗ trợ tiếng Việt, múi giờ
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.py ./

ENV HOST=0.0.0.0 \
    PORT=8000 \
    DATA_ROOT=/data \
    ASSETS_DIR=/assets \
    SUB_FONT="DejaVu Sans" \
    PYTHONUNBUFFERED=1

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz')" || exit 1
CMD ["python", "run.py"]
