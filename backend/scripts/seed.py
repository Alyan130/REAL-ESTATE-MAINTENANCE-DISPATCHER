"""
backend/scripts/seed.py

Populate a fresh database with a realistic dataset for manual testing.

    python -m scripts.seed              # seed (refuses if data exists)
    python -m scripts.seed --reset      # wipe the seeded tables first
    python -m scripts.seed --password X # override the shared password

**This is also the only way to create the first property manager.** There is no
signup endpoint anywhere in the codebase, and both invite endpoints require an
already-authenticated PM — so without this script a fresh database has no way in.

The data is deliberately shaped to exercise the negotiation agent rather than to
look impressive:

  - Plumbing carries target 180 / max 400, so one quote auto-confirms and another
    lands on the PM's decision card. Structural has NO ceiling, which is the
    "never auto-approve" default.
  - There is no structural vendor, so that ticket escalates instead of dispatching
    — the vendors screen's coverage-gap warning has something real to report.
  - Tickets sit at PENDING_APPROVAL so the approve button starts the whole loop.

Everything is committed in one transaction: a half-seeded database is worse than
an empty one.

Addresses are `@example.com` (RFC 2606, reserved for documentation), not the
`@demo.test` the frontend demo fixtures use. `.test` is a special-use TLD that
Pydantic's `EmailStr` rejects outright, so a `@demo.test` account cannot log in
through the real API at all — the demo fixtures get away with it only because
the demo adapter never runs Pydantic.
"""
from __future__ import annotations

import argparse
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.category_setting import CategorySetting
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.ticket import Ticket
from app.models.user import User
from app.models.vendor import Vendor

DEFAULT_PASSWORD = "demo1234"

# Truncated in FK order. `alembic_version` is deliberately absent — wiping data
# must never look like an un-migration.
SEEDED_TABLES = [
    "vendor_messages",
    "vendor_jobs",
    "tickets",
    "tenants",
    "notifications",
    "category_settings",
    "properties",
    "vendors",
    "users",
]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _ago(days: float) -> datetime:
    return _now() - timedelta(days=days)


# (name, label, vendor_selectable, target, max) — max=None means never auto-approve.
CATEGORIES: list[tuple[str, str, bool, Decimal | None, Decimal | None]] = [
    ("plumbing", "Plumbing", True, Decimal("180.00"), Decimal("400.00")),
    ("electrical", "Electrical", True, Decimal("220.00"), Decimal("500.00")),
    ("hvac", "HVAC", True, Decimal("260.00"), Decimal("600.00")),
    # No ceiling: every structural quote comes to the PM. This is the safe
    # default a PM who hasn't set prices gets, and it needs to be visible.
    ("structural", "Structural", True, Decimal("450.00"), None),
    ("appliance", "Appliance", True, Decimal("150.00"), Decimal("350.00")),
    ("pest", "Pest", True, Decimal("120.00"), Decimal("250.00")),
    ("cleaning", "Cleaning", True, Decimal("90.00"), Decimal("200.00")),
    ("other", "Other", False, None, None),
]


def already_seeded(db: Session) -> bool:
    return db.query(User).first() is not None


def reset(db: Session) -> None:
    """Truncate every seeded table. Leaves the schema and alembic state alone."""
    db.execute(
        text(f"TRUNCATE {', '.join(SEEDED_TABLES)} RESTART IDENTITY CASCADE")
    )
    db.commit()
    print("Wiped:", ", ".join(SEEDED_TABLES))


