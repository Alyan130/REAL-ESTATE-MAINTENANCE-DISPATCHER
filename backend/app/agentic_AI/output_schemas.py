from typing import Optional

from pydantic import BaseModel, Field


class IntakeClassification(BaseModel):
    # A plain `str`, not a Literal: the category vocabulary is per-PM and lives
    # in `category_settings`, so the valid values aren't known at import time.
    # The prompt lists the PM's own categories and `normalize_category` checks
    # the answer against them, mapping anything unrecognised to "other".
    category: str = Field(
        description="the category slug, copied exactly from the list of categories in the prompt. use 'other' when nothing fits"
    )
    priority: str = Field(description="P1, P2, P3, P4")
    ai_summary: str = Field(description="one plain English sentence for PM. format: 'P{n} {category} — {what happened}'")
    requires_pm_approval: bool = Field(description="False if P1 — auto dispatch immediately. True if P2, P3, P4 — PM must approve")
    pm_notes: str = Field(description="extra context for PM, empty string if none")


class VendorReplyExtraction(BaseModel):
    """
    One negotiation turn: what to say back, and what the vendor's message meant.

    Both halves come from the same call. The `reply` is free text and can handle
    anything the contractor raises; every other field is the typed summary that
    the rest of the system actually acts on. Vendor prose never reaches a
    decision — only these fields do.

    `intent` and `recommendation` are plain `str` validated against a frozenset
    in code rather than `Literal`, consistent with how the category vocabulary
    was loosened: a model answering off-vocabulary should be corrected, not
    raise inside `with_structured_output`.
    """

    reply: str = Field(
        description="your message back to the contractor. 2-3 sentences, plain text"
    )
    price: Optional[float] = Field(
        default=None,
        description="a firm TOTAL for the whole job that the contractor themselves named. null for hourly rates, call-out fees, ranges, or any figure you inferred",
    )
    availability: Optional[str] = Field(
        default=None,
        description="when they said they could attend, in their own words. null if not mentioned",
    )
    intent: str = Field(
        description="one of: quote, question, negotiating, decline, unclear"
    )
    is_firm_total: bool = Field(
        description="false if the price is conditional in any way — 'depends what I find', 'plus parts', 'starting at'"
    )
    recommendation: str = Field(
        description="'approve' only for a firm unconditional total the contractor committed to. 'send_to_pm' for anything else, including when unsure"
    )
    reasoning: str = Field(
        description="one short sentence explaining the recommendation. shown to the property manager"
    )


VENDOR_INTENTS = frozenset(
    {"quote", "question", "negotiating", "decline", "unclear"}
)
VENDOR_RECOMMENDATIONS = frozenset({"approve", "send_to_pm"})
