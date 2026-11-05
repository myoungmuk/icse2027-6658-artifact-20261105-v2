#!/usr/bin/env python3
"""Phase 3: LLM code-review of blind packets -> structured mergeability verdict.

Each packet is judged by a served LLM acting as a maintainer doing code review.
The model returns strict JSON: a merge decision, mergeability boolean, and a list of
issues each tagged with a failure-mode (F1..F11) and severity. mergeable := decision
== "merge". Resumable: one output file per (reviewer, packet); existing files skipped.

Usage
-----
    python scripts/03_run_reviewer.py --split lite --reviewer reviewer-14b \
        --base-url http://work03:8000/v1 --workers 24
"""
from __future__ import annotations

import argparse
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = ROOT / "data" / "review_packets"
OUT_DIR = ROOT / "data" / "llm_reviews"

TAXONOMY = {
    "F1": "Functional incompleteness (issue not fully resolved / edge cases missed)",
    "F2": "Behavioral regression risk (may break existing/untested behavior)",
    "F3": "Test overfitting (special-cased to the failing test, not a general fix)",
    "F4": "Non-minimal change / scope creep (unrelated or excessive edits)",
    "F5": "Maintainability/readability defect (unclear, complex, poorly structured)",
    "F6": "Project convention mismatch (style/API/idiom inconsistent with the repo)",
    "F7": "Insufficient tests (no or inadequate tests for the change)",
    "F8": "Incorrect or fragile approach (wrong abstraction, hacky, brittle)",
    "F9": "API/compatibility break (public API or backward-compatibility issue)",
    "F10": "Performance regression (introduces avoidable inefficiency)",
    "F11": "Documentation/comment gap (missing docstring/comment updates)",
}
TAX_TEXT = "\n".join(f"  {k}: {v}" for k, v in TAXONOMY.items())

SYSTEM = (
    "You are a senior maintainer of the target open-source project doing code review on a "
    "pull request. The PR's automated tests already PASS. Passing tests is necessary but "
    "NOT sufficient for merge: you must judge whether this change is actually mergeable "
    "the way a careful human maintainer would, considering functional completeness, "
    "regression risk, test adequacy, minimality, maintainability, and project conventions. "
    "Be rigorous and skeptical, but do not invent problems that are not supported by the "
    "diff. Respond with a single JSON object only."
)

# Calibrated reviewer: instrument validated against developer-merged gold patches.
# Removes packet artifacts (diff omits test files by construction) and anchors the merge
# bar to how real maintainers actually merge.
SYSTEM_CAL = (
    "You are a senior maintainer of the target open-source project reviewing a pull "
    "request. The repository's reproduction test (which encodes the bug report) and its "
    "existing regression test suite have ALREADY been run against this change and PASS; "
    "test execution is handled by the project's CI, not by you. The diff you see shows the "
    "source-code change only and intentionally OMITS test files, so absence of test files "
    "in the diff is EXPECTED and must NOT by itself be treated as a problem. "
    "Your job is to judge the SOURCE CHANGE the way a real maintainer does when deciding to "
    "merge. Real maintainers merge changes that correctly resolve the issue without "
    "introducing clear correctness, regression, or compatibility problems; merged PRs are "
    "rarely perfect and routinely contain minor stylistic imperfections. Reserve a "
    "'blocking' severity ONLY for problems that would genuinely make you refuse to merge "
    "(incorrect or incomplete fix, concrete regression/compatibility break, clearly wrong "
    "approach). Style nits, optional refactors, and 'could add more tests' are 'minor' and "
    "are NOT blocking. Do not invent problems unsupported by the diff. Respond with a "
    "single JSON object only."
)

TASK_CAL = (
    "\n\nReminder: tests already pass and test files are intentionally not shown — do NOT "
    "raise F7 (insufficient tests) unless the source change itself is untestable or a "
    "maintainer would truly block merge on it. Mark an issue 'blocking' only if you would "
    "personally refuse to merge over it."
)

PROMPT = """## Pull request under review

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
}}"""

_JSON_RE = re.compile(r"\{.*\}", re.S)


