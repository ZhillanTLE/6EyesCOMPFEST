"""
llm.py — One Gemini call, three ways to not make it.

Every agent in this package goes through `complete_json`. It returns parsed
JSON or None, and None is always survivable: each caller has a deterministic
fallback, so a missing key, an exhausted quota or a malformed response degrades
the demo's prose rather than breaking the pipeline.

Two ways a call does not happen, both deliberate and both declared:

  MOCK_LLM=true          plumbing work that does not need inference
  WINDFALL_FIXTURES=1    replaying a captured run; fixtures replace inference

A third way is NOT allowed. Live mode -- no fixtures, no mock -- with no
GEMINI_API_KEY is a misconfiguration, not a mode. It raises
LiveInferenceUnavailable at the start of the run rather than quietly
producing template prose that reads exactly like model output in a
screenshot. "The demo still works without a key" is precisely the
reassurance that would let an unconfigured judging machine present canned
text as inference, so it is refused loudly instead.

Within a configured live run, a single failed call (quota, transport,
malformed JSON) still degrades to the deterministic draft, because losing
one stage's prose is better than losing the trace. That degradation is
never silent: the stage carries `reasonedBy` / `writtenBy` of
"deterministic (...)" and the console renders a FALLBACK badge beside it.

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
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Which model, resolved once at import and never changed during a run, so the
# static-parameter rule holds. Overridable because model availability is per
# key, not universal: "gemini-flash-latest" returned 429 on the demo key while
# other aliases had quota, and several 2.5 names now 404 with "no longer
# available to new users". Run `python -m backend.tools.gemini_probe` to see
# what a given key can actually call.
MODEL = os.environ.get("GEMINI_MODEL", "").strip() or "gemini-flash-lite-latest"
TEMPERATURE = 0.0
# Generous because the current Gemini models are REASONING models: they spend
# an internal thinking budget before emitting anything, and that budget counts
# against this ceiling. At 900 a classifier call spent ~860 tokens thinking,
# emitted 33, and hit MAX_TOKENS mid-sentence -- which surfaced as
# "unparseable response" and a silent fall back to templates. The visible JSON
# these agents produce is a few hundred tokens at most; the headroom is for
# the thinking, not the answer.
MAX_OUTPUT_TOKENS = 8192

# Seconds to wait before the single retry. Free-tier limits are per-minute.
RETRY_BACKOFF_SECONDS = 3.0


def mocked() -> bool:
    return os.environ.get("MOCK_LLM", "").strip().lower() in ("1", "true", "yes")


class LiveInferenceUnavailable(RuntimeError):
    """Live mode was requested but no GEMINI_API_KEY is configured."""


def has_key() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def live_inference_opt_in() -> bool:
    """
    Run real inference while prices still replay.

    WINDFALL_FIXTURES governs PRICES: it replays captured Duffel/RapidAPI
    totals so judging day survives a rate limit or a dead network. Reasoning is
    a separate axis. Without this flag the two move together, which means a
    Gemini key cannot be demonstrated at all unless Duffel and RapidAPI keys
    are also present -- and those need a signup and a paid subscription.

    Swapping the data source behind a tool without touching a prompt is the
    architectural claim the paper makes in section 5.1, so exercising real
    agents over replayed prices demonstrates that claim rather than bending it.

    It stays OFF by default: a plain WINDFALL_FIXTURES=1 run must remain fully
    offline and quota-free.
    """
    return os.environ.get("WINDFALL_LIVE_INFERENCE", "").strip().lower() in ("1", "true", "yes")


def live_mode() -> bool:
    """True when PRICES come from live providers: no mock, no fixtures."""
    if mocked():
        return False
    from . import providers
    return not providers.use_fixtures()


def require_configured() -> None:
    """
    Fail a live run that cannot actually reach the model.

    Called once at the top of pipeline.run, so the failure arrives before any
    stage has produced prose, and the caller gets one clear message instead of
    a trace whose reasoning is templates wearing the model's label.
    """
    if (live_mode() or live_inference_opt_in()) and not has_key():
        raise LiveInferenceUnavailable(
            "Live inference is enabled but GEMINI_API_KEY is not set, so the "
            "Classifier and Notification Curator cannot run. Set GEMINI_API_KEY "
            "in backend/.env to use the live path, or set WINDFALL_FIXTURES=1 to "
            "replay the captured run, or MOCK_LLM=true for plumbing work. "
            "Refusing to substitute template text for model output.")


def available() -> bool:
    """Whether a real inference call should be attempted at all."""
    if mocked():
        return False
    from . import providers
    if providers.use_fixtures() and not live_inference_opt_in():
        return False
    return has_key()


def why_unavailable() -> str:
    """Surfaced in the trace so 'templates' is never mistaken for 'the model'."""
    if mocked():
        return "MOCK_LLM=true"
    from . import providers
    if providers.use_fixtures() and not live_inference_opt_in():
        return "replaying a captured run"
    if not has_key():
        # Unreachable through pipeline.run, which refuses this case up front.
        # Kept so a direct caller still gets an honest label rather than a
        # blank one.
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


def complete_json(system: str, payload: dict, label: str = "llm") -> Optional[dict]:
    """
    One structured-output call. Returns parsed JSON, or None on any failure.

    Callers must treat None as normal, not exceptional.

    `label` names the calling stage in the log. The call is narrated at INFO --
    model, wall clock, token usage -- so a demo can show the terminal and let
    someone watch inference happen rather than take the console's word for it.
    This is console output only: nothing is written to disk, so it stays
    observability rather than the automated data logging the scope rule bans.
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
                logger.info("[%s] calling %s (attempt %s)", label, MODEL, attempt)
                started = time.monotonic()
                response = model.generate_content(prompt, generation_config=config)
                elapsed = time.monotonic() - started
                parsed = _extract_json(getattr(response, "text", "") or "")
                if parsed is not None:
                    usage = getattr(response, "usage_metadata", None)
                    logger.info(
                        "[%s] %s replied in %.2fs (%s prompt + %s output = %s tokens)",
                        label, MODEL, elapsed,
                        getattr(usage, "prompt_token_count", "?"),
                        getattr(usage, "candidates_token_count", "?"),
                        getattr(usage, "total_token_count", "?"))
                    for key, value in parsed.items():
                        preview = str(value)
                        if len(preview) > 160:
                            preview = preview[:157] + "..."
                        logger.info("[%s]   %s = %s", label, key, preview)
                    return parsed
                logger.warning("[llm] unparseable response on attempt %s", attempt)
            except Exception as exc:
                # One short backoff before the retry. Free-tier quota is
                # per-minute, so a rate-limited call retried immediately is
                # certain to fail again; a couple of seconds is often enough.
                # Synchronous and bounded -- two attempts, then the caller's
                # deterministic fallback. Never a queue.
                brief = str(exc).strip().splitlines()[0][:120]
                logger.warning("[llm] %s attempt %s failed: %s", label, attempt, brief)
                if attempt == 1:
                    time.sleep(RETRY_BACKOFF_SECONDS)
        return None
    except Exception as exc:
        logger.warning("[llm] setup failed: %s", exc)
        return None
