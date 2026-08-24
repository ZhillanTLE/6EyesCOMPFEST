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

from backend.recovery import llm, pipeline, providers, repository, sender

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
        # `source` is about PRICES. Reasoning is a separate axis, reported
        # alongside it so the console can say which half is replayed rather
        # than labelling a run with live agents "Replaying capture".
        "source": "fixture" if providers.use_fixtures() else "live",
        "inference": "gemini" if llm.available() else llm.why_unavailable(),
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
    except llm.LiveInferenceUnavailable as exc:
        # 503, not 500: the service is correctly refusing to run rather than
        # failing unexpectedly, and the message says exactly how to fix it.
        logger.error("[recovery] %s", exc)
        return jsonify({"error": str(exc), "reason": "live_inference_unconfigured"}), 503
    except KeyError:
        return jsonify({"error": "Unknown traveler: {}".format(traveler_id)}), 404
    except Exception as exc:  # pragma: no cover - surfaced, never swallowed
        logger.exception("[recovery] pipeline failed for %s", traveler_id)
        return jsonify({"error": "Pipeline failed: {}".format(exc)}), 500

    return jsonify(result.to_dict()), 200


@bp.post("/send")
def send():
    """
    Deliver the approved notification. Reachable ONLY from an explicit approval
    action -- never from the pipeline run.

    That separation is the point: an analyst clicking through six travelers to
    read their reasoning must not put six emails in anyone's inbox. Running the
    pipeline drafts; a second, deliberate click delivers.

    Delivery is synchronous inside this request. No queue, no worker, no
    scheduler, so it stays inside the backend scope rule -- the approval click
    is a confirmation on a side-effecting action, not a second input that
    triggers the AI.

    Every send routes to DEMO_RECIPIENT. Seeded travelers are synthetic and
    their addresses are invented; delivering to them would bounce.
    """
    data = request.get_json(silent=True) or {}
    traveler_id = data.get("travelerId") or data.get("traveler_id")
    if not traveler_id:
        return jsonify({"error": "Missing 'travelerId' in request body"}), 400

    try:
        result = pipeline.run(traveler_id)
    except llm.LiveInferenceUnavailable as exc:
        logger.error("[recovery] %s", exc)
        return jsonify({"error": str(exc), "reason": "live_inference_unconfigured"}), 503
    except KeyError:
        return jsonify({"error": "Unknown traveler: {}".format(traveler_id)}), 404

    if result.notification is None:
        return jsonify({
            "error": "Nothing to send: the pipeline produced no notification.",
            "outcome": result.decision.outcome,
        }), 409

    receipt = sender.send_email(
        result.notification, result.traveler_name, result.cart_id)
    status = 200 if receipt.state != sender.SendState.FAILED else 502
    return jsonify({
        "state": receipt.state,
        "channel": receipt.channel,
        "recipient": receipt.recipient,
        "subject": receipt.subject,
        "detail": receipt.detail,
        "travelerName": result.traveler_name,
        "outcome": result.decision.outcome,
        # WhatsApp is preview-only for penyisihan: the Business API needs
        # verified business status and pre-approved templates.
        "whatsapp": {"state": "preview_only",
                     "detail": "WhatsApp Business API is out of scope for this stage."},
    }), status


@bp.get("/health")
def health():
    # The container healthcheck only needs 200/!200, but a human curling this
    # should be able to see that a live deployment has no key before clicking
    # a cart and getting a 503.
    configured = not (llm.live_mode() and not llm.has_key())
    return jsonify({
        "status": "healthy",
        "service": "windfall-recovery",
        "mode": "fixture" if providers.use_fixtures() else "live",
        "inference": llm.why_unavailable(),
        "inferenceConfigured": configured,
        "carts": len(repository.all_travelers()),
    }), 200
