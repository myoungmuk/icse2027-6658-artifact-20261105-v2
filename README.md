# ICSE 2027 #6658 — Beyond %Resolved

**Beyond %Resolved:Reassessing SWE-bench Through Human and LLM Code Review**

Myeongmuk Kang ([0009-0002-5351-0269](https://orcid.org/0009-0002-5351-0269)) and
Geunseok Yang ([0000-0001-5677-5129](https://orcid.org/0000-0001-5677-5129)),
Hankyong National University.

Corresponding author: **Geunseok Yang** (`gsyang@hknu.ac.kr`), confirmed by the authors.

Version: [`2026.11.06-v14`](https://github.com/myoungmuk/icse2027-6658-artifact-20261105-v2/releases/tag/2026.11.06-v14).
See [README_KO.md](README_KO.md) for the Korean handoff.

This release adds residual CPU diagnostics for four archived failing candidates,
while preserving historical analysis, earlier adaptations and native saved-output replays. The camera-ready candidate remains **10
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

## Factual and publication checks recorded in v5

The existing human-pilot rater is author-confirmed as Myeongmuk Kang. Prior review
experience and his precise rubric-development role remain undocumented. That v5
update added no human reviews, inference or numerical results.

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

## v6 clarification and saved-response analysis

The configuration is called adjusted, with historical calibrated labels preserved.
The redundant scale plot is omitted from the manuscript layout; its source is retained.
The text clarifies the illustrative 14B anchor, rationale and post-merge limits, and
the worked diagnostic decision. Two deterministic hosted-rationale examples and the
small same-task control analysis are in [analysis_supplement_v6](analysis_supplement_v6/README.md).
These are descriptive additions, not new inference or independent maintainer validation.
The manuscript remains 9 body pages plus one reference page, with unchanged class,
font size, margins, numerical inputs and bibliography.

## v7 focused technical rationale checks

The new [six-case audit](rationale_case_audit/README.md) checks exact archived
patches against pinned upstream source. Five focused claims have local support;
the django-11179 gold objection about regular-path PK cleanup is contradicted by
existing code. These are post-hoc source/function/branch probes with explicit
synthetic inputs and backend stand-ins, not full integration tests, independent
human ratings or a reviewer correctness rate. Historical outputs are preserved.

    python tools/probe_rationale_cases.py --output /path/to/new-output-directory

For local upload preparation and optional supplied portal evidence, use:

    python tools/verify_submission.py --output /path/to/new-check.json

This tool follows this checkout's metadata and PDF, checks PDF metadata and visible
title separately, and accepts --downloaded-pdf and --system-title-file. It performs
no network access or upload and does not authenticate the supplied files' origin.
The six-case probe uses Python standard library; the PDF checker requires PyMuPDF.
The historical v6 supplement remains preserved; v7 adds technical evidence for
its two resolved-agent examples and four further cases.

## v8 full-split controls and scoped post-merge histories

The separately frozen test-blind 7B extension evaluates all 300 Lite and 500 Verified
gold memberships (707 unique tasks; 93 shared), plus 302 unresolved candidates.
All 1,009 calls complete: 1,006 outputs are valid and three malformed JSON responses
remain failures. Gold acceptance is 143/299 valid on Lite and 284/499 on Verified.
Among 300 complete same-task failing/developer pairs, acceptance is 135/300 versus
149/300, with discordant counts 47/61 and exploratory exact McNemar p=.211.
Four empty candidates and two incomplete pairs are explicit. See `full_split_control/`.
This does not revalidate historical 14B/hosted instruments or independently develop
calibration.

`postmerge_history/` follows 365 days after all three hosted nonaccepted gold PRs.
File commits of 12/93/35 are churn, not defect counts. Matplotlib issue 27103 explicitly
identifies the original PR source commit; fix 27179 and its regression test and release
note align with the empty-bin concern. No matching regression was found for the other
two specific concerns in this scoped inspection. Other branches, renames and indirect
effects remain outside scope. Public follow-up predates the 2026 judging.

    python tools/reproduce_full_split.py --output /path/to/new-analysis-directory

This command uses saved outputs, not new inference. Archived freeze manifests retain
machine paths; new inference elsewhere requires a new explicit setup. No new human
ratings or harness runs are included. The paper stays at 9 body + 1 reference pages,
with unchanged class, font size, margins and historical numerical inputs.


## v9 targeted database checks and primary-source clarification

The [two-case SQLite follow-up](database_rationale_checks/README.md) uses complete
pinned Django packages, five variant processes and 15 targeted scenarios. It
contradicts the focal gold stale-PK objection and supports the focal failing
candidate filter objection. It is not a full test suite, independent adjudication
or a reviewer accuracy estimate. Startup failures and runtime compatibility are
retained explicitly. A three-cohort saved-output census indexes 7,011 records and
prepares 3,262 nonaccepted outputs for later review; it does not adjudicate them.

The paper explicitly distinguishes LLaMA-Reviewer's binary review-necessity task
and RovoDev's binary comment selection from patch acceptance. Paper-linked
replication materials for the IST work and LLaMA-Reviewer were located and their
availability checked; no original-system inference is claimed. The paper remains
nine body pages plus one reference page. All older inputs/releases are preserved.


## v10 prospective task-disjoint configuration selection

The [new study](task_disjoint_calibration/README.md) excludes all 707 prior tasks,
uses 40 development and 100 heldout tasks, and seals a development-only selection
before heldout inference. Two frozen test-blind 7B configurations see the same
issue/diff inputs. Of 560 planned inputs, 558 generations run and two overlength
inputs are explicitly skipped. Full outputs, source receipts, frozen code and
portable offline analysis are included. This is a new finite configuration study,
not historical calibration recovery or independent maintainer validation. No
human ratings or new harness runs are added. The paper remains 9+1 pages; earlier
release assets and historical inputs are preserved.


## v11 actual official regression tests

The [38-case audit](official_regression_audit/README.md) runs official regression
targets against complete pinned source variants. All candidates fail and all
developer controls pass. There are 114 final processes, 387 executed test slots,
60 skips and 24 preserved earlier infrastructure attempts. Raw results, frozen
inputs, source receipts, evidence cards and offline recomputation are included.
This supports functional rejection within one hosted-reviewer stratum; it is not
independent adjudication of every rationale. No new inference or human ratings.
The paper remains 9+1 pages. Prior release assets and historical results remain.


## v12 gold and original saved-output evidence

The [new follow-up](nonhuman_followup/README.md) runs full packages for all three
hosted nonaccepted gold patches and replays original saved outputs from three
prior works. Matplotlib's default empty-bin regression is reproduced despite an
official test pass; sklearn's omitted argument has no output effect in four
tested configurations. Raw controls, diagnostic variants, source hashes, native
saved outputs, separate invalid-response accounting and offline scripts are
included. These are targeted technical findings, not independent human labels,
fresh native-model inference or all-system same-task comparisons. Checklist
coverage remains 49/58(84.48%). The manuscript stays9+1 pages; prior releases remain.


## v13 residual CPU diagnostics

See [residual_diagnostics](residual_diagnostics/README.md) for4 post-hoc cases,
26 final processes,122 executed test slots and51 witness scenarios. Separate
warning-policy and import-only interventions expose deeper functional effects;
PCA provides a normal-path qualification. No new human ratings or model inference.
Checklist coverage remains 49/58(84.48%); the paper remains9+1 pages.


## v14 fresh 14B inference

See [rerun_14b](rerun_14b/README.md). All 2,197 archived 14B configurations
receive a fresh known-condition rerun, followed by 560 planned inputs on 140 new
development/heldout tasks. Actual model calls: 2,756.
Exact historical runtime identity remains unknown; archived false negative-control
instructions remain explicitly flagged. No human ratings or native Cihan/Shi full
pipeline. Paper 9+1 pages; checklist 49/58(84.48%). Prior releases remain.
