---
description: Invoked when starting work on a new feature.
---

## Steps

### 1. Confirm Feature Name
Take the feature name from the user and convert it to kebab-case.
- `Dark Mode Toggle` → `feature/dark-mode-toggle`
- `Fix Save Button` → `feature/fix-save-button`

### 2. Check if Branch Already Exists
Before creating anything, check existing branches:
```bash
git branch -a | grep feature/<name>
```
- If the branch **exists** → check it out, do not create a new one.
- If the branch **does not exist** → create it.

### 3. Create and Switch to the Branch
```bash
git checkout -b feature/<kebab-case-feature-name>
```

### 4. Verify
```bash
git branch --show-current
```
Confirm the active branch is the feature branch before doing any work.

### 5. (If GitHub MCP is connected)
Use the GitHub MCP server to verify the remote also reflects the new branch after first push.
Use `list-branches` to confirm it exists on the remote once pushed.

## Rules
- Never start work on `main` — branch first, always.
- One branch per feature — never create a second branch for improvements or fixes on the same feature.
- If the feature branch already exists, always check it out and continue on it.
- Branch naming: `feature/<kebab-case>` — no spaces, no uppercase, no slashes beyond the prefix.
- Notify the user with the active branch name before proceeding with any implementation.