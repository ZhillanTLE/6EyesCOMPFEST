"""
Golden-fixture tests.

The committed golden.json is what the frontend builds against, so its shape and
its coverage are both contractual. These tests fail loudly if a backend change
silently moves an outcome.
"""
import json
import os
import unittest

os.environ.setdefault("WINDFALL_FIXTURES", "1")

from backend.recovery import pipeline, repository  # noqa: E402
from backend.recovery.schemas import Outcome  # noqa: E402

GOLDEN = os.path.join(os.path.dirname(__file__), "..", "recovery", "seed", "golden.json")


class TestGolden(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(GOLDEN, encoding="utf-8") as fh:
            cls.golden = json.load(fh)

    def test_covers_all_four_outcomes_plus_error(self):
        seen = {r["decision"]["outcome"] for r in self.golden["results"].values()}
        self.assertEqual(
            seen,
            {Outcome.REBUILD, Outcome.LATERAL, Outcome.REMINDER,
             Outcome.ALTERNATIVE, Outcome.ERROR},
        )

    def test_matches_a_fresh_pipeline_run(self):
        """Regenerating must be a no-op. If this fails, either the fixture is
        stale or the pipeline changed -- both need a human to look."""
        for traveler_id, stored in self.golden["results"].items():
            fresh = pipeline.run(traveler_id).to_dict()
            self.assertEqual(fresh["decision"]["outcome"],
                             stored["decision"]["outcome"], traveler_id)
            self.assertEqual(fresh["decision"]["final_total_idr"],
                             stored["decision"]["final_total_idr"], traveler_id)

    def test_every_traveler_hits_its_calibration_target(self):
        """The seed was constructed to exercise one path each. If live prices
        drift a traveler off its target, that is a seed problem to fix in the
        seed -- never by adjusting the arithmetic."""
        for row in repository.all_travelers():
            target = row["calibration_target"]
            outcome = self.golden["results"][row["traveler_id"]]["decision"]["outcome"]
            if target == "cold_start":
                self.assertTrue(
                    self.golden["results"][row["traveler_id"]]["gate"]["cold_start_exception"],
                    row["name"])
            else:
                self.assertEqual(outcome, target, row["name"])

    def test_no_result_concedes_margin(self):
        for tid, r in self.golden["results"].items():
            self.assertEqual(r["decision"]["margin_conceded_idr"], 0, tid)

    def test_deadline_only_when_carrier_guarantees_it(self):
        """No fake countdowns: an expiry may exist only on an eligible hold."""
        for tid, r in self.golden["results"].items():
            hold = r["hold"]
            if hold["expires_at"]:
                self.assertEqual(hold["state"], "eligible", tid)

    def test_queue_withholds_tier_and_campaign_share(self):
        """The browse card must not pre-announce the Classifier's conclusion."""
        for entry in self.golden["queue"]:
            for banned in ("tier", "campaign_share", "usual_spend", "outcome"):
                self.assertNotIn(banned, entry, entry["name"])

    def test_timings_are_present_and_positive_for_completed_runs(self):
        for tid, r in self.golden["results"].items():
            stages = {t["stage"]: t["duration_ms"] for t in r["timings"]}
            self.assertIn("classifier", stages, tid)
            self.assertGreater(stages["classifier"], 0, tid)
            if r["decision"]["outcome"] != Outcome.ERROR:
                self.assertGreater(stages["notifier"], 0, tid)

    def test_notification_exists_for_every_non_error_outcome(self):
        """Reminder gets a real drafted message like every other outcome. It is
        a decision, not an absence, and an empty preview would say otherwise."""
        for tid, r in self.golden["results"].items():
            if r["decision"]["outcome"] == Outcome.ERROR:
                continue
            note = r["notification"]
            self.assertIsNotNone(note, tid)
            self.assertTrue(note["subject"].strip(), tid)
            self.assertGreaterEqual(len(note["body_paragraphs"]), 2, tid)
            self.assertTrue(note["whatsapp"].strip(), tid)
            self.assertTrue(note["cta_label"].strip(), tid)

    def test_no_emoji_in_traveler_facing_copy(self):
        for tid, r in self.golden["results"].items():
            note = r["notification"]
            if not note:
                continue
            blob = " ".join([note["subject"], note["whatsapp"]] + note["body_paragraphs"])
            for ch in blob:
                self.assertLess(ord(ch), 0x2190, "emoji in {}: {!r}".format(tid, ch))


if __name__ == "__main__":
    unittest.main()
