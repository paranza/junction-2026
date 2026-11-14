# Public Stoa project research

Research for Junction 2026, Stoa's Make Blueprints Talk challenge. All times in the current report are explicit; Europe/Helsinki is UTC+02:00 during this event.

- [Plumbing and complex scans, early Sunday](stoa-plumbing-complex-2026-11-15.md): source-level comparison of OCR, scale, geometry, P&ID candidates and network graphs, with verified public-site limitations and concrete Metria priorities.
- [Current competitor assessment, Saturday evening](stoa-competitors-2026-11-14-evening.md): refreshed public repositories, three browser-verified demo sites, comparison with current Metria and prioritized improvements.
- [Morning differentiation assessment](stoa-differentiation.md): historical feature counts and recommendations. Its claims about unoccupied task areas are superseded by the evening refresh.
- [Morning competitor assessment](stoa-competitors.md): preserved overnight findings and pinned sources, with a dated pointer to the evening update.
- [Original research and comparison](initial-research.md): archived first-pass findings and the improvement plan. Several statements were superseded; use the current assessment for decisions.
- [Current machine-readable snapshot](stoa-competitor-snapshot.json): public repository names, default branches, pinned HEADs, check times and repeatable discovery queries.
- [Morning snapshot, 14 November](stoa-competitor-snapshot-2026-11-14-morning.json): preserved before the evening refresh.
- [Original seven HEADs](initial-heads-2026-11-13.json): the comparison point from 13 November, 23:33 UTC.

We inspect public source text and public commit metadata. A repository is not proof of an independently registered competing team. Code presence, README plans, synthetic mocks, published results and a working deployment are different evidence. Competitor scores have not been independently reproduced. We do not execute competitor code or copy their source into this repository.

## Refresh and monitoring

From the repository root, use Python 3.9 or later, with normal HTTPS certificate verification:

```sh
python3 ops/competitor_watch.py --no-update
python3 ops/competitor_watch.py
python3 -m unittest discover -s ops/tests -v
```

The first command writes a report without advancing local monitoring state. The second preserves successful default-branch checks in `.local/stoa-competitor-watch/`, which is ignored by Git. It compares HEADs, not repository `updated_at` or `pushed_at` alone. Failed requests retain the last successful HEAD and are reported as errors, never as proof nothing changed. Discovered search matches require human qualification before being described as competitors. A repeated candidate is deduplicated in local state. `--skip-search` checks known repositories only.

The helper uses unauthenticated public GitHub REST calls. Rate limiting or an unavailable repository can prevent a complete check. Search is bounded to the first 100 matches per query and reports any truncated coverage. For deeper discovery, paginate the relevant GitHub search, inspect forks and public owner repositories, and check commit/issue search and general web indexes. Newly created repositories may not be indexed yet. The helper is a change detector, not an automatic technical assessment.

Verification on 14 November: seven monitor tests passed, including HEAD-versus-metadata comparison, candidate deduplication, failure preservation and `--no-update`. A live known-repository helper run correctly reported rate-limit errors and did not advance local state. Current snapshot HEADs were separately refreshed through public Git/Atom reads; the live helper run itself did not establish that repositories were unchanged. The returned API reset was 10:33 Europe/Helsinki, before the first scheduled hourly check.

On the original research machine, `/usr/bin/python3` has working HTTPS trust; the separately installed framework `python3` may need its standard certificate setup repaired. Do not disable TLS verification to run the monitor.

An hourly Codex scheduled task was configured in the research chat through **15 November 2026, 10:00 Europe/Helsinki**, the recorded final submission deadline. It checks updates and new discoveries, inspects meaningful diffs, and reports material findings. It stays quiet when nothing meaningful changes. The scheduled task configuration is local to its owner's Codex app; this repo does not install a scheduler on another teammate's computer. Keep that computer on and the app running for local scheduled checks. See the [official scheduling documentation](https://learn.chatgpt.com/docs/scheduled-tasks).

For meaningful changes, append a dated update to the current report, update the public snapshot, and commit only the research changes. Preserve original snapshots and use pinned commit links. Do not commit local reports, credentials, private notes, competitor datasets or copied source trees. Application changes and deployments need their own implementation work.
