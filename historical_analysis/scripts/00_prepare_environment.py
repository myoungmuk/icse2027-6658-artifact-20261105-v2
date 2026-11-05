#!/usr/bin/env python3
"""Phase 0: environment + tooling sanity.

Checks Python / Docker / git, verifies the repo directory skeleton (creating any
missing directories), and writes both a human report and a machine-readable summary:

    results/sanity/environment_check.md
    results/sanity/environment_check.json

Stdlib only. Does NOT run SWE-bench. Safe to run repeatedly (idempotent).
"""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Directory skeleton the project expects to exist.
EXPECTED_DIRS = [
    "configs/datasets", "configs/agents", "configs/reviewers", "configs/contexts",
    "data/raw", "data/swebench_instances",
    "data/patches/raw_agent_outputs", "data/patches/normalized",
    "data/trajectories", "data/swebench_results",
    "data/review_packets/json", "data/review_packets/md",
    "data/annotations/human_raw", "data/annotations/adjudicated",
    "data/llm_reviews", "data/issue_matches",
    "scripts", "docs",
    "results/sanity", "results/agent_runs", "results/swebench_eval",
    "results/annotations", "results/llm_reviews",
    "results/rq1_mergeability_gap", "results/rq2_failure_taxonomy",
    "results/rq3_llm_reviewer", "results/rq4_review_loop",
    "results/rq5_context_ablation",
    "results/tables", "results/figures", "results/reports",
]


def _run(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", "not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:  # noqa: BLE001
        return 1, "", repr(e)


def check_python() -> dict:
    return {
        "available": True,
        "version": platform.python_version(),
        "executable": sys.executable,
        "implementation": platform.python_implementation(),
    }


def check_git() -> dict:
    path = shutil.which("git")
    info = {"available": path is not None, "path": path, "version": None}
    if path:
        rc, out, _ = _run([path, "--version"])
        if rc == 0:
            info["version"] = out
    return info


def check_docker() -> dict:
    path = shutil.which("docker")
    info = {
        "client_available": path is not None,
        "path": path,
        "client_version": None,
        "server_running": False,
        "server_version": None,
        "note": None,
    }
    if not path:
        info["note"] = "docker client not on PATH; SWE-bench harness will be blocked"
        return info
    rc, out, _ = _run([path, "version", "--format", "{{.Client.Version}}"])
    if rc == 0 and out:
        info["client_version"] = out
    rc, out, err = _run([path, "version", "--format", "{{.Server.Version}}"])
    if rc == 0 and out:
        info["server_running"] = True
        info["server_version"] = out
    else:
        info["note"] = f"docker daemon not reachable ({err or 'no server'}); harness blocked"
    return info


def check_dirs() -> dict:
    created, present = [], []
    for rel in EXPECTED_DIRS:
        d = PROJECT_ROOT / rel
        if d.is_dir():
            present.append(rel)
        else:
            d.mkdir(parents=True, exist_ok=True)
            created.append(rel)
    return {"root": str(PROJECT_ROOT), "present": present, "created": created}


def check_disk() -> dict:
    out = {}
    for label, p in {"project_root": PROJECT_ROOT, "tmp": Path("/tmp"),
                     "home": Path.home()}.items():
        try:
            u = shutil.disk_usage(p)
            out[label] = {
                "path": str(p),
                "total_gb": round(u.total / 1e9, 1),
                "used_gb": round(u.used / 1e9, 1),
                "free_gb": round(u.free / 1e9, 1),
            }
        except Exception as e:  # noqa: BLE001
            out[label] = {"path": str(p), "error": repr(e)}
    return out


def check_optional_imports() -> dict:
    mods = {}
    for name in ["datasets", "yaml", "swebench"]:
        try:
            m = __import__(name)
            mods[name] = {"available": True, "version": getattr(m, "__version__", None)}
        except Exception as e:  # noqa: BLE001
            mods[name] = {"available": False, "error": repr(e)}
    return mods


def main() -> int:
    ts = datetime.now(timezone.utc).isoformat()
    summary = {
        "timestamp_utc": ts,
        "project_root": str(PROJECT_ROOT),
        "python": check_python(),
        "git": check_git(),
        "docker": check_docker(),
        "imports": check_optional_imports(),
        "disk": check_disk(),
        "directories": check_dirs(),
    }

    harness_ready = (
        summary["docker"]["server_running"]
        and summary["imports"].get("swebench", {}).get("available", False)
    )
    metadata_ready = summary["imports"].get("datasets", {}).get("available", False)
    summary["capabilities"] = {
        "metadata_loading_ready": metadata_ready,
        "swebench_harness_ready": harness_ready,
    }

    sanity = PROJECT_ROOT / "results" / "sanity"
    sanity.mkdir(parents=True, exist_ok=True)
    (sanity / "environment_check.json").write_text(json.dumps(summary, indent=2))

    d = summary
    md = []
    md.append("# Environment Check (Phase 0)")
    md.append("")
    md.append(f"- Generated (UTC): `{ts}`")
    md.append(f"- Project root: `{d['project_root']}`")
    md.append("")
    md.append("## Core tooling")
    md.append("")
    md.append("| Tool | Available | Version |")
    md.append("|------|-----------|---------|")
    md.append(f"| Python | yes | {d['python']['version']} ({d['python']['implementation']}) |")
    md.append(f"| git | {'yes' if d['git']['available'] else 'NO'} | {d['git']['version']} |")
    dk = d["docker"]
    md.append(f"| Docker client | {'yes' if dk['client_available'] else 'NO'} | {dk['client_version']} |")
    md.append(f"| Docker daemon | {'yes' if dk['server_running'] else 'NO'} | {dk['server_version']} |")
    if dk.get("note"):
        md.append(f"\n> Docker note: {dk['note']}")
    md.append("")
    md.append("## Python imports")
    md.append("")
    md.append("| Module | Available | Version |")
    md.append("|--------|-----------|---------|")
    for name, info in d["imports"].items():
        md.append(f"| {name} | {'yes' if info['available'] else 'NO'} | {info.get('version')} |")
    md.append("")
    md.append("## Capabilities")
    md.append("")
    cap = d["capabilities"]
    md.append(f"- Metadata loading ready (datasets): **{cap['metadata_loading_ready']}**")
    md.append(f"- SWE-bench harness ready (docker daemon + swebench): **{cap['swebench_harness_ready']}**")
    md.append("")
    md.append("## Disk")
    md.append("")
    md.append("| Path | Free (GB) | Total (GB) |")
    md.append("|------|-----------|------------|")
    for label, info in d["disk"].items():
        if "error" in info:
            md.append(f"| {label} ({info['path']}) | error | {info['error']} |")
        else:
            md.append(f"| {label} (`{info['path']}`) | {info['free_gb']} | {info['total_gb']} |")
    md.append("")
    md.append("## Directories")
    md.append("")
    md.append(f"- Present: {len(d['directories']['present'])}")
    md.append(f"- Created this run: {len(d['directories']['created'])}")
    if d["directories"]["created"]:
        for c in d["directories"]["created"]:
            md.append(f"  - `{c}`")
    md.append("")
    (sanity / "environment_check.md").write_text("\n".join(md) + "\n")

    print(f"[00] wrote {sanity/'environment_check.md'}")
    print(f"[00] wrote {sanity/'environment_check.json'}")
    print(f"[00] metadata_ready={metadata_ready} harness_ready={harness_ready}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
