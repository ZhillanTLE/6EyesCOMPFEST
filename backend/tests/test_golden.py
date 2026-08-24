"""
Golden-fixture regression tests -- one function per cart.

WHY THE SHAPE MATTERS. An earlier revision looped `repository.all_travelers()`
and ran the pipeline over the whole seed. That is the seed of automated
evaluation, which is exactly what the "no bulk testing scripts" rule targets.
Explicit single-cart tests are just tests: they name what they cover, they
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
        self.assertEqual(fresh["decision"]["finalTotalIdr"],
                         stored["decision"]["finalTotalIdr"])
        self.assertEqual(fresh["decision"]["clearedRung"],
                         stored["decision"]["clearedRung"])

    def assertNoMarginConceded(self):
        self.assertEqual(self.stored()["decision"]["marginConcededIdr"], 0)

    def assertDeadlineOnlyIfGuaranteed(self):
        hold = self.stored()["hold"]
        if hold["expiresAt"]:
            self.assertEqual(hold["state"], "eligible")

    def assertNotificationIsReal(self):
        note = self.stored()["notification"]
        self.assertIsNotNone(note)
        self.assertTrue(note["subject"].strip())
        self.assertGreaterEqual(len(note["bodyParagraphs"]), 2)
        self.assertTrue(note["whatsapp"].strip())
        self.assertTrue(note["ctaLabel"].strip())

    def assertNoEmoji(self):
        note = self.stored()["notification"]
        if not note:
            return
        blob = " ".join([note["subject"], note["whatsapp"]] + note["bodyParagraphs"])
        for ch in blob:
            self.assertLess(ord(ch), 0x2190, "emoji in copy: {!r}".format(ch))


class TestNasywaReminder(GoldenCartCase):
    """wf-03 Premium, campaign share 9%. The gate closes on the price-sensitivity
    axis even though the cart runs over usual spend. This is the differentiator:
    a traveler price is not blocking gets no discount."""

    traveler_id = "wf-03"

    def test_outcome_is_reminder(self):
        self.assertEqual(self.stored()["decision"]["outcome"], Outcome.REMINDER)

    def test_gate_closed_on_campaign_share_not_budget(self):
        gate = self.stored()["gate"]
        self.assertFalse(gate["opened"])
        self.assertFalse(gate["priceSensitive"])
        self.assertTrue(gate["overBudget"], "the cart IS over budget; the other axis closed it")

    def test_price_is_untouched(self):
        d = self.stored()["decision"]
        self.assertEqual(d["savingIdr"], 0)
        self.assertEqual(d["finalTotalIdr"], self.stored()["originalTotalIdr"])

    def test_still_gets_a_real_notification(self):
        """A reminder is a decision, not an absence. It gets a full message."""
        self.assertNotificationIsReal()

    def test_matches_fresh_run(self):
        self.assertMatchesFreshRun()

    def test_no_margin_conceded(self):
        self.assertNoMarginConceded()


class TestSalsabillaReminder(GoldenCartCase):
    """wf-08 Premium, campaign share 11%. The seed's second low-share Premium
    traveler, and the second refusal to discount. Kept as its own case because
    one reminder could be a fluke of a single cart's arithmetic; two, at the
    same tier and from the same axis, is the rule working."""

    traveler_id = "wf-08"

    def test_outcome_is_reminder(self):
        self.assertEqual(self.stored()["decision"]["outcome"], Outcome.REMINDER)

    def test_gate_closed_on_campaign_share(self):
        gate = self.stored()["gate"]
        self.assertFalse(gate["opened"])
        self.assertFalse(gate["priceSensitive"])

    def test_still_gets_a_real_notification(self):
        self.assertNotificationIsReal()

    def test_matches_fresh_run(self):
        self.assertMatchesFreshRun()

    def test_no_margin_conceded(self):
        self.assertNoMarginConceded()


class TestZhillanRebuild(GoldenCartCase):
    """wf-02 Comfort, campaign share 48%. Both axes agree, and the ladder has to
    walk to the last rung before anything clears tau = 10%."""

    traveler_id = "wf-02"

    def test_outcome_is_rebuild(self):
        self.assertEqual(self.stored()["decision"]["outcome"], Outcome.REBUILD)

    def test_gate_opened_on_both_axes(self):
        gate = self.stored()["gate"]
        self.assertTrue(gate["opened"])
        self.assertTrue(gate["priceSensitive"])
        self.assertTrue(gate["overBudget"])

    def test_genuinely_clears_the_comfort_threshold(self):
        """tau(Comfort) = 10%. Constructed to clear, never back-fitted."""
        d = self.stored()["decision"]
        self.assertEqual(d["clearedRung"], config.RUNG_TIER_DOWN)
        self.assertGreaterEqual(d["savingPct"], config.TAU[config.TIER_COMFORT])

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


class TestZayyanLateral(GoldenCartCase):
    """wf-05 Comfort. A same-star swap clears on rung 02, so the ladder stops
    before any downgrade -- the traveler keeps the class of trip they chose."""

    traveler_id = "wf-05"

    def test_outcome_is_lateral_not_rebuild(self):
        self.assertEqual(self.stored()["decision"]["outcome"], Outcome.LATERAL)

    def test_stopped_at_the_lateral_rung(self):
        d = self.stored()["decision"]
        self.assertEqual(d["clearedRung"], config.RUNG_LATERAL)
        self.assertEqual(len(d["attempts"]), 2, "tier-down must never have been priced")

    def test_star_rating_is_unchanged(self):
        """The whole point of a lateral: same star, different property."""
        winner = next(a for a in self.stored()["decision"]["attempts"] if a["cleared"])
        self.assertEqual(winner["hotel"]["stars"], 4)

    def test_matches_fresh_run(self):
        self.assertMatchesFreshRun()

    def test_no_margin_conceded(self):
        self.assertNoMarginConceded()


class TestAdrianoColdStartAlternative(GoldenCartCase):
    """wf-04 One booking. Campaign share is unmeasurable, the tier comes from the
    cart, the ladder still runs because a rebuild concedes nothing -- and when
    no rung clears, a different trip is proposed rather than a discount.

    The design bundle prints a 45% campaign share for this traveler. One booking
    is no history to compute a share from, so it stays null here."""

    traveler_id = "wf-04"

    def test_campaign_share_is_null_never_fabricated(self):
        self.assertIsNone(self.stored()["gate"]["campaignShare"])
        self.assertIsNone(self.stored()["gate"]["priceSensitive"])

    def test_tier_came_from_the_cart_not_history(self):
        self.assertEqual(self.stored()["classification"]["tierSource"], "cart_proxy")
        self.assertTrue(self.stored()["classification"]["isColdStart"])

    def test_ladder_still_ran_under_the_exception(self):
        """Rebuild concedes no margin, so a weaker signal can still justify it."""
        self.assertTrue(self.stored()["gate"]["coldStartException"])
        self.assertTrue(self.stored()["gate"]["opened"])
        self.assertEqual(len(self.stored()["decision"]["attempts"]), 3)

    def test_outcome_is_alternative(self):
        self.assertEqual(self.stored()["decision"]["outcome"], Outcome.ALTERNATIVE)
        self.assertIsNone(self.stored()["decision"]["clearedRung"])

    def test_matches_fresh_run(self):
        self.assertMatchesFreshRun()

    def test_no_margin_conceded(self):
        self.assertNoMarginConceded()


class TestDariusAlternative(GoldenCartCase):
    """wf-09 Comfort. The gate opens on both axes, every rung is priced, and none
    of them reaches tau. Falls through to a different trip."""

    traveler_id = "wf-09"

    def test_outcome_is_alternative(self):
        self.assertEqual(self.stored()["decision"]["outcome"], Outcome.ALTERNATIVE)

    def test_gate_opened_but_nothing_cleared(self):
        self.assertTrue(self.stored()["gate"]["opened"])
        self.assertIsNone(self.stored()["decision"]["clearedRung"])

    def test_every_rung_was_priced_and_reported(self):
        """The rungs that missed are the evidence restraint was earned."""
        attempts = self.stored()["decision"]["attempts"]
        self.assertEqual(len(attempts), 3)
        for a in attempts:
            self.assertTrue(a["available"], a["rung"])
            self.assertFalse(a["cleared"], a["rung"])
            self.assertLess(a["delta"], config.TAU[config.TIER_COMFORT])

    def test_matches_fresh_run(self):
        self.assertMatchesFreshRun()

    def test_no_margin_conceded(self):
        self.assertNoMarginConceded()


class TestChristianoUpstreamFailure(GoldenCartCase):
    """wf-06 Carrier inventory unavailable. A pipeline over live inventory will
    fail sometimes, and a demo that cannot show it is dishonest."""

    traveler_id = "wf-06"

    def test_outcome_is_error(self):
        self.assertEqual(self.stored()["decision"]["outcome"], Outcome.ERROR)

    def test_classifier_still_completed(self):
        stages = {t["stage"]: t["durationMs"] for t in self.stored()["timings"]}
        self.assertGreater(stages["classifier"], 0)
        self.assertTrue(self.stored()["classification"]["reasoning"])

    def test_no_notification_is_drafted(self):
        self.assertIsNone(self.stored()["notification"])

    def test_gate_still_evaluates_because_p0_is_known(self):
        """p_0 is the abandonment price and does not depend on today's
        inventory, so losing the carrier feed does not cost us the gate. Both
        signals are still measurable; only the rebuild search is impossible.
        That matches the paper's error narrative -- the classifier completed,
        the searcher halted -- rather than blanking the whole trace."""
        gate = self.stored()["gate"]
        self.assertTrue(gate["opened"])
        self.assertTrue(gate["priceSensitive"])
        self.assertGreater(gate["budgetGap"], 0)

    def test_no_rebuild_was_attempted(self):
        self.assertEqual(self.stored()["decision"]["attempts"], [])

    def test_no_deadline_is_shown(self):
        self.assertDeadlineOnlyIfGuaranteed()


class TestGoldenCoverage(unittest.TestCase):
    """Structural assertions over the file itself -- not pipeline runs."""

    def test_all_four_outcomes_plus_error_are_covered(self):
        seen = {r["decision"]["outcome"] for r in GOLD["results"].values()}
        self.assertEqual(seen, {Outcome.REBUILD, Outcome.LATERAL, Outcome.REMINDER,
                                Outcome.ALTERNATIVE, Outcome.ERROR})

    def test_the_two_axis_rule_holds_across_the_whole_seed(self):
        """The thesis, asserted over the file rather than over one lucky pair.

        Reading a stored fixture is not a bulk run: nothing is executed here.
        Every traveler with a measurable share below c* must have been refused
        an intervention, and every one at or above it with an over-budget cart
        must have had the ladder run. One counterexample and the product is a
        single-axis discounter wearing two axes."""
        for tid, r in GOLD["results"].items():
            gate = r["gate"]
            share = gate["campaignShare"]
            if share is None:
                continue  # cold start runs under its own stated exception
            if share < config.C_STAR:
                self.assertFalse(gate["opened"], "{} opened below c*".format(tid))
                self.assertEqual(r["decision"]["outcome"], Outcome.REMINDER, tid)
            elif gate["budgetGap"] > 0:
                self.assertTrue(gate["opened"], "{} closed with both axes met".format(tid))

    def test_no_outcome_ever_concedes_margin(self):
        for tid, r in GOLD["results"].items():
            self.assertEqual(r["decision"]["marginConcededIdr"], 0, tid)

    def test_queue_withholds_the_reasoned_verdict(self):
        """Browse cards carry the provisional estimate (tier, campaign share);
        the Classifier's reasoned verdict is not pre-announced."""
        for entry in GOLD["queue"]:
            self.assertNotIn("outcome", entry)
            self.assertNotIn("reasoning", entry)


if __name__ == "__main__":
    unittest.main()
