from pathlib import Path
import json,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[1]
DATA=BASE/'ICSE2027_6658_GitHubRelease_20261105_v7/repository/historical_analysis/data'
def dump(p,x):
 with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
alltasks={};sources=[];split_ids={}
for split in ['lite','verified']:
 path=DATA/f'swebench_instances/{split}.jsonl';sources.append(path);rs=rows(path);split_ids[split]=[x['instance_id'] for x in rs]
 assert len(rs)==(300 if split=='lite' else 500)
 for t in rs:
  v={k:t[k] for k in ['instance_id','repo','base_commit','problem_statement','patch']}
  assert v['patch'].strip()
  if t['instance_id'] in alltasks:assert alltasks[t['instance_id']]==v
  alltasks[t['instance_id']]=v
assert len(alltasks)==707
candidates=[]
for iid,t in sorted(alltasks.items()):
 candidates.append({'code':'g_'+iid,'instance_id':iid,'kind':'gold','splits':[s for s,ids in split_ids.items() if iid in ids], 'repo':t['repo'],'base_commit':t['base_commit'],'issue':t['problem_statement'],'diff':t['patch']})
neg=DATA/'review_packets/verified_negctrl';sources += [neg/'packets.jsonl',neg/'packets_key.json']
keys={x['packet_id']:x for x in json.loads((neg/'packets_key.json').read_text())}
for p in sorted(rows(neg/'packets.jsonl'),key=lambda p:keys[p['packet_id']]['instance_id']):
 k=keys[p['packet_id']];assert k['candidate_source'].startswith('agent') and not k['resolved']
 t=alltasks[k['instance_id']];assert p['repo']==t['repo'] and p['base_commit']==t['base_commit'] and p['issue_text']==t['problem_statement'] and p['diff'].strip()
 candidates.append({'code':'a_'+k['instance_id'],'instance_id':k['instance_id'],'kind':'unresolved_agent','splits':['verified'],'original_packet_id':p['packet_id'],'repo':p['repo'],'base_commit':p['base_commit'],'issue':p['issue_text'],'diff':p['diff']})
assert len(candidates)==1009
cfg={'model_id':'Qwen/Qwen2.5-Coder-7B-Instruct','revision':'c03e6d358207e414f1eca0bb1891e29f1db0e242','model_path':'/workspace/models/huggingface/Qwen/Qwen2.5-Coder-7B-Instruct/c03e6d358207e414f1eca0bb1891e29f1db0e242','seed':6658,'max_batch_size':8,'padded_token_budget':16384,'max_input_tokens':32256,'max_new_tokens':512,'dtype':'bfloat16','do_sample':False}
dump(ROOT/'candidates.json',candidates);dump(ROOT/'config.json',cfg);dump(ROOT/'cohort.json',{'split_ids':split_ids,'unique_gold':707,'overlap':93,'unresolved_available_candidates':302,'unresolved_total':306,'planned_judgments':1009})
sources += [ROOT/x for x in ['PROTOCOL.md','prepare.py','run.py','prompts.py','config.json','candidates.json','cohort.json','run_gpu.sh']]
sources += [Path(cfg['model_path'])/f for f in ['config.json','generation_config.json','tokenizer_config.json','model.safetensors.index.json']]
dump(ROOT/'freeze_manifest.json',{'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'files':[{'path':str(p),'size':p.stat().st_size,'sha256':sha(p)} for p in sources],'weights_note':'Pinned revision; model config hashes only, no independent all-weight-shard hashing claim.'})
print('Frozen 707 unique gold +302 unresolved candidates; 1009 judgments.')
