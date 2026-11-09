"""Frozen independent-factor prompts; no functional or source labels in messages."""
import json

ARMS = ('E0B0', 'E1B0', 'E0B1', 'E1B1')
TAXONOMY = {
    'F1': 'Functional incompleteness (issue not fully resolved / edge cases missed)',
    'F2': 'Behavioral regression risk (may break existing/untested behavior)',
    'F3': 'Test overfitting (special-cased to a test, not a general fix)',
    'F4': 'Non-minimal change / scope creep (unrelated or excessive edits)',
    'F5': 'Maintainability/readability defect (unclear, complex, poorly structured)',
    'F6': 'Project convention mismatch (style/API/idiom inconsistent with the repo)',
    'F7': 'Insufficient tests (no or inadequate tests for the change)',
    'F8': 'Incorrect or fragile approach (wrong abstraction, hacky, brittle)',
    'F9': 'API/compatibility break (public API or backward-compatibility issue)',
    'F10': 'Performance regression (introduces avoidable inefficiency)',
    'F11': 'Documentation/comment gap (missing docstring/comment updates)',
}
BASE = ('You are a senior maintainer of the target open-source project doing code review '
        'on a pull request. Judge whether this change is mergeable, considering functional '
        'completeness, regression risk, test adequacy, minimality, maintainability, and '
        'project conventions. Automated test outcomes are not supplied. Do not assume '
        'that tests passed or failed. Be rigorous and skeptical, but do not invent '
        'problems unsupported by the provided issue and diff. Respond with a single JSON object only.')
EXPLANATION = (' The benchmark source-change packet may omit separate test files. '
               'Absence of test files in this packet alone is not evidence that the '
               'original change lacks tests.')
BLOCKING = (' Real maintainers routinely merge imperfect changes. Reserve blocking '
            'severity for a concrete incorrect or incomplete fix, regression, compatibility '
            'break, or clearly wrong approach that would make you refuse to merge. '
            'Style nits, optional refactors, and suggestions to add more tests are minor '
            'unless there is a concrete merge-blocking defect supported by the source change.')

def messages(arm, c):
    assert arm in ARMS
    system = BASE + (EXPLANATION if arm[1]=='1' else '') + (BLOCKING if arm[3]=='1' else '')
    taxonomy = '\n'.join(f'{k}: {v}' for k,v in TAXONOMY.items())
    user = f'''## Pull request under review
Repository: {c['repo']}
Base commit: {c['base_commit']}

### Linked issue / problem statement
{c['issue']}

### Proposed patch (unified diff)
```diff
{c['diff']}
```

## Your task
Decide whether you would MERGE this PR as-is. Identify any merge-blocking or quality
problems, tagging each with a failure-mode code from this taxonomy:
{taxonomy}

Severity: "blocking" (must fix before merge), "major" (should fix), "minor" (nit).
A PR is mergeable only if it has NO blocking issues.
Return ONLY this JSON object:
{{"summary":"<=2 sentence assessment","issues":[{{"failure_mode":"F#","severity":"blocking|major|minor","description":"..."}}],"merge_decision":"merge | request_changes | reject","confidence":0.0}}
Confidence must be a number between 0 and 1; it is not used for acceptance.'''
    return [{'role':'system','content':system}, {'role':'user','content':user}]

def parse(raw, finish_reason):
    if finish_reason != 'stop':
        return None, 'output_truncated_or_nonstop'
    try:
        v = json.loads(raw)
    except (ValueError, TypeError):
        return None, 'malformed_json'
    if not isinstance(v, dict) or not isinstance(v.get('summary'), str):
        return None, 'invalid_schema'
    if v.get('merge_decision') not in ('merge','request_changes','reject') or not isinstance(v.get('issues'),list):
        return None, 'invalid_schema'
    if type(v.get('confidence')) not in (int,float) or not 0 <= v['confidence'] <= 1:
        return None, 'invalid_schema'
    for i in v['issues']:
        if not isinstance(i,dict) or i.get('failure_mode') not in TAXONOMY or i.get('severity') not in ('blocking','major','minor') or not isinstance(i.get('description'),str):
            return None, 'invalid_schema'
    return v, 'ok'

def accepted(v):
    return v['merge_decision']=='merge' and not any(i['severity']=='blocking' for i in v['issues'])
