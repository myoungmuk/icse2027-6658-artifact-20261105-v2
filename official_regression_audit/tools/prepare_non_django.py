"""Acquire pinned repositories and build native extensions before test freezing."""
import argparse,concurrent.futures,hashlib,json,os,shutil,subprocess,tarfile,urllib.request
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXP=ROOT/'experiment_non_django'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):
    with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')


def acquire(c):
    folder=EXP/'sources'/c['instance_id'];folder.mkdir(parents=True)
    url='https://codeload.github.com/'+c['repo']+'/tar.gz/'+c['base_commit']
    with urllib.request.urlopen(url,timeout=90) as r:body=r.read()
    archive=folder/'upstream_base.tar.gz'
    with archive.open('xb') as f:f.write(body)
    pristine=folder/'pristine';pristine.mkdir()
    with tarfile.open(archive) as tar:tar.extractall(pristine,filter='data')
    tree=next(p for p in pristine.iterdir() if p.is_dir())
    shutil.copytree(tree,folder/'base')
    record={'instance_id':c['instance_id'],'repo':c['repo'],'base_commit':c['base_commit'],'url':url,'archive_sha256':sha(archive),'archive_bytes':len(body),'acquired_at_utc':datetime.now(timezone.utc).isoformat()}
    dump(folder/'ACQUIRED.json',record);print('ACQUIRED',c['instance_id'],len(body),flush=True)
    return record


def env_key(c):
    iid=c['instance_id']
    if iid.startswith('sympy') or iid.endswith('3095') or iid.endswith('3305') or iid.endswith('14629'):return 'legacy_science'
    if iid.startswith('sphinx'):return 'sphinx_7' if c['version'].startswith('7') else 'sphinx_4'
    if iid.startswith('pylint'):return 'pylint_3'
    if iid.startswith('pytest'):return 'pytest_self'
    if iid.startswith('psf'):return 'requests'
    return 'modern_science'


def prepare(c):
    folder=EXP/'sources'/c['instance_id'];base=folder/'base';key=env_key(c);python=ROOT/'runtimes'/key/'bin/python'
    native=c['repo'] in ['astropy/astropy','matplotlib/matplotlib','scikit-learn/scikit-learn']
    build=None
    if native:
        env=dict(os.environ,SETUPTOOLS_USE_DISTUTILS='stdlib',SETUPTOOLS_SCM_PRETEND_VERSION=c['version']+'.0',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        command=[str(python),'setup.py','build_ext','--inplace','-j','2']
        started=datetime.now(timezone.utc).isoformat()
        try:
            p=subprocess.run(command,cwd=base,env=env,capture_output=True,text=True,timeout=600);rc=p.returncode;stdout=p.stdout;stderr=p.stderr
        except subprocess.TimeoutExpired as ex:
            rc=None;stdout=(ex.stdout or b'').decode(errors='replace');stderr=(ex.stderr or b'').decode(errors='replace')
        (folder/'native_build.stdout.txt').write_text(stdout);(folder/'native_build.stderr.txt').write_text(stderr)
        build=dict(command=command,returncode=rc,started_at_utc=started,finished_at_utc=datetime.now(timezone.utc).isoformat(),native_extension_files=[{'path':str(p.relative_to(base)),'sha256':sha(p)} for p in sorted(base.rglob('*.so'))])
        dump(folder/'NATIVE_BUILD.json',build)
    for name in ['candidate','developer']:shutil.copytree(base,folder/name)
    for name,text in [('candidate',c['candidate_diff']),('developer',c['developer_diff']),('official_tests',c['test_patch'])]:
        with (folder/(name+'.diff')).open('x') as f:f.write(text)
    variants=[]
    for name in ['base','candidate','developer']:
        work=folder/name;applications=[]
        for patch in ([name] if name!='base' else [])+['official_tests']:
            p=subprocess.run(['git','apply','--verbose','--whitespace=nowarn',str((folder/(patch+'.diff')).resolve())],cwd=work,capture_output=True,text=True)
            applications.append({'patch':patch,'sha256':sha(folder/(patch+'.diff')),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
            if p.returncode:break
        paths=[]
        for diff in [c['candidate_diff'],c['developer_diff'],c['test_patch']]:
            paths += [s[6:] for s in diff.splitlines() if s.startswith('+++ b/')]
        variants.append({'name':name,'patches_applied':all(a['returncode']==0 for a in applications),'applications':applications,
            'file_hashes':{p:sha(work/p) for p in sorted(set(paths)) if (work/p).is_file()}})
    record={**json.loads((folder/'ACQUIRED.json').read_text()),'environment_key':key,'python':str(python),
        'native_build_required':native,'native_build':build,'variants':variants}
    dump(folder/'PREPARED.json',record);print('PREPARED',c['instance_id'],key,'build',build and build['returncode'],flush=True)
    return record


def main():
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['acquire','prepare']);a=ap.parse_args()
    cases=json.loads((EXP/'CASE_INPUTS.json').read_text())['cases']
    if a.phase=='acquire':(EXP/'sources').mkdir()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records=list(pool.map(acquire if a.phase=='acquire' else prepare,cases))
    dump(EXP/('ACQUISITION.json' if a.phase=='acquire' else 'PREPARATION.json'),{'cases':records})


if __name__=='__main__':main()
