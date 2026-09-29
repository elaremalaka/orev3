exec(open('/tmp/ore-publication-auth.py').read().split('f=A/')[0])
c=json.load(open(O/'COMMIT-AUTHENTICATION.json'));h=c['commit'];before=json.load(open(O/'PRE-PUBLICATION-BOUNDARY.json'))
def run(a):
 r=git(a)
 with (O/'TRANSITION-COMMANDS.jsonl').open('a') as f:f.write(json.dumps(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),**r))+'\n')
 assert r['exit_code']==0,r
 return r['stdout']
assert run(['rev-parse','HEAD']).strip()==h;assert run(['symbolic-ref','HEAD']).strip()=='refs/heads/research/post-v1';assert run(['rev-parse','@{upstream}']).strip()==c['parent'];assert not run(['diff','--cached','--raw'])
for r in before['material']:assert identity((P/r['path']).read_bytes())['sha256']==r['sha256'],r['path']
oldrefs=next(r['stdout'] for r in before['commands'] if r['args'][0]=='for-each-ref');newrefs=run(['for-each-ref','--format=%(refname) %(objectname) %(objecttype) %(symref)']);assert newrefs==oldrefs.replace('refs/heads/research/post-v1 '+c['parent'],'refs/heads/research/post-v1 '+h)
assert identity((P/'.git/config').read_bytes())['sha256']==next(r['sha256'] for r in before['raw_git'] if r['path']=='.git/config')
remote=run(['ls-remote','--symref','origin','HEAD','refs/heads/research/post-v1']);assert f"{c['parent']}\trefs/heads/research/post-v1\n" in remote
run(['-c','http.version=HTTP/1.1','-c','http.postBuffer=524288000','push','--no-follow-tags','origin',h+':refs/heads/research/post-v1'])
after=run(['ls-remote','--symref','origin','HEAD','refs/heads/research/post-v1']);assert f'{h}\trefs/heads/research/post-v1\n' in after
assert run(['rev-parse','HEAD','@{upstream}']).splitlines()==[h,h];assert run(['rev-list','--left-right','--count','HEAD...@{upstream}']).split()==['0','0'];save('POST-PUSH-REMOTE.json',dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),commit=h,remote=after,equality=True,ahead=0,behind=0,independent_activation_review=False));print('Published',h,'remote equality PASS; ahead/behind 0/0')
