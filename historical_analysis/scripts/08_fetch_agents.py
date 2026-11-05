#!/usr/bin/env python3
"""Fetch additional agents' patches from the public SWE-bench submissions S3 bucket.

For each chosen leaderboard entry, download patch.diff for its RESOLVED instances and
build data/raw/agents/<key>/all_preds.jsonl + data/swebench_results/<key>_resolved.json.
Resolved labels come from the official experiments results.json (authoritative).
"""
from __future__ import annotations
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "data/raw/experiments/evaluation"
OUTAG = ROOT / "data/raw/agents"
RES = ROOT / "data/swebench_results"
BUCKET = "https://swe-bench-submissions.s3.amazonaws.com"

# key -> (split, leaderboard_entry, short_label)
AGENTS = {
    "rag-gpt4": ("verified", "20240402_rag_gpt4", "RAG+GPT-4"),
    "sweagent-claude35": ("verified", "20240620_sweagent_claude3.5sonnet", "SWE-agent+Claude-3.5"),
    "openhands-codeact": ("verified", "20241029_OpenHands-CodeAct-2.1-sonnet-20241022", "OpenHands-CodeAct"),
}


def fetch(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return None


def main() -> int:
    for key, (split, entry, label) in AGENTS.items():
        resolved = json.load(open(EXP / split / entry / "results/results.json"))["resolved"]
        outdir = OUTAG / key
        outdir.mkdir(parents=True, exist_ok=True)
        preds = {}

        def one(iid):
            url = f"{BUCKET}/{split}/{entry}/logs/{iid}/patch.diff"
            d = fetch(url)
            return iid, d

        with ThreadPoolExecutor(max_workers=24) as ex:
            futs = [ex.submit(one, i) for i in resolved]
            for f in as_completed(futs):
                iid, d = f.result()
                if d and d.strip():
                    preds[iid] = d
        with (outdir / "all_preds.jsonl").open("w") as f:
            for iid, patch in preds.items():
                f.write(json.dumps({"instance_id": iid, "model_patch": patch,
                                    "model_name_or_path": key}) + "\n")
        rec = {"split": split, "agent": key, "label": label, "leaderboard_entry": entry,
               "resolved_ids": sorted(preds.keys()), "n_resolved": len(preds),
               "n_total": {"lite": 300, "verified": 500}[split],
               "pct_resolved": round(100 * len(resolved) / {"lite": 300, "verified": 500}[split], 2)}
        json.dump(rec, open(RES / f"{key}_resolved.json", "w"), indent=2)
        print(f"{key}: fetched {len(preds)}/{len(resolved)} patches  ({label})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
