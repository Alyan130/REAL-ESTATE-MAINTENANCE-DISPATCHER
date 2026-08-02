import operator
from typing import Annotated, Optional

from pydantic import BaseModel, Field

class TicketState(BaseModel):
    # --- Identifiers (just IDs, data lives in Postgres) ---
    ticket_id: str
    property_id: str
    tenant_id: str
    pm_id: str

    # --- Intake Agent Output ---
    priority: Optional[str] = Field(default=None, description="P1/P2/P3/P4")
    category: Optional[str] = Field(default=None, description="plumbing/electrical etc")
    ai_summary: Optional[str] = Field(default=None, description="intake analysis")
    requires_pm_approval: Optional[bool] = Field(default=None, description="intake decision")
    pm_notes: Optional[str] = Field(default=None, description="notes for PM")

    # --- PM Decision ---
    pm_approved: Optional[bool] = Field(default=None)

    # --- Dispatch Agent Output ---
    assigned_vendor_id: Optional[str] = Field(default=None)
    # Reducers for LangGraph to accumulate
    vendors_contacted: Annotated[list[str], operator.add] = Field(default_factory=list)
    dispatch_attempts: Annotated[int, operator.add] = Field(default=0)

    # --- Negotiation Agent Output ---
    # Reducers for LangGraph to accumulate
    negotiation_messages: Annotated[list[dict], operator.add] = Field(default_factory=list)
    final_price: Optional[float] = Field(default=None)
    job_confirmed: Optional[bool] = Field(default=None)
    counter_offered: Optional[bool] = Field(default=None)

    # Per-VendorJob negotiation state.
    #
    # Every field below is plain overwrite — NO reducers — because
    # `open_negotiation` resets all of them when the next vendor starts. This is
    # exactly why `counter_rounds` cannot copy the `Annotated[int, operator.add]`
    # trick `dispatch_attempts` uses: an operator.add channel can only ever be
    # incremented, never reset to 0, and vendor #2 runs on this same TicketState.
    active_vendor_job_id: Optional[str] = Field(default=None)
    chat_token: Optional[str] = Field(default=None)
    # The thread this negotiation runs on, supplied by the caller that invoked
    # the graph and mirrored onto the VendorJob row. Persisting it means a
    # resume is always a lookup and never a guess about naming conventions.
    negotiation_thread_id: Optional[str] = Field(default=None)
    # The reply drafted this turn, held between interpret_reply and
    # post_ai_reply. Cleared once sent.
    pending_reply: Optional[str] = Field(default=None)
    quoted_price: Optional[float] = Field(default=None)
    quoted_availability: Optional[str] = Field(default=None)
    vendor_intent: Optional[str] = Field(
        default=None, description="quote|question|negotiating|decline|unclear"
    )
    is_firm_total: Optional[bool] = Field(default=None)
    ai_recommendation: Optional[str] = Field(
        default=None, description="approve|send_to_pm"
    )
    ai_reasoning: Optional[str] = Field(default=None)
    counter_rounds: int = Field(default=0)
    chat_turns: int = Field(default=0)
    auto_approved: Optional[bool] = Field(default=None)
    decision_reason: Optional[str] = Field(default=None)
    pm_negotiation_action: Optional[str] = Field(
        default=None, description="accept|counter|next_vendor"
    )
    pm_counter_price: Optional[float] = Field(default=None)
    close_reason: Optional[str] = Field(
        default=None, description="DECLINED|EXPIRED|SUPERSEDED"
    )

    # --- Pipeline Control ---
    current_status: str = Field(default="intake")
    error: Optional[str] = Field(default=None)