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

    def test_live_mode_without_a_key_is_refused_not_faked(self):
        """
        The case this project must never get wrong.

        A live run with no key previously degraded to template prose, which
        renders identically to model output in a screenshot. It now refuses,
        so nobody can demonstrate "the AI" on an unconfigured machine.
        """
        os.environ["WINDFALL_FIXTURES"] = "0"
        os.environ["MOCK_LLM"] = "false"
        os.environ["GEMINI_API_KEY"] = ""
        self.assertTrue(llm.live_mode())
        self.assertFalse(llm.has_key())
        with self.assertRaises(llm.LiveInferenceUnavailable) as caught:
            llm.require_configured()
        message = str(caught.exception)
        self.assertIn("GEMINI_API_KEY", message)
        self.assertIn("WINDFALL_FIXTURES=1", message)

    def test_the_pipeline_itself_refuses_an_unconfigured_live_run(self):
        """The guard has to sit on the entry point, not just in the adapter."""
        os.environ["WINDFALL_FIXTURES"] = "0"
        os.environ["MOCK_LLM"] = "false"
        os.environ["GEMINI_API_KEY"] = ""
        with self.assertRaises(llm.LiveInferenceUnavailable):
            pipeline.run("wf-01")

    def test_declared_modes_are_still_allowed_to_run(self):
        """Refusing the unconfigured case must not break the two real modes."""
        os.environ["WINDFALL_FIXTURES"] = "1"
        os.environ["MOCK_LLM"] = "false"
        os.environ["GEMINI_API_KEY"] = ""
        llm.require_configured()  # fixtures: declared, allowed

        os.environ["WINDFALL_FIXTURES"] = "0"
        os.environ["MOCK_LLM"] = "true"
        llm.require_configured()  # mock: declared, allowed

    def test_a_configured_live_run_is_allowed(self):
        os.environ["WINDFALL_FIXTURES"] = "0"
        os.environ["MOCK_LLM"] = "false"
        os.environ["GEMINI_API_KEY"] = "a-key"
        llm.require_configured()
        self.assertTrue(llm.available())
        self.assertEqual(llm.why_unavailable(), "available")


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
        cart = repository.build_cart(row)
        g = gate.evaluate(history, cart.total_idr)
        result = classifier_agent.classify(
            history, cart, tier_prior="Premium", tier_source="history",
            gate_result=g, reference_spend=repository.reference_spend())
        self.assertEqual(result.tier, "Premium")
        self.assertEqual(result.tier_prior, "Premium")
        self.assertTrue(result.reasoning)

    def test_provenance_is_reported_not_hidden(self):
        """A template must never be mistaken for inference in the trace."""
        history, row = repository.get("wf-03")
        cart = repository.build_cart(row)
        result = classifier_agent.classify(
            history, cart, "Premium", "history",
            gate.evaluate(history, cart.total_idr), repository.reference_spend())
        self.assertTrue(result.reasoned_by.startswith("deterministic"))

    def test_reasoning_asymmetry_survives_the_agent_layer(self):
        """Two lines for an intervention, one for a reminder. Padding the
        reminder would imply deliberation that did not happen."""
        rebuild = pipeline.run("wf-02").classification.reasoning
        reminder = pipeline.run("wf-03").classification.reasoning
        self.assertEqual(len(rebuild), 2)
        self.assertEqual(len(reminder), 1)


class TestSearcherAuthority(unittest.TestCase):
    def test_returns_nothing_rather_than_inventing_judgement(self):
        """With no model there is no comparability opinion to give. A template
        pretending to be judgement would be worse than silence."""
        history, row = repository.get("wf-02")
        cart = repository.build_cart(row)
        result = pipeline.run("wf-02")
        self.assertEqual(
            searcher_agent.assess(cart, "Premium", 0.15, result.decision.attempts),
            {})

    def test_cannot_overturn_the_arithmetic(self):
        """`cleared` comes from ladder.py and is not in the agent's gift."""
        result = pipeline.run("wf-02")
        winner = [a for a in result.decision.attempts if a.cleared]
        self.assertEqual(len(winner), 1)
        self.assertGreaterEqual(winner[0].delta, config.TAU["Comfort"])


class TestCuratorBoundary(unittest.TestCase):
    def test_receives_a_decided_outcome_and_cannot_change_it(self):
        result = pipeline.run("wf-05")
        draft = notification_curator.curate(
            repository.build_cart(repository.get("wf-05")[1]),
            "Bagus Hartono", result.decision, result.hold, "Comfort")
        self.assertIsNotNone(draft.subject)
        # The draft describes; the outcome is unchanged by describing it.
        self.assertEqual(pipeline.run("wf-05").decision.outcome, result.decision.outcome)

    def test_no_emoji_survives_the_cleaner(self):
        self.assertEqual(notification_curator._clean("Halo \U0001F44B Anda"), "Halo  Anda")

    def test_provenance_is_reported(self):
        result = pipeline.run("wf-03")
        self.assertTrue(result.notification.written_by.startswith("deterministic"))


if __name__ == "__main__":
    unittest.main()


class TestFixtureAndLiveActuallyDiffer(unittest.TestCase):
    """
    The two modes must take different code paths.

    An earlier revision always used the fixture provider and only changed the
    `source` label, so WINDFALL_FIXTURES=0 dropped the "replaying capture"
    badge while still replaying the capture. That is exactly the failure the
    flag exists to prevent -- "cached for reliability" quietly becoming
    "faked" -- so it gets a test.
    """

    def setUp(self):
        self._env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        from backend.recovery import providers
        providers._fixtures = None

    def test_fixture_mode_replays_the_capture(self):
        os.environ["WINDFALL_FIXTURES"] = "1"
        result = pipeline.run("wf-02")
        self.assertEqual(result.source, "fixture")
        self.assertEqual(result.decision.outcome, "rebuild")

    def test_live_mode_without_travel_credentials_fails_rather_than_replaying(self):
        """With no keys the honest result is an upstream failure. Falling back
        to fixtures here would make live mode indistinguishable from replay.

        A Gemini key is set because this test is about the PRICE providers:
        without one the run is refused earlier, by the inference guard, and
        this assertion would never be reached.
        """
        os.environ["WINDFALL_FIXTURES"] = "0"
        os.environ["GEMINI_API_KEY"] = "set-so-the-inference-guard-passes"
        os.environ["DUFFEL_API_KEY"] = ""
        os.environ["RAPIDAPI_KEY"] = ""
        result = pipeline.run("wf-02")
        self.assertEqual(result.source, "live")
        self.assertEqual(result.decision.outcome, "error")
        # Crucially NOT the captured rebuild: no fixture leaked through.
        self.assertEqual(result.decision.saving_idr, 0)
