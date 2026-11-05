"""Portable offline analysis of official gold regressions and targeted witnesses."""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];EXP=ROOT/'experiment_gold'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def flatten(x):
    if isinstance(x,dict):
        for k in sorted(x):yield from flatten(x[k])
    elif isinstance(x,list):
        for item in x:yield from flatten(item)
    else:yield float(x)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'evidence/gold_analysis.json');a=ap.parse_args()
    freeze=read(EXP/'FREEZE.json')
    assert all(sha(ROOT/p)==h for p,h in freeze['sha256'].items())
    out=EXP/'execution_v1';official=[];processes=read(out/'EXECUTION.json')['records']
    for p in processes:
        assert not p['timed_out']
        prefix=p['instance_id']+'_'+p['variant']+'_'+p['kind']
        if p['kind']!='official':assert p['returncode']==0;continue
        if p['instance_id'].startswith('django'):
            x=read(out/(prefix+'_tests.json'));assert x['top_exception'] is None and len(x['runner_summaries'])==1
            s=x['runner_summaries'][0];counts={'tests':s['tests_run'],'failures':s['failures'],'errors':s['errors'],'skipped':s['skipped']}
        else:
            suites=list(ET.parse(out/(prefix+'.xml')).getroot().iter('testsuite'));assert len(suites)==1
            counts={k:int(suites[0].get(k)) for k in ['tests','failures','errors','skipped']}
        assert p['returncode']==(1 if p['variant']=='base' else 0),(p,counts)
        official.append({'instance_id':p['instance_id'],'variant':p['variant'],'returncode':p['returncode'],**counts})
    sk={}
    for n in ['base','gold','gold_restore_intercept']:
        sk[n]=read(out/('scikit-learn__scikit-learn-11578_'+n+'_witness_observations.json'))
    comparisons=[]
    for left,right in zip(sk['gold']['scenarios'][:4],sk['gold_restore_intercept']['scenarios'][:4]):
        assert left['name']==right['name'] and left['status']==right['status']=='returned'
        differences={}
        for field in ['probabilities','coefficients','intercepts','selected_C','scores']:
            aa=list(flatten(left[field]));bb=list(flatten(right[field]));assert len(aa)==len(bb)
            differences[field]={'elements':len(aa),'max_absolute_difference':max(abs(x-y) for x,y in zip(aa,bb)),'exactly_equal':aa==bb}
        comparisons.append({'scenario':left['name'],'differences':differences})
    assert all(v['exactly_equal'] for c in comparisons for v in c['differences'].values())
    mpl={n:read(out/('matplotlib__matplotlib-26113_'+n+'_witness_observations.json')) for n in ['base','gold','gold_default_one']}
    for i in [0,1,2]:
        assert mpl['base']['scenarios'][i]['status']=='returned'
        assert mpl['gold']['scenarios'][i]['exception_type']=='ValueError'
        assert mpl['gold_default_one']['scenarios'][i]['status']=='returned'
    assert len(mpl['gold']['scenarios'][3]['warnings'])>0 and not mpl['gold_default_one']['scenarios'][3]['warnings']
    result={'scope':'All three hosted nonaccepted gold cases; full pinned packages, official tests and post-hoc diagnostic witnesses. No independent human adjudication.',
      'cases':3,'variant_trees':8,'processes':len(processes),'official_processes':len(official),'official_test_slots':sum(x['tests'] for x in official),'official_results':official,
      'witness_processes':6,'witness_scenarios':33,'matplotlib':mpl,'sklearn_constructor_traces':{n:x['scenarios'][-1] for n,x in sk.items()},
      'sklearn_gold_vs_restore_comparisons':comparisons,
      'findings':['All three official gold patches pass their official targets; each base fails the focal regression.',
        'Matplotlib gold triggers ValueError on empty/singleton max/min with omitted mincnt, although its official regression passes. Gold default-one diagnostic restores these scenarios; explicitly requested mincnt0 remains an error, as expected.',
        'sklearn omission of fit_intercept is real. Restoring it produces exactly equal scores, chosen C, coefficients, intercepts and predicted probabilities in four Iris CV configurations. This does not prove absence of all defects or dismiss maintainability concerns.',
        'Django official FastDeleteTests runs nine methods; base fails the new PK clearing target and gold passes all nine. Prior full-SQLite ordinary-path contradiction evidence remains separately preserved.'],
      'validation':{'frozen_inputs_unchanged':True,'all3gold_controls_pass':True,'all3bases_fail':True,'sklearn4configurations_exactly_equal':True,'matplotlib_full_package_regression_reproduced':True,'no_human_labels_or_model_calls':True},
      'limits':['Targets are purposeful post-hoc witnesses; no population-wide rationale error estimate.','Diagnostic interventions are not separate original developer patches.','Functional agreement cannot decide every maintainability or reviewer-value judgment.']}
    assert len(processes)==14 and len(official)==8
    with a.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:result[k] for k in ['cases','variant_trees','processes','official_processes','official_test_slots','witness_scenarios','validation']},indent=2))
if __name__=='__main__':main()
