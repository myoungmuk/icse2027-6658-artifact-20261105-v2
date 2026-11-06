"""Post-hoc descriptive checks of saved heldout outputs; no new inference."""
from collections import defaultdict
from pathlib import Path
from random import Random
import hashlib
import json
import statistics

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / 'ICSE2027_6658_Rerun_20261106_v14'


def interval(values):
    ordered = sorted(values)
    return [ordered[int((len(ordered) - 1) * q)] for q in [.025, .975]]


def main():
    pairs = defaultdict(dict)
    provenance = []
    for p in sorted((OLD / 'run_v5/disjoint').glob('*.json')):
        record = json.loads(p.read_text())
        if record['split'] != 'heldout':
            continue
        assert record['status'] == 'ok'
        pairs[(record['instance_id'], record['arm'])][record['kind']] = record['parsed']['verdict'] == 'ACCEPT'
        provenance.append({'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    rows = []
    for task in sorted({i for i, a in pairs}):
        result = {'instance_id': task, 'repository': task.rsplit('-', 1)[0]}
        for arm in ['strict', 'adjusted']:
            p = pairs[task, arm]
            assert set(p) == {'developer', 'official_unresolved'}
            result[arm] = (int(p['developer']) + int(not p['official_unresolved'])) / 2
            result[arm + '_developer_accept'] = int(p['developer'])
            result[arm + '_unresolved_accept'] = int(p['official_unresolved'])
        result['adjusted_minus_strict'] = result['adjusted'] - result['strict']
        rows.append(result)
    assert len(rows) == 100
    groups = defaultdict(list)
    for row in rows:
        groups[row['repository']].append(row)
    rng = Random(665815)
    repositories = sorted(groups)
    boot = defaultdict(list)
    for _ in range(10000):
        draw = [row for repo in rng.choices(repositories, k=len(repositories)) for row in groups[repo]]
        for metric in ['strict', 'adjusted', 'adjusted_minus_strict']:
            boot[metric].append(statistics.mean(row[metric] for row in draw))
    repo_rows = []
    for repo, subset in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        item = {'repository': repo, 'tasks': len(subset), 'sample_share': len(subset) / len(rows)}
        for metric in ['strict', 'adjusted', 'adjusted_minus_strict']:
            item[metric] = statistics.mean(row[metric] for row in subset)
        repo_rows.append(item)
    sensitivity = {}
    for metric in ['strict', 'adjusted', 'adjusted_minus_strict']:
        removed = {repo: statistics.mean(row[metric] for row in rows if row['repository'] != repo) for repo in repositories}
        sensitivity[metric] = {
            'task_weighted_estimate': statistics.mean(row[metric] for row in rows),
            'repository_cluster_bootstrap_95ci': interval(boot[metric]),
            'equal_repository_weighted_mean': statistics.mean(statistics.mean(row[metric] for row in groups[repo]) for repo in repositories),
            'leave_one_repository_out': removed,
            'leave_one_repository_out_range': [min(removed.values()), max(removed.values())],
        }
    analysis = json.loads((OLD / 'evidence/analysis_v14.json').read_text())
    assert sensitivity['adjusted']['task_weighted_estimate'] == analysis['disjoint']['heldout']['arms']['adjusted']['complete_pair_proxy_agreement']['estimate']
    assert abs(sensitivity['adjusted_minus_strict']['task_weighted_estimate'] - .02) < 1e-12
    selected = analysis['disjoint']['heldout']['arms']['adjusted']
    result = {
        'scope': 'Post-hoc repository sensitivity of existing sealed-selection heldout outputs. No new model calls, human ratings, or harness executions.',
        'tasks': len(rows), 'repositories': len(repositories), 'rows': repo_rows,
        'metrics': sensitivity,
        'cluster_bootstrap_method': 'Resample repository labels uniformly with replacement; retain every task within each selected cluster, count repeated draws repeatedly, and divide by the drawn task count.',
        'resamples': 10000, 'seed': 665815,
        'selected_developer_acceptance': selected['class_acceptance']['developer']['acceptance_valid'],
        'selected_unresolved_acceptance': selected['class_acceptance']['official_unresolved']['acceptance_valid'],
        'selected_proxy_specificity': 1 - selected['class_acceptance']['official_unresolved']['acceptance_valid'],
        'always_accept_or_always_reject_balanced_proxy_agreement': .5,
        'frozen_primary_metrics_unchanged': True,
        'not_preregistered': True,
        'limits': [
            'Few and unequal repository clusters; intervals are exploratory and do not establish external validity.',
            'The balanced functional proxy is not maintainer truth; a constant decision baseline is only a numerical reference.',
            'Do not select another arm or task subset from these post-hoc results.',
            'Do not interpret a confidence interval crossing zero as equivalence or proof of no effect.',
        ],
        'checks': {'all100complete_pairs_retained': True, 'all400heldout_records_valid': len(provenance) == 400,
                   'primary_adjusted_proxy_matches_frozen_analysis': True, 'primary_difference_matches': True,
                   'all_repository_task_counts_sum100': sum(x['tasks'] for x in repo_rows) == 100},
    }
    for name, value in [('repository_sensitivity_v15.json', result), ('repository_sensitivity_inputs_sha256.json', provenance)]:
        with (ROOT / 'evidence' / name).open('x') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
