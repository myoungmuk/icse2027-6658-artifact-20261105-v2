# ICSE 2027 #6658 — Beyond %Resolved

**Beyond %Resolved:Reassessing SWE-bench Through Human and LLM Code Review**

Myeongmuk Kang ([0009-0002-5351-0269](https://orcid.org/0009-0002-5351-0269)) and
Geunseok Yang ([0000-0001-5677-5129](https://orcid.org/0000-0001-5677-5129)),
Hankyong National University.

Corresponding author: **Geunseok Yang** (`gsyang@hknu.ac.kr`), confirmed by the authors.

Version: [`2026.11.05-v5`](https://github.com/myoungmuk/icse2027-6658-artifact-20261105-v2/releases/tag/2026.11.05-v5).
See [README_KO.md](README_KO.md) for the Korean handoff.

This release preserves the historical analysis and separately versions two new,
controlled adaptations of related work. The camera-ready candidate remains **10
pages: 9 body + 1 references**. Publisher rights metadata and final submission
are separate from releasing this research artifact.

## Contents and regeneration

- `paper/`: 10-page manuscript candidate, source, generated tables and figures.
- `historical_analysis/`: preserved packets, saved verdicts, source metadata,
  pinned dependencies, 223-check analysis and upstream license snapshots.
  Follow `historical_analysis/REPRODUCE.md`.
- `binary_pilots/`: two disjoint 20-task pilots, 80 patches in total, 240 fresh
  binary judgments and 40 draft-rubric generations, original prompts/responses,
  selection/exclusion records, frozen protocols and analyses.
- `python tools/reproduce_pilots.py --output <new-directory>` regenerates both
  pilot summaries and CSVs from raw saved responses and compares their hashes.
  This requires only Python standard library; it does not perform new inference.
- `python tools/verify_manifest.py` checks the versioned release inventory.

Frozen manifests inside `binary_pilots/` retain their original machine paths as
historical evidence. They are not rewritten for publication. The portable release
inventory is `MANIFEST_SHA256.json`; archived inference scripts require a new,
explicitly versioned runtime/model-path setup before new inference on another host.

## New comparison: prospective follow-up only

All three adapters use pinned Qwen2.5-Coder-7B-Instruct, greedy decoding, the same
complete issue/candidate inputs, no disclosed execution outcomes, and common
binary output. The follow-up sample has ten officially resolved and ten unresolved
Agentless tasks, plus their twenty developer patches.

| Adapted judge | Functional-label agreement, agent | Unresolved rejected | Developer patches accepted |
|---|---:|---:|---:|
| ICSE test-blind maintainer | 14/20 | 7/10 | 9/20 |
| Cihan binary diff | 13/20 | 7/10 | 8/20 |
| Shi draft rubric | 15/20 | 6/10 | 11/20 |

The initial pilot's strict parser rejected 37 Markdown-fenced responses. Its
primary result is preserved; fence-only recovery is a **post hoc sensitivity
analysis**. Before follow-up inference, fence handling and a disjoint sample were
frozen. All 120 follow-up responses are valid. See the two protocols and raw files.

These are **method adaptations**, not reproductions of the original complete
systems. Cihan's function-level task becomes diff classification without correction
generation. Shi's unrefined draft-rubric ablation uses a developer reference;
actual two-human refinement and human-consensus labels are absent. Its additional
reference access prevents an information-matched superiority comparison.
Inherited functional execution labels are not newly run tests or mergeability
truth. Small samples and wide intervals support no superiority claim.

## Historical limitations preserved

Same-cohort rubric development, joint prompt changes, false test-pass assertions
in the archived negative control, missing hosted snapshot identity, and the
single non-independent human pilot are explicitly disclosed. The new adapted
pilots do not retroactively repair or validate the archived instruments.

See `historical_analysis/THIRD_PARTY_NOTICES.md` and the upstream license snapshots
for third-party materials. This artifact does not relicense upstream code or data;
no blanket license is assigned across the mixed-source historical collection.

## Current factual and publication checks (v5)

The existing human-pilot rater is author-confirmed as Myeongmuk Kang. Prior review
experience and his precise rubric-development role remain undocumented. No new
human reviews, inference or numerical results were added.

The bibliography now has verified page ranges for all 26 cited formal papers:
23 exact DOI records and three official ICLR proceedings records. Eight additional
entries were completed in v5. Agentless is cited under its formal 2025 title,
Demystifying LLM-Based Software Engineering Agents; OpenHands and SWE-bench
Multimodal are cited as ICLR 2025 papers. LLaMA-Reviewer is cited as ISSRE 2023.
Cihan and the Qwen technical report remain identified preprints; the remaining two
citations are the SWE-bench Verified announcement and the Codex software website.
See `bibliography/VERIFICATION.json` and `bibliography/ADDITIONAL_VERIFICATION_V5.json`.
The earlier two HTTP 429 fallbacks remain disclosed; these are not new successful
requests. The manuscript remains nine body pages plus one reference page.
