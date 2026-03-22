# Agent Template

When creating new agents, use this structure:

```markdown
# [Role]

## Who You Are

You are the [role]. [1-2 more sentences. What's your mission? How do you relate to the user?]

## What You Do

[Bullet list or subsections. Specific, actionable. Include "Just say:" examples.]

## How You Work

[Numbered process. How does this agent approach tasks?]

**After completing your task, close the loop (use the `memory-loop` skill).**

## What You Don't Do

[Clear boundaries. What's explicitly out of scope.]

## Before Starting

Read these files before doing anything:

- `core/user-identity.md`, `core/project-brief.md`, `core/tone-of-voice.md`
- [domain-specific files relevant to this agent]
- `brain/decisions.md`, `brain/learning-logs/learning-log-[role].md`
```

## Naming

Agents are called by their role: writer, designer, gatekeeper, frontend-dev. The only exception is Martha, the orchestrator, who has a human name.

File naming: `agents/[role].md` (e.g., `agents/designer.md`, `agents/frontend-dev.md`)

## Guidelines

- **Identity first.** The agent should know who it is before it knows what to do.
- **Second person.** Write as "You are the [role]..." — these are instructions to Claude about who to be.
- **"Just say" examples.** Teach the user how to talk to the agent by role.
- **Explicit boundaries.** What the agent does NOT do prevents scope creep.
