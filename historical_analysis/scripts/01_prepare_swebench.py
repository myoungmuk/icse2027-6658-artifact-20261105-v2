#!/usr/bin/env python3
"""Phase 1: SWE-bench metadata + harness sanity.

What it does
------------
1. Loads SWE-bench Lite and Verified metadata from HuggingFace (per config yaml).
2. Normalizes to data/swebench_instances/{lite,verified}.jsonl (allowlisted fields).
3. Deterministically samples N instances per split (sorted by instance_id).
4. Builds no-op and gold prediction sets for the sample.
5. (only with --run-harness) Runs the SWE-bench Docker harness on the sample:
   no-op patches should usually FAIL, gold patches should usually PASS.
6. Writes results/sanity/harness_sanity_results.jsonl and harness_sanity_report.md.

Without --run-harness it still completes 1-4 and records sanity rows as 'not_run',
explaining what is blocked. The Docker harness pulls multi-GB images per instance, so
it is opt-in.

Usage
-----
    python scripts/01_prepare_swebench.py
    python scripts/01_prepare_swebench.py --run-harness
    python scripts/01_prepare_swebench.py --splits lite --sample-n 3 --run-harness
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "configs" / "datasets"
INSTANCE_DIR = PROJECT_ROOT / "data" / "swebench_instances"
SANITY_DIR = PROJECT_ROOT / "results" / "sanity"
HARNESS_DIR = SANITY_DIR / "_harness"

SANITY_RESULT_KEYS = [
    "instance_id", "dataset_split", "repository", "base_commit", "patch_type",
    "patch_apply", "swebench_result", "fail_to_pass", "pass_to_pass",
    "error_type", "log_path",
]


def log(msg: str) -> None:
    print(f"[01] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# Metadata loading
# --------------------------------------------------------------------------- #
def load_config(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text())


def load_split_metadata(cfg: dict) -> tuple[list[dict], str | None]:
    """Return (normalized_instances, error). Empty list + error on failure."""
    try:
        from datasets import load_dataset
    except Exception as e:  # noqa: BLE001
        return [], f"datasets import failed: {e!r}"

    try:
        ds = load_dataset(cfg["hf_dataset"], split=cfg["hf_split"])
    except Exception as e:  # noqa: BLE001
        return [], f"load_dataset failed: {e!r}"

    keep = cfg["keep_fields"]
    cols = set(ds.column_names)
    rows = []
    for ex in ds:
        row = {k: ex.get(k) for k in keep if k in cols}
        # FAIL_TO_PASS / PASS_TO_PASS are stored as JSON-encoded strings in SWE-bench.
        for tk in ("FAIL_TO_PASS", "PASS_TO_PASS"):
            v = row.get(tk)
            if isinstance(v, str):
                try:
                    row[tk] = json.loads(v)
                except Exception:  # noqa: BLE001
                    pass
        rows.append(row)
    return rows, None


def normalize_and_save(cfg: dict) -> dict:
    label = cfg["split_label"]
    rows, err = load_split_metadata(cfg)
    out_path = INSTANCE_DIR / f"{label}.jsonl"
    if err:
        return {"split": label, "loaded": False, "num_instances": 0,
                "path": str(out_path), "error": err}
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    expected = cfg.get("expected_num_instances")
    return {
        "split": label, "loaded": True, "num_instances": len(rows),
        "expected_num_instances": expected,
        "count_matches_expected": (expected is None or len(rows) == expected),
        "path": str(out_path), "error": None,
    }


def sample_instances(cfg: dict, n: int) -> list[dict]:
    """Deterministic: sort by instance_id, take first n."""
    path = INSTANCE_DIR / f"{cfg['split_label']}.jsonl"
    if not path.exists():
        return []
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    rows.sort(key=lambda r: r.get("instance_id", ""))
    return rows[:n]


# --------------------------------------------------------------------------- #
# Harness sanity
# --------------------------------------------------------------------------- #
def docker_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        p = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"],
                           capture_output=True, text=True, timeout=15)
        return p.returncode == 0 and bool(p.stdout.strip())
    except Exception:  # noqa: BLE001
        return False


def swebench_importable() -> bool:
    try:
        __import__("swebench")
        return True
    except Exception:  # noqa: BLE001
        return False


def _blocked_row(inst: dict, split: str, ptype: str, error_type: str) -> dict:
    return {
        "instance_id": inst.get("instance_id"),
        "dataset_split": split,
        "repository": inst.get("repo"),
        "base_commit": inst.get("base_commit"),
        "patch_type": ptype,
        "patch_apply": False,
        "swebench_result": "not_run",
        "fail_to_pass": "not_run",
        "pass_to_pass": "not_run",
        "error_type": error_type,
        "log_path": None,
    }


def _tests_status(report_inst: dict, key: str) -> str:
    ts = (report_inst or {}).get("tests_status", {}).get(key, {})
    success = ts.get("success", [])
    failure = ts.get("failure", [])
    if not success and not failure:
        return "not_run"
    return "passed" if not failure else "failed"


def run_harness(samples: list[dict], split: str, ptype: str, hf_dataset: str,
                hf_split: str, timeout: int) -> list[dict]:
    """Run SWE-bench harness for one (split, patch_type) over the sample."""
    if not samples:
        return []
    model_name = "gold" if ptype == "gold" else "sanity_noop"
    run_id = f"sanity_{split}_{ptype}"
    work = HARNESS_DIR / run_id
    work.mkdir(parents=True, exist_ok=True)
    instance_ids = [s["instance_id"] for s in samples]

    # predictions_path: literal "gold" lets swebench fill gold patches itself.
    if ptype == "gold":
        preds_arg = "gold"
    else:
        preds = [{"instance_id": s["instance_id"], "model_name_or_path": model_name,
                  "model_patch": ""} for s in samples]
        preds_path = work / "predictions.jsonl"
        with preds_path.open("w") as f:
            for p in preds:
                f.write(json.dumps(p) + "\n")
        preds_arg = str(preds_path)

    cmd = [
        sys.executable, "-m", "swebench.harness.run_evaluation",
        "--dataset_name", hf_dataset,
        "--split", hf_split,
        "--predictions_path", preds_arg,
        "--instance_ids", *instance_ids,
        "--max_workers", "1",
        "--run_id", run_id,
        "--namespace", "swebench",   # pull prebuilt registry images (x86_64)
        "--timeout", str(timeout),
    ]
    log(f"harness run: split={split} type={ptype} ids={instance_ids}")
    proc_log = work / "run_evaluation.stdout.log"
    try:
        with proc_log.open("w") as lf:
            subprocess.run(cmd, cwd=work, stdout=lf, stderr=subprocess.STDOUT,
                           timeout=timeout * len(instance_ids) + 1800, check=False)
        proc_error = None
    except subprocess.TimeoutExpired:
        proc_error = "test_timeout"
    except Exception as e:  # noqa: BLE001
        proc_error = f"unknown: {e!r}"

    # Final summary report: {model_name}.{run_id}.json. SWE-bench short-circuits empty
    # patches (no-op) here as empty_patch_ids and writes NO per-instance report.json.
    summary = {}
    summary_path = work / f"{model_name}.{run_id}.json"
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text())
        except Exception:  # noqa: BLE001
            summary = {}
    empty_ids = set(summary.get("empty_patch_ids", []))
    error_ids = set(summary.get("error_ids", []))

    rows = []
    for s in samples:
        iid = s["instance_id"]
        rep_dir = work / "logs" / "run_evaluation" / run_id / model_name / iid
        report_json = rep_dir / "report.json"
        run_log = rep_dir / "run_instance.log"
        log_path = str(run_log) if run_log.exists() else str(proc_log)
        row = {
            "instance_id": iid, "dataset_split": split,
            "repository": s.get("repo"), "base_commit": s.get("base_commit"),
            "patch_type": ptype,
        }
        if report_json.exists():
            try:
                rep = json.loads(report_json.read_text())
                ri = rep.get(iid, rep)  # report keyed by instance_id
                resolved = bool(ri.get("resolved", False))
                applied = bool(ri.get("patch_successfully_applied", ri.get("patch_exists", False)))
                row.update({
                    "patch_apply": applied,
                    "swebench_result": "resolved" if resolved else "unresolved",
                    "fail_to_pass": _tests_status(ri, "FAIL_TO_PASS"),
                    "pass_to_pass": _tests_status(ri, "PASS_TO_PASS"),
                    "error_type": "none",
                    "log_path": log_path,
                })
            except Exception as e:  # noqa: BLE001
                row.update({"patch_apply": False, "swebench_result": "error",
                            "fail_to_pass": "unknown", "pass_to_pass": "unknown",
                            "error_type": "parser_error", "log_path": log_path})
                row["_parse_error"] = repr(e)
        elif iid in empty_ids:
            # Empty (no-op) patch: SWE-bench correctly counts it as unresolved.
            # This is the EXPECTED no-op outcome, not an error.
            row.update({
                "patch_apply": False, "swebench_result": "unresolved",
                "fail_to_pass": "failed", "pass_to_pass": "not_run",
                "error_type": "none",
                "log_path": str(summary_path) if summary_path.exists() else log_path,
            })
        else:
            # No per-instance report and not a known empty patch: classify the failure.
            if iid in error_ids:
                et, res = "environment_error", "error"
            elif proc_error == "test_timeout":
                et, res = "test_timeout", "error"
            elif "docker" in (proc_error or "").lower():
                et, res = "docker_error", "error"
            else:
                et, res = (proc_error or "environment_error"), "error"
                if et not in ("test_timeout", "docker_error", "environment_error"):
                    et = "unknown"
            row.update({
                "patch_apply": False, "swebench_result": res,
                "fail_to_pass": "not_run", "pass_to_pass": "not_run",
                "error_type": et, "log_path": log_path,
            })
        rows.append({k: row.get(k) for k in SANITY_RESULT_KEYS} |
                    {k: v for k, v in row.items() if k.startswith("_")})
    return rows


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def write_report(meta: list[dict], sanity_rows: list[dict], run_harness_flag: bool,
                 caps: dict, sample_map: dict) -> None:
    SANITY_DIR.mkdir(parents=True, exist_ok=True)
    res_path = SANITY_DIR / "harness_sanity_results.jsonl"
    with res_path.open("w") as f:
        for r in sanity_rows:
            f.write(json.dumps(r) + "\n")

    ts = datetime.now(timezone.utc).isoformat()
    md = ["# SWE-bench Harness Sanity Report (Phase 1)", "",
          f"- Generated (UTC): `{ts}`",
          f"- Harness actually run: **{run_harness_flag}**",
          f"- Docker daemon ready: **{caps['docker_ready']}**",
          f"- swebench importable: **{caps['swebench_importable']}**", "",
          "## 1. Metadata loading", "",
          "| Split | Loaded | #Instances | Expected | Match | Path |",
          "|-------|--------|-----------|----------|-------|------|"]
    for m in meta:
        md.append(f"| {m['split']} | {'yes' if m['loaded'] else 'NO'} | "
                  f"{m['num_instances']} | {m.get('expected_num_instances')} | "
                  f"{m.get('count_matches_expected')} | `{m['path']}` |")
    for m in meta:
        if m.get("error"):
            md.append(f"\n> {m['split']} load error: `{m['error']}`")
    md += ["", "## 2. Sample selected (deterministic, sorted by instance_id)", ""]
    for split, ids in sample_map.items():
        md.append(f"- **{split}** ({len(ids)}): " + ", ".join(f"`{i}`" for i in ids))
    md += ["", "## 3. Harness sanity results", ""]
    if not run_harness_flag:
        md += [
            "Harness was **not run** (no `--run-harness`). Rows below are `not_run`.",
            "",
            "Blocked because the SWE-bench Docker harness pulls a multi-GB image per "
            "instance and builds per-instance test environments. To execute:",
            "",
            "```bash",
            "python scripts/01_prepare_swebench.py --run-harness",
            "```",
            "",
            "Expectation when run: **no-op → unresolved (FAIL_TO_PASS fails)**, "
            "**gold → resolved**. Deviations indicate environment/harness issues.",
            "",
        ]
    md += ["| Instance | Split | Type | Apply | Result | F2P | P2P | Error |",
           "|----------|-------|------|-------|--------|-----|-----|-------|"]
    for r in sanity_rows:
        md.append(f"| `{r['instance_id']}` | {r['dataset_split']} | {r['patch_type']} | "
                  f"{r['patch_apply']} | {r['swebench_result']} | {r['fail_to_pass']} | "
                  f"{r['pass_to_pass']} | {r['error_type']} |")
    md.append("")
    if run_harness_flag:
        noop = [r for r in sanity_rows if r["patch_type"] == "noop"]
        gold = [r for r in sanity_rows if r["patch_type"] == "gold"]
        noop_ok = sum(1 for r in noop if r["swebench_result"] == "unresolved")
        gold_ok = sum(1 for r in gold if r["swebench_result"] == "resolved")
        errs = [r for r in sanity_rows if r["swebench_result"] == "error"]
        md += ["## 4. Interpretation", "",
               f"- no-op behaving as expected (unresolved): {noop_ok}/{len(noop)}",
               f"- gold behaving as expected (resolved): {gold_ok}/{len(gold)}",
               f"- errored/blocked instances: {len(errs)}"]
        for r in errs:
            md.append(f"  - `{r['instance_id']}` ({r['patch_type']}): "
                      f"{r['error_type']} — see `{r['log_path']}`")
        md.append("")
    (SANITY_DIR / "harness_sanity_report.md").write_text("\n".join(md) + "\n")
    log(f"wrote {res_path}")
    log(f"wrote {SANITY_DIR/'harness_sanity_report.md'}")


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", nargs="+", default=["lite", "verified"],
                    choices=["lite", "verified"])
    ap.add_argument("--sample-n", type=int, default=5)
    ap.add_argument("--run-harness", action="store_true",
                    help="actually run the Docker SWE-bench harness (pulls big images)")
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    cfg_files = {"lite": "swebench_lite.yaml", "verified": "swebench_verified.yaml"}
    configs = {s: load_config(cfg_files[s]) for s in args.splits}

    # 1-2. load + normalize
    meta = [normalize_and_save(configs[s]) for s in args.splits]
    for m in meta:
        log(f"split={m['split']} loaded={m['loaded']} n={m['num_instances']} "
            f"err={m.get('error')}")

    # 3. sample
    sample_map, samples_by_split = {}, {}
    for s in args.splits:
        smp = sample_instances(configs[s], args.sample_n)
        samples_by_split[s] = smp
        sample_map[s] = [r["instance_id"] for r in smp]

    caps = {"docker_ready": docker_ready(), "swebench_importable": swebench_importable()}

    # 4-5. sanity rows
    sanity_rows: list[dict] = []
    can_run = args.run_harness and caps["docker_ready"] and caps["swebench_importable"]
    if args.run_harness and not can_run:
        log(f"--run-harness requested but blocked: docker_ready={caps['docker_ready']} "
            f"swebench_importable={caps['swebench_importable']}")
    for s in args.splits:
        smp = samples_by_split[s]
        if not smp:
            continue
        for ptype in ("noop", "gold"):
            if can_run:
                sanity_rows += run_harness(smp, s, ptype, configs[s]["hf_dataset"],
                                           configs[s]["hf_split"], args.timeout)
            else:
                et = "none" if not args.run_harness else "docker_error"
                sanity_rows += [_blocked_row(i, s, ptype, et) for i in smp]

    write_report(meta, sanity_rows, can_run, caps, sample_map)
    log("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
