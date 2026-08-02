"""
core/categories.py

The starter category vocabulary.

This used to be the single source of truth — a `Literal` that constrained both
the intake agent's classification and the categories a PM could tag a vendor
with. The authority now lives in the `category_settings` table, one row per PM,
so a PM can add trades this list never anticipated.

What remains here is the seed: the rows every PM starts with, copied into the
table by the migration for existing PMs and by `CategoryService.ensure_seeded`
for anyone created later. It is also the last-resort fallback for
`load_allowed_categories` — if that ever returned an empty list, the intake
prompt would offer the model no categories at all and every ticket would
silently classify as `other` and stop dispatching.
"""
from __future__ import annotations

# The intake fallback. A ticket lands here when no category fits, which matches
# no vendor and therefore routes the ticket to the PM.
OTHER = "other"

#                        (name, label, is_vendor_selectable)
SEED_CATEGORIES: list[tuple[str, str, bool]] = [
    ("plumbing", "Plumbing", True),
    ("electrical", "Electrical", True),
    ("hvac", "HVAC", True),
    ("structural", "Structural", True),
    ("appliance", "Appliance", True),
    ("pest", "Pest", True),
    ("cleaning", "Cleaning", True),
    (OTHER, "Other", False),
]

SEED_CATEGORY_NAMES: list[str] = [name for name, _, _ in SEED_CATEGORIES]
