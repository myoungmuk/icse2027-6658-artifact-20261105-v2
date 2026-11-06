"""Fresh 14B-AWQ inference: archived instrument rerun, then disjoint selection."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'inputs'))
from historical_rubric import parse_verdict, normalize
from disjoint_prompts import messages, parse


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, obj):
    with p.open('x') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def now():
    return datetime.now(timezone.utc).isoformat()


def verify():
    for x in json.loads((ROOT / 'FREEZE.json').read_text())['files']:
        assert sha(ROOT / x['path']) == x['sha256'], x['path']


def main():
    verify()
    import torch
    import vllm
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import GuidedDecodingParams
    cfg = json.loads((ROOT / 'inputs/config.json').read_text())
    acquisition = json.loads((ROOT / 'evidence/model_acquisition.json').read_text())
    assert acquisition['all_expected_sizes_and_LFS_hashes_verified']
    out = ROOT / 'run_v5'
    out.mkdir()
    (out / 'historical').mkdir()
    (out / 'disjoint').mkdir()
    (out / 'request_submissions').mkdir()
    (out / 'request_completions').mkdir()
    dump(out / 'environment.json', {'started_at_utc': now(), 'python': platform.python_version(),
         'torch': torch.__version__, 'vllm': vllm.__version__, 'cuda': torch.version.cuda,
         'config': cfg, 'freeze_sha256': sha(ROOT / 'FREEZE.json'),
         'nvidia_smi': subprocess.check_output(['nvidia-smi'], text=True),
         'pip_freeze': subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True),
         'historical_runtime_bit_identity_claimed': False})
    llm = LLM(model=cfg['model_path'], tokenizer=cfg['model_path'], dtype='half',
        guided_decoding_backend='xgrammar', quantization=cfg['quantization'], max_model_len=cfg['max_model_len'],
        gpu_memory_utilization=cfg['gpu_memory_utilization'], seed=cfg['seed'],
        max_num_seqs=24, max_num_batched_tokens=4096, enforce_eager=True,
        enable_prefix_caching=False, enable_chunked_prefill=True,
        trust_remote_code=False, disable_log_stats=False)
    tokenizer = llm.get_tokenizer()
    total_calls = 0
    submitted_calls = 0
    started = time.monotonic()
    print('MODEL_READY', now(), flush=True)

    def render(msg):
        return tokenizer.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)

    def generate(records, folder, historical):
        nonlocal total_calls, submitted_calls
        prepared, lengths = [], []
        for row in records:
            row = dict(row)
            text = render(row['messages'])
            tokens = tokenizer(text, add_special_tokens=False)['input_ids']
            lengths.append(len(tokens))
            row['input_tokens'] = len(tokens)
            row['messages_sha256'] = hashlib.sha256(json.dumps(row.pop('messages'), ensure_ascii=False).encode()).hexdigest()
            row['attempts'] = []
            maximum = cfg['historical_max_tokens'] if historical else cfg['disjoint_max_tokens']
            if len(tokens) > cfg['max_model_len'] - maximum:
                row.update(status='input_too_long', normalized=None, parsed=None)
                dump(folder / (row['id'] + '.json'), row)
            else:
                prepared.append((row, text))
        temperatures = cfg['historical_temperatures'] if historical else cfg['disjoint_temperatures']
        for attempt, temperature in enumerate(temperatures):
            retry = []
            for offset in range(0, len(prepared), 48):
                batch = prepared[offset:offset + 48]
                params = SamplingParams(temperature=temperature, seed=cfg['seed'] + attempt,
                    max_tokens=cfg['historical_max_tokens'] if historical else cfg['disjoint_max_tokens'],
                    guided_decoding=GuidedDecodingParams(json_object=True, backend='xgrammar') if historical else None)
                submitted_calls += len(batch)
                submission = {'ids': [row['id'] for row, _ in batch], 'attempt': attempt, 'temperature': temperature, 'submitted_at_utc': now(), 'requests': len(batch)}
                dump(out / 'request_submissions' / (str(submitted_calls) + '.json'), submission)
                answers = llm.generate([text for _, text in batch], params, use_tqdm=False)
                assert len(answers) == len(batch)
                total_calls += len(batch)
                dump(out / 'request_completions' / (str(submitted_calls) + '.json'), {'requests': len(batch), 'returned_at_utc': now()})
                for (row, text), answer in zip(batch, answers):
                    value = answer.outputs[0]
                    raw = value.text
                    event = {'attempt': attempt, 'temperature': temperature, 'seed': cfg['seed'] + attempt,
                             'raw': raw, 'finish_reason': value.finish_reason, 'output_tokens': len(value.token_ids),
                             'returned_model_request_id': answer.request_id, 'completed_at_utc': now()}
                    row['attempts'].append(event)
                    parsed, normalized = None, None
                    if historical:
                        parsed = parse_verdict(raw)
                        if isinstance(parsed, dict):
                            try:
                                normalized = normalize(parsed)
                            except Exception:
                                normalized = None
                        valid = normalized is not None
                        schema_valid = isinstance(parsed, dict) and isinstance(parsed.get('merge_decision'), str) and parsed.get('merge_decision') in {'merge', 'request_changes', 'reject'} and isinstance(parsed.get('issues'), list)
                    else:
                        parsed = parse(raw)
                        valid = parsed is not None and value.finish_reason == 'stop'
                        schema_valid = parsed is not None
                    if not valid and attempt + 1 < len(temperatures):
                        retry.append((row, text))
                        continue
                    row.update(parsed=parsed, normalized=normalized, strict_schema_valid=schema_valid,
                               status='ok' if valid else 'invalid_or_truncated')
                    dump(folder / (row['id'] + '.json'), row)
                print('PROGRESS', folder.name, 'attempt', attempt, min(offset + len(batch), len(prepared)), '/', len(prepared),
                      'all_calls', total_calls, 'elapsed_seconds', round(time.monotonic() - started), flush=True)
            prepared = retry
            if not prepared:
                break
        return {'records': len(records), 'max_input_tokens': max(lengths), 'overlength': sum(n > cfg['max_model_len'] - maximum for n in lengths)}

    historical = json.loads((ROOT / 'inputs/historical_records.json').read_text())
    hist_preflight = generate(historical, out / 'historical', True)
    dump(out / 'historical_finished.json', {'completed_at_utc': now(), **hist_preflight})
    candidates = json.loads((ROOT / 'disjoint/candidates.json').read_text())
    for split in ['development', 'heldout']:
        if split == 'heldout':
            seal = json.loads((out / 'selection_sealed.json').read_text())
            for x in seal['development_output_hashes']:
                assert sha(out / x['path']) == x['sha256']
            assert not any(json.loads(p.read_text())['split'] == 'heldout' for p in (out / 'disjoint').glob('*.json'))
            dump(out / 'heldout_started.json', {'started_at_utc': now(), 'selection_sha256': sha(out / 'selection_sealed.json'), 'no_heldout_output_existed': True})
        records = []
        for c in candidates:
            if c['split'] != split:
                continue
            for arm in ['strict', 'adjusted']:
                records.append({**{k: c[k] for k in ['code', 'instance_id', 'split', 'kind']},
                    'id': c['code'] + '_' + arm, 'arm': arm, 'messages': messages(arm, c)})
        generate(records, out / 'disjoint', False)
        if split == 'development':
            files = sorted((out / 'disjoint').glob('*.json'))
            rr = [json.loads(p.read_text()) for p in files]
            assert len(rr) == 160 and all(x['split'] == 'development' for x in rr)
            scores = {}
            for arm in ['strict', 'adjusted']:
                group = [x for x in rr if x['arm'] == arm]
                correct = sum(x['status'] == 'ok' and x['parsed']['verdict'] == ('ACCEPT' if x['kind'] == 'developer' else 'REJECT') for x in group)
                scores[arm] = {'proxy_correct': correct, 'planned': 80, 'valid': sum(x['status'] == 'ok' for x in group)}
            chosen = 'adjusted' if scores['adjusted']['proxy_correct'] > scores['strict']['proxy_correct'] else 'strict'
            dump(out / 'selection_sealed.json', {'sealed_at_utc': now(), 'chosen_arm': chosen,
                'scores': scores, 'selection_rule': cfg['selection_rule'], 'heldout_inference_started': False,
                'development_output_hashes': [{'path': str(p.relative_to(out)), 'sha256': sha(p)} for p in files]})
            print('SELECTION_SEALED', chosen, scores, flush=True)
    verify()
    assert len(list((out / 'historical').glob('*.json'))) == 2197
    assert len(list((out / 'disjoint').glob('*.json'))) == 560
    dump(out / 'completion.json', {'completed_at_utc': now(), 'historical_records': 2197,
        'disjoint_records': 560, 'actual_inference_calls': total_calls, 'attempted_generation_requests_this_run': submitted_calls, 'elapsed_seconds': time.monotonic() - started,
        'frozen_inputs_verified': True, 'selection_sha256': sha(out / 'selection_sealed.json')})
    print('COMPLETED', total_calls, now(), flush=True)


if __name__ == '__main__':
    main()
