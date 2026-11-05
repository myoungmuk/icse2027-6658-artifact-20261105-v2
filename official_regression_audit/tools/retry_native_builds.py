"""Additional pinned-source builds, preserving earlier failed build records."""
import concurrent.futures,hashlib,json,os,shutil,subprocess
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
EXP=ROOT/'experiment_non_django'
def run(iid):
    folder=EXP/'sources'/iid;prep=json.loads((folder/'PREPARED.json').read_text());base=folder/'base'
    env=dict(os.environ,SETUPTOOLS_USE_DISTUTILS='stdlib',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    cmd=[prep['python'],'setup.py','build_ext','--inplace','-j','2']
    r={'command':cmd,'started_at_utc':datetime.now(timezone.utc).isoformat()}
    with (folder/'native_build_v2.stdout.txt').open('xb') as o,(folder/'native_build_v2.stderr.txt').open('xb') as e:
        p=subprocess.run(cmd,cwd=base,env=env,stdout=o,stderr=e,timeout=600)
    r.update(returncode=p.returncode,finished_at_utc=datetime.now(timezone.utc).isoformat(),files=[])
    if p.returncode==0:
        for src in sorted(base.rglob('*.so')):
            rel=src.relative_to(base)
            r['files'].append({'path':str(rel),'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
            for name in ['candidate','developer']:
                target=folder/name/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
        for src in [base/'astropy/version.py',base/'lib/matplotlib/_version.py']:
            if src.is_file():
                for name in ['candidate','developer']:shutil.copy2(src,folder/name/src.relative_to(base))
    with (folder/'NATIVE_BUILD_V2.json').open('x') as f:json.dump(r,f,indent=2)
    print(iid,p.returncode,len(r['files']),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as p:list(p.map(run,['astropy__astropy-13236','matplotlib__matplotlib-24627']))
