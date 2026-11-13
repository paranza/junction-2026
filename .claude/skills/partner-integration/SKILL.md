---
name: partner-integration
description: Establish and document a selected Junction partner API integration, including access, a minimal request, limits and live-versus-mock evidence.
---

# Partner integration

Read [partner notes](../../../docs/partners.md), [decisions](../../../docs/decisions.md) and the provider's current official documentation. Paths are relative to this skill directory.

Confirm the endpoint, supported SDK, credentials, available credits/limits and data usage terms. A sponsor announcement is not proof of account access. Keep secret values out of logs, commits and examples; document only environment variable names.

Within the requested integration scope, make the smallest useful request and inspect its actual response. Check relevant failures such as unavailable credentials, empty results and rate limits. Use bounded retries. Stop repeated paid requests when the same failure persists and report the concrete cause.

Record the working request shape, response fields, timestamp and remaining limits without secret values. Identify fixture or mocked checks explicitly. Do not report a live integration as working until a live call succeeds. Adding an integration does not authorize purchases, account changes, real orders or unrelated external writes.
