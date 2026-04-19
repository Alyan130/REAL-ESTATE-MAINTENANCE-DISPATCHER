---
description: Invoked when a feature is complete and ready to be reviewed for merging into main.
---

## Steps

### 1. Confirm the Feature Branch is Up to Date
```bash
git status
git push origin feature/<n>
```
Ensure all commits are pushed before opening the PR. No unpushed local commits.

### 2. Open the Pull Request via GitHub MCP
Use the GitHub MCP `create-pull-request` tool with the following:

| Field | Value |
|---|---|
| `base` | `main` |
| `head` | `feature/<n>` |
| `title` | Clear, plain-English title of what the feature does |
| `body` | Summary of changes (see PR body template below) |

### PR Body Template
```md
## What Changed
- Brief description of what this PR introduces or fixes.

## Why
- The reason this change was made.

## Notes for Reviewer
- Anything the reviewer should know before merging (edge cases, dependencies, risks).
```

### 3. Notify the User
After the PR is created, share:
- The PR URL
- The feature branch name
- A reminder that **only the human merges** — do not trigger a merge.

## Rules
- Never merge the PR yourself — open it and stop.
- Always target `main` as the base branch, never another feature branch.
- PR title must be plain language — no ticket IDs, no vague labels like "updates".
- If GitHub MCP is not connected, output the PR body to the user and instruct them to open it manually.
- One PR per feature branch — do not bundle multiple features into one PR.