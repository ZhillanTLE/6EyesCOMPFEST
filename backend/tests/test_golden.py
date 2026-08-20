"""
Golden-fixture regression tests -- one function per cart.

WHY THE SHAPE MATTERS. An earlier revision looped `repository.all_travelers()`
and ran the pipeline over the whole seed. That is the seed of automated
evaluation, which is exactly what the "no bulk testing scripts" rule targets.
Six explicit single-cart tests are just tests: they name what they cover, they
fail one at a time, and nothing here can grow into an eval harness.

Parameterisation would be the same loop wearing a hat. Each cart gets its own
function on purpose.

Together these are the regression net for the four outcomes.
"""
import json
import os
import unittest

os.environ.setdefault("WINDFALL_FIXTURES", "1")

from backend.recovery import config, pipeline  # noqa: E402
from backend.recovery.schemas import Outcome  # noqa: E402

GOLDEN = os.path.join(os.path.dirname(__file__), "..", "recovery", "seed", "golden.json")

with open(GOLDEN, encoding="utf-8") as _fh:
    GOLD = json.load(_fh)


class GoldenCartCase(unittest.TestCase):
    """Assertions shared by the per-cart cases below. Not a loop: each subclass
    names one cart and the suite reports on it individually."""

    traveler_id = None
    expected_outcome = None

    def stored(self):
        return GOLD["results"][self.traveler_id]

    def assertMatchesFreshRun(self):
        """Regenerating must be a no-op. A diff here means either the fixture
        is stale or the pipeline moved -- both need a human."""
        fresh = pipeline.run(self.traveler_id).to_dict()
        stored = self.stored()
        self.assertEqual(fresh["decision"]["outcome"], stored["decision"]["outcome"])
        self.assertEqual(fresh["decision"]["final_total_idr"],
                         stored["decision"]["final_total_idr"])
        self.assertEqual(fresh["decision"]["cleared_rung"],
                         stored["decision"]["cleared_rung"])

    def assertNoMarginConceded(self):
        self.assertEqual(self.stored()["decision"]["margin_conceded_idr"], 0)

    def assertDeadlineOnlyIfGuaranteed(self):
        hold = self.stored()["hold"]
        if hold["expires_at"]:
            self.assertEqual(hold["state"], "eligible")

    def assertNotificationIsReal(self):
        note = self.stored()["notification"]
        self.assertIsNotNone(note)
        self.assertTrue(note["subject"].strip())
        self.assertGreaterEqual(len(note["body_paragraphs"]), 2)
        self.assertTrue(note["whatsapp"].strip())
        self.assertTrue(note["cta_label"].strip())

    def assertNoEmoji(self):
        note = self.stored()["notification"]
        if not note:
            return
        blob = " ".join([note["subject"], note["whatsapp"]] + note["body_paragraphs"])
        for ch in blob:
            self.assertLess(ord(ch), 0x2190, "emoji in copy: {!r}".format(ch))


class TestPrasetyoReminder(GoldenCartCase):
    """wf-01 Premium, campaign share 9%. The gate closes on the price-sensitivity
    axis even though the cart runs over usual spend. This is the differentiator:
    a traveler price is not blocking gets no discount."""

    traveler_id = "wf-01"

    def test_outcome_is_reminder(self):
        self.assertEqual(self.stored()["decision"]["outcome"], Outcome.REMINDER)

    def test_gate_closed_on_campaign_share_not_budget(self):
        gate = self.stored()["gate"]
        self.assertFalse(gate["opened"])
        self.assertFalse(gate["price_sensitive"])
        self.assertTrue(gate["over_budget"], "the cart IS over budget; the other axis closed it")

    def test_price_is_untouched(self):
        d = self.stored()["decision"]
        self.assertEqual(d["saving_idr"], 0)
        self.assertEqual(d["final_total_idr"], self.stored()["original_total_idr"])

    def test_still_gets_a_real_notification(self):
        """A reminder is a decision, not an absence. It gets a full message."""
        self.assertNotificationIsReal()

    def test_matches_fresh_run(self):
        self.assertMatchesFreshRun()

    def test_no_margin_conceded(self):
        self.assertNoMarginConceded()


