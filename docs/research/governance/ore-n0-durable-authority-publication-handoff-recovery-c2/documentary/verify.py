"""Read-only documentary validation; never independent review or prospective preflight."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
P=Path(__file__).resolve().parents[1]
R=P.parents[3]
C=P.with_name(P.name[:-1]+'1')
I=P.with_name('ore-n0-repository-integration-c1')
BASE='docs/research/governance/'
CP=str(C.relative_to(R))+'/'
PP=str(P.relative_to(R))+'/'
PTR=BASE+'ORE-N0-RECOVERY-CURRENT-GATE.json'
OLDPTR=BASE+'ORE-N0-CURRENT-GATE.json'
GATE=PP+'CURRENT-NEXT-GATE.json'
NEXT='ORE N0 — DURABLE RECOVERY ADOPTION / PUBLICATION AUTHOR'
FUTURE='FRESH INDEPENDENT HIGH-RISK REVIEW — ORE N0 RECOVERY PUBLICATION / ACTIVATION READINESS'
REVIEW='FRESH INDEPENDENT HIGH-RISK REVIEW — ORE N0 DURABLE AUTHORITY / PUBLICATION HANDOFF RECOVERY C2'
HEAD='d1c9fc56fc183cdcca83d82cc896e4859a00f4dc'
PINNED={
'evidence/recovery-review/REVIEW.md':'442b89751ead8f7ebf2bc756ff98cd4ea9abe766c00f49616e4b83a654d5e085',
'evidence/recovery-review/REVIEW-FREEZE.json':'089ace456d80d7d2ee0d20258c78c59aef78972e654e88e6e11264c0277fc8e9',
'evidence/recovery-author/AUTHOR-FREEZE.json':'40c79bbc7c019c6b52ddbfd3a750fb0d84b3f12eafa32e9ba6a51ea5666424b2',
'evidence/stopped-publication/RESULT.md':'696bc6b1a6523bcceff8e3b7c924b5199d8831e44707d15f51697f823ebe61b9',
'evidence/stopped-publication/RESULT-FREEZE.json':'1e39317845cb6c7945a8646e26ef5a17ffdd998a4c88e1f930308a6f46ae72ba'}

def audit(event,args):
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        assert '/.codex/' not in os.fsdecode(args[0]),'external session storage read prohibited'
sys.addaudithook(audit)

def identity(b):
    return dict(bytes=len(b),lf=b.count(b'\n'),terminal_LF=b.endswith(b'\n'),sha256=hashlib.sha256(b).hexdigest())
def canonical(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()

class View:
    """Same validator over real files or injected missing/changed byte bodies."""
    def __init__(self,changes=None):self.changes=changes or {};self.missing=[]
    def read(self,path):
        q=Path(path);assert not q.is_absolute() and '..' not in q.parts,'external retrieval path'
        if path in self.changes:b=self.changes[path]
        else:
            p=R/path;assert not p.is_symlink(),'symlink authority'
            b=p.read_bytes() if p.is_file() else None
        if b is None:self.missing.append(path)
        return b
    def load(self,path):
        b=self.read(path);return json.loads(b) if b is not None else None
    def match(self,path,expected):
        b=self.read(path)
        if b is not None:assert identity(b)=={k:expected[k] for k in identity(b)},('identity',path)
        return b

def select(nodes):
    ids={n['path'] for n in nodes};assert len(ids)==len(nodes),'duplicate gate'
    parents={n['path']:set(n['parents']) for n in nodes}
    assert all(p in ids for ps in parents.values() for p in ps),'missing predecessor'
    def visit(n,active,done):
        assert n not in active,'cyclic precedence'
        if n in done:return
        for p in parents[n]:visit(p,active|{n},done)
        done.add(n)
    done=set()
    for n in ids:visit(n,set(),done)
    terminals=ids-set().union(*parents.values())
    assert len(terminals)==1,'ambiguous precedence'
    return terminals.pop()

def transition_route(verified_conditions):
    """Routing model only. Inputs must come from later independent durable-evidence checks.
    This function does not authenticate a future publication or accept user declarations.
    """
    if any(x == 'FAIL' for x in verified_conditions):
        return 'FAIL/BLOCK', None
    if len(verified_conditions) != 7 or any(x != 'PASS' for x in verified_conditions):
        return 'U/BLOCK', NEXT
    return 'PASS', FUTURE

def check_state(g,old):
    expected=dict(revision=2,controlling_state='recovery reviewed PASS, recovery publication pending',
        publication_status='RECOVERY PUBLICATION PENDING',recovery_review_status='C1 INDEPENDENT PASS',
        recovery_review_meaning='PASS — exact frozen recovery package. Activation readiness remains U/BLOCK.',
        published_integration_commit=HEAD,publication_integrity='PASS',recovery_publication_complete=False,
        activation_readiness='U/BLOCK',N0_established=False,N0_activated=False,T_N0=None,
        prospective_preflight_executed=False,CD_substantive_status='BLOCKED',
        CD_dependency_status='CD prospectively dependency-eligible; documentary only',
        upstream_ore_obligation='UPSTREAM ORE COMPATIBILITY / DRIFT CONTROL = REQUIRED and UNSATISFIED',
        next_gate=NEXT,next_gate_count=1,future_post_publication_next_gate=FUTURE,
        author_lane_next_gate=REVIEW,author_lane_next_gate_count=1)
    for k,v in expected.items():assert k in g and type(g[k]) is type(v) and g[k]==v,('state',k)
    assert g['historical_ledger']==old['historical_ledger'],'historical promotion'
    assert g['historical_ledger_status']==old['historical_ledger_status']
    assert g['precedence']==dict(kind='explicit authenticated supersession DAG',order=4,predecessor_order=3,
        tie='FAIL/BLOCK; residual U preserved',missing_dependency='U/BLOCK',filename_or_mtime_order_permitted=False)
    t=g['post_publication_transition']
    assert t['initial_state']==g['controlling_state'] and t['next_gate']==FUTURE
    assert t['resulting_state']=='recovery publication complete, independent activation-readiness re-review pending'
    assert t['automatic_activation'] is False
    assert len(t['required_conjuncts'])==7 and len(set(t['required_conjuncts']))==7
    for text in ['independent C2 PASS','separate compatible action authorization','publication commit','C2 author freeze','publication receipt','published descendant commit','fresh live']:
        assert any(text in s for s in t['required_conjuncts']),('transition prerequisite',text)
    annex=t['later_evidence_annex']
    assert annex['root']==BASE+'ore-n0-recovery-adoption'
    assert annex['fixed_roles']==['C2-AUTHOR-FREEZE.json','C2-REVIEW.md','C2-REVIEW-FREEZE.json','PUBLICATION-RECEIPT.json']
    assert 'STOP before staging' in annex['status']
    assert t['incomplete'].startswith('U/BLOCK') and t['contradiction'].startswith('FAIL/BLOCK')

def check(v,final=False):
    # Contradictions in available inputs take FAIL precedence over accumulated missing bodies.
    old=v.load(CP+'CURRENT-NEXT-GATE.json');g=v.load(GATE)
    if g is not None and old is not None:check_state(g,old)
    for n,h in PINNED.items():
        b=v.read(PP+n)
        if b is not None:assert identity(b)['sha256']==h,('original evidence',n)
    ret=v.load(PP+'RETENTION-MAP.json')
    if ret:
        assert len(ret['records'])==5 and {x['repository_path'] for x in ret['records']}=={PP+n for n in PINNED}
        for x in ret['records']:
            assert x['source_identity']==x['identity']
            assert x['copy_semantics']=='Exact original bytes; original authority/scope/negatives only. No new review, no stronger PASS, no activation authority.'
            assert x['permitted_consumers']==['independent C2 review','separately authorized exact adoption/publication','independent recovery publication/activation-readiness verification','repository-only documentary continuation']
            assert len(x['invalidation_conditions'])==6 and 'source is provenance only' in x['retrieval']
            if 'recovery-review/' in x['repository_path']:
                assert x['originator_lane']=='01a0edc7-1267-7970-8d61-d7cc12f00aa5'
                assert x['source']=='/Users/erale/.codex/visualizations/2026/09/29/'+x['originator_lane']+'/'+Path(x['repository_path']).name
            if 'recovery-author/' in x['repository_path']:
                assert x['originator_lane']=='01a0ebc9-fbc7-7c43-82ed-250264b724ff'
                assert x['original_source'].endswith('/'+x['originator_lane']+'/RECOVERY-AUTHOR-FREEZE.json')
                assert x['source'].endswith('/01a0edc7-1267-7970-8d61-d7cc12f00aa5/REVIEWED-AUTHOR-FREEZE.json')
            if 'stopped-publication/' in x['repository_path']:
                assert x['originator_lane']=='01a0ee12-9c8b-7d73-a5e5-fa16320bac15'
                assert x['source']=='/Users/erale/.codex/visualizations/2026/09/29/'+x['originator_lane']+'/recovery-publication-gate/'+Path(x['repository_path']).name
            v.match(x['repository_path'],x['identity'])
        v.match(ret['existing_C1_evidence']['path'],ret['existing_C1_evidence']['identity'])
        assert ret['existing_C1_evidence']['count']==49
    af=v.load(PP+'evidence/recovery-author/AUTHOR-FREEZE.json');rf=v.load(PP+'evidence/recovery-review/REVIEW-FREEZE.json')
    if af:
        assert af['file_count']==af['additions']==62 and af['edits']==0 and af['retained_evidence_count']==49
        assert identity(canonical(af['canonical_delta']))['sha256']=='aa8ebf3d40a2e59d8c8d968d24452d700603c32f286c319d363b30c447efa4d1'
        assert len({x['path'] for x in af['canonical_delta']})==62
        for x in af['canonical_delta']:
            assert x['operation']=='add' and x['before'] is None
            b=v.match(x['path'],x['after'])
            if b is not None:
                assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==x['after']['git_blob_sha1']
                assert (R/x['path']).stat().st_mode&0o777==0o644
    if rf:
        assert rf['reviewer_lane']=='01a0edc7-1267-7970-8d61-d7cc12f00aa5'
        assert rf['verdict_file']=='REVIEW.md' and rf['next_gate']==NEXT
        assert rf['reviewed_author_freeze_sha256']==PINNED['evidence/recovery-author/AUTHOR-FREEZE.json']
        assert rf['reviewed_canonical_delta_sha256']=='aa8ebf3d40a2e59d8c8d968d24452d700603c32f286c319d363b30c447efa4d1'
        v.match(PP+'evidence/recovery-review/REVIEW.md',rf['identity'])
    sf=v.load(PP+'evidence/stopped-publication/RESULT-FREEZE.json')
    if sf:
        rows=[x for x in sf['files'] if x['path']=='RESULT.md'];assert len(rows)==1 and sf['result']=='STOP / BLOCKED BEFORE STAGING'
        v.match(PP+'evidence/stopped-publication/RESULT.md',rows[0]['identity'])
    retained=v.load(CP+'RETENTION-MAP.json')
    if retained:
        assert len(retained['records'])==49
        for x in retained['records']:v.match(x['repository_path'],x['identity'])
    ptr=v.load(PTR)
    predecessors=[OLDPTR,CP+'CURRENT-NEXT-GATE.json',BASE+'ore-n0-repository-integration-c1/CURRENT-NEXT-GATE.json']
    if g and ptr:
        assert ptr['candidate_path']==P.name+'/CURRENT-NEXT-GATE.json'
        v.match(GATE,ptr['candidate_identity']);assert ptr['supersedes']==g['supersedes']
        assert [x['path'] for x in g['supersedes']]==predecessors
        for x in g['supersedes']:v.match(x['path'],x['identity'])
        for x in g['durable_evidence_references']:v.match(x['path'],x['identity'])
        assert {x['path'] for x in g['durable_evidence_references']}=={PP+n for n in PINNED}|{CP+'RETENTION-MAP.json'}
        assert ptr['next_gate']==NEXT and ptr['author_lane_next_gate']==REVIEW and ptr['future_post_publication_next_gate']==FUTURE
        nodes=[dict(path=n,parents=[]) for n in predecessors]+[dict(path=PTR,parents=predecessors)]
        assert select(nodes)==PTR==select(nodes[::-1])
        entries=[]
        for p in P.parent.glob('*.json'):
            d=v.load(str(p.relative_to(R)))
            if d and str(d.get('schema','')).startswith('ore-n0-current-gate-entrypoint/'):entries.append(str(p.relative_to(R)))
        assert set(entries)=={PTR,OLDPTR},'unresolved additional N0 entrypoint'
    scope=v.load(PP+'SCOPE.json')
    if scope:
        assert scope['classification']=={'additions':14,'edits':0}
        planned={x['path'] for x in scope['paths']}
        if final:
            actual={str(p.relative_to(R)) for p in P.rglob('*') if p.is_file()}|{PTR}
            assert not actual-planned and len(planned)==14,'scope enlarged'
            v.missing.extend(sorted(planned-actual))
        assert all(x['operation']=='add' and x['before'] is None for x in scope['paths'])
    if final:
        m=v.load(PP+'MANIFEST.json')
        if m and scope:
            assert {x['path'] for x in m['members']}==planned-{PP+'MANIFEST.json'}
            for x in m['members']:
                body=v.match(x['path'],x['identity'])
                if body is not None:assert (R/x['path']).stat().st_mode&0o777==0o644
    return 'U/BLOCK' if v.missing else 'PASS'

def route(changes=None):
    try:return check(View(changes))
    except (AssertionError,ValueError,KeyError,TypeError):return 'FAIL/BLOCK'

def attacks():
    tests=[]
    def test(name,changes,expected):
        got=route(changes);assert got==expected,(name,got,expected)
        tests.append(dict(case=name,expected=expected,observed=got,defense='PASS'))
    def mutate(path,fn):
        d=json.loads((R/path).read_bytes());fn(d);return {path:canonical(d)}
    for name,path in [('PASS hash present but body missing',PP+'evidence/recovery-review/REVIEW.md'),('review body present but freeze absent',PP+'evidence/recovery-review/REVIEW-FREEZE.json'),('recovery author freeze absent',PP+'evidence/recovery-author/AUTHOR-FREEZE.json'),('raw-index anchor omitted',CP+'evidence/index/staged-index.bin'),('one retained C1 body unreachable',CP+'evidence/integration-review/anchor-retrieval.json')]:test(name,{path:None},'U/BLOCK')
    test('hash-only PASS',{PP+'evidence/recovery-review/REVIEW.md':PINNED['evidence/recovery-review/REVIEW.md'].encode()},'FAIL/BLOCK')
    test('freeze points to wrong review',mutate(PP+'evidence/recovery-review/REVIEW-FREEZE.json',lambda d:d['identity'].update(sha256='0'*64)),'FAIL/BLOCK')
    test('author freeze confused with review freeze',{PP+'evidence/recovery-review/REVIEW-FREEZE.json':(P/'evidence/recovery-author/AUTHOR-FREEZE.json').read_bytes()},'FAIL/BLOCK')
    for name,k,val in [('stale C1 gate controls','next_gate','FRESH INDEPENDENT HIGH-RISK REVIEW — ORE N0 DURABLE AUTHORITY / PUBLICATION HANDOFF RECOVERY'),('jump to activation','next_gate','ORE N0 — ACTIVATION AUTHOR'),('future gate current before publication','next_gate',FUTURE),('publication complete before commit','recovery_publication_complete',True),('activation readiness promoted','activation_readiness','PASS'),('N0 active','N0_activated',True),('T_N0 set','T_N0','2026-09-29'),('preflight executed','prospective_preflight_executed',True),('historical U promoted','historical_ledger',[]),('CD eligibility becomes substantive authority','CD_substantive_status','AUTHORIZED'),('upstream removed','upstream_ore_obligation','SATISFIED')]:
        test(name,mutate(GATE,lambda d,k=k,val=val:d.update({k:val})),'FAIL/BLOCK')
    test('copied PASS becomes new review',mutate(PP+'RETENTION-MAP.json',lambda d:d['records'][0].update(copy_semantics='New stronger PASS')),'FAIL/BLOCK')
    test('external visualization retrieval needed',mutate(PP+'RETENTION-MAP.json',lambda d:d['records'][0].update(repository_path=d['records'][0]['source'])),'FAIL/BLOCK')
    test('FAIL precedence with missing PASS',dict({PP+'evidence/recovery-review/REVIEW.md':None},**mutate(GATE,lambda d:d.update(N0_activated=True))),'FAIL/BLOCK')
    graph=[dict(path='z-old',parents=[]),dict(path='a-new',parents=['z-old'])]
    assert select(graph)==select(graph[::-1])=='a-new'
    tests.append(dict(case='filename and enumeration order reversed',expected='PASS',observed='PASS',defense='PASS'))
    for name,bad in [('ambiguous precedence',graph+[dict(path='other',parents=[])]),('cycle',[dict(path='a',parents=['b']),dict(path='b',parents=['a'])])]:
        try:select(bad)
        except AssertionError:tests.append(dict(case=name,expected='FAIL/BLOCK',observed='FAIL/BLOCK',defense='PASS'))
        else:raise AssertionError(name)
    for name, proofs, expected in [
        ('future routing model: all seven independently verified conditions', ['PASS']*7, ('PASS', FUTURE)),
        ('future routing model: no publication proof', ['PASS']*6+['U'], ('U/BLOCK', NEXT)),
        ('future routing model: contradictory publication proof with residual U', ['PASS']*5+['FAIL','U'], ('FAIL/BLOCK', None))]:
        got=transition_route(proofs);assert got==expected
        tests.append(dict(case=name,expected=expected,observed=got,defense='PASS; synthetic routing model, not actual publication evidence'))
    return tests

def run_script(script,*args):
    p=subprocess.run([sys.executable,'-B',str(script),*args],cwd=R,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_NO_REPLACE_OBJECTS='1'),capture_output=True,text=True)
    assert p.returncode==0,(str(script),p.stdout,p.stderr)
    return json.loads(p.stdout)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--author-core',action='store_true');ap.add_argument('--lineage',action='store_true');args=ap.parse_args()
    v=View();result=check(v,final=not args.author_core)
    if result!='PASS':print(json.dumps(dict(result=result,missing=v.missing)));return 2
    for p in P.rglob('*.json'):json.loads(p.read_bytes())
    for link in re.findall(r'\]\(([^)]+)\)',(P/'HANDOFF.md').read_text()):
        if args.author_core and link=='AUTHOR-VALIDATION.json':continue
        assert (P/link).is_file(),link
    c1=run_script(C/'documentary/verify.py')
    lineage=run_script(I/'documentary/verify.py','--lineage') if args.lineage else 'Not rerun; --lineage verifies full nested closure'
    print(json.dumps(dict(result='PASS — C2 author documentary validation only',mode='author-core pre-manifest' if args.author_core else 'final manifest validation',adversarial=attacks(),C1_validation=c1,lineage=lineage,repository_only='PASS: repository paths and immutable Git objects only; Python audit hook rejects .codex reads. Inspected child scripts use repository/Git/temporary reconstruction only; no OS-wide isolation claimed.',retained_new_bodies=5,retained_C1_bodies=49,raw_index='UNCHANGED path A; exact C1 reconstruction passed',controlling_next_gate=NEXT,author_lane_next_gate=REVIEW,future_post_publication_next_gate=FUTURE,activation_readiness='U/BLOCK',N0_activated=False,T_N0=None,CD_substantive_status='BLOCKED'),ensure_ascii=False,indent=2));return 0
if __name__=='__main__':
    try:sys.exit(main())
    except FileNotFoundError as e:print(json.dumps(dict(result='U/BLOCK',reason=str(e))));sys.exit(2)
    except (AssertionError,ValueError,KeyError,TypeError,subprocess.CalledProcessError) as e:print(json.dumps(dict(result='FAIL/BLOCK',residual_U='preserved',reason=str(e))));sys.exit(1)
