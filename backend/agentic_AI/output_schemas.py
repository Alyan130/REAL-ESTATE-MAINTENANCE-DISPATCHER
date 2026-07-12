from pydantic import BaseModel, Field

class IntakeClassification(BaseModel):
    category: str = Field(description="one of: plumbing, electrical, hvac, structural, appliance, pest, cleaning, other")
    priority: str = Field(description="P1, P2, P3, P4")
    ai_summary: str = Field(description="one plain English sentence for PM. format: 'P{n} {category} — {what happened}'")
    requires_pm_approval: bool = Field(description="False if P1 — auto dispatch immediately. True if P2, P3, P4 — PM must approve")
    pm_notes: str = Field(description="extra context for PM, empty string if none")
