"""
Agent-layer tests.

What matters here is not that the model is clever -- it is that the model
cannot exceed its authority, and that its absence is survivable and visible.
"""
import os
import unittest

os.environ.setdefault("WINDFALL_FIXTURES", "1")

from backend.recovery import (classifier_agent, config, gate, llm,  # noqa: E402
                              notification_curator, pipeline, repository,
                              searcher_agent, tiers)


class TestInferenceGating(unittest.TestCase):
    """Three separate reasons a call does not happen, each survivable."""

    def setUp(self):
        self._env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_fixtures_replace_inference(self):
        os.environ["WINDFALL_FIXTURES"] = "1"
        os.environ["GEMINI_API_KEY"] = "irrelevant"
        self.assertFalse(llm.available())
        self.assertIn("captured run", llm.why_unavailable())

    def test_mock_llm_replaces_inference(self):
        os.environ["MOCK_LLM"] = "true"
        self.assertFalse(llm.available())
        self.assertEqual(llm.why_unavailable(), "MOCK_LLM=true")

    def test_missing_key_is_survivable_not_fatal(self):
        """A clean clone with no credentials must still produce a working demo."""
        os.environ["WINDFALL_FIXTURES"] = "0"
        os.environ["MOCK_LLM"] = "false"
        os.environ["GEMINI_API_KEY"] = ""
        self.assertFalse(llm.available())
        self.assertIsNone(llm.complete_json("system", {"a": 1}))


class TestClassifierAuthority(unittest.TestCase):
    """The agent reasons a tier; it does not get to replace the calibration."""

    def test_one_step_moves_are_allowed(self):
        self.assertTrue(classifier_agent._one_step_apart("Value", "Comfort"))
        self.assertTrue(classifier_agent._one_step_apart("Comfort", "Premium"))
        self.assertTrue(classifier_agent._one_step_apart("Premium", "Premium"))

    def test_two_step_jumps_are_not(self):
        """A model able to jump Value to Premium could quietly replace the
        percentile calibration with its own judgement."""
        self.assertFalse(classifier_agent._one_step_apart("Value", "Premium"))

    def test_falls_back_to_the_prior_when_inference_is_unavailable(self):
        history, row = repository.get("wf-02")
        cart = repository.build_cart(row, 26000000, 45000000)
        g = gate.evaluate(history, cart.total_idr)
        result = classifier_agent.classify(
            history, cart, tier_prior="Premium", tier_source="history",
            gate_result=g, reference_spend=repository.reference_spend())
        self.assertEqual(result.tier, "Premium")
        self.assertEqual(result.tier_prior, "Premium")
        self.assertTrue(result.reasoning)

    def test_provenance_is_reported_not_hidden(self):
        """A template must never be mistaken for inference in the trace."""
        history, row = repository.get("wf-01")
        cart = repository.build_cart(row, 41000000, 25000000)
        result = classifier_agent.classify(
            history, cart, "Premium", "history",
            gate.evaluate(history, cart.total_idr), repository.reference_spend())
        self.assertTrue(result.reasoned_by.startswith("deterministic"))

    def test_reasoning_asymmetry_survives_the_agent_layer(self):
        """Two lines for an intervention, one for a reminder. Padding the
        reminder would imply deliberation that did not happen."""
        rebuild = pipeline.run("wf-02").classification.reasoning
        reminder = pipeline.run("wf-01").classification.reasoning
        self.assertEqual(len(rebuild), 2)
        self.assertEqual(len(reminder), 1)


class TestSearcherAuthority(unittest.TestCase):
    def test_returns_nothing_rather_than_inventing_judgement(self):
        """With no model there is no comparability opinion to give. A template
        pretending to be judgement would be worse than silence."""
        history, row = repository.get("wf-02")
        cart = repository.build_cart(row, 26000000, 45000000)
        result = pipeline.run("wf-02")
        self.assertEqual(
            searcher_agent.assess(cart, "Premium", 0.15, result.decision.attempts),
            {})

    def test_cannot_overturn_the_arithmetic(self):
        """`cleared` comes from ladder.py and is not in the agent's gift."""
        result = pipeline.run("wf-02")
        winner = [a for a in result.decision.attempts if a.cleared]
        self.assertEqual(len(winner), 1)
        self.assertGreaterEqual(winner[0].delta, config.TAU["Premium"])


class TestCuratorBoundary(unittest.TestCase):
    def test_receives_a_decided_outcome_and_cannot_change_it(self):
        result = pipeline.run("wf-03")
        draft = notification_curator.curate(
            repository.build_cart(repository.get("wf-03")[1], 13000000, 18000000),
            "Bagus Hartono", result.decision, result.hold, "Comfort")
        self.assertIsNotNone(draft.subject)
        # The draft describes; the outcome is unchanged by describing it.
        self.assertEqual(pipeline.run("wf-03").decision.outcome, result.decision.outcome)

    def test_no_emoji_survives_the_cleaner(self):
        self.assertEqual(notification_curator._clean("Halo \U0001F44B Anda"), "Halo  Anda")

    def test_provenance_is_reported(self):
        result = pipeline.run("wf-01")
        self.assertTrue(result.notification.written_by.startswith("deterministic"))


if __name__ == "__main__":
    unittest.main()
