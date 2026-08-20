# Windfall backend — Flask, synchronous recovery pipeline.
FROM python:3.12-slim

# Never write .pyc, never buffer stdout: logs must appear in `docker compose up`
# as they happen rather than when a buffer happens to flush.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Dependencies first, so editing source does not reinstall the world.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend

# The recovery pipeline is entirely synchronous and holds no state, so the
# threading async mode is sufficient and avoids the gevent monkey-patch. The
# gevent worker in gunicorn.conf.py exists for the older SocketIO planning
# endpoint and is not needed to serve /api/recovery.
ENV SOCKETIO_ASYNC_MODE=threading \
    PORT=8000 \
    AUTH_DISABLED=true

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/recovery/health', timeout=4).status==200 else 1)"

CMD ["python", "-m", "backend.app"]
