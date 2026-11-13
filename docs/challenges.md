# Challenge research

Research date: **13 November 2026**. No challenge has been selected.

## Evidence and limits

- **Observed:** all 19 names below were transcribed in order from the teammate's dashboard dropdown [screenshot](assets/challenge-titles.png). A highlighted row is not a confirmed team choice. Names preserve the screenshot wording, including "Aaltonomous" and the period after "Wikipedia Through Time."
- **Published clue:** an organizer announcement or workshop description gives some context. It still does not replace the full challenge brief.
- **Inference:** a possible interpretation of a title. Example prototypes are brainstorming, not requirements.

Public exact-title searches did not reveal complete briefs. Public announcements supply useful partial evidence for Cala, S-Pankki and physical AI. Sponsor guesses are explicitly marked below.

## All 19 titles

| # | Title from screenshot | Likely scope and evidence | Example small demo, our idea only | Confirm before committing |
| --- | --- | --- | --- | --- |
| 1 | The Internet Butler / Your Personal Assistant | Inference: an assistant that completes everyday web tasks, possibly across services. | Research one purchase, compare options and ask the user to confirm the next action. | Required tools; read-only research versus actual actions; provided accounts and APIs. |
| 2 | Wikipedia Through Time. | Inference: explore article history or answer questions using knowledge from a chosen date. Could instead mean a historical learning experience. | A timeline showing how one article and its cited claims changed, linked to revisions. | Revision data versus historical subjects; languages; scale and permitted datasets. |
| 3 | Personal Economic Trainer | Published clue: S-Pankki describes conversational money understanding using synthetic banking transactions. [S3] | Explain a spending pattern and show a transparent savings scenario computed from sample transactions. | Dataset schema, required calculations, scoring and allowed advice scope. |
| 4 | Rethinking Recruitment | Inference: improve matching, skills assessment or recruiter/candidate workflows. | Match a small set of candidates to a role using visible evidence and explain missing information. | Target user, supplied data, evaluation criteria and required fairness controls. |
| 5 | Aaltonomous Humanoid | Inference: humanoid autonomy; the spelling suggests Aalto, which is publicly announced as a challenge partner. The title-to-partner link is unconfirmed. [S3] | One bounded perception-to-action task on the provided robot or permitted simulator. | Exact robot, access slots, SDK, safety process and whether simulation qualifies. |
| 6 | The Robot Teleoperation Challenge | Inference: remote human control of a robot, possibly including feedback or learning from demonstrations. | Operate one pick-and-place task with clear operator feedback. | Hardware, input device, network latency and judged task. |
| 7 | Trusted Trade Agents | Inference: trustworthy agents for procurement, commerce or negotiation. The title alone does not identify the trade domain. | Compare offers and produce an explainable order proposal with a spending limit and approval step. | Partner, market, mock versus live transactions, identity and approval requirements. |
| 8 | Break the Agent | Inference: test an AI agent's robustness or security, possibly an adversarial evaluation challenge. | Reproduce failures in an authorized test agent and show before/after defense results. | Provided target, permitted testing scope and scoring. |
| 9 | Stop Simulating, Start Moving: See It. Detect It. Act on It. The Intel Physical AI Challenge | Intel is named in the title. An organizer announcement describes Intel x Ignite Next working with robot arms and cameras. [S3] | Detect one object type and move it to a specified location. | Required hardware/software, physical execution criteria and equipment availability. |
| 10 | The Web Is Your Real-Time Database | Inference: search and extract fresh web information into structured, queryable records. Context.dev is a plausible partner because Junction announced its live-web/structured-data APIs, but the title mapping is unconfirmed. [S3] | Track a small set of changing facts with source links, timestamps and detected changes. | Partner, extraction/search APIs, freshness requirement and usage limits. |
| 11 | Make Blueprints Talk | Inference: question-answering or extraction over architectural/engineering drawings, perhaps CAD or BIM. | Answer a question about a supplied plan and highlight the source region. | File formats, sample drawings, expected geometric accuracy and domain. |
| 12 | AI Glasses for Everyone, Everyday | Inference: a practical wearable AI or AR experience, possibly accessibility or hands-free assistance. | Complete one everyday task using the provided glasses and their supported inputs. | Device, SDK, hardware access and whether a phone/browser substitute is allowed. |
| 13 | Beyond the Clinic | Inference: support outside clinical visits, such as follow-up, care coordination or home monitoring. No specific sponsor mapping is confirmed. | Turn a supplied fictional care plan into a clear follow-up checklist and handoff summary. | Target population, clinical versus administrative scope and approved data. |
| 14 | Equal Care Across Finland | Inference: improve access to care across regions, languages or patient groups. | Compare service availability and explain one access gap using provided or approved public data. | Intended inequality, Finnish datasets, geographical scope and success metric. |
| 15 | Spread | Low-confidence inference: could concern information distribution, financial spreads, disease spread or something else. | No meaningful prototype recommendation until the partner and brief are known. | What does "spread" refer to? This title is too ambiguous to rank. |
| 16 | Make Unicorns Real | Published clue: Cala's workshop links this to founder/VC needs and connected company, people, investor and funding data. [S2] | Produce an evidence-backed investor shortlist with relationship paths and reasons for each match. | API access, data coverage, required Cala usage and partner judging criteria. |
| 17 | Earned Trust in AI Code | Inference: establish confidence in AI-generated code through checks, evidence or review. | Compare a generated patch against independent tests and present failures with reproducible evidence. | Required coding tools, target languages, benchmark and definition of trust. |
| 18 | The Green European Renaissance | Inference: sustainability, energy, circularity or climate applications in a European setting. | Compare two resource-use scenarios with explicit assumptions and a measurable outcome. | Specific sector, supplied data, partner and how impact is judged. |
| 19 | Decode the Noise | Low-confidence inference: extract signal from noisy audio, sensor data, documents or information streams. | Demonstrate one detection/extraction task against a small labeled sample once the modality is known. | Data modality, target signal, baseline and scoring metric. |

