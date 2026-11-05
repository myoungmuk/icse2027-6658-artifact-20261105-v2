"""Offline CPU probes of six focused saved claims using pinned source fragments.

Synthetic inputs/backend stand-ins isolate local logic. These are not new human
ratings, full project integration tests, SWE-bench harness runs or bug-frequency estimates.
"""
import argparse,ast,collections,contextlib,copy,hashlib,json,math,operator,platform,types,warnings
from pathlib import Path
DEFAULT=Path(__file__).resolve().parents[1]/'rationale_case_audit'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def tree(case,version):
    source=(case/(version+'_source.py')).read_text()
    return source,ast.parse(source)


def named_function(source,name,owner=None):
    t=ast.parse(source)
    scope=next(n for n in ast.walk(t) if isinstance(n,ast.ClassDef) and n.name==owner) if owner else t
    return next(n for n in scope.body if isinstance(n,ast.FunctionDef) and n.name==name)


def compile_function(node,namespace):
    node=copy.deepcopy(node);node.decorator_list=[]
    module=ast.Module(body=[node],type_ignores=[])
    exec(compile(ast.fix_missing_locations(module),'<pinned-source-function>','exec'),namespace)
    return namespace[node.name]


def capture(call):
    try:
        value=call()
        if isinstance(value,float) and math.isnan(value):value='NaN'
        if isinstance(value,tuple):value=list(value)
        return {'outcome':'returned','value':value}
    except Exception as e:return {'outcome':'raised','exception':type(e).__name__,'message':str(e)}


def reference(source,node,version):
    snippet=ast.get_source_segment(source,node)
    return {'version':version,'start_line':node.lineno,'end_line':node.end_lineno,
            'source':snippet,'snippet_sha256':hashlib.sha256(snippet.encode()).hexdigest()}


