"""
auth.py — Firebase JWT authentication middleware for Flask.

Usage:
  @app.route('/api/plan-trip', methods=['POST'])
  @require_auth
  def plan_trip():
      uid = request.uid  # verified Firebase user ID
      ...

Development bypass:
  Set AUTH_DISABLED=true in your .env to skip token verification during
  local development without Firebase credentials.
"""
import os
import logging
import functools
from flask import request, jsonify

logger = logging.getLogger(__name__)

_firebase_auth = None

def _get_firebase_auth():
    global _firebase_auth
    if _firebase_auth is not None:
        return _firebase_auth
    try:
        import firebase_admin
        from firebase_admin import auth
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        _firebase_auth = auth
        logger.info("[Auth] Firebase auth module loaded.")
    except Exception as e:
        logger.warning(f"[Auth] Could not load Firebase auth: {e}")
    return _firebase_auth


def verify_firebase_token(id_token: str) -> dict:
    """Verify a Firebase ID token. Returns decoded claims dict on success.
    
    Raises:
        ValueError: If the token is missing or malformed.
        PermissionError: If verification fails (expired, revoked, invalid).
    """
    if not id_token:
        raise ValueError("No ID token provided.")

    auth = _get_firebase_auth()
    if auth is None:
        raise PermissionError("Firebase auth not configured on server.")

    try:
        decoded = auth.verify_id_token(id_token, check_revoked=True)
        return decoded
    except Exception as e:
        raise PermissionError(f"Token verification failed: {e}")


def require_auth(f):
    """Decorator that enforces Firebase JWT authentication on a route.
    
    Bypass conditions (any one is sufficient):
      - AUTH_DISABLED=true env var (explicit dev/test mode)
      - No GOOGLE_APPLICATION_CREDENTIALS env var (Firebase not configured)
    
    In bypass mode, request.uid is set to 'dev-user'.
    In production, reads Authorization: Bearer <token> and verifies via Firebase Admin.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_disabled = os.environ.get("AUTH_DISABLED", "false").lower() == "true"
        firebase_configured = bool(
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or
            os.environ.get("FIREBASE_CONFIG")
        )

        # Bypass auth when explicitly disabled or Firebase is not configured at all
        if auth_disabled or not firebase_configured:
            request.uid = "dev-user"
            return f(*args, **kwargs)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header."}), 401

        id_token = auth_header.split("Bearer ", 1)[1].strip()
        try:
            claims = verify_firebase_token(id_token)
            request.uid = claims["uid"]
            return f(*args, **kwargs)
        except (ValueError, PermissionError) as e:
            logger.warning(f"[Auth] Unauthorized request: {e}")
            return jsonify({"error": str(e)}), 401

    return decorated
