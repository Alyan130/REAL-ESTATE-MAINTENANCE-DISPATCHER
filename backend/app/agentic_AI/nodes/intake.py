"""
backend/agentic_AI/nodes/intake.py
"""
import logging
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.config import settings
from app.database import SessionLocal
from app.models.ticket import Ticket
from app.agentic_AI.ticket_state import TicketState
from app.agentic_AI.output_schemas import IntakeClassification

logger = logging.getLogger(__name__)

async def classify_node(state: TicketState) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        ticket = db.get(Ticket, state.ticket_id)
        if not ticket:
            logger.warning("Ticket %s not found in DB", state.ticket_id)
            return {"error": "ticket not found"}

        ticket_description = ticket.description or ""
        ticket_title = ticket.title or ""
        media_urls = ticket.media_urls or []

        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        structured_llm = llm.with_structured_output(IntakeClassification)
        
        content = [
            {"type": "text", "text": f"Title: {ticket_title}\nDescription: {ticket_description}\n\nPlease classify this maintenance ticket based on the provided text and images (if any). P1: emergency/safety/flooding/no power; P2: urgent/affects daily living; P3: standard/inconvenient; P4: minor/cosmetic. requires_pm_approval is False ONLY for P1."}
        ]
        
        for url in media_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url}
            })

        msg = HumanMessage(content=content)
        classification: IntakeClassification = await structured_llm.ainvoke([msg])
        
        return {
            "category": classification.category,
            "priority": classification.priority,
            "ai_summary": classification.ai_summary,
            "requires_pm_approval": classification.requires_pm_approval,
            "pm_notes": classification.pm_notes
        }

    except Exception as e:
        logger.exception("Error in classify_node for %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()

async def persist_triage_node(state: TicketState) -> Dict[str, Any]:
    if state.category is None or state.priority is None:
        logger.warning("classify_node output missing, skipping DB update")
        return {"error": "triage skipped — classification missing"}

    db = SessionLocal()
    try:
        from datetime import datetime
        ticket = db.get(Ticket, state.ticket_id)
        if not ticket:
            return {"error": "ticket not found"}

        ticket.category = state.category
        ticket.priority = state.priority
        ticket.ai_summary = state.ai_summary
        ticket.status = "TRIAGED"
        ticket.updated_at = datetime.utcnow()
        db.commit()
        return {"current_status": "TRIAGED"}
    except Exception as e:
        db.rollback()
        logger.exception("Error persisting triage for %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()