def parse_verdict(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        pass
    m = _JSON_RE.search(text or "")
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def normalize(v: dict) -> dict:
    dec = str(v.get("merge_decision", "")).strip().lower()
    if dec not in ("merge", "request_changes", "reject"):
        dec = "reject"
    issues = v.get("issues") or []
    clean = []
    for it in issues:
        if not isinstance(it, dict):
            continue
        fm = str(it.get("failure_mode", "")).upper().replace("FAILURE", "").strip()
        if fm not in TAXONOMY:
            fm = "F8"
        sev = str(it.get("severity", "minor")).lower()
        if sev not in ("blocking", "major", "minor"):
            sev = "minor"
        clean.append({"failure_mode": fm, "severity": sev,
                      "description": str(it.get("description", ""))[:600]})
    has_blocking = any(i["severity"] == "blocking" for i in clean)
    mergeable = (dec == "merge") and not has_blocking
    return {
        "summary": str(v.get("summary", ""))[:600],
        "issues": clean,
        "merge_decision": dec,
        "mergeable": bool(mergeable),
        "confidence": v.get("confidence"),
    }


def review_one(client: OpenAI, model: str, pkt: dict, max_diff_chars: int,
               mode: str = "strict") -> dict:
    diff = pkt["diff"]
    if len(diff) > max_diff_chars:
        diff = diff[:max_diff_chars] + "\n... [diff truncated] ..."
    issue = pkt["issue_text"]
    if len(issue) > 6000:
        issue = issue[:6000] + "\n... [truncated] ..."
    system = SYSTEM_CAL if mode == "calibrated" else SYSTEM
    prompt = PROMPT.format(
        repo=pkt["repo"], base_commit=pkt["base_commit"],
        files=", ".join(pkt["changed_files"][:20]) or "(none)",
        add=pkt["diff_stats"]["added_lines"], rem=pkt["diff_stats"]["removed_lines"],
        issue=issue, diff=diff, tax=TAX_TEXT)
    if mode == "calibrated":
        prompt += TASK_CAL
    last_err = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": prompt}],
                temperature=0.0 if attempt == 0 else 0.3,
                max_tokens=1200,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content
            v = parse_verdict(raw)
            if v is not None:
                out = normalize(v)
                out["packet_id"] = pkt["packet_id"]
                out["_attempt"] = attempt
                return out
            last_err = "parse_fail"
        except Exception as e:  # noqa: BLE001
            last_err = repr(e)[:200]
    return {"packet_id": pkt["packet_id"], "error": last_err, "mergeable": None,
            "merge_decision": "error", "issues": [], "summary": ""}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True,
                    help="lite | verified | a path like agents/<key> under data/review_packets")
    ap.add_argument("--reviewer", required=True, help="served-model-name sent to the API")
    ap.add_argument("--label", default=None, help="output dir label (default: --reviewer)")
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--max-diff-chars", type=int, default=24000)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--mode", choices=["strict", "calibrated"], default="strict")
    args = ap.parse_args()

    client = OpenAI(base_url=args.base_url, api_key="EMPTY", timeout=180, max_retries=1)
    packets = [json.loads(l) for l in (PACKET_DIR / args.split / "packets.jsonl")
               .read_text().splitlines() if l.strip()]
    if args.limit:
        packets = packets[:args.limit]
    label = args.label or args.reviewer
    out_dir = OUT_DIR / args.split / label
    out_dir.mkdir(parents=True, exist_ok=True)
    todo = [p for p in packets if not (out_dir / f"{p['packet_id']}.json").exists()]
    print(f"[{args.split}/{label}] total={len(packets)} todo={len(todo)} mode={args.mode}", flush=True)

    lock = threading.Lock()
    done = [0]

    def work(p):
        v = review_one(client, args.reviewer, p, args.max_diff_chars, args.mode)
        (out_dir / f"{p['packet_id']}.json").write_text(json.dumps(v))
        with lock:
            done[0] += 1
            if done[0] % 20 == 0:
                print(f"  {done[0]}/{len(todo)}", flush=True)
        return v

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work, p) for p in todo]
        for _ in as_completed(futs):
            pass
    errs = sum(1 for p in packets
               if json.loads((out_dir / f"{p['packet_id']}.json").read_text()).get("error"))
    print(f"done. errors={errs}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