def seed(db: Session, password: str) -> None:
    pw = hash_password(password)

    # ─── Property manager ────────────────────────────────────────────────────
    pm = User(
        id=uuid.uuid4(),
        email="pm@example.com",
        full_name="Alex Whitfield",
        phone="+44 117 496 0001",
        role="pm",
        is_active=True,
        invite_status="approved",
        password_hash=pw,
    )
    db.add(pm)

    # ─── Categories ──────────────────────────────────────────────────────────
    # Migration A's backfill only fires for users that existed when it ran, so a
    # PM created afterwards needs these written here. CategoryService.ensure_seeded
    # would also cover it lazily, but without prices — and the prices are the
    # point of this dataset.
    for order, (name, label, selectable, target, ceiling) in enumerate(CATEGORIES):
        db.add(
            CategorySetting(
                id=uuid.uuid4(),
                pm_id=pm.id,
                name=name,
                label=label,
                target_price=target,
                max_price=ceiling,
                is_vendor_selectable=selectable,
                is_active=True,
                sort_order=order,
            )
        )

    # ─── Properties ──────────────────────────────────────────────────────────
    properties = [
        Property(
            id=uuid.uuid4(),
            pm_id=pm.id,
            name="Rosewood Court",
            address="14 Rosewood Court, Bristol BS1 4TR",
            is_active=True,
        ),
        Property(
            id=uuid.uuid4(),
            pm_id=pm.id,
            name="Maple House",
            address="88 Maple Road, Bristol BS6 7QN",
            is_active=True,
        ),
        Property(
            id=uuid.uuid4(),
            pm_id=pm.id,
            name="Kingsley Mews",
            address="3 Kingsley Mews, Bath BA2 3LD",
            is_active=True,
        ),
    ]
    db.add_all(properties)
    rosewood, maple, kingsley = properties

    # ─── Tenants ─────────────────────────────────────────────────────────────
    tenant_specs = [
        ("tenant@example.com", "Priya Raman", rosewood, "4B", "approved"),
        ("marcus@example.com", "Marcus Bell", maple, "12", "approved"),
        # Pending invite: reproduces ACCOUNT_PENDING on login.
        ("sofia@example.com", "Sofia Alvarez", kingsley, "2", "pending"),
    ]
    tenants: list[Tenant] = []
    for email, name, prop, unit, invite_status in tenant_specs:
        user = User(
            id=uuid.uuid4(),
            email=email,
            full_name=name,
            role="tenant",
            is_active=True,
            invite_status=invite_status,
            password_hash=pw if invite_status == "approved" else None,
        )
        db.add(user)
        tenant = Tenant(
            id=uuid.uuid4(),
            user_id=user.id,
            property_id=prop.id,
            unit_number=unit,
            lease_start=date.today() - timedelta(days=400),
            lease_end=date.today() + timedelta(days=330),
            is_active=True,
        )
        db.add(tenant)
        tenants.append(tenant)

    priya, marcus, sofia = tenants

    # ─── Vendors ─────────────────────────────────────────────────────────────
    # Deliberately NO structural vendor: that ticket must escalate, so the
    # coverage-gap path is exercised rather than assumed.
    vendor_specs = [
        ("vendor@example.com", "Northgate Plumbing", ["plumbing"], 4.8, 4),
        ("volt@example.com", "Volt & Co Electrical", ["electrical"], 4.5, 3),
        ("aircare@example.com", "AirCare Heating", ["hvac", "appliance"], 4.2, 2),
        ("brightclean@example.com", "BrightClean Services", ["cleaning", "pest"], 4.6, 5),
        # A second plumber, so "try another vendor" has somewhere to go.
        ("citywide@example.com", "Citywide Drains", ["plumbing"], 4.1, 3),
    ]
    for email, name, categories, rating, capacity in vendor_specs:
        db.add(
            User(
                id=uuid.uuid4(),
                email=email,
                full_name=name,
                role="vendor",
                is_active=True,
                invite_status="approved",
                password_hash=pw,
            )
        )
        db.add(
            Vendor(
                id=uuid.uuid4(),
                pm_id=pm.id,
                name=name,
                email=email,
                phone="+44 117 496 00" + str(20 + len(name) % 70),
                categories=categories,
                rating=rating,
                max_concurrent_jobs=capacity,
                is_active=True,
            )
        )

    # ─── Tickets ─────────────────────────────────────────────────────────────
    # (tenant, property, title, description, category, priority, status, summary,
    #  permission_to_enter, age_days)
    ticket_specs = [
        (
            priya, rosewood,
            "Kitchen tap won't stop dripping",
            "It's been going for about a week and it's getting worse overnight.",
            "plumbing", "P3", "PENDING_APPROVAL",
            "P3 plumbing — kitchen mixer tap dripping continuously for a week and worsening. Likely a worn cartridge or washer.",
            True, 1,
        ),
        (
            marcus, maple,
            "Crack above the bedroom window",
            "Diagonal, about 40cm. It wasn't there last month.",
            "structural", "P2", "PENDING_APPROVAL",
            "P2 structural — new diagonal crack ~40cm above a bedroom window frame, appeared within the last month. Needs assessment.",
            True, 2,
        ),
        (
            priya, rosewood,
            "Water coming through the bathroom ceiling",
            "It's running, not dripping. I've put a bucket under it.",
            "plumbing", "P1", "TRIAGED",
            "P1 plumbing — active water ingress through the bathroom ceiling from the flat above. Emergency.",
            True, 4,
        ),
        (
            sofia, kingsley,
            "Living room radiator stays cold",
            "The rest of the flat heats up fine. Bled it twice, no change.",
            "hvac", "P3", "PENDING_APPROVAL",
            "P3 hvac — single radiator not heating while the rest of the system works, and bleeding hasn't helped. Likely a stuck valve.",
            False, 6,
        ),
        (
            marcus, maple,
            "Communal stairwell hasn't been cleaned in three weeks",
            None,
            "cleaning", "P4", "OPEN",
            None,
            False, 8,
        ),
        (
            priya, rosewood,
            "Fridge freezer compartment not freezing",
            "The fridge part is fine. Everything in the freezer defrosted.",
            "appliance", "P3", "CANCELLED",
            "P3 appliance — freezer compartment not holding temperature while the fridge section works normally.",
            True, 20,
        ),
    ]

    for tenant, prop, title, description, category, priority, status, summary, entry, age in ticket_specs:
        db.add(
            Ticket(
                id=uuid.uuid4(),
                property_id=prop.id,
                tenant_id=tenant.id,
                title=title,
                description=description,
                category=category,
                priority=priority,
                status=status,
                media_urls=None,
                ai_summary=summary,
                permission_to_enter=entry,
                created_at=_ago(age),
                updated_at=_ago(age),
            )
        )

    db.commit()


def summarise(db: Session) -> None:
    print("\nSeeded:")
    for model, label in (
        (User, "users"),
        (Property, "properties"),
        (Tenant, "tenants"),
        (Vendor, "vendors"),
        (CategorySetting, "category_settings"),
        (Ticket, "tickets"),
    ):
        print(f"  {label:20} {db.query(model).count()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the dispatcher database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Truncate the seeded tables first. Destructive.",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help=f"Shared password for every seeded account (default: {DEFAULT_PASSWORD}).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.reset:
            reset(db)
        elif already_seeded(db):
            print(
                "Database already has users — refusing to seed on top.\n"
                "Re-run with --reset to wipe and reseed."
            )
            return 1

        seed(db, args.password)
        summarise(db)

        print(f"\nSign in as pm@example.com / {args.password}")
        print(
            "\nTo exercise the negotiation agent: open the kitchen-tap ticket and\n"
            "approve it. Plumbing is capped at $400, so a quote under that confirms\n"
            "itself and one over it comes back to you."
        )
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
