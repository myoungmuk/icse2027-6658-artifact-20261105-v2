"""Combine frozen official target results after disclosed backend follow-ups."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import argparse
import hashlib
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent
EXP = ROOT / 'research_followup/postgres16560'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    with path.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',type=Path,required=True)
    result_dir=parser.parse_args().output_dir
    result_dir.mkdir(parents=True,exist_ok=False)
    old = read(BASE / 'official_regression_audit/evidence/regression_analysis.json')
    residual_root = BASE / 'residual_diagnostics'
    residual = read(residual_root / 'evidence/residual_analysis_v13.json')
    postgres = {}
    combined = []
    for archived in old['cases']:
        row = {k: copy.deepcopy(archived[k]) for k in ['instance_id', 'repo', 'base_commit', 'packet_id', 'verdict_sha256']}
        row['variants'] = {}
        for variant in ['base', 'candidate', 'developer']:
            initial = archived['variants'][variant]
            expected_ids = {e['test_id'] for e in initial['test_events'] if not e['outcome'].startswith('subtest_')}
            if archived['instance_id'] == 'django__django-16560':
                path = EXP / 'execution_v1' / (variant + '_tests.json')
                result = read(path)
                assert result['top_exception'] is None and len(result['runner_summaries']) == 1
                summary = result['runner_summaries'][0]
                counts = {'tests': summary['tests_run'], 'skipped': summary['skipped'],
                          'failures': summary['failures'], 'errors': summary['errors']}
                events = result['events']
                assert {e['test_id'] for e in events if not e['outcome'].startswith('subtest_')} == expected_ids
                postgres[variant] = {'counts': counts, 'events': events, 'source': str(path.relative_to(ROOT)), 'sha256': sha(path)}
                provenance = 'v17 private PostgreSQL 15.18, same 13 official target methods'
            elif archived['instance_id'] == 'pydata__xarray-6744':
                selected = [r for r in residual['tests'] if r['instance_id'] == archived['instance_id'] and r['variant'] == variant and r['policy'] == 'official']
                assert len(selected) == 1
                path = residual_root / selected[0]['source']
                suites = list(ET.parse(path).getroot().iter('testsuite'))
                assert len(suites) == 1
                counts = {k: int(suites[0].get(k)) for k in ['tests', 'skipped', 'failures', 'errors']}
                ids = {e.get('classname', '') + '::' + e.get('name', '') for e in suites[0].iter('testcase')}
                assert ids == expected_ids
                provenance = 'v13 NumPy/Dask follow-up, same 32 official parameter slots'
            else:
                counts = {k: initial[k] for k in ['tests', 'skipped', 'failures', 'errors']}
                path = BASE / 'official_regression_audit' / initial['source_result']
                assert sha(path) == initial['source_sha256']
                provenance = 'unchanged v11 final selected execution'
            assert counts['tests'] == initial['tests']
            counts['executed'] = counts['tests'] - counts['skipped']
            counts['successful'] = counts['failures'] == counts['errors'] == 0
            row['variants'][variant] = {**counts, 'source': str(path), 'sha256': sha(path), 'provenance': provenance}
        combined.append(row)
    totals = {variant: {k: sum(row['variants'][variant][k] for row in combined)
                        for k in ['tests', 'executed', 'skipped', 'failures', 'errors']}
              for variant in ['base', 'candidate', 'developer']}
    checks = {
        'same38cases_retained': len(combined) == len({r['instance_id'] for r in combined}) == 38,
        'same_official_target_ids_for_both_replacements': True,
        'all149slots_per_variant_now_execute_without_skips': all(v['tests'] == v['executed'] == 149 and v['skipped'] == 0 for v in totals.values()),
        'all38_developer_controls_pass': all(r['variants']['developer']['successful'] for r in combined),
        'all38_candidate_and_base_controls_fail': all(not r['variants'][v]['successful'] for r in combined for v in ['base', 'candidate']),
        'all13_PG_methods_per_variant_zero_skips': all(v['counts']['tests'] == 13 and v['counts']['skipped'] == 0 for v in postgres.values()),
        'no_server_left_running': read(EXP / 'server_shutdown.json')['no_running_server_left'],
        'original_sources_and_working_copies_unchanged': all(read(EXP / 'EXECUTION.json')[k] for k in ['source_copies_unchanged', 'original_sources_unchanged']),
    }
    assert all(checks.values())
    summary = {
        'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'New PostgreSQL backend execution for one previously skipped case; combined ledger reuses unchanged v11 results for 36 cases and existing v13 Dask results for one case. Not 38 newly rerun tasks.',
        'postgres': postgres, 'case_count': 38, 'selected_variant_processes': 114,
        'totals': totals, 'combined_executed_slots': sum(v['executed'] for v in totals.values()),
        'combined_skipped_slots': sum(v['skipped'] for v in totals.values()),
        'new_test_processes': 3, 'new_test_slots': 39, 'newly_enabled_previously_skipped_slots': 12,
        'prior_environment_initialization_failures': 1, 'failed_init_generated_study_results': 0,
        'replacement_selection_rule': 'Keep all original target IDs. Replace only the two previously skipped cases using the existing Dask follow-up and the new PostgreSQL follow-up, irrespective of outcome.',
        'checks': checks, 'coverage_unchanged': {'completed': 50, 'total': 58, 'percent': 86.21},
        'B03_status': 'P', 'new_model_calls': 0, 'new_human_ratings': 0, 'full_container_harness_runs': 0,
        'limits': ['This strengthens functional rejection evidence for the scoped 38 candidates; it does not establish truth of every rationale or an independent population error rate.',
                   'Current PostgreSQL/Python runtime differs from the historical run. No model inference or human judgment is rerun.',
                   'The 447 slots span retained and follow-up runs; the three newly executed processes contain 39 slots.'],
    }
    write(result_dir / 'postgres_followup_summary_v17.json', summary)
    write(result_dir / 'combined_38case_regression_ledger_v17.json', {'cases': combined, 'totals': totals, 'selection_rule': summary['replacement_selection_rule']})
    print(json.dumps({k: v for k, v in summary.items() if k not in ['postgres', 'limits', 'replacement_selection_rule']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
