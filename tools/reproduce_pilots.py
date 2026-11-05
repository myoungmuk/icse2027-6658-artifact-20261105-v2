#!/usr/bin/env python3
"""Reanalyse saved responses without inference or changing archived evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

REPOSITORY = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(script, workspace):
    result = subprocess.run(
        [sys.executable, str(workspace / script)], cwd=workspace,
        capture_output=True, text=True, check=False,
        env={**__import__('os').environ, 'PYTHONDONTWRITEBYTECODE': '1'},
    )
    (workspace / (script + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
    (workspace / (script + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'{script} failed ({result.returncode}); see {workspace}')


def prepare(source, destination, run_name, sensitivity=False):
    destination.mkdir()
    names = ['analyze.py', 'tasks.json', 'config.json']
    if sensitivity:
        names += ['format_sensitivity.py', 'prompts.py']
    for name in names:
        shutil.copy2(source / name, destination / name)
    shutil.copytree(source / run_name, destination / run_name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path,
                        help='New output directory outside this repository; must not exist.')
    args = parser.parse_args()
    output = args.output.resolve()
    if output == REPOSITORY or REPOSITORY in output.parents:
        parser.error('Choose an output directory outside the preserved release repository.')
    output.mkdir(parents=True, exist_ok=False)
    initial = REPOSITORY / 'binary_pilots'
    followup = initial / 'followup_v2'
    first_work = output / 'initial'
    next_work = output / 'followup'
    prepare(initial, first_work, 'run_v1', sensitivity=True)
    prepare(followup, next_work, 'run_v2')
    run('analyze.py', first_work)
    run('format_sensitivity.py', first_work)
    run('analyze.py', next_work)
    checks = []
    for source, work, directory, files in [
        (initial, first_work, 'analysis_v1', ['summary.json', 'verdicts.csv', 'RESULTS_KO.md']),
        (initial, first_work, 'format_sensitivity_v1', ['summary.json', 'verdicts.csv']),
        (followup, next_work, 'analysis_v2', ['summary.json', 'verdicts.csv', 'RESULTS_KO.md']),
    ]:
        for name in files:
            archived = source / directory / name
            regenerated = work / directory / name
            expected, actual = sha256(archived), sha256(regenerated)
            checks.append({'archived_path': archived.relative_to(REPOSITORY).as_posix(),
                           'regenerated_path': regenerated.relative_to(output).as_posix(),
                           'expected_sha256': expected, 'actual_sha256': actual,
                           'matches': expected == actual})
    report = {'new_inference_calls': 0, 'source_files_modified': False,
              'checks': checks, 'all_match': all(c['matches'] for c in checks)}
    (output / 'reproduction_validation.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'all_match': report['all_match'], 'files_compared': len(checks),
                      'new_inference_calls': 0, 'output': str(output)}, indent=2))
    return 0 if report['all_match'] else 1


if __name__ == '__main__':
    sys.exit(main())
