# Tone of Voice

## Context

This is an internal tool project. There is no external audience, no brand to project. "Tone of voice" here means: how the team communicates with the user, and how the CLI output communicates with the operator.

## Principles

**Clear over clever.**
No jargon, no unnecessary abstraction. If there's a simpler word, use it.

**Direct.**
Say what the system is doing. No fluff. CLI output should be informative: what ran, what succeeded, what failed.

**Functional.**
The product doesn't need to feel good — it needs to work reliably. Communication should reflect that: honest status, clear errors, no decorative language.

**Explain, don't decorate.**
When a decision needs to be made, explain it plainly. No metaphors, no marketing language. This user wants to understand the mechanism.

## For CLI Output (when writing messages, logs, or prompts)

- Use plain language: `✓ PDF generated` not `🎉 Your member list is ready!`
- Errors should say what went wrong and where: `Error: Could not connect to WordPress API (check WP_API_KEY in .env)`
- Progress messages should be brief: `Fetching members from WordPress...`

## Language

English for all communication with the user, code, variable names, file paths, and CLI output.
