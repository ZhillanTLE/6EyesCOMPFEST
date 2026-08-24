"""
MCP tool contract tests.

Paper section 5.1 names exactly four tools and stakes an architectural claim on
them: the data source behind a tool can be swapped without touching a prompt.
These tests pin the surface, and pin the one tool that must never appear.
"""
import asyncio
import os
import unittest

os.environ.setdefault("WINDFALL_FIXTURES", "1")

from backend.recovery import mcp_tools  # noqa: E402

PAPER_TOOLS = {
    "read_traveler_history",
    "search_flights",
    "search_hotels",
    "check_hold_eligibility",
}


class TestToolSurface(unittest.TestCase):
    def test_the_four_paper_tools_are_dispatchable(self):
        self.assertEqual(PAPER_TOOLS, set(mcp_tools.TOOLS))

    def test_create_hold_is_absent_and_stays_absent(self):
        """Placing a hold is a real write against airline inventory. A demo
        clicking through six carts must not place six holds."""
        self.assertNotIn("create_hold", mcp_tools.TOOLS)
        with self.assertRaises(KeyError):
            mcp_tools.call_tool("create_hold", cart_id="cart-wf-02")

    def test_the_mcp_server_exposes_the_same_four(self):
        """The stdio server and the in-process path must not drift apart --
        that shared implementation is what makes the contract claim true."""
        from backend import mcp_server
        names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
        self.assertTrue(PAPER_TOOLS <= names)
        self.assertNotIn("create_hold", names)


class TestReadTravelerHistory(unittest.TestCase):
    def test_returns_history_and_the_abandoned_cart(self):
        row = mcp_tools.call_tool("read_traveler_history", traveler_id="wf-02")
        self.assertEqual(row["travelerId"], "wf-02")
        self.assertIn("cart", row)
        self.assertGreater(row["usualSpend"], 0)

    def test_cold_start_campaign_share_is_null_through_the_tool(self):
        """Null must survive the tool boundary. Estimating it here would fake
        the price-sensitivity signal at exactly the point a future live data
        source would be swapped in."""
        row = mcp_tools.call_tool("read_traveler_history", traveler_id="wf-04")
        self.assertTrue(row["isColdStart"])
        self.assertIsNone(row["campaignShare"])

    def test_unknown_traveler_raises(self):
        with self.assertRaises(KeyError):
            mcp_tools.call_tool("read_traveler_history", traveler_id="nope")


class TestCheckHoldEligibility(unittest.TestCase):
    def test_eligible_carrier_yields_a_real_expiry(self):
        row = mcp_tools.call_tool("check_hold_eligibility",
                                  cart_id="cart-wf-01", carrier="ANA")
        self.assertEqual(row["state"], "eligible")
        self.assertTrue(row["expiresAt"])
        self.assertTrue(row["mayRenderDeadline"])

    def test_ineligible_carrier_yields_no_deadline_at_all(self):
        """No fake countdowns. Not a shorter one, not a softened one -- none."""
        row = mcp_tools.call_tool("check_hold_eligibility",
                                  cart_id="cart-wf-03", carrier="Emirates")
        self.assertEqual(row["state"], "not_eligible")
        self.assertIsNone(row["expiresAt"])
        self.assertFalse(row["mayRenderDeadline"])

    def test_scope_is_declared_flight_only(self):
        """The hotel has no equivalent primitive and re-prices at conversion.
        Callers must be able to say so rather than implying a frozen cart."""
        row = mcp_tools.call_tool("check_hold_eligibility",
                                  cart_id="cart-wf-05", carrier="British Airways")
        self.assertEqual(row["scope"], "flight_only")


if __name__ == "__main__":
    unittest.main()


class TestContractHoldsAcrossTheProcessBoundary(unittest.TestCase):
    """
    Paper section 5.1's architectural claim, made testable.

    The claim is that MCP is a real interface contract, not decoration: the
    same tool call produces the same result whether it runs in-process or over
    a real stdio session. If the two ever diverge, the claim is false and the
    "swap the data source without touching a prompt" argument goes with it.

    Spawns `python -m backend.mcp_server`, so it is slower than the rest of the
    suite. That cost buys a claim that would otherwise rest on assertion.
    """

    def setUp(self):
        self._env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def _both_paths(self, tool, **kwargs):
        os.environ["WINDFALL_MCP"] = ""
        in_process = mcp_tools.call_tool(tool, **kwargs)
        os.environ["WINDFALL_MCP"] = "stdio"
        over_stdio = mcp_tools.call_tool(tool, **kwargs)
        return in_process, over_stdio

    def test_read_traveler_history_agrees(self):
        a, b = self._both_paths("read_traveler_history", traveler_id="wf-02")
        self.assertEqual(a, b)

    def test_cold_start_null_survives_the_boundary(self):
        """Null is the easiest thing for a serialisation layer to quietly turn
        into 0, which would fabricate the price-sensitivity signal."""
        a, b = self._both_paths("read_traveler_history", traveler_id="wf-04")
        self.assertIsNone(a["campaignShare"])
        self.assertIsNone(b["campaignShare"])

    def test_hold_eligibility_agrees(self):
        a, b = self._both_paths("check_hold_eligibility",
                                cart_id="cart-wf-01", carrier="ANA")
        self.assertEqual(a, b)
        self.assertEqual(a["state"], "eligible")
