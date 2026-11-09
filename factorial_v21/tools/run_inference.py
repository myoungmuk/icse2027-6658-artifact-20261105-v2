"""Full finite factorial inference. Raw outputs immutable; interrupted runs append."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time
from prompts import ARMS, messages, parse, accepted

ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def dump(p,x):
    with p.open('x') as f: json.dump(x,f,ensure_ascii=False,indent=2); f.write('\n')
def verify():
    for row in json.loads((ROOT/'FREEZE.json').read_text())['files']:
        p=Path(row['path']); assert sha(p)==row['sha256'],str(p)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('model',choices=['7b','14b']);ap.add_argument('node');ap.add_argument('attempt');a=ap.parse_args()
    verify()
    import torch
    import vllm
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import GuidedDecodingParams
    cfg=json.loads((ROOT/'inputs/config.json').read_text());mcfg=cfg['models'][a.model]
    base=ROOT/('run_'+a.model);base.mkdir(exist_ok=True)
    records=base/'records';records.mkdir(exist_ok=True)
    attempt=base/a.attempt;attempt.mkdir()
    (attempt/'submissions').mkdir();(attempt/'completions').mkdir()
    dump(attempt/'environment.json',{'started_at_utc':now(),'model':a.model,'node':a.node,'python':platform.python_version(),'torch':torch.__version__,'vllm':vllm.__version__,'cuda':torch.version.cuda,'freeze_sha256':sha(ROOT/'FREEZE.json'),'config':cfg,'model_config':mcfg,'nvidia_smi':subprocess.check_output(['nvidia-smi'],text=True),'pip_freeze':subprocess.check_output([os.sys.executable,'-m','pip','freeze'],text=True)})
    llm=LLM(model=mcfg['model_path'],tokenizer=mcfg['model_path'],dtype='half',quantization=mcfg['quantization'],guided_decoding_backend='xgrammar',max_model_len=cfg['max_model_len'],gpu_memory_utilization=cfg['gpu_memory_utilization'],seed=cfg['seed'],max_num_seqs=cfg['max_num_seqs'],max_num_batched_tokens=cfg['max_num_batched_tokens'],enforce_eager=True,enable_prefix_caching=False,enable_chunked_prefill=True,trust_remote_code=False,disable_log_stats=False)
    tokenizer=llm.get_tokenizer(); print('MODEL_READY',now(),flush=True)
    cs=json.loads((ROOT/'inputs/candidates.json').read_text())
    prepared=[];eligibility=[]
    for ci,c in enumerate(cs):
        texts={};lens={};hashes={}
        for arm in ARMS:
            msg=messages(arm,c);text=tokenizer.apply_chat_template(msg,tokenize=False,add_generation_prompt=True)
            texts[arm]=text;lens[arm]=len(tokenizer(text,add_special_tokens=False)['input_ids'])
            hashes[arm]=hashlib.sha256(json.dumps(msg,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        eligible=max(lens.values())<=cfg['max_model_len']-cfg['max_tokens']
        eligibility.append({'code':c['code'],'input_tokens':lens,'eligible':eligible})
        # Counterbalance condition order while retaining identical model order.
        arms=ARMS[ci%4:]+ARMS[:ci%4]
        for arm in arms:
            rid=c['code']+'_'+arm;path=records/(rid+'.json')
            row={k:c[k] for k in ['code','instance_id','kind','splits']}
            row.update(id=rid,model=a.model,revision=mcfg['revision'],arm=arm,node=a.node,attempt=a.attempt,input_tokens=lens[arm],messages_sha256=hashes[arm],freeze_sha256=sha(ROOT/'FREEZE.json'))
            if path.exists():
                old=json.loads(path.read_text());assert old['messages_sha256']==hashes[arm] and old['freeze_sha256']==row['freeze_sha256'];continue
            if not eligible:
                row.update(status='input_too_long',raw=None,parsed=None,accepted=None)
                dump(path,row)
            else: prepared.append((row,texts[arm]))
    dump(attempt/'eligibility.json',eligibility)
    print('ELIGIBLE',sum(x['eligible'] for x in eligibility),'of',len(cs),'TODO',len(prepared),now(),flush=True)
    params=SamplingParams(temperature=cfg['temperature'],seed=cfg['seed'],max_tokens=cfg['max_tokens'],guided_decoding=GuidedDecodingParams(json_object=True,backend='xgrammar'))
    start=time.monotonic();submitted=returned=0
    for offset in range(0,len(prepared),48):
        batch=prepared[offset:offset+48];bid=f'{offset:05d}'
        dump(attempt/'submissions'/(bid+'.json'),{'ids':[r['id'] for r,_ in batch],'submitted_at_utc':now(),'requests':len(batch)})
        submitted+=len(batch)
        answers=llm.generate([t for _,t in batch],params,use_tqdm=False)
        assert len(answers)==len(batch)
        returned+=len(batch)
        for (row,text),answer in zip(batch,answers):
            val=answer.outputs[0];v,status=parse(val.text,val.finish_reason)
            row.update(status=status,raw=val.text,parsed=v,accepted=accepted(v) if v is not None else None,finish_reason=val.finish_reason,output_tokens=len(val.token_ids),returned_model_request_id=answer.request_id,completed_at_utc=now(),seed=cfg['seed'],temperature=cfg['temperature'])
            dump(records/(row['id']+'.json'),row)
        dump(attempt/'completions'/(bid+'.json'),{'returned_at_utc':now(),'requests':len(batch)})
        print('PROGRESS',returned,'/',len(prepared),'records',len(list(records.glob('*.json'))),'elapsed_seconds',round(time.monotonic()-start),now(),flush=True)
    verify();assert len(list(records.glob('*.json')))==4812
    dump(attempt/'completion.json',{'completed_at_utc':now(),'submitted':submitted,'returned':returned,'planned_records':4812,'elapsed_seconds':time.monotonic()-start,'frozen_inputs_verified':True})
    print('COMPLETED',a.model,4812,now(),flush=True)

if __name__=='__main__':main()
