#!/usr/bin/env python3
"""Post-hoc descriptive paired controls and deterministic rationale examples; no inference."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_mcnemar(b, c):
    n = b + c
    return min(1., 2 * sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2**n) if n else 1.


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True, help='New directory outside the repository.')
    output = ap.parse_args().output.resolve()
    assert ROOT not in [output, *output.parents], 'Output must be outside the preserved repository.'
    output.mkdir(parents=True, exist_ok=False)
    f = ROOT / 'binary_pilots/followup_v2'
    tasks = json.loads((f / 'tasks.json').read_text())
    cfg = json.loads((f / 'config.json').read_text())
    pairs = {}
    for arm in cfg['arms']:
        pairs[arm] = {}
        for resolved in (False, True):
            records = []
            for t in tasks:
                if t['agent_resolved'] != resolved:
                    continue
                files = {s: f / 'run_v2/raw' / f'{t["task_code"]}_{s}_{arm}.json' for s in ('agent', 'gold')}
                data = {s: json.loads(p.read_text()) for s, p in files.items()}
                assert all(d['status'] == 'ok' and d['parsed'] is not None for d in data.values())
                records.append({'instance_id': t['instance_id'], 'task_code': t['task_code'],
                    'agent_accept': data['agent']['parsed']['verdict'] == 'ACCEPT',
                    'developer_accept': data['gold']['parsed']['verdict'] == 'ACCEPT',
                    'inputs_sha256': {s: digest(p) for s, p in files.items()}})
            cells = {
                'both_accept': sum(x['agent_accept'] and x['developer_accept'] for x in records),
                'agent_only_accept': sum(x['agent_accept'] and not x['developer_accept'] for x in records),
                'developer_only_accept': sum(not x['agent_accept'] and x['developer_accept'] for x in records),
                'both_reject': sum(not x['agent_accept'] and not x['developer_accept'] for x in records)}
            assert len(records) == sum(cells.values()) == 10
            pairs[arm]['resolved' if resolved else 'unresolved'] = {
                'complete_pairs': len(records), 'agent_accepted': sum(x['agent_accept'] for x in records),
                'developer_accepted': sum(x['developer_accept'] for x in records), **cells,
                'two_sided_exact_mcnemar_p': exact_mcnemar(cells['agent_only_accept'], cells['developer_only_accept']),
                'records': records}
        # Reconcile independently with the frozen, previously published aggregate summary.
        summary = json.loads((f / 'analysis_v2/summary.json').read_text())['arms'][arm]
        assert sum(x['developer_accepted'] for x in pairs[arm].values()) == summary['gold_accepted']
        assert pairs[arm]['unresolved']['agent_accepted'] == summary['fp']
        assert pairs[arm]['resolved']['agent_accepted'] == summary['tp']
    historical = ROOT / 'historical_analysis'
    key = historical / 'data/review_packets/verified/packets_key.json'
    candidates = []
    for item in sorted(json.loads(key.read_text()), key=lambda x: x['instance_id']):
        if item['candidate_source'] != 'agent':
            continue
        file = historical / 'data/llm_reviews/verified/reviewer-claude-frontier' / (item['packet_id'] + '.json')
        v = json.loads(file.read_text())
        accepted = v['merge_decision'] == 'merge' and not any(i.get('severity') == 'blocking' for i in v['issues'])
        if not accepted:
            candidates.append({'instance_id': item['instance_id'], 'packet_id': item['packet_id'],
                'verdict_file': file.relative_to(ROOT).as_posix(), 'verdict_sha256': digest(file),
                'summary': v['summary'], 'issues': v['issues']})
    assert len(candidates) == 30
    result = {'analysis_type': 'post_hoc_saved_response_analysis', 'new_inference_calls': 0,
        'new_harness_runs': 0, 'human_rationale_adjudications': 0,
        'followup_same_task_pairs': pairs,
        'hosted_agent_nonaccepted_count': len(candidates),
        'rationale_example_selection': 'First two non-accepted agent patches sorted lexically by instance_id; descriptive, not representative.',
        'rationale_examples': candidates[:2],
        'limits': ['Ten pairs per functional-label stratum, one adapted open-weight model.',
            'Exploratory exact p values, not prespecified confirmatory tests or equivalence evidence.',
            'Shi draft sees developer reference information; the arms are not information-matched.',
            'Inherited functional labels, no new harness execution or maintainer ground truth.',
            'These pilots do not validate the historical instruments or correct their archived inputs.',
            'Quoted model rationales are not adjudicated defects; historical-fix wording suggests possible recognition, not proven training exposure.']}
    (output / 'paired_controls_and_rationale_examples.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'new_inference_calls': 0, 'followup': {a: {g: {k: v for k, v in x.items() if k != 'records'} for g, x in b.items()} for a, b in pairs.items()},
        'selected_cases': [x['instance_id'] for x in candidates[:2]]}, indent=2))


if __name__ == '__main__':
    main()
