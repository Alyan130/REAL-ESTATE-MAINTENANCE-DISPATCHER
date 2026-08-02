---
allowed-tools: Bash
description: Invoked When user wants to get context of project changes and current state
---


## Purpose
Gives the agent a fast summary of the project's current state from `CHANGE-LOG.md`.
Used to onboard a new agent without burning token limit on full history.

## Steps

### 1. Read CHANGE-LOG.md and CHECKPOINT.md
Open and read the full `CHANGE-LOG.md` from the project root.
Open and read the full `CHECKPOINT.md` from the project root.

### 2. Summarize Old History (1 line)
Everything older than the last 3–4 days back gets collapsed into a summary.
Example: _"Prior to [date]: auth, CRUD, dark mode, and drag-and-drop were shipped."_

### 3. Focus on Recent Changes (Last 2–3 Days)
List the most recent versions in detail:
- What was added
- What was fixed
- Anything the next agent must know (gotchas, dependencies, unfinished work)

### 4. Output Format
```
## Project Context — [today's date]

**History (summarized):** [8-10 lines of everything older]

**Recent Changes:**
- [version] [date]: [what changed + anything important to know]
- [version] [date]: [what changed + anything important to know]

**Current State:** [one line on where the project stands right now]
```

## Rules
- Never output the full changelog — summarize old, detail recent.
- Keep all context concise and clear.