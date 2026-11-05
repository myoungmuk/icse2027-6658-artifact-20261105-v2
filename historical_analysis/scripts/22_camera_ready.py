"""Recreate camera-ready tables and figures from archived verdicts, without inference.

Run from any directory: python scripts/22_camera_ready.py
Outputs are isolated under results/camera_ready; historical files are unchanged.
"""
from pathlib import Path
from collections import Counter
import ast
import csv
import hashlib
import json
import math
import random
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/camera_ready'
MODELS = [('Qwen-7B', 'reviewer-7b'), ('Qwen-14B', 'reviewer-14b'),
          ('Qwen-32B', 'reviewer-32b'), ('Llama-8B', 'reviewer-llama8b'),
          ('DeepSeek-6.7B', 'reviewer-dscoder')]
CHECKS = []


def read(path):
    return json.loads(path.read_text())


def check(name, actual, expected):
    CHECKS.append({'name': name, 'actual': actual, 'expected': expected, 'pass': actual == expected})


def verdicts(split, reviewer):
    return {p.stem: read(p) for p in sorted((ROOT / 'data/llm_reviews' / split / reviewer).glob('*.json'))}


def key(split):
    return {x['packet_id']: x for x in read(ROOT / 'data/review_packets' / split / 'packets_key.json')}


def instances(split, reviewer, source):
    k = key(split)
    return {k[p]['instance_id']: v for p, v in verdicts(split, reviewer).items()
            if p in k and k[p]['candidate_source'] == source and v.get('mergeable') is not None}


def count(v):
    return sum(bool(x['mergeable']) for x in v.values())


def pct(n, d):
    return 100 * n / d


def paired(a, g):
    shared = set(a) & set(g)
    b = sum(g[i]['mergeable'] and not a[i]['mergeable'] for i in shared)
    c = sum(a[i]['mergeable'] and not g[i]['mergeable'] for i in shared)
    n = b + c
    p = min(1., 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2**n)
    return {'n': len(shared), 'gold_only': b, 'agent_only': c, 'p': p}


def stats(a, g):
    return {'agent_n': len(a), 'gold_n': len(g), 'agent_accepted': count(a), 'gold_accepted': count(g),
            'agent_pct': pct(count(a), len(a)), 'gold_pct': pct(count(g), len(g)),
            'gold_rejection_pct': pct(len(g) - count(g), len(g)),
            'gold_blocking_n': sum(any(i.get('severity') == 'blocking' for i in v['issues']) for v in g.values()),
            'paired': paired(a, g)}


def ptex(p):
    return r'$<0.001$' if p < .001 else f'{p:.4f}'


def table(name, columns, header, rows):
    lines = [r'\begin{tabular}{' + columns + '}', r'\toprule', header + r' \\', r'\midrule']
    lines += [' & '.join(str(x) for x in row) + r' \\' for row in rows]
    lines += [r'\bottomrule', r'\end{tabular}']
    (OUT / 'tables' / (name + '.tex')).write_text('\n'.join(lines) + '\n')


def fleiss(vs, pids):
    n = len(vs)
    counts = [sum(bool(v[p]['mergeable']) for v in vs) for p in pids]
    marginal = sum(counts) / (len(counts) * n)
    expected = marginal**2 + (1-marginal)**2
    observed = sum((x*(x-1)+(n-x)*(n-x-1))/(n*(n-1)) for x in counts)/len(counts)
    return (observed-expected)/(1-expected)


def cohen(a, b):
    shared = sorted(set(a) & set(b))
    observed = sum(a[i] == b[i] for i in shared) / len(shared)
    pa = sum(a[i] for i in shared) / len(shared)
    pb = sum(b[i] for i in shared) / len(shared)
    expected = pa*pb + (1-pa)*(1-pb)
    return (observed-expected)/(1-expected)


