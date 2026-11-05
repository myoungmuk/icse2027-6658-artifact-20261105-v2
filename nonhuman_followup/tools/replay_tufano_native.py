"""Recompute exact-string revision matches from the pinned author's saved outputs."""
import argparse, collections, hashlib, json, re, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',type=Path,default=ROOT/'prior_systems/tufano_native/saved_outputs/generated-predictions')
    ap.add_argument('--output',type=Path,default=ROOT/'evidence/tufano_native_replay.json')
    a=ap.parse_args();results=[];sources=[]
    for p in sorted(a.source.glob('*-encoder-predictions.zip')):
        sources.append({'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        with zipfile.ZipFile(p) as z:
            for n in sorted(z.namelist()):
                if not n.endswith('.txt') or n.startswith('__MACOSX'):continue
                k=int(re.search(r'_k(\d+)_',n).group(1));data=z.read(n)
                blocks=re.split(r'\n\s*\n',data.decode().strip());exact=0;keys=[]
                for b in blocks:
                    ls=b.splitlines()
                    gold=[s.split(':',1)[1].strip() for s in ls if s.startswith('ORACLE ')]
                    preds=[s.split(':',1)[1].strip() for s in ls if re.match(r'^PREDICTION\s+\d+\s*:',s)]
                    inputs=[s.split(':',1)[1].strip() for s in ls if s.startswith('INPUT_CODE ')]
                    assert len(gold)==len(inputs)==1 and len(preds)==k
                    exact+=gold[0] in preds;keys.append((inputs[0],gold[0]))
                assert len(blocks)==1719
                results.append({'file':n,'sha256':hashlib.sha256(data).hexdigest(),'beam_size':k,
                    'representation':'abstracted' if '_abstracted' in n else 'raw',
                    'model':p.stem,'rows':len(blocks),'exact_match_any_beam':exact,
                    'exact_match_rate':exact/len(blocks),'duplicate_input_oracle_pairs':len(keys)-len(set(keys))})
    assert len(sources)==2 and len(results)==16
    report={'native_saved_outputs_only':True,'new_model_calls':0,'new_human_labels':0,
        'source_commit':'fe3711b91c079175dc2332090fcbb17eec98458d',
        'source_url':'https://github.com/anonyauthors/code_review',
        'task':'Generate a revised Java method, optionally conditioned on reviewer comment; not binary patch acceptance.',
        'metric':'Exact string equality after stripping field boundary whitespace. Any of k predictions equals ORACLE. No compilation or functional correctness claimed.',
        'unique_test_entities_as_documented':1719,'condition_files':16,'sources':sources,'conditions':results,
        'limits':['Files are sorted to put perfect predictions first; file row position is not a cross-model pairing key.',
            'Raw and abstracted representations and beams repeat test entities; no pooled independent-task estimate.',
            'Exact-match revision output is not a positive-control binary-judge experiment.',
            'No original model weights or new inference; this replays saved author outputs.']}
    with a.output.open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
