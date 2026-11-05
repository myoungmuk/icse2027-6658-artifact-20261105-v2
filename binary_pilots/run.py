"""Finite GPU batch with raw responses, exact prompts and fail-closed accounting."""
import hashlib
import json
import os
import platform
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from prompts import judge_messages, parse, rubric_messages

ROOT = Path(__file__).resolve().parent

def dump(path, obj):
    with path.open('x') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')

def verify():
    for f in json.loads((ROOT / 'freeze_manifest.json').read_text())['files']:
        assert hashlib.sha256(Path(f['path']).read_bytes()).hexdigest() == f['sha256'], f['path']

def main():
    verify()
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    cfg = json.loads((ROOT / 'config.json').read_text())
    tasks = json.loads((ROOT / 'tasks.json').read_text())
    output = ROOT / 'run_v1'
    output.mkdir(exist_ok=False)
    (output / 'raw').mkdir()
    (output / 'rubrics').mkdir()
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    torch.set_num_threads(4)
    random.seed(cfg['seed'])
    torch.manual_seed(cfg['seed'])
    torch.cuda.manual_seed_all(cfg['seed'])
    torch.backends.cuda.matmul.allow_tf32 = False
    env = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
           'python': platform.python_version(), 'torch': torch.__version__,
           'transformers': transformers.__version__, 'cuda': torch.version.cuda,
           'gpu': torch.cuda.get_device_name(0), 'config': cfg,
           'freeze_manifest_sha256': hashlib.sha256((ROOT/'freeze_manifest.json').read_bytes()).hexdigest(),
           'determinism': 'Greedy decoding, fixed seed, batch size; bitwise cross-hardware reproducibility not claimed.'}
    env['pip_freeze'] = subprocess.check_output(['python3', '-m', 'pip', 'freeze'], text=True)
    dump(output / 'environment.json', env)
    tokenizer = AutoTokenizer.from_pretrained(cfg['model_path'], local_files_only=True,
                                             padding_side='left')
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    print('LOADING_MODEL', flush=True)
    model = AutoModelForCausalLM.from_pretrained(
        cfg['model_path'], local_files_only=True, torch_dtype=torch.bfloat16,
        attn_implementation='sdpa', device_map='cuda:0')
    model.eval()
    print('MODEL_READY', flush=True)

    def generate_batch(records, limit):
        results = []
        active = []
        for rec in records:
            rendered = tokenizer.apply_chat_template(rec['messages'], tokenize=False, add_generation_prompt=True)
            tokens = tokenizer(rendered, add_special_tokens=False)['input_ids']
            rec = {**rec, 'input_tokens': len(tokens), 'max_new_tokens': limit}
            if len(tokens) > cfg['max_input_tokens']:
                rec.update(status='input_too_long', raw='', parsed=None)
                results.append(rec)
            else:
                active.append((rec, rendered))
        if active:
            batch = tokenizer([x[1] for x in active], padding=True, return_tensors='pt',
                              add_special_tokens=False).to('cuda')
            start = time.monotonic()
            with torch.inference_mode():
                generated = model.generate(
                    **batch, do_sample=False, max_new_tokens=limit,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    use_cache=True)
            torch.cuda.synchronize()
            elapsed = time.monotonic() - start
            width = batch['input_ids'].shape[1]
            for (rec, _), tokens in zip(active, generated[:, width:].tolist()):
                stop = next((i for i, t in enumerate(tokens) if t == tokenizer.eos_token_id), None)
                actual = tokens[:stop] if stop is not None else tokens
                raw = tokenizer.decode(actual, skip_special_tokens=True)
                parsed = parse(raw) if rec['kind'] == 'judge' else None
                rec.update(raw=raw, output_tokens=len(actual),
                           finish_reason='eos' if stop is not None else 'length',
                           batch_elapsed_seconds=elapsed, parsed=parsed,
                           status=('ok' if (parsed is not None or rec['kind'] == 'rubric') and stop is not None else 'invalid_or_truncated'))
                results.append(rec)
        return results

    # Generate all per-bug rubrics without observing any new candidate verdicts.
    rubrics = {}
    for start in range(0, len(tasks), cfg['batch_size']):
        part = tasks[start:start + cfg['batch_size']]
        records = [{'kind': 'rubric', 'task_code': t['task_code'],
                    'messages': rubric_messages(t)} for t in part]
        for rec in generate_batch(records, cfg['rubric_max_new_tokens']):
            dump(output / 'rubrics' / (rec['task_code'] + '.json'), rec)
            if rec['status'] == 'ok' and rec['raw'].strip():
                rubrics[rec['task_code']] = rec['raw']
        print(f'RUBRICS {start + len(part)}/{len(tasks)}', flush=True)

    records = []
    for t in tasks:
        for source in ['agent', 'gold']:
            code = t['task_code'] + '_' + source
            for arm in cfg['arms']:
                rec = {'kind': 'judge', 'candidate_code': code, 'task_code': t['task_code'], 'arm': arm}
                if arm == 'shi_draft_rubric' and t['task_code'] not in rubrics:
                    dump(output / 'raw' / f'{code}_{arm}.json', {**rec, 'status': 'rubric_failed', 'parsed': None})
                    continue
                rec['messages'] = judge_messages(arm, t, t[source + '_diff'],
                                rubrics[t['task_code']] if arm == 'shi_draft_rubric' else None)
                records.append(rec)
    # Frozen hash ordering mixes arms/sources; neither source nor code goes into messages.
    records.sort(key=lambda r: hashlib.sha256((r['candidate_code'] + r['arm']).encode()).hexdigest())
    for start in range(0, len(records), cfg['batch_size']):
        part = records[start:start + cfg['batch_size']]
        for rec in generate_batch(part, cfg['judge_max_new_tokens']):
            dump(output / 'raw' / f'{rec["candidate_code"]}_{rec["arm"]}.json', rec)
        print(f'JUDGMENTS {start + len(part)}/{len(records)}', flush=True)
    verify()
    dump(output / 'completion.json', {'completed_at_utc': datetime.now(timezone.utc).isoformat(),
          'raw_records': len(list((output/'raw').glob('*.json'))),
          'rubrics': len(list((output/'rubrics').glob('*.json'))),
          'original_and_frozen_hashes_verified': True,
          'max_gpu_memory_allocated_bytes': torch.cuda.max_memory_allocated()})
    print('COMPLETED_HASHES_VERIFIED', flush=True)

if __name__ == '__main__':
    main()
