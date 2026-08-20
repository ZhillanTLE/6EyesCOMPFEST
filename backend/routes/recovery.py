"""
routes/recovery.py — The Windfall recovery endpoint.

A deliberately isolated blueprint. It shares no machinery with /api/plan-trip:

  no background thread   the whole pipeline runs inside the request
  no SocketIO            the full trace is the response body
  no Firestore           the seed is read from a local JSON file
  no auth decorator      there is nothing user-owned to protect here

That isolation is the point. The penyisihan scope rules require synchronous
processing, no background jobs and no distributed database, and the surest way
to be able to say so is for the recovery path not to touch any of it. The older
planning endpoint keeps its own architecture and is out of scope.
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from backend.recovery import pipeline, providers, repository

logger = logging.getLogger(__name__)

bp = Blueprint("recovery", __name__, url_prefix="/api/recovery")


@bp.get("/queue")
def queue():
    """
    The browse list: abandoned carts awaiting a decision.

    Carries no tier and no campaign share. Those are the Classifier's output,
    and putting them on the card the analyst clicks would let the pipeline
    appear to conclude something already on screen.
    """
    return jsonify({
        "queue": repository.queue(),
        "source": "fixture" if providers.use_fixtures() else "live",
    }), 200


@bp.post("/run")
def run():
    """
    Run the full pipeline for one cart and return the entire reasoning trace.

    One request, one response, everything inside it: tier and the evidence
    behind it, the gate result and which axis decided it, every ladder attempt
    including the ones that failed, the outcome, hold eligibility, and the
    drafted notification. Nothing is streamed and nothing is deferred.
    """
    data = request.get_json(silent=True) or {}
    # camelCase is the wire contract; snake_case accepted so an older client
    # or a hand-rolled curl does not silently 400.
    traveler_id = data.get("travelerId") or data.get("traveler_id")
    if not traveler_id:
        return jsonify({"error": "Missing 'travelerId' in request body"}), 400

    try:
        result = pipeline.run(traveler_id)
    except KeyError:
        return jsonify({"error": "Unknown traveler: {}".format(traveler_id)}), 404
    except Exception as exc:  # pragma: no cover - surfaced, never swallowed
        logger.exception("[recovery] pipeline failed for %s", traveler_id)
        return jsonify({"error": "Pipeline failed: {}".format(exc)}), 500

    return jsonify(result.to_dict()), 200


@bp.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "windfall-recovery",
        "mode": "fixture" if providers.use_fixtures() else "live",
        "carts": len(repository.all_travelers()),
    }), 200
