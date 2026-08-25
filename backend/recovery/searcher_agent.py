"""
searcher_agent.py — Stage 2. Is this substitution actually comparable?

Paper Tabel 1.7 gives this stage the job of "menilai kecukupan tiap percobaan
terhadap ambang tingkatan". Read literally that would put threshold arithmetic
in a model, which paper section 4 forbids in the same breath -- transactional
figures must be auditable and reproducible.

The reconciliation, and it is a real one rather than a dodge: SUFFICIENCY
SPLITS IN TWO.

  Arithmetic   delta_k = (p0 - pk)/p0, and delta_k >= tau.
               Deterministic, in ladder.py, unit-tested. No model touches it.

  Comparability  Is a 4-star in Otemachi a fair stand-in for a 5-star in
               Otemachi? Is this "same area" in any sense a traveler would
               recognise? That is contextual judgement, and it is exactly the
               kind of question a percentage cannot answer.

A rung can clear the threshold and still be a poor substitution. The agent
cannot overturn `cleared` -- the ladder already stopped there -- but it can
say so, and the analyst approving the send gets to see it before deciding.

This module never mutates a LadderAttempt. It returns notes alongside them.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Sequence

from . import llm
from .formatting import idr, plain_pct
from .schemas import LadderAttempt

logger = logging.getLogger(__name__)

SYSTEM = """You are the Searcher stage of Windfall, an abandoned-cart recovery
pipeline for an Indonesian online travel agency.

A deterministic ladder has already priced each rebuild attempt and decided which
one cleared the tier threshold. THAT ARITHMETIC IS SETTLED AND YOU CANNOT CHANGE
IT. Do not recompute a saving and do not disagree about which attempt cleared.

Your job is the part arithmetic cannot do: judge whether each substitution is
genuinely comparable for this traveler. Consider the star rating, the area, the
dates, and how the replacement property relates to the one they chose.

Rules:
- One short note per attempt, in English, for an analyst.
- Say plainly when a substitution is weak even though it cleared the threshold.
  A cleared rung is not automatically a good offer, and the analyst approving
  the send needs to know that before they approve it.
- A same-star swap is NOT a downgrade. Never describe it as one.
- Never invent a hotel, a price, or a percentage.

Respond with strict JSON:
{"notes": [{"index": 1, "comparable": true, "note": "..."}]}
"""


def assess(cart, tier: str, threshold: float,
           attempts: Sequence[LadderAttempt]) -> Dict[int, Dict]:
    """
    Returns {attempt_index: {"comparable": bool, "note": str}}.

    Empty dict when inference is unavailable -- the ledger renders fine without
    notes, so there is no fallback text to invent here. A silent absence is
    better than a template pretending to be judgement.
    """
    priced = [a for a in attempts if a.available]
    if not priced:
        return {}

    payload = {
        "traveler": {"tier": tier, "threshold": plain_pct(threshold)},
        "originalCart": {
            "hotel": cart.hotel.name,
            "stars": cart.hotel.stars,
            "area": cart.hotel.area,
            "city": cart.hotel.city,
            "total": idr(cart.total_idr),
        },
        "attempts": [{
            "index": a.index,
            "rung": a.rung,
            "label": a.label,
            "replacementHotel": a.hotel.name if a.hotel else None,
            "replacementStars": a.hotel.stars if a.hotel else None,
            "replacementArea": a.hotel.area if a.hotel else None,
            "total": idr(a.total_idr),
            "saving": plain_pct(a.delta),
            "clearedThreshold": a.cleared,
        } for a in priced],
    }

    result = llm.complete_json(SYSTEM, payload, label="searcher")
    if not result:
        return {}

    out: Dict[int, Dict] = {}
    for row in (result.get("notes") or []):
        try:
            index = int(row.get("index"))
        except (TypeError, ValueError):
            continue
        note = str(row.get("note") or "").strip()
        if not note:
            continue
        out[index] = {
            "comparable": bool(row.get("comparable", True)),
            "note": "".join(ch for ch in note if ord(ch) < 0x2190),
        }
    return out