class TestAyuRebuild(GoldenCartCase):
    """wf-02 Premium, campaign share 46%. Same tier as wf-01, opposite outcome,
    purely because campaign share differs. The demo's strongest contrast."""

    traveler_id = "wf-02"

    def test_outcome_is_rebuild(self):
        self.assertEqual(self.stored()["decision"]["outcome"], Outcome.REBUILD)

    def test_same_tier_as_the_reminder_traveler(self):
        self.assertEqual(self.stored()["classification"]["tier"],
                         GOLD["results"]["wf-01"]["classification"]["tier"])

    def test_gate_opened_on_both_axes(self):
        gate = self.stored()["gate"]
        self.assertTrue(gate["opened"])
        self.assertTrue(gate["price_sensitive"])
        self.assertTrue(gate["over_budget"])

    def test_genuinely_clears_the_premium_threshold(self):
        """tau(Premium) = 15%. Constructed to clear, never back-fitted."""
        d = self.stored()["decision"]
        self.assertEqual(d["cleared_rung"], config.RUNG_TIER_DOWN)
        self.assertGreaterEqual(d["saving_pct"], config.TAU[config.TIER_PREMIUM])

    def test_earlier_rungs_were_tried_and_reported(self):
        attempts = self.stored()["decision"]["attempts"]
        self.assertEqual(len(attempts), 3)
        self.assertFalse(attempts[0]["cleared"])
        self.assertFalse(attempts[1]["cleared"])

    def test_matches_fresh_run(self):
        self.assertMatchesFreshRun()

    def test_no_margin_conceded(self):
        self.assertNoMarginConceded()

    def test_deadline_only_if_guaranteed(self):
        self.assertDeadlineOnlyIfGuaranteed()


class TestBagusLateral(GoldenCartCase):
    """wf-03 Comfort. A same-star swap clears on rung 02, so the ladder stops
    before proposing any downgrade."""

    traveler_id = "wf-03"

    def test_outcome_is_lateral_not_rebuild(self):
        """A same-star swap is not a downgrade and must not read as one."""
        self.assertEqual(self.stored()["decision"]["outcome"], Outcome.LATERAL)
        self.assertEqual(self.stored()["decision"]["cleared_rung"], config.RUNG_LATERAL)

    def test_ladder_stopped_before_tier_down(self):
        rungs = [a["rung"] for a in self.stored()["decision"]["attempts"]]
        self.assertNotIn(config.RUNG_TIER_DOWN, rungs)

    def test_star_rating_is_unchanged(self):
        winner = next(a for a in self.stored()["decision"]["attempts"] if a["cleared"])
        self.assertEqual(winner["hotel"]["stars"], 4)

    def test_matches_fresh_run(self):
        self.assertMatchesFreshRun()

    def test_no_margin_conceded(self):
        self.assertNoMarginConceded()


class TestIntanAlternative(GoldenCartCase):
    """wf-04 Value. The gate opens, but no rung clears -- thin inventory means
    even a star down saves little. Falls through to a different trip."""

    traveler_id = "wf-04"

    def test_outcome_is_alternative(self):
        self.assertEqual(self.stored()["decision"]["outcome"], Outcome.ALTERNATIVE)

    def test_gate_opened_but_nothing_cleared(self):
        self.assertTrue(self.stored()["gate"]["opened"])
        self.assertIsNone(self.stored()["decision"]["cleared_rung"])

    def test_every_rung_was_priced_and_reported(self):
        """The rungs that missed are the evidence restraint was earned."""
        attempts = self.stored()["decision"]["attempts"]
        self.assertEqual(len(attempts), 3)
        for a in attempts:
            self.assertTrue(a["available"], a["rung"])
            self.assertFalse(a["cleared"], a["rung"])
            self.assertLess(a["delta"], config.TAU[config.TIER_VALUE])

    def test_matches_fresh_run(self):
        self.assertMatchesFreshRun()

    def test_no_margin_conceded(self):
        self.assertNoMarginConceded()


