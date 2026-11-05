"""Execute frozen CPU diagnoses with preserved outputs and bounded processes."""
import concurrent.futures,hashlib,json,os,signal,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];EXP=ROOT/'experiment'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def dump(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2)
def run(job,out):
    c,v,kind=job;iid=c['instance_id'];src=EXP/'sources'/iid/v;prefixes=[src]
    if (src/'src').is_dir():prefixes.insert(0,src/'src')
    if iid.startswith('pydata'):prefixes.append(ROOT/'dependencies')
    if iid.startswith('django'):prefixes.append(ROOT.parent/'ICSE2027_6658_RegressionAudit_20261105_v11/experiment/runtime_dependencies')
    env=dict(os.environ,PYTHONPATH=os.pathsep.join(map(str,prefixes)),PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYTHONHASHSEED='0',SETUPTOOLS_USE_DISTUTILS='local',MPLBACKEND='Agg')
    stem=iid+'_'+v+'_'+kind
    if kind=='witness':cmd=[c['python'],str(ROOT/'tools/probe_v13.py'),'--case',iid,'--source',str(src),'--output',str(out/(stem+'_observations.json'))]
    elif iid.startswith('django'):cmd=[c['python'],str(EXP/'launch_official_tests.py'),'--source',str(src),'--output',str(out/(stem+'_tests.json')),*c['official_targets']]
    else:
        cmd=[c['python'],'-m','pytest','-q','--tb=short','-p','no:cacheprovider','-o','addopts=','--junitxml='+str(out/(stem+'.xml'))]
        if kind=='official_futurewarning_ignored':cmd+=['-W','ignore::FutureWarning']
        cmd+=c['official_targets']
    record={'instance_id':iid,'variant':v,'kind':kind,'command':cmd,'cwd':str(src),'PYTHONPATH':env['PYTHONPATH'],'started_at_utc':now()};start=time.monotonic()
    with (out/(stem+'.stdout.txt')).open('xb') as stdout,(out/(stem+'.stderr.txt')).open('xb') as stderr:
        p=subprocess.Popen(cmd,cwd=src,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
        try:record.update(returncode=p.wait(timeout=240),timed_out=False)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();record.update(returncode=p.returncode,timed_out=True)
    record.update(finished_at_utc=now(),elapsed_seconds=time.monotonic()-start);dump(out/(stem+'_process.json'),record)
    print(iid,v,kind,record['returncode'],round(record['elapsed_seconds'],2),flush=True);return record
def main():
    f=json.loads((EXP/'FREEZE.json').read_text());assert all(sha(ROOT/p)==h for p,h in f['sha256'].items())
    cases=json.loads((EXP/'CASES.json').read_text())['cases'];jobs=[]
    for c in cases:
        iid=c['instance_id']
        for v in c['variants']:
            jobs.append((c,v,'witness'))
            if not iid.startswith('scikit'):jobs.append((c,v,'official'))
            if iid.startswith('astropy'):jobs.append((c,v,'official_futurewarning_ignored'))
    out=EXP/'execution_v1';out.mkdir();dump(out/'PLAN.json',{'jobs':[{'case':c['instance_id'],'variant':v,'kind':k} for c,v,k in jobs],'freeze_sha256':sha(EXP/'FREEZE.json')})
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(lambda job:run(job,out),jobs))
    dump(out/'EXECUTION.json',{'records':records})
if __name__=='__main__':main()
