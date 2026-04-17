---
name: up:plan
description: Create implementation plan: files, classes, methods, interfaces, test strategy, phases
---

## When to use
- After design is complete (`up:design`)
- Need to break down implementation into phases

## Input
Read `docs/tasks/<slug>.md` to understand design, invariants, principles.

## Output

Update task file with:

### Files to change
- List of files with action (create/modify/delete)
- E.g., `src/auth.py` — modify, add `LoginValidator` class

### Classes/Methods
- What classes/methods to create/update
- Their interfaces (signature, params, return)

### Test strategy
- How to test this feature
- Unit tests? Integration? Manual?

### Phases
Break implementation into ordered phases:
- Phase 1: <description>
- Phase 2: <description>
- ...

### Order of execution
Define which phase first, dependencies between phases.

## Rules

- Only include non-trivial code blocks in plan
- Keep code examples minimal
- Reference invariants by ID (IV-1, PC-2, etc.)
- No actual implementation code yet

## Output format

```markdown
## Plan

### Files
| File | Action | Description |
|------|--------|-------------|
| src/auth.py | modify | Add LoginValidator class |

### Interfaces
- `LoginValidator.validate(credentials) -> bool`

### Test Strategy
- Unit tests for LoginValidator
- Integration test for login flow

### Phases
1. **Phase 1**: Create LoginValidator class
2. **Phase 2**: Integrate with auth module
3. **Phase 3**: Add tests

### Dependencies
- Phase 2 depends on Phase 1
```