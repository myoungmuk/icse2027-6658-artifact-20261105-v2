"""Copy preserved sources and fix a post-hoc diagnostic plan before execution."""
import hashlib,json,shutil,zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
OLD=BASE/'ICSE2027_6658_RegressionAudit_20261105_v11'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):
    if p.exists():assert json.loads(p.read_text())==x;return
    with p.open('x') as f:json.dump(x,f,indent=2)
def main():
    wheel=[]
    for p in sorted((ROOT/'wheels').glob('*.whl')):
        wheel.append({'file':p.name,'sha256':sha(p)})
        with zipfile.ZipFile(p) as z:z.extractall(ROOT/'dependencies')
    assert len(wheel)==11
    dump(ROOT/'experiment/DEPENDENCIES.json',{'installed_in_new_target_only':True,'wheels':wheel,'original_environments_mutated':False})
    cases=[]
    for folder,ids in [('experiment',['django__django-13568']),('experiment_non_django',['astropy__astropy-13236','pydata__xarray-6744','scikit-learn__scikit-learn-25102'])]:
        allcases=json.loads((OLD/folder/'CASE_INPUTS.json').read_text())['cases']
        for c in [c for c in allcases if c['instance_id'] in ids]:
            iid=c['instance_id'];oldsrc=OLD/folder/'sources'/iid;dst=ROOT/'experiment/sources'/iid;dst.mkdir(parents=True,exist_ok=True)
            prep=json.loads((oldsrc/'PREPARED.json').read_text()) if not iid.startswith('django') else {};critical=[]
            # Omit build intermediates/caches, retain installed native extensions and actual tests.
            for variant in ['base','candidate','developer']:
                shutil.copytree(oldsrc/variant,dst/variant,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','.git','build','tmp'))
                files=set()
                for patch in [c['candidate_diff'],c['developer_diff'],c['test_patch']]:
                    files.update(s[6:] for s in patch.splitlines() if s.startswith('+++ b/'))
                for rel in sorted(files):
                    a=oldsrc/variant/rel;b=dst/variant/rel
                    assert sha(a)==sha(b)
                    critical.append({'original':str(a),'copy':str(b.relative_to(ROOT)),'sha256':sha(a)})
            variants=['base','candidate','developer']
            if iid.startswith('django'):
                shutil.copytree(dst/'candidate',dst/'candidate_import_only')
                p=dst/'candidate_import_only/django/contrib/auth/checks.py';s=p.read_text()
                assert 'from django.db import models' not in s
                p.write_text('from django.db import models\n'+s);variants.append('candidate_import_only')
                python='/usr/local/bin/python';targets=['auth_tests.test_checks.UserModelChecksTests.test_username_partially_unique','auth_tests.test_checks.UserModelChecksTests.test_username_unique_with_model_constraint']
            else:
                python=prep['python'];entry=next(t for t in json.loads((OLD/folder/'TARGETS.json').read_text())['cases'] if t['instance_id']==iid);targets=entry['targets']
            cases.append({'instance_id':iid,'variants':variants,'python':python,'official_targets':targets,'original_critical_hashes':critical,'inputs':c})
    dump(ROOT/'experiment/CASES.json',{'cases':cases})
    shutil.copyfile(OLD/'experiment/launch_official_tests.py',ROOT/'experiment/launch_official_tests.py')
    protocol='''# v13 residual CPU diagnostics (post-hoc selection)

Four cases were selected because v11 explicitly left their deeper claims untested:
Django13568 import NameError, sklearn25102 default branch/value casting,
Astropy13236 warning-before-behavior, and xarray6744 Dask skips.
These cases are post-hoc, not a population accuracy sample or independent labels.

Copy full pinned source from preserved v11, preserving critical source/test bytes
and native extensions. Never edit old sources/environments. Django's fourth tree
adds only a missing models import, a diagnostic intervention rather than the
archived candidate. Base/candidate/developer stay unchanged. Witnesses test
single/multi/conditional uniqueness under both authentication backends, default
and pandas StandardScaler plus PCA, structured ndarray type/ECSV roundtrip,
and centered rolling iteration for NumPy/Dask with default/min_periods1.

Replay Django selected official targets in four trees. Replay Astropy official
targets in three trees under original warnings, then separately with FutureWarning
ignored to reach behavioral assertions. Do not replace original warning-policy
results with amended-policy results. Replay xarray's same whole official rolling
function with pinned Dask2022.9.2 in a separate dependency target. Newly executed
Dask cases are not claimed as prior executed passes. Skip/collection/timeout and
instrumentation errors remain explicit. At most four single-threaded CPU workers.
No original native-model inference, LLM calls, GPU jobs or new human responses.
'''
    (ROOT/'experiment/PROTOCOL.md').write_text(protocol)
    paths=[ROOT/'experiment'/n for n in ['CASES.json','DEPENDENCIES.json','PROTOCOL.md','launch_official_tests.py']]
    paths+=[ROOT/'tools'/n for n in ['run_v13.py','probe_v13.py']]
    dump(ROOT/'experiment/FREEZE.json',{'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'sha256':{str(p.relative_to(ROOT)):sha(p) for p in paths}})
    print('Prepared',len(cases),'cases',sum(len(c['variants']) for c in cases),'trees')
if __name__=='__main__':main()
