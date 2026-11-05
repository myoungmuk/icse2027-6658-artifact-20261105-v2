"""Index the three main binary-review cohorts; no rationale truth inference."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT.parent / 'ICSE2027_6658_GitHubRelease_20261105_v8/repository/historical_analysis'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--historical', type=Path, default=DEFAULT)
    parser.add_argument('--output', type=Path, default=ROOT / 'census_v1')
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    root = args.historical
    records, missing, orphaned = [], [], []
    groups = []
    for packet_dir in sorted((root / 'data/review_packets').iterdir()):
        keyfile = packet_dir / 'packets_key.json'
        packetfile = packet_dir / 'packets.jsonl'
        review_dir = root / 'data/llm_reviews' / packet_dir.name
        if not keyfile.is_file() or not packetfile.is_file() or not review_dir.is_dir():
            continue
        keys_list = json.loads(keyfile.read_text())
        keys = {x['packet_id']: x for x in keys_list}
        assert len(keys) == len(keys_list)
        packets = {x['packet_id']: x for x in map(json.loads, packetfile.read_text().splitlines())}
        assert set(keys) == set(packets)
        for judge in sorted(x for x in review_dir.iterdir() if x.is_dir()):
            paths = {p.stem: p for p in judge.glob('*.json')}
            for packet in sorted(set(keys) - set(paths)):
                missing.append({'cohort': packet_dir.name, 'reviewer': judge.name, 'packet_id': packet})
            for packet in sorted(set(paths) - set(keys)):
                orphaned.append(str(paths[packet].relative_to(root)))
            rows = []
            for packet in sorted(set(keys) & set(paths)):
                p = paths[packet]
                key, source = keys[packet], packets[packet]
                try:
                    value = json.loads(p.read_text())
                except (ValueError, UnicodeError) as error:
                    value = {'parse_error': type(error).__name__}
                accepted = value.get('mergeable') if isinstance(value, dict) else None
                valid = type(accepted) is bool
                status = 'ACCEPTED' if valid and accepted else ('NONACCEPTED' if valid else 'UNPARSEABLE_OR_MISSING_DECISION')
                kind = ('gold' if key['candidate_source'] == 'gold' else
                        ('resolved_agent' if key['resolved'] else 'failing_agent'))
                issues = value.get('issues', []) if isinstance(value, dict) else []
                issues = issues if isinstance(issues, list) else []
                row = {'cohort': packet_dir.name, 'reviewer': judge.name, 'packet_id': packet,
                       'instance_id': key['instance_id'], 'group': kind, 'status': status,
                       'verdict_path': str(p.relative_to(root)), 'verdict_sha256': sha(p),
                       'base_commit': source['base_commit'], 'repo': source['repo'],
                       'candidate_diff_sha256': hashlib.sha256(source['diff'].encode()).hexdigest(),
                       'summary': value.get('summary', '') if isinstance(value, dict) else '',
                       'issue_count': len(issues), 'issues': issues,
                       'factual_rationale_adjudication': 'NOT_ADJUDICATED',
                       'independent_human_adjudication': False}
                records.append(row)
                rows.append(row)
            for kind in ('gold', 'resolved_agent', 'failing_agent'):
                subset = [x for x in rows if x['group'] == kind]
                if subset:
                    groups.append({'cohort': packet_dir.name, 'reviewer': judge.name, 'group': kind,
                                   'outputs_found': len(subset), 'counts': dict(Counter(x['status'] for x in subset))})
    work = [x for x in records if x['status'] == 'NONACCEPTED']
    fields = ['cohort', 'reviewer', 'packet_id', 'instance_id', 'group', 'verdict_path',
              'verdict_sha256', 'base_commit', 'repo', 'candidate_diff_sha256', 'summary', 'issue_count',
              'factual_rationale_adjudication', 'independent_human_adjudication']
    with (args.output / 'NONACCEPTED_WORKLIST.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: row[k] for k in fields} for row in work)
    dump(args.output / 'ALL_SAVED_OUTPUTS.json', records)
    dump(args.output / 'MISSING_PACKET_REVIEWER_PAIRS.json', missing)
    hosted = [x for x in work if x['reviewer'] == 'reviewer-claude-frontier' and x['cohort'] in ('verified', 'verified_negctrl')]
    summary = {
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'saved_outputs_with_packet_keys': len(records), 'nonaccepted_outputs': len(work),
        'overall_status_counts': dict(Counter(x['status'] for x in records)),
        'cohorts': sorted({x['cohort'] for x in records}),
        'reviewers': sorted({x['reviewer'] for x in records}),
        'missing_packet_reviewer_pairs': len(missing), 'orphaned_outputs': orphaned,
        'groups': groups,
        'hosted_verified_nonaccepted_by_group': dict(Counter(x['group'] for x in hosted)),
        'reviewer_rationale_truth_rate_computed': False,
        'reviewer_outputs_are_not_independent_tasks': True,
        'no_missing_output_imputed_as_reject': True,
        'new_human_ratings': 0, 'new_harness_runs': 0, 'new_model_calls': 0,
        'interpretation': 'Exhaustive saved-output inventory, not truth adjudication. Duplicate tasks, prompts and reviewers remain distinct archived records. Missing pairs are inventory gaps, not necessarily failed calls or planned evaluations. Worklist statuses remain unadjudicated even where a separate focused claim has been checked.'
    }
    dump(args.output / 'SUMMARY.json', summary)
    dump(args.output / 'MANIFEST.json', {'files': [
        {'path': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)}
        for p in sorted(args.output.iterdir()) if p.is_file()]})
    print(json.dumps({k: summary[k] for k in ('saved_outputs_with_packet_keys', 'nonaccepted_outputs',
        'overall_status_counts', 'cohorts', 'missing_packet_reviewer_pairs', 'hosted_verified_nonaccepted_by_group')}, indent=2))


if __name__ == '__main__':
    main()
