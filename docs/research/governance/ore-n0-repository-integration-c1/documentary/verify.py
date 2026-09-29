#!/usr/bin/env python3
"""Read-only integration documentary checks. No Git mutation or prospective preflight.
Temporary archive reconstruction uses tempfile outside the repository. No source code
from retained evidence is executed. External freeze authentication remains mandatory.
"""
import argparse
import base64
import hashlib
import json
import re
import tarfile
import tempfile
from pathlib import Path

P = Path(__file__).resolve().parents[1]

def identity(data):
    return dict(bytes=len(data), lf=data.count(b'\n'), terminal_LF=data.endswith(b'\n'), sha256=hashlib.sha256(data).hexdigest())

def check(data, expected):
    got = identity(data)
    assert all(got[k] == expected[k] for k in got if k in expected), ('identity mismatch', got, expected)
    return got

def load(path):
    return json.loads(path.read_bytes())

def safe(name):
    p = Path(name)
    assert not p.is_absolute() and '..' not in p.parts, ('unsafe path', name)
    return p

def gate_check(g):
    assert g['status'] == 'DRAFT-UNREVIEWED'
    assert g['N0_candidate_independently_reviewed_PASS'] is True
    for k in ['N0_established', 'N0_activated', 'prospective_preflight_executed', 'review_executed']:
        assert g[k] is False, k
    assert g['T_N0'] is None
    assert g['CD_substantive_status'].startswith('BLOCKED')
    assert g['CD_dependency_status'] == 'CD prospectively dependency-eligible'
    assert g['CD_binding']['candidate'] == 'ORE-N0-PROSPECTIVE-BOUNDARY-C6'
    assert g['CD_binding']['review'] == 'RR-ORE-N0-PROSPECTIVE-BOUNDARY-C6-PASS'
    assert g['next_gate_count'] == 1
    assert g['next_gate'] == 'FRESH INDEPENDENT HIGH-RISK REVIEW — ORE N0 REPOSITORY INTEGRATION / ADOPTION PACKAGE'
    assert g['upstream_ore_obligation'] == 'UPSTREAM ORE COMPATIBILITY / DRIFT CONTROL = REQUIRED and UNSATISFIED'

NEXT = {
    'C6': 'ORE-N0-PROSPECTIVE-BOUNDARY-C6/provenance/ORE-N0-PROSPECTIVE-BOUNDARY-C5.tar.gz',
    'C5': 'ORE-N0-PROSPECTIVE-BOUNDARY-C5/provenance/ORE-N0-PROSPECTIVE-BOUNDARY-C4.tar.gz',
    'C4': 'ORE-N0-PROSPECTIVE-BOUNDARY-C4/provenance/ORE-N0-PROSPECTIVE-BOUNDARY-C3.tar.gz',
    'C3': 'ORE-N0-PROSPECTIVE-BOUNDARY-C3/provenance/ORE-N0-PROSPECTIVE-BOUNDARY-C2-INCOMPLETE.tar.gz',
}

