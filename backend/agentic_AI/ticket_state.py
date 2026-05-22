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

    # --- Pipeline Control ---
    current_status: str = Field(default="intake")
    error: Optional[str] = Field(default=None)