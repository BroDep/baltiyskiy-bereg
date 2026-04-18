---
name: up:execute
description: Implement task in phases: create branch, code, test, commit incrementally
---

## When to use
- After plan is ready (`up:plan`)
- Time to write actual code

## Input
Read `docs/tasks/<slug>.md` to understand plan, phases, interfaces.

## Steps

### 1. Create git branch
```bash
git checkout -b task/<slug>
```

### 2. Execute phases in order
For each phase in plan:
1. Read relevant files
2. Implement changes
3. Run tests
4. Commit with descriptive message

### 3. Check consistency
After each phase:
- Verify against plan (all items done?)
- Check invariants still hold
- If not, either fix or escalate to user

## Principles

- One commit per phase
- Commit message: "Phase N: <what>"
- Don't delete files — copy and rename instead
- If TDD: write failing test → make change → test passes

## Progress tracking

After each phase, update task file:
```markdown
### Completed
- [x] Phase 1: Create LoginValidator class
```

## If blocked

If stuck:
1. Document what was tried
2. Ask user for direction
3. Use `/up:step-back` to reassess