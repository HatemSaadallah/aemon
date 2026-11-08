import hashlib,json,copy,sys,tempfile,shutil,argparse,subprocess
from pathlib import Path
from types import SimpleNamespace
parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--output',type=Path);parser.add_argument('--repo',type=Path,default=Path.cwd());parser.add_argument('--baseline-revision',default='0311430');args=parser.parse_args()
ROOT=args.repo.resolve();sys.path.insert(0,str(ROOT/"src"))
import strategy_agent.env.cases as cases_module
from strategy_agent.env.checks import _affected
from strategy_agent.env.tools import Investigation
PATH=args.candidate
data=json.loads(PATH.read_text());original=json.loads(subprocess.check_output(['git','show',args.baseline_revision+':strategy/dossier/cases_heldout.json'],cwd=ROOT,text=True))
checks={}
checks['original_cases_preserved']=all(dict(c,split='heldout') in data['cases'] for c in original['cases'])
checks['unique_case_ids']=len({c['id'] for c in data['cases']})==len(data['cases'])
checks['case_count']=len(data['cases'])==16
checks['eight_added']=len(data['cases'])-len(original['cases'])==8
before=cases_module.load_cases();checks['default_excludes_heldout']=not {c.id for c in before}&{c['id'] for c in data['cases']}
with tempfile.TemporaryDirectory(prefix='codex-heldout-validation-') as temp:
 here=Path(temp);(here/'dossier').mkdir()
 for name in ['evidence.json','cases.json']:
  shutil.copyfile(ROOT/'data/dossier'/name,here/'dossier'/name)
 shutil.copyfile(PATH,here/'dossier/cases_heldout.json')
 old=cases_module.DOSSIER;cases_module.DOSSIER=here/"dossier"
 try:
  heldout=cases_module.load_cases(split='heldout');default=cases_module.load_cases()
 finally:cases_module.DOSSIER=old
checks['isolated_loader_accepts_sixteen']=len(heldout)==16
checks['development_ids_unchanged']=[c.id for c in default]==[c.id for c in before]
checks['no_market_evidence_shared']=all(all(r.scope==c.id.split('-')[0] for r in c.dossier.records.values()) for c in heldout)
examples={'epro':('A durability and repairability promise makes households choose the washer.','The existing self-service laundromat route is best.'),'aqp':('Cartridge maintenance friction stops households using filters.','People switch from bottled water to tap water on price.'),'simo':('Learning brewing skills through onboarding makes a buyer choose the offer.','Owners buy visible machines to signal status to guests.')}
examples['rational']=('Installation coordination friction deters home cooks from reserving a combi-steamer.','Households buy primarily to display a chef-status brand.')
for scope in examples:
 pair=[c for c in data['cases'] if c['scope']==scope and c.get('shock',{}).get('direction') in ('supports','undermines')]
 checks[scope+'_opposed_pair']=len(pair)==2 and {c['shock']['direction'] for c in pair}=={'supports','undermines'}
 a,b=[c['shock']['design'] for c in pair]
 checks[scope+'_actor_metadata_neutral']=pair[0]['shock']['record']['id']==pair[1]['shock']['record']['id'] and pair[0]['shock']['record']['title']==pair[1]['shock']['record']['title']
 checks[scope+'_mirrored_counts']=a['treatment_count']==b['control_count'] and a['control_count']==b['treatment_count'] and a['treatment_n']==b['treatment_n']==400
 for c in [c for c in heldout if c.id.startswith(scope+'-') and c.shock and c.shock_direction!='irrelevant']:
  relevant,unrelated=examples[scope]
  run=SimpleNamespace(case=c,theories={'T1':{'first_claim':relevant,'why_behaviour_changes':''},'T2':{'first_claim':unrelated,'why_behaviour_changes':''}})
  checks[c.id+'_target_example']=_affected(run)==['T1']
  inv=Investigation(c);inv.frame={'objective':'test'};inv.theories={'T1':{}};inv.shock_delivered=True;inv.surfaced.add(c.shock.id);inv.read.add(c.shock.id)
  result=inv.call('assess_evidence',{'theory_id':'T1','evidence_id':c.shock.id,'direction':'supports','quote':'SIMULATED RESULT, NOT REAL DATA.','evidence_kind':'independent_study','does_not_show':'No real-world demand is demonstrated.'})
  checks[c.id+'_synthetic_support_refused']='error' in result and inv.calls[-1]['category']=='synthetic_as_evidence'
  result=inv.call('finish',{'recommendation':'test','target_customer':'test','value_proposition':'test','favoured_theory':'T1','next_action':'test','uncertainty':'test','would_change_if':['test'],'evidence_ids':[c.shock.id]})
  checks[c.id+'_synthetic_finish_refused']='error' in result and inv.calls[-1]['category']=='synthetic_as_evidence'
report={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'candidate_sha256':hashlib.sha256(PATH.read_bytes()).hexdigest(),'scope':'isolated schema, lexical eligibility examples, loader leakage and synthetic-evidence guard probes; no held-out model runs','checks':checks,'passed':sum(checks.values()),'total':len(checks)}
if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));assert all(checks.values())
