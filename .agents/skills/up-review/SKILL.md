---
name: up:review
description: Independent code review: check invariants, find bugs, assess quality
---

## When to use
- After verification (`up:verify`)
- Need independent review before finishing

## Input
Read `docs/tasks/<slug>.md` to understand:
- Design (invariants, principles, assumptions)
- Plan (what was implemented)
- Verification results

## Process

### 1. Read changed files
```bash
git diff main...HEAD --stat
```

Review each changed file.

### 2. Check invariants

For each invariant (IV-1, IV-2, etc.):
- Does the code maintain it?
- Are there any violations?

### 3. Check plan coverage

For each plan item:
- Is it implemented correctly?
- Any missing functionality?

### 4. Find bugs

Look for:
- Logic errors
- Missing error handling
- Security issues
- Performance problems

### 5. Rate findings

Confidence levels:
- ≥80%: High confidence bug
- 60-79%: Likely issue
- <60%: Possible improvement

Severity:
- Critical: Must fix
- Important: Should fix
- Minor: Nice to have

## Output

Update task file:
```markdown
## Review

### Invariant Checks
- [x] IV-1: PASS - <explanation>
- [ ] IV-2: FAIL - <explanation>

### Bug Findings

| # | Description | Severity | Confidence |
|---|-------------|----------|-------------|
| 1 | Memory leak in connection | Critical | 85% |
| 2 | Missing null check | Important | 90% |

### Recommendations
- Consider adding logging
- Refactor duplicated code
```

## If critical issues found

- Don't finish task
- Go back to execute: fix issues
- Re-verify