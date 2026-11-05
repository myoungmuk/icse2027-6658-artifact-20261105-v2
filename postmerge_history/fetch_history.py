"""Read-only public GitHub queries via connected official CLI; no messages."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import json,subprocess,hashlib,os,urllib.parse,re
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[1]
HIST=BASE/'ICSE2027_6658_GitHubRelease_20261105_v7/repository/historical_analysis'
GH=BASE/'tools/github_icse_20261105/bin/gh'
ENV={**os.environ,'GH_CONFIG_DIR':str(BASE/'.config/icse6658-github')}
def dump(p,x):
 with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def fetch(endpoint,dest):
 if dest.exists():return json.loads(dest.read_text())
 result=subprocess.run([str(GH),'api',endpoint],env=ENV,capture_output=True,text=True,timeout=90)
 if result.returncode:raise RuntimeError(result.stderr[:500])
 data=json.loads(result.stdout);dump(dest,data)
 with (ROOT/'requests.jsonl').open('a') as f:f.write(json.dumps({'url':'https://api.github.com/'+endpoint,'fetched_at':datetime.now(timezone.utc).isoformat(),'path':str(dest.relative_to(ROOT)),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})+'\n')
 return data

def main():
 packets={p['packet_id']:p for p in map(json.loads,(HIST/'data/review_packets/verified/packets.jsonl').read_text().splitlines())}
 selected=[]
 for k in json.loads((HIST/'data/review_packets/verified/packets_key.json').read_text()):
  vpath=HIST/'data/llm_reviews/verified/reviewer-claude-frontier'/(k['packet_id']+'.json')
  if k['candidate_source']=='gold' and vpath.exists():
   v=json.loads(vpath.read_text())
   if not v['mergeable']:selected.append((k,packets[k['packet_id']],v))
 assert len(selected)==3
 results=[]
 for k,p,v in sorted(selected,key=lambda x:x[0]['instance_id']):
  folder=ROOT/k['instance_id'];folder.mkdir(exist_ok=True)
  dump(folder/'packet.json',p);dump(folder/'verdict.json',v)
  number=k['instance_id'].rsplit('-',1)[1];repo=p['repo']
  pr=fetch(f'repos/{repo}/pulls/{number}',folder/'original_pr.json');assert pr['merged_at'] and pr['merge_commit_sha']
  merged=datetime.fromisoformat(pr['merged_at'].replace('Z','+00:00'));end=merged+timedelta(days=365)
  repoinfo=fetch(f'repos/{repo}',folder/'repo.json');branch=repoinfo['default_branch']
  endpoint=f'repos/{repo}/commits?'+urllib.parse.urlencode({'sha':branch,'until':end.isoformat(),'per_page':1})
  ends=fetch(endpoint,folder/'window_end_commits.json');assert ends
  endsha=ends[0]['sha'];paths=p['changed_files'];allcommits={};pathpages={}
  for index,path in enumerate(paths):
   commits=[];page=1
   while True:
    endpoint=f'repos/{repo}/commits?'+urllib.parse.urlencode({'sha':endsha,'path':path,'since':(merged+timedelta(seconds=1)).isoformat(),'until':end.isoformat(),'per_page':100,'page':page})
    chunk=fetch(endpoint,folder/f'path_{index:02}_page_{page:03}.json');assert isinstance(chunk,list)
    commits+=chunk
    if len(chunk)<100:break
    page+=1
   pathpages[path]={'commits':len(commits),'pages':page}
   for c in commits:allcommits[c['sha']]=c
  details=[]
  for sha,c in sorted(allcommits.items(),key=lambda x:x[1]['commit']['committer']['date']):
   detail=fetch(f'repos/{repo}/commits/{sha}',folder/('commit_'+sha+'.json'))
   relevant=[f for f in detail.get('files',[]) if f['filename'] in paths]
   details.append({'sha':sha,'date':c['commit']['committer']['date'],'message':c['commit']['message'],'html_url':c['html_url'],'files':[{'filename':f['filename'],'additions':f['additions'],'deletions':f['deletions'],'changes':f['changes'],'patch_present':'patch' in f,'patch':f.get('patch')} for f in relevant]})
  rec={'instance_id':k['instance_id'],'repo':repo,'original_pr_url':pr['html_url'],'merge_sha':pr['merge_commit_sha'],'merged_at':pr['merged_at'],'window_end':end.isoformat(),'window_days':365,'end_commit_sha':endsha,'default_branch_queried':branch,'source_paths':paths,'path_history_coverage':pathpages,'distinct_path_commits':len(details),'files_additions':sum(f['additions'] for c in details for f in c['files']),'files_deletions':sum(f['deletions'] for c in details for f in c['files']),'commits':details,'limitations':'Default-branch file churn, not attributed defects. PR merge and metadata patch may differ; inspect exact code. No rename-follow across paths.'}
  dump(folder/'history_summary.json',rec);results.append(rec);print(k['instance_id'],'commits',len(details),'add/del',rec['files_additions'],rec['files_deletions'],flush=True)
 dump(ROOT/'HISTORY_SUMMARY.json',{'protocol_sha256':hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest(),'cases':results,'scope':'All three hosted nonaccepted gold cases; no population defect-rate claim.'})

if __name__=='__main__':main()
