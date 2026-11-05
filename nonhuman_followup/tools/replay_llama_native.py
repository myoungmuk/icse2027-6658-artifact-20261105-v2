"""Read saved native review-necessity outputs; no model inference or code execution."""
import argparse, collections, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = Path('/workspace/models/torch/zenodo/llama-reviewer-prefix/7991113/extracted/prefix(lit-llama)/lit-llama-main')

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def native(s):
    s = s.lower()
    if 'yes' in s or 'true' in s: return 1
    if 'no' in s or 'false' in s: return 0
    return 0

def strict(s):
    return {'yes': 1, 'no': 0}.get(s.strip().lower())

def metrics(golds, preds):
    counts = collections.Counter(zip(golds, preds))
    tn, fp, fn, tp = (counts[k] for k in [(0,0),(0,1),(1,0),(1,1)])
    div = lambda a,b: a/b if b else 0.0
    return dict(rows=len(golds), tn=tn, fp=fp, fn=fn, tp=tp,
        accuracy=div(tp+tn,len(golds)), precision_yes=div(tp,tp+fp),
        recall_yes=div(tp,tp+fn), f1_yes=div(2*tp,2*tp+fp+fn))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source', type=Path, default=DEFAULT)
    ap.add_argument('--output', type=Path, default=ROOT/'evidence/llama_native_replay.json')
    a=ap.parse_args(); records=[]; files=[]
    for p in sorted((a.source/'output/adapter/crer_data/quality_estimation').rglob('predictions.txt')):
        gold=p.parent/'golds.txt'; preds=p.read_text().splitlines(); golds=gold.read_text().splitlines()
        diagnostic='test_train' in p.parts; assert len(preds)==len(golds)==(10000 if diagnostic else 31252)
        assert all(strict(g) is not None for g in golds)
        # The writer escapes strings using repr(s)[1:-1]. Keep these saved bytes:
        # no eval/unescaping; substring label tests match the original parser.
        valid=[i for i,s in enumerate(preds) if strict(s) is not None]
        record={'condition':str(p.parent.relative_to(a.source/'output/adapter/crer_data/quality_estimation')),
            'training_diagnostic_excluded_from_test':diagnostic,
            'native_parser':metrics([native(g) for g in golds],[native(s) for s in preds]),
            'strict_valid_rows':len(valid),'strict_invalid_rows':len(preds)-len(valid),
            'strict_valid_only':metrics([strict(golds[i]) for i in valid],[strict(preds[i]) for i in valid]),
            'noncanonical_outputs':dict(collections.Counter(s for s in preds if strict(s) is None)),
            'native_invalid_to_zero':sum(not any(t in s.lower() for t in ['yes','true','no','false']) for s in preds)}
        records.append(record)
        for f in [p,gold]: files.append({'path':str(f.relative_to(a.source)),'sha256':sha(f),'bytes':f.stat().st_size})
    assert len(records)==5
    test=a.source/'data/crer_data/quality_estimation/test.json'
    alignment=None
    if test.exists():
        data=json.loads(test.read_text()); assert len(data)==31252
        assert len({d['instruction'] for d in data})==1
        alignment={'test_dataset_sha256':sha(test),'test_rows':len(data),
            'instruction':data[0]['instruction'],
            'all_four_test_gold_files_match_dataset_order':all(
                (a.source/f['path']).read_text().splitlines()==[repr(d['output'])[1:-1] for d in data]
                for f in files if f['path'].endswith('golds.txt') and '/test_train/' not in f['path'])}
        assert alignment['all_four_test_gold_files_match_dataset_order']
    report={'source':'https://doi.org/10.5281/zenodo.7991113','saved_results_only':True,
        'new_model_calls':0,'new_training':0,'new_human_labels':0,
        'native_task':'review necessity: whether a diff hunk requires code review, not mergeability',
        'native_parser_rule':'lowercase; substring yes/true first => 1; no/false => 0; otherwise => 0',
        'strict_parser_rule':'entire stripped lowercased saved string must be yes or no; invalid excluded only in separate strict summary',
        'test_rows_per_condition':31252,'test_conditions':4,'test_prediction_rows':125008,
        'training_diagnostic_rows':10000,'files':files,'dataset_alignment':alignment,'conditions':records,
        'limits':['Four conditions use the same test rows; not 125008 independent tasks.',
            'Checkpoints include last and named best; these are not new training or independent replications.',
            'Training diagnostic test_train is excluded from test claims.',
            'No same-task SWEbench binary judge inference, base checkpoint download or GPU job.']}
    with a.output.open('x') as f: json.dump(report,f,indent=2)
    print(json.dumps({'alignment':alignment,'conditions':records},indent=2))

if __name__=='__main__': main()
