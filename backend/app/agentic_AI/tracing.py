"""
app/agentic_AI/tracing.py

One place that builds the config every graph invocation is given.

Without this each run reaches LangSmith named after the graph class with a
thread id and nothing else, so "why did ticket X stall" means opening anonymous
runs one at a time. `ticket_id` and `pm_id` are attached as metadata because
LangSmith filters on metadata but only substring-matches on names, and the tags
carry the coarse cut (which stage, which priority) that you actually scan a run
list by.

Pure formatting — reads no database, makes no decisions, mirrors the split
already stated in `tools/dispatch.py`.
"""
from __future__ import annotations

from typing import Any

# The stage names double as LangSmith tags, so keep them stable — renaming one
# orphans every saved filter built on it.
STAGE_INTAKE = "intake"
STAGE_DISPATCH = "dispatch"
STAGE_NEGOTIATION = "negotiation"


def trace_config(
    thread_id: str,
    *,
    stage: str,
    run_name: str,
    ticket_id: str | None = None,
    pm_id: str | None = None,
    vendor_job_id: str | None = None,
    priority: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """
    Build a RunnableConfig carrying the checkpointer thread plus trace labels.

    `thread_id` keeps its exact meaning — it is the checkpoint key, and a resume
    must pass the same one it paused on. Everything else here is observability
    only and never affects graph behaviour.
    """
    metadata: dict[str, Any] = {"stage": stage, "thread_id": thread_id}
    tags: list[str] = [stage]

    if ticket_id:
        metadata["ticket_id"] = ticket_id
    if pm_id:
        metadata["pm_id"] = pm_id
    if vendor_job_id:
        metadata["vendor_job_id"] = vendor_job_id
    if priority:
        metadata["priority"] = priority
        tags.append(priority)

    metadata.update({k: v for k, v in extra.items() if v is not None})

    return {
        "configurable": {"thread_id": thread_id},
        "run_name": run_name,
        "tags": tags,
        "metadata": metadata,
    }