def verify_archive(handle, label, auth, report):
    handle.seek(0)
    observed = {}
    manifests = []
    names = set()
    child = tempfile.TemporaryFile() if label in NEXT else None
    with tarfile.open(fileobj=handle, mode='r|gz') as archive:
        for m in archive:
            safe(m.name)
            assert m.name not in names, ('duplicate archive member', m.name)
            names.add(m.name)
            assert m.isdir() or m.isfile(), ('unsupported member type', m.name)
            if m.isdir():
                continue
            f = archive.extractfile(m)
            digest = hashlib.sha256()
            size = lf = 0
            terminal = False
            chunks = [] if m.name.endswith('/freeze-manifest.json') else None
            while True:
                d = f.read(1024 * 1024)
                if not d:
                    break
                digest.update(d); size += len(d); lf += d.count(b'\n'); terminal = d.endswith(b'\n')
                if chunks is not None:
                    chunks.append(d)
                if child is not None and m.name == NEXT[label]:
                    child.write(d)
            observed[m.name] = dict(bytes=size, lf=lf, terminal_LF=terminal, sha256=digest.hexdigest(), mode=oct(m.mode))
            if chunks is not None:
                manifests.append((m.name, json.loads(b''.join(chunks))))
    expected = {r['path']: r for r in auth['members']}
    assert set(observed) == set(expected), ('archive member set', label)
    assert len(names) == auth['entries'], ('archive entries', label)
    for name, r in expected.items():
        assert observed[name] == {k: r[k] for k in observed[name]}, ('archive member', name)
    for name, manifest in manifests:
        prefix = name.rsplit('/', 1)[0] + '/'
        rows = manifest.get('files', manifest.get('members'))
        assert len({r['path'] for r in rows}) == len(rows)
        for r in rows:
            safe(r['path']); got = observed[prefix + r['path']]
            for k in ['bytes', 'lf', 'terminal_LF', 'sha256']:
                if k in r:
                    assert got[k] == r[k], (name, r['path'], k)
            if 'mode' in r:
                assert int(got['mode'], 8) == int(r['mode'], 8)
    report.append(dict(archive=label,files=len(observed),entries=len(names),manifests=[dict(path=n,listed=len(m.get('files',m.get('members')))) for n,m in manifests]))
    if child is not None:
        assert child.tell() > 0
        return child
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lineage', action='store_true', help='Authenticate all nested archive members/manifests, without executing retained code.')
    args = ap.parse_args()
    scope = load(P/'SCOPE.json')
    relroot = scope['package_root']
    declared = {r['path'][len(relroot)+1:] for r in scope['paths']}
    actual = {str(p.relative_to(P)) for p in P.rglob('*') if p.is_file()}
    assert actual == declared, ('package path mismatch', actual ^ declared)
    assert all(r['operation']=='add' and r['before'] is None and r['before_status']=='ABSENT' for r in scope['paths'])
    operations = json.dumps(scope['paths'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    assert hashlib.sha256(operations).hexdigest() == scope['canonical_intended_operations_sha256']
    members = load(P/'MEMBERS.json')['members']
    assert {r['path'] for r in members} == actual - {'MEMBERS.json'}
    for r in members:
        p=P/safe(r['path']); assert p.is_file() and not p.is_symlink()
        check(p.read_bytes(),r)
        assert (p.stat().st_mode & 0o777)==0o644
    for p in P.rglob('*.json'):
        load(p)
    mapping = load(P/'AUTHORITY-MAP.json')
    for n,r in mapping['identities'].items():
        check((P/safe(n)).read_bytes(),r)
    check((P/'evidence/C6-CANDIDATE.md').read_bytes(),dict(bytes=32281,lf=202,terminal_LF=True,sha256='a025a8b007410cbd9bc30bb5f4f95246dbeac6c2f8caa34b6ed411803936cafa'))
    verdict=(P/'evidence/C6-PASS-VERDICT.md').read_bytes()
    check(verdict,dict(bytes=18405,lf=130,terminal_LF=True,sha256='3996a05cfe2a24e3d0d88719cf51449a7dad419c55ac308e94abb6a5ce6f332e'))
    original=json.loads((P/'evidence/C6-PASS-original-record.jsonl').read_bytes())
    text=''.join(x.get('text','') for x in original['payload']['content'])
    exact=text.split('BEGIN FROZEN VERDICT\n',1)[1].split('END FROZEN VERDICT',1)[0].encode('utf-8')
    assert exact==verdict
    gate=load(P/'CURRENT-NEXT-GATE.json');gate_check(gate)
    manifest=load(P/'evidence/C6-freeze-manifest.json')
    c6rows={r['path']:r for r in manifest['files']}
    for n in ['historical-ledger.json','historical-ledger-C4-addendum.json','historical-ledger-C5-addendum.json','historical-ledger-C6-addendum.json']:
        check((P/'evidence'/n).read_bytes(),c6rows[n])
    check((P/'UPSTREAM-ORE-OBLIGATION.md').read_bytes(),c6rows['UPSTREAM-ORE-OBLIGATION.md'])
    assert len(load(P/'evidence/historical-ledger-C4-addendum.json')['historical_truth_targets'])==179
    for name in ['INTEGRATION.md','CONTINUATION.md','ACTIVATION-CONTRACT.md','RETRIEVAL.md']:
        text=(P/name).read_text()
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if '://' in target or target.startswith('#'):
                continue
            assert (P/safe(target.split('#')[0])).exists(), (name,target)
        assert 'DRAFT-UNREVIEWED' in text, name
    chunks=load(P/'evidence/archive-chunks.json')
    report=[]
    with tempfile.TemporaryFile() as joined:
        digest=hashlib.sha256();size=0
        for i,r in enumerate(chunks['parts']):
            assert r['path']==f'evidence/C6-archive/part-{i:03d}' and r['offset']==size
            d=(P/safe(r['path'])).read_bytes();check(d,r);joined.write(d);digest.update(d);size+=len(d)
        assert size==374268105
        assert digest.hexdigest()==chunks['archive_identity']['sha256']==mapping['archive']['sha256']=='bef9fdfbb7e929b058a869c4ae4b6b466e0f8d99e570e1647677fe676c2dfc12'
        if args.lineage:
            auth={x['label']:x for x in load(P/'evidence/authentication.json')}
            handle=joined
            for label in ['C6','C5','C4','C3','C2']:
                child=verify_archive(handle,label,auth[label],report)
                if handle is not joined:
                    handle.close()
                handle=child
    rejected=[]
    for key,value in [('N0_established',True),('N0_activated',True),('prospective_preflight_executed',True),('CD_substantive_status','PASS'),('upstream_ore_obligation','SATISFIED'),('next_gate_count',2)]:
        altered=dict(gate);altered[key]=value
        try:
            gate_check(altered)
        except AssertionError:
            rejected.append(key)
        else:
            raise AssertionError(('accepted invalid gate',key))
    try:
        check(verdict+b'\n',mapping['identities']['evidence/C6-PASS-VERDICT.md'])
    except AssertionError:
        rejected.append('normalized_or_changed_verdict')
    else:
        raise AssertionError('accepted modified verdict')
    print(json.dumps(dict(status='PASS author documentary checks only; not independent review or prospective preflight',package_members=len(actual),bound_by_members_manifest=len(members),archive_sha256=chunks['archive_identity']['sha256'],nested_archives=report,negative_cases_rejected=rejected,N0_established=False,N0_activated=False,prospective_preflight_executed=False,CD_executed=False),indent=2))

if __name__=='__main__':
    main()
