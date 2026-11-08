"""Frozen judge transport and offline qualification. No calls occur without `run`."""
import argparse,json,pathlib,hashlib,random,math,urllib.request,urllib.error,http.server
ROOT=pathlib.Path(__file__).resolve().parent

def read(path): return [json.loads(s) for s in pathlib.Path(path).read_text().splitlines() if s.strip()]
def config():
 c=json.loads((ROOT/'config_v1.json').read_text())
 for name,digest in c['artifact_sha256'].items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest: raise ValueError('frozen artifact changed: '+name)
 return c

def validate(v,packet,applicable=None):
 if not isinstance(v,dict) or v.get('packet_id')!=packet: raise ValueError('packet identity mismatch')
 c=config()
 if set(v.get('dimensions',{}))!=set(c['dimensions']): raise ValueError('dimension set differs')
 for d,x in v['dimensions'].items():
  if not isinstance(x,dict):raise ValueError('dimension must be an object')
  if applicable is not None and ((d not in applicable) != (x.get('status')=='not_applicable')):raise ValueError('applicability mismatch')
  if x.get('status') not in ('scored','not_reached','not_applicable'): raise ValueError('invalid status')
  if x['status']=='scored' and (type(x.get('score')) is not int or not 0<=x['score']<=3):raise ValueError('invalid score')
  if x['status']!='scored' and x.get('score') is not None:raise ValueError('unscored dimension has score')
  if not isinstance(x.get('event_ids'),list) or not isinstance(x.get('reason'),str):raise ValueError('missing explanation')
 if type(v.get('suitable_for_training')) is not bool or not isinstance(v.get('red_flags'),list) or not isinstance(v.get('screen_reason'),str):raise ValueError('missing screening output')
 for flag in v['red_flags']:
  if not isinstance(flag,dict) or not isinstance(flag.get('kind'),str) or not isinstance(flag.get('event_ids'),list) or not isinstance(flag.get('reason'),str):raise ValueError('malformed red flag')
 if v['suitable_for_training'] and v['red_flags']:raise ValueError('accepted trajectory carries a critical red flag')
 return v

def wilson(k,n,z=1.96):
 if not n:return [0,1]
 q=k/n; den=1+z*z/n; mid=(q+z*z/(2*n))/den; rad=z*math.sqrt(q*(1-q)/n+z*z/(4*n*n))/den
 return [mid-rad,mid+rad]

def evaluate(predictions,key,fixture_mode=False):
 c=config(); truth=read(key); preds=read(predictions); mapped={}
 key_digest=hashlib.sha256(pathlib.Path(key).read_bytes()).hexdigest()
 errors=[]
 if not fixture_mode and key_digest!=c['artifact_sha256']['qualification_key_v1.jsonl']:errors.append('qualification key digest differs')
 for p in preds:
  pid=p.get('packet_id')
  if pid in mapped:errors.append('duplicate prediction '+str(pid))
  mapped[pid]=p
 if len({x['packet_id'] for x in truth})!=len(truth):errors.append('duplicate key id')
 if set(mapped)!=set(x['packet_id'] for x in truth):errors.append('prediction/key coverage differs')
 groups={'positive':[],'negative':[]}; flags=[]
 for t in truth:
  pid=t['packet_id']
  try:
   outer=mapped[pid]
   if not fixture_mode:
    if outer.get('fixture'):raise ValueError('fixture output cannot qualify candidate')
    if outer.get('model')!=c['candidate_model'] or outer.get('teacher_model')!=c['teacher_model']:raise ValueError('candidate/teacher mismatch')
    if outer.get('generation')!=c['generation']:raise ValueError('generation settings mismatch')
    if outer.get('prompt_sha256')!=c['artifact_sha256']['judge_prompt_v1.txt']:raise ValueError('prompt digest mismatch')
    if outer.get('packets_sha256')!=c['artifact_sha256']['qualification_blind.jsonl']:raise ValueError('blind packet digest mismatch')
   p=validate(outer.get('judgment',outer),pid,t.get('applicable_dimensions'))
   for dimension,status in t.get('expected_status',{}).items():
    if p['dimensions'][dimension]['status']!=status:raise ValueError('scheduled-but-unreached stage misclassified')
   groups['positive' if t['expected_suitable'] else 'negative'].append((t,p['suitable_for_training']==t['expected_suitable']))
   found={f.get('kind') for f in p['red_flags'] if isinstance(f,dict)}
   if not set(t.get('required_flags',[]))<=found:flags.append(pid)
  except (KeyError,ValueError,TypeError) as e:errors.append(pid+': '+str(e))
 stats={}
 for label,items in groups.items():
  n=len(items);k=sum(ok for _,ok in items); clusters=len({t['cluster_id'] for t,_ in items})
  stats[label]={'correct':k,'n':n,'clusters':clusters,'rate':k/n if n else None,'wilson_95':wilson(k,n,c['z'])}
 independent_counts=all(v['clusters']==v['n'] for v in stats.values())
 qualified=not errors and not flags and independent_counts and all(t.get('role')=='qualification' for t in truth) and all(v['n']>=c['minimum_'+label+'_clusters'] and v['rate']>=c['minimum_rate'] and v['wilson_95'][0]>=c['minimum_wilson_lower'] for label,v in stats.items())
 return {'version':c['version'],'status':('offline_fixture_checks_passed' if qualified else 'offline_fixture_checks_failed') if fixture_mode else ('qualified_on_synthetic_controls' if qualified else 'not_qualified'),'statistics':stats,'errors':errors,'missed_required_flags':flags,'note':'Synthetic control performance does not establish accuracy on natural teacher trajectories.'}

