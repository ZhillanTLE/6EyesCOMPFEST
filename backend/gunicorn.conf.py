"""
gunicorn.conf.py — Gunicorn production configuration.

Run with:
  gunicorn -c backend/gunicorn.conf.py "backend.app:app"

Uses gevent-websocket worker to handle Socket.IO connections at scale.
Set GUNICORN_WORKERS env var to override worker count (default: 1 for gevent).
"""
import os

# Gevent WebSocket worker handles both HTTP and WebSocket connections
worker_class = "geventwebsocket.gunicorn.workers.GeventWebSocketWorker"

# One gevent worker handles thousands of concurrent connections via greenlets
workers = int(os.environ.get("GUNICORN_WORKERS", "1"))

# Greenlet concurrency per worker
worker_connections = int(os.environ.get("GUNICORN_CONNECTIONS", "1000"))

# Bind address
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Timeouts
timeout = 120          # seconds before worker is killed (long for LLM queries)
keepalive = 5

# Logging
accesslog = "-"        # stdout
errorlog = "-"         # stdout
loglevel = os.environ.get("LOG_LEVEL", "info")

# Preload to share memory between workers (improves startup time)
preload_app = False    # Keep False with gevent to avoid forking issues
