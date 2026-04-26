---
description: Invoked when a feature is complete and ready to be reviewed for merging into main.
---

## Steps

---

### 1. Check Working Tree is Clean

Run:
```bash
git status --porcelain
```

**If the output is non-empty (uncommitted or untracked changes exist):**
- ❌ **Abort immediately.**
- Surface this exact message to the user:

  > ⛔ Aborted: Your working tree has uncommitted changes. Please commit or stash them before opening a PR.
  > Run `git status` to see what's pending.

- Do **not** proceed to any further step.

**If the output is empty**, continue to Step 2.

---

### 3. Check for an Existing PR on This Branch

Before creating a new PR, use the GitHub MCP `list-pull-requests` tool to check if a PR already exists for `feature/<n>` targeting `main`.

**If a PR already exists:**
- ❌ **Do not create a new PR.**
- Surface this message to the user:

  > ⚠️ A PR already exists for `feature/<n>` → `main`:
  > **[PR Title]** — [PR URL]
  >
  > Linking to the existing PR instead of creating a duplicate. If you want to update it, edit the PR body manually.

- Skip to Step 5 (Approval Gate) using the existing PR number.

**If no PR exists**, continue to Step 4.

---

### 4. Open the Pull Request via GitHub MCP

Use the GitHub MCP `create-pull-request` tool with the following:

| Field | Value |
|---|---|
| `base` | `main` |
| `head` | `feature/<n>` |
| `title` | Clear, plain-English title of what the feature does |
| `body` | See PR body template below |

**If PR creation fails:**
- ❌ **Abort immediately.**
- Surface the full error to the user and stop. Do not attempt to merge.

#### PR Body Template

```md
## What Changed
- Brief description of what this PR introduces or fixes.

## Why
- The reason this change was made.

## Notes for Reviewer
- Anything the reviewer should know before merging (edge cases, dependencies, risks).
```

---

### 5. ⛔ Approval Gate — Human Must Confirm Before Merge

After the PR is created (or linked), **stop and wait**.

Show the user this message:

> ✅ PR ready for review:
> **[PR Title]**
> 🔗 [PR URL]
> Branch: `feature/<n>` → `main`
>
> **Review the PR before proceeding.**
> When you're ready to merge, reply: `merge PR` or `go ahead and merge`.
>
> ⚠️ The agent will not merge until you explicitly confirm.

**Do not proceed to Step 6 until the user sends an explicit confirmation message.**

Accepted confirmation phrases (case-insensitive):
- `merge PR`
- `go ahead and merge`
- `merge it`
- `approve and merge`
- `lgtm merge`

Any other response should be treated as **not confirmed**. Ask the user to confirm explicitly.

---

### 6. Merge the Pull Request via GitHub MCP

Once the user confirms, use the GitHub MCP `merge-pull-request` tool:

| Field | Value |
|---|---|
| `pull_number` | PR number from Step 4 or 3 |
| `merge_method` | `squash` |
| `commit_title` | Same plain-English title used for the PR |
| `commit_message` | One-line summary of the change |

**If the merge fails:**
- ❌ **Do not retry automatically.**
- Surface the full error to the user.
- Then show:

  > ⛔ Merge failed. Common causes:
  > - Merge conflicts between `feature/<n>` and `main`
  > - Required status checks have not passed
  > - Branch protection requires approvals that haven't been granted
  >
  > Resolve the issue above and re-confirm to retry.

- Stop and wait for user instruction.

---

### 7. Notify the User

After a successful merge, show:

> ✅ Merged successfully!
> - **PR:** [PR Title] — [PR URL]
> - **Branch:** `feature/<n>` → `main`
> - **Merge commit SHA:** `<sha>`

---

## Rules

- **Never merge without explicit human confirmation** — the approval gate in Step 5 is mandatory and cannot be skipped.
- Always target `main` as the base branch — never another feature branch.
- PR title must be plain language — no ticket IDs, no vague labels like "updates" or "fix".
- If GitHub MCP is not connected, output the PR body to the user and instruct them to open and merge it manually.
- One PR per feature branch — detect and link duplicates instead of creating new ones.
- Never force-merge — if merge fails, stop and surface the error.
- Do not proceed past any failed step — each step is a hard gate.