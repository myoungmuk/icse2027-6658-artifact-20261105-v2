"""Freeze known-condition 14B reruns separately from a fresh task-disjoint study."""
import ast
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent
OLD = BASE / 'ICSE2027_6658_IndependentCalibration_20261105_v10'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, value):
    with p.open('x') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


def main():
    source = BASE / 'review_swe/scripts/03_run_reviewer.py'
    snapshot = ROOT / 'inputs/original_03_run_reviewer.py'
    shutil.copyfile(source, snapshot)
    tree = ast.parse(source.read_text())
    wanted = {'TAXONOMY', 'TAX_TEXT', 'SYSTEM', 'SYSTEM_CAL', 'TASK_CAL', 'PROMPT', '_JSON_RE'}
    nodes = [n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in wanted for t in n.targets)]
    nodes += [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'parse_verdict', 'normalize'}]
    module = 'import json,re\n' + '\n\n'.join(ast.unparse(n) for n in nodes) + '\n'
    (ROOT / 'inputs/historical_rubric.py').write_text(module)
    ns = {}
    exec(compile(module, str(snapshot), 'exec'), ns)
    rows, source_manifest = [], []
    scopes = [('lite', ['strict', 'calibrated']), ('verified', ['strict', 'calibrated']),
              ('verified_negctrl', ['calibrated']), ('agents/_gold', ['calibrated']),
              ('agents/rag-gpt4', ['calibrated']), ('agents/sweagent-claude35', ['calibrated']),
              ('agents/openhands-codeact', ['calibrated'])]
    for scope, arms in scopes:
        path = BASE / 'review_swe/data/review_packets' / scope / 'packets.jsonl'
        key = path.parent / 'packets_key.json'
        packets = [json.loads(s) for s in path.read_text().splitlines() if s.strip()]
        source_manifest.extend({'path': str(p), 'sha256': sha(p)} for p in [path, key])
        for arm in arms:
            for packet in packets:
                diff, issue = packet['diff'], packet['issue_text']
                if len(diff) > 24000:
                    diff = diff[:24000] + '\n... [diff truncated] ...'
                if len(issue) > 6000:
                    issue = issue[:6000] + '\n... [truncated] ...'
                prompt = ns['PROMPT'].format(repo=packet['repo'], base_commit=packet['base_commit'],
                    files=', '.join(packet['changed_files'][:20]) or '(none)',
                    add=packet['diff_stats']['added_lines'], rem=packet['diff_stats']['removed_lines'],
                    issue=issue, diff=diff, tax=ns['TAX_TEXT'])
                if arm == 'calibrated':
                    prompt += ns['TASK_CAL']
                label = 'reviewer-14b-cal' if arm == 'calibrated' else 'reviewer-14b'
                previous = BASE / 'review_swe/data/llm_reviews' / scope / label / (packet['packet_id'] + '.json')
                identifier = hashlib.sha256((scope + ':' + arm + ':' + packet['packet_id']).encode()).hexdigest()[:24]
                rows.append({'id': identifier, 'scope': scope, 'arm': arm, 'packet_id': packet['packet_id'],
                    'messages': [{'role': 'system', 'content': ns['SYSTEM_CAL'] if arm == 'calibrated' else ns['SYSTEM']},
                                 {'role': 'user', 'content': prompt}],
                    'historical_output_path': str(previous), 'historical_output_sha256': sha(previous),
                    'historical_negative_pass_assertion_known_false': scope == 'verified_negctrl'})
    assert len(rows) == len({r['id'] for r in rows}) == 2197
    dump(ROOT / 'inputs/historical_records.json', rows)
    dump(ROOT / 'inputs/original_provenance.json', {'original_script_sha256': sha(source),
         'source_manifest': source_manifest, 'historical_outputs': len(rows),
         'limits': ['Historical model revision, vLLM build, hardware and numerical settings were not fully recorded.',
                   'The known false pass assertion on archived negative controls is deliberately retained for rerun comparability, not presented as a valid control.',
                   'Repeated packets across scopes are not independent cases.']})
    # New tasks exclude both earlier 707-task union and all 140 v10 tasks.
    prior = json.loads((OLD / 'experiment/selection_audit.json').read_text())
    excluded = sorted(set(prior['excluded_tasks']) | set(prior['development_ids']) | set(prior['heldout_ids']))
    assert len(excluded) == 847
    dump(ROOT / 'inputs/disjoint_exclusions.json', {'excluded_tasks': excluded, 'archived_packet_tasks': prior['archived_packet_tasks']})
    prepare = (OLD / 'tools/prepare_experiment.py').read_text()
    prepare = prepare.replace("str(ROOT / 'data_tools')", repr(str(OLD / 'data_tools')))
    prepare = prepare.replace('len(excluded) == 707', 'len(excluded) == 847').replace('ICSE6658-v10-', 'ICSE6658-v14-')
    prepare = prepare.replace("model_id='Qwen/Qwen2.5-Coder-7B-Instruct'", "model_id='Qwen/Qwen2.5-Coder-14B-Instruct-AWQ'")
    revision = json.loads((ROOT / 'evidence/model_remote_manifest.json').read_text())['revision']
    prepare = prepare.replace('c03e6d358207e414f1eca0bb1891e29f1db0e242', revision)
    prepare = prepare.replace('/Qwen2.5-Coder-7B-Instruct/', '/Qwen2.5-Coder-14B-Instruct-AWQ/')
    script = ROOT / 'tools/prepare_disjoint.py'
    script.write_text(prepare)
    subprocess.run(['python', str(script), '--sources', str(OLD / 'sources'), '--experiment', str(ROOT / 'disjoint'),
                    '--excluded-audit', str(ROOT / 'inputs/disjoint_exclusions.json')], check=True)
    effective = json.loads((ROOT / 'disjoint/config.json').read_text())
    effective.update(dtype='float16', backend='vllm', effective_runtime_configuration='../inputs/config.json')
    effective.pop('max_batch_size')
    effective.pop('padded_token_budget')
    (ROOT / 'disjoint/config.json').write_text(json.dumps(effective, indent=2) + '\n')
    shutil.copyfile(OLD / 'experiment/prompts.py', ROOT / 'inputs/disjoint_prompts.py')
    config = {'model_id': 'Qwen/Qwen2.5-Coder-14B-Instruct-AWQ', 'revision': revision,
        'model_path': '/workspace/models/huggingface/Qwen/Qwen2.5-Coder-14B-Instruct-AWQ/' + revision,
        'vllm_version': '0.10.2', 'seed': 6658, 'dtype': 'float16', 'quantization': 'awq_marlin',
        'max_model_len': 32768, 'gpu_memory_utilization': 0.88,
        'historical_max_tokens': 1200, 'historical_attempts': 3, 'historical_temperatures': [0.0, 0.3, 0.3],
        'historical_json_object_constraint': True, 'disjoint_max_tokens': 512,
        'disjoint_temperatures': [0.0], 'disjoint_json_object_constraint': False,
        'selection_rule': '(developer ACCEPT + unresolved REJECT) / 80 planned development records; invalid=0 correct, ties strict',
        'exact_historical_runtime_reproduction_claimed': False}
    dump(ROOT / 'inputs/config.json', config)
    print(json.dumps({'historical_records': len(rows), 'new_disjoint_tasks': 140, 'new_disjoint_planned_inputs': 560,
                      'model_revision': revision, 'prepared_at_utc': datetime.now(timezone.utc).isoformat()}, indent=2))


if __name__ == '__main__':
    main()