class TestRizkyColdStart(GoldenCartCase):
    """wf-05 One booking. Campaign share is unmeasurable, the tier comes from
    the cart, the ladder still runs, and nothing clears -- so the cart is left
    exactly as it was. The 'found something, not worth showing' case."""

    traveler_id = "wf-05"

    def test_campaign_share_is_null_never_fabricated(self):
        self.assertIsNone(self.stored()["gate"]["campaign_share"])
        self.assertIsNone(self.stored()["gate"]["price_sensitive"])

    def test_tier_came_from_the_cart_not_history(self):
        self.assertEqual(self.stored()["classification"]["tier_source"], "cart_proxy")
        self.assertTrue(self.stored()["classification"]["is_cold_start"])

    def test_ladder_still_ran_under_the_exception(self):
        """Rebuild concedes no margin, so a weaker signal can still justify it."""
        self.assertTrue(self.stored()["gate"]["cold_start_exception"])
        self.assertTrue(self.stored()["gate"]["opened"])
        self.assertEqual(len(self.stored()["decision"]["attempts"]), 3)

    def test_falls_to_reminder_when_nothing_is_worth_showing(self):
        self.assertEqual(self.stored()["decision"]["outcome"], Outcome.REMINDER)
        self.assertEqual(self.stored()["decision"]["saving_idr"], 0)

    def test_matches_fresh_run(self):
        self.assertMatchesFreshRun()

    def test_no_margin_conceded(self):
        self.assertNoMarginConceded()


class TestDewiUpstreamFailure(GoldenCartCase):
    """wf-06 Carrier inventory unavailable. A pipeline over live inventory will
    fail sometimes, and a demo that cannot show it is dishonest."""

    traveler_id = "wf-06"

    def test_outcome_is_error(self):
        self.assertEqual(self.stored()["decision"]["outcome"], Outcome.ERROR)

    def test_classifier_still_completed(self):
        stages = {t["stage"]: t["duration_ms"] for t in self.stored()["timings"]}
        self.assertGreater(stages["classifier"], 0)
        self.assertTrue(self.stored()["classification"]["reasoning"])

    def test_no_notification_is_drafted(self):
        self.assertIsNone(self.stored()["notification"])

    def test_gate_reports_itself_unevaluated_rather_than_zeroed(self):
        """With no prices there is no cart total, so the budget gap is
        undefined. Reporting a zero would read as a real measurement."""
        self.assertFalse(self.stored()["gate"]["opened"])
        self.assertIn("tidak dievaluasi", self.stored()["gate"]["reason"])

    def test_no_deadline_is_shown(self):
        self.assertDeadlineOnlyIfGuaranteed()


class TestGoldenCoverage(unittest.TestCase):
    """One structural assertion over the file itself -- not a pipeline run."""

    def test_all_four_outcomes_plus_error_are_covered(self):
        seen = {r["decision"]["outcome"] for r in GOLD["results"].values()}
        self.assertEqual(seen, {Outcome.REBUILD, Outcome.LATERAL, Outcome.REMINDER,
                                Outcome.ALTERNATIVE, Outcome.ERROR})

    def test_queue_withholds_the_reasoned_verdict(self):
        """Browse cards carry the provisional estimate (tier, campaign share);
        the Classifier's reasoned verdict is not pre-announced."""
        for entry in GOLD["queue"]:
            self.assertNotIn("outcome", entry)
            self.assertNotIn("reasoning", entry)


if __name__ == "__main__":
    unittest.main()
