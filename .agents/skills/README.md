# Skill Creator — How to Create and Improve Skills

This skill helps you create new skills for the Baltiyskiy Bereg project using best practices.

---

## What is a Skill?

A skill is a reusable set of instructions for AI agents to perform specific tasks consistently and effectively.

---

## When to Create a Skill

Create a skill when:
- A complex task is performed repeatedly
- The task requires specific steps that are easy to forget
- The task has input/output contracts that need to be clear
- Multiple agents need to perform the same task

---

## Skill Template

Every skill should follow this structure:

```markdown
# [Skill Name]

## Purpose
What this skill does and why it exists.

## When to Use
When to invoke this skill.

## Input
What the skill expects (parameters, context).

## Output
What the skill produces (files, changes, results).

## Steps
1. Step one
2. Step two
3. ...

## Examples
### Example 1
```
Expected input → Expected output
```

## Best Practices
- Practice 1
- Practice 2

## Self-Improvement Notes
This section is updated when the skill is used and improved.
```

---

## Creating a New Skill

### Step 1: Identify the Need
- Is this task repetitive?
- Do multiple steps need to be remembered?
- Is there a specific output format?

### Step 2: Draft the Skill
Use the template above. Keep it concise but complete.

### Step 3: Review and Improve
After using the skill:
- Note what worked well
- Note what could be improved
- Update the self-improvement section

### Step 4: Store in `.agents/skills/`
```
.agents/skills/
├── README.md           # This file
├── [skill-name].md    # Your new skill
└── templates/
    └── skill-template.md
```

---

## Skill Naming Convention

- Use lowercase with hyphens: `db-query.md`, `api-integration.md`
- Name by action: `create-api-endpoint`, `write-tests`
- Be descriptive but concise

---

## Best Practices

### Do
- ✅ Keep skills focused on one task
- ✅ Include concrete examples
- ✅ Specify input/output clearly
- ✅ Add error handling notes
- ✅ Include self-improvement section
- ✅ Update skills after using them

### Don't
- ❌ Make skills too long (max ~100 lines)
- ❌ Duplicate functionality from other skills
- ❌ Include sensitive information
- ❌ Make skills too generic

---

## Self-Improvement Protocol

After using any skill:

1. **Evaluate**: Did it work as expected?
2. **Identify**: What was confusing or missing?
3. **Update**: Add notes to the skill
4. **Commit**: Save improvements

```markdown
## Self-Improvement Notes
- [Date] Improved by [Agent]: Added step about X
- [Date] Fixed Y because it caused Z error
```

---

## Examples of Good Skills

See existing skills in this folder for reference.

---

## Related Skills

- [TBD: Add related skills as you create them]
