"""Acquire immutable full gold-case source and build native extensions on CPU."""
import concurrent.futures,hashlib,json,os,shutil,subprocess,tarfile,urllib.request
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];EXP=ROOT/'experiment_gold'
PREV=ROOT.parent/'ICSE2027_6658_RegressionAudit_20261105_v11'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):
    with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def run(c):
    iid=c['instance_id'];folder=EXP/'sources'/iid;folder.mkdir(parents=True)
    url='https://codeload.github.com/'+c['repo']+'/tar.gz/'+c['base_commit']
    archive=folder/'upstream_base.tar.gz';reused=None
    if c['repo']=='django/django':
        old=ROOT.parent/'ICSE2027_6658_FactCheck_20261105_v9/integration'/iid/'upstream_base.tar.gz'
        shutil.copyfile(old,archive);reused=str(old)
    else:
        with urllib.request.urlopen(url,timeout=90) as r:body=r.read()
        with archive.open('xb') as f:f.write(body)
    pristine=folder/'pristine';pristine.mkdir()
    with tarfile.open(archive) as t:t.extractall(pristine,filter='data')
    tree=next(p for p in pristine.iterdir() if p.is_dir());base=folder/'base';shutil.copytree(tree,base)
    build=None;key=None
    if c['repo']!='django/django':
        key='legacy_science' if c['repo']=='scikit-learn/scikit-learn' else 'modern_science'
        py=PREV/'runtimes'/key/'bin/python'
        env=dict(os.environ,SETUPTOOLS_USE_DISTUTILS='stdlib',SETUPTOOLS_SCM_PRETEND_VERSION=c['version']+'.0',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        cmd=[str(py),'setup.py','build_ext','--inplace','-j','2']
        build={'command':cmd,'started_at_utc':datetime.now(timezone.utc).isoformat()}
        with (folder/'native_build.stdout.txt').open('xb') as o,(folder/'native_build.stderr.txt').open('xb') as e:
            try:p=subprocess.run(cmd,cwd=base,env=env,stdout=o,stderr=e,timeout=600);build['returncode']=p.returncode
            except subprocess.TimeoutExpired:build['returncode']=None;build['timed_out']=True
        build.update(finished_at_utc=datetime.now(timezone.utc).isoformat(),extensions=[{'path':str(p.relative_to(base)),'sha256':sha(p)} for p in sorted(base.rglob('*.so'))])
        dump(folder/'NATIVE_BUILD.json',build)
    shutil.copytree(base,folder/'gold')
    for n,text in [('gold',c['gold_diff']),('official_tests',c['test_patch'])]:
        with (folder/(n+'.diff')).open('x') as f:f.write(text)
    applications={}
    for name in ['base','gold']:
        apps=[]
        for patch in (['gold'] if name=='gold' else [])+['official_tests']:
            p=subprocess.run(['git','apply','--verbose','--whitespace=nowarn',str((folder/(patch+'.diff')).resolve())],cwd=folder/name,capture_output=True,text=True)
            apps.append({'patch':patch,'sha256':sha(folder/(patch+'.diff')),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
            if p.returncode:break
        assert all(a['returncode']==0 for a in apps),(iid,name,apps);applications[name]=apps
    diagnostic=None
    if c['repo']=='scikit-learn/scikit-learn':
        name='gold_restore_intercept';rel='sklearn/linear_model/logistic.py'
        before='log_reg = LogisticRegression(multi_class=multi_class)'
        after='log_reg = LogisticRegression(fit_intercept=fit_intercept, multi_class=multi_class)'
    elif c['repo']=='matplotlib/matplotlib':
        name='gold_default_one';rel='lib/matplotlib/axes/_axes.py'
        before='if mincnt is None:'+chr(10)+'                mincnt = 0'
        after='if mincnt is None:'+chr(10)+'                mincnt = 1'
    else:name=None
    if name:
        shutil.copytree(folder/'gold',folder/name);path=folder/name/rel;text=path.read_text();assert text.count(before)==1
        path.write_text(text.replace(before,after));diagnostic={'variant':name,'file':rel,'before':before,'after':after,'purpose':'Minimal diagnostic intervention, not a newly evaluated upstream patch or independent label.'}
    paths=set(line[6:] for diff in [c['gold_diff'],c['test_patch']] for line in diff.splitlines() if line.startswith('+++ b/'))
    names=['base','gold']+([name] if name else [])
    record={'instance_id':iid,'repo':c['repo'],'base_commit':c['base_commit'],'url':url,'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'reused_source_archive':reused,'environment_key':key,'native_build':build,'patch_applications':applications,'diagnostic_intervention':diagnostic,
      'variants':{n:{rel:sha(folder/n/rel) for rel in sorted(paths) if (folder/n/rel).is_file()} for n in names}}
    dump(folder/'PREPARED.json',record);print('PREPARED',iid,build and build['returncode'],len(names),flush=True)
    return record
if __name__=='__main__':
    (EXP/'sources').mkdir();cases=json.loads((EXP/'CASE_INPUTS.json').read_text())['cases']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as p:records=list(p.map(run,cases))
    dump(EXP/'PREPARATION.json',{'cases':records})
