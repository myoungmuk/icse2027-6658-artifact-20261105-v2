"""Offline, portable verification and prespecified task-level analysis; no inference."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def percentile(values, q):
    s = sorted(values)
    at = (len(s) - 1) * q
    lo = math.floor(at)
    hi = math.ceil(at)
    return s[lo] + (s[hi] - s[lo]) * (at - lo)


def bootstrap(values):
    if not values:
        return None
    rng = random.Random(6658)
    n = len(values)
    means = [sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000)]
    return {'estimate': sum(values) / n, 'task_bootstrap_95ci': [percentile(means, .025), percentile(means, .975)],
            'tasks': n, 'resamples': 10000, 'seed': 6658}


def wilson(k, n):
    if not n:
        return None
    z = 1.959963984540054
    den = 1 + z*z/n
    center = (k/n + z*z/(2*n))/den
    half = z*math.sqrt(k/n*(1-k/n)/n + z*z/(4*n*n))/den
    return [center-half, center+half]


def mcnemar(b, c):
    n = b+c
    return min(1., 2*sum(math.comb(n, k) for k in range(min(b, c)+1))/2**n) if n else 1.


def analyze(exp):
    run = exp / 'run_v1'
    freeze = json.loads((exp / 'freeze_manifest.json').read_text())
    assert all(sha(exp/f['path']) == f['sha256'] for f in freeze['files'])
    spec = importlib.util.spec_from_file_location('frozen_prompts', exp / 'prompts.py')
    prompts = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prompts)
    cs = json.loads((exp / 'candidates.json').read_text())
    cfg = json.loads((exp / 'config.json').read_text())
    candidates = {r['code']: r for r in cs}
    expected = {(c['code'], a) for c in cs for a in cfg['arms']}
    paths = sorted((run / 'raw').glob('*.json'))
    rows = [json.loads(p.read_text()) for p in paths]
    assert len(rows) == 560 and {(r['code'], r['arm']) for r in rows} == expected
    assert len({(r['code'], r['arm']) for r in rows}) == len(rows)
    for r in rows:
        c = candidates[r['code']]
        assert r['messages'] == prompts.messages(r['arm'], c)
        assert all(r[k] == c[k] for k in ['instance_id', 'split', 'kind'])
        if r['status'] == 'ok':
            assert prompts.parse(r['raw']) == r['parsed'] and r['finish_reason'] == 'eos'
        if r.get('parsed') is not None:
            assert prompts.parse(r['raw']) == r['parsed']
    env = json.loads((run / 'environment.json').read_text())
    selection = json.loads((run / 'selection_sealed.json').read_text())
    start = json.loads((run / 'heldout_started.json').read_text())
    end = json.loads((run / 'completion.json').read_text())
    assert start['no_heldout_raw_existed'] and not selection['heldout_inference_started']
    assert sha(run/'selection_sealed.json') == start['selection_sha256'] == end['selection_sha256']
    assert sha(exp/'freeze_manifest.json') == env['freeze_sha256']
    assert datetime.fromisoformat(freeze['frozen_at_utc']) < datetime.fromisoformat(env['started_at_utc']) < datetime.fromisoformat(selection['sealed_at_utc']) < datetime.fromisoformat(start['started_at_utc']) < datetime.fromisoformat(end['completed_at_utc'])
    assert len(selection['development_raw_hashes']) == 160
    for f in selection['development_raw_hashes']:
        p = run / f['path']
        assert sha(p) == f['sha256'] and json.loads(p.read_text())['split'] == 'development'
    scores = {}
    for arm in cfg['arms']:
        rr = [r for r in rows if r['split']=='development' and r['arm']==arm]
        n = sum(r['status']=='ok' and r['parsed']['verdict']==('ACCEPT' if r['kind']=='developer' else 'REJECT') for r in rr)
        scores[arm] = n
        assert n == selection['scores'][arm]['proxy_correct'] and len(rr)==80
    chosen = 'adjusted' if scores['adjusted'] > scores['strict'] else 'strict'
    assert chosen == selection['chosen_arm'] == start['chosen_arm']
    audit = json.loads((exp / 'selection_audit.json').read_text())
    dev = set(audit['development_ids'])
    held = set(audit['heldout_ids'])
    assert len(dev)==40 and len(held)==100 and not dev&held and not (dev|held)&set(audit['excluded_tasks'])
    metrics = {}
    keyed = {(r['split'], r['instance_id'], r['kind'], r['arm']): r for r in rows}
    valid = lambda r: r['status']=='ok'
    accept = lambda r: int(r['parsed']['verdict']=='ACCEPT')
    for split, ids in [('development', dev), ('heldout', held)]:
        metrics[split] = {}
        for arm in cfg['arms']:
            rr = [r for r in rows if r['split']==split and r['arm']==arm]
            classes = {}
            for kind in ['developer', 'official_unresolved']:
                rs = [r for r in rr if r['kind']==kind]
                good = [r for r in rs if valid(r)]
                accepted = sum(accept(r) for r in good)
                classes[kind] = dict(planned=len(rs), valid=len(good), accepted=accepted,
                    rejected=len(good)-accepted, invalid=len(rs)-len(good),
                    acceptance_valid=accepted/len(good) if good else None,
                    acceptance_wilson95=wilson(accepted,len(good)))
            pairs = [(keyed[(split,i,'developer',arm)], keyed[(split,i,'official_unresolved',arm)]) for i in sorted(ids)]
            pairs = [(g,a) for g,a in pairs if valid(g) and valid(a)]
            goldonly = sum(accept(g)==1 and accept(a)==0 for g,a in pairs)
            agentonly = sum(accept(g)==0 and accept(a)==1 for g,a in pairs)
            proxy = [(accept(g)+1-accept(a))/2 for g,a in pairs]
            gap = [accept(g)-accept(a) for g,a in pairs]
            correct = sum(valid(r) and r['parsed']['verdict']==('ACCEPT' if r['kind']=='developer' else 'REJECT') for r in rr)
            metrics[split][arm] = dict(classes=classes, statuses=dict(Counter(r['status'] for r in rr)),
                planned_proxy_agreement=correct/len(rr), planned_proxy_correct=correct,
                complete_pairs=len(pairs), paired_developer_accepted=sum(accept(g) for g,a in pairs),
                paired_unresolved_accepted=sum(accept(a) for g,a in pairs),
                developer_only_accepted=goldonly, unresolved_only_accepted=agentonly,
                exact_mcnemar_p=mcnemar(goldonly,agentonly),
                complete_pair_proxy_agreement=bootstrap(proxy),
                complete_pair_acceptance_gap=bootstrap(gap))
        common=[]
        for i in sorted(ids):
            rs=[keyed[(split,i,k,a)] for a in cfg['arms'] for k in ['developer','official_unresolved']]
            if all(valid(r) for r in rs):
                strict=(accept(rs[0])+1-accept(rs[1]))/2
                adjusted=(accept(rs[2])+1-accept(rs[3]))/2
                common.append(adjusted-strict)
        metrics[split]['adjusted_minus_strict_proxy'] = bootstrap(common)
    return dict(version='v10', chosen_arm=chosen, development_scores=selection['scores'],
        validation={'frozen_hashes_match':True,'560_unique_expected_records':True,
            'messages_match_source_blind_frozen_builder':True,'strict_parser_recomputed':True,
            'selection_recomputed_from_development_only':True,'selection_precedes_heldout':True,
            'development_raw_hashes_unchanged':True,'task_overlap_zero':True,
            'no_prior707_task_overlap':True},
        metrics=metrics, status_counts=dict(Counter(r['status'] for r in rows)),
        oom_events=end['oom_events'], max_gpu_memory_allocated_bytes=end['max_gpu_memory_allocated_bytes'],
        started_at_utc=env['started_at_utc'], sealed_at_utc=selection['sealed_at_utc'],
        heldout_started_at_utc=start['started_at_utc'], completed_at_utc=end['completed_at_utc'],
        scope='New finite prompt-configuration selection on historical functional proxies. Not historical calibration recovery, model-independent validation, fresh harness execution, human agreement, or maintainer truth.',
        output_hashes=[{'path':str(p.relative_to(exp)),'sha256':sha(p)} for p in paths])


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--experiment',type=Path,default=Path(__file__).resolve().parents[1]/'experiment')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    result=analyze(args.experiment)
    with args.output.open('x') as f:
        json.dump(result,f,indent=2)
        f.write('\n')
    print(json.dumps({k:result[k] for k in ['chosen_arm','development_scores','validation','metrics','status_counts']},indent=2))


if __name__=='__main__':
    main()
