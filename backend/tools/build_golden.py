"""
build_golden.py — Capture the golden fixture for ONE cart.

    WINDFALL_FIXTURES=1 python -m backend.tools.build_golden --cart wf-02

One cart per invocation, by design. A runner that swept the whole seed would be
a bulk-testing script, and persisting its output would be automated logging --
both outside the penyisihan scope. Capture is a deliberate manual act, and
regenerating all six means typing the command six times, which is the point:
each capture is a decision someone made, not a side effect of running the app.

Merges into the existing golden.json rather than rewriting it, so capturing one
cart never silently disturbs the other five.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

os.environ.setdefault("WINDFALL_FIXTURES", "1")

from backend.recovery import pipeline, repository  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "recovery", "seed", "golden.json")


def load() -> dict:
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as fh:
            return json.load(fh)
    return {"_readme": "", "queue": [], "results": {}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cart", required=True,
                    help="traveler_id to capture, e.g. wf-02")
    ap.add_argument("--list", action="store_true",
                    help="print the available traveler ids and exit")
    args = ap.parse_args()

    known = repository.traveler_ids()
    if args.list:
        print("\n".join(known))
        return 0
    if args.cart not in known:
        print("unknown cart {!r}; known ids: {}".format(args.cart, ", ".join(known)),
              file=sys.stderr)
        return 1

    payload = load()
    payload["_readme"] = (
        "Generated one cart at a time by backend/tools/build_golden.py --cart <id>. "
        "Do not hand-edit. Covers all four outcomes plus the upstream-failure path."
    )
    payload["queue"] = repository.queue()
    payload["results"][args.cart] = pipeline.run(args.cart).to_dict()

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    outcome = payload["results"][args.cart]["decision"]["outcome"]
    print("captured {} -> {}".format(args.cart, outcome))
    missing = [c for c in known if c not in payload["results"]]
    if missing:
        print("not yet captured: {}".format(", ".join(missing)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
