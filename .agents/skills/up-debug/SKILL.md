---
name: up:debug
description: Four-phase root-cause investigation for bugs
---

## When to use
- Bug investigation
- Root cause analysis

## Phase 1: Reproduce

Create minimal reproduction:
- What triggers the bug?
- Can you isolate it?
- Document steps to reproduce

## Phase 2: Gather evidence

- Look at logs
- Check database state
- Add temporary debug output
- Examine relevant code

## Phase 3: Form hypothesis

- What could cause this?
- Rank by likelihood
- Design tests to verify

## Phase 4: Fix and verify

- Implement fix
- Verify reproduction no longer works
- Verify existing functionality still works
- Commit

## Output format

```markdown
## Debug: <bug description>

### Phase 1: Reproduction
Steps:
1. ...
2. ...

### Phase 2: Evidence
- <finding 1>
- <finding 2>

### Phase 3: Hypothesis
- H1: <theory> (confidence: 80%)
- H2: <theory> (confidence: 20%)

### Phase 4: Fix
<how it was fixed>

### Verification
- [x] Bug no longer reproduces
- [x] Existing features work
```