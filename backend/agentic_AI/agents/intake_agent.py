"""
backend/agentic_AI/agents/intake_agent.py
"""
import logging
from langgraph.graph import StateGraph, START, END

from agentic_AI.ticket_state import TicketState
from agentic_AI.nodes.intake import classify_node, persist_triage_node

logger = logging.getLogger(__name__)

builder = StateGraph(TicketState)
builder.add_node("classify_node", classify_node)
builder.add_node("persist_triage_node", persist_triage_node)

builder.add_edge(START, "classify_node")
builder.add_edge("classify_node", "persist_triage_node")
builder.add_edge("persist_triage_node", END)

intake_graph = builder.compile()
