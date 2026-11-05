"""Prespecified descriptive endpoints from saved outputs; standard library only."""
from pathlib import Path
from collections import Counter
import json,hashlib,math,argparse
ROOT=Path(__file__).resolve().parent

def wilson(k,n):
 if not n:return None
 z=1.959963984540054;p=k/n;den=1+z*z/n;center=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
 return [center-half,center+half]
def mcnemar(b,c):
 n=b+c
 return 1.0 if not n else min(1.0,2*sum(math.comb(n,k) for k in range(min(b,c)+1))/(2**n))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--data-root',type=Path,default=ROOT);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();r=args.data_root;o=args.output;o.mkdir()
 cohort=json.loads((r/'cohort.json').read_text());candidates=json.loads((r/'candidates.json').read_text());completion=json.loads((r/'run_v1/completion.json').read_text());assert completion['raw_records']==1009
 raw={c['code']:json.loads((r/'run_v1/raw'/(c['code']+'.json')).read_text()) for c in candidates};assert len(raw)==1009
 def accept(code):
  v=raw[code]
  return None if v['status']!='ok' else v['parsed']['verdict']=='ACCEPT'
 def proportion(codes):
  vals=[accept(c) for c in codes];n=sum(v is not None for v in vals);k=sum(v is True for v in vals)
  return {'planned':len(vals),'valid':n,'failures':len(vals)-n,'accepted':k,'acceptance_valid':k/n if n else None,'wilson95_valid':wilson(k,n),'planned_denominator_accept_lower':k/len(vals),'planned_denominator_accept_upper':(k+len(vals)-n)/len(vals)}
 split={s:proportion(['g_'+iid for iid in ids]) for s,ids in cohort['split_ids'].items()}
 goldcodes=['g_'+c['instance_id'] for c in candidates if c['kind']=='gold']
 agent=[c for c in candidates if c['kind']=='unresolved_agent'];pairs=Counter();missing=[]
 for c in agent:
  av=accept(c['code']);gv=accept('g_'+c['instance_id'])
  if av is None or gv is None:missing.append(c['instance_id']);continue
  pairs[('both_accept' if av and gv else 'agent_only' if av else 'gold_only' if gv else 'both_reject')]+=1
 paired={'available':302,'underlying_unresolved_tasks':306,'empty_or_absent_candidate_packets':4,'complete':sum(pairs.values()),'missing':missing,**{k:pairs[k] for k in ['both_accept','agent_only','gold_only','both_reject']}}
 paired.update(exact_mcnemar_p=mcnemar(pairs['agent_only'],pairs['gold_only']),agent=proportion([c['code'] for c in agent]),developer_same_tasks=proportion(['g_'+c['instance_id'] for c in agent]))
 token={'input_tokens':sum(x.get('input_tokens',0) for x in raw.values()),'output_tokens':sum(x.get('output_tokens',0) for x in raw.values()),'calls_with_generated_output':sum(bool(x.get('raw')) for x in raw.values())}
 result={'analysis':'prospective full-split gold and matched unresolved controls; test-blind7B adapter','split_gold':split,'unique_gold':proportion(goldcodes),'shared_lite_verified_tasks':93,'same_task_controls':paired,'status_counts':dict(Counter(x['status'] for x in raw.values())),'token_cost':token,'new_human_ratings':0,'new_harness_runs':0,'no_historical_reviewer_revalidation_claim':True,'no_independent_calibration_generalization_claim':True}
 with (o/'SUMMARY.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 checks={'all1009_candidates_accounted':len(raw)==len(candidates)==1009,'300_and500_complete_split_membership':len(cohort['split_ids']['lite'])==300 and len(cohort['split_ids']['verified'])==500,'707_unique_gold_and93_shared':len(goldcodes)==707 and len(set(cohort['split_ids']['lite'])&set(cohort['split_ids']['verified']))==93,'302_same_task_controls':len(agent)==302 and all('g_'+c['instance_id'] in raw for c in agent),'all_complete_messages_unchanged':all(c['issue'] in ''.join(m['content'] for m in raw[c['code']]['messages']) and c['diff'] in ''.join(m['content'] for m in raw[c['code']]['messages']) for c in candidates),'no_false_pass_instruction':all('No execution results are provided.' in v['messages'][0]['content'] for v in raw.values()),'no_invalid_output_imputed':all(accept(code) is None for code,v in raw.items() if v['status']!='ok')}
 with (o/'VALIDATION.json').open('x') as f:json.dump({'checks':checks,'results_sha256':hashlib.sha256((o/'SUMMARY.json').read_bytes()).hexdigest()},f,indent=2);f.write('\n')
 print(json.dumps(result,indent=2));assert all(checks.values())

if __name__=='__main__':main()
