"""
backend/agentic_AI/agents/orchestration_agent.py
"""
import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, START, END
from langgraph.graph.graph import CompiledGraph

from agentic_AI.ticket_state import TicketState
from agentic_AI.agents.intake_agent import intake_graph
from database import SessionLocal
from models.notification import Notification

logger = logging.getLogger(__name__)

async def notify_pm_node(state: TicketState) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        import uuid
        notification = Notification(
            id=uuid.uuid4(),
            user_id=uuid.UUID(state.pm_id),
            type="TICKET_PENDING_APPROVAL",
            title="Ticket needs your approval",
            message=state.ai_summary or "A new ticket requires review",
            is_read=False
        )
        db.add(notification)
        
        from models.ticket import Ticket
        ticket = db.get(Ticket, state.ticket_id)
        if ticket:
            ticket.status = "PENDING_APPROVAL"
            
        db.commit()
        return {"current_status": "PENDING_APPROVAL"}
    except Exception as e:
        db.rollback()
        logger.exception("notify_pm_node error for ticket %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()

async def trigger_dispatch_node(state: TicketState) -> Dict[str, Any]:
    logger.info("trigger_dispatch_node placeholder executing")
    return {"current_status": "DISPATCHING"}

def route_after_intake(state: TicketState) -> str:
    if state.error is not None:
        return END
    if state.requires_pm_approval is False:
        return "dispatch"
    return "notify_pm"

builder = StateGraph(TicketState)

builder.add_node("intake", intake_graph)
builder.add_node("notify_pm", notify_pm_node)
builder.add_node("trigger_dispatch_node", trigger_dispatch_node)

builder.add_edge(START, "intake")
builder.add_conditional_edges(
    "intake",
    route_after_intake,
    {
        END: END,
        "dispatch": "trigger_dispatch_node",
        "notify_pm": "notify_pm"
    }
)
builder.add_edge("notify_pm", END)
builder.add_edge("trigger_dispatch_node", END)

def get_parent_graph(checkpointer=None) -> CompiledGraph:
    return builder.compile(checkpointer=checkpointer)
