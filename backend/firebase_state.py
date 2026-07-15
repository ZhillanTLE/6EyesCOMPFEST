"""
firebase_state.py — Session persistence layer.

Priority:
  1. Google Cloud Firestore (with atomic transactions on swap operations)
  2. Thread-safe in-memory dict fallback (safe for single-process; no disk writes)

The disk-based sessions_db.json fallback has been intentionally removed to
prevent file-lock conflicts when multiple concurrent requests hit the server.
"""
import os
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Firestore initialisation
# ---------------------------------------------------------------------------
use_firebase = False
db = None

try:
    import firebase_admin
    from firebase_admin import credentials, firestore

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    firebase_config = os.environ.get("FIREBASE_CONFIG")

    if creds_path or firebase_config:
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        db = firestore.client()
        use_firebase = True
        logger.info("[Firestore] Firebase Admin initialized successfully.")
    else:
        logger.warning("[Firestore] No credentials found — using in-memory fallback.")
except ImportError:
    logger.warning("[Firestore] firebase_admin not installed — using in-memory fallback.")
except Exception as e:
    logger.warning(f"[Firestore] Initialization failed ({e}) — using in-memory fallback.")

# ---------------------------------------------------------------------------
# Thread-safe in-memory store (used when Firestore is unavailable)
# ---------------------------------------------------------------------------
_sessions_lock = threading.Lock()
_local_sessions: dict = {}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _default_session(session_id: str, total_budget: float, currency: str, currency_symbol: str, user_id: str = "") -> dict:
    return {
        "session_id": session_id,
        "user_id": user_id,
        "total_budget": total_budget,
        "remaining_budget": total_budget,
        "currency": currency,
        "currency_symbol": currency_symbol,
        "outbound_options": [],
        "inbound_options": [],
        "hotel_options": [],
        "selected_outbound_idx": 0,
        "selected_inbound_idx": 0,
        "selected_hotel_idx": 0,
        "itinerary": [],
    }

def recalculate_budget(session: dict):
    """Recalculate remaining_budget in-place based on selected indices and itinerary."""
    total = session.get("total_budget", 0.0)
    costs = 0.0
    for key_opts, key_idx in [
        ("outbound_options", "selected_outbound_idx"),
        ("inbound_options", "selected_inbound_idx"),
        ("hotel_options", "selected_hotel_idx"),
    ]:
        opts = session.get(key_opts, [])
        idx = session.get(key_idx, 0)
        if idx < len(opts):
            costs += opts[idx].get("cost", 0.0)
            
    # Include daily estimated costs from the itinerary
    itinerary = session.get("itinerary", [])
    for day in itinerary:
        costs += day.get("estimated_cost", 0.0)
        
    session["remaining_budget"] = total - costs

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def initialize_session(
    session_id: str,
    total_budget: float,
    currency: str = "USD",
    currency_symbol: str = "$",
    user_id: str = "",
) -> dict:
    """Create a new session document. Idempotent — safe to call multiple times."""
    data = _default_session(session_id, total_budget, currency, currency_symbol, user_id)

    if use_firebase:
        try:
            db.collection("sessions").document(session_id).set(data)
            logger.info(f"[Firestore] Initialized session {session_id}")
            return data
        except Exception as e:
            logger.error(f"[Firestore] initialize_session error: {e} — writing to memory.")

    with _sessions_lock:
        _local_sessions[session_id] = data
    logger.info(f"[Memory] Initialized session {session_id}")
    return data


def get_session(session_id: str) -> dict:
    """Read session state. Returns a blank session if not found."""
    if use_firebase:
        try:
            doc = db.collection("sessions").document(session_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            logger.error(f"[Firestore] get_session error: {e} — checking memory.")

    with _sessions_lock:
        if session_id in _local_sessions:
            return dict(_local_sessions[session_id])  # return a copy

    logger.warning(f"Session {session_id} not found — creating blank.")
    return initialize_session(session_id, 1000.0)


def assert_session_owner(session_id: str, user_id: str):
    """Raise PermissionError if user_id does not own session_id.
    
    Skipped when AUTH_DISABLED=true (local dev without Firebase credentials).
    """
    if os.environ.get("AUTH_DISABLED", "false").lower() == "true":
        return
    if user_id == "system":
        return
    session = get_session(session_id)
    owner = session.get("user_id", "")
    if not owner:
        return
    if not user_id:
        raise PermissionError("Missing user identity.")
    if owner != user_id:
        raise PermissionError(f"User {user_id} does not own session {session_id}.")


def update_session_options(
    session_id: str,
    outbound_options: Optional[list] = None,
    inbound_options: Optional[list] = None,
    hotel_options: Optional[list] = None,
    itinerary: Optional[list] = None,
) -> dict:
    """Merge new option lists into the session and persist."""
    session = get_session(session_id)

    if outbound_options is not None:
        session["outbound_options"] = outbound_options
    if inbound_options is not None:
        session["inbound_options"] = inbound_options
    if hotel_options is not None:
        session["hotel_options"] = hotel_options
    if itinerary is not None:
        session["itinerary"] = itinerary

    recalculate_budget(session)
    _persist(session_id, session)
    return session


def swap_session_item(session_id: str, item_type: str, option_index: int, user_id: str = "") -> dict:
    """Atomically swap a flight/hotel selection and update remaining_budget.
    
    Uses a Firestore transaction when Firebase is active to prevent concurrent
    modifications from producing stale budget calculations.
    """
    assert_session_owner(session_id, user_id)

    if use_firebase:
        try:
            return _firestore_atomic_swap(session_id, item_type, option_index)
        except PermissionError:
            raise
        except Exception as e:
            logger.error(f"[Firestore] Atomic swap failed: {e} — falling back to memory swap.")

    # Memory fallback (single-process safe via lock)
    with _sessions_lock:
        session = _local_sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found.")
        _apply_swap(session, item_type, option_index)
        recalculate_budget(session)
        _local_sessions[session_id] = session
        return dict(session)


def _apply_swap(session: dict, item_type: str, option_index: int):
    key_map = {
        "outbound": "selected_outbound_idx",
        "inbound": "selected_inbound_idx",
        "hotel": "selected_hotel_idx",
    }
    key = key_map.get(item_type)
    if key:
        session[key] = option_index


def _firestore_atomic_swap(session_id: str, item_type: str, option_index: int) -> dict:
    """Execute swap inside a Firestore transaction for ACID guarantees."""
    doc_ref = db.collection("sessions").document(session_id)

    @firestore.transactional
    def _txn(transaction):
        snapshot = doc_ref.get(transaction=transaction)
        if not snapshot.exists:
            raise ValueError(f"Session {session_id} not found in Firestore.")
        session = snapshot.to_dict()
        _apply_swap(session, item_type, option_index)
        recalculate_budget(session)
        transaction.set(doc_ref, session)
        return session

    transaction = db.transaction()
    return _txn(transaction)


def _persist(session_id: str, session: dict):
    """Write session to Firestore or in-memory store."""
    if use_firebase:
        try:
            db.collection("sessions").document(session_id).set(session)
            return
        except Exception as e:
            logger.error(f"[Firestore] persist error: {e} — writing to memory.")

    with _sessions_lock:
        _local_sessions[session_id] = session
