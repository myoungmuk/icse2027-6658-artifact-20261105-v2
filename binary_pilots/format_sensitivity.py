"""Post hoc sensitivity: remove only a whole-response Markdown JSON fence.

Never replaces the frozen primary analysis. No inference, label repair, coercion,
or missing-answer imputation. This diagnostic is motivated by observed format
failures and is explicitly post hoc.
"""
import csv
import json
import re
from collections import Counter
from pathlib import Path
from analyze import wilson
from prompts import parse

ROOT=Path(__file__).resolve().parent
FENCE=re.compile(r'\A```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```[ \t]*\Z')

def main():
    out=ROOT/'format_sensitivity_v1';out.mkdir(exist_ok=False)
    tasks={x['task_code']:x for x in json.loads((ROOT/'tasks.json').read_text())}
    cfg=json.loads((ROOT/'config.json').read_text())
    rows=[]
    for f in sorted((ROOT/'run_v1/raw').glob('*.json')):
        r=json.loads(f.read_text());obj=r.get('parsed') if r['status']=='ok' else None
        recovery='none'
        if obj is None and r.get('finish_reason')=='eos':
            m=FENCE.fullmatch(r.get('raw',''))
            if m:
                obj=parse(m.group(1));recovery='whole_response_json_fence_only' if obj else 'unrecovered'
        if obj is None:recovery='unrecovered'
        t=tasks[r['task_code']]
        rows.append({'task_code':r['task_code'],'instance_id':t['instance_id'],
            'source':r['candidate_code'].rsplit('_',1)[1],'arm':r['arm'],
            'agent_resolved_reference':t['agent_resolved'],
            'primary_status':r['status'],'format_handling':recovery,
            'decision':obj['verdict'] if obj else None,'reason':obj['reason'] if obj else '',
            'raw_file':str(f.relative_to(ROOT))})
    with (out/'verdicts.csv').open('x',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'analysis_type':'post_hoc_format_only_sensitivity',
      'reason':'Frozen strict parser rejected whole-response Markdown JSON fences.',
      'primary_analysis_unchanged':True,'new_model_calls':0,
      'total':len(rows),'format_handling':dict(Counter(r['format_handling']for r in rows)), 'arms':{}}
    for arm in cfg['arms']:
        rr=[r for r in rows if r['arm']==arm];a=[r for r in rr if r['source']=='agent'];g=[r for r in rr if r['source']=='gold']
        tp=sum(r['decision']=='ACCEPT'and r['agent_resolved_reference']for r in a)
        tn=sum(r['decision']=='REJECT'and not r['agent_resolved_reference']for r in a)
        fp=sum(r['decision']=='ACCEPT'and not r['agent_resolved_reference']for r in a)
        fn=sum(r['decision']=='REJECT'and r['agent_resolved_reference']for r in a)
        va=sum(r['decision']is not None for r in a);vg=sum(r['decision']is not None for r in g)
        summary['arms'][arm]={'agent_planned':len(a),'agent_valid':va,'agent_failures':len(a)-va,
          'tp':tp,'tn':tn,'fp':fp,'fn':fn,'agent_correct':tp+tn,
          'agent_accuracy':(tp+tn)/va if va else None,'agent_accuracy_wilson95':wilson(tp+tn,va),
          'sensitivity':tp/(tp+fn)if tp+fn else None,'specificity':tn/(tn+fp)if tn+fp else None,
          'gold_planned':len(g),'gold_valid':vg,'gold_accepted':sum(r['decision']=='ACCEPT'for r in g),
          'primary_format_failures':sum(r['primary_status']!='ok'for r in rr),
          'format_recovered':sum(r['format_handling']=='whole_response_json_fence_only'for r in rr),
          'remaining_failures':sum(r['decision']is None for r in rr)}
    assert len(rows)==120
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
