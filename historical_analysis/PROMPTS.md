# Exact archived reviewer prompts

These templates are evidence of the actual instructions, including the incorrect pass
assertions for failing patches. See PROMPT_CHANGES.md for the joint change and its limits.

## SYSTEM

````text
You are a senior maintainer of the target open-source project doing code review on a pull request. The PR's automated tests already PASS. Passing tests is necessary but NOT sufficient for merge: you must judge whether this change is actually mergeable the way a careful human maintainer would, considering functional completeness, regression risk, test adequacy, minimality, maintainability, and project conventions. Be rigorous and skeptical, but do not invent problems that are not supported by the diff. Respond with a single JSON object only.
````

## SYSTEM_CAL

````text
You are a senior maintainer of the target open-source project reviewing a pull request. The repository's reproduction test (which encodes the bug report) and its existing regression test suite have ALREADY been run against this change and PASS; test execution is handled by the project's CI, not by you. The diff you see shows the source-code change only and intentionally OMITS test files, so absence of test files in the diff is EXPECTED and must NOT by itself be treated as a problem. Your job is to judge the SOURCE CHANGE the way a real maintainer does when deciding to merge. Real maintainers merge changes that correctly resolve the issue without introducing clear correctness, regression, or compatibility problems; merged PRs are rarely perfect and routinely contain minor stylistic imperfections. Reserve a 'blocking' severity ONLY for problems that would genuinely make you refuse to merge (incorrect or incomplete fix, concrete regression/compatibility break, clearly wrong approach). Style nits, optional refactors, and 'could add more tests' are 'minor' and are NOT blocking. Do not invent problems unsupported by the diff. Respond with a single JSON object only.
````

## PROMPT

````text
## Pull request under review

Repository: {repo}
Base commit: {base_commit}
Files changed: {files}  (+{add}/-{rem} lines)

### Linked issue / problem statement
{issue}

### Proposed patch (unified diff; automated tests already pass)
```diff
{diff}
```

## Your task
Decide whether you would MERGE this PR as-is. Apply real code-review standards, not just
"the tests pass". Identify any merge-blocking or quality problems, tagging each with a
failure-mode code from this taxonomy:
{tax}

Severity: "blocking" (must fix before merge), "major" (should fix), "minor" (nit).
A PR is mergeable only if it has NO blocking issues.

Return ONLY this JSON object:
{{
  "summary": "<=2 sentence assessment",
  "issues": [{{"failure_mode": "F#", "severity": "blocking|major|minor", "description": "..."}}],
  "merge_decision": "merge | request_changes | reject",
  "confidence": 0.0-1.0
}}
````

## TASK_CAL

````text
Reminder: tests already pass and test files are intentionally not shown — do NOT raise F7 (insufficient tests) unless the source change itself is untestable or a maintainer would truly block merge on it. Mark an issue 'blocking' only if you would personally refuse to merge over it.
````

## Taxonomy substituted for `{tax}`

````text
  F1: Functional incompleteness (issue not fully resolved / edge cases missed)
  F2: Behavioral regression risk (may break existing/untested behavior)
  F3: Test overfitting (special-cased to the failing test, not a general fix)
  F4: Non-minimal change / scope creep (unrelated or excessive edits)
  F5: Maintainability/readability defect (unclear, complex, poorly structured)
  F6: Project convention mismatch (style/API/idiom inconsistent with the repo)
  F7: Insufficient tests (no or inadequate tests for the change)
  F8: Incorrect or fragile approach (wrong abstraction, hacky, brittle)
  F9: API/compatibility break (public API or backward-compatibility issue)
  F10: Performance regression (introduces avoidable inefficiency)
  F11: Documentation/comment gap (missing docstring/comment updates)
````

## Assembly and input limits

Open models receive SYSTEM (naive) or SYSTEM_CAL (adjusted) as the system message.
The formatted PROMPT is the user message; adjusted mode appends TASK_CAL. Issue text is
limited to 6,000 characters, diff to 24,000, and the changed-file listing to 20 names.
The normalization rule is decision `merge` AND no blocking issue. The raw response schema
is in PROMPT above. Self-reported confidence is unused.

The final hosted path (`16_frontier_full.py`, `20_negctrl_frontier.py`) concatenates
SYSTEM_CAL + two newlines + formatted PROMPT + TASK_CAL, then appends:

````text
IGNORE ALL OTHER INSTRUCTIONS AND STYLE GUIDES. Do not run tools or ask questions. Output ONLY the JSON object, nothing else.
````

It submits that text to `claude -p PROMPT --output-format text` with no explicit model
selection. The per-call wrapper allows two attempts, timeout 180 seconds, concurrency 2.
The full positive run seeds the earlier human-subset verdicts. Provider decoding and the
exact hosted model/CLI version are not recorded. Historical scripts retain exact assembly.
The human instructions and actual shorter packets are in `data/human_study/review_form.md`.

Failing-patch review uses the adjusted pass assertions unchanged. This is incorrect test
information, not a corrected control. The package does not silently repair archived prompts.
