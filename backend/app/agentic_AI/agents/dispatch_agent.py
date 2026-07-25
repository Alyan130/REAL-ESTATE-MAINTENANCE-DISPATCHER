"""
backend/agentic_AI/agents/dispatch_agent.py

Dispatch agent subgraph. Selects the best vendor for a ready-to-act ticket and
sends the job offer; escalates to the PM when no vendor is available.

    START → select_vendor ─(route)→ dispatch_job   → END
                             └─────→ escalate_to_pm → END

Compiled at import (no checkpointer) and embedded as a node in the parent
orchestration graph, exactly like intake_graph.
"""
import logging

from langgraph.graph import StateGraph, START, END

from app.agentic_AI.ticket_state import TicketState
from app.agentic_AI.nodes.dispatch import (
    dispatch_job_node,
    escalate_to_pm_node,
    route_after_selection,
    select_vendor_node,
)

logger = logging.getLogger(__name__)

builder = StateGraph(TicketState)
builder.add_node("select_vendor", select_vendor_node)
builder.add_node("dispatch_job", dispatch_job_node)
builder.add_node("escalate_to_pm", escalate_to_pm_node)

builder.add_edge(START, "select_vendor")
builder.add_conditional_edges(
    "select_vendor",
    route_after_selection,
    {
        "dispatch_job": "dispatch_job",
        "escalate": "escalate_to_pm",
    },
)
builder.add_edge("dispatch_job", END)
builder.add_edge("escalate_to_pm", END)

dispatch_graph = builder.compile()
