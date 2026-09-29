exec(open('/tmp/ore-publication-auth.py').read().split('f=A/')[0])
import sys
rows=json.load(open(O/'AUTHENTICATED-PACKAGE.json'))['canonical_delta'];base='063d823dc97f1a3690e26f8bb328385acb9d0aef';phase=sys.argv[1]
def run(a):
 t=datetime.datetime.now(datetime.timezone.utc).isoformat();r=git(a)
 with (O/'TRANSITION-COMMANDS.jsonl').open('a') as f:f.write(json.dumps(dict(time=t,**r))+'\n')
 assert r['exit_code']==0,r
 return r['stdout']
def material():
 for r in json.load(open(O/'PRE-PUBLICATION-BOUNDARY.json'))['material']:
  p=P/r['path'];assert identity(p.read_bytes())['sha256']==r['sha256'],r['path'];assert oct(stat.S_IMODE(p.stat().st_mode))==r['mode']
 for r in rows:
  p=P/r['path'];assert identity(p.read_bytes())=={k:r['after'][k] for k in identity(p.read_bytes())},r['path'];assert stat.S_IMODE(p.stat().st_mode)==0o644
 expected={r['path'] for r in json.load(open(O/'PRE-PUBLICATION-BOUNDARY.json'))['material'] if r['classification']=='untracked'}
 actual=set(run(['ls-files','--others','--exclude-standard']).splitlines());assert actual==expected|(set(r['path'] for r in rows) if phase=='stage' else set()),(actual^expected)
def indexed():
 changes=run(['diff','--cached','--name-status']).splitlines();assert changes==['A\t'+r['path'] for r in rows],changes
 for r in rows:
  b=subprocess.check_output(['git','show',':'+r['path']],cwd=P);assert identity(b)=={k:r['after'][k] for k in identity(b)}
  assert run(['ls-files','--stage','--',r['path']]).strip()==f"100644 {r['after']['git_blob_sha1']} 0\t{r['path']}"
 run(['diff','--cached','--check']);material()
if phase=='stage':
 assert run(['rev-parse','HEAD']).strip()==base;assert not run(['diff','--cached','--raw']);material();assert identity((P/'.git/index').read_bytes())['sha256']=='07d944187853f09e383860d24370e5c18052ff962e9bef5133082d739e647fc4'
 run(['add','--']+[r['path'] for r in rows]);phase='staged';indexed();save('STAGED-FREEZE.json',dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),canonical_delta_sha256='2e64bc07720a8e91b387724704d44860ee9a16fb5d5e364b46c11c5f97c12b1b',rows=rows,index=identity((P/'.git/index').read_bytes()),tree=run(['write-tree']).strip(),entries=run(['ls-files','--stage']),status=run(['status','--porcelain=v2','--branch','--untracked-files=all'])))
elif phase=='commit':
 assert run(['rev-parse','HEAD']).strip()==base;indexed();run(['commit','-F',str(O/'COMMIT-MESSAGE.txt')]);commit=run(['rev-parse','HEAD']).strip();assert run(['rev-list','--parents','-n','1','HEAD']).split()==[commit,base];assert run(['diff-tree','--no-commit-id','--name-status','-r','HEAD']).splitlines()==['A\t'+r['path'] for r in rows]
 for r in rows:
  b=subprocess.check_output(['git','show',commit+':'+r['path']],cwd=P);assert identity(b)=={k:r['after'][k] for k in identity(b)}
 assert not run(['diff','--cached','--raw']);material();tree=run(['rev-parse','HEAD^{tree}']).strip();assert tree==json.load(open(O/'STAGED-FREEZE.json'))['tree'];assert run(['log','-1','--format=%B']).strip()==(O/'COMMIT-MESSAGE.txt').read_text().strip();save('COMMIT-AUTHENTICATION.json',dict(commit=commit,parent=base,tree=tree,rows=rows,message=run(['log','-1','--format=%B']),commit_raw=run(['cat-file','commit',commit]),full_tree=run(['ls-tree','-r','-t','--full-tree','HEAD']),index=identity((P/'.git/index').read_bytes()),index_entries=run(['ls-files','--stage']),refs=run(['for-each-ref','--format=%(refname) %(objectname) %(objecttype) %(symref)']),status=run(['status','--porcelain=v2','--branch','--untracked-files=all']),ahead_behind=run(['rev-list','--left-right','--count','HEAD...@{upstream}'])));print(commit,tree)
print(phase,'PASS')
