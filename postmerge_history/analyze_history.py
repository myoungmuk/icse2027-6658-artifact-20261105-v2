"""Scoped descriptive source-history analysis; no churn-as-defect inference."""
from pathlib import Path
import json,hashlib,importlib.util,re
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('history_fetch',ROOT/'fetch_history.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
h=json.loads((ROOT/'HISTORY_SUMMARY.json').read_text());receipts=[]
# Stronger evidence is explicitly linked upstream bug report, fix PR, test and release note.
case=ROOT/'matplotlib__matplotlib-26113'
for endpoint,name in [('repos/matplotlib/matplotlib/issues/27103','linked_bug_27103.json'),('repos/matplotlib/matplotlib/pulls/27179','linked_fix_pr_27179.json')]:
 d=f.fetch(endpoint,case/name);receipts.append({'url':d['html_url'],'title':d['title'],'body':d.get('body'),'created_at':d['created_at'],'closed_at':d.get('closed_at'),'merged_at':d.get('merged_at')})
fix=json.loads(next(case.glob('commit_1344a9018f24*.json')).read_text());axes=next(x for x in fix['files'] if x['filename']=='lib/matplotlib/axes/_axes.py')
assert '-                mincnt = 0' in axes['patch'] and '+                mincnt = 1' in axes['patch']
notes=next(x for x in fix['files'] if x['filename'].endswith('27179-KS.rst'))['patch'];assert 'errors or warnings' in notes
bug=receipts[0];assert '27103' in bug['url']
results=[]
for c in h['cases']:
 target=c['instance_id'];dates=[x['date'] for x in c['commits']]
 # API list pages saved to completion; commit files use default max300, check no candidate truncation.
 complete=all(len(json.loads((ROOT/target/('commit_'+x['sha']+'.json')).read_text()).get('files',[]))<300 for x in c['commits'])
 assert complete
 assert all(fx['patch_present'] for x in c['commits'] for fx in x['files']),target
 row={k:c[k] for k in ['instance_id','original_pr_url','merge_sha','merged_at','window_end','window_days','end_commit_sha','source_paths','distinct_path_commits','files_additions','files_deletions','path_history_coverage']}
 row.update(all_commit_file_responses_below300=True,all_relevant_patches_present=True,default_branch_file_churn_includes_merge_commits=True,rename_following=False)
 if target.startswith('matplotlib'):
  row.update(targeted_observation='Direct subsequent upstream regression evidence aligns with the empty-reduction concern: fix1344a901 changes default mincnt0 to1, adds np.max(empty) regression test linked to issue27103, and release note explicitly reports errors/warnings after3.8.0 inclusivity change.',targeted_fix_url=fix['html_url'],targeted_fix_sha=fix['sha'],evidence_class='UPSTREAM_DOCUMENTED_MATCHING_REGRESSION',linked_records=receipts,causal_caution='Matched code/test/release-note evidence; no independent defect attribution study. This public2023 fix predates the2026 judging and may have been recognizable.')
 elif target.startswith('django'):
  row.update(targeted_observation='File changes include cascade-deletion fixes/features, but inspected commit messages/diffs do not document the claimed regular-path PK-cleanup omission. Pinned-source probe already contradicts that claim. Absence in this scoped history is not absence of bugs.',evidence_class='NO_MATCHING_PK_REGRESSION_IDENTIFIED_IN_SCOPED_REVIEW')
 else:
  row.update(targeted_observation='File changes include multi_class API/default updates and other fixes. The saved rationale itself calls dropping fit_intercept functionally harmless in the then-current scoring path; no inspected history explicitly documents a regression caused by that omission.',evidence_class='NO_MATCHING_OMISSION_REGRESSION_IDENTIFIED_IN_SCOPED_REVIEW')
 results.append(row)
rec={'analysis_type':'post_hoc365day_scoped_default_branch_file_history','case_selection':'All3nonaccepted hosted gold cases, exhaustive within that subgroup only.','cases':results,'limits':['File additions/deletions count merge-diff churn and may double-count changes across merge commits.','File-level churn is not defect count or causal attribution.','No rename-following; other branches, indirect effects and unreported bugs can be missed.','No population error-rate or future-outcome prediction claim.','Subsequent history was publicly available before the archived2026model judgments.'],'new_model_calls':0,'new_harness_runs':0,'new_human_ratings':0}
f.dump(ROOT/'ANALYSIS.json',rec)
for r in results:print(r['instance_id'],r['distinct_path_commits'],r['files_additions'],r['files_deletions'],r['evidence_class'])
