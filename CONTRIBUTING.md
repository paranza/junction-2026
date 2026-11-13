# Working together

## Before taking a task

Create an issue using the task template, or agree the same details in the team chat: owner, intended outcome, files likely to change and a visible completion condition. Check docs/decisions.md for current choices.

## Branches and reviews

1. Clone the repo into your own local folder.
2. Start from current main and create a short branch such as feature/search or docs/challenge-notes.
3. Keep a change small enough for another teammate to review quickly.
4. Open a pull request with what changed and the checks you actually ran.
5. Have another teammate review it, then merge and update main locally.

One integration owner coordinates merges and shared API/schema changes. This is a team convention; remote branch protection has not been configured.

## Agent sessions

Each person owns the output of their assistants. Give tasks a scope and completion condition. Use a separate Git worktree for simultaneous writers on one computer. Ask research/review agents to report findings before changing another person's area.

## First application commit

Once hacking has started and the team selects a challenge:

- Record the stack, runtime version and deployment target in docs/decisions.md.
- Add the application, lockfile and a secrets-free .env.example with only the variables actually used.
- Document fresh-clone installation and the dev/build/check commands in README.md.
- Add CI for those real commands and verify a minimal deployed user flow.

There is currently no application to install, build or test.
