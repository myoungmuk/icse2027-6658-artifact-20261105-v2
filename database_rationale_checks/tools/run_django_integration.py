"""Run each real database check in a separate Python process, keeping failures."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import argparse

ROOT = Path(__file__).resolve().parents[1]


def dump(path, obj):
    with path.open('x') as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-name', default='execution_v2')
    parser.add_argument('--integration', type=Path, default=ROOT / 'integration')
    args = parser.parse_args()
    base = args.integration.resolve()
    acquisition = json.loads((base / 'ACQUISITION.json').read_text())
    run = base / args.run_name
    run.mkdir(exist_ok=False)
    env = dict(os.environ, PYTHONPATH=str(base / 'runtime_dependencies'), PYTHONDONTWRITEBYTECODE='1')
    distributions = [dict(name=x.metadata['Name'], version=x.version)
                     for x in importlib.metadata.distributions(path=[str(base / 'runtime_dependencies')])]
    records = []
    for case in acquisition['cases']:
        for variant in case['variants']:
            name = case['instance_id'] + '_' + variant['name']
            command = [sys.executable, str(base / 'probe_django_sqlite.py'),
                       '--case', case['instance_id'], '--source', variant['source_path'],
                       '--output', str(run / (name + '.json'))]
            started = datetime.now(timezone.utc).isoformat()
            result = subprocess.run(command, cwd=base, env=env, text=True, capture_output=True, timeout=120)
            (run / (name + '.stdout.txt')).write_text(result.stdout)
            (run / (name + '.stderr.txt')).write_text(result.stderr)
            records.append({'instance_id': case['instance_id'], 'variant': variant['name'],
                            'command': command, 'returncode': result.returncode, 'started_utc': started,
                            'finished_utc': datetime.now(timezone.utc).isoformat(),
                            'source_file_sha256': variant['changed_file_sha256'],
                            'result_present': (run / (name + '.json')).is_file()})
            print(name, 'returncode', result.returncode, flush=True)
            if result.returncode:
                print(result.stderr[-3000:], flush=True)
    dump(run / 'EXECUTION.json', {
        'python': sys.version, 'dependencies': distributions,
        'protocol_sha256': hashlib.sha256((base / 'PROTOCOL.md').read_bytes()).hexdigest(),
        'probe_script_sha256': hashlib.sha256((base / 'probe_django_sqlite.py').read_bytes()).hexdigest(),
        'records': records, 'all_processes_succeeded': all(x['returncode'] == 0 for x in records),
        'new_harness_runs': 0, 'new_model_calls': 0, 'new_human_ratings': 0,
    })
    if not all(x['returncode'] == 0 for x in records):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
