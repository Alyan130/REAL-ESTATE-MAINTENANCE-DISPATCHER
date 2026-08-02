"""
backend/agentic_AI/prompts.py

Prompt templates for the agents.

This module is pure formatting: it takes values that have already been fetched
and decided elsewhere and renders them into text. It reads no database and makes
no decisions — that split mirrors `tools/dispatch.py` ("nodes orchestrate; these
do the DB work") and keeps prompts diffable and testable on their own.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoids a runtime import cycle: tools.intake → models → app
    from app.agentic_AI.tools.intake import CategoryOption
    from app.agentic_AI.tools.negotiation import Mandate


INTAKE_INSTRUCTIONS = """\
Classify this maintenance ticket from the text and any images.

Category — choose exactly one slug from this list and copy it verbatim:
{category_lines}

If nothing on that list genuinely fits, answer "other". Do not invent a slug
that is not listed.

Priority:
  P1 — emergency: safety risk, flooding, no power, no heat in winter, gas
  P2 — urgent: affects daily living
  P3 — standard: inconvenient but liveable
  P4 — minor: cosmetic

requires_pm_approval is False ONLY for P1, which dispatches immediately.\
"""


def build_intake_prompt(
    *,
    title: str,
    description: str,
    categories: "list[CategoryOption]",
) -> str:
    """
    Render the intake classification prompt for one ticket.

    `categories` is the PM's own vocabulary, loaded at call time — the model can
    only be asked for a category that this PM actually has a vendor pool for.
    Both slug and label are shown, since the label is what carries the meaning
    ("hvac" alone is less legible to the model than "hvac — Heating & Cooling").
    """
    category_lines = "\n".join(
        f"  - {option.name} — {option.label}" for option in categories
    )
    instructions = INTAKE_INSTRUCTIONS.format(category_lines=category_lines)

    return f"Title: {title}\nDescription: {description}\n\n{instructions}"


# ─── Negotiation ─────────────────────────────────────────────────────────────

NEGOTIATION_SYSTEM_PROMPT = """\
You are a maintenance coordinator messaging a contractor on behalf of a property
manager. You are NOT the property manager and you cannot approve spending.

The job
  Title: {ticket_title}
  What the tenant reported: {ticket_summary}
  Trade: {category_label}
  Urgency: {priority_label}
  Property: {property_label}
  Access: {access_note}

Conversation so far
{transcript}

Your mandate
{mandate_lines}

Rules for your reply
  1. Never state a dollar figure unless it appears in "Your mandate" above, or
     the contractor named it first.
  2. Never agree to a price. Only the property manager approves spending. If
     they push for a yes, say you'll put it to the manager and come back.
  3. Aim to leave with two things: a firm TOTAL for the whole job, and a day
     they can attend. Ask for whichever is missing.
  4. If they hedge — "depends what I find", "plus parts", "starting at" — ask
     what the total would be in the most likely case. An open-ended number is
     not a quote.
  5. If they ask something you were not told above, say you'll check with the
     property manager. Never invent a detail about the property, the tenant, or
     the job.
  6. Two or three sentences. Plain text, no markdown, no emoji, no signature.
  7. Never mention budgets, ceilings, limits, approval thresholds, or that you
     are an AI.

Judging their message
  Set `price` ONLY to a firm total the contractor themselves named for the whole
  job. Leave it null for hourly rates, call-out fees, part-costs, ranges, or
  anything you inferred rather than read.

  Set `is_firm_total` false when the figure is conditional in any way.

  Set `recommendation`:
    - "approve"    the price is a firm, unconditional total for the whole job
                   and the contractor has committed to it
    - "send_to_pm" anything else — conditional, vague, a range, a rate, an
                   unusually high or low figure, or you are simply unsure

  When in doubt, "send_to_pm". A quote sent to the manager unnecessarily costs
  a moment of their time; one approved wrongly costs them money.
"""


def build_negotiation_prompt(mandate: "Mandate", transcript: str) -> str:
    """
    Render the negotiation prompt for one turn.

    `mandate.max_price` does not exist by construction — the auto-approve
    ceiling is never rendered into this text. A model that knows the ceiling
    negotiates toward it or leaks it, and vendor replies are untrusted input in
    this same context, so a visible ceiling is a movable one. The comparison
    happens in Python afterwards, against a number the model never saw.
    """
    lines: list[str] = []

    if mandate.authorised_counter is not None:
        # The PM authorised this exact figure. It is the only number the model
        # is permitted to say, and saying it is the point of this turn.
        lines.append(
            f"  The property manager has authorised you to offer "
            f"${mandate.authorised_counter:,.2f} for this job. Put that figure to "
            f"the contractor directly and ask if they can do it."
        )
    elif mandate.anchor_price is not None:
        lines.append(
            f"  Jobs like this usually settle around ${mandate.anchor_price:,.2f}. "
            f"Use that only to judge whether a quote sounds reasonable — do NOT "
            f"state it, and do not offer it."
        )
    else:
        lines.append(
            "  You have no reference price for this job. Ask what they would "
            "charge; do not suggest a figure yourself."
        )

    return NEGOTIATION_SYSTEM_PROMPT.format(
        ticket_title=mandate.ticket_title,
        ticket_summary=mandate.ticket_summary or "(no further detail given)",
        category_label=mandate.category_label,
        priority_label=mandate.priority_label,
        property_label=mandate.property_label,
        access_note=mandate.access_note,
        transcript=transcript,
        mandate_lines="\n".join(lines),
    )


NEGOTIATION_OPENER = """\
Hi {vendor_name} — we have a {category_label} job at {property_label}: {ticket_title}.
{ticket_summary}
Could you let me know your total for the work and a day you could attend?\
"""


# Used when a drafted reply fails the money guard. Saying something safe and
# generic beats sending a figure nobody authorised.
NEGOTIATION_FALLBACK_REPLY = (
    "Thanks — let me check that with the property manager and come straight back "
    "to you."
)
