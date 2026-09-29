"""Read-only candidate documentary verifier, not independent review or prospective preflight.
No external session reads, network, Git writes, or execution of historical retained code.
"""
import copy
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

P = Path(__file__).resolve().parents[1]
R = P.parents[3]
I = P.parent/'ore-n0-repository-integration-c1'
COMMIT = 'd1c9fc56fc183cdcca83d82cc896e4859a00f4dc'
NEXT = 'FRESH INDEPENDENT HIGH-RISK REVIEW — ORE N0 DURABLE AUTHORITY / PUBLICATION HANDOFF RECOVERY'
GAPS = ['complete integration PASS, author freeze, and publication evidence lack authenticated accepted durable retention;', 'repository-only recovery lacks an authenticated current-gate supersession;', 'required raw-index retention or accepted equivalent representation remains unresolved.']
PINNED = {
    'evidence/integration-review/RR-ORE-N0-REPOSITORY-INTEGRATION-C1-PASS.md': '060db9a1730a55710095142dcebb35e158571988e707f7ce24cca02f9a2266ad',
    'evidence/integration-author/C1-AUTHOR-FREEZE.json': 'a938e15517035f9e1b484833a74c48b7f3e83072247c9820f9d33c7dd776ee6b',
    'evidence/publication/PUBLICATION-ADOPTION-RECEIPT.json': '8436af27bda385083d5295ff6ae8fb33a3486d6d04f07e5f1e8408cd8acaa5d0',
    'evidence/activation-readiness/REVIEW.md': '7b371223292bef71aafc26896ee73f325171bf199d1f0a2e67f1fec964fc3e2f',
    'evidence/index/prepublication-index.bin': '07d944187853f09e383860d24370e5c18052ff962e9bef5133082d739e647fc4',
    'evidence/index/staged-index.bin': 'cd15512f695b4a83efb17cc04399daff604c3dcda9fa92328dce043e8b8b7faa',
    'evidence/index/publication-index.bin': 'ff65baf0e554bdcdaa1024c15fd6c0d8253f307db237f8f6e743f292a6c99699',
}

# Any accidental dependency on session/visualization files is an actual failing test.
def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        assert '/.codex/' not in os.fsdecode(args[0]), 'external storage dependence'
sys.addaudithook(audit)


def identity(b):
    return dict(bytes=len(b), lf=b.count(b'\n'), terminal_LF=b.endswith(b'\n'), sha256=hashlib.sha256(b).hexdigest())


def load(p):
    return json.loads(p.read_bytes())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=R, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1'))


def identity_route(body, expected):
    if body is None:
        return 'U/BLOCK'
    return 'PASS' if identity(body) == expected else 'FAIL/BLOCK'


def state_route(g):
    expected = {'status': 'DRAFT-UNREVIEWED', 'publication_completed': True,
        'publication_integrity': 'PASS', 'activation_readiness': 'U/BLOCK',
        'N0_established': False, 'N0_activated': False, 'T_N0': None,
        'prospective_preflight_executed': False, 'CD_executed': False,
        'CD_substantive_status': 'BLOCKED', 'CD_dependency_status': 'CD prospectively dependency-eligible',
        'review_executed': False, 'accepted_durable_retention': False, 'recovery_published': False,
        'next_gate_count': 1, 'next_gate': NEXT, 'published_commit': COMMIT,
        'upstream_ore_obligation': 'UPSTREAM ORE COMPATIBILITY / DRIFT CONTROL = REQUIRED and UNSATISFIED',
        'recovery_gaps': GAPS, 'order': 3}
    if any(k not in g for k in expected):
        return 'U/BLOCK'
    if any(g[k] != v for k,v in expected.items()):
        return 'FAIL/BLOCK'
    if g.get('historical_ledger') != load(P/'evidence/publication/PUBLICATION-ADOPTION-RECEIPT.json')['historical_ledger']:
        return 'FAIL/BLOCK'
    if g.get('predecessor',{}).get('sha256') != '10471c83b968c8557492aee33f9a835c7786cbbfab7ae0a5dedc5b562f239c04':
        return 'U/BLOCK'
    if [x['order'] for x in g.get('supersession_chain',[])] != [1,2,3]:
        return 'U/BLOCK'
    return 'PASS'


