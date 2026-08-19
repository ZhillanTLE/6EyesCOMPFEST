"""
Endpoint tests for the recovery blueprint.

Beyond status codes, these pin the two properties that make the endpoint
compliant with the penyisihan scope rules: it is synchronous, and the whole
reasoning trace arrives in the response body rather than over a socket.
"""
import os
import unittest

os.environ.setdefault("WINDFALL_FIXTURES", "1")
os.environ.setdefault("AUTH_DISABLED", "true")

from backend.app import app  # noqa: E402


class TestRecoveryApi(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()

    def test_health(self):
        r = self.c.get("/api/recovery/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["service"], "windfall-recovery")

    def test_queue_returns_every_cart(self):
        body = self.c.get("/api/recovery/queue").get_json()
        self.assertEqual(len(body["queue"]), 6)

    def test_queue_withholds_classifier_conclusions(self):
        for entry in self.c.get("/api/recovery/queue").get_json()["queue"]:
            for banned in ("tier", "campaign_share", "usual_spend", "outcome"):
                self.assertNotIn(banned, entry)

    def test_run_returns_the_whole_trace_in_one_response(self):
        """No streaming, no follow-up call: everything the console renders has
        to be in this body."""
        body = self.c.post("/api/recovery/run", json={"traveler_id": "wf-03"}).get_json()
        for key in ("classification", "gate", "decision", "hold",
                    "notification", "timings", "original_total_idr", "source"):
            self.assertIn(key, body)
        self.assertTrue(body["classification"]["reasoning"])
        self.assertTrue(body["decision"]["attempts"])
        self.assertEqual(len(body["timings"]), 3)

    def test_failed_attempts_are_reported_not_hidden(self):
        """The rungs that missed are the evidence that restraint was earned."""
        body = self.c.post("/api/recovery/run", json={"traveler_id": "wf-02"}).get_json()
        attempts = body["decision"]["attempts"]
        self.assertGreater(len(attempts), 1)
        self.assertFalse(attempts[0]["cleared"])
        self.assertTrue(attempts[-1]["cleared"])

    def test_reminder_still_carries_a_full_notification(self):
        body = self.c.post("/api/recovery/run", json={"traveler_id": "wf-01"}).get_json()
        self.assertEqual(body["decision"]["outcome"], "reminder")
        self.assertIsNotNone(body["notification"])
        self.assertGreaterEqual(len(body["notification"]["body_paragraphs"]), 2)

    def test_error_path_returns_200_with_an_error_outcome(self):
        """An upstream inventory failure is a result the console renders, not
        an HTTP failure. Only a broken pipeline is a 5xx."""
        r = self.c.post("/api/recovery/run", json={"traveler_id": "wf-06"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["decision"]["outcome"], "error")

    def test_unknown_traveler_404(self):
        self.assertEqual(
            self.c.post("/api/recovery/run", json={"traveler_id": "nope"}).status_code, 404)

    def test_missing_body_400(self):
        self.assertEqual(self.c.post("/api/recovery/run", json={}).status_code, 400)

    def test_recovery_path_does_not_require_auth(self):
        """Rule 1 forbids complex authentication. The recovery blueprint has no
        auth decorator, unlike the older planning endpoints."""
        self.assertEqual(self.c.get("/api/recovery/queue").status_code, 200)

    def test_existing_endpoints_are_untouched(self):
        rules = {r.rule for r in app.url_map.iter_rules()}
        for rule in ("/api/health", "/api/plan-trip", "/api/swap-item"):
            self.assertIn(rule, rules)


if __name__ == "__main__":
    unittest.main()
