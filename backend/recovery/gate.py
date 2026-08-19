"""
gate.py — The two-axis intervention test (paper §4.1).

    D_i = rebuild ladder   iff   c_i >= c*  AND  g_i > 0
          reminder, no discount               otherwise

Both conditions, always. A high campaign share on a cart the traveler can
comfortably afford is not a reason to intervene, and a cart over budget held by
someone who never waits for a promo is not either. The conjunction is the whole
argument: it is what stops margin being spent on travelers who would convert
anyway, and what stops a downgrade being offered to someone who did not want one.

A note on the paper's stated justification. Section 4.1 defends this gate on
margin grounds, but section 2.3.1 also insists a rebuild concedes no margin at
all -- both cannot be true. The gate is right; the reason is relevance, not
margin. Proposing a 4-star-to-3-star downgrade to a traveler who books
full-fare 5-star is an insult, and per Rzepakowski and Jaroszewicz it risks
negative uplift on exactly the high-value segment you can least afford to annoy.
"""
from __future__ import annotations

from . import config
from .schemas import GateResult, TravelerHistory


def budget_gap(cart_total_idr: int, usual_spend: int) -> float:
    """
    g_i = (p_0 - s_bar_i) / s_bar_i. Positive means the cart sits above what
    this traveler usually spends per trip.
    """
    if usual_spend <= 0:
        raise ValueError("usual_spend must be positive to compute a budget gap")
    return (cart_total_idr - usual_spend) / usual_spend


def evaluate(history: TravelerHistory, cart_total_idr: int) -> GateResult:
    gap = budget_gap(cart_total_idr, history.usual_spend)
    over_budget = gap > 0
    share = history.campaign_share

    # Cold start (paper section 3.2.5, as amended).
    # campaign_share is None, so c_i >= c* cannot be evaluated. Read literally,
    # the conjunction would fail and every cold-start cart would fall to
    # reminder -- which would make the whole cart-proxy stage dead code, since
    # the proxy tier could then never change an outcome.
    #
    # The exception: a cold-start cart may walk the ladder. A rebuild is
    # composition change, not concession, so it costs nothing to offer on a
    # weaker signal. What cold start cannot justify is a margin-costing action,
    # and this build issues none, so the restriction is free.
    if share is None:
        if not config.COLD_START_MAY_REBUILD:
            return GateResult(
                opened=False, campaign_share=None, budget_gap=gap,
                price_sensitive=None, over_budget=over_budget,
                reason="No booking history; price sensitivity unmeasurable.",
                cold_start_exception=True,
            )
        return GateResult(
            opened=True, campaign_share=None, budget_gap=gap,
            price_sensitive=None, over_budget=over_budget,
            reason=(
                "No booking history, so price sensitivity is unmeasurable. The "
                "ladder still runs on the cart-derived tier because a rebuild "
                "concedes no margin; no discount is available on this path."
            ),
            cold_start_exception=True,
        )

    price_sensitive = share >= config.C_STAR

    if price_sensitive and over_budget:
        reason = (
            "Campaign share {:.0%} is at or above the {:.0%} bar and the cart "
            "sits {:.0%} above usual spend. Both signals agree, so a rebuild "
            "is worth attempting."
        ).format(share, config.C_STAR, gap)
        return GateResult(True, share, gap, True, over_budget, reason)

    # Closed. Say which axis closed it -- the trace has to be arguable.
    if not price_sensitive and not over_budget:
        reason = (
            "Campaign share {:.0%} is below the {:.0%} bar and the cart is "
            "within usual spend. Neither signal points at price; a reminder is "
            "the correct action."
        ).format(share, config.C_STAR)
    elif not price_sensitive:
        reason = (
            "The cart sits {:.0%} above usual spend, but campaign share {:.0%} "
            "is below the {:.0%} bar -- this traveler historically pays full "
            "price. Price is not the barrier."
        ).format(gap, share, config.C_STAR)
    else:
        reason = (
            "Campaign share {:.0%} is above the {:.0%} bar, but the cart is "
            "within usual spend. A high campaign share alone does not justify "
            "an intervention."
        ).format(share, config.C_STAR)
    return GateResult(False, share, gap, price_sensitive, over_budget, reason)
