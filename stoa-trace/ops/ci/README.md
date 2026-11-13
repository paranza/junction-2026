# CI template

`github-actions.yml.example` is a GitHub Actions workflow for the application tests, frozen benchmark-manifest validation and frontend production build. Those checks also ran locally in the handoff checkout.

The handoff credential has repository push permission but no `workflow` scope, and GitHub rejected publishing the active workflow. The template is therefore stored here without enabling automation or changing account permissions.

A maintainer using credentials permitted to update workflows can copy the file to `.github/workflows/stoa-trace.yml` in the repository root and commit it. It uses the `stoa-trace/` subdirectory, Python 3.11, the pinned Node/npm setup, and no provider API secrets. The unit suite uses fixtures and the benchmark invocation is a dry run; no paid model requests are made.
