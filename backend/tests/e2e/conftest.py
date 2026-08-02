"""
Shared fixtures for the end-to-end suite.

Nothing here is mocked. The suite talks to the real database, the real Postgres
checkpointer, and a real LLM, because the thing under test is whether the loop
actually runs — a mocked version of it proves only that the code compiles.

`TestClient` is what makes an async pipeline assertable: it drains
`BackgroundTasks` synchronously on the way out of each response, so by the time a
call returns, the graph work that call scheduled has already finished. That
replaces polling with sleeps, which is the usual way these tests rot.
"""
from __future__ import annotations

import io
import json
import struct
import uuid
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ticket ids from the last run, so the LangSmith report can find the traces
# without anyone copying ids out of the console.
RUN_RECORD = Path(__file__).parent / ".last_run.json"
_recorded: dict[str, str] = {}


def record_ticket(case: str, ticket_id: uuid.UUID) -> None:
    _recorded[case] = str(ticket_id)
    RUN_RECORD.write_text(json.dumps(_recorded, indent=2), encoding="utf-8")

PM_EMAIL = "pm@example.com"
TENANT_EMAIL = "tenant@example.com"
PASSWORD = "demo1234"


def _png(width: int = 64, height: int = 64) -> bytes:
    """
    Build a valid RGB PNG.

    Generated rather than pasted as a hex literal, because a hand-typed literal
    is one mistyped nibble away from a bad chunk CRC — which Supabase Storage
    serves back happily as `image/png`, so the only thing that notices is the
    vision model, several seconds later, with `image_parse_error`. Computing the
    CRCs here makes that class of failure impossible.

    A photo is not optional: `TicketService.create` only schedules the graph
    `if files`, so a ticket submitted without one stays OPEN and nothing runs.
    """

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB

    rows = bytearray()
    for y in range(height):
        rows.append(0)  # filter type 0 (None) per scanline
        for x in range(width):
            # A soft gradient — real image data rather than a flat block, so the
            # encoder produces a normal-looking IDAT.
            rows += bytes((x * 4 % 256, y * 4 % 256, (x + y) * 2 % 256))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
        + chunk(b"IEND", b"")
    )


SAMPLE_PHOTO = _png()


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: end-to-end test against live services")


@pytest.fixture(scope="session", autouse=True)
def seeded_database() -> None:
    """
    Reseed before the suite runs. **This wipes the database.**

    Not optional hygiene — the cases assert on *which* vendor was selected, and
    vendor selection depends on capacity. Every run leaves APPROVED jobs behind,
    and once Northgate Plumbing reaches its 4-job limit the dispatcher correctly
    picks the next-best plumber instead. Without a reset the suite passes, then
    passes, then fails on the fourth run for a reason that looks like a bug and
    is not one.

    Set `E2E_NO_RESEED=1` to keep existing data — useful when inspecting the
    state a failed run left behind.
    """
    import os

    if os.environ.get("E2E_NO_RESEED"):
        print("\n[e2e] E2E_NO_RESEED set — using the database as-is")
        return

    from app.database import SessionLocal
    from scripts.seed import reset, seed

    db = SessionLocal()
    try:
        reset(db)
        seed(db, PASSWORD)
        print("[e2e] database reseeded")
    finally:
        db.close()


@pytest.fixture(scope="session")
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture(scope="session")
def pm_token(client: TestClient) -> str:
    r = client.post("/auth/login", json={"email": PM_EMAIL, "password": PASSWORD})
    assert r.status_code == 200, f"PM login failed — is the database seeded? {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def tenant_token(client: TestClient) -> str:
    r = client.post("/auth/login", json={"email": TENANT_EMAIL, "password": PASSWORD})
    assert r.status_code == 200, f"Tenant login failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture
def pm_auth(pm_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {pm_token}"}


@pytest.fixture
def tenant_auth(tenant_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tenant_token}"}


def submit_ticket(
    client: TestClient,
    auth: dict[str, str],
    *,
    title: str,
    description: str,
    permission_to_enter: bool = True,
) -> uuid.UUID:
    """Submit a ticket with one photo and return its id."""
    r = client.post(
        "/tickets",
        headers=auth,
        data={
            "title": title,
            "description": description,
            "permission_to_enter": str(permission_to_enter).lower(),
        },
        files={"photos": ("evidence.png", io.BytesIO(SAMPLE_PHOTO), "image/png")},
    )
    assert r.status_code == 202, r.text
    return uuid.UUID(r.json()["id"])
