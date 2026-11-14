# Deployment verification

The existing protected deployment is <https://stoa-86-38-182-146.sslip.io>. Credentials remain in private local configuration. No second VM is required.

Last completed deployment at the time of this note: `9486581`, 14 November 2026. The later unknown-upload improvements and Gemini adapter still require the next validated deployment.

Verified on the actual VM:

- Unauthenticated request rejected with 401; authenticated health succeeded with all 913 original documents.
- Native IFC answer: 211 doors with 211 source evidence items; PNG preview rendered.
- Review persistence: temporary exclusion changed the count to 210, then restoring the actual object returned it to 211. Reload, JSON export and container restart preserved 211.
- Four real hosted unknown-upload requests completed; see `generalization-report.md`. The model-attempt ledger reached four and was not reset.

Before replacement, Docker image and SQLite backups were made on the existing host. Every later sync/start must preserve `/srv/stoa/data`, source counts, saved answers, review history and the existing model-attempt ledger. Provider keys transfer over encrypted SSH stdin and never enter build archives or Git.

For the next deployment, run production Python checks, frontend tests/build and the development native regression, then `ops/deploy_verda.py sync`, `start` and `ops/verify_remote.py --exercise --restart`. Gemini needs a private key and a successful real request before it is described as live. Future deployment checks must update this note with the actual tested revision and results.
