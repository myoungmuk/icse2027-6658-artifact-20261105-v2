"""Build a deterministic pilot and freeze inputs before any new judgments."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path("/workspace/users/2022810001/review_swe/data")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")

def jsonl(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]

def main():
    if (ROOT / "freeze_manifest.json").exists():
        raise SystemExit("Already frozen; use a new experiment version.")
    files = [DATA / "swebench_instances/verified.jsonl",
             DATA / "swebench_results/verified_resolved.json"]
    metadata = {x["instance_id"]: x for x in jsonl(files[0])}
    resolved = set(json.loads(files[1].read_text())["resolved_ids"])
    tasks, exclusions, counts = [], [], {}
    for split in ["verified", "verified_negctrl"]:
        d = DATA / "review_packets" / split
        files.extend([d / "packets.jsonl", d / "packets_key.json"])
        keys = {x["packet_id"]: x for x in json.loads((d / "packets_key.json").read_text())}
        eligible = []
        for p in jsonl(d / "packets.jsonl"):
            key = keys[p["packet_id"]]
            if not key["candidate_source"].startswith("agent"):
                continue
            iid = key["instance_id"]
            g = metadata[iid]
            assert p["issue_text"] == g["problem_statement"], iid
            assert p["base_commit"] == g["base_commit"], iid
            assert bool(key["resolved"]) == (iid in resolved), iid
            sizes = [len(p["issue_text"]), len(p["diff"]), len(g["patch"])]
            if not p["diff"].strip() or not g["patch"].strip() or any(
                    a > b for a, b in zip(sizes, [6000, 16000, 16000])) or sum(sizes) > 30000:
                exclusions.append({"instance_id": iid, "split": split, "sizes": sizes,
                                   "reason": "empty_or_length_limit"})
                continue
            eligible.append((sha(("ICSE6658-two-baselines-v1:" + iid).encode()), p, key, g))
        eligible.sort(key=lambda x: x[0])
        counts[split] = len(eligible)
        for rank, (h, p, key, g) in enumerate(eligible[10:20], 11):
            tasks.append({"instance_id": key["instance_id"], "repo": p["repo"],
                          "base_commit": p["base_commit"], "issue": p["issue_text"],
                          "agent_diff": p["diff"], "gold_diff": g["patch"],
                          "agent_resolved": bool(key["resolved"]),
                          "original_packet_id": p["packet_id"], "selection_hash": h,
                          "stratum_rank": rank, "source_split": split})
    assert len(tasks) == 20 and sum(t["agent_resolved"] for t in tasks) == 10
    assert len({t["instance_id"] for t in tasks}) == 20
    tasks.sort(key=lambda t: t["selection_hash"])
    for i, t in enumerate(tasks, 1):
        t["task_code"] = f"t{i:03}"
    dump(ROOT / "tasks.json", tasks)
    dump(ROOT / "selection_audit.json", {"eligible_counts": counts, "exclusions": exclusions,
          "selected": [{k: t[k] for k in ["instance_id", "repo", "source_split", "selection_hash"]}
                       for t in tasks]})
    config = {"model_id": "Qwen/Qwen2.5-Coder-7B-Instruct",
              "revision": "c03e6d358207e414f1eca0bb1891e29f1db0e242",
              "model_path": "/workspace/models/huggingface/Qwen/Qwen2.5-Coder-7B-Instruct/c03e6d358207e414f1eca0bb1891e29f1db0e242",
              "seed": 6658, "batch_size": 4, "max_input_tokens": 12288,
              "judge_max_new_tokens": 512, "rubric_max_new_tokens": 1024,
              "do_sample": False, "dtype": "bfloat16",
              "arms": ["icse_test_blind", "cihan_binary_diff", "shi_draft_rubric"]}
    dump(ROOT / "config.json", config)
    model_path = Path(config["model_path"])
    files += [model_path / f for f in ["config.json", "generation_config.json", "tokenizer_config.json", "model.safetensors.index.json"]]
    files += [ROOT / p for p in ["protocol_v1.md", "prepare.py", "prompts.py", "run.py", "analyze.py", "validate.py", "config.json", "tasks.json", "selection_audit.json", "followup_provenance.json", "run_gpu.sh"]]
    files += list((ROOT / "sources").glob("*fulltext.txt"))
    files += [ROOT / "sources/cihan_replication_package.zip"]
    for p in files:
        assert p.is_file(), str(p)
    dump(ROOT / "freeze_manifest.json", {"frozen_at_utc": datetime.now(timezone.utc).isoformat(),
         "note": "Before new verdicts. Model weight shards use pinned local revision; only model config files are hashed here.",
         "files": [{"path": str(p), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in files]})
    print("Frozen 20 tasks / 40 patches / 3 arms; all original inputs recorded.")

if __name__ == "__main__":
    main()
