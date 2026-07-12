"""
core/categories.py

Single source of truth for the maintenance category vocabulary.

Both the Intake agent (LLM classification output) and vendor creation (PM input)
draw their category values from here, so the two sides cannot drift apart — a
guaranteed shared vocabulary is what makes vendor matching reliable.

When the taxonomy later moves to a DB table (per-client editable categories),
this constant is the seed and the call sites stay the same.
"""
from __future__ import annotations

from typing import Literal, get_args

# Full ticket vocabulary. "other" is an intake catch-all when the issue does not
# fit a known trade — it intentionally matches no specialized vendor and routes
# such tickets to the PM.
TicketCategory = Literal[
    "plumbing",
    "electrical",
    "hvac",
    "structural",
    "appliance",
    "pest",
    "cleaning",
    "other",
]

# Vendors specialize in a trade — "other" is never a vendor specialty, so it is
# excluded from the categories a PM may assign to a vendor.
VENDOR_CATEGORIES: list[str] = [c for c in get_args(TicketCategory) if c != "other"]

VendorCategory = Literal[
    "plumbing",
    "electrical",
    "hvac",
    "structural",
    "appliance",
    "pest",
    "cleaning",
]