def supplementary_claims(metrics, frontier):
    """Check numeric prose, pilot, fixed-subset analysis and prompt provenance."""
    points = [metrics[b+s]['verified'] for _,b in MODELS for s in ['', '-cal']]
    x, y = [p['gold_pct'] for p in points], [p['agent_pct'] for p in points]
    xm, ym = statistics.mean(x), statistics.mean(y)
    r = sum((a-xm)*(b-ym) for a,b in zip(x,y)) / math.sqrt(
        sum((a-xm)**2 for a in x)*sum((b-ym)**2 for b in y))
    gap = statistics.mean(abs(a-b) for a,b in zip(x,y))
    check('aggregate/correlation', round(r,3), .994)
    check('aggregate/mean_absolute_gap', round(gap,1), 3.5)
    s = metrics['reviewer-14b-cal']['lite']
    p, n, z = s['agent_accepted']/s['agent_n'], s['agent_n'], 1.96
    center = p + z*z/(2*n)
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    wilson = [round(100*v/(1+z*z/n),2) for v in [center-half,center+half]]
    check('headline/Lite Wilson interval', wilson, [61.08,78.98])
    check('headline/Verified discordant pairs',
          sum(metrics['reviewer-14b-cal']['verified']['paired'][k]
              for k in ['gold_only','agent_only']),35)

    hk = {x['packet_id']:x for x in read(ROOT/'data/human_study/key.json')}
    human = {}
    with (ROOT/'data/human_study/responses_rater1.csv').open(newline='') as f:
        for row in csv.DictReader(f):
            human[row['packet_id']] = (row['decision']=='merge' and row['blocking'] in ['no',''])
    aa, gg = [{hk[p]['instance_id']:{'mergeable':v} for p,v in human.items()
               if hk[p]['candidate_source']==source} for source in ['agent','gold']]
    human_stats = {'agent_n':len(aa),'gold_n':len(gg),'agent_accepted':count(aa),
                   'gold_accepted':count(gg),'paired':paired(aa,gg),'kappas':{}}
    check('pilot/counts',[len(aa),len(gg),count(aa),count(gg)],[20,20,15,13])
    old_human = read(ROOT/'results/reports/human_study.json')
    check('pilot/paired p',round(human_stats['paired']['p'],4),old_human['raters']['rater1']['mcnemar_p'])
    fr = {p:bool(v['mergeable']) for p,v in verdicts('verified','reviewer-claude-frontier').items()
          if v.get('mergeable') is not None}
    for _,base in MODELS:
        reviewer = base+'-cal'
        vs = {p:bool(v['mergeable']) for p,v in verdicts('verified',reviewer).items()
              if v.get('mergeable') is not None}
        human_stats['kappas'][reviewer] = cohen(human,vs)
        check('pilot/kappa/'+reviewer,round(cohen(human,vs),3),old_human['human_vs_llm_cohen'][reviewer])
        check('frontier/kappa/'+reviewer,round(cohen(fr,vs),3),
              read(ROOT/'results/reports/frontier_full.json')['kappa_vs_open'][reviewer])
    human_stats['kappas']['reviewer-claude-frontier'] = cohen(human,fr)
    check('pilot/kappa/hosted',round(cohen(human,fr),3),.167)

    a = instances('verified','reviewer-claude-frontier','agent')
    g = instances('verified','reviewer-claude-frontier','gold')
    diffs = [int(g[i]['mergeable'])-int(a[i]['mergeable']) for i in sorted(set(a)&set(g))]
    rng = random.Random(20260701)
    bootstrap = sorted(100*sum(diffs[rng.randrange(len(diffs))] for _ in diffs)/len(diffs)
                       for _ in range(10000))
    frontier['paired_gap_pct'] = 100*statistics.mean(diffs)
    frontier['bootstrap_ci_pct'] = [bootstrap[249],bootstrap[9749]]
    frontier['bootstrap'] = {'seed':20260701,'replicates':10000,'sorted_indices':[249,9749]}
    check('frontier/paired gap',round(frontier['paired_gap_pct'],1),13.9)
    check('frontier/bootstrap',list(map(lambda x:round(x,1),frontier['bootstrap_ci_pct'])),[8.8,19.6])

    subsets = {}
    saved = read(ROOT/'results/reports/robustness.json')['calibration_cv']
    for reviewer, old in saved.items():
        a, g = instances('verified',reviewer,'agent'), instances('verified',reviewer,'gold')
        ids = sorted(set(a)|set(g))
        groups = []
        for k in range(5):
            group = set(ids[k::5])
            group_g = {i:v for i,v in g.items() if i in group}
            groups.append(round(100*(1-count(group_g)/len(group_g)),1))
        record = {'gold_rejection_by_subset_pct':groups,
                  'mean':round(statistics.mean(groups),1),'population_sd':round(statistics.pstdev(groups),1)}
        check('subset/'+reviewer,[record['mean'],record['population_sd']],
              [old['false_rej_mean'],old['false_rej_sd']])
        subsets[reviewer] = record

    tree = ast.parse((ROOT/'scripts/03_run_reviewer.py').read_text())
    prompt_md = (ROOT/'PROMPTS.md').read_text()
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in
                ['SYSTEM','SYSTEM_CAL','PROMPT','TASK_CAL'] for t in node.targets):
            check('prompt/verbatim/'+node.targets[0].id,ast.literal_eval(node.value).strip() in prompt_md,True)
    for iid, keyword in [('django__django-10914','test'),('django__django-13964','empty_values')]:
        v = instances('lite','reviewer-32b','gold')[iid]
        check('qualitative/'+iid,keyword in json.dumps(v).lower(),True)
    return {'aggregate':{'pearson_r':r,'mean_absolute_gap_pct':gap},
            'headline_wilson_pct':wilson,'human':human_stats,'fixed_subsets':subsets}


