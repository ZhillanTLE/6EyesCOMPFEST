"""
Tests for the deterministic recovery core.

Stdlib unittest on purpose: the repo has no pytest and a judge cloning this
should be able to run the suite with nothing but python.

    python -m unittest discover -s backend/tests -t .

Under test is every decision the pipeline makes WITHOUT a model in the loop --
tier, gate, ladder, outcome. Paper section 4 promises these are reproducible
and auditable, so they are the part that gets tests.
"""
import json
import os
import unittest

from backend.recovery import config, gate, ladder, outcomes, tiers
from backend.recovery.ladder import RungCandidate
from backend.recovery.schemas import (
    AbandonedCart, FlightSpec, HotelSpec, Outcome, TravelerHistory,
)

SEED_PATH = os.path.join(
    os.path.dirname(__file__), "..", "recovery", "seed", "travelers.json")


def make_cart(flight_idr=0, hotel_idr=0, stars=4, cabin="economy"):
    return AbandonedCart(
        cart_id="c1", traveler_id="t1",
        flight=FlightSpec("Garuda", "CGK", "SIN", "2027-01-01", "2027-01-05",
                          cabin, 2, flight_idr),
        hotel=HotelSpec("Test Hotel", stars, "Singapore", "Marina Bay",
                        "2027-01-01", "2027-01-04", hotel_idr),
        abandoned_hours_ago=5,
    )


def make_history(usual_spend=20000000, campaign_share=0.4, bookings=5):
    return TravelerHistory("t1", "Test", bookings, usual_spend, campaign_share)


def fixed_provider(prices):
    """Provider returning a preset total per rung; None means nothing found."""
    def _p(rung, cart):
        if rung not in prices or prices[rung] is None:
            return None
        return RungCandidate(prices[rung])
    return _p


class TestTiers(unittest.TestCase):
    def setUp(self):
        self.dist = [9000000, 15000000, 21000000, 26000000, 58000000, 62000000]

    def test_percentile_boundaries_match_paper(self):
        self.assertEqual(tiers.tier_from_percentile(0.10), config.TIER_VALUE)
        self.assertEqual(tiers.tier_from_percentile(0.30), config.TIER_VALUE)
        self.assertEqual(tiers.tier_from_percentile(0.31), config.TIER_COMFORT)
        self.assertEqual(tiers.tier_from_percentile(0.80), config.TIER_COMFORT)
        self.assertEqual(tiers.tier_from_percentile(0.81), config.TIER_PREMIUM)

    def test_tier_is_monotone_in_spend(self):
        """The seed defect that shipped in the prototype: a lower average spend
        landing in a higher tier. Percentile assignment cannot do that, and this
        test exists to keep it that way."""
        seen = [tiers.tier_from_percentile(tiers.percentile_rank(m, self.dist))
                for m in sorted(self.dist)]
        order = {config.TIER_VALUE: 0, config.TIER_COMFORT: 1, config.TIER_PREMIUM: 2}
        ranks = [order[t] for t in seen]
        self.assertEqual(ranks, sorted(ranks))

    def test_thresholds_match_paper(self):
        self.assertEqual(tiers.threshold_for(config.TIER_VALUE), 0.05)
        self.assertEqual(tiers.threshold_for(config.TIER_COMFORT), 0.10)
        self.assertEqual(tiers.threshold_for(config.TIER_PREMIUM), 0.15)

    def test_cold_start_uses_cart_proxy_not_history(self):
        cold = TravelerHistory("t1", "New", 1, 15000000, None)
        tier, source = tiers.assign_tier(
            cold, make_cart(stars=5, cabin="business"), self.dist)
        self.assertEqual(source, "cart_proxy")
        self.assertEqual(tier, config.TIER_PREMIUM)


