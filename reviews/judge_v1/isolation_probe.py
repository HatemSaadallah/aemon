import json,os,pathlib,subprocess
root=pathlib.Path('/home/USER/.cache/codex-judge-campaign')
binary=pathlib.Path('/home/USER/.local/bin/codex').resolve()
cmd=['bwrap','--die-with-parent','--new-session','--unshare-pid','--unshare-ipc','--unshare-uts','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--symlink','usr/bin','/bin','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/work','--dir','/home/USER/.codex','--ro-bind',str(binary),'/judge-codex','--ro-bind','/home/USER/.codex/auth.json','/home/USER/.codex/auth.json','--ro-bind','/etc/ssl','/etc/ssl','--ro-bind','/etc/resolv.conf','/etc/resolv.conf','--ro-bind','/etc/hosts','/etc/hosts','--ro-bind',str(root/'judge_prompt_v1.txt'),'/judge_prompt.txt','--chdir','/work','--clearenv','--setenv','HOME','/home/USER','--setenv','PATH','/usr/local/bin:/usr/bin:/bin']
check=subprocess.run(cmd+['/usr/bin/test','!','-e','/home/USER/Desktop/lexsi-ai-hackathon'],capture_output=True);assert check.returncode==0, check.stderr.decode()
cmd+=['/judge-codex','exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--sandbox','read-only','--json','--model','gpt-6-astra']
settings={'features.shell_tool':False,'features.unified_exec':False,'features.shell_snapshot':False,'features.apps':False,'features.browser_use':False,'features.multi_agent':False,'features.memories':False,'memories.use_memories':False,'memories.generate_memories':False,'web_search':'disabled','project_doc_max_bytes':0,'model_instructions_file':'/judge_prompt.txt','model_reasoning_effort':'medium'}
for k,v in settings.items():cmd+=['-c',k+'='+json.dumps(v)]
cmd+=['-']
packet=json.loads((root/'qualification_blind.jsonl').read_text().splitlines()[0])
(root/'first_packet_id.txt').write_text(packet['packet_id'])
with (root/'codex_first.jsonl').open('x') as out,(root/'codex_first.stderr').open('x') as err:
 r=subprocess.run(cmd,input=json.dumps(packet),text=True,stdout=out,stderr=err,timeout=300)
print('returncode',r.returncode)
