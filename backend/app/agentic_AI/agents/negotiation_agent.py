"""
backend/agentic_AI/agents/negotiation_agent.py

Negotiation agent subgraph. Chats with the dispatched vendor, extracts a price,
and either auto-approves it against the PM's ceiling or hands the PM a decision.

    START → open_negotiation → await_vendor_reply ⏸ → interpret_reply
                                      ↑                      │
                                      │                      ├─ no price → post_ai_reply ─┐
                                      └──────────────────────┴────────────────────────────┘
                                                             ├─ declined  → close_negotiation → END
                                                             └─ price     → evaluate_quote
                                                                   ├─ under ceiling → confirm_job → END
                                                                   └─ otherwise → notify_pm_quote
                                                                          → await_pm_decision ⏸
                                                                             ├─ accept  → confirm_job
                                                                             ├─ counter → send_counter (max 1)
                                                                             └─ next    → close_negotiation

Two pause points, both `interrupt()`. Compiled at import with no checkpointer
and embedded as a node in a parent graph that owns one — exactly like
intake_graph and dispatch_graph.
"""
import logging

from langgraph.graph import StateGraph, START, END

from app.agentic_AI.ticket_state import TicketState
from app.agentic_AI.nodes.negotiation import (
    await_pm_decision_node,
    await_vendor_reply_node,
    close_negotiation_node,
    confirm_job_node,
    evaluate_quote_node,
    interpret_reply_node,
    notify_pm_quote_node,
    open_negotiation_node,
    post_ai_reply_node,
    route_after_evaluate,
    route_after_interpret,
    route_after_pm_decision,
    send_counter_node,
)

logger = logging.getLogger(__name__)

builder = StateGraph(TicketState)

builder.add_node("open_negotiation", open_negotiation_node)
builder.add_node("await_vendor_reply", await_vendor_reply_node)
builder.add_node("interpret_reply", interpret_reply_node)
builder.add_node("post_ai_reply", post_ai_reply_node)
builder.add_node("evaluate_quote", evaluate_quote_node)
builder.add_node("notify_pm_quote", notify_pm_quote_node)
builder.add_node("await_pm_decision", await_pm_decision_node)
builder.add_node("send_counter", send_counter_node)
builder.add_node("confirm_job", confirm_job_node)
builder.add_node("close_negotiation", close_negotiation_node)

builder.add_edge(START, "open_negotiation")
builder.add_edge("open_negotiation", "await_vendor_reply")
builder.add_edge("await_vendor_reply", "interpret_reply")

builder.add_conditional_edges(
    "interpret_reply",
    route_after_interpret,
    {
        "post_ai_reply": "post_ai_reply",
        "evaluate_quote": "evaluate_quote",
        "close": "close_negotiation",
    },
)
# The chat loop. Bounded by MAX_CHAT_TURNS in route_after_interpret — without
# that cap this cycle trips LangGraph's recursion limit and the ticket dies with
# nothing user-visible to explain it.
builder.add_edge("post_ai_reply", "await_vendor_reply")

builder.add_conditional_edges(
    "evaluate_quote",
    route_after_evaluate,
    {
        "confirm_job": "confirm_job",
        "notify_pm": "notify_pm_quote",
    },
)
builder.add_edge("notify_pm_quote", "await_pm_decision")
builder.add_conditional_edges(
    "await_pm_decision",
    route_after_pm_decision,
    {
        "confirm_job": "confirm_job",
        "send_counter": "send_counter",
        "close": "close_negotiation",
        # A resume that carried no usable decision sits back down rather than
        # guessing what the PM meant.
        "await_pm_decision": "await_pm_decision",
    },
)
# The counter loop, capped at MAX_COUNTER_ROUNDS.
builder.add_edge("send_counter", "await_vendor_reply")

builder.add_edge("confirm_job", END)
builder.add_edge("close_negotiation", END)

negotiation_graph = builder.compile()


def get_negotiation_graph(checkpointer=None):
    """
    A standalone negotiation graph on its own checkpointer.

    Used by the rebuild-from-DB fallback, when the parent graph's checkpoint has
    expired but the negotiation is still live in Postgres.
    """
    return builder.compile(checkpointer=checkpointer)
