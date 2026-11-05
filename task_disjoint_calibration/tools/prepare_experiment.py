"""Prospectively prepare a task-disjoint, finite two-configuration experiment."""
import collections
import argparse
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, obj):
    with path.open('x') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sources', type=Path, default=ROOT / 'sources')
    ap.add_argument('--experiment', type=Path, default=ROOT / 'experiment')
    ap.add_argument('--excluded-audit', type=Path, help='Existing public selection audit containing the frozen 707 excluded IDs')
    args = ap.parse_args()
    sys.path.insert(0, str(ROOT / 'data_tools'))
    import pyarrow.parquet as pq
    sources = args.sources
    exp = args.experiment
    exp.mkdir(parents=True, exist_ok=True)
    tasks = {r['instance_id']: r for r in pq.read_table(sources / 'full_test_parquet.parquet').to_pylist()}
    raw_path = sources / 'listing_20240402_sweagent_gpt4_all_preds.jsonl.json'
    predictions = [json.loads(l) for l in raw_path.read_text().splitlines() if l.strip()]
    multiplicities = collections.Counter(r['instance_id'] for r in predictions)
    duplicates = {i: n for i, n in multiplicities.items() if n > 1}
    preds = {r['instance_id']: r for r in predictions if multiplicities[r['instance_id']] == 1}
    results = json.loads((sources / 'sweagent_full_results.json').read_text())
    if args.excluded_audit:
        old_audit = json.loads(args.excluded_audit.read_text())
        excluded = set(old_audit['excluded_tasks'])
        archive_count = old_audit['archived_packet_tasks']
    else:
        prior = json.loads((BASE / 'ICSE2027_6658_ResponseCompletion_20261105_v3/all_gold_matched/candidates.json').read_text())
        excluded = {r['instance_id'] for r in prior}
        archive = set()
        for p in (BASE / 'review_swe/data/review_packets').rglob('packets.jsonl'):
            archive |= {r['instance_id'] for r in map(json.loads, p.read_text().splitlines()) if r.get('instance_id')}
        excluded |= archive
        archive_count = len(archive)
    assert len(excluded) == 707
    pool = (set(results['applied']) & set(results['with_logs'])) - set(results['resolved'])
    for key in ['test_errored', 'test_timeout', 'reset_failed', 'install_fail', 'no_apply']:
        pool -= set(results[key])
    pool -= excluded
    eligible = [i for i in pool if i in tasks and i in preds
                and (preds[i].get('model_patch') or '').strip()
                and tasks[i]['patch'].strip()
                and preds[i]['model_patch'].strip() != tasks[i]['patch'].strip()]
    salt = 'ICSE6658-v10-task-disjoint-20261105:'
    ordered = sorted(eligible, key=lambda i: hashlib.sha256((salt + i).encode()).hexdigest())
    assert len(ordered) >= 140
    selected = ordered[:140]
    candidates = []
    for pos, iid in enumerate(selected):
        t = tasks[iid]
        split = 'development' if pos < 40 else 'heldout'
        for kind, diff in [('developer', t['patch']), ('official_unresolved', preds[iid]['model_patch'])]:
            code = hashlib.sha256(('ICSE6658-v10-packet:' + iid + ':' + kind).encode()).hexdigest()[:20]
            candidates.append(dict(code=code, instance_id=iid, split=split, kind=kind,
                                   repo=t['repo'], base_commit=t['base_commit'],
                                   issue=t['problem_statement'], diff=diff))
    dev = {r['instance_id'] for r in candidates if r['split'] == 'development'}
    held = {r['instance_id'] for r in candidates if r['split'] == 'heldout'}
    issue_hash = lambda i: hashlib.sha256(tasks[i]['problem_statement'].strip().encode()).hexdigest()
    exact_issue_overlap = {issue_hash(i) for i in dev} & {issue_hash(i) for i in held}
    patch_hashes = lambda split: {hashlib.sha256(r['diff'].strip().encode()).hexdigest() for r in candidates if r['split'] == split}
    exact_patch_overlap = patch_hashes('development') & patch_hashes('heldout')
    assert not dev & held and not (dev | held) & excluded
    assert not exact_issue_overlap and not exact_patch_overlap
    dump(exp / 'candidates.json', candidates)
    dump(exp / 'selection_audit.json', {
        'full_test_tasks': len(tasks), 'predictions': len(predictions),
        'duplicated_prediction_ids_excluded': duplicates,
        'predictions_sha256': sha(raw_path), 'prediction_url': 'https://swe-bench-submissions.s3.amazonaws.com/test/20240402_sweagent_gpt4/all_preds.jsonl',
        'official_results_sha256': sha(sources / 'sweagent_full_results.json'),
        'excluded_tasks': sorted(excluded), 'archived_packet_tasks': archive_count,
        'eligible_after_filters': len(ordered), 'ordering_salt': salt,
        'eligible_ordered_ids': ordered, 'development_ids': sorted(dev), 'heldout_ids': sorted(held),
        'task_overlap': 0, 'prior_task_overlap': 0,
        'exact_issue_text_overlap': len(exact_issue_overlap),
        'exact_candidate_diff_overlap': len(exact_patch_overlap),
        'semantic_duplicates_or_pretraining_exposure_ruled_out': False,
        'repository_counts': {s: dict(collections.Counter(tasks[i]['repo'] for i in ids)) for s, ids in [('development', dev), ('heldout', held)]},
        'label_scope': 'Applied + logs + not resolved, excluding listed setup/test exceptions. Published historical functional proxy, not fresh harness or maintainer truth.',
    })
    oldconfig = dict(model_id='Qwen/Qwen2.5-Coder-7B-Instruct', revision='c03e6d358207e414f1eca0bb1891e29f1db0e242',
        model_path='/workspace/models/huggingface/Qwen/Qwen2.5-Coder-7B-Instruct/c03e6d358207e414f1eca0bb1891e29f1db0e242',
        seed=6658, max_batch_size=8, padded_token_budget=16384,
        max_input_tokens=32256, max_new_tokens=512, dtype='bfloat16', do_sample=False)
    dump(exp / 'config.json', {**oldconfig, 'arms': ['strict', 'adjusted'],
         'development_tasks': 40, 'heldout_tasks': 100,
         'selection_score': '(developer ACCEPT + official-unresolved REJECT) / 80 planned development packets; invalid decisions contribute zero correct, never an imputed verdict',
         'tie_break': 'strict', 'no_heldout_retuning': True})
    print(json.dumps({'eligible': len(ordered), 'tasks': len(selected), 'candidates': len(candidates),
                      'development': len(dev), 'heldout': len(held), 'no_overlap_checks_pass': True}, indent=2))


if __name__ == '__main__':
    main()
