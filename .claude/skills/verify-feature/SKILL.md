---
name: verify-feature
description: Verify an implemented MUSTA HELMI feature against observable completion criteria and report actual check results before handoff.
---

# Verify feature

Read the task's completion criteria, relevant changed files and README.md's actual check commands. The repository initially contains no application, so do not invent a build command or report application tests as passing.

Use checks proportionate to the behavior: relevant automated tests, a direct request or the main browser interaction. For user-facing changes, include the affected flow and a meaningful failure or empty state. For AI features, check factual/calculation outputs independently of the model's own explanation.

Distinguish live API checks from fixtures and mocked results. Report commands run, observed outcomes and what remains untested. Fix in-scope issues when authorized; do not silently change another teammate's owned interface. Do not broaden testing after sufficient checks pass unless a new issue justifies it.
