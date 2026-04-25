---
trigger: model_decision
description: Runs every time a new feature is being planned.
---

## Steps

### 1. Explore the Codebase
Before planning anything, explore the full codebase to understand:
- Existing structure, patterns, and conventions
- Related modules, components, or services the feature will touch
- Potential conflicts or dependencies

Align the new feature plan with what already exists — never plan in isolation.

### 2. Use Context7 MCP (Only When Asked)
If the user explicitly says to use Context7 mcp for this feature, use the `resolve-library-id` tool to gain external context about the library or technology involved in the feature.

Do **not** use Context7 by default. Simple codebase exploration is sufficient for most planning tasks.

## Rules
- Always explore the codebase first — no exceptions
- Only use Context7 MCP when the user explicitly requests it
- Never plan a feature without understanding how it fits into the existing codebase