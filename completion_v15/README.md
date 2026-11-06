# v15 author-experience disclosure and submission preparation

The candidate manuscript remains **10 pages (9 body + 1 references)**. This update reports retrospective author clarification: the pilot rater checked code/data correctness in his own research and recalls no experience modifying others' code. Duration and rubric-design involvement remain undocumented; professional or independent review expertise is not established. The pilot remains one non-independent author and no new human judgments are added.

The original v14 scientific outputs, protocols, release assets and tags are unchanged. Reviewer-item coverage is 50/58 (86.21%), with 5 partial, 1 unexecuted and 2 historical-record gaps. This is neither an acceptance probability nor completed submission.

A **post-hoc** check uses the existing 100 heldout tasks from 10 repositories. Django accounts for 38%; the repository-cluster bootstrap interval for adjusted-minus-strict is -2.78 to +11.72 percentage points. Frozen primary results stay 54.5% proxy agreement (task-bootstrap CI49–60) and +2pp versus strict (CI-4–+8). Neither analysis establishes reliable operational merge judging or a clear improvement. These proxies are not maintainer truth.

Replay the new sensitivity check from saved public v14 raw outputs:

```bash
python completion_v15/tools/reproduce_repository_sensitivity.py --output /tmp/icse-v15-repository-check
```

Compare submission evidence using `completion_v15/tools/verify_submission.py`. Its default PDF and metadata refer to this candidate. No portal upload is performed.

**Distinct deadlines:** Major Revision: 2026-11-17 23:59:59 AoE; directly accepted camera-ready: 2026-11-24 AoE; accepted major-revision camera-ready: 2027-01-25 AoE. Paper-specific decision and private author instructions remain unverified. A public deadlines page does not establish a paper decision.

Official guidance: https://conf.researchr.org/track/icse-2027/icse-2027-research-track
Paper login: https://icse2027.hotcrp.com/paper/6658
