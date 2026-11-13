# MUSTA HELMI project instructions

## Context

- Four-person team at Junction 2026, European Tech Renaissance.
- Read README.md and relevant docs before changing the project.
- The selected challenge is Stoa's Make Blueprints Talk. The Trace prototype is in `stoa-trace/`; read its `README.md` and `HANDOFF.md` before application work.
- docs/challenges.md separates observed titles, published clues and hypotheses. Never present a hypothesis as an official requirement or sponsor assignment.
- docs/event.md and docs/submission.md contain event constraints. Check the clock and latest organizer information before submission work; the published hacking start was 2026-11-13 19:30 Europe/Helsinki. Earlier foundation notes and `INFRA/architecture_pipeline.md` describe proposals; the implementation and measured results are documented in `stoa-trace/`.

## Working together

- Use small task branches and pull requests. One person owns each task and its completion criteria.
- Give concurrent coding agents separate worktrees. Coordinate shared interfaces and dependency files before editing them.
- Keep AGENTS.md as the shared source of instructions. CLAUDE.md imports it.
- Record consequential product and stack choices in docs/decisions.md.
- Keep rules and paths portable across teammates' computers.
- Use English, plain language and no em dashes.

## Implementation and verification

- Choose packages only after the challenge and stack are agreed. Pin runtime/package-manager versions and commit the relevant lockfile then.
- Add actual setup, build and test commands to README.md when the application exists.
- Verify the changed behavior with appropriate checks. Report what ran, what passed and what remains untested.
- Keep demo data clearly identified. Do not claim a live integration works when only a mock was tested.
- Keep credentials, private contact details and local agent settings out of Git. Use .env.example for variable names once requirements are known.
- Preserve required third-party notices and check partner data terms before redistribution.

## Team skills

Use the following shared workflows when relevant. Read the linked SKILL.md explicitly if the current assistant does not list it in its skill selector:

- [challenge-fit](.agents/skills/challenge-fit/SKILL.md)
- [partner-integration](.claude/skills/partner-integration/SKILL.md)
- [verify-feature](.claude/skills/verify-feature/SKILL.md)
- [demo-check](.claude/skills/demo-check/SKILL.md)
- [submission-check](.claude/skills/submission-check/SKILL.md)

Claude has entrypoints for all five; challenge-fit is also automatically discoverable by Codex. Windows permissions prevented the other four Codex entrypoints during initialization, so Codex should read their shared files through this list. Availability does not authorize external purchases, messages or submissions.
