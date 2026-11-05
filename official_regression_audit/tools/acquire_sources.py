"""New isolated, complete pinned source variants and mechanically selected tests."""
import argparse,ast,concurrent.futures,hashlib,json,re,shutil,subprocess,tarfile
from datetime import datetime,timezone
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):
    with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')


def added_locations(diff):
    out={};path=None;line=None
    for s in diff.splitlines():
        if s.startswith('+++ b/'):
            path=s[6:];out.setdefault(path,set())
        elif s.startswith('@@ '):
            m=re.search(r'\+(\d+)',s);line=int(m.group(1))
        elif path is not None and line is not None:
            if s.startswith('+'):
                out[path].add(line);line+=1
            elif s.startswith(' '):line+=1
    return out


def targets(tree,diff):
    result=[];selection=[]
    for path,lines in added_locations(diff).items():
        p=Path(path)
        if not p.parts or p.parts[0]!='tests' or not (p.name.startswith('test') and p.suffix=='.py'):continue
        module='.'.join(p.with_suffix('').parts[1:])
        syntax=ast.parse((tree/path).read_text());selected=[]
        for cls in [n for n in syntax.body if isinstance(n,ast.ClassDef)]:
            for node in cls.body:
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test_'):
                    start=min([node.lineno]+[n.lineno for n in node.decorator_list])
                    if any(start<=i<=node.end_lineno for i in lines):selected.append(module+'.'+cls.name+'.'+node.name)
        if not selected:selected=[module]
        result+=selected;selection.append(dict(test_file=path,added_lines=sorted(lines),targets=selected))
    assert result,'No official regression target could be identified'
    return sorted(set(result)),selection


def acquire(case,experiment,source_cache):
    iid=case['instance_id'];folder=experiment/'sources'/iid;folder.mkdir(parents=True)
    url='https://codeload.github.com/django/django/tar.gz/'+case['base_commit']
    archive=folder/'upstream_base.tar.gz';reuse=None
    if source_cache and iid=='django__django-13028':
        old=source_cache/iid/'upstream_base.tar.gz'
        if old.exists():
            assert sha(old)=='f629862682dc7f1f5b3dc827f4e50f93d9aa4627aee6c6d12a927d397b1ac59f'
            shutil.copyfile(old,archive);reuse=str(old)
    if not archive.exists():
        with urllib.request.urlopen(url,timeout=90) as r:body=r.read()
        with archive.open('xb') as f:f.write(body)
    pristine=folder/'pristine';pristine.mkdir()
    with tarfile.open(archive) as tar:tar.extractall(pristine,filter='data')
    trees=[p for p in pristine.iterdir() if p.is_dir()];assert len(trees)==1
    tree=trees[0]
    for name,text in [('candidate',case['candidate_diff']),('developer',case['developer_diff']),('official_tests',case['test_patch'])]:
        with (folder/(name+'.diff')).open('x') as f:f.write(text)
    variants=[];reference_targets=None;mapping=None
    for name in ['base','candidate','developer']:
        work=folder/name;shutil.copytree(tree,work)
        applications=[]
        for patch in ([name] if name!='base' else [])+['official_tests']:
            command=['git','apply','--verbose','--whitespace=nowarn',str((folder/(patch+'.diff')).resolve())]
            p=subprocess.run(command,cwd=work,capture_output=True,text=True)
            applications.append(dict(patch=patch,sha256=sha(folder/(patch+'.diff')),returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
            if p.returncode:break
        applied=all(x['returncode']==0 for x in applications)
        selected=None
        if applied:
            selected,m=targets(work,case['test_patch'])
            if reference_targets is None:reference_targets=selected;mapping=m
            assert selected==reference_targets,(iid,name,'different regression targets')
        changed=set(added_locations(case['candidate_diff']))|set(added_locations(case['developer_diff']))|set(added_locations(case['test_patch']))
        hashes={p:sha(work/p) for p in sorted(changed) if (work/p).is_file()}
        variants.append(dict(name=name,source_path=str(work.resolve()),patches_applied=applied,applications=applications,targets=selected,file_hashes=hashes))
    receipt=dict(instance_id=iid,base_commit=case['base_commit'],url=url,archive_sha256=sha(archive),
        archive_bytes=archive.stat().st_size,reused_immutable_archive=reuse,
        acquired_at_utc=datetime.now(timezone.utc).isoformat(),targets=reference_targets,target_mapping=mapping,variants=variants)
    dump(folder/'RECEIPT.json',receipt)
    print('ACQUIRED',iid,'targets',len(reference_targets or []),'applied',sum(v['patches_applied'] for v in variants),flush=True)
    return receipt


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--experiment',type=Path,default=ROOT/'experiment')
    ap.add_argument('--source-cache',type=Path,default=ROOT.parent/'ICSE2027_6658_FactCheck_20261105_v9/integration')
    args=ap.parse_args();experiment=args.experiment.resolve();(experiment/'sources').mkdir()
    cases=json.loads((experiment/'CASE_INPUTS.json').read_text())['cases']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(acquire,c,experiment,args.source_cache) for c in cases]
        results=[f.result() for f in futures]
    dump(experiment/'ACQUISITION.json',{'cases':sorted(results,key=lambda x:x['instance_id']),'protocol_sha256':sha(experiment/'PROTOCOL.md')})


if __name__=='__main__':main()
