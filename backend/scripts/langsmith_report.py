"""
backend/scripts/langsmith_report.py

Cost and latency report for an end-to-end run.

    python -m scripts.langsmith_report                 # read tests/e2e/.last_run.json
    python -m scripts.langsmith_report <id> [<id> …]   # explicit ticket ids

Every graph invocation carries `ticket_id` in its metadata (added in 0.18.2), so
this is a metadata query rather than manual trace-hunting. Metadata is inherited
by child runs, which is what makes the LLM calls findable by the ticket that
caused them.

The number to watch is the **LLM call count**. The expected shape is 2 for TC-1
(intake classify + one vendor-reply extraction) and 3 for TC-2 (intake + hedged
reply + firm reply). A materially higher count means the graph is looping — the
chat loop is bounded at MAX_CHAT_TURNS, but a loop that runs 11 times before
stopping is a cost problem long before it is a correctness one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from app.config import settings  # noqa: F401  — exports LANGSMITH_* into os.environ

RUN_RECORD = Path(__file__).resolve().parent.parent / "tests" / "e2e" / ".last_run.json"


def load_cases(argv: list[str]) -> dict[str, str]:
    if argv:
        return {f"case-{i + 1}": t for i, t in enumerate(argv)}
    if not RUN_RECORD.exists():
        raise SystemExit(
            f"No ticket ids given and {RUN_RECORD} does not exist.\n"
            "Run the e2e suite first, or pass ticket ids as arguments."
        )
    return json.loads(RUN_RECORD.read_text(encoding="utf-8"))


def runs_for_ticket(client, project: str, ticket_id: str) -> list:
    """
    Every run tagged with this ticket.

    Tries the server-side metadata filter first and falls back to scanning recent
    runs, because the filter grammar has changed between langsmith releases and a
    report is not worth pinning a version over.
    """
    try:
        return list(
            client.list_runs(
                project_name=project,
                filter=f'and(eq(metadata_key, "ticket_id"), eq(metadata_value, "{ticket_id}"))',
            )
        )
    except Exception:
        found = []
        for run in client.list_runs(project_name=project, limit=400):
            meta = (run.extra or {}).get("metadata") or {}
            if meta.get("ticket_id") == ticket_id:
                found.append(run)
        return found


def summarise(runs: list) -> dict:
    llm = [r for r in runs if r.run_type == "llm"]
    errors = [r for r in runs if getattr(r, "error", None)]

    calls = []
    for r in sorted(llm, key=lambda r: r.start_time or 0):
        usage = {}
        for source in ((r.extra or {}).get("metadata") or {}, r.outputs or {}):
            for key in ("usage_metadata", "token_usage", "usage"):
                if isinstance(source.get(key), dict):
                    usage = source[key]
                    break
            if usage:
                break
        # LangChain normalises to input/output/total; raw OpenAI uses prompt/completion.
        prompt = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        completion = usage.get("output_tokens") or usage.get("completion_tokens") or 0
        total = usage.get("total_tokens") or (prompt + completion)

        latency = None
        if r.start_time and r.end_time:
            latency = (r.end_time - r.start_time).total_seconds()

        calls.append(
            {
                "name": r.name,
                "model": ((r.extra or {}).get("metadata") or {}).get("ls_model_name")
                or (r.extra or {}).get("invocation_params", {}).get("model")
                or "?",
                "prompt": prompt,
                "completion": completion,
                "total": total,
                "latency": latency,
                "error": getattr(r, "error", None),
            }
        )

    return {
        "runs": len(runs),
        "llm_calls": len(llm),
        "errors": len(errors),
        "prompt": sum(c["prompt"] for c in calls),
        "completion": sum(c["completion"] for c in calls),
        "total": sum(c["total"] for c in calls),
        "latency": sum(c["latency"] or 0 for c in calls),
        "calls": calls,
    }


def main() -> int:
    try:
        from langsmith import Client
    except ImportError:
        raise SystemExit("langsmith is not installed — pip install langsmith")

    project = settings.LANGSMITH_PROJECT or "default"
    cases = load_cases(sys.argv[1:])
    client = Client()

    print(f"LangSmith project: {project}\n")

    results: dict[str, dict] = {}
    for case, ticket_id in cases.items():
        runs = runs_for_ticket(client, project, ticket_id)
        summary = summarise(runs)
        results[case] = summary

        print(f"── {case} — ticket {ticket_id}")
        if not runs:
            print("   no runs found. Traces can lag a few seconds; retry shortly.\n")
            continue
        for i, call in enumerate(summary["calls"], 1):
            latency = f"{call['latency']:.2f}s" if call["latency"] is not None else "?"
            print(
                f"   {i}. {call['name'][:34]:34} {call['model'][:24]:24} "
                f"{call['prompt']:>6} + {call['completion']:>5} = {call['total']:>6} tok  {latency:>7}"
            )
            if call["error"]:
                print(f"      ERROR: {str(call['error'])[:100]}")
        print()

    if len(results) > 1:
        print("── TC-1 vs TC-2 " + "─" * 44)
        rows = [
            ("LLM calls", "llm_calls", "{:d}"),
            ("Prompt tokens", "prompt", "{:,d}"),
            ("Completion tokens", "completion", "{:,d}"),
            ("Total tokens", "total", "{:,d}"),
            ("LLM wall-clock", "latency", "{:.2f}s"),
            ("Errors", "errors", "{:d}"),
            ("Total runs traced", "runs", "{:d}"),
        ]
        names = list(results)
        print(f"   {'':22}" + "".join(f"{n:>14}" for n in names))
        for label, key, fmt in rows:
            cells = "".join(f"{fmt.format(results[n][key]):>14}" for n in names)
            print(f"   {label:22}{cells}")

        print()
        for name in names:
            count = results[name]["llm_calls"]
            expected = 2 if name.endswith("1") else 3
            if count > expected:
                print(
                    f"   NOTE: {name} made {count} LLM calls, expected ~{expected}. "
                    "Worth checking the graph isn't looping."
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
