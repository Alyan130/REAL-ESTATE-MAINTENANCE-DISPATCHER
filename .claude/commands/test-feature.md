---
description: Use this when you are asked to test a feature.
---

## User Responsibility
You must be on the correct feature branch before invoking this command.
```bash
git branch --show-current
```
If you are not on the right branch — stop, switch, then proceed.

---

## Steps

### 1. Check for Existing TestSprite Config
```bash
cat .testsprite/config.json
```
- **Config EXISTS** → skip Step 2, go directly to Step 3
- **Config does NOT exist** → run Step 2 first

### 2. Bootstrap (First Time Only)
Only run this once per project. Never run it again after `config.json` exists.
```
testsprite_bootstrap_tests({
  localPort: <dev-port>,
  type: "frontend" | "backend",
  projectPath: "<absolute-project-path>",
  testScope: "diff"
})
```
When the browser config portal opens:
- Set scope to **Code Diff** — tests only the feature branch changes
- Upload `docs/features/<feature-name>/plan.md` as the PRD
- Enter app URL and credentials if login is required

### 3. Read Feature Docs
Go to `docs/features/<feature-name>/` and read:
- `plan.md` — what the feature does (used as PRD source of truth)
- `architecture.md` — which codebase areas are involved

Pass this context in all subsequent steps so TestSprite knows exactly what to test.

### 4. Generate Code Summary
```
testsprite_generate_code_summary({
  projectRootPath: "<absolute-project-path>"
})
```

### 5. Generate PRD
```
testsprite_generate_standardized_prd({
  projectPath: "<absolute-project-path>"
})
```

### 6. Generate Test Plan
**Frontend:**
```
testsprite_generate_frontend_test_plan({
  projectPath: "<absolute-project-path>",
  needLogin: true | false
})
```
**Backend:**
```
testsprite_generate_backend_test_plan({
  projectPath: "<absolute-project-path>"
})
```

### 7. Execute Tests
```
testsprite_generate_code_and_execute({
  projectName: "<project-root-name>",
  projectPath: "<absolute-project-path>",
  testIds: [],
  additionalInstruction: "Test only the <feature-name> feature based on the provided plan and architecture."
})
```

### 8. Review Results in Dashboard
```
testsprite_open_test_result_dashboard()
```
Agent reads results, identifies failures, and applies TestSprite's fix recommendations.

### 9. Fix & Rerun
```
testsprite_rerun_tests({
  projectPath: "<absolute-project-path>"
})
```
Repeat until all tests pass.

---

## Rules
- Check for `config.json` first — never run bootstrap on an already configured project.
- Always read `plan.md` and `architecture.md` before generating tests.
- Always use `testScope: "diff"` — feature changes only, not the full codebase.
- Never push to GitHub until all tests pass.
- Agent must act on TestSprite fix recommendations — never ignore them.