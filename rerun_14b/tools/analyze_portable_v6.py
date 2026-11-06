"""Recompute rerun agreement and task-level heldout statistics from raw outputs."""
from collections import Counter
import argparse
import hashlib
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def mcnemar(b, c):
    n = b + c
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2**n) if n else 1.0


def wilson(k, n):
    if not n:
        return None
    z = 1.959963984540054
    p = k / n
    den = 1 + z * z / n
    middle = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [middle - half, middle + half]


def bootstrap(values):
    if not values:
        return None
    rng = random.Random(6658)
    n = len(values)
    samples = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000))
    return {'estimate': sum(values) / n, 'task_bootstrap_95ci': [samples[249], samples[9749]],
            'tasks': n, 'resamples': 10000, 'seed': 6658}


def rate(k, n):
    return {'accepted': k, 'valid': n, 'acceptance_valid': k / n if n else None, 'wilson95': wilson(k, n)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=ROOT / 'evidence/analysis_v14.json')
    args = ap.parse_args()
    inputs = read(ROOT / 'inputs/historical_records.json')
    historical = {r['id']: read(ROOT / 'run_v5/historical' / (r['id'] + '.json')) for r in inputs}
    portable_keys = read(ROOT / 'inputs_extra/packet_keys.json')
    keys = {}
    for scope, item in portable_keys.items():
        assert hashlib.sha256(item['raw'].encode()).hexdigest() == item['sha256']
        keys[scope] = {x['packet_id']: x for x in json.loads(item['raw'])}
    portable_old = read(ROOT / 'inputs_extra/historical_baselines.json')
    old = {}
    for r in inputs:
        item = portable_old[r['id']]
        assert hashlib.sha256(item['raw'].encode()).hexdigest() == r['historical_output_sha256'] == item['sha256']
        old[r['id']] = json.loads(item['raw'])
    def accepted(r):
        return r['status'] == 'ok' and r['normalized']['mergeable']
    groups = []
    for scope, arm in sorted({(r['scope'], r['arm']) for r in inputs}):
        rr = [r for r in historical.values() if r['scope'] == scope and r['arm'] == arm]
        details = []
        for kind in sorted({keys[scope][r['packet_id']]['candidate_source'] for r in rr}):
            group = [r for r in rr if keys[scope][r['packet_id']]['candidate_source'] == kind]
            valid = [r for r in group if r['status'] == 'ok']
            baseline = [r for r in group if isinstance(old[r['id']].get('mergeable'), bool)]
            pairs = [r for r in valid if isinstance(old[r['id']].get('mergeable'), bool)]
            old_only = sum(old[r['id']]['mergeable'] and not accepted(r) for r in pairs)
            new_only = sum(not old[r['id']]['mergeable'] and accepted(r) for r in pairs)
            details.append({'candidate_source': kind, 'planned': len(group),
                'new': rate(sum(accepted(r) for r in valid), len(valid)),
                'old': rate(sum(old[r['id']]['mergeable'] for r in baseline), len(baseline)),
                'statuses': dict(Counter(r['status'] for r in group)),
                'noncanonical_historical_schema': sum(not r.get('strict_schema_valid', False) for r in valid),
                'old_new_paired': {'n': len(pairs), 'same_decision': len(pairs) - old_only - new_only,
                    'agreement': (len(pairs) - old_only - new_only) / len(pairs) if pairs else None,
                    'old_only_accept': old_only, 'new_only_accept': new_only,
                    'exact_mcnemar_p': mcnemar(old_only, new_only)}})
        groups.append({'scope': scope, 'arm': arm, 'classes': details})
    # Agent/gold comparison on the original common tasks, not an unpaired rate test.
    paired = []
    for scope in ['lite', 'verified', 'agents/rag-gpt4', 'agents/sweagent-claude35', 'agents/openhands-codeact']:
        arms = ['strict', 'calibrated'] if scope in {'lite', 'verified'} else ['calibrated']
        for arm in arms:
            rows = [r for r in historical.values() if r['scope'] == scope and r['arm'] == arm and r['status'] == 'ok']
            gold_scope = scope if scope in {'lite', 'verified'} else 'agents/_gold'
            gold_rows = [r for r in historical.values() if r['scope'] == gold_scope and r['arm'] == arm and r['status'] == 'ok' and keys[gold_scope][r['packet_id']]['candidate_source'] == 'gold']
            gold = {keys[gold_scope][r['packet_id']]['instance_id']: r for r in gold_rows}
            agents = [r for r in rows if keys[scope][r['packet_id']]['candidate_source'] == 'agent']
            pairs = [(r, gold[keys[scope][r['packet_id']]['instance_id']]) for r in agents if keys[scope][r['packet_id']]['instance_id'] in gold]
            a, g = sum(accepted(x) for x, y in pairs), sum(accepted(y) for x, y in pairs)
            b = sum(accepted(x) and not accepted(y) for x, y in pairs)
            c = sum(not accepted(x) and accepted(y) for x, y in pairs)
            paired.append({'scope': scope, 'arm': arm, 'complete_pairs': len(pairs), 'agent_accepted': a,
                'gold_accepted': g, 'agent_only_accept': b, 'gold_only_accept': c, 'exact_mcnemar_p': mcnemar(b, c)})
    disjoint = [read(p) for p in sorted((ROOT / 'run_v5/disjoint').glob('*.json'))]
    assert len(disjoint) == 560
    seal = read(ROOT / 'run_v5/selection_sealed.json')
    held_start = read(ROOT / 'run_v5/heldout_started.json')
    assert seal['sealed_at_utc'] < held_start['started_at_utc']
    assert sha(ROOT / 'run_v5/selection_sealed.json') == held_start['selection_sha256']
    assert all(sha(ROOT / 'run_v5' / x['path']) == x['sha256'] for x in seal['development_output_hashes'])
    sections = {}
    for split in ['development', 'heldout']:
        arms = {}
        pair_values = {}
        for arm in ['strict', 'adjusted']:
            rr = [r for r in disjoint if r['split'] == split and r['arm'] == arm]
            valid = [r for r in rr if r['status'] == 'ok']
            by_id = {}
            for r in valid:
                by_id.setdefault(r['instance_id'], {})[r['kind']] = r['parsed']['verdict'] == 'ACCEPT'
            complete = {i: d for i, d in by_id.items() if set(d) == {'developer', 'official_unresolved'}}
            outcomes = {i: (d['developer'] + (not d['official_unresolved'])) / 2 for i, d in complete.items()}
            pair_values[arm] = outcomes
            b = sum(d['developer'] and not d['official_unresolved'] for d in complete.values())
            c = sum(not d['developer'] and d['official_unresolved'] for d in complete.values())
            classes = {}
            for kind in ['developer', 'official_unresolved']:
                group = [r for r in valid if r['kind'] == kind]
                classes[kind] = rate(sum(r['parsed']['verdict'] == 'ACCEPT' for r in group), len(group))
            correct = sum((r['parsed']['verdict'] == 'ACCEPT') == (r['kind'] == 'developer') for r in valid)
            arms[arm] = {'planned': len(rr), 'valid': len(valid), 'statuses': dict(Counter(r['status'] for r in rr)),
                'class_acceptance': classes, 'planned_proxy_correct': correct,
                'planned_proxy_agreement': correct / len(rr), 'complete_pairs': len(complete),
                'paired_developer_accepted': sum(d['developer'] for d in complete.values()),
                'paired_unresolved_accepted': sum(d['official_unresolved'] for d in complete.values()),
                'developer_only_accept': b, 'unresolved_only_accept': c,
                'exact_mcnemar_p': mcnemar(b, c), 'complete_pair_proxy_agreement': bootstrap(list(outcomes.values()))}
        ids = sorted(set(pair_values['strict']) & set(pair_values['adjusted']))
        sections[split] = {'arms': arms, 'adjusted_minus_strict_proxy': bootstrap([pair_values['adjusted'][i] - pair_values['strict'][i] for i in ids])}
    dev = sections['development']['arms']
    chosen = 'adjusted' if dev['adjusted']['planned_proxy_correct'] > dev['strict']['planned_proxy_correct'] else 'strict'
    assert chosen == seal['chosen_arm']
    for arm in ['strict', 'adjusted']:
        assert dev[arm]['planned_proxy_correct'] == seal['scores'][arm]['proxy_correct']
    audit = read(ROOT / 'disjoint/selection_audit.json')
    source_freeze = read(ROOT / 'FREEZE.json')
    completion = read(ROOT / 'run_v5/completion.json')
    total_calls = sum(len(r['attempts']) for r in list(historical.values()) + disjoint)
    checks = {'runtime_recovery_v9_amendment_unchanged': all(sha(ROOT / x['path']) == x['sha256'] for x in read(ROOT / 'RUNTIME_AMENDMENT_V9.json')['files']), 'request_submission_ledger_complete': sum(read(p)['requests'] for p in (ROOT / 'run_v5/request_submissions').glob('*.json')) == sum(read(p)['requests'] for p in (ROOT / 'run_v5/request_completions').glob('*.json')) == completion['attempted_generation_requests_this_run'] == total_calls, 'runtime_recovery_v6_amendment_unchanged': all(sha(ROOT / x['path']) == x['sha256'] for x in read(ROOT / 'RUNTIME_AMENDMENT_V6.json')['files']), 'runtime_recovery_v5_amendment_unchanged': all(sha(ROOT / x['path']) == x['sha256'] for x in read(ROOT / 'RUNTIME_AMENDMENT_V5.json')['files']), 'runtime_recovery_amendment_unchanged': all(sha(ROOT / x['path']) == x['sha256'] for x in read(ROOT / 'RUNTIME_AMENDMENT_V4.json')['files']), 'portable_analysis_amendment_unchanged': all(sha(ROOT / x['path']) == x['sha256'] for x in read(ROOT / 'ANALYSIS_AMENDMENT_V2.json')['files']), 'all_frozen_inputs_and_code_unchanged': all(sha(ROOT / x['path']) == x['sha256'] for x in source_freeze['files']),
        'all_2197_historical_and560_disjoint_records_present': len(historical) == 2197 and len(disjoint) == 560,
        'all_historical_baseline_hashes_match': True,
        'selection_development_only_and_sealed_before_heldout': chosen == seal['chosen_arm'] and held_start['no_heldout_output_existed'],
        'fresh140_tasks_exclude_previous847': len(audit['excluded_tasks']) == 847 and not (set(audit['development_ids']) | set(audit['heldout_ids'])) & set(audit['excluded_tasks']),
        'all_model_calls_recounted': total_calls == completion['actual_inference_calls'],
        'raw_historical_messages_match_original_2197': read(ROOT / 'evidence/input_equivalence.json')['all2197_pass']}
    result = {'scope': 'Known-condition 14B-AWQ fresh inference rerun; independent new task-disjoint validation. Not exact old runtime/snapshot recovery.',
        'historical': {'records': 2197, 'groups': groups, 'agent_gold_pairs': paired,
            'known_false_negative_pass_instruction_retained': True},
        'disjoint': {'development_tasks': 40, 'heldout_tasks': 100, 'chosen_arm': chosen, **sections},
        'actual_inference_calls': total_calls, 'actual_inference_calls_definition': 'Requests returning outputs in the active completed run. Earlier submitted failed-batch requests are reported separately.', 'prior_failed_generation_requests': 48, 'all_submitted_requests_including_prior_failed_batch': total_calls + 48, 'checks': checks,
        'limits': ['Historical weights revision/runtime identity incomplete; numerical rerun differences do not isolate a cause.',
                   'Archived negative-control pass assertion is known false; rerun is not a valid repaired-control experiment.',
                   'Historical proxy labels and current developer patches are not independent maintainer truth.',
                   'No new human ratings, full SWE-bench container harness, or native Cihan/Shi full pipeline.']}
    assert all(checks.values()), checks
    with args.output.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'actual_inference_calls': total_calls, 'chosen_arm': chosen,
         'heldout_selected': sections['heldout']['arms'][chosen], 'checks': checks}, indent=2))


if __name__ == '__main__':
    main()