class TestGate(unittest.TestCase):
    """The conjunction is the product. These four cases are the whole thesis."""

    def test_both_signals_agree_opens(self):
        r = gate.evaluate(make_history(20000000, 0.46), 24000000)
        self.assertTrue(r.opened)

    def test_high_campaign_share_alone_does_not_open(self):
        """Price-sensitive, but the cart is within budget. No intervention."""
        r = gate.evaluate(make_history(30000000, 0.46), 24000000)
        self.assertFalse(r.opened)
        self.assertTrue(r.price_sensitive)
        self.assertFalse(r.over_budget)

    def test_budget_gap_alone_does_not_open(self):
        """Over budget, but historically pays full price. Price is not the barrier."""
        r = gate.evaluate(make_history(20000000, 0.09), 24000000)
        self.assertFalse(r.opened)
        self.assertFalse(r.price_sensitive)
        self.assertTrue(r.over_budget)

    def test_neither_signal_closes(self):
        r = gate.evaluate(make_history(30000000, 0.09), 24000000)
        self.assertFalse(r.opened)

    def test_c_star_boundary_is_inclusive(self):
        r = gate.evaluate(make_history(20000000, config.C_STAR), 24000000)
        self.assertTrue(r.price_sensitive)

    def test_cold_start_opens_under_the_exception(self):
        cold = TravelerHistory("t1", "New", 1, 15000000, None)
        r = gate.evaluate(cold, 20000000)
        self.assertTrue(r.opened)
        self.assertTrue(r.cold_start_exception)
        self.assertIsNone(r.price_sensitive)

    def test_closed_gate_always_names_the_axis(self):
        for usual, share in ((30000000, 0.46), (20000000, 0.09), (30000000, 0.09)):
            r = gate.evaluate(make_history(usual, share), 24000000)
            self.assertFalse(r.opened)
            self.assertGreater(len(r.reason), 40, "closed gate must give a reason")


class TestLadder(unittest.TestCase):
    def test_stops_at_first_clearing_rung(self):
        cart = make_cart(10000000, 10000000)
        attempts = ladder.run(cart, 0.05, fixed_provider({
            config.RUNG_REPRICE: 19600000,
            config.RUNG_LATERAL: 18800000,
            config.RUNG_TIER_DOWN: 16000000,
        }))
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[-1].rung, config.RUNG_LATERAL)
        self.assertTrue(attempts[-1].cleared)

    def test_smallest_sufficient_change_wins_not_the_cheapest(self):
        """min over k of delta_k >= tau, not argmax delta. A bigger saving
        further down the ladder must not displace a sufficient one higher up."""
        cart = make_cart(10000000, 10000000)
        attempts = ladder.run(cart, 0.05, fixed_provider({
            config.RUNG_REPRICE: 18000000,
            config.RUNG_LATERAL: 12000000,
        }))
        self.assertEqual(len(attempts), 1)
        self.assertEqual(ladder.winner(attempts).rung, config.RUNG_REPRICE)

    def test_priced_but_missed_is_distinct_from_nothing_found(self):
        """The 'found something, not worth showing' case has to stay visible --
        it is the evidence that restraint was earned rather than assumed."""
        cart = make_cart(10000000, 10000000)
        attempts = ladder.run(cart, 0.20, fixed_provider({
            config.RUNG_REPRICE: None,
            config.RUNG_LATERAL: 19000000,
            config.RUNG_TIER_DOWN: None,
        }))
        self.assertFalse(attempts[0].available)
        self.assertIsNone(attempts[0].delta)
        self.assertTrue(attempts[1].available)
        self.assertAlmostEqual(attempts[1].delta, 0.05)
        self.assertFalse(attempts[1].cleared)

    def test_threshold_is_inclusive(self):
        attempts = ladder.run(make_cart(10000000, 10000000), 0.10,
                              fixed_provider({config.RUNG_REPRICE: 18000000}))
        self.assertTrue(attempts[0].cleared)

    def test_flight_is_pinned_across_rungs(self):
        """No rung may alter the flight -- a Hold Order is held against a
        specific offer, and swapping it would void the guarantee."""
        seen = []

        def spy(rung, cart):
            seen.append((cart.flight.carrier, cart.flight.duffel_offer_id))
            return RungCandidate(19000000)

        ladder.run(make_cart(10000000, 10000000), 0.99, spy)
        self.assertEqual(len(set(seen)), 1)


