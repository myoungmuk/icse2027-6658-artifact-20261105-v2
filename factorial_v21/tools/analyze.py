"""Prespecified full-cohort, paired, and task-cluster factorial analyses."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from scipy.stats import binomtest
from prompts import ARMS, parse, accepted

ROOT=Path(__file__).resolve().parents[1]
KINDS=('gold','resolved_agent','unresolved_agent')

def wilson(k,n):
    if n==0:return None
    z=1.959963984540054;p=k/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den;rad=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [mid-rad,mid+rad]

def rate(rows):
    valid=[r for r in rows if r['status']=='ok'];n=len(valid);k=sum(r['accepted'] for r in valid);m=len(rows)-n
    return {'planned':len(rows),'valid':n,'accepted':k,'rate':k/n if n else None,'wilson95':wilson(k,n),'statuses':dict(Counter(r['status'] for r in rows)),'missingness_bounds':[k/len(rows),(k+m)/len(rows)] if rows else None}

def paired(x,y):
    # x-y, binary arrays on the same tasks/candidates.
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float);d=x-y;n=len(d)
    if not n:return {'n':0}
    b=int(sum((x==1)&(y==0)));c=int(sum((x==0)&(y==1)))
    rng=np.random.default_rng(6658)
    bs=np.array([d[rng.integers(n,size=n)].mean() for _ in range(4000)])
    return {'n':n,'x_accepted':int(x.sum()),'y_accepted':int(y.sum()),'x_only':b,'y_only':c,'difference':float(d.mean()),'bootstrap95':np.quantile(bs,[.025,.975]).tolist(),'exact_mcnemar_p':float(binomtest(b,b+c,.5).pvalue) if b+c else 1.0}

def cluster_effect(rows):
    if not rows:return {'complete_candidates':0}
    # rows = (task, four binary values), preserve all candidates within a task.
    accum={}
    for task,v in rows:
        # ARMS:00,10,01,11
        effects=np.array([(v[1]-v[0]+v[3]-v[2])/2,(v[2]-v[0]+v[3]-v[1])/2,v[3]-v[2]-v[1]+v[0]],dtype=float)
        if task not in accum:accum[task]=[np.zeros(3),0]
        accum[task][0]+=effects;accum[task][1]+=1
    sums=np.array([v[0] for v in accum.values()]);counts=np.array([v[1] for v in accum.values()]);n=len(counts)
    rng=np.random.default_rng(6658);bs=[]
    for _ in range(4000):
        ids=rng.integers(n,size=n);bs.append(sums[ids].sum(axis=0)/counts[ids].sum())
    cis=np.quantile(bs,[.025,.975],axis=0);est=sums.sum(axis=0)/counts.sum()
    return {'complete_candidates':len(rows),'task_clusters':n,'effects':{k:{'difference':float(est[i]),'task_cluster_bootstrap95':cis[:,i].tolist()} for i,k in enumerate(['E_average','B_average','E_by_B_interaction'])}}

def main():
    for row in json.loads((ROOT/'FREEZE.json').read_text())['files']:
        assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
    cs=json.loads((ROOT/'inputs/candidates.json').read_text());models={};tests=[];allrows={}
    for model in ['7b','14b']:
        rows=[json.loads(p.read_text()) for p in sorted((ROOT/('run_'+model)/'records').glob('*.json'))]
        assert len(rows)==4812 and len({r['id'] for r in rows})==4812
        for r in rows:
            if r['status']=='input_too_long':assert r['accepted'] is None
            else:
                v,status=parse(r['raw'],r['finish_reason']);assert status==r['status'] and v==r['parsed']
                assert r['accepted']==(accepted(v) if v is not None else None)
        idx={(r['code'],r['arm']):r for r in rows};allrows[model]=idx
        m={'conditions':{},'factorial':{}}
        for arm in ARMS:
            group=[r for r in rows if r['arm']==arm]
            cond={kind:rate([r for r in group if r['kind']==kind]) for kind in KINDS}
            for split in ['lite','verified']:cond['gold_'+split]=rate([r for r in group if r['kind']=='gold' and split in r['splits']])
            for kind,prefix in [('resolved_agent','r_'),('unresolved_agent','a_')]:
                available=[c for c in cs if c['kind']==kind];pairs=[]
                for c in available:
                    a=idx[(c['code'],arm)];g=idx[('g_'+c['instance_id'],arm)]
                    if a['status']==g['status']=='ok':pairs.append((a['accepted'],g['accepted']))
                cond[kind+'_vs_gold']=paired([p[0] for p in pairs],[p[1] for p in pairs]);cond[kind+'_vs_gold']['planned_pairs']=len(available)
            m['conditions'][arm]=cond
        for kind in ['all',*KINDS]:
            candidates=[c for c in cs if kind=='all' or c['kind']==kind];complete=[]
            for c in candidates:
                rr=[idx[(c['code'],a)] for a in ARMS]
                if all(r['status']=='ok' for r in rr):complete.append((c['instance_id'],[int(r['accepted']) for r in rr]))
            m['factorial'][kind]=cluster_effect(complete)
            if kind=='all':continue
            for name,a,b in [('E_at_B0',1,0),('E_at_B1',3,2),('B_at_E0',2,0),('B_at_E1',3,1)]:
                t=paired([v[a] for _,v in complete],[v[b] for _,v in complete]);t.update(model=model,kind=kind,contrast=name);tests.append(t)
        m['finish_reasons']=dict(Counter(r.get('finish_reason','not_generated') for r in rows))
        m['output_tokens']=sum(r.get('output_tokens',0) for r in rows)
        models[model]=m
    assert len(tests)==24
    order=sorted(range(len(tests)),key=lambda i:tests[i]['exact_mcnemar_p']);prev=0
    for rank,i in enumerate(order):
        p=min(1,(len(tests)-rank)*tests[i]['exact_mcnemar_p']);prev=max(prev,p);tests[i]['holm_p_24']=prev
    agreement={}
    for arm in ARMS:
        xy=[(allrows['7b'][(c['code'],arm)],allrows['14b'][(c['code'],arm)]) for c in cs]
        xy=[(int(x['accepted']),int(y['accepted'])) for x,y in xy if x['status']==y['status']=='ok']
        n=len(xy);x=sum(a for a,b in xy)/n;y=sum(b for a,b in xy)/n;po=sum(a==b for a,b in xy)/n;pe=x*y+(1-x)*(1-y)
        agreement[arm]={'common_valid':n,'agreement':po,'cohen_kappa':(po-pe)/(1-pe) if pe<1 else None,'caveat':'Quantization and model size both differ.'}
    result={'planned_records':9624,'models':models,'simple_contrasts_holm_family_24':tests,'cross_model_agreement':agreement,'limitations':['New instrument; not retrospective causal attribution or exact historical replay.','Tasks reused; not unseen-task validation.','Functional labels are inherited proxies, not maintainer truth.','Independent humans/native unavailable APIs/history not completed by GPU inference.']}
    out=ROOT/'reports/analysis.json'
    with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('ANALYSIS_COMPLETE',out)

if __name__=='__main__':main()
