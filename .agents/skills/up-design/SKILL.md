---
name: up:design
description: Discuss requirements, discover invariants, principles, assumptions, unknowns
---

## When to use
- Starting a new task from `/up:make`
- Need to clarify requirements before planning

## Output

Update `docs/tasks/<slug>.md` with:

### Design
- What problem are we solving?
- Why does it matter?
- Scope: what's in/out?

### Invariants (IV)
- Specific things that MUST hold
- E.g., "class Player must not access internals of class Enemy"
- Format: `IV-1: <statement>`

### Principles (PC)
- Soft guidance
- E.g., "prefer composition over inheritance"
- Format: `PC-1: <statement>`

### Assumptions (AS)
- Unverified premises the design rests on
- Will be checked in Conclusion
- Format: `AS-1: <statement>`

### Unknowns (UK)
- Open questions to resolve during plan/execute
- Format: `UK-1: <question>`

### TDD decision
- Decide whether to use test-driven development for this task

## Questions to ask user

1. What is the desired outcome?
2. What are the edge cases?
3. What should NOT happen?

## Output format

```markdown
# Task: <slug>

## Design
<description>

## Invariants
- IV-1: <statement>

## Principles
- PC-1: <statement>

## Assumptions
- AS-1: <statement>

## Unknowns
- UK-1: <question>

## TDD
Yes/No — <reason>
```