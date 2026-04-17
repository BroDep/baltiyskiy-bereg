---
name: up:verify
description: Manual smoke testing: positive/negative checks, invariant verification
---

## When to use
- After implementation (`up:execute`)
- Need to verify the feature works correctly

## Input
Read `docs/tasks/<slug>.md` to understand:
- Invariants from design
- Plan items to verify

## Process

### 1. Define checklist

**Positive checks** (should work):
- Feature X works with valid input
- Edge case Y handled correctly

**Negative checks** (should NOT work):
- Invalid input rejected
- Errors handled gracefully

**Invariant checks** (must hold):
- IV-1: <check>
- IV-2: <check>

### 2. Run tests
```bash
# Run project tests
uv run pytest

# Manual verification steps
...
```

### 3. Document results

Update task file:
```markdown
## Verification

### Positive
- [x] Login with valid credentials → success
- [x] Login with invalid credentials → error shown

### Negative
- [x] Empty password → rejected
- [x] SQL injection in username → sanitized

### Invariants
- [x] IV-1: User data never logged in plain text

### Summary
All checks passed / N failures
```

### 4. On failure

If any check fails:
- Log failure details
- Loop back to execute: call `/up:execute` to fix
- Don't mark task complete until all pass