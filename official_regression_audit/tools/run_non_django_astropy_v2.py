"""Frozen official-regression replay. Infrastructure failures are never rejections."""
import argparse,ast,concurrent.futures,hashlib,json,os,re,signal,subprocess,time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXP=ROOT/'experiment_non_django'

def now():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):
    with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')

def freeze():
    cases=json.loads((EXP/'CASE_INPUTS.json').read_text())['cases'];targets=[]
    for c in cases:
        folder=EXP/'sources'/c['instance_id'];prep=json.loads((folder/'PREPARED.json').read_text())
        assert all(v['patches_applied'] for v in prep['variants']),c['instance_id']
        mapped=[]
        for label in c['official_FAIL_TO_PASS']:
            if '::' in label:
                node=label.split('[',1)[0];assert (folder/'base'/node.split('::')[0]).is_file(),node
                mapped.append({'official_label':label,'targets':[node]})
            else:
                files=[s[6:] for s in c['test_patch'].splitlines() if s.startswith('+++ b/') and s.endswith('.py')]
                found=[]
                for fn in files:
                    tree=ast.parse((folder/'base'/fn).read_text())
                    for n in tree.body:
                        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==label:found.append(fn+'::'+label)
                assert found,(c['instance_id'],label)
                mapped.append({'official_label':label,'targets':found})
        extra=[]
        if c['instance_id']=='pydata__xarray-3305':
            node='xarray/tests/test_dataarray.py::TestDataArray::test_sortby'
            assert node in c['official_PASS_TO_PASS'];extra=[node]
        selected=sorted(set(t for m in mapped for t in m['targets'])|set(extra))
        targets.append({'instance_id':c['instance_id'],'environment_key':prep['environment_key'],
            'python':prep['python'],'mapping':mapped,'additional_official_PASS_TO_PASS':extra,'targets':selected})
    dump(EXP/'TARGETS.json',{'cases':targets,'rule':'All official FAIL_TO_PASS functions; parameterized labels expand to whole function. SymPy short names map to every matching top-level function in official test_patch files. Add only xarray3305 official sortby PASS_TO_PASS because the archived rationale explicitly alleges that collateral regression. No outputs consulted.'})
    versions={}
    for key in sorted(set(t['environment_key'] for t in targets)):
        py=ROOT/'runtimes'/key/'bin/python'
        p=subprocess.run([str(py),'-c','import sys,importlib.metadata as m,json; print(json.dumps({"python":sys.version,"packages":sorted((d.metadata["Name"],d.version) for d in m.distributions())}))'],capture_output=True,text=True,check=True)
        versions[key]=json.loads(p.stdout)
    dump(EXP/'RUNTIME_FROZEN.json',versions)
    protocol='''# Official regression replay, non-Django extension (22 tasks)

This adds all remaining non-Django tasks in the archived hosted reviewer's 38 nonaccepted officially-unresolved candidates. It is a census of this stratum, not all saved reviewer outputs or all failing patches.

Three isolated full pinned-source trees per task: base + official test_patch; archived candidate + official test_patch; developer + official test_patch. No tested source compatibility edits. Native extensions, when required, are compiled from the same pinned base and shared only across these Python-only patch variants. Native build failures are infrastructure failures, never candidate failures. Build/dependency retries retain separate logs and artifacts.

Targets are every official FAIL_TO_PASS function, expanded to all parameter values; short SymPy identifiers map mechanically to matching top-level functions in official test-patch files. One preselected collateral target, xarray3305 sortby, comes from official PASS_TO_PASS and the archived rationale. No other collateral claims are presumed tested.

Run the project's original source under Python 3.9 with isolated pinned dependency environments. PYTHONPATH gives pinned source priority over installed release code. Disable external pytest plugin autoload; project conftest/plugins remain in use. Use real pytest JUnit XML and preserve stdout/stderr, process status and timing. At most four CPU processes; single-threaded BLAS; timeout 240 seconds per variant, process group killed on timeout. Build/dependency/collection errors and skips remain explicit. Repaired environments may be replayed in a new output directory; previous failed attempts remain intact.

Successful functional discrimination requires actual executed test failure/error in candidate and successful developer control with no collection/startup error. A functional failure does not validate every rationale sentence, maintainability objection, security hypothesis or original human review. No new human labels, hosted model calls, full SWEbench container harness runs, or GPU allocation.
'''
    with (EXP/'PROTOCOL.md').open('x') as f:f.write(protocol)
    paths=[EXP/'CASE_INPUTS.json',EXP/'TARGETS.json',EXP/'RUNTIME_FROZEN.json',EXP/'PROTOCOL.md',Path(__file__)]
    paths+=list((EXP/'sources').glob('*/PREPARED.json'))
    dump(EXP/'FREEZE.json',{'frozen_at_utc':now(),'sha256':{str(p.relative_to(ROOT)):sha(p) for p in paths}})
    print('FROZEN',len(targets),sum(len(t['targets']) for t in targets),flush=True)

def run_one(job,out):
    c,name=job;iid=c['instance_id'];source=EXP/'sources'/iid/name
    prefixes=[source]
    if (source/'src').is_dir():prefixes.insert(0,source/'src')
    if iid.startswith('matplotlib'):prefixes.insert(0,source/'lib')
    env=dict(os.environ,PYTHONPATH=os.pathsep.join(map(str,prefixes)),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLBACKEND='Agg',PYTHONHASHSEED='0',
        SETUPTOOLS_USE_DISTUTILS='stdlib')
    xml=out/(iid+'_'+name+'.xml')
    plugins=['-p','pytest_remotedata.plugin','-p','pytest_doctestplus.plugin','-p','pytest_arraydiff.plugin'] if iid.startswith('astropy') else []
    command=[c['python'],'-m','pytest',*plugins,'-q','--tb=short','-o','addopts=','--junitxml='+str(xml),*c['targets']]
    record={'instance_id':iid,'variant':name,'command':command,'cwd':str(source),'PYTHONPATH':env['PYTHONPATH'],'started_at_utc':now()}
    start=time.monotonic()
    with (out/(iid+'_'+name+'.stdout.txt')).open('xb') as stdout,(out/(iid+'_'+name+'.stderr.txt')).open('xb') as stderr:
        p=subprocess.Popen(command,cwd=source,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
        try:record['returncode']=p.wait(timeout=240);record['timed_out']=False
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);p.wait();record.update(returncode=p.returncode,timed_out=True)
    record.update(finished_at_utc=now(),elapsed_seconds=time.monotonic()-start)
    dump(out/(iid+'_'+name+'_process.json'),record)
    print(iid,name,record['returncode'],round(record['elapsed_seconds'],2),flush=True)
    return record

def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['freeze','run']);ap.add_argument('--version',default='v1');ap.add_argument('--cases',nargs='*');a=ap.parse_args()
    if a.action=='freeze':freeze();return
    frozen=json.loads((EXP/'FREEZE.json').read_text())
    for p,h in frozen['sha256'].items():assert sha(ROOT/p)==h,p
    cases=json.loads((EXP/'TARGETS.json').read_text())['cases']
    if a.cases:cases=[c for c in cases if c['instance_id'] in a.cases]
    out=EXP/('execution_'+a.version);out.mkdir()
    dump(out/'PLAN.json',{'created_at_utc':now(),'cases':[c['instance_id'] for c in cases],'freeze_sha256':sha(EXP/'FREEZE.json'),'environment_amendments':[str(p.relative_to(ROOT)) for p in sorted((ROOT/'evidence').glob('*supplement*'))]})
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(lambda job:run_one(job,out),[(c,n) for c in cases for n in ['base','candidate','developer']]))
    dump(out/'EXECUTION.json',records)

if __name__=='__main__':main()
