# Team tools and agents

## Everyone's setup

1. Install Git and your preferred editor. Use individual accounts and repository invitations.
2. Install or enable at least one coding assistant: [Codex](https://learn.chatgpt.com/docs/cli) or [Claude Code](https://code.claude.com/docs/en/setup). Use both if useful and available to your account.
3. Clone this repository and start the assistant in its root folder.
4. Ask it to summarize AGENTS.md and the current decisions, then check it has the right context.
5. Verify one team skill is discoverable. Codex uses `$challenge-fit`; Claude Code uses `/challenge-fit`.

No project packages are installed yet. There is no application to launch. Native Windows/PowerShell is a valid starting point; do not switch a teammate's environment without a concrete need.

## Shared instructions and skills

Codex reads [AGENTS.md](../AGENTS.md); [CLAUDE.md](../CLAUDE.md) imports that same file for Claude Code. Personal preferences should not contain paths or assumptions that other teammates need to reproduce.

The challenge-fit workflow lives under .agents/skills, with a Claude entrypoint linking to it. The other four workflows live under .claude/skills. AGENTS.md links every workflow explicitly so either assistant can read the same procedure without Windows symlinks or duplicated instructions.

Initialization limitation: Windows denied further writes inside .agents even through the runtime approval path. All five skills are discoverable by Claude; only challenge-fit is automatically discoverable by Codex. In Codex, ask to use the relevant workflow linked from AGENTS.md. Add the other four Codex entrypoints when that directory's permissions are resolved through the normal environment settings.

| Skill | Use |
| --- | --- |
| challenge-fit | Compare a proposed idea with actual criteria and current evidence |
| partner-integration | Establish a documented, working partner API integration |
| verify-feature | Verify observable behavior and distinguish live from mocked checks |
| demo-check | Rehearse the user flow, video, live pitch and fallback |
| submission-check | Check submission fields, access, timing and FINAL status |

Official references: [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Claude skills](https://code.claude.com/docs/en/skills), [Claude instruction imports](https://code.claude.com/docs/en/memory).

## Agent assignments

Start with one human owner and one coding agent per task. Use a fresh review session for important changes. Additional research or verification agents are useful when their inputs and outputs are clearly bounded; they do not need permanent persona files.

Example task:

> Implement [feature] in [files/folder]. Done means [observable result]. Coordinate shared interface changes with [owner]. Run [actual check commands] and report what remains untested.

For simultaneous coding sessions on one computer, give each its own branch and worktree. Agree API shapes and designate one owner for shared dependency files before parallel implementation.

## Packages after choosing the stack

- For a web app, choose one [Node.js LTS](https://nodejs.org/en/download) version and one package manager, for example [pnpm](https://pnpm.io/installation). Pin versions and commit the lockfile.
- Use the selected framework's standard formatter/linter/check commands. Add [Playwright](https://playwright.dev/docs/intro) for the main browser flow when appropriate.
- For Python, [uv](https://docs.astral.sh/uv/) is a possible environment/dependency manager. Choose it only if Python is needed.
- Use the [official OpenAI SDK](https://developers.openai.com/api/docs/libraries) or [Anthropic SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/overview) when the product actually uses that provider.
- Add a database, deployment service or tool connector when the chosen user flow requires it. Record credentials separately and configure only the access the task needs.

First application milestone: every teammate can install from a fresh clone, run the same user flow and see a deployment pass the documented checks.
