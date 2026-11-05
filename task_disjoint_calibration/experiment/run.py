"""Finite staged run: development -> sealed selection -> untouched heldout inference."""
import gc
import hashlib
import json
import os
import platform
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from prompts import messages, parse

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, obj):
    with p.open('x') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def now():
    return datetime.now(timezone.utc).isoformat()


def verify():
    for item in json.loads((ROOT / 'freeze_manifest.json').read_text())['files']:
        assert sha(ROOT / item['path']) == item['sha256'], item['path']


def main():
    verify()
    import torch
    import transformers
    from transformers import AutoTokenizer, AutoModelForCausalLM
    assert torch.cuda.is_available()
    cfg = json.loads((ROOT / 'config.json').read_text())
    candidates = json.loads((ROOT / 'candidates.json').read_text())
    out = ROOT / 'run_v1'
    out.mkdir()
    (out / 'raw').mkdir()
    torch.set_num_threads(4)
    random.seed(cfg['seed'])
    torch.manual_seed(cfg['seed'])
    torch.cuda.manual_seed_all(cfg['seed'])
    torch.backends.cuda.matmul.allow_tf32 = False
    dump(out / 'environment.json', dict(started_at_utc=now(), python=platform.python_version(),
         torch=torch.__version__, transformers=transformers.__version__, cuda=torch.version.cuda,
         gpu=torch.cuda.get_device_name(0), config=cfg, freeze_sha256=sha(ROOT / 'freeze_manifest.json'),
         pip_freeze=subprocess.check_output([os.sys.executable, '-m', 'pip', 'freeze'], text=True)))
    tokenizer = AutoTokenizer.from_pretrained(cfg['model_path'], local_files_only=True, padding_side='left')
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    records = []
    for c in candidates:
        for arm in cfg['arms']:
            msg = messages(arm, c)
            text = tokenizer.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)
            length = len(tokenizer(text, add_special_tokens=False)['input_ids'])
            rec = {k: c[k] for k in ['code', 'instance_id', 'split', 'kind']}
            rec.update(arm=arm, messages=msg, input_tokens=length)
            records.append((rec, text))
    dump(out / 'input_preflight.json', dict(planned=len(records),
         too_long=sum(r['input_tokens'] > cfg['max_input_tokens'] for r, _ in records),
         max_tokens=max(r['input_tokens'] for r, _ in records),
         all_complete_text_no_truncation=True))
    print('PREFLIGHT', len(records), 'max_tokens', max(r['input_tokens'] for r, _ in records), flush=True)
    model = AutoModelForCausalLM.from_pretrained(cfg['model_path'], local_files_only=True,
            torch_dtype=torch.bfloat16, attn_implementation='sdpa', device_map='cuda:0')
    model.eval()
    print('MODEL_READY', flush=True)
    start_all = time.monotonic()
    oom_events = []

    def record_path(r):
        return out / 'raw' / (r['code'] + '_' + r['arm'] + '.json')

    def run_batch(part):
        batch = generated = None
        try:
            batch = tokenizer([t for _, t in part], padding=True, return_tensors='pt', add_special_tokens=False).to('cuda')
            start = time.monotonic()
            with torch.inference_mode():
                generated = model.generate(**batch, do_sample=False, max_new_tokens=cfg['max_new_tokens'],
                    pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id, use_cache=True)
            torch.cuda.synchronize()
            elapsed = time.monotonic() - start
            outputs = generated[:, batch['input_ids'].shape[1]:].tolist()
        except torch.cuda.OutOfMemoryError:
            oom_events.append(dict(codes=[r['code'] + '_' + r['arm'] for r, _ in part]))
            del batch, generated
            gc.collect()
            torch.cuda.empty_cache()
            if len(part) > 1:
                mid = len(part) // 2
                run_batch(part[:mid])
                run_batch(part[mid:])
                return
            rec = part[0][0]
            rec.update(status='singleton_oom', parsed=None, raw='')
            dump(record_path(rec), rec)
            return
        for (rec, _), tokens in zip(part, outputs):
            stop = next((i for i, t in enumerate(tokens) if t == tokenizer.eos_token_id), None)
            actual = tokens[:stop] if stop is not None else tokens
            raw = tokenizer.decode(actual, skip_special_tokens=True)
            parsed = parse(raw)
            rec.update(raw=raw, parsed=parsed, output_tokens=len(actual),
                       finish_reason='eos' if stop is not None else 'length',
                       batch_elapsed_seconds=elapsed,
                       status='ok' if parsed is not None and stop is not None else 'invalid_or_truncated')
            dump(record_path(rec), rec)
        del batch, generated

    for split in ['development', 'heldout']:
        if split == 'heldout':
            selection = json.loads((out / 'selection_sealed.json').read_text())
            for item in selection['development_raw_hashes']:
                assert sha(out / item['path']) == item['sha256']
            dump(out / 'heldout_started.json', dict(started_at_utc=now(),
                 selection_sha256=sha(out / 'selection_sealed.json'), chosen_arm=selection['chosen_arm'],
                 no_heldout_raw_existed=not any(json.loads(p.read_text())['split'] == 'heldout' for p in (out / 'raw').glob('*.json'))))
        group = []
        for rec, text in records:
            if rec['split'] != split:
                continue
            if rec['input_tokens'] > cfg['max_input_tokens']:
                rec.update(status='input_too_long', raw='', parsed=None)
                dump(record_path(rec), rec)
            else:
                group.append((rec, text))
        group.sort(key=lambda x: (x[0]['input_tokens'], x[0]['code'], x[0]['arm']))
        offset = batches = 0
        while offset < len(group):
            end = offset + 1
            while end < len(group) and end - offset < cfg['max_batch_size'] and group[end][0]['input_tokens'] * (end - offset + 1) <= cfg['padded_token_budget']:
                end += 1
            run_batch(group[offset:end])
            offset = end
            batches += 1
            if batches % 5 == 0 or offset == len(group):
                print('PROGRESS', split, offset, '/', len(group), 'elapsed_seconds', round(time.monotonic() - start_all), flush=True)
        if split == 'development':
            paths = sorted((out / 'raw').glob('*.json'))
            raw = [json.loads(p.read_text()) for p in paths]
            assert len(raw) == 160 and all(r['split'] == 'development' for r in raw)
            scores = {}
            for arm in cfg['arms']:
                rr = [r for r in raw if r['arm'] == arm]
                correct = sum(r['status'] == 'ok' and r['parsed']['verdict'] == ('ACCEPT' if r['kind'] == 'developer' else 'REJECT') for r in rr)
                scores[arm] = dict(proxy_correct=correct, planned=80, score=correct / 80,
                                   valid=sum(r['status'] == 'ok' for r in rr))
            chosen = 'adjusted' if scores['adjusted']['proxy_correct'] > scores['strict']['proxy_correct'] else 'strict'
            dump(out / 'selection_sealed.json', dict(sealed_at_utc=now(), chosen_arm=chosen, scores=scores,
                 rule=cfg['selection_score'], tie_break=cfg['tie_break'],
                 development_raw_hashes=[dict(path=str(p.relative_to(out)), sha256=sha(p)) for p in paths],
                 heldout_inference_started=False))
            print('SELECTION_SEALED', chosen, scores, flush=True)
    verify()
    dump(out / 'completion.json', dict(completed_at_utc=now(), planned=560,
         raw_records=len(list((out / 'raw').glob('*.json'))), frozen_hashes_verified=True,
         selection_sha256=sha(out / 'selection_sealed.json'), oom_events=oom_events,
         max_gpu_memory_allocated_bytes=torch.cuda.max_memory_allocated(), elapsed_seconds=time.monotonic() - start_all))
    print('COMPLETED_HASHES_VERIFIED', flush=True)


if __name__ == '__main__':
    main()