def probe_order(case):
    expr=(case/'expressions_base.py').read_text();const=(case/'constants_base.py').read_text()
    orderdir=next(n for n in ast.parse(const).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ORDER_DIR' for t in n.targets))
    namespace={};exec(compile(ast.Module(body=[orderdir],type_ignores=[]),'<pinned-constants>','exec'),namespace)
    # Exact upstream initializers; a marker method is supplied only for the constructor's hasattr check.
    init_f=compile_function(named_function(expr,'__init__','F'),{})
    init_o=compile_function(named_function(expr,'__init__','OrderBy'),{})
    F=type('FInput',(),{'__init__':init_f,'resolve_expression':lambda self:None})
    OrderBy=type('OrderByInput',(),{'__init__':init_o})
    desc=OrderBy(F('x'),descending=True)
    non_name=OrderBy(types.SimpleNamespace(resolve_expression=lambda:None),descending=True)
    results={};refs=[]
    for v in ['base','patched']:
        source,_=tree(case,v);node=named_function(source,'get_order_dir')
        fn=compile_function(node,dict(namespace))
        results[v]={'plain_field':capture(lambda:fn('x')),'descending_expression':capture(lambda:fn(desc)),
                    'expression_without_name':capture(lambda:fn(non_name))}
        refs.append(reference(source,node,v))
    supported=(results['patched']['descending_expression']=={'outcome':'returned','value':['x','ASC']}
               and results['patched']['expression_without_name'].get('exception')=='AttributeError')
    return supported,results,refs,(
        'The added coercion ignores descending=True and assumes .expression.name exists.',
        'Extracted get_order_dir and upstream constructors; an expression marker stands in for query resolution. No SQL compiler or database is executed.')


def probe_trim(case):
    results={};refs=[]
    for v in ['base','patched']:
        source,_=tree(case,v);node=named_function(source,'trim_docstring');fn=compile_function(node,{})
        results[v]={name:capture(lambda value=value:fn(value)) for name,value in [
            ('single_line','A summary.'),('trailing_blank','A summary.\n   \n'),
            ('normal_multiline','Summary.\n    Detail.')]}
        refs.append(reference(source,node,v))
    supported=(all(results['base'][x]['outcome']=='returned' and results['patched'][x].get('exception')=='ValueError'
                   for x in ['single_line','trailing_blank']))
    return supported,results,refs,(
        'Skipping the first line without a default makes min() fail for a nonempty single-line or blank-tail docstring.',
        'The entire extracted trim_docstring function runs on synthetic strings with no external bindings.')


def probe_delete(case):
    class Instance:
        def __init__(self,pk):self.id=pk
        @property
        def pk(self):return self.id
    Model=type('SyntheticModel',(),{'_meta':types.SimpleNamespace(pk=types.SimpleNamespace(attname='id'),label='test.Model',auto_created=False)})
    class DeleteQuery:
        def __init__(self,model):pass
        def delete_batch(self,keys,using):return len(keys)
    signal=types.SimpleNamespace(send=lambda **kw:None)
    tx=types.SimpleNamespace(atomic=lambda **kw:contextlib.nullcontext(),
        mark_for_rollback_on_error=lambda **kw:contextlib.nullcontext())
    namespace={'attrgetter':operator.attrgetter,'Counter':collections.Counter,'transaction':tx,
        'sql':types.SimpleNamespace(DeleteQuery=DeleteQuery),'signals':types.SimpleNamespace(pre_delete=signal,post_delete=signal)}
    results={};refs=[]
    for v in ['base','patched']:
        source,_=tree(case,v);node=named_function(source,'delete','Collector');fn=compile_function(node,dict(namespace))
        results[v]={}
        for name,fast,n in [('fast_single',True,1),('regular_two',False,2)]:
            instances=[Instance(i+7) for i in range(n)]
            collector=types.SimpleNamespace(data={Model:instances},sort=lambda:None,can_fast_delete=lambda instance:fast,
                using='synthetic_backend',fast_deletes=[],field_updates={})
            collector.instances_with_model=lambda:[(Model,x) for x in instances]
            call=capture(lambda:fn(collector))
            # Counter return keys are serializable; retain the actual final in-memory identifiers.
            results[v][name]={'call':call,'remaining_ids':[x.id for x in instances]}
        refs.append(reference(source,node,v))
    contradicted=(results['base']['regular_two']['remaining_ids']==[None,None]
        and results['patched']['regular_two']['remaining_ids']==[None,None]
        and results['base']['fast_single']['remaining_ids']==[7]
        and results['patched']['fast_single']['remaining_ids']==[None])
    return contradicted,results,refs,(
        'The saved gold objection says the regular deletion path retains stale PKs; the pinned code already clears them.',
        'The whole extracted Collector.delete method executes with synthetic model objects and no-op transaction/signal/query stand-ins. This is a source-control-flow probe, not a real Django database test.')


def probe_hexbin(case):
    results={};refs=[]
    for v in ['base','patched']:
        source,t=tree(case,v)
        hexbin=named_function(source,'hexbin','Axes')
        node=next(n for n in ast.walk(hexbin) if isinstance(n,ast.IfExp)
            and isinstance(n.body,ast.Call) and isinstance(n.body.func,ast.Name) and n.body.func.id=='reduce_C_function'
            and 'len(acc)' in ast.unparse(n.test))
        default=next(n for n in ast.walk(hexbin) if isinstance(n,ast.If) and ast.unparse(n.test)=='mincnt is None'
                     and any(isinstance(x,ast.Assign) and ast.unparse(x.value)=='0' for x in n.body))
        assert ast.unparse(default.body[0])=='mincnt = 0'
        code=compile(ast.Expression(body=copy.deepcopy(node)),'<pinned-empty-bin-expression>','eval')
        results[v]={name:capture(lambda acc=acc:eval(code,{'acc':acc,'mincnt':0,
            'reduce_C_function':min,'np':types.SimpleNamespace(nan=float('nan'))})) for name,acc in [('empty',[]),('nonempty',[2,3])]}
        refs.append(reference(source,node,v));refs.append(reference(source,default,v))
    supported=(results['base']['empty'].get('value')=='NaN'
        and results['patched']['empty'].get('exception')=='ValueError'
        and results['patched']['nonempty'].get('value')==2)
    return supported,results,refs,(
        'With default mincnt=0, the changed >= branch calls an empty-sensitive reducer on an empty bin.',
        'The exact extracted conditional expression is evaluated with Python min as an allowed empty-sensitive reducer. No matplotlib plot, NumPy implementation, or full hexbin function is run.')


def probe_astropy(case):
    class NdarrayMixin:pass
    class StructuredArray:
        dtype=('field_a','field_b')
        def view(self,kind):return kind()
    class Column:
        def __init__(self,data):self.data=data
    results={};refs=[]
    for v in ['base','patched']:
        source,t=tree(case,v)
        node=next(n for n in ast.walk(t) if isinstance(n,ast.If)
            and 'isinstance(data, Column)' in ast.unparse(n.test)
            and 'len(data.dtype) > 1' in ast.unparse(n.test))
        ns={'data':StructuredArray(),'data_is_mixin':False,'Column':Column,'NdarrayMixin':NdarrayMixin,
            'np':types.SimpleNamespace(ndarray=StructuredArray),'warnings':warnings,'FutureWarning':FutureWarning}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(node)],type_ignores=[])),
                '<pinned-structured-array-branch>','exec'),ns)
        results[v]={'result_type':type(ns['data']).__name__,'data_is_mixin':ns['data_is_mixin'],
            'warnings':[str(w.message) for w in caught]}
        refs.append(reference(source,node,v))
    supported=(results['base']['result_type']=='NdarrayMixin' and results['base']['data_is_mixin'] is True
        and results['patched']['result_type']=='Column' and results['patched']['data_is_mixin'] is False
        and any('future' in s for s in results['patched']['warnings']))
    return supported,results,refs,(
        'The candidate changes the structured-array branch to Column immediately while warning that this happens in the future.',
        'The exact branch runs with minimal stand-ins implementing its type checks and assignments. This verifies local branch behavior, not Astropy serialization or a complete compatibility regression.')


