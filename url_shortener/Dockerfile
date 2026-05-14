# url_shortener/Dockerfile
# Packages the FastAPI URL shortener into a portable container image.
#
# BRD NFR-2: /healthz reachable within 5 s of docker run.
# BRD NFR-3: CPython 3.11.x runtime.
# HLD ADR-004: dependency layer before application code for cache efficiency.
#
# Build:
#   docker build -t url-shortener -f url_shortener/Dockerfile url_shortener/
#
# Run:
#   docker run -p 8000:8000 url-shortener
#
# Override base URL:
#   docker run -p 8000:8000 -e BASE_URL=https://short.example.com url-shortener

FROM python:3.11-slim

# Set working directory inside the container (ADR-003: PYTHONPATH = /app)
WORKDIR /app

# --- Layer 1: install runtime dependencies (cached unless requirements.txt changes) ---
# ADR-004: copy requirements first to maximise Docker layer cache reuse.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Layer 2: copy application source (invalidated only when main.py changes) ---
COPY main.py .

# Expose the uvicorn default port (BRD §9 risk 3 assumption: port 8000)
EXPOSE 8000

# Health check so orchestrators know when the container is ready (BRD NFR-2, AC-9)
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" \
    || exit 1

# Start uvicorn in single-worker mode (BRD §7 assumption; ADR-001 thread-safety note)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
