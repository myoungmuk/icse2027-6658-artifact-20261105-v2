"""Freeze and execute official targets plus full-package diagnostic witnesses."""
import argparse,concurrent.futures,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];EXP=ROOT/'experiment_gold'
V11=ROOT.parent/'ICSE2027_6658_RegressionAudit_20261105_v11'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):
    with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def freeze():
    rows=[]
    for c in json.loads((EXP/'CASE_INPUTS.json').read_text())['cases']:
        p=json.loads((EXP/'sources'/c['instance_id']/'PREPARED.json').read_text())
        label=c['official_FAIL_TO_PASS'][0]
        if c['repo']=='django/django':
            name,qual=label.split(' (');target=qual[:-1]+'.'+name
            # Entire class provides retained regression controls, not just F2P.
            targets=[qual[:-1]]
        else:targets=[label]
        rows.append({'instance_id':c['instance_id'],'repo':c['repo'],'targets':targets,'official_labels':c['official_FAIL_TO_PASS'],'variants':list(p['variants']),'environment_key':p['environment_key']})
    dump(EXP/'TARGETS.json',{'cases':rows,'selection':'All three hosted nonaccepted gold tasks. Exact official parameter labels for pytest; full official Django FastDeleteTests class. Diagnostic probes fixed separately; not a population error estimate.'})
    shutil.copyfile(V11/'experiment/launch_official_tests.py',EXP/'launch_django_tests.py')
    protocol="""# Full-package gold rejection witnesses (v12)

All three hosted nonaccepted gold cases; post-hoc technical inspection. Archived
gold diff equals the official developer patch byte for byte for every task.
Base and gold are separate full source trees at immutable task base commits, with
the same official test patch. Native extensions are built from that source once
and used unchanged across Python-only variants; no release-wheel overlays.

Official controls: exact FAIL_TO_PASS pytest parameter labels for sklearn and
Matplotlib; the full Django FastDeleteTests class containing the official new
regression. Full-package witnesses for Matplotlib use empty/singleton C with
max/min/mean reductions and default/explicit mincnt. sklearn compares all fold
scores, selected C, coefficients, intercepts and predictions on Iris, crossing
fit_intercept True/False with ovr/multinomial. A separate external constructor
instrumentation run records the omitted/passed keyword without editing source.

Two diagnostic interventions are explicitly not historical patches: restoring
fit_intercept in the gold sklearn constructor; changing only default mincnt to
one in gold Matplotlib, matching the focal source change in the documented later
upstream fix. They isolate mechanisms; they do not confer maintainer acceptance.
The sklearn comparison records exact equality and maximum numerical differences.
No untested concern is automatically true and no independent human truth labels
or rationale-accuracy percentage are produced.

Freeze case inputs, protocol, targets, launchers and prepared source hashes before
the first test. Use isolated existing CPU dependency environments without changing
them; extra build dependencies live in v12. Preserve every startup/build/test retry
under a distinct output name. Bounded CPU processes, no GPU or model calls.
"""
    with (EXP/'PROTOCOL.md').open('x') as f:f.write(protocol)
    files=[EXP/n for n in ['CASE_INPUTS.json','TARGETS.json','PROTOCOL.md','launch_django_tests.py','probe_full_package.py']]
    files += [Path(__file__)]+list((EXP/'sources').glob('*/PREPARED.json'))+list((EXP/'sources').glob('*/NATIVE_BUILD*.json'))
    dump(EXP/'FREEZE.json',{'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'sha256':{str(p.relative_to(ROOT)):sha(p) for p in files}})
    print('Frozen',len(rows),'cases',sum(len(r['variants']) for r in rows),'variants')
def run(job,out):
    c,n,kind=job;iid=c['instance_id'];work=EXP/'sources'/iid/n
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLBACKEND='Agg',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
    prefix=iid+'_'+n+'_'+kind
    if c['repo']=='django/django':
        env.update(PYTHONPATH=str(V11/'experiment/runtime_dependencies'),SETUPTOOLS_USE_DISTUTILS='local')
        cmd=[sys.executable,str(EXP/'launch_django_tests.py'),'--source',str(work),'--output',str(out/(prefix+'_tests.json')),*c['targets']]
    else:
        env.update(PYTHONPATH=str(work/('lib' if c['repo']=='matplotlib/matplotlib' else '.')),SETUPTOOLS_USE_DISTUTILS='stdlib')
        py=V11/'runtimes'/c['environment_key']/'bin/python'
        if kind=='official':cmd=[str(py),'-m','pytest','-q','--tb=short','-o','addopts=','--junitxml='+str(out/(prefix+'.xml')),*c['targets']]
        else:cmd=[str(py),str(EXP/'probe_full_package.py'),'--kind','matplotlib' if c['repo']=='matplotlib/matplotlib' else 'sklearn','--output',str(out/(prefix+'_observations.json'))]
    record={'instance_id':iid,'variant':n,'kind':kind,'command':cmd,'cwd':str(work),'PYTHONPATH':env['PYTHONPATH'],'started_at_utc':datetime.now(timezone.utc).isoformat()}
    try:
        p=subprocess.run(cmd,cwd=work,env=env,capture_output=True,text=True,timeout=240)
        record.update(returncode=p.returncode,timed_out=False);stdout=p.stdout;stderr=p.stderr
    except subprocess.TimeoutExpired as ex:record.update(returncode=None,timed_out=True);stdout=str(ex.stdout);stderr=str(ex.stderr)
    for label,s in [('stdout',stdout),('stderr',stderr)]:
        with (out/(prefix+'.'+label+'.txt')).open('x') as f:f.write(s)
    record['finished_at_utc']=datetime.now(timezone.utc).isoformat();dump(out/(prefix+'_process.json'),record)
    print(iid,n,kind,record['returncode'],flush=True);return record
def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['freeze','run']);ap.add_argument('--version',default='v1');a=ap.parse_args()
    if a.action=='freeze':freeze();return
    frozen=json.loads((EXP/'FREEZE.json').read_text())
    for p,h in frozen['sha256'].items():assert sha(ROOT/p)==h,p
    cases=json.loads((EXP/'TARGETS.json').read_text())['cases'];out=EXP/('execution_'+a.version);out.mkdir()
    jobs=[(c,n,k) for c in cases for n in c['variants'] for k in (['official'] if c['repo']=='django/django' else ['official','witness'])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as p:records=list(p.map(lambda job:run(job,out),jobs))
    dump(out/'EXECUTION.json',{'records':records,'processes':len(records),'freeze_sha256':sha(EXP/'FREEZE.json')})
if __name__=='__main__':main()
