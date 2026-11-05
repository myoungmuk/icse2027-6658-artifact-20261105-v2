"""Offline analysis of actual official test results, preserving retry denominators."""
import argparse,collections,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def django(c):
    out=ROOT/'experiment/execution_v1';variants={}
    for name in ['base','candidate','developer']:
        prefix=c['instance_id']+'_'+name;x=load(out/(prefix+'_tests.json'));p=load(out/(prefix+'_process.json'))
        s=x['runner_summaries'];assert len(s)==1 and x['top_exception'] is None
        s=s[0];events=x['events']
        variants[name]={'tests':s['tests_run'],'skipped':s['skipped'],'failures':s['failures'],'errors':s['errors'],
            'executed':s['tests_run']-s['skipped'],'successful':s['successful'],
            'test_events':events,'source_result':str((out/(prefix+'_tests.json')).relative_to(ROOT)),
            'source_sha256':sha(out/(prefix+'_tests.json')),'process':p}
    return variants

def pytest(c):
    exp=ROOT/'experiment_non_django';iid=c['instance_id']
    dirs=sorted((p for p in exp.glob('execution_v*') if (p/(iid+'_developer_process.json')).exists()),key=lambda p:int(p.name.split('_v')[-1]))
    assert dirs,iid
    out=dirs[-1];variants={}
    for name in ['base','candidate','developer']:
        prefix=iid+'_'+name;process=load(out/(prefix+'_process.json'));xml=out/(prefix+'.xml')
        assert not process['timed_out'] and xml.is_file(),(iid,name)
        suites=list(ET.parse(xml).getroot().iter('testsuite'));assert len(suites)==1
        a=suites[0].attrib;counts={k:int(a[k]) for k in ['tests','failures','errors','skipped']};events=[]
        for t in suites[0].iter('testcase'):
            bad=[n for n in t if n.tag in ['error','failure','skipped']]
            event={'test_id':t.get('classname','')+'::'+t.get('name',''),'outcome':bad[0].tag if bad else 'success'}
            if bad:event.update(message=bad[0].get('message',''),traceback=bad[0].text or '')
            events.append(event)
        assert not any(e['outcome']=='error' and ('collection failure' in e.get('message','') or 'failed on setup' in e.get('message','')) for e in events),(iid,name)
        assert process['returncode'] in [0,1],(iid,name)
        variants[name]={**counts,'executed':counts['tests']-counts['skipped'],
            'successful':process['returncode']==0 and counts['errors']==0 and counts['failures']==0,
            'test_events':events,'source_result':str(xml.relative_to(ROOT)),'source_sha256':sha(xml),'process':process}
    return variants

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'evidence/regression_analysis.json');a=ap.parse_args()
    checks={};cases=[]
    for exp in ['experiment','experiment_non_django']:
        frozen=load(ROOT/exp/'FREEZE.json')
        hashes=frozen.get('sha256',frozen.get('files',{}))
        # Django uses explicit records under its original freeze structure.
        if isinstance(hashes,dict):
            checked={p:sha(ROOT/p)==h for p,h in hashes.items()};checks[exp+'_freeze_unchanged']=all(checked.values())
        else:checks[exp+'_freeze_unchanged']=all(sha((ROOT/exp/x['path']).resolve())==x['sha256'] for x in hashes)
        for c in load(ROOT/exp/'CASE_INPUTS.json')['cases']:
            variants=django(c) if exp=='experiment' else pytest(c)
            assert variants['developer']['successful'] and variants['developer']['executed']>0,c['instance_id']
            assert not variants['candidate']['successful'] and variants['candidate']['failures']+variants['candidate']['errors']>0,c['instance_id']
            assert not variants['base']['successful'],c['instance_id']
            cases.append({'instance_id':c['instance_id'],'repo':c['repo'],'base_commit':c['base_commit'],
                'packet_id':c['packet_id'],'verdict_sha256':c['verdict_sha256'],
                'archived_summary':c['archived_verdict']['summary'],'variants':variants,
                'interpretation':'Candidate functional failure with successful developer control. Does not validate all rationale sentences.'})
    assert len(cases)==len(set(c['instance_id'] for c in cases))==38
    checks.update(exact_38_unique_cases=True,all_developer_controls_succeed=True,all_candidates_fail_executed_tests=True,
        all_base_controls_fail=True,no_infrastructure_failure_in_final_selection=True,no_human_ratings_added=True)
    totals={name:dict(collections.Counter({k:sum(c['variants'][name][k] for c in cases) for k in ['tests','executed','skipped','failures','errors']})) for name in ['base','candidate','developer']}
    attempts=[]
    for exp in ['experiment','experiment_non_django']:
        for d in sorted((ROOT/exp).glob('execution_v*')):
            files=list(d.glob('*_process.json'));attempts.append({'directory':str(d.relative_to(ROOT)),'processes':len(files),'returncodes':dict(collections.Counter(str(load(p)['returncode']) for p in files))})
    result={'scope':'All 38 archived hosted nonaccepted officially-unresolved candidates; 16 Django and 22 other tasks. Targeted official regressions in full pinned source trees, not full SWEbench container harness.',
        'case_count':38,'final_variant_processes':114,'all_attempt_processes':sum(x['processes'] for x in attempts),
        'attempts':attempts,'totals':totals,'validation':checks,'cases':cases,
        'limits':['Parameter expansion and SymPy short-name mapping enlarge target scope; see frozen targets.',
            'Skipped tests are not executed passes. Django subtest events are not independent test-method counts.',
            'Final selection uses latest disclosed environment-repair attempt, never best outcome. Earlier failures remain preserved.',
            'Functional failure supports rejection at decision level; no automatic rationale-accuracy percentage or independent human truth labels.',
            'No new model inference, independent human ratings, full container harness runs, or GPU work.']}
    assert all(checks.values()),checks
    with a.output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ['case_count','final_variant_processes','all_attempt_processes','totals','validation']},indent=2))

if __name__=='__main__':main()
