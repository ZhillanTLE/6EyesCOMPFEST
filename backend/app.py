"""
app.py — Core Agentic Engine API server.

Production stack:
  - Flask 3 + Flask-SocketIO 5 (gevent async_mode)
  - Redis message queue for multi-instance WebSocket coordination
  - Firebase JWT auth on all mutation endpoints
  - CORS restricted to ALLOWED_ORIGINS env var

Local development:
  - Set AUTH_DISABLED=true to bypass JWT checks
  - Set ALLOWED_ORIGINS=* for localhost access
  - Run with: python -m backend.app
  
Production deployment:
  - gunicorn -c backend/gunicorn.conf.py "backend.app:app"
"""
import os
import re
import uuid
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from dotenv import load_dotenv
import threading

# Monkey-patch early for gevent (must happen before any other imports)
_async_mode = os.environ.get("SOCKETIO_ASYNC_MODE", "threading")
if _async_mode == "gevent":
    from gevent import monkey
    monkey.patch_all()

# Load environment variables from .env file.
# override=False so an explicitly set variable beats the file:
#   WINDFALL_FIXTURES=0 python -m backend.app
# has to mean what it says even when backend/.env pins it to 1. With
# override=True the file silently won, which also let a developer's .env
# reconfigure the test suite during discovery.
load_dotenv(override=False)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class _DropHealthPolls(logging.Filter):
    """
    Keep the container HEALTHCHECK out of the log.

    Docker polls /api/recovery/health every 10 seconds. That poll is what makes
    `depends_on: service_healthy` work, so it must keep running -- but printing
    every one of them scrolls the pipeline's reasoning off screen during a demo.
    The check still happens; only its access-log line is dropped. A failing
    check still surfaces, because Docker reports the container unhealthy and
    the handler's own errors log normally.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/recovery/health" not in record.getMessage()


logging.getLogger("werkzeug").addFilter(_DropHealthPolls())

# The Firestore and Redis fallback notices belong to the older plan-trip app.
# The recovery pipeline touches neither -- it reads a local seed file and holds
# no state -- so on a Windfall demo they read as broken setup rather than as
# the informational lines they are. Errors from either still print.
for _legacy in ("backend.firebase_state", "backend.redis_cache"):
    logging.getLogger(_legacy).setLevel(logging.ERROR)

# ---------------------------------------------------------------------------
# Flask + CORS
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")

# Restrict CORS to explicit origins in production; default open for dev
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
if _allowed_origins != "*":
    _origins = [o.strip() for o in _allowed_origins.split(",")]
else:
    _origins = "*"
CORS(app, resources={r"/*": {"origins": _origins}})

# ---------------------------------------------------------------------------
# Flask-SocketIO with optional Redis message broker
# ---------------------------------------------------------------------------
_redis_url = os.environ.get("REDIS_URL")
_socketio_kwargs = dict(
    cors_allowed_origins=_origins,
    async_mode=_async_mode,
)
if _redis_url:
    _socketio_kwargs["message_queue"] = _redis_url
    logger.info(f"[SocketIO] Using Redis message broker: {_redis_url[:30]}...")

socketio = SocketIO(app, **_socketio_kwargs)

# ---------------------------------------------------------------------------
# Local module imports (after gevent patch)
# ---------------------------------------------------------------------------
from backend import firebase_state
from backend import gemini_agent
from backend.auth import require_auth
from backend.routes.recovery import bp as recovery_bp

# ---------------------------------------------------------------------------
# Windfall recovery pipeline
# ---------------------------------------------------------------------------
# Registered as an isolated blueprint. It runs entirely inside the request --
# no background thread, no SocketIO emit, no Firestore, no auth decorator --
# because the penyisihan scope rules require synchronous processing with local
# storage. The planning endpoints below keep their own architecture; the two
# do not share state.
app.register_blueprint(recovery_bp)


# ---------------------------------------------------------------------------
# Budget extraction helper
# ---------------------------------------------------------------------------
def extract_budget(text: str) -> float:
    """Extract a numerical budget from natural language (multi-currency)."""
    text_clean = text.replace(",", "")
    match = re.search(
        r"(?:IDR|Rp|CNY|JPY|USD|EUR|GBP|SGD|AUD|[$¥€£])\s*(\d+(?:\.\d+)?)",
        text_clean,
        re.IGNORECASE,
    )
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    match_trailing = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:dollars?|rupiah|yen|yuan|euros?)", text_clean, re.IGNORECASE
    )
    if match_trailing:
        try:
            return float(match_trailing.group(1))
        except ValueError:
            pass
    for num in re.findall(r"\b\d+(?:\.\d+)?\b", text_clean):
        try:
            val = float(num)
            if val > 50:
                return val
        except ValueError:
            pass
    return 1000.0


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "Core Agentic Engine"}), 200


@app.route("/api/plan-trip", methods=["POST"])
@require_auth
def plan_trip():
    """Initiate an AI-driven trip planning workflow for the authenticated user."""
    data = request.get_json() or {}
    user_text = data.get("user_text")
    session_id = data.get("session_id")

    if not user_text:
        return jsonify({"error": "Missing 'user_text' in request body"}), 400

    if not session_id:
        session_id = str(uuid.uuid4())

    user_id = getattr(request, "uid", "dev-user")

    # Fast local parsing for budget & currency to respond instantly (within milliseconds)
    budget = extract_budget(user_text)
    currency = "USD"
    currency_symbol = "$"
    user_text_lower = user_text.lower()
    if "rupiah" in user_text_lower or "idr" in user_text_lower or "rp" in user_text_lower:
        currency = "IDR"
        currency_symbol = "Rp"
    elif "yen" in user_text_lower or "jpy" in user_text_lower or "¥" in user_text_lower:
        currency = "JPY"
        currency_symbol = "¥"
    elif "yuan" in user_text_lower or "cny" in user_text_lower:
        currency = "CNY"
        currency_symbol = "¥"
    elif "euro" in user_text_lower or "eur" in user_text_lower or "€" in user_text_lower:
        currency = "EUR"
        currency_symbol = "€"
    elif "pound" in user_text_lower or "gbp" in user_text_lower or "£" in user_text_lower:
        currency = "GBP"
        currency_symbol = "£"

    # Initialize session with owner user_id
    firebase_state.initialize_session(session_id, budget, currency, currency_symbol, user_id=user_id)

    # Run planning workflow in background thread (handles slow LLM extraction & GDS tool calling)
    thread = threading.Thread(
        target=gemini_agent.run_agent_workflow,
        args=(user_text, session_id, socketio, budget, None),
        daemon=True,
    )
    thread.start()

    return jsonify({
        "status": "initiated",
        "session_id": session_id,
        "initial_budget": budget,
        "currency": currency,
        "currency_symbol": currency_symbol,
    }), 200


@app.route("/api/swap-item", methods=["POST"])
@require_auth
def swap_item():
    """Swap flight/hotel selection and recalculate budget (authenticated + owner-verified)."""
    data = request.get_json() or {}
    session_id = data.get("session_id")
    item_type = data.get("item_type")   # "outbound" | "inbound" | "hotel"
    option_index = data.get("option_index")
    user_id = getattr(request, "uid", "dev-user")

    if not session_id or not item_type or option_index is None:
        return jsonify({"error": "Missing parameters"}), 400

    try:
        option_index = int(option_index)
        session = firebase_state.swap_session_item(session_id, item_type, option_index, user_id=user_id)

        # Broadcast to all clients in session room
        socketio.emit(
            "item_swapped",
            {
                "item_type": item_type,
                "option_index": option_index,
                "remaining_budget": session["remaining_budget"],
            },
            room=session_id,
        )

        return jsonify({
            "status": "success",
            "session_id": session_id,
            "remaining_budget": session["remaining_budget"],
        }), 200

    except PermissionError as e:
        logger.warning(f"[Auth] Ownership violation: {e}")
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        logger.error(f"Error swapping session item: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# WebSocket Event Handlers
# ---------------------------------------------------------------------------
@socketio.on("connect")
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    emit("connection_response", {"data": "Connected to Agentic Engine"})


@socketio.on("disconnect")
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on("join_session")
def handle_join_session(data):
    session_id = data.get("session_id")
    if session_id:
        join_room(session_id)
        logger.info(f"Client {request.sid} joined room: {session_id}")
        emit("join_response", {"status": "success", "room": session_id})
    else:
        emit("error", {"message": "Missing session_id"})


@socketio.on("leave_session")
def handle_leave_session(data):
    session_id = data.get("session_id")
    if session_id:
        leave_room(session_id)
        emit("leave_response", {"status": "success", "room": session_id})


# ---------------------------------------------------------------------------
# Local dev entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting development server on port {port}")
    # NOTE: For production use gunicorn -c backend/gunicorn.conf.py "backend.app:app"
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
