"""Inspect previously staged data files only; never execute decoded content."""
import base64, hashlib, json, lzma
from pathlib import Path
chunks=[]
for p in sorted(Path('.import/legacy').glob('*.txt')):
    b=p.read_bytes();chunks.append(b)
    print(p.name,len(b),hashlib.sha256(b).hexdigest(),repr(b[:16]))
for label,raw in [('joined',b''.join(chunks))]+[(str(i),x) for i,x in enumerate(chunks)]:
    try:
        b=base64.b64decode(raw)
        d=lzma.LZMADecompressor();v=d.decompress(b,max_length=32000000)
        print('decode',label,len(b),len(v),'complete',d.eof)
        if d.eof:
            obj=json.loads(v)
            print('json',type(obj).__name__,len(obj))
            if isinstance(obj,dict):
                print('keys',list(obj)[:40])
                for k,x in list(obj.items())[:2]:print('sample',k,type(x).__name__,repr(x)[:500])
            if isinstance(obj,list):print('sample',repr(obj[:1])[:1000])
    except Exception as e:print('incomplete',label,type(e).__name__,str(e)[:120])
