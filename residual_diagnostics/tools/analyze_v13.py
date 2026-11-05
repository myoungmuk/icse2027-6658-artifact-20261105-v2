"""Portable offline analysis of post-hoc residual diagnostics, not human labels."""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];EXP=ROOT/'experiment'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'evidence/residual_analysis_v13.json');a=ap.parse_args()
    for n in ['FREEZE.json','AMENDMENT_V2.json']:
        assert all(sha(ROOT/p)==h for p,h in read(EXP/n)['sha256'].items())
    runs={v:read(EXP/v/'EXECUTION.json')['records'] for v in ['execution_v1','execution_v2']}
    keyed={}
    for ver,records in runs.items():
        for r in records:
            assert not r['timed_out']
            keyed[(r['instance_id'],r['variant'],r['kind'])]=(ver,r)
    assert len(keyed)==26 and sum(map(len,runs.values()))==36
    tests=[];witnesses={};scenarios=0
    for (iid,v,kind),(ver,r) in keyed.items():
        path=EXP/ver;stem=iid+'_'+v+'_'+kind
        if kind=='witness':
            assert r['returncode']==0
            x=read(path/(stem+'_observations.json'));witnesses.setdefault(iid,{})[v]=x
            scenarios+=len(x['scenarios']);continue
        assert r['returncode'] in [0,1]
        if iid.startswith('django'):
            x=read(path/(stem+'_tests.json'));assert x['top_exception'] is None
            s=x['runner_summaries'][0];count={'tests':s['tests_run'],'failures':s['failures'],'errors':s['errors'],'skipped':s['skipped']}
        else:
            suites=list(ET.parse(path/(stem+'.xml')).getroot().iter('testsuite'));assert len(suites)==1
            count={k:int(suites[0].get(k)) for k in ['tests','failures','errors','skipped']}
        tests.append({'instance_id':iid,'variant':v,'policy':kind,'source':str(path.relative_to(ROOT)/(stem+('_tests.json' if iid.startswith('django') else '.xml'))),'returncode':r['returncode'],**count})
    dj=witnesses['django__django-13568'];sk=witnesses['scikit-learn__scikit-learn-25102'];astro=witnesses['astropy__astropy-13236'];xr=witnesses['pydata__xarray-6744']
    assert all(s['exception_type']=='NameError' for s in dj['candidate']['scenarios'])
    assert all(not s['result']['check_ids'] for s in dj['candidate_import_only']['scenarios'])
    assert all(bool(s['result']['check_ids'])==(i>=2) for i,s in enumerate(dj['developer']['scenarios']))
    assert sk['candidate']['scenarios'][0]['exception_type']=='NameError'
    assert sk['candidate']['scenarios'][1]['result']['values']==[[-1],[0],[1]]
    assert all(sk[v]['scenarios'][1]['result']['values']==sk[v]['scenarios'][1]['result']['expected_analytic_values'] for v in ['base','developer'])
    assert all(sk[v]['scenarios'][2]['status']=='returned' for v in sk)
    assert astro['base']['scenarios'][0]['result']['column_type']=='NdarrayMixin'
    assert astro['candidate']['scenarios'][0]['result']['column_type']==astro['developer']['scenarios'][0]['result']['column_type']=='Column'
    assert astro['candidate']['scenarios'][1]['result']['column_type']=='Column' and not astro['candidate']['scenarios'][1]['result']['has_mask']
    assert astro['developer']['scenarios'][1]['result']['column_type']=='MaskedColumn' and astro['developer']['scenarios'][1]['result']['has_mask']
    assert all(s['result']['labels']==[0,0,0,1,2,3,4,5,6] for s in xr['candidate']['scenarios'])
    assert all(s['result']['manual_means']==s['result']['vectorized_means'] for s in xr['developer']['scenarios'])
    assert all(s['metadata']['dask']=='2022.9.2' for s in xr.values())
    checks={'frozen_inputs_and_amendment_unchanged':True,'all_final_processes_completed':True,
      'all_developer_controls_pass':all(t['returncode']==0 for t in tests if t['variant']=='developer'),
      'dask32slots_per_variant_no_skips':all(t['tests']==32 and t['skipped']==0 for t in tests if t['instance_id'].startswith('pydata')),
      'all_actual_test_slots122_no_skips':sum(t['tests'] for t in tests)==122 and sum(t['skipped'] for t in tests)==0,
      'witness51scenarios_in13processes':scenarios==51 and sum(len(v) for v in witnesses.values())==13}
    assert all(checks.values())
    result={'scope':'Four post-hoc cases with previously untested deeper assertions. Author technical diagnostics, not independent rationale labels or a population error rate.',
      'case_count':4,'source_trees':13,'final_processes':26,'all_attempt_processes':36,
      'retained_replaced_attempts':{'Django_witness_app_registry_failures':4,'Astropy_pytest_plugin_collection_failures':6},
      'final_official_or_amended_processes':13,'final_test_slots':122,'final_skips':0,'newly_enabled_Dask_slots':48,
      'final_witness_processes':13,'witness_scenarios':51,'tests':tests,'witnesses':witnesses,'checks':checks,
      'findings':[
        'Django missing import triggers NameError. Adding only that import reveals suppression of E003/W004 for multi-field and conditional constraints; developer preserves checks. The diagnostic is not the archived candidate.',
        'sklearn default StandardScaler raises NameError; pandas integer StandardScaler truncates to -1,0,1 instead of +-1.224744871391589. PCA renamed-column output succeeds in all three variants: broad claims about every renamed-column path are unsupported.',
        'Astropy candidate and developer both use Column for ordinary structured data; type conversion alone cannot establish premature incompatibility. Candidate emits a misleading future warning and loses structured masks. Ignoring that warning separately still leaves the masked-column official test failing; developer passes.',
        'xarray with Dask executes all32 official slots per variant, previously16 were skipped. Base6 and candidate12 failures, developer0. Candidate repeats labels0 three times and omits7/8, with empty initial windows; developer iteration matches vectorized means in NumPy/Dask under default and min_periods1.'],
      'limits':['Selection is post-hoc; no error-rate estimate or independent human adjudication.',
        'Astropy amended warning-policy tests remain separate from original-policy tests.',
        'Django import-only intervention is a diagnostic, not a new original patch.',
        'No full container harness, model inference, GPU job or new human rating.']}
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps({k:result[k] for k in ['case_count','final_processes','all_attempt_processes','final_test_slots','witness_scenarios','checks']},indent=2))
if __name__=='__main__':main()
