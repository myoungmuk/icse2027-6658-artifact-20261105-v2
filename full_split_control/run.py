"""Finite prospective all-gold/matched-controls batch. No historical files edited."""
import gc,hashlib,json,os,platform,random,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
from prompts import judge_messages,parse
ROOT=Path(__file__).resolve().parent

def dump(p,x):
 with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def verify():
 for x in json.loads((ROOT/'freeze_manifest.json').read_text())['files']:
  assert hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256'],x['path']
def main():
 verify()
 import torch,transformers
 from transformers import AutoTokenizer,AutoModelForCausalLM
 assert torch.cuda.is_available()
 cfg=json.loads((ROOT/'config.json').read_text());out=ROOT/'run_v1';out.mkdir();(out/'raw').mkdir()
 torch.set_num_threads(4);random.seed(cfg['seed']);torch.manual_seed(cfg['seed']);torch.cuda.manual_seed_all(cfg['seed']);torch.backends.cuda.matmul.allow_tf32=False
 env={'started_at_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),'torch':torch.__version__,'transformers':transformers.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'config':cfg,'freeze_sha256':hashlib.sha256((ROOT/'freeze_manifest.json').read_bytes()).hexdigest(),'pip_freeze':subprocess.check_output([os.sys.executable,'-m','pip','freeze'],text=True),'scope':'New test-blind adapter evaluation, not historical model revalidation.'};dump(out/'environment.json',env)
 tokenizer=AutoTokenizer.from_pretrained(cfg['model_path'],local_files_only=True,padding_side='left')
 if tokenizer.pad_token_id is None:tokenizer.pad_token=tokenizer.eos_token
 records=[]
 for c in json.loads((ROOT/'candidates.json').read_text()):
  messages=judge_messages('icse_test_blind',c,c['diff']);rendered=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
  tokens=tokenizer(rendered,add_special_tokens=False)['input_ids']
  rec={k:c[k] for k in ['code','instance_id','kind','splits']};rec.update(messages=messages,input_tokens=len(tokens),max_new_tokens=cfg['max_new_tokens'])
  if len(tokens)>cfg['max_input_tokens']:
   rec.update(status='input_too_long',parsed=None,raw='');dump(out/'raw'/(c['code']+'.json'),rec)
  else:records.append((rec,rendered))
 records.sort(key=lambda x:(x[0]['input_tokens'],x[0]['code']))
 dump(out/'input_preflight.json',{'planned':1009,'within_context':len(records),'too_long':1009-len(records),'min_tokens':min(r[0]['input_tokens'] for r in records),'max_tokens':max(r[0]['input_tokens'] for r in records),'all_complete_text_no_truncation':True})
 print('PREFLIGHT',1009,len(records),records[-1][0]['input_tokens'],flush=True)
 model=AutoModelForCausalLM.from_pretrained(cfg['model_path'],local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='sdpa',device_map='cuda:0');model.eval();print('MODEL_READY',flush=True)
 oom_events=[];start_all=time.monotonic()
 def run_batch(part):
  batch=None;generated=None
  try:
   batch=tokenizer([x[1] for x in part],padding=True,return_tensors='pt',add_special_tokens=False).to('cuda')
   start=time.monotonic()
   with torch.inference_mode():generated=model.generate(**batch,do_sample=False,max_new_tokens=cfg['max_new_tokens'],pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id,use_cache=True)
   torch.cuda.synchronize();elapsed=time.monotonic()-start;width=batch['input_ids'].shape[1]
   outputs=generated[:,width:].tolist()
  except torch.cuda.OutOfMemoryError:
   oom_events.append({'codes':[x[0]['code'] for x in part],'max_input_tokens':max(x[0]['input_tokens'] for x in part)})
   del batch,generated;gc.collect();torch.cuda.empty_cache()
   if len(part)>1:
    mid=len(part)//2;run_batch(part[:mid]);run_batch(part[mid:]);return
   rec=part[0][0];rec.update(status='singleton_oom',parsed=None,raw='');dump(out/'raw'/(rec['code']+'.json'),rec);return
  for (rec,_),tokens in zip(part,outputs):
   stop=next((i for i,t in enumerate(tokens) if t==tokenizer.eos_token_id),None);actual=tokens[:stop] if stop is not None else tokens;raw=tokenizer.decode(actual,skip_special_tokens=True);parsed=parse(raw)
   rec.update(raw=raw,parsed=parsed,output_tokens=len(actual),finish_reason='eos' if stop is not None else 'length',batch_elapsed_seconds=elapsed,status='ok' if parsed is not None and stop is not None else 'invalid_or_truncated')
   dump(out/'raw'/(rec['code']+'.json'),rec)
  del batch,generated
 offset=0;batches=0
 while offset<len(records):
  end=offset+1
  while end<len(records) and end-offset<cfg['max_batch_size'] and records[end][0]['input_tokens']*(end-offset+1)<=cfg['padded_token_budget']:end+=1
  run_batch(records[offset:end]);offset=end;batches+=1
  if batches%5==0 or offset==len(records):print('PROGRESS',offset,'/',len(records),'elapsed_seconds',round(time.monotonic()-start_all),flush=True)
 verify();dump(out/'completion.json',{'completed_at_utc':datetime.now(timezone.utc).isoformat(),'planned':1009,'raw_records':len(list((out/'raw').glob('*.json'))),'frozen_hashes_verified':True,'oom_events':oom_events,'max_gpu_memory_allocated_bytes':torch.cuda.max_memory_allocated(),'elapsed_seconds':time.monotonic()-start_all});print('COMPLETED_HASHES_VERIFIED',flush=True)

if __name__=='__main__':main()
