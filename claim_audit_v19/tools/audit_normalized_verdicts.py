"""Recompute stored acceptance without importing historical metric/runner modules."""
from pathlib import Path
from collections import Counter, defaultdict
import ast
import hashlib
import json
import argparse

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent
STUDY = BASE / 'review_swe'
MAIN = {'lite', 'verified', 'verified_negctrl'}


def read(p):
    return json.loads(p.read_text())


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def exact_p(b, c):
    from math import comb
    return min(1., 2 * sum(comb(b+c, k) for k in range(min(b,c)+1)) / 2**(b+c))


def main():
    global STUDY
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--study',type=Path,default=STUDY)
    ap.add_argument('--census',type=Path,default=BASE/'ICSE2027_6658_ReverseAudit_20261109_v18/evidence/rationale_census_v18.json')
    ap.add_argument('--out',type=Path,default=ROOT/'evidence/normalized_verdict_audit_v19.json')
    args=ap.parse_args();STUDY=args.study.resolve()
    groups = defaultdict(Counter)
    observations, inputs, decisions = [], [], {}
    for p in sorted((STUDY/'data/llm_reviews').rglob('*.json')):
        if not p.parent.name.startswith('reviewer-'):
            continue
        rel = p.relative_to(STUDY).as_posix()
        scope = p.relative_to(STUDY/'data/llm_reviews').parts[0]
        r = read(p)
        key = scope+'/'+p.parent.name
        c = groups[key]
        c['files'] += 1
        inputs.append({'path': rel, 'sha256': digest(p)})
        issues = r.get('issues') or []
        blocker = any(i.get('severity') == 'blocking' for i in issues)
        reconstructed = r.get('merge_decision') == 'merge' and not blocker
        if r.get('mergeable') is None:
            c['excluded'] += 1
        else:
            c['valid'] += 1
            c['acceptance_mismatches'] += type(r['mergeable']) is not bool or r['mergeable'] != reconstructed
            c['accepted'] += reconstructed
        c['merge_with_blocker'] += r.get('merge_decision') == 'merge' and blocker
        c['summary_fields'] += 'summary' in r
        c['issue_fields'] += len(issues)
        sc = len(r.get('summary', '')) == 600
        ic = [i for i, v in enumerate(issues) if len(v.get('description','')) == 600]
        c['summaries_at_600'] += sc
        c['issues_at_600'] += len(ic)
        c['verdicts_with_capped_field'] += bool(sc or ic)
        c['fields_over_600'] += len(r.get('summary','')) > 600
        c['fields_over_600'] += sum(len(i.get('description','')) > 600 for i in issues)
        if sc or ic or (r.get('merge_decision') == 'merge' and blocker):
            observations.append({'path':rel, 'summary_at_cap':sc, 'issue_indices_at_cap':ic,
                                 'merge_with_blocker':r.get('merge_decision') == 'merge' and blocker})
        decisions[(scope,p.parent.name,p.stem)] = reconstructed if r.get('mergeable') is not None else None

    metrics = []
    for report in sorted((STUDY/'results/reports').glob('metrics_reviewer-*.json')):
        reviewer = report.stem.removeprefix('metrics_')
        inputs.append({'path':report.relative_to(STUDY).as_posix(),'sha256':digest(report)})
        for split, old in read(report).items():
            kp=STUDY/'data/review_packets'/split/'packets_key.json'
            key=read(kp); inputs.append({'path':kp.relative_to(STUDY).as_posix(),'sha256':digest(kp)})
            sources = {'agent':{}, 'gold':{}}
            for k in key:
                v=decisions.get((split,reviewer,k['packet_id']))
                if v is not None:
                    sources[k['candidate_source']][k['instance_id']]=v
            a,g=sources['agent'],sources['gold']
            common=a.keys() & g.keys()
            b=sum(g[k] and not a[k] for k in common)
            c=sum(a[k] and not g[k] for k in common)
            actual={'n_agent_reviewed':len(a),'n_gold_reviewed':len(g),
                    'merge_agent':sum(a.values()),'merge_gold':sum(g.values()),
                    'RAP':round(100*sum(a.values())/len(a),2),
                    'gold_false_rejection_rate':round(100*(1-sum(g.values())/len(g)),2)}
            checks={k:v==old[k] for k,v in actual.items()}
            checks['paired_discordants']=b==old['mcnemar']['gold_ok_agent_not'] and c==old['mcnemar']['agent_ok_gold_not']
            checks['exact_mcnemar']=abs(exact_p(b,c)-old['mcnemar']['p_value'])<0.000051
            metrics.append({'split':split,'reviewer':reviewer,'recomputed':actual,'checks':checks})

    # Run the preserved function alone to check the length boundary without its API imports.
    runner=STUDY/'scripts/03_run_reviewer.py'
    tree=ast.parse(runner.read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='normalize')
    ns={'TAXONOMY':{f'F{i}':None for i in range(1,12)}}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(runner),'exec'),ns)
    boundary=[]
    for decision in ['merge','request_changes','reject']:
        for severity in ['blocking','major','minor']:
            long={'merge_decision':decision,'summary':'x'*601,'issues':[{'failure_mode':'F1','severity':severity,'description':'y'*601}]}
            short={**long,'summary':'x'*599,'issues':[{**long['issues'][0],'description':'y'*599}]}
            a,b=ns['normalize'](long),ns['normalize'](short)
            boundary.append(len(a['summary'])==600 and len(a['issues'][0]['description'])==600 and a['mergeable']==b['mergeable'])
    totals={}
    for label, selection in [('main',MAIN),('additional',{'agents','human_subset'})]:
        c=Counter()
        for key,v in groups.items():
            if key.split('/')[0] in selection:c.update(v)
        totals[label]=dict(c)
    assert not sum(c['acceptance_mismatches'] for c in groups.values())
    assert all(all(m['checks'].values()) for m in metrics)
    assert all(boundary)
    # The v18 census contains only nonaccepted gold/negative records, not all reviews.
    census=read(args.census)['records']
    cap=Counter()
    for r in census:
        cap['summary_at_cap']+=len(r.get('summary',''))==600
        cap['issue_at_cap']+=sum(len(i.get('description',''))==600 for i in r.get('issues',[]))
    from math import sqrt
    reviewers=['reviewer-'+m+s for m in ['7b','14b','32b','llama8b','dscoder'] for s in ['', '-cal']]
    rates=[]
    key=read(STUDY/'data/review_packets/verified/packets_key.json')
    for reviewer in reviewers:
        sources={'agent':[],'gold':[]}
        for k in key:
            v=decisions.get(('verified',reviewer,k['packet_id']))
            if v is not None:sources[k['candidate_source']].append(v)
        rates.append({s:sum(v)/len(v) for s,v in sources.items()})
    x=[r['agent'] for r in rates];y=[r['gold'] for r in rates]
    mx,my=sum(x)/len(x),sum(y)/len(y)
    pearson=sum((a-mx)*(b-my) for a,b in zip(x,y))/sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
    panel=[m for m in reviewers if m.endswith('-cal')]
    shared=[k['packet_id'] for k in key if all(decisions.get(('verified',m,k['packet_id'])) is not None for m in panel)]
    counts=[sum(decisions[('verified',m,p)] for m in panel) for p in shared]
    n=len(panel);N=len(counts)
    observed=sum((v*(v-1)+(n-v)*(n-v-1))/(n*(n-1)) for v in counts)/N
    accepted=sum(counts)/(N*n);chance=accepted**2+(1-accepted)**2
    fleiss=(observed-chance)/(1-chance)
    hosted={'agent':{},'gold':{}}
    for k in key:
        v=decisions.get(('verified','reviewer-claude-frontier',k['packet_id']))
        if v is not None:hosted[k['candidate_source']][k['instance_id']]=v
    a,g=hosted['agent'],hosted['gold'];common=a.keys()&g.keys()
    b=sum(g[k] and not a[k] for k in common);c=sum(a[k] and not g[k] for k in common)
    statistics={'ten_configuration_pearson_r':pearson,'five_adjusted_fleiss_kappa':fleiss,
                'five_adjusted_common_packets':N,'hosted_agent_accepted':sum(a.values()),
                'hosted_gold_accepted':sum(g.values()),'hosted_paired_tasks':len(common),
                'hosted_discordants':[b,c],'hosted_exact_mcnemar_p':exact_p(b,c)}
    assert round(pearson,3)==.994 and round(fleiss,4)==.0245 and N==383
    assert (sum(a.values()),sum(g.values()),len(common),b,c)==(164,191,194,29,2)
    result={'scope':'All stored primary Lite/Verified/Verified-negative files. Additional scaffold/human-subset files counted separately; overlaps are not independent judgments.',
            'totals':totals,'groups':{k:dict(v) for k,v in groups.items()},
            'at_cap_and_action_override_records':observations,
            'metric_comparisons':metrics,'metric_checks':sum(len(m['checks']) for m in metrics),
            'normalizer_boundary_checks':len(boundary),'normalizer_boundary_checks_pass':all(boundary),
            'v18_nonaccepted_census_at_cap':dict(cap),
            'independently_recomputed_statistics':statistics,
            'limitations':['Exactly 600 characters identifies the storage cap; it does not prove every field was truncated.',
                          'Length truncation preserves stored decision/severity, but cannot recover discarded rationale text.',
                          'This checks implementation and stored numbers, not rationale truth, raw-response parsing fidelity, or maintainer agreement.',
                          'No new inference, human response, functional probe or GPU job.'],
            'runner_sha256':digest(runner),'input_hashes':list({i['path']:i for i in inputs}.values())}
    out=args.out
    with out.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ['totals','metric_checks','normalizer_boundary_checks','v18_nonaccepted_census_at_cap']},indent=2))


if __name__=='__main__':main()
