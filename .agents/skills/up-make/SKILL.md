---
name: up:make
description: Orchestrate full task workflow: design → plan → execute → verify → review → update docs
---

## When to use
- User gives a non-trivial task (feature, fix, refactor)
- Need structured approach with documentation

## Usage

### Standard mode
```
/up:make <description>
```

Example: `/up:make fix the flaky login test`

### Hands-off mode
```
/up:make handsoff <description>
```

Agent asks minimal questions, makes conservative choices.

## Workflow stages

1. **Design** — Call `up:design` skill to discuss requirements, discover invariants/principles/assumptions
2. **Plan** — Call `up:plan` skill to create implementation plan
3. **Execute** — Call `up:execute` skill to implement in phases
4. **Verify** — Call `up:verify` skill for manual testing
5. **Review** — Call `up:review` skill for independent review
6. **Docs** — Update project docs

## Task file

All work tracked in `docs/tasks/<slug>.md`:
- `<slug>` = task description slugified (e.g., "fix-the-flaky-login-test")
- This file is the source of truth
- Any new agent can read it and continue

## Principles

- Don't delete things (copy and rename instead)
- Work in git branch
- Use conservative defaults
- Fix only critical/important issues
- One conversation per feature
- Clear context between stages

## Hands-off mode rules

- Ask max 3 clarifying questions upfront
- Log all non-obvious decisions in task file
- Never introduce silent defaults/fallbacks
- If stuck, ask user for direction
- End with summary of what was done