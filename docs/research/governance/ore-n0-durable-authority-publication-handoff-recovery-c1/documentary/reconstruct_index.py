"""Read-only exact staged-index reconstruction; never installs or writes an index."""
import pathlib,hashlib,struct
O=pathlib.Path(__file__).resolve().parents[1]/'evidence/index'
def split(b):
 assert b[:4]==b'DIRC' and hashlib.sha1(b[:-20]).digest()==b[-20:]
 ver,n=struct.unpack('>II',b[4:12]);assert ver==2;pos=12
 for _ in range(n):
  start=pos;flags=int.from_bytes(b[pos+60:pos+62]);assert not flags&0x4000
  end=b.index(b'\0',pos+62);pos=start+((end-start+1+7)//8)*8;assert b[end:pos]==b'\0'*(pos-end)
 return pos,b[pos:-20]
def invalidate(data,pos=0,prefix=''):
 nul=data.index(b'\0',pos);name=data[pos:nul];end=data.index(b'\n',nul);count,kids=map(int,data[nul+1:end].split());q=end+1+(20 if count>=0 else 0);path=prefix+name.decode();raw=data[pos:q]
 if path in {'','docs','docs/research','docs/research/governance'}:raw=name+b'\0-1 '+str(kids).encode()+b'\n'
 for _ in range(kids):child,q=invalidate(data,q,path+'/' if path else '');raw+=child
 return raw,q
before=(O/'prepublication-index.bin').read_bytes();after=(O/'publication-index.bin').read_bytes();assert hashlib.sha256(before).hexdigest()=='07d944187853f09e383860d24370e5c18052ff962e9bef5133082d739e647fc4';assert hashlib.sha256(after).hexdigest()=='ff65baf0e554bdcdaa1024c15fd6c0d8253f307db237f8f6e743f292a6c99699';off,ext=split(before);postoff,postext=split(after);assert postoff==87772;assert len(postext)==8+int.from_bytes(postext[4:8])
assert ext[:4]==postext[:4]==b'TREE' and len(ext)==8+int.from_bytes(ext[4:8]);tree,end=invalidate(ext[8:]);assert end==len(ext)-8 and len(tree)==3837
body=after[:postoff]+b'TREE'+len(tree).to_bytes(4)+tree;raw=body+hashlib.sha1(body).digest()
print(len(raw),raw.count(b'\n'),hashlib.sha256(raw).hexdigest())
assert len(raw)==91637 and raw.count(b'\n')==266 and hashlib.sha256(raw).hexdigest()=='cd15512f695b4a83efb17cc04399daff604c3dcda9fa92328dce043e8b8b7faa'
assert (O/'staged-index.bin').read_bytes()==raw
print('PASS exact raw reconstruction; no writes')
