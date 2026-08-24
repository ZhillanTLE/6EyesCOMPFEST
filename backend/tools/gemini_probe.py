"""
gemini_probe.py - Will the demo actually show real inference?

    python -m backend.tools.gemini_probe

Run this BEFORE recording. The pipeline is deliberately survivable: when a
Gemini call fails -- wrong model name, exhausted quota, revoked key, no
network -- the agents fall back to deterministic drafts so the trace still
renders. That is the right behaviour in front of a judge and the wrong thing
to discover halfway through a take, because the console will quietly show
FALLBACK badges and prose that reads exactly like model output.

So this makes ONE real call through the same `llm.complete_json` the agents
use, and reports what actually happened. One call, not a loop over the seed:
this is a connectivity probe, not a bulk-testing script.

It is READ-ONLY with respect to the repo. It writes no fixture, captures
nothing to disk, and changes no constant.

Exit codes:  0 real inference works   1 misconfigured or unreachable
"""
from __future__ import annotations

import os
import sys

from backend.recovery import llm, providers


def _mode_report() -> None:
    print("Configuration")
    print("  WINDFALL_FIXTURES       = {}".format(os.environ.get("WINDFALL_FIXTURES", "(unset)")))
    print("  WINDFALL_LIVE_INFERENCE = {}".format(os.environ.get("WINDFALL_LIVE_INFERENCE", "(unset)")))
    print("  MOCK_LLM                = {}".format(os.environ.get("MOCK_LLM", "(unset)")))
    print("  GEMINI_API_KEY          = {}".format("set" if llm.has_key() else "NOT SET"))
    print("  prices                  = {}".format("replayed capture" if providers.use_fixtures() else "live providers"))
    print("  model                   = {}".format(llm.MODEL))
    print()


def _suggest_models() -> None:
    """A wrong MODEL constant is the failure that looks like a quota problem."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"].strip())
        usable = [m.name for m in genai.list_models()
                  if "generateContent" in getattr(m, "supported_generation_methods", [])]
    except Exception as exc:
        # google.api_core errors stringify into a multi-line protobuf dump;
        # the first line carries the part a human needs.
        first = str(exc).strip().splitlines()[0][:160]
        print("  (could not list models: {})".format(first))
        return
    if not usable:
        print("  (the key lists no models supporting generateContent)")
        return
    print("  Models this key can actually call:")
    for name in usable[:12]:
        marker = "  <-- llm.MODEL" if name.endswith(llm.MODEL) else ""
        print("    {}{}".format(name, marker))
    if not any(n.endswith(llm.MODEL) for n in usable):
        print()
        print("  llm.MODEL ({}) is NOT in that list. Set MODEL in".format(llm.MODEL))
        print("  backend/recovery/llm.py to one of the names above.")


def main() -> int:
    print()
    print("Windfall - Gemini preflight")
    print("=" * 66)
    _mode_report()

    if llm.mocked():
        print("RESULT: MOCK_LLM is on, so no call is made and the console will")
        print("        label every stage deterministic. Unset it to record.")
        return 1

    if not llm.has_key():
        print("RESULT: no GEMINI_API_KEY. A live run is refused outright; a")
        print("        fixtures run renders replayed reasoning. Neither shows")
        print("        the model working. Set the key in backend/.env.")
        return 1

    if not llm.available():
        print("RESULT: a key is set but inference is switched off ({}).".format(llm.why_unavailable()))
        print("        For real agents over replayed prices, set")
        print("        WINDFALL_LIVE_INFERENCE=1 alongside WINDFALL_FIXTURES=1.")
        return 1

    print("Calling {} once through llm.complete_json ...".format(llm.MODEL))
    result = llm.complete_json(
        "You are a connectivity probe. Reply with strict JSON only.",
        {"reply": "state ok", "shape": {"ok": True, "note": "short string"}})

    if result is None:
        print()
        print("RESULT: THE CALL FAILED. The pipeline would fall back to")
        print("        deterministic drafts and the console would show FALLBACK")
        print("        badges. Do not record yet.")
        print()
        _suggest_models()
        return 1

    print()
    print("  response: {}".format(result))
    print()
    print("RESULT: real inference works. The Classifier and Notification")
    print("        Curator will report reasonedBy/writtenBy = 'gemini' and the")
    print("        console will show no FALLBACK badge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
