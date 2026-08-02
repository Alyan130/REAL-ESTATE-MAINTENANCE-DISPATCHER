"""
Intake category handling.

These are the guards that keep the agent working now that the category
vocabulary is per-PM data rather than a compile-time `Literal`. Nothing here
touches the database or the LLM, so no fixtures are needed.

The invariant worth protecting: whatever the model answers with,
`normalize_category` returns a member of the PM's allowed list. If that ever
breaks, `find_best_vendor` matches nothing and tickets stop dispatching with no
error anywhere.
"""
from __future__ import annotations

import uuid

import pytest

from app.agentic_AI.tools.intake import load_allowed_categories, normalize_category
from app.core.categories import OTHER, SEED_CATEGORIES

PM_ID = uuid.uuid4()
ALLOWED = ["plumbing", "electrical", "hvac", "landscaping", "other"]


# ─── Test doubles ────────────────────────────────────────────────────────────


class _Row:
    def __init__(self, name: str, label: str) -> None:
        self.name = name
        self.label = label


class _Query:
    def __init__(self, rows: list[_Row], raises: bool) -> None:
        self._rows = rows
        self._raises = raises

    def filter(self, *_args, **_kwargs) -> "_Query":
        return self

    def order_by(self, *_args, **_kwargs) -> "_Query":
        return self

    def all(self) -> list[_Row]:
        if self._raises:
            raise RuntimeError("connection lost")
        return self._rows


class _Session:
    def __init__(self, rows: list[_Row] | None = None, raises: bool = False) -> None:
        self._query = _Query(rows or [], raises)

    def query(self, *_args, **_kwargs) -> "_Query":
        return self._query


# ─── load_allowed_categories ─────────────────────────────────────────────────


def test_falls_back_to_seed_when_the_pm_has_no_categories():
    """An empty list would make every ticket 'other' and silently stop dispatch."""
    options = load_allowed_categories(_Session(rows=[]), PM_ID)

    assert [option.name for option in options] == [name for name, _, _ in SEED_CATEGORIES]


def test_falls_back_to_seed_when_the_lookup_fails():
    """A database blip must degrade intake, not break it."""
    options = load_allowed_categories(_Session(raises=True), PM_ID)

    assert len(options) == len(SEED_CATEGORIES)


def test_never_returns_an_empty_list():
    for session in (_Session(rows=[]), _Session(raises=True)):
        assert load_allowed_categories(session, PM_ID)


def test_uses_the_pms_own_categories_when_present():
    rows = [_Row("landscaping", "Landscaping"), _Row("other", "Other")]

    options = load_allowed_categories(_Session(rows=rows), PM_ID)

    assert [option.name for option in options] == ["landscaping", "other"]
    assert [option.label for option in options] == ["Landscaping", "Other"]


# ─── normalize_category ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("plumbing", "plumbing"),
        ("HVAC", "hvac"),
        ("  Plumbing  ", "plumbing"),
        ("LANDSCAPING", "landscaping"),
        # A PM-added category the seed list has never heard of.
        ("landscaping", "landscaping"),
    ],
)
def test_accepts_the_pms_vocabulary_regardless_of_casing(answer, expected):
    assert normalize_category(answer, ALLOWED) == expected


@pytest.mark.parametrize("answer", ["roofing", "air conditioning", "", "   ", None])
def test_unknown_answers_become_other(answer):
    """`other` matches no vendor, so the ticket escalates to the PM."""
    assert normalize_category(answer, ALLOWED) == OTHER


def test_an_empty_allowed_list_still_yields_other():
    assert normalize_category("plumbing", []) == OTHER


@pytest.mark.parametrize(
    "answer",
    ["plumbing", "Plumbing", "roofing", "", None, "  other ", "HVAC", "nonsense"],
)
def test_the_result_is_always_inside_the_allowed_list(answer):
    """The invariant dispatch depends on."""
    assert normalize_category(answer, ALLOWED) in ALLOWED