def main():
    for sub in ['tables', 'figures']:
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    metrics, main_rows, quality_rows, family_rows = {}, [], [], []
    inventory = []
    for label, base in MODELS:
        for suffix in ['', '-cal']:
            reviewer = base + suffix
            metrics[reviewer] = {}
            saved = read(ROOT / 'results/reports' / f'metrics_{reviewer}.json')
            for split in saved:
                a, g = instances(split, reviewer, 'agent'), instances(split, reviewer, 'gold')
                s = stats(a, g)
                metrics[reviewer][split] = s
                old = saved[split]
                for field, val in [('n_agent_reviewed',len(a)),('n_gold_reviewed',len(g)),
                                   ('merge_agent',count(a)),('merge_gold',count(g)),
                                   ('RAP',round(s['agent_pct'],2)),
                                   ('gold_false_rejection_rate',round(s['gold_rejection_pct'],2)),
                                   ('hallucinated_review_rate',round(pct(s['gold_blocking_n'],len(g)),2))]:
                    check(f'{reviewer}/{split}/{field}', val, old[field])
                check(f'{reviewer}/{split}/mcnemar',
                      round(s['paired']['p'],5),old['mcnemar']['p_value'])
                if base.startswith('reviewer-') and label.startswith('Qwen'):
                    main_rows.append([label, 'Adjusted' if suffix else 'Naive', split.capitalize(),
                                      len(a),f"{s['agent_pct']:.2f}",f"{s['gold_pct']:.2f}",
                                      f"{s['gold_rejection_pct']:.2f}",ptex(s['paired']['p'])])
                    if suffix:
                        quality_rows.append([label,split.capitalize(),len(g),f"{s['gold_pct']:.2f}",
                                             f"{pct(s['gold_blocking_n'],len(g)):.2f}",f"{s['gold_rejection_pct']:.2f}"])
        c, n = metrics[base+'-cal']['verified'], metrics[base]['verified']
        family_rows.append([label, f"{n['gold_rejection_pct']:.2f}",f"{c['gold_rejection_pct']:.2f}",
                            f"{c['agent_pct']:.2f}",f"{c['gold_pct']:.2f}",
                            f"{c['agent_n']}/{c['gold_n']}/{c['paired']['n']}",ptex(c['paired']['p'])])
    table('main_table','lllrrrrr',r'Reviewer & Prompt & Split & $n$ & RAP\% & Gold acc.\% & Gold rej.\% & Paired $p$',main_rows)
    table('quality_table','llrrrr',r'Reviewer & Split & $n_g$ & Gold acc.\% & Gold blocking\% & Gold rej.\%',quality_rows)
    table('family_table','lrrrrcr',r'Reviewer & Naive gold rej.\% & Adj. gold rej.\% & Adj. RAP\% & Adj. gold acc.\% & $n_a/n_g/n_p$ & Paired $p$',family_rows)

    agents = {}
    rows = []
    saved_agents = read(ROOT/'results/reports/agent_metrics.json')
    for agent, label, nominal in [('rag-gpt4','RAG+GPT-4',14),('sweagent-claude35','SWE-agent+Claude-3.5',168),
                                  ('agentless','Agentless+GPT-4o',194),('openhands-codeact','OpenHands-CodeAct',265)]:
        agents[agent] = {}
        for _, base in MODELS[:3]:
            reviewer=base+'-cal'
            if agent=='agentless':
                a,g=instances('verified',reviewer,'agent'),instances('verified',reviewer,'gold')
            else:
                a,g=instances('agents/'+agent,reviewer,'agent'),instances('agents/_gold',reviewer,'gold')
            g={i:g[i] for i in set(a)&set(g)}
            s=stats(a,g)
            agents[agent][reviewer]=s
            old=saved_agents[agent]['per_reviewer'][reviewer]
            for field,val in [('n',len(a)),('RAP',round(s['agent_pct'],1)),('gold_rate',round(s['gold_pct'],1)),('mcnemar_p',round(s['paired']['p'],4))]:
                check(f'agents/{agent}/{reviewer}/{field}',val,old[field])
        ss=list(agents[agent].values())
        rows.append([label,nominal,f'{nominal/5:.1f}']+[f"{s['agent_pct']:.1f}" for s in ss]+[ptex(s['paired']['p']) for s in ss])
    table('agents_table','lrrrrrrrr',r'Coding agent & $n$ & \%Resolved & RAP$_7$ & RAP$_{14}$ & RAP$_{32}$ & $p_7$ & $p_{14}$ & $p_{32}$',rows)

    frontier=stats(instances('verified','reviewer-claude-frontier','agent'),instances('verified','reviewer-claude-frontier','gold'))
    check('frontier/agent',frontier['agent_accepted'],164)
    check('frontier/gold',frontier['gold_accepted'],191)
    check('frontier/discordant', [frontier['paired']['gold_only'],frontier['paired']['agent_only']],[29,2])
    negative, rows = {}, []
    for label,reviewer in [(l,b+'-cal') for l,b in MODELS]+[('Claude CLI','reviewer-claude-frontier')]:
        vs={p:v for p,v in verdicts('verified_negctrl',reviewer).items() if v.get('mergeable') is not None}
        g=instances('verified',reviewer,'gold')
        negative[reviewer]={'accepted':count(vs),'n':len(vs),'pct':pct(count(vs),len(vs))}
        rows.append([label,f'{count(g)}/{len(g)}',f'{pct(count(g),len(g)):.1f}',f'{count(vs)}/{len(vs)}',f'{pct(count(vs),len(vs)):.1f}'])
        old=read(ROOT/'results/reports/negctrl.json')[reviewer]['accept_agent_FAILING']
        check('negative/'+reviewer,[len(vs),round(pct(count(vs),len(vs)),1)],[old['n'],old['accept_pct']])
    table('negative_table','lrrrr',r'Reviewer & Gold $k/n$ & Gold\% & Failing $k/n$ & Failing\%',rows)
    order=[json.loads(s)['packet_id'] for s in (ROOT/'data/review_packets/verified_negctrl/packets.jsonl').read_text().splitlines() if s.strip()]
    fv=verdicts('verified_negctrl','reviewer-claude-frontier')
    positions=[i+1 for i,p in enumerate(order) if p in fv]
    check('negative/frontier positions',positions,list(range(1,80))+[81,82])
    overlap=set(x['instance_id'] for x in key('verified').values()) & set(x['instance_id'] for x in key('verified_negctrl').values())
    check('negative/positive task overlap',len(overlap),0)

    rows=[]
    for _,base in MODELS[:3]:
        for split in ['lite','verified']:
            vs=instances(split,base+'-cal','agent')
            d=Counter(v['merge_decision'] for v in vs.values())
            for source in ['agent','gold']:
                vv=instances(split,base+'-cal',source)
                d=Counter(v['merge_decision'] for v in vv.values())
                rows.append([base.replace('reviewer-','Qwen-').upper().replace('QWEN','Qwen'),source,split.capitalize()]+[f'{pct(d[x],len(vv)):.1f}' for x in ['merge','request_changes','reject']])
    # Stored schema uses request_changes (checked against source categories below).
    all_categories={v['merge_decision'] for split in ['lite','verified'] for v in instances(split,'reviewer-14b-cal','agent').values()}
    check('decision/schema',sorted(all_categories),['merge','reject','request_changes'])
    table('decisions_table','lllrrr',r'Reviewer & Source & Split & Merge\% & Changes\% & Reject\%',rows)
    names={'F1':'Functional incompleteness','F2':'Regression risk','F3':'Test overfitting','F4':'Non-minimal change','F5':'Maintainability','F6':'Convention mismatch','F7':'Insufficient tests','F8':'Fragile approach','F9':'API/compatibility','F10':'Performance','F11':'Documentation'}
    tax={}
    for split in ['lite','verified']:
        c=Counter()
        for v in instances(split,'reviewer-14b-cal','agent').values():
            if not v['mergeable']:c.update({i['failure_mode'] for i in v['issues'] if i.get('failure_mode') in names})
        tax[split]=c
    table('taxonomy_table','llrr',r'Code & Cited concern & Lite & Verified',[[f,names[f],tax['lite'][f],tax['verified'][f]] for f in names if tax['lite'][f] or tax['verified'][f]])
    agreement=[]
    for split,models,label in [('lite',MODELS[:3],'Qwen / Lite'),('verified',MODELS[:3],'Qwen / Verified'),('verified',MODELS,'Five / Verified')]:
        vs=[{p:v for p,v in verdicts(split,b+'-cal').items() if v.get('mergeable') is not None} for _,b in models]
        common=set.intersection(*[set(v) for v in vs]);k=key(split)
        rec={'label':label,'n_common':len(common)}
        for src in ['all','agent','gold']:
            pids=sorted(p for p in common if src=='all' or k[p]['candidate_source']==src)
            rec[src]=fleiss(vs,pids)
        agreement.append(rec)
    for record, expected in zip(agreement,[.1008,.1172,.0245]):
        check('agreement/'+record['label'],round(record['all'],4),expected)
    table('agreement_table','lrrrr',r'Panel / Split & $n$ packets & $\kappa_{all}$ & $\kappa_a$ & $\kappa_g$',[[r['label'],r['n_common']]+[f'{r[x]:.4f}' for x in ['all','agent','gold']] for r in agreement])
    supplementary = supplementary_claims(metrics,frontier)
    normalization_mismatches = []
    for path in sorted((ROOT/'data/llm_reviews').rglob('*.json')):
        v=read(path)
        if v.get('mergeable') is not None:
            expected = v['merge_decision']=='merge' and not any(i.get('severity')=='blocking' for i in v['issues'])
            if v['mergeable'] != expected:
                normalization_mismatches.append(path.relative_to(ROOT).as_posix())
        inventory.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'valid':v.get('mergeable') is not None,'attempt':v.get('_attempt','unrecorded')})
    check('all saved verdicts/normalization',normalization_mismatches,[])
    with (OUT/'verdict_inventory.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(inventory[0]));w.writeheader();w.writerows(inventory)
    result={'main':metrics,'agents':agents,'frontier':frontier,'negative':negative,'negative_frontier_positions':positions,'agreement':agreement,'supplementary':supplementary,'checks':CHECKS,'verdict_files':len(inventory)}
    (OUT/'metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    failures=[x for x in CHECKS if not x['pass']]
    print(json.dumps({'checks':len(CHECKS),'failed':failures,'frontier':frontier,'artifact_verdict_files':len(inventory)},indent=2))
    if failures:raise SystemExit('Evidence mismatch; manuscript generation stopped.')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'pdf.fonttype':42})
    fig,ax=plt.subplots(figsize=(4.6,2.8))
    for offset,suffix,label,color in [(-.19,'','Naive','#b44536'),(.19,'-cal','Rubric-adjusted','#2674a5')]:
        ax.bar([i+offset for i in range(3)],[metrics[b+suffix]['lite']['gold_rejection_pct'] for _,b in MODELS[:3]],.38,label=label,color=color)
    ax.set(xticks=range(3),xticklabels=['Qwen-7B','Qwen-14B','Qwen-32B'],ylabel='Gold rejection (%)',ylim=(0,105))
    pdf_metadata = {'CreationDate':None,'ModDate':None}
    ax.legend(fontsize=8);fig.tight_layout();fig.savefig(OUT/'figures/false_rejection.pdf',metadata=pdf_metadata);plt.close(fig)
    fig,ax=plt.subplots(figsize=(4.6,3.2));colors=['#4477aa','#228833','#aa3377','#ccbb44','#66ccee']
    for (label,b),color in zip(MODELS,colors):
        vals=[metrics[b+s]['verified'] for s in ['','-cal']]
        ax.plot([x['gold_pct'] for x in vals],[x['agent_pct'] for x in vals],color=color,alpha=.5,linewidth=.8)
        ax.scatter([vals[0]['gold_pct']],[vals[0]['agent_pct']],color=color,marker='o',s=26)
        ax.scatter([vals[1]['gold_pct']],[vals[1]['agent_pct']],color=color,marker='s',s=29,label=label)
    ax.plot([0,100],[0,100],'--',color='0.65',linewidth=.8)
    ax.scatter([frontier['gold_pct']],[frontier['agent_pct']],marker='*',s=110,c='black',label='Claude CLI (ID unrecorded)')
    ax.set(xlabel='Gold acceptance (%)',ylabel='Agent acceptance (%)',xlim=(-3,104),ylim=(-3,104))
    ax.legend(fontsize=6.8,loc='upper left',framealpha=.9);fig.tight_layout();fig.savefig(OUT/'figures/dilemma_frontier.pdf',metadata=pdf_metadata);plt.close(fig)
    fig,ax=plt.subplots(figsize=(4.6,2.7))
    for offset,key_,label,color in [(-.19,'agent_pct','Agent','#2674a5'),(.19,'gold_pct','Gold','#ba8b2a')]:
        ax.bar([i+offset for i in range(3)],[metrics[b+'-cal']['lite'][key_] for _,b in MODELS[:3]],.38,label=label,color=color)
    ax.set(xticks=range(3),xticklabels=['Qwen-7B','Qwen-14B','Qwen-32B'],ylabel='Acceptance (%)',ylim=(0,105))
    ax.legend(fontsize=8);fig.tight_layout();fig.savefig(OUT/'figures/agent_vs_gold.pdf',metadata=pdf_metadata);plt.close(fig)


if __name__=='__main__':
    main()
