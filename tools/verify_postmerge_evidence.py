#!/usr/bin/env python3
"""Verify archived public history receipts and the explicitly linked regression.

No network calls and no inference that churn equals a defect count.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]/'postmerge_history'
def main():
 issues=[];count=0
 for line in (ROOT/'requests.jsonl').read_text().splitlines():
  rec=json.loads(line);p=ROOT/rec['path'];count+=1
  if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=rec['sha256']:issues.append(rec['path'])
 h=json.loads((ROOT/'HISTORY_SUMMARY.json').read_text());recounts=[]
 for case in h['cases']:
  path=ROOT/case['instance_id'];observed=set()
  for page in path.glob('path_*_page_*.json'):observed.update(x['sha'] for x in json.loads(page.read_text()))
  assert len(observed)==case['distinct_path_commits']
  additions=deletions=0
  for sha in observed:
   c=json.loads((path/('commit_'+sha+'.json')).read_text())
   for f in c['files']:
    if f['filename'] in case['source_paths']:additions+=f['additions'];deletions+=f['deletions']
  assert additions==case['files_additions'] and deletions==case['files_deletions']
  recounts.append({'case':case['instance_id'],'path_commits':len(observed),'additions':additions,'deletions':deletions})
 f=ROOT/'matplotlib__matplotlib-26113';bug=json.loads((f/'linked_bug_27103.json').read_text());prcommits=json.loads((f/'original_pr_commits.json').read_text());links=[c['sha'] for c in prcommits if c['sha'] in bug['body']];assert len(links)==1
 fix=json.loads((f/'commit_1344a9018f243281d09c29fdb788c9a966dc4714.json').read_text());axes=next(x for x in fix['files'] if x['filename']=='lib/matplotlib/axes/_axes.py');assert '-                mincnt = 0' in axes['patch'] and '+                mincnt = 1' in axes['patch']
 print(json.dumps({'receipt_files_checked':count,'all_receipt_hashes_match':not issues,'issues':issues,'churn_recount':recounts,'original_PR_source_commit_explicitly_named_by_later_bug':links[0],'new_network_or_model_calls':0,'churn_is_not_defect_count':True},indent=2));return 1 if issues else 0
if __name__=='__main__':sys.exit(main())
