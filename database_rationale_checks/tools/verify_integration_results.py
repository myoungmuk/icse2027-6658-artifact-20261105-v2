"""Verify recorded counterfactual outcomes and exact pinned file identities offline."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--integration', type=Path, default=ROOT / 'integration')
    parser.add_argument('--run-name', default='execution_v2')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    base = args.integration.resolve()
    run = base / args.run_name
    execution = json.loads((run / 'EXECUTION.json').read_text())
    acquisition = json.loads((base / 'ACQUISITION.json').read_text())
    recorded_sources = {(case['instance_id'], v['name']): Path(v['source_path'])
                        for case in acquisition['cases'] for v in case['variants']}
    assert execution['all_processes_succeeded']
    checks = []
    observations = {}
    for iid, variants in [('django__django-11179', ['base', 'candidate']),
                          ('django__django-13028', ['base', 'candidate', 'developer'])]:
        for variant in variants:
            record = json.loads((run / f'{iid}_{variant}.json').read_text())
            results = record['results']
            observations[iid + '_' + variant] = results
            assert Path(record['django_import_path']).is_relative_to(recorded_sources[(iid, variant)])
            for scenario, result in results.items():
                if iid.endswith('11179'):
                    if scenario == 'fast_single':
                        valid = result['can_fast_delete'] and result['rows_remaining'] == 0
                        valid &= result['pk_after'] == (result['pk_before'] if variant == 'base' else None)
                    elif scenario == 'regular_cascade':
                        valid = not result['can_fast_delete'] and result['pk_after'] is None
                        valid &= result['parent_rows_remaining'] == result['child_rows_remaining'] == 0
                    else:
                        valid = result['collected_instances'] == 2 and result['pks_after'] == [None, None]
                        valid &= result['rows_remaining'] == 0
                    valid &= result['call']['outcome'] == 'returned'
                else:
                    outcome = result['call']
                    if scenario == 'filterable_false' and variant != 'developer':
                        valid = outcome['outcome'] == 'raised' and outcome['exception'] == 'NotSupportedError'
                    else:
                        valid = outcome['outcome'] == 'returned' and outcome['value'] == [result['expected_matching_pk']]
                checks.append({'instance_id': iid, 'variant': variant, 'scenario': scenario, 'pass': bool(valid)})
            sql = [q['sql'] for q in record['sql_statements']]
            assert any('CREATE TABLE' in q for q in sql)
            assert any('INSERT INTO' in q for q in sql)
            assert any(('DELETE FROM' if iid.endswith('11179') else 'SELECT') in q for q in sql)
    source_checks = []
    for case in acquisition['cases']:
        archive = base / case['instance_id'] / 'upstream_base.tar.gz'
        archive_present = archive.is_file()
        if archive_present:
            assert hashlib.sha256(archive.read_bytes()).hexdigest() == case['archive_sha256']
        for variant in case['variants']:
            # In portable supplements source trees may be reacquired separately.
            file = base / case['instance_id'] / variant['name'] / variant['changed_file']
            if file.is_file():
                assert hashlib.sha256(file.read_bytes()).hexdigest() == variant['changed_file_sha256']
            source_checks.append({'instance_id': case['instance_id'], 'variant': variant['name'],
                                  'full_source_present': file.is_file(), 'archive_present': archive_present,
                                  'recorded_source_sha256': variant['changed_file_sha256']})
    assert len(checks) == 15 and all(x['pass'] for x in checks)
    result = {
        'distinct_tasks': 2, 'separate_variant_processes': 5, 'scenario_checks': 15,
        'all15_expected_scenarios_match': True, 'checks': checks, 'source_checks': source_checks,
        'observations': observations,
        'gold_focused_claim': 'Regular-path stale-PK objection contradicted by real SQLite cascade and two-instance deletion; the archived one-line developer patch fixes fast-single PK cleanup.',
        'failing_focused_claim': 'Unchanged reported NotSupportedError reproduced through the real ORM for the failing candidate; the separate developer patch succeeds.',
        'historical_runtime_reproduced': False, 'independent_human_adjudication': False,
        'full_Django_test_suite': False, 'new_SWE_bench_harness_runs': 0,
        'new_model_calls': 0, 'new_human_ratings': 0,
        'selection': 'Post-hoc purposeful follow-up of two cases from the previously frozen six-case audit; no prevalence or global reviewer accuracy estimate.',
    }
    with args.output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('distinct_tasks', 'separate_variant_processes',
        'scenario_checks', 'all15_expected_scenarios_match', 'gold_focused_claim', 'failing_focused_claim')}, indent=2))


if __name__ == '__main__':
    main()
