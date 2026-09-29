exec(open('/tmp/ore-publication-auth.py').read().split('f=A/')[0])
import shutil
c=json.load(open(O/'COMMIT-AUTHENTICATION.json'));h=c['commit'];baseline=json.load(open(O/'PRE-PUBLICATION-BOUNDARY.json'));rows=c['rows'];commands=[]
def run(a):
 r=git(a);commands.append(r);assert r['exit_code']==0,r;return r['stdout']
assert run(['rev-parse','HEAD','@{upstream}']).splitlines()==[h,h];assert run(['rev-list','--left-right','--count','HEAD...@{upstream}']).split()==['0','0'];assert not run(['diff','--cached','--raw']);run(['diff','--check']);run(['diff','--cached','--check'])
assert run(['diff-tree','--no-commit-id','--name-status','-r',h]).splitlines()==['A\t'+r['path'] for r in rows]
assert run(['rev-list','--parents','-n','1',h]).split()==[h,c['parent']];assert run(['rev-parse','HEAD^{tree}']).strip()==c['tree']
for r in rows:
 p=P/r['path'];b=p.read_bytes();assert identity(b)=={k:r['after'][k] for k in identity(b)};assert stat.S_IMODE(p.stat().st_mode)==0o644;assert not p.is_symlink();assert subprocess.check_output(['git','cat-file','blob',r['after']['git_blob_sha1']],cwd=P)==b
for r in baseline['material']:
 p=P/r['path'];assert identity(p.read_bytes())['sha256']==r['sha256'];assert oct(stat.S_IMODE(p.stat().st_mode))==r['mode']
expected={r['path'] for r in baseline['material'] if r['classification']=='untracked'};assert set(run(['ls-files','--others','--exclude-standard']).splitlines())==expected
oldrefs=next(r['stdout'] for r in baseline['commands'] if r['args'][0]=='for-each-ref');expectedrefs=oldrefs.replace('refs/heads/research/post-v1 '+c['parent'],'refs/heads/research/post-v1 '+h).replace('refs/remotes/origin/research/post-v1 '+c['parent'],'refs/remotes/origin/research/post-v1 '+h);assert run(['for-each-ref','--format=%(refname) %(objectname) %(objecttype) %(symref)'])==expectedrefs
for r in baseline['raw_git']:
 if r['path'] in ['.git/index','.git/refs/heads/research/post-v1','.git/refs/remotes/origin/research/post-v1']:continue
 p=P/r['path'];assert identity(p.read_bytes() if p.exists() else b'')['sha256']==r['sha256'],r['path']
for r in json.loads((Q/'evidence/repository-before.json').read_bytes())['commands']:
 if r['args'][0] in ['config','remote','symbolic-ref','worktree']:assert run(r['args'])==r['stdout']
assert run(['diff','--binary'])==next(r['stdout'] for r in baseline['commands'] if r['args']==['diff','--binary'])
ignored=[]
for n in run(['ls-files','--others','--ignored','--exclude-standard','-z']).split('\0'):
 if not n:continue
 p=P/n;s=p.lstat();ignored.append(dict(path=n,bytes=s.st_size,mode=oct(s.st_mode),mtime_ns=s.st_mtime_ns,symlink=os.readlink(p) if p.is_symlink() else None))
old={r['path']:r for r in baseline['ignored_metadata']};new={r['path']:r for r in ignored};changes=[dict(path=k,before=old.get(k),now=new.get(k)) for k in sorted(old.keys()|new.keys()) if old.get(k)!=new.get(k)];assert {r['path'] for r in changes}<={r['path'] for r in baseline['ignored_changes']}
save('FINAL-REPOSITORY-BOUNDARY.json',dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),commands=commands,commit=h,parent=c['parent'],tree=c['tree'],index=identity((P/'.git/index').read_bytes()),index_entries=run(['ls-files','--stage']),status=run(['status','--porcelain=v2','--branch','--untracked-files=all']),material_all_755_unchanged=True,package_all_37_unchanged=True,untracked_unrelated=31,tracked_modified=5,staged=0,refs_count=39,refs_only_authorized_research_and_tracking_changed=True,ignored_metadata=ignored,ignored_changes=changes))
print('Final boundary PASS: 37 exact published files, 755 inherited files unchanged, empty index delta, five inherited modifications, 31 unrelated untracked; refs/config preserved.')
