"""
Tests for the deterministic half of the negotiation agent.

These are the highest-value tests in the feature: everything here decides or
constrains money, none of it needs a database or a model, and all of it is the
kind of logic that fails silently in production. The conversational half is not
tested — it is non-deterministic by design, and running it is a better check
than mocking it.
"""
from decimal import Decimal

from app.agentic_AI.tools.negotiation import (
    MAX_CHAT_TURNS,
    MAX_COUNTER_ROUNDS,
    evaluate_auto_approve,
    followup_schedule_for,
    price_appears_in_text,
    suggest_counter,
)


# ─── evaluate_auto_approve ───────────────────────────────────────────────────


def test_approves_under_ceiling_when_model_recommends():
    decision = evaluate_auto_approve(
        price=180, ai_recommendation="approve", max_price=Decimal("400")
    )
    assert decision.approved is True


def test_rejects_over_ceiling_even_when_model_recommends():
    """The ceiling is the one thing the model does not get a vote on."""
    decision = evaluate_auto_approve(
        price=900, ai_recommendation="approve", max_price=Decimal("400")
    )
    assert decision.approved is False
    assert "900.00" in decision.reason and "400.00" in decision.reason


def test_rejects_when_model_defers_even_under_ceiling():
    """A conditional quote under the ceiling still needs a human."""
    decision = evaluate_auto_approve(
        price=200, ai_recommendation="send_to_pm", max_price=Decimal("400")
    )
    assert decision.approved is False


def test_never_approves_without_a_ceiling():
    """NULL max_price means the PM has not consented to any amount."""
    decision = evaluate_auto_approve(
        price=10, ai_recommendation="approve", max_price=None
    )
    assert decision.approved is False
    assert "ceiling" in decision.reason.lower()


def test_no_price_never_approves():
    decision = evaluate_auto_approve(
        price=None, ai_recommendation="approve", max_price=Decimal("400")
    )
    assert decision.approved is False


def test_price_exactly_at_ceiling_approves():
    decision = evaluate_auto_approve(
        price=400, ai_recommendation="approve", max_price=Decimal("400")
    )
    assert decision.approved is True


# ─── price_appears_in_text ───────────────────────────────────────────────────


def test_accepts_price_the_vendor_actually_said():
    assert price_appears_in_text(180, "I can do it for $180, Tuesday afternoon")


def test_accepts_comma_formatted_price():
    assert price_appears_in_text(1200.50, "It'll be $1,200.50 all in")


def test_accepts_bare_number():
    assert price_appears_in_text(250, "250 for the lot")


def test_accepts_other_currency_symbol():
    assert price_appears_in_text(300, "£300 including parts")


def test_rejects_price_the_vendor_never_said():
    """The failure this guard exists for: a figure inferred from vague words."""
    assert not price_appears_in_text(200, "sounds like about two hundred")


def test_rejects_a_different_number():
    assert not price_appears_in_text(500, "I can do it for $180")


def test_none_price_is_never_present():
    assert not price_appears_in_text(None, "$180")


# ─── suggest_counter ─────────────────────────────────────────────────────────


def test_no_counter_without_an_anchor():
    assert suggest_counter(quoted=500, anchor=None, max_price=Decimal("400")) is None


def test_no_counter_when_quote_already_at_or_below_anchor():
    assert suggest_counter(quoted=150, anchor=Decimal("180"), max_price=None) is None


def test_counter_never_exceeds_the_quote():
    counter = suggest_counter(
        quoted=200, anchor=Decimal("180"), max_price=Decimal("400")
    )
    assert counter is not None and counter <= Decimal("200")


def test_counter_never_exceeds_the_ceiling():
    counter = suggest_counter(
        quoted=900, anchor=Decimal("800"), max_price=Decimal("400")
    )
    assert counter is not None and counter <= Decimal("400")


def test_counter_rounds_to_nearest_five():
    counter = suggest_counter(quoted=900, anchor=Decimal("183"), max_price=None)
    assert counter is not None and counter % 5 == 0


# ─── follow-up schedule ──────────────────────────────────────────────────────


def test_emergency_is_chased_within_the_hour():
    assert followup_schedule_for("P1")[0] < 1


def test_minor_work_is_not_chased_for_a_day():
    assert followup_schedule_for("P4")[0] >= 24


def test_unknown_priority_falls_back_to_standard():
    assert followup_schedule_for(None) == followup_schedule_for("P3")
    assert followup_schedule_for("nonsense") == followup_schedule_for("P3")


def test_every_schedule_is_finite():
    """An unbounded chase would hound a vendor forever."""
    for priority in ("P1", "P2", "P3", "P4"):
        assert 0 < len(followup_schedule_for(priority)) <= 3


# ─── caps ────────────────────────────────────────────────────────────────────


def test_chat_turns_capped_below_langgraph_recursion_limit():
    """
    The chat loop is a cycle; LangGraph's default recursion limit is 25. Each
    turn costs roughly two supersteps, so the cap has to leave headroom or a
    chatty vendor kills the ticket with a GraphRecursionError.
    """
    assert MAX_CHAT_TURNS <= 12


def test_exactly_one_counter_round():
    assert MAX_COUNTER_ROUNDS == 1
