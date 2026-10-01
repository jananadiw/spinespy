<!-- BEGIN:agent-rules -->

# Agent Entry Point
## Instruction Priority

1. System and developer instructions.
2. Global rules in `~/.agents/AGENTS.md`.
3. Task-specific source files.

## Workflow

- Use `Discuss -> Plan -> Execute -> Verify`.
- Do not code before plan approval unless the user asks for a mechanical edit.
- During planning, name assumptions, success criteria, and likely `context/TREE.md` nodes.
- During execution, inspect nearby source first and keep edits scoped.
- During verification, check behavior, tests or lint, orphaned code, and decision drift.

## Retrieval

- Keep context stingy; start with `context/TREE.md`.
- Use `README.md` only for setup, stack, or full structure.
<!-- END:agent-rules -->
