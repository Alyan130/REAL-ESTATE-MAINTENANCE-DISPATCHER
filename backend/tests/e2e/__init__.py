"""
End-to-end tests. These hit the real database, the real checkpointer, and a real
LLM — they are not unit tests and are excluded from the default run.

    python -m pytest tests/e2e -v -s

See docs/test-cases/e2e-test-plan.md.
"""
