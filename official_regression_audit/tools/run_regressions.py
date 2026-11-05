"""Run 48 bounded, isolated CPU processes; retain incomplete and failed outcomes."""
import argparse,concurrent.futures,hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):
    with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--experiment',type=Path,default=ROOT/'experiment');ap.add_argument('--run-name',default='execution_v1');args=ap.parse_args()
    exp=args.experiment.resolve();freeze=json.loads((exp/'FREEZE.json').read_text())
    for f in freeze['files']:assert sha(exp/f['path'])==f['sha256'],f['path']
    acq=json.loads((exp/'ACQUISITION.json').read_text());out=exp/args.run_name;out.mkdir()
    env={'PATH':os.environ['PATH'],'PYTHONPATH':str(exp/'runtime_dependencies'),'PYTHONDONTWRITEBYTECODE':'1','SETUPTOOLS_USE_DISTUTILS':'local','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MPLBACKEND':'Agg','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','TZ':'UTC'}
    target_map=json.loads((exp/'TARGETS_FINAL.json').read_text())['cases']
    jobs=[(c,v) for c in acq['cases'] for v in c['variants']]
    def run(job):
        c,v=job;iid=c['instance_id'];code=iid+'_'+v['name'];started=datetime.now(timezone.utc).isoformat()
        if not v['patches_applied']:
            rec=dict(instance_id=iid,variant=v['name'],status='patch_application_failure',started_at_utc=started)
            dump(out/(code+'_process.json'),rec);return rec
        work=exp/'sources'/iid/v['name']
        assert all(sha(work/p)==h for p,h in v['file_hashes'].items())
        command=[sys.executable,str(exp/'launch_official_tests.py'),'--source',str(work),'--output',str(out/(code+'_tests.json')),*target_map[iid]['targets']]
        status='finished';returncode=None
        try:
            p=subprocess.run(command,cwd=exp,env=env,capture_output=True,text=True,timeout=180);stdout=p.stdout;stderr=p.stderr;returncode=p.returncode
        except subprocess.TimeoutExpired as ex:
            status='timeout';stdout=ex.stdout or b'';stderr=ex.stderr or b''
            if isinstance(stdout,bytes):stdout=stdout.decode(errors='replace')
            if isinstance(stderr,bytes):stderr=stderr.decode(errors='replace')
        (out/(code+'.stdout.txt')).write_text(stdout);(out/(code+'.stderr.txt')).write_text(stderr)
        rec=dict(instance_id=iid,variant=v['name'],status=status,command=command,returncode=returncode,
            started_at_utc=started,finished_at_utc=datetime.now(timezone.utc).isoformat(),tests_json_present=(out/(code+'_tests.json')).exists(),
            source_files_unchanged=all(sha(work/p)==h for p,h in v['file_hashes'].items()))
        dump(out/(code+'_process.json'),rec)
        print('FINISHED',code,'returncode',returncode,'status',status,flush=True)
        return rec
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records=list(pool.map(run,jobs))
    for f in freeze['files']:assert sha(exp/f['path'])==f['sha256'],f['path']
    dump(out/'EXECUTION.json',dict(python=sys.version,records=records,planned_processes=48,
        freeze_sha256=sha(exp/'FREEZE.json'),frozen_files_unchanged=True,new_full_harness_runs=0,new_model_calls=0,new_human_ratings=0))


if __name__=='__main__':main()
