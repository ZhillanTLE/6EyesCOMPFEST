"""
llm.py — One Gemini call, three ways to not make it.

Every agent in this package goes through `complete_json`. It returns parsed
JSON or None, and None is always survivable: each caller has a deterministic
fallback, so a missing key, an exhausted quota or a malformed response degrades
the demo's prose rather than breaking the pipeline.

The three ways a call does not happen, all deliberate:

  MOCK_LLM=true          plumbing work that does not need inference
  WINDFALL_FIXTURES=1    replaying a captured run; fixtures replace inference
  no GEMINI_API_KEY      a clean clone still produces a working demo

Prompts are module-level constants and the temperature is zero. The penyisihan
rules require static parameters at demonstration time, so nothing here tunes,
samples, or adapts between calls.

The call is synchronous and happens inside the request that triggered it. No
retry queue: one retry on a transport error, then the fallback.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

MODEL = "gemini-flash-latest"
TEMPERATURE = 0.0
MAX_OUTPUT_TOKENS = 900


def mocked() -> bool:
    return os.environ.get("MOCK_LLM", "").strip().lower() in ("1", "true", "yes")


def available() -> bool:
    """Whether a real inference call should be attempted at all."""
    if mocked():
        return False
    from . import providers
    if providers.use_fixtures():
        return False
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def why_unavailable() -> str:
    """Surfaced in the trace so 'templates' is never mistaken for 'the model'."""
    if mocked():
        return "MOCK_LLM=true"
    from . import providers
    if providers.use_fixtures():
        return "replaying a captured run"
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        return "no GEMINI_API_KEY configured"
    return "available"


def _extract_json(raw: str) -> Optional[dict]:
    """Models fence JSON in markdown more often than they should."""
    match = re.search(r"\{[\s\S]*\}", raw or "")
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def complete_json(system: str, payload: dict) -> Optional[dict]:
    """
    One structured-output call. Returns parsed JSON, or None on any failure.

    Callers must treat None as normal, not exceptional.
    """
    if not available():
        return None

    try:
        import google.generativeai as genai
    except ImportError:
        logger.warning("[llm] google-generativeai not installed")
        return None

    try:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"].strip())
        model = genai.GenerativeModel(MODEL, system_instruction=system)
        prompt = (json.dumps(payload, ensure_ascii=False)
                  + "\n\nRespond with strict JSON only. No markdown, no prose.")
        config = {"temperature": TEMPERATURE, "max_output_tokens": MAX_OUTPUT_TOKENS}

        for attempt in (1, 2):
            try:
                response = model.generate_content(prompt, generation_config=config)
                parsed = _extract_json(getattr(response, "text", "") or "")
                if parsed is not None:
                    return parsed
                logger.warning("[llm] unparseable response on attempt %s", attempt)
            except Exception as exc:
                logger.warning("[llm] call failed on attempt %s: %s", attempt, exc)
        return None
    except Exception as exc:
        logger.warning("[llm] setup failed: %s", exc)
        return None
