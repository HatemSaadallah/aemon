import json,tempfile,pathlib,copy
import judge
c=judge.config();truth=judge.read(judge.ROOT/'qualification_key_v1.jsonl')
def prediction(t):
 dims={d:{'status':('not_applicable' if d not in t['applicable_dimensions'] else t.get('expected_status',{}).get(d,'scored')),'score':2,'event_ids':['A1'],'reason':'offline transport fixture'} for d in c['dimensions']}
 for x in dims.values():
  if x['status']!='scored':x['score']=None
 return {'packet_id':t['packet_id'],'dimensions':dims,'red_flags':[{'kind':x,'event_ids':['A3'],'reason':'fixture'} for x in t['required_flags']],'suitable_for_training':t['expected_suitable'],'screen_reason':'offline fixture, not model output'}
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp)/'pred.jsonl';rows=[prediction(t) for t in truth];key=judge.ROOT/'qualification_key_v1.jsonl'
 def check(rows,fixture=True,k=key):p.write_text(''.join(json.dumps(x)+'\n' for x in rows));return judge.evaluate(p,k,fixture)
 assert check(rows)['status']=='offline_fixture_checks_passed'
 for broken in [rows[:-1],rows+[rows[0]]]:assert check(broken)['status']=='offline_fixture_checks_failed'
 broken=copy.deepcopy(rows);broken[0]['suitable_for_training']=False;assert check(broken)['status']=='offline_fixture_checks_failed'
 broken=copy.deepcopy(rows);broken[0]['dimensions'].pop('revision');assert check(broken)['status']=='offline_fixture_checks_failed'
 broken=copy.deepcopy(rows);broken[1]['red_flags']=[];assert check(broken)['status']=='offline_fixture_checks_failed'
 dev=judge.read(judge.ROOT/'anchor_key_v1.jsonl');assert check([prediction(t) for t in dev],k=judge.ROOT/'anchor_key_v1.jsonl')['status']=='offline_fixture_checks_failed'
 assert check(rows,fixture=False)['status']=='not_qualified'
 wrappers=[{'packet_id':v['packet_id'],'fixture':True,'model':c['candidate_model'],'teacher_model':c['teacher_model'],'prompt_sha256':c['artifact_sha256']['judge_prompt_v1.txt'],'packets_sha256':c['artifact_sha256']['qualification_blind.jsonl'],'generation':c['generation'],'judgment':v} for v in rows]
 assert check(wrappers,fixture=False)['status']=='not_qualified'
 for field,value in [('model','wrong-model'),('prompt_sha256','wrong-hash'),('packets_sha256','wrong-packets')]:
  broken=copy.deepcopy(wrappers)
  for v in broken:v.pop('fixture');v[field]=value
  result=check(broken,fixture=False);assert result['status']=='not_qualified'
  expected={'model':'candidate/teacher mismatch','prompt_sha256':'prompt digest mismatch','packets_sha256':'blind packet digest mismatch'}[field]
  assert any(expected in e for e in result['errors'])
 badkey=pathlib.Path(tmp)/'key.jsonl';badkey.write_text(key.read_text()+'\n');assert check(wrappers,fixture=False,k=badkey)['status']=='not_qualified'
 broken=copy.deepcopy(rows)
 idx=next(i for i,t in enumerate(truth) if t.get('expected_status'))
 broken[idx]['dimensions']['revision']['status']='not_applicable';assert check(broken)['status']=='offline_fixture_checks_failed'
print('14 offline probes passed; no candidate qualification or inference was performed.')
