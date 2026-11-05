"""Recompute positive-control classifications from the authors' native saved results."""
import argparse,collections,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'prior_systems/cihan_replication/Replication Package/experiment-artifacts'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def summarize(rows):
    valid=[r for r in rows if r['classification_status']=='valid']
    return {'rows':len(rows),'valid':len(valid),'invalid':len(rows)-len(valid),
      'Correct':sum(r['classification']=='Correct' for r in valid),
      'Incorrect':sum(r['classification']=='Incorrect' for r in valid),
      'correct_rate':sum(r['classification']=='Correct' for r in valid)/len(valid) if valid else None,
      'unique_function_ids':len({r['function_id'] for r in rows}),
      'notes':'Repeated runs and model/prompt conditions are not independent tasks. Invalid or potentially stale classifications are excluded, not treated as Incorrect.'}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=DEFAULT);ap.add_argument('--output',type=Path,default=ROOT/'evidence/cihan_native_replay.json');a=ap.parse_args()
    records=[];sources=[];groups={}
    for p in sorted(a.source.glob('run_*/results/*.jsonl')):
        sources.append({'path':str(p.relative_to(a.source)),'sha256':sha(p),'bytes':p.stat().st_size})
        rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
        canonical='_gt_' in p.name;expected=164 if canonical else 492
        assert len(rows)==expected,(str(p),len(rows))
        for i,r in enumerate(rows):
            assert r['question']=='question_'+str(i+1)
            raw=r.get('suggested_label');label=raw.strip() if isinstance(raw,str) else None
            error=str(r.get('error','none'))
            unsafe=error in ['cannot parse the response yaml','invalid yaml variable value type']
            status='valid' if label in ['Correct','Incorrect'] and not unsafe else 'unavailable_or_potentially_stale'
            if canonical:assert r['prev_label']=='Correct' and r['prev_score']==1.0
            records.append({'run':p.parent.parent.name,'condition':p.stem,'canonical':canonical,
                'function_id':i%164,'classification':label,'classification_status':status,
                'saved_error':error,'original_input_label':r['prev_label'],
                'corrected_code_execution_is_distinct':True})
        groups[p.parent.parent.name+'/'+p.stem]=summarize(records[-len(rows):])
    assert len(sources)==24 and len(records)==7872
    positive=[r for r in records if r['canonical']];generated=[r for r in records if not r['canonical']]
    counts={'canonical':summarize(positive),'generated':summarize(generated)}
    pairs={}
    for r in records:
        if r['canonical']:pairs.setdefault(r['condition'].replace('_gt_','_')+'/canonical',[]).append(r)
    report={'native_artifact_source':'https://doi.org/10.5281/zenodo.14962566','saved_results_only':True,
        'new_inference_calls':0,'same_SWEbench_binary_mergeability_experiment':False,
        'scope':'Original HumanEval correctness labels and original authors canonical positive controls. No adapter outputs are substituted for native results.',
        'row_count':7872,'files':sources,'by_run_condition':groups,'totals':counts,
        'limits':['Rows include repeated functions, three runs, models and description conditions; pooled totals are descriptive, not independent-task estimates.',
          'Correct/Incorrect concerns functional code correctness rather than repository merge decisions.',
          'Original result code can leave stale classifications after YAML parse/field failures; those saved rows are excluded without imputation.',
          'No original API calls, corrected-code execution, same-task SWEbench inference, or independent human labels are claimed.']}
    with a.output.open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps({'rows':7872,'totals':counts,'conditions':groups},indent=2))
if __name__=='__main__':main()
