import pathlib,json,subprocess,os,hashlib,stat,datetime
P=pathlib.Path('/Users/erale/Documents/orev3');O=pathlib.Path('/Users/erale/.codex/visualizations/2026/09/29/01a0eb6e-5f96-7000-b217-ab265e6f2e5e');Q=P/'docs/research/governance/ore-n0-repository-integration-c1';A=pathlib.Path('/Users/erale/.codex/visualizations/2026/09/29/01a0eb15-819f-75d1-b221-939a84121556');R=pathlib.Path('/Users/erale/.codex/visualizations/2026/09/29/01a0eb5b-7133-7f92-be4c-c11e13d66ae8');O.mkdir(exist_ok=True)
def identity(b):return dict(bytes=len(b),lf=b.count(b'\n'),terminal_LF=b.endswith(b'\n'),sha256=hashlib.sha256(b).hexdigest())
def save(n,x):(O/n).write_text(json.dumps(x,indent=2)+'\n')
def git(a):
 r=subprocess.run(['git',*a],cwd=P,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),capture_output=True);return dict(args=a,exit_code=r.returncode,stdout=r.stdout.decode(),stderr=r.stderr.decode())
f=A/'C1-AUTHOR-FREEZE.json';assert identity(f.read_bytes())['sha256']=='a938e15517035f9e1b484833a74c48b7f3e83072247c9820f9d33c7dd776ee6b';freeze=json.loads(f.read_bytes())
v=R/'RR-ORE-N0-REPOSITORY-INTEGRATION-C1-PASS.md';assert identity(v.read_bytes())==dict(bytes=41748,lf=272,terminal_LF=True,sha256='060db9a1730a55710095142dcebb35e158571988e707f7ce24cca02f9a2266ad');review=json.loads((R/'REVIEW-FREEZE.json').read_bytes());assert review['identity']==identity(v.read_bytes());assert review['sole_next_gate']=='ORE N0 — INTEGRATION ADOPTION / PUBLICATION AUTHOR';assert not review['N0_activated']
rows=[]
for r in freeze['canonical_delta']:
 p=P/r['path'];assert p.is_file() and not p.is_symlink();b=p.read_bytes();x=dict(**identity(b),filesystem_mode=f'{stat.S_IMODE(p.stat().st_mode):04o}',git_mode='100644',git_blob_sha1=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest());assert x==r['after'],r['path'];rows.append(dict(operation='add',path=r['path'],before=None,after=x))
assert len(rows)==37;assert {str(p.relative_to(P)) for p in Q.rglob('*') if p.is_file()}=={r['path'] for r in rows};canonical=json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();assert hashlib.sha256(canonical).hexdigest()=='2e64bc07720a8e91b387724704d44860ee9a16fb5d5e364b46c11c5f97c12b1b';save('AUTHENTICATED-PACKAGE.json',dict(verdict=identity(v.read_bytes()),author_freeze=identity(f.read_bytes()),canonical_delta_sha256=hashlib.sha256(canonical).hexdigest(),canonical_delta=rows))
before=json.loads((Q/'evidence/repository-before.json').read_bytes());prior=json.loads((R/'repository-review.json').read_bytes());commands=[git(r['args']) for r in before['commands']];material=[]
for r in before['material']:
 p=P/r['path'];b=p.read_bytes();x=dict(**identity(b),mode=oct(stat.S_IMODE(p.stat().st_mode)));material.append(dict(path=r['path'],classification=r['classification'],**x,matches=all(x[k]==r[k] for k in x),reviewed_identity={k:r[k] for k in x}))
raw=[]
for n,r in before['raw_git'].items():
 if 'identity' not in r:continue
 p=P/n;b=p.read_bytes() if p.exists() else b'';raw.append(dict(path=n,**identity(b),matches=identity(b)['sha256']==r['identity']['sha256'],expected_sha256=r['identity']['sha256']))
ignored=[]
for n in git(['ls-files','--others','--ignored','--exclude-standard','-z'])['stdout'].split('\0'):
 if not n:continue
 p=P/n;s=p.lstat();ignored.append(dict(path=n,bytes=s.st_size,mode=oct(s.st_mode),mtime_ns=s.st_mtime_ns,symlink=os.readlink(p) if p.is_symlink() else None))
old={r['path']:r for r in prior['ignored_metadata']};new={r['path']:r for r in ignored};changes=[dict(path=k,before=old.get(k),now=new.get(k)) for k in sorted(old.keys()|new.keys()) if old.get(k)!=new.get(k)]
oldcommands={tuple(r['args']):r for r in prior['commands']};cd=[]
for r in commands:
 oldr=oldcommands.get(tuple(r['args']));
 if oldr and (r['exit_code'],r['stdout'])!=(oldr['exit_code'],oldr['stdout']):cd.append(dict(args=r['args'],before=oldr,now=r))
report=dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),commands=commands,material=material,raw_git=raw,ignored_metadata=ignored,ignored_changes=changes,command_drift=cd)
save('PRE-PUBLICATION-BOUNDARY.json',report)
print('package PASS 37; canonical delta PASS; author/reviewer identities PASS');print('material mismatches',json.dumps([r for r in material if not r['matches']],indent=2));print('raw mismatches',json.dumps([r for r in raw if not r['matches']],indent=2));print('command drift',[r['args'] for r in cd]);print('ignored changes',json.dumps(changes,indent=2))
for r in commands:
 if r['args'][0] in ['rev-parse','rev-list','symbolic-ref','remote','diff']:print(r['args'],r['exit_code'],r['stdout'][:1500])
