"""Pre-execution mapping of benchmark method IDs/docstrings, without importing tests."""
import ast,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def method_catalog(tree,paths):
    methods={}
    for path in paths:
        p=Path(path)
        if p.suffix!='.py' or p.parts[0]!='tests' or not p.name.startswith('test'):continue
        module='.'.join(p.with_suffix('').parts[1:])
        for cls in ast.parse((tree/p).read_text()).body:
            if isinstance(cls,ast.ClassDef):
                for node in cls.body:
                    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test_'):
                        methods[module+'.'+cls.name+'.'+node.name]=ast.get_docstring(node) or ''
    return methods


def exists(tree,target):
    parts=target.split('.')
    for n in range(len(parts)-2,0,-1):
        p=tree/'tests'/Path(*parts[:n]).with_suffix('.py')
        if p.exists():
            node=ast.parse(p.read_text())
            for name in parts[n:]:
                matches=[x for x in getattr(node,'body',[]) if isinstance(x,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and x.name==name]
                if not matches:return False
                node=matches[0]
            return isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))
    return False


def main():
    exp=ROOT/'experiment';cases=json.loads((exp/'CASE_INPUTS.json').read_text())['cases'];acq=json.loads((exp/'ACQUISITION.json').read_text());by={c['instance_id']:c for c in acq['cases']};result={}
    norm=lambda t:' '.join(t.split()).strip()
    for c in cases:
        iid=c['instance_id'];a=by[iid];tree=exp/'sources'/iid/'base';paths=[r['test_file'] for r in a['target_mapping']];catalog=method_catalog(tree,paths);targets=set(a['targets']);mapping=[]
        for label in c['official_FAIL_TO_PASS']:
            match=re.fullmatch(r'(test_\w+) \(([^)]+)\)',label);resolved=[];method=None
            if match:
                method,path=match.groups();target=path if path.endswith('.'+method) else path+'.'+method
                if exists(tree,target):resolved=[target]
            if not resolved:
                desc=norm(label)
                for name,doc in catalog.items():
                    first=norm(doc.split('\n')[0]) if doc else ''
                    if first and (first.startswith(desc) or desc.startswith(first)):resolved.append(name)
            targets.update(resolved);mapping.append({'official_label':label,'resolved_targets':resolved,'resolved':bool(resolved)})
        for v in a['variants']:
            if v['patches_applied']:
                work=exp/'sources'/iid/v['name']
                assert all(exists(work,t) for t in targets),(iid,v['name'],targets)
        result[iid]={'targets':sorted(targets),'official_FAIL_TO_PASS_mapping':mapping,
            'unresolved_official_labels':[x['official_label'] for x in mapping if not x['resolved']],
            'same_targets_for_all_variants':True,'target_selection_before_execution':True}
        print(iid,'targets',len(targets),'official_labels',len(mapping),'unresolved',sum(not x['resolved'] for x in mapping),flush=True)
    with (exp/'TARGETS_FINAL.json').open('x') as f:json.dump({'cases':result},f,ensure_ascii=False,indent=2);f.write('\n')


if __name__=='__main__':main()