class TestOutcomes(unittest.TestCase):
    OPEN = (20000000, 0.46)
    SHUT = (30000000, 0.09)

    def _gate(self, pair, cart_total=24000000):
        return gate.evaluate(make_history(*pair), cart_total)

    def test_closed_gate_yields_reminder_at_full_price(self):
        d = outcomes.decide(self._gate(self.SHUT), 24000000)
        self.assertEqual(d.outcome, Outcome.REMINDER)
        self.assertEqual(d.saving_idr, 0)
        self.assertEqual(d.final_total_idr, 24000000)

    def test_lateral_is_not_reported_as_rebuild(self):
        attempts = ladder.run(make_cart(12000000, 12000000), 0.10, fixed_provider({
            config.RUNG_REPRICE: 23600000,
            config.RUNG_LATERAL: 21000000,
        }))
        d = outcomes.decide(self._gate(self.OPEN), 24000000, attempts)
        self.assertEqual(d.outcome, Outcome.LATERAL)
        self.assertEqual(d.cleared_rung, config.RUNG_LATERAL)

    def test_tier_down_reports_as_rebuild(self):
        attempts = ladder.run(make_cart(12000000, 12000000), 0.10, fixed_provider({
            config.RUNG_REPRICE: 23600000,
            config.RUNG_LATERAL: 23000000,
            config.RUNG_TIER_DOWN: 21000000,
        }))
        d = outcomes.decide(self._gate(self.OPEN), 24000000, attempts)
        self.assertEqual(d.outcome, Outcome.REBUILD)

    def test_nothing_clears_falls_to_alternative_when_one_exists(self):
        attempts = ladder.run(make_cart(12000000, 12000000), 0.10, fixed_provider({
            config.RUNG_REPRICE: 23600000,
            config.RUNG_LATERAL: 23000000,
            config.RUNG_TIER_DOWN: 22400000,
        }))
        d = outcomes.decide(self._gate(self.OPEN), 24000000, attempts,
                            alternative_total_idr=18000000)
        self.assertEqual(d.outcome, Outcome.ALTERNATIVE)

    def test_nothing_clears_and_no_alternative_falls_to_reminder(self):
        attempts = ladder.run(make_cart(12000000, 12000000), 0.10, fixed_provider({
            config.RUNG_REPRICE: 23600000,
            config.RUNG_LATERAL: 23000000,
            config.RUNG_TIER_DOWN: 22400000,
        }))
        d = outcomes.decide(self._gate(self.OPEN), 24000000, attempts)
        self.assertEqual(d.outcome, Outcome.REMINDER)
        self.assertEqual(d.saving_idr, 0)

    def test_no_outcome_ever_concedes_margin(self):
        """The load-bearing claim of section 2.3. If this fails, the whole
        margin-preservation argument fails with it."""
        cases = [
            outcomes.decide(self._gate(self.SHUT), 24000000),
            outcomes.decide(self._gate(self.OPEN), 24000000, ladder.run(
                make_cart(12000000, 12000000), 0.10,
                fixed_provider({config.RUNG_REPRICE: 21000000}))),
            outcomes.decide(self._gate(self.OPEN), 24000000, (),
                            alternative_total_idr=18000000),
        ]
        for d in cases:
            self.assertEqual(d.margin_conceded_idr, 0, d.outcome)


class TestSeed(unittest.TestCase):
    def setUp(self):
        with open(SEED_PATH, encoding="utf-8") as fh:
            self.seed = json.load(fh)

    def test_six_travelers_one_per_path(self):
        targets = [t["calibrationTarget"] for t in self.seed["travelers"]]
        self.assertEqual(len(targets), 6)
        self.assertEqual(len(set(targets)), 6)

    def test_cold_start_campaign_share_is_null_not_fabricated(self):
        """A traveler with no history cannot have a measured discount share.
        The prototype shipped one with booking_count 1 and campaign 45%."""
        for t in self.seed["travelers"]:
            if t["bookings"] <= config.COLD_START_MAX_BOOKINGS:
                self.assertIsNone(t["campaignShare"], t["name"])

    def test_seed_carries_no_prices_and_no_outcomes(self):
        """Prices come from live re-query; outcomes are computed. A seed holding
        either would make the demo a slideshow."""
        banned = {"value", "price", "total", "save", "saving", "nw", "r1", "r2",
                  "alt_price", "type", "outcome", "decision"}
        for t in self.seed["travelers"]:
            keys = (list(t) + list(t["cart"]) + list(t["cart"]["flight"])
                    + list(t["cart"]["hotel"]))
            for key in keys:
                self.assertNotIn(key.lower(), banned,
                                 "{}: {}".format(t["name"], key))

    def test_campaign_shares_sit_clear_of_c_star(self):
        """c* = 0.25 is calibrated against this distribution. If a share drifts
        near the bar, the demo outcome becomes a coin flip."""
        for t in self.seed["travelers"]:
            share = t["campaignShare"]
            if share is not None:
                self.assertGreater(abs(share - config.C_STAR), 0.05, t["name"])


if __name__ == "__main__":
    unittest.main()