def probe_filterable(case):
    class NotSupportedError(Exception):pass
    results={};refs=[]
    for v in ['base','patched']:
        source,_=tree(case,v);node=named_function(source,'check_filterable','Query')
        fn=compile_function(node,{'NotSupportedError':NotSupportedError})
        receiver=types.SimpleNamespace()
        results[v]={name:capture(lambda obj=obj:fn(receiver,obj)) for name,obj in [
            ('reported_false_field',types.SimpleNamespace(filterable=False)),
            ('true_field',types.SimpleNamespace(filterable=True)),('no_field',types.SimpleNamespace())]}
        refs.append(reference(source,node,v))
    supported=all(results[v]['reported_false_field'].get('exception')=='NotSupportedError' for v in ['base','patched'])
    return supported,results,refs,(
        'Changing getattr to hasattr-and-not still raises for the reported non-expression object with filterable=False.',
        'The extracted entire method runs with a local exception class and synthetic object attributes. No QuerySet or database is run; no global equivalence claim is made for descriptors with side effects.')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cases',type=Path,default=DEFAULT)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    selection=json.loads((args.cases/'SELECTION_FROZEN.json').read_text())
    implementations={'django__django-11555':probe_order,'django__django-12155':probe_trim,
        'django__django-11179':probe_delete,'matplotlib__matplotlib-26113':probe_hexbin,
        'astropy__astropy-13236':probe_astropy,'django__django-13028':probe_filterable}
    rows=[]
    for c in selection['cases']:
        case=args.cases/c['instance_id']
        assert sha(case/'verdict.json')==c['verdict_sha256'] and sha(case/'candidate.diff')==c['candidate_diff_sha256']
        receipt=json.loads((case/'context_receipt.json').read_text())
        assert all(sha(case/x['file'])==x['sha256'] for x in receipt['sources'])
        assert sha(case/'patched_source.py')==receipt['patched_sha256']
        expected,observed,refs,(claim,scope)=implementations[c['instance_id']](case)
        assert expected,(c['instance_id'],observed)
        status='FOCUSED_CLAIM_CONTRADICTED_BY_CONTEXT' if c['instance_id']=='django__django-11179' else 'FOCUSED_CLAIM_SUPPORTED_LOCALLY'
        rows.append({**c,'focused_claim':claim,'status':status,'scope':scope,'observations':observed,'source_references':refs,
            'independent_human_adjudication':False,'full_project_integration_test':False})
    result={'analysis_type':'post_hoc_technical_rationale_case_audit','selection':selection['selection_rule'],
        'selection_sha256':sha(args.cases/'SELECTION_FROZEN.json'),'python_version':platform.python_version(),
        'new_inference_calls':0,'new_harness_runs':0,'new_human_ratings':0,'case_count':len(rows),
        'status_counts':dict(collections.Counter(x['status'] for x in rows)),'cases':rows,
        'interpretation':'Selected focused technical claims only. No adjudicated hallucination rate, reviewer correctness rate, post-merge churn estimate or maintainer validation is established.'}
    (args.output/'RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'case_count':len(rows),'status_counts':result['status_counts'],'new_human_ratings':0,
        'new_harness_runs':0},indent=2))


if __name__=='__main__':main()