## What to inspect first

For a team choosing a software project without guaranteed hardware, our provisional research order is:

1. **Make Unicorns Real:** relatively concrete public context and a clear business user.
2. **Personal Economic Trainer:** concrete public context and synthetic data; verify dataset access and expected calculations.
3. **The Web Is Your Real-Time Database:** potentially a fast end-to-end demo if the partner supplies usable APIs.
4. **Earned Trust in AI Code:** potentially measurable outcomes, provided the team can design independent checks.
5. **Make Blueprints Talk:** potentially a clear visual demonstration, but document formats and geometry could dominate the weekend.

This ranks what to investigate, not expected winning chances or team fit. We do not yet know all four teammates' skills. Hardware tracks become much more attractive if a teammate has relevant experience and the equipment is immediately available.

## Questions for every partner

- Who is the user, what problem matters and what is the required output?
- What are the judging criteria and mandatory technologies?
- Can we get a working sample request or dataset immediately?
- What limits, costs, licenses or hardware queues could block the demo?
- Can one small user flow demonstrate innovation, impact and implementation?
- Does the proposed use qualify for this challenge and any additional challenge we enter?

## Sources

- **S1:** [Dashboard screenshot supplied by teammate](assets/challenge-titles.png), received 13 November 2026. Titles only. Organizer UI remains third-party material.
- **S2:** [Official Junction 2026 website](https://2026.hackjunction.com/), Cala workshop description and Hardware Lab information, checked 13 November 2026. The same Cala context appears in the supplied participant guide.
- **S3:** [Junction's official LinkedIn page](https://fi.linkedin.com/company/hackjunction), checked 13 November 2026. Visible announcements identify S-Pankki's Personal Economic Trainer, Aalto as a challenge partner, Intel x Ignite Next's robot/camera activity, and Context.dev's API capabilities. The feed changes; replace this link with exact challenge briefs when published.

No public description found is not proof that no description exists. Check the authenticated dashboard and mentor channels when challenges are released. Do not probe hidden endpoints to fill missing briefs.
