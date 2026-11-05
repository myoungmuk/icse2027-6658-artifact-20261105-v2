# How the two reviewer configurations differ

Both configurations already assert that automated tests pass. The adjusted configuration
jointly adds an explanation that held-out test files are intentionally absent and narrows
what should count as a merge-blocking concern. The user template is shared; an extra reminder
is appended in the adjusted setting. `PROMPTS.md` preserves the complete templates.

| Component | Naive | Adjusted |
|---|---|---|
| System test context | "The PR's automated tests already PASS" | Explicit reproduction/regression test-pass assertion and explanation of intentionally absent test files |
| Blocking criterion | Rigorous and skeptical maintainer review | Explicit refusal-to-merge criterion; style nits/optional tests are minor |
| User heading | Tests already pass | Same |
| Final reminder | None | Repeats pass assertion, omitted-test explanation and narrower blocking criterion |

This is a comparison between jointly changed configurations, not a factorial ablation.
Gold from the evaluated cohort informed the adjustment. There is no independent held-out
development guarantee or recoverable history of intermediate rubric edits.

The failing-patch path reused the adjusted templates unchanged, including all three pass
assertions. This was incorrect information for those candidates. The reported failing-patch
rates are archived observations under that error; no corrected rerun or causal comparison
of truthful versus false test information was performed. It was not a preplanned stress test.