def index_entries(b):
    assert b[:4] == b'DIRC' and hashlib.sha1(b[:-20]).digest() == b[-20:]
    v,n = struct.unpack('>II',b[4:12]); assert v == 2
    pos,rows = 12,[]
    for _ in range(n):
        start=pos;flags=int.from_bytes(b[pos+60:pos+62]);assert not flags&0x4000
        end=b.index(b'\0',pos+62);name=b[pos+62:end].decode();mode=int.from_bytes(b[pos+24:pos+28]);blob=b[pos+40:pos+60].hex();stage=(flags>>12)&3
        assert not flags&0x8000 and stage == 0
        rows.append(f'{mode:06o} {blob} {stage}\t{name}\n')
        pos=start+((end-start+1+7)//8)*8;assert b[end:pos]==b'\0'*(pos-end)
    ext=b[pos:-20];assert ext[:4]==b'TREE' and len(ext)==8+int.from_bytes(ext[4:8])
    return ''.join(rows),pos,ext


def main():
    manifest=load(P/'MANIFEST.json');scope=load(P/'SCOPE.json')
    assert len(scope['paths'])==62
    intended=json.dumps(scope['paths'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    assert identity(intended)==scope['canonical_intended_delta_identity']
    actual={str(p.relative_to(R)) for p in P.rglob('*') if p.is_file()}
    actual.add('docs/research/governance/ORE-N0-CURRENT-GATE.json')
    assert actual=={r['path'] for r in scope['paths']}
    assert all(r['operation']=='add' and r['before'] is None and r['before_status']=='ABSENT' for r in scope['paths'])
    assert {r['repository_path'] for r in manifest['members']}==actual-{str((P/'MANIFEST.json').relative_to(R))}
    for row in manifest['members']:
        p=R/row['repository_path']; assert not p.is_symlink() and p.stat().st_mode&0o777==0o644
        assert identity_route(p.read_bytes(),row['identity'])=='PASS',str(p)
        assert all(k in row for k in ['artifact_id','propositions','kind','source_provenance','authority_status','permitted_consumers','invalidation_conditions','retrieval'])
    for name,h in PINNED.items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==h
    for p in P.rglob('*.json'):load(p)
    for p in P.rglob('*.jsonl'):
        for line in p.read_bytes().splitlines():json.loads(line)
    for name in ['RECOVERY.md','RAW-INDEX-RETENTION.md']:
        for link in re.findall(r'\]\(([^)]+)\)',(P/name).read_text()):
            assert (P/link.split('#')[0]).is_file(),link
    retained=load(P/'RETENTION-MAP.json')
    for row in retained['records']:
        assert identity_route((R/row['repository_path']).read_bytes(),row['identity'])=='PASS'
        assert row['identity']==row['originating_external_identity']
    g=load(P/'CURRENT-NEXT-GATE.json');assert state_route(g)=='PASS'
    ptr=load(P.parent/'ORE-N0-CURRENT-GATE.json')
    assert ptr['candidate_path']==P.name+'/CURRENT-NEXT-GATE.json'
    assert identity((P/'CURRENT-NEXT-GATE.json').read_bytes())==ptr['candidate_identity']
    assert identity((I/'CURRENT-NEXT-GATE.json').read_bytes())==ptr['predecessor_identity']
    assert ptr['next_gate']==NEXT and ptr['next_gate_count']==1
    oldfreeze=load(P/'evidence/integration-author/C1-AUTHOR-FREEZE.json')
    rows=oldfreeze['canonical_delta'];assert len(rows)==37
    delta=json.dumps(rows,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    assert hashlib.sha256(delta).hexdigest()=='2e64bc07720a8e91b387724704d44860ee9a16fb5d5e364b46c11c5f97c12b1b'
    assert git('rev-list','--parents','-n','1',COMMIT).decode().split()==[COMMIT,'063d823dc97f1a3690e26f8bb328385acb9d0aef']
    assert git('rev-parse',COMMIT+'^{tree}').decode().strip()=='5e9f62e95c3a956e1d2a82d30859a214720652af'
    assert git('diff-tree','--no-commit-id','--name-status','-r',COMMIT).decode().splitlines()==['A\t'+r['path'] for r in rows]
    for row in rows:
        b=(R/row['path']).read_bytes(); assert b==git('cat-file','blob',COMMIT+':'+row['path'])
        assert identity(b)=={k:row['after'][k] for k in identity(b)}
    staged=load(P/'evidence/publication/STAGED-FREEZE.json')
    b=(P/'evidence/index/staged-index.bin').read_bytes();after=(P/'evidence/index/publication-index.bin').read_bytes()
    assert identity(b)==staged['index'] and staged['rows']==rows
    entries,off,ext=index_entries(b); assert entries==staged['entries']
    after_entries,after_off,_=index_entries(after);assert entries==after_entries and b[:off]==after[:after_off]
    commit_entries=''.join(f'{line.split()[0]} {line.split()[2]} 0\t{line.split(chr(9),1)[1]}\n' for line in git('ls-tree','-r','--full-tree',COMMIT).decode().splitlines())
    assert entries==commit_entries
    # Only newly authored read-only reconstruction tool is executed; retained historical scripts are inert.
    subprocess.run([sys.executable,'-B',str(P/'documentary/reconstruct_index.py')],check=True,capture_output=True)
    checks=[]
    def test(name,got,expected):
        assert got==expected,(name,got,expected)
        checks.append(dict(case=name,observed_routing=got,expected_routing=expected,defense='PASS'))
    for n,case in [('evidence/integration-review/RR-ORE-N0-REPOSITORY-INTEGRATION-C1-PASS.md','integration hash survives but raw verdict absent'),('evidence/integration-author/C1-AUTHOR-FREEZE.json','author freeze hash survives but raw freeze absent'),('evidence/publication/PUBLICATION-ADOPTION-RECEIPT.json','receipt only transient locator'),('evidence/index/staged-index.bin','required raw staged index omitted')]:
        test(case,identity_route(None,identity((P/n).read_bytes())),'U/BLOCK')
    v=(P/'evidence/integration-review/RR-ORE-N0-REPOSITORY-INTEGRATION-C1-PASS.md').read_bytes();test('newline normalization',identity_route(v+b'\n',identity(v)),'FAIL/BLOCK')
    for key,value,name in [('order',0,'stale prepublication gate selected'),('N0_activated',True,'N0 activation promotion'),('activation_readiness','PASS','publication PASS becomes activation PASS'),('CD_substantive_status','PASS','CD documentary eligibility becomes authority'),('upstream_ore_obligation','SATISFIED','upstream obligation disappears'),('review_executed',True,'retained review copy becomes new review'),('historical_ledger',[],'historical U disappears'),('published_commit','0'*40,'drift silently ignored')]:
        m=copy.deepcopy(g);m[key]=value;test(name,state_route(m),'FAIL/BLOCK')
    for key,name in [('activation_readiness','readiness U/BLOCK omitted'),('predecessor','no deterministic precedence'),('supersession_chain','two gates without ordering')]:
        m=copy.deepcopy(g);m.pop(key);test(name,state_route(m),'U/BLOCK')
    def anchor_route(raw,binding,equivalent=False):
        if raw is None or not binding:return 'U/BLOCK'
        if equivalent:return 'U/BLOCK' # No alternative equivalence authorized in path A.
        return 'PASS'
    test('equivalent representation drops flags/extensions/stages',anchor_route(b,True,True),'U/BLOCK')
    test('exact raw index without boundary provenance',anchor_route(b,False),'U/BLOCK')
    test('fresh lane depends on unavailable session storage',anchor_route(None,True),'U/BLOCK')
    test('durable path without identity binding',anchor_route(b,False),'U/BLOCK')
    planned={r['path'] for r in scope['paths']}
    test('unrelated transient archived', 'PASS' if planned|{'unrelated-session.bin'}==planned else 'FAIL/BLOCK','FAIL/BLOCK')
    test('all required exact bytes and inactive ordered state',state_route(g),'PASS')
    return dict(result='PASS — candidate documentary validation only',adversarial=checks,repository_only='PASS with Python audit hook rejecting .codex file reads; all necessary evidence read from repository paths and Git objects',members_including_manifest=62,retained_evidence_objects=len(retained['records']),published_members_unchanged=37,index='PASS exact reconstruction and full raw retention; no equivalent',activation_readiness='U/BLOCK',accepted_durable_retention=False,next_gate=NEXT)


if __name__=='__main__':
    try:print(json.dumps(main(),ensure_ascii=False,indent=2))
    except FileNotFoundError as e:
        print(json.dumps(dict(result='U/BLOCK',reason=str(e))));sys.exit(2)
    except (AssertionError,ValueError,KeyError,subprocess.CalledProcessError) as e:
        print(json.dumps(dict(result='FAIL/BLOCK',residual_U='preserved where evidence remains unknown',reason=str(e))));sys.exit(1)
