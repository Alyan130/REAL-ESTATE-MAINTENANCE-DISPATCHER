"""
backend/agentic_AI/agents/orchestration_agent.py
"""
import logging
from datetime import datetime
from typing import Dict, Any

from langgraph.graph import StateGraph, START, END
# langgraph 1.x dropped langgraph.graph.graph.CompiledGraph; CompiledStateGraph
# is its replacement for a compiled StateGraph.
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from app.agentic_AI.ticket_state import TicketState
from app.agentic_AI.agents.intake_agent import intake_graph
from app.agentic_AI.agents.dispatch_agent import dispatch_graph
from app.database import SessionLocal
from app.models.notification import Notification

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
        
        from app.models.ticket import Ticket
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

async def human_approval_node(state: TicketState) -> Dict[str, Any]:
    """
    Human-in-the-loop pause point. The graph freezes here (state saved to the
    Redis checkpointer) until the PM resumes it via Command(resume=...) from the
    /approve or /reject endpoint.

    interrupt() MUST be the first statement — on resume the whole node re-runs
    from the top, so nothing side-effecting may precede it. The PM-facing
    "question" was already written by notify_pm_node (a separate, completed node
    that does not re-run), so this node only records the decision.
    """
    decision = interrupt(
        {
            "ticket_id": state.ticket_id,
            "ai_summary": state.ai_summary,
            "action": "approve_or_reject",
        }
    )
    return {"pm_approved": bool(decision.get("approved"))}


def route_on_decision(state: TicketState) -> str:
    return "dispatch" if state.pm_approved else "cancel"


async def cancel_node(state: TicketState) -> Dict[str, Any]:
    """PM rejected the ticket — mark it CANCELLED. (Reached only via graph resume.)"""
    db = SessionLocal()
    try:
        from app.models.ticket import Ticket
        ticket = db.get(Ticket, state.ticket_id)
        if ticket:
            ticket.status = "CANCELLED"
            ticket.updated_at = datetime.utcnow()
        db.commit()
        return {"current_status": "CANCELLED"}
    except Exception as e:
        db.rollback()
        logger.exception("cancel_node error for ticket %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()


def route_after_intake(state: TicketState) -> str:
    if state.error is not None:
        return END
    if state.requires_pm_approval is False:
        return "dispatch"
    return "notify_pm"

builder = StateGraph(TicketState)

builder.add_node("intake", intake_graph)
builder.add_node("notify_pm", notify_pm_node)
builder.add_node("human_approval", human_approval_node)
builder.add_node("cancel", cancel_node)
builder.add_node("dispatch", dispatch_graph)

builder.add_edge(START, "intake")
builder.add_conditional_edges(
    "intake",
    route_after_intake,
    {
        END: END,
        "dispatch": "dispatch",
        "notify_pm": "notify_pm"
    }
)

builder.add_edge("notify_pm", "human_approval")
builder.add_conditional_edges(
    "human_approval",
    route_on_decision,
    {
        "dispatch": "dispatch",
        "cancel": "cancel"
    }
)
builder.add_edge("cancel", END)
builder.add_edge("dispatch", END)

def get_parent_graph(checkpointer=None) -> CompiledStateGraph:
    return builder.compile(checkpointer=checkpointer)
