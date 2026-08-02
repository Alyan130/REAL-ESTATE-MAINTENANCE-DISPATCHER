"""
backend/agentic_AI/tools/intake.py

Reusable workers for the Intake agent — loading a PM's category vocabulary and
normalising whatever the model answers with. Nodes orchestrate; these do the DB
work and the deterministic checks.

The category vocabulary is per-PM and editable, so it cannot be a compile-time
`Literal` on the structured-output schema. Instead the prompt lists the PM's own
categories and `normalize_category` validates the answer against that same list.
The model is guided, not constrained — which is why the normaliser is not
optional.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.categories import OTHER, SEED_CATEGORIES
from app.models.category_setting import CategorySetting

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CategoryOption:
    """One line of the category list the prompt shows the model."""

    name: str
    label: str


def load_allowed_categories(db: Session, pm_id: uuid.UUID) -> list[CategoryOption]:
    """
    The categories this PM's tickets may be classified into.

    NEVER returns an empty list. If the PM has no rows — a brand-new PM whose
    lazy seed hasn't run, or a database that lost them — this falls back to the
    seed vocabulary.

    That fallback is load-bearing. With an empty list the prompt would offer the
    model no categories at all, every answer would fail normalisation and become
    "other", "other" matches no vendor, and every ticket would quietly stop
    dispatching with nothing in the logs to explain why.
    """
    try:
        rows = (
            db.query(CategorySetting)
            .filter(
                CategorySetting.pm_id == pm_id,
                CategorySetting.is_active.is_(True),
            )
            .order_by(CategorySetting.sort_order.asc(), CategorySetting.label.asc())
            .all()
        )
    except Exception:
        # A failed lookup must degrade to the seed list, not take down intake.
        logger.exception("Could not load categories for PM %s — using seed list", pm_id)
        rows = []

    if not rows:
        logger.warning(
            "No categories found for PM %s — falling back to the seed vocabulary", pm_id
        )
        return [
            CategoryOption(name=name, label=label) for name, label, _ in SEED_CATEGORIES
        ]

    return [CategoryOption(name=row.name, label=row.label) for row in rows]


def normalize_category(raw: str | None, allowed: list[str]) -> str:
    """
    Fold the model's answer onto the PM's vocabulary.

    Matching is case- and whitespace-insensitive, and tolerates the model
    answering with the display label ("Air Conditioning") instead of the slug.
    Anything still unrecognised becomes `other`, which matches no vendor and so
    routes the ticket to the PM — the same escalation an unknown trade deserves.
    """
    if not raw:
        return OTHER

    candidate = raw.strip().lower()
    if not candidate:
        return OTHER

    for name in allowed:
        if candidate == name.lower():
            return name

    # The model sometimes answers with the label; accept a slugified match too.
    slugged = candidate.replace(" ", "-").replace("_", "-")
    for name in allowed:
        if slugged == name.lower():
            return name

    logger.info("Intake returned unknown category %r — normalised to %r", raw, OTHER)
    return OTHER
