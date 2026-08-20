"""
Sending tests.

The rules under test are the ones with real-world consequences: reading a
trace must not send anything, every send must route to the demo inbox, and
suppression must never be reported as success.
"""
import os
import unittest

os.environ.setdefault("WINDFALL_FIXTURES", "1")
os.environ.setdefault("AUTH_DISABLED", "true")

from backend.app import app  # noqa: E402
from backend.recovery import sender  # noqa: E402


class TestSendingBoundary(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()
        self._env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_running_the_pipeline_sends_nothing(self):
        """The load-bearing separation. Clicking through six travelers to read
        their traces must not deliver six emails."""
        calls = []
        original = sender.send_email
        sender.send_email = lambda *a, **k: calls.append(a)
        try:
            self.c.post("/api/recovery/run", json={"travelerId": "wf-02"})
        finally:
            sender.send_email = original
        self.assertEqual(calls, [])

    def test_suppressed_is_not_reported_as_sent(self):
        os.environ["SEND_ENABLED"] = "false"
        body = self.c.post("/api/recovery/send", json={"travelerId": "wf-01"}).get_json()
        self.assertEqual(body["state"], "suppressed")
        self.assertNotEqual(body["state"], "sent")

    def test_refuses_to_send_without_a_demo_recipient(self):
        """Seeded travelers have invented addresses; delivering to them bounces."""
        os.environ["SEND_ENABLED"] = "true"
        os.environ["DEMO_RECIPIENT"] = ""
        r = self.c.post("/api/recovery/send", json={"travelerId": "wf-01"})
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.get_json()["state"], "failed")

    def test_whatsapp_is_always_declared_preview_only(self):
        os.environ["SEND_ENABLED"] = "false"
        body = self.c.post("/api/recovery/send", json={"travelerId": "wf-03"}).get_json()
        self.assertEqual(body["whatsapp"]["state"], "preview_only")

    def test_nothing_to_send_on_the_error_path(self):
        r = self.c.post("/api/recovery/send", json={"travelerId": "wf-06"})
        self.assertEqual(r.status_code, 409)

    def test_fixtures_do_not_disable_delivery(self):
        """WINDFALL_FIXTURES replaces inference, not delivery. If fixtures
        silently disabled sending, judging day could not prove it works."""
        os.environ["WINDFALL_FIXTURES"] = "1"
        os.environ["SEND_ENABLED"] = "true"
        os.environ["DEMO_RECIPIENT"] = "demo@example.test"
        os.environ["SMTP_HOST"] = ""
        body = self.c.post("/api/recovery/send", json={"travelerId": "wf-01"}).get_json()
        # Fails on transport, not on a fixture guard -- delivery was attempted.
        self.assertEqual(body["state"], "failed")
        self.assertIn("SMTP_HOST", body["detail"])

    def test_missing_traveler_id_400(self):
        self.assertEqual(self.c.post("/api/recovery/send", json={}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
