import json,re
_JSON_RE = re.compile(r'\{.*\}', re.S)
TAXONOMY = {'F1': 'Functional incompleteness (issue not fully resolved / edge cases missed)', 'F2': 'Behavioral regression risk (may break existing/untested behavior)', 'F3': 'Test overfitting (special-cased to the failing test, not a general fix)', 'F4': 'Non-minimal change / scope creep (unrelated or excessive edits)', 'F5': 'Maintainability/readability defect (unclear, complex, poorly structured)', 'F6': 'Project convention mismatch (style/API/idiom inconsistent with the repo)', 'F7': 'Insufficient tests (no or inadequate tests for the change)', 'F8': 'Incorrect or fragile approach (wrong abstraction, hacky, brittle)', 'F9': 'API/compatibility break (public API or backward-compatibility issue)', 'F10': 'Performance regression (introduces avoidable inefficiency)', 'F11': 'Documentation/comment gap (missing docstring/comment updates)'}

TAX_TEXT = '\n'.join((f'  {k}: {v}' for k, v in TAXONOMY.items()))

SYSTEM = "You are a senior maintainer of the target open-source project doing code review on a pull request. The PR's automated tests already PASS. Passing tests is necessary but NOT sufficient for merge: you must judge whether this change is actually mergeable the way a careful human maintainer would, considering functional completeness, regression risk, test adequacy, minimality, maintainability, and project conventions. Be rigorous and skeptical, but do not invent problems that are not supported by the diff. Respond with a single JSON object only."

SYSTEM_CAL = "You are a senior maintainer of the target open-source project reviewing a pull request. The repository's reproduction test (which encodes the bug report) and its existing regression test suite have ALREADY been run against this change and PASS; test execution is handled by the project's CI, not by you. The diff you see shows the source-code change only and intentionally OMITS test files, so absence of test files in the diff is EXPECTED and must NOT by itself be treated as a problem. Your job is to judge the SOURCE CHANGE the way a real maintainer does when deciding to merge. Real maintainers merge changes that correctly resolve the issue without introducing clear correctness, regression, or compatibility problems; merged PRs are rarely perfect and routinely contain minor stylistic imperfections. Reserve a 'blocking' severity ONLY for problems that would genuinely make you refuse to merge (incorrect or incomplete fix, concrete regression/compatibility break, clearly wrong approach). Style nits, optional refactors, and 'could add more tests' are 'minor' and are NOT blocking. Do not invent problems unsupported by the diff. Respond with a single JSON object only."

TASK_CAL = "\n\nReminder: tests already pass and test files are intentionally not shown — do NOT raise F7 (insufficient tests) unless the source change itself is untestable or a maintainer would truly block merge on it. Mark an issue 'blocking' only if you would personally refuse to merge over it."

PROMPT = '## Pull request under review\n\nRepository: {repo}\nBase commit: {base_commit}\nFiles changed: {files}  (+{add}/-{rem} lines)\n\n### Linked issue / problem statement\n{issue}\n\n### Proposed patch (unified diff; automated tests already pass)\n```diff\n{diff}\n```\n\n## Your task\nDecide whether you would MERGE this PR as-is. Apply real code-review standards, not just\n"the tests pass". Identify any merge-blocking or quality problems, tagging each with a\nfailure-mode code from this taxonomy:\n{tax}\n\nSeverity: "blocking" (must fix before merge), "major" (should fix), "minor" (nit).\nA PR is mergeable only if it has NO blocking issues.\n\nReturn ONLY this JSON object:\n{{\n  "summary": "<=2 sentence assessment",\n  "issues": [{{"failure_mode": "F#", "severity": "blocking|major|minor", "description": "..."}}],\n  "merge_decision": "merge | request_changes | reject",\n  "confidence": 0.0-1.0\n}}'

def parse_verdict(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        pass
    m = _JSON_RE.search(text or '')
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None

def normalize(v: dict) -> dict:
    dec = str(v.get('merge_decision', '')).strip().lower()
    if dec not in ('merge', 'request_changes', 'reject'):
        dec = 'reject'
    issues = v.get('issues') or []
    clean = []
    for it in issues:
        if not isinstance(it, dict):
            continue
        fm = str(it.get('failure_mode', '')).upper().replace('FAILURE', '').strip()
        if fm not in TAXONOMY:
            fm = 'F8'
        sev = str(it.get('severity', 'minor')).lower()
        if sev not in ('blocking', 'major', 'minor'):
            sev = 'minor'
        clean.append({'failure_mode': fm, 'severity': sev, 'description': str(it.get('description', ''))[:600]})
    has_blocking = any((i['severity'] == 'blocking' for i in clean))
    mergeable = dec == 'merge' and (not has_blocking)
    return {'summary': str(v.get('summary', ''))[:600], 'issues': clean, 'merge_decision': dec, 'mergeable': bool(mergeable), 'confidence': v.get('confidence')}
