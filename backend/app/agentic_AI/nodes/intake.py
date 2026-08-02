"""
backend/agentic_AI/nodes/intake.py
"""
import logging
import uuid
from typing import Dict, Any, List

from langchain_core.messages import HumanMessage

from app.config import settings
from app.database import SessionLocal
from app.models.ticket import Ticket
from app.agentic_AI import prompts
from app.agentic_AI.llm import get_structured_model
from app.agentic_AI.ticket_state import TicketState
from app.agentic_AI.output_schemas import IntakeClassification
from app.agentic_AI.tools.intake import load_allowed_categories, normalize_category

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

        # The vocabulary is per-PM and editable, so it is read at call time and
        # listed in the prompt rather than baked into the output schema.
        allowed = load_allowed_categories(db, uuid.UUID(state.pm_id))

        structured_llm = get_structured_model(IntakeClassification)

        content = [
            {
                "type": "text",
                "text": prompts.build_intake_prompt(
                    title=ticket_title,
                    description=ticket_description,
                    categories=allowed,
                ),
            }
        ]

        for url in media_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url}
            })

        msg = HumanMessage(content=content)
        classification: IntakeClassification = await structured_llm.ainvoke([msg])

        # `category` is a plain str on the schema, so the model's answer is
        # guidance until this check folds it onto the PM's actual vocabulary.
        # Anything unrecognised becomes "other", which matches no vendor and
        # routes the ticket to the PM instead of failing the graph.
        category = normalize_category(
            classification.category, [option.name for option in allowed]
        )

        return {
            "category": category,
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
