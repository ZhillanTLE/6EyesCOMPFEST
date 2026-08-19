"""
duffel_hold_probe.py — Does hold actually work on our key, for our carriers?

    python -m backend.tools.duffel_hold_probe

READ-ONLY BY CONSTRUCTION. This creates offer requests and reads the
payment_requirements block on the returned offers. It never calls
POST /air/orders, because that is a real write against live airline inventory.
There is deliberately no flag to make it do so.

Why this runs before any freeze UI is built: hold support is carrier- and
account-specific. If none of the seeded routes support it, the honest move is
to drop the price-freeze from the demo narrative and let the rebuild ladder be
the whole story -- a smaller true demo beats a simulated feature the paper
claims is real. If some carriers support it, reselect the seed onto those.

What we are reading, per Duffel's offer schema:
  payment_requirements.requires_instant_payment
      false  -> the offer can be held and paid for later. This is hold support.
      true   -> pay now or lose it. No deadline may be shown to a traveler.
  payment_requirements.payment_required_by
      ISO 8601. THE ONLY legitimate source for a countdown in the UI.
  payment_requirements.price_guarantee_expires_at
      ISO 8601. Until when the quoted price itself is guaranteed.

Anything not sourced from those two timestamps is a fake countdown, which the
design system forbids outright and which is the fastest way to lose a judge's
trust on a product whose entire pitch is restraint.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta

try:
    import requests
except ImportError:
    sys.exit("requests is not installed; pip install -r backend/requirements.txt")

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

API = "https://api.duffel.com/air/offer_requests"

# The seeded carriers, by route. Kept in step with recovery/seed/travelers.json.
ROUTES = [
    ("Emirates",           "CGK", "LHR", "business"),
    ("Singapore Airlines", "CGK", "HND", "economy"),
    ("Garuda Indonesia",   "CGK", "SIN", "economy"),
    ("IndiGo",             "CGK", "DXB", "economy"),
    ("Vietnam Airlines",   "CGK", "SGN", "economy"),
    ("China Eastern",      "CGK", "PVG", "economy"),
]


def _key():
    k = os.environ.get("DUFFEL_API_KEY", "").strip().strip("'\"")
    if not k:
        sys.exit(
            "DUFFEL_API_KEY is not set.\n"
            "Copy backend/.env.example to backend/.env and add a key.\n"
            "It must be a duffel_live_ key: duffel_test_ returns synthetic\n"
            "payment_requirements, so a probe against it proves nothing."
        )
    if k.startswith("duffel_test_"):
        print("WARNING: this is a SANDBOX key. Hold results below are synthetic\n"
              "         and must not be used to decide the demo narrative.\n")
    return k


def probe(origin, destination, cabin, depart, key):
    """One offer request. Returns (ok, summary_rows, error)."""
    body = {
        "data": {
            "slices": [{
                "origin": origin,
                "destination": destination,
                "departure_date": depart,
            }],
            "passengers": [{"type": "adult"}],
            "cabin_class": cabin,
        }
    }
    try:
        resp = requests.post(
            API + "?limit=20",
            headers={
                "Authorization": "Bearer " + key,
                "Duffel-Version": "v2",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=body,
            timeout=45,
        )
    except Exception as exc:
        return False, [], "request failed: {}".format(exc)

    if resp.status_code >= 400:
        return False, [], "HTTP {}: {}".format(resp.status_code, resp.text[:200])

    offers = (resp.json().get("data") or {}).get("offers") or []
    rows = []
    for o in offers:
        pr = o.get("payment_requirements") or {}
        rows.append({
            "offer_id": o.get("id"),
            "carrier": ((o.get("owner") or {}).get("name")) or "?",
            "total": "{} {}".format(o.get("total_currency"), o.get("total_amount")),
            "instant": pr.get("requires_instant_payment"),
            "pay_by": pr.get("payment_required_by"),
            "price_guarantee": pr.get("price_guarantee_expires_at"),
        })
    return True, rows, None


def main():
    key = _key()
    depart = (date.today() + timedelta(days=45)).isoformat()
    print("Duffel hold-eligibility probe")
    print("departure date: {}   (read-only; no orders are created)".format(depart))
    print("=" * 78)

    verdict = {}
    for label, origin, destination, cabin in ROUTES:
        ok, rows, err = probe(origin, destination, cabin, depart, key)
        print("\n{}  {} -> {}  [{}]".format(label, origin, destination, cabin))
        if not ok:
            print("  ERROR  {}".format(err))
            verdict[label] = "error"
            continue
        if not rows:
            print("  no offers returned")
            verdict[label] = "no offers"
            continue

        holdable = [r for r in rows if r["instant"] is False]
        print("  {} offers, {} holdable".format(len(rows), len(holdable)))
        for r in (holdable or rows)[:3]:
            print("    {:<26} {:>16}  instant={!s:<5} pay_by={} guarantee={}".format(
                r["carrier"][:26], r["total"], r["instant"],
                r["pay_by"] or "-", r["price_guarantee"] or "-"))
        verdict[label] = "HOLD OK" if holdable else "instant payment only"

    print("\n" + "=" * 78)
    print("VERDICT")
    for label, v in verdict.items():
        print("  {:<22} {}".format(label, v))

    supported = [k for k, v in verdict.items() if v == "HOLD OK"]
    print()
    if supported:
        print("{} of {} seeded carriers support hold: {}".format(
            len(supported), len(ROUTES), ", ".join(supported)))
        print("Point the freeze demo at these routes. Any seeded route NOT in")
        print("this list must render hold state = not_eligible, with no deadline.")
    else:
        print("NO seeded carrier supports hold on this key.")
        print("Recommendation: drop the price-freeze from the demo narrative and")
        print("make the rebuild ladder the entire story. Do not simulate a freeze")
        print("the paper describes as real -- amend section 2.1 and Tabel 1.5")
        print("instead. A smaller honest demo is worth more than a fake feature.")

    with open("duffel_hold_probe_result.json", "w", encoding="utf-8") as fh:
        json.dump(verdict, fh, indent=2)
    print("\nwrote duffel_hold_probe_result.json")


if __name__ == "__main__":
    main()