def main():
 p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
 b=sub.add_parser('prepare');b.add_argument('--packets',required=True);b.add_argument('--output',required=True);b.add_argument('--seed',type=int,default=20261102)
 r=sub.add_parser('run');r.add_argument('--packets',required=True);r.add_argument('--output',required=True);r.add_argument('--url',required=True);r.add_argument('--model',required=True);r.add_argument('--teacher-model',required=True);r.add_argument('--max-tokens',type=int,default=3000)
 e=sub.add_parser('evaluate');e.add_argument('--predictions',required=True);e.add_argument('--key',required=True);e.add_argument('--output',required=True);e.add_argument('--fixture',action='store_true',help='offline checker exercise only; never qualifies candidate')
 s=sub.add_parser('serve');s.add_argument('--port',type=int,default=8012)
 a=p.parse_args();c=config()
 if a.command=='prepare':
  items=read(a.packets);random.Random(a.seed).shuffle(items)
  # Explicit allowlist prevents expected labels, provenance and condition metadata entering packets.
  clean=[{k:v for k,v in x.items() if k in ('packet_id','synthetic','case','sources','events','applicable_dimensions','scheduled_update','update_delivered')} for x in items]
  out=pathlib.Path(a.output)
  if out.exists():raise ValueError('refuse overwrite')
  out.write_text(''.join(json.dumps(x)+'\n' for x in clean))
 elif a.command=='run':
  if a.max_tokens!=c['generation']['max_tokens']:raise ValueError('max_tokens differs from frozen generation settings')
  if a.model!=c['candidate_model'] or a.teacher_model!=c['teacher_model']:raise ValueError('candidate and teacher must match frozen config')
  if hashlib.sha256(pathlib.Path(a.packets).read_bytes()).hexdigest()!=c['artifact_sha256']['qualification_blind.jsonl']:raise ValueError('blind input differs from frozen qualification input')
  if 'claude' in a.model.lower() or a.model.lower()==a.teacher_model.lower():raise ValueError('candidate must be non-Claude and distinct from teacher')
  out=pathlib.Path(a.output)
  if out.exists():raise ValueError('refuse overwrite')
  with out.open('x') as f:
   for x in read(a.packets):
    body={'model':a.model,'messages':[{'role':'system','content':(ROOT/'judge_prompt_v1.txt').read_text()},{'role':'user','content':json.dumps(x)}],'temperature':0,'max_tokens':a.max_tokens,'stream':False}
    result={'packet_id':x['packet_id'],'model':a.model,'teacher_model':a.teacher_model,'prompt_sha256':c['artifact_sha256']['judge_prompt_v1.txt'],'packets_sha256':c['artifact_sha256']['qualification_blind.jsonl'],'generation':c['generation']}
    try:
     req=urllib.request.Request(a.url.rstrip('/')+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
     with urllib.request.urlopen(req,timeout=600) as response: raw=json.load(response)
     result['raw']=raw; text=raw['choices'][0]['message']['content'];result['judgment']=validate(json.loads(text),x['packet_id'],x.get('applicable_dimensions'))
    except Exception as ex:result['error']=str(ex)
    f.write(json.dumps(result)+'\n');f.flush()
 elif a.command=='evaluate':
  out=pathlib.Path(a.output)
  if out.exists():raise ValueError('refuse overwrite')
  out.write_text(json.dumps(evaluate(a.predictions,a.key,a.fixture),indent=2)+'\n')
 else:
  class Handler(http.server.BaseHTTPRequestHandler):
   def do_GET(self):
    if self.path=='/api/status':data=json.dumps({'status':'not_run','config':c,'anchors':read(ROOT/'anchors_v1.jsonl')}).encode();mime='application/json'
    elif self.path=='/':data=(ROOT/'index.html').read_bytes();mime='text/html'
    else:self.send_error(404);return
    self.send_response(200);self.send_header('Content-Type',mime);self.end_headers();self.wfile.write(data)
  http.server.ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__':main()
