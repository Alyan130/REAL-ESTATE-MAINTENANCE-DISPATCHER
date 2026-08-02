---
allowed-tools: Bash
description: Update the CHECKPOINT.md file after each change
---


## Purpose
The CHECKPOINT.md is the project's shared memory. It transfers context between agents — every entry must give the next agent enough information to understand what changed, why, and where to start from.

## How to Update:
- First read the CHECKPOINT.md file.
- Then Delete the Complete file apart from Frontmatter [Update it as well].
- Then re-inngest it with new information.

## Frontmater Format:
```
## [version] - YYYY-MM-DD
### Added / Fixed / Changed
- What changed, why it changed, and anything the next agent should know.
```

## Rules
- - DONT create new file , only update in existing CHECKPOINT.md 
- Keep entries to 5-6 lines. Be concise but never sacrifice clarity for brevity.
- Plain language — no jargon, no raw implementation details.
- Always include **why** something changed or **what to watch out for** if it affects future work.
- Every entry should leave the next agent with zero ambiguity about the current state of the project.