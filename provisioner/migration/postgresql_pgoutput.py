"""Bounded PostgreSQL17 pgoutput v1 decoding; no SQL or credential authority."""
from dataclasses import dataclass
import hashlib
import struct

from provisioner.execution.run_files import require

SUPPORTED_TYPES=frozenset({16,20,21,23,25,1700,2950})
UNCHANGED={'unchangedToast':True}


def lsn(number):
    require(type(number) is int and 0<=number<2**64,'Invalid PostgreSQL WAL position')
    return f'{number>>32:X}/{number&0xffffffff:X}'


def lsn_number(value):
    import re
    require(isinstance(value,str) and re.fullmatch('[0-9A-F]{1,8}/[0-9A-F]{1,8}',value),
            'Canonical PostgreSQL WAL position required')
    high,low=(int(part,16) for part in value.split('/'));return (high<<32)|low


class _Reader:
    def __init__(self,raw):
        require(isinstance(raw,bytes) and 1<=len(raw)<=4*1024*1024,'Bounded original pgoutput message required')
        self.raw=raw;self.position=0
    def take(self,size):
        require(0<=size<=len(self.raw)-self.position,'Truncated pgoutput message')
        result=self.raw[self.position:self.position+size];self.position+=size;return result
    def byte(self):return self.take(1)
    def integer(self,size):return int.from_bytes(self.take(size),'big',signed=False)
    def string(self):
        end=self.raw.find(b'\0',self.position)
        require(end>=self.position and end-self.position<=63,'Invalid pgoutput relation identifier')
        result=self.take(end-self.position).decode('utf-8');self.take(1);return result
    def tuple(self,count):
        require(self.integer(2)==count,'pgoutput column count changed')
        values=[]
        for _ in range(count):
            kind=self.byte()
            if kind==b'n':values.append(None)
            elif kind==b'u':values.append(UNCHANGED)
            else:
                require(kind==b't','Only selected text-format pgoutput is supported')
                size=self.integer(4);require(size<=1024*1024,'pgoutput field exceeds the selected bound')
                values.append(self.take(size).decode('utf-8'))
        return values
    def finish(self):require(self.position==len(self.raw),'Trailing pgoutput message bytes')


@dataclass(frozen=True)
class PgTransaction:
    xid:int
    commit_lsn:str
    end_lsn:str
    operations:tuple
    digest:str


def decode_transactions(rows,tables,*,max_changes=1000,max_bytes=4*1024*1024):
    """Decode whole committed source transactions without consuming their slot.

    Unsupported origins, streaming, two-phase work, schema changes, binary values,
    partial transactions and excess bounds refuse all apply. Relations are checked
    against the originally selected typed columns and primary key.
    """
    require(type(max_changes) is int and 1<=max_changes<=1000 and type(max_bytes) is int
            and 1<=max_bytes<=4*1024*1024,'Finite selected pgoutput batch required')
    selected={(row['schema'],row['name']):row for row in tables};relations={}
    current=None;operations=[];transactions=[];retained=[];total=0;changes=0;last=0
    for row in rows:
        require(isinstance(row,(list,tuple)) and len(row)==3 and isinstance(row[2],(bytes,memoryview)),
                'Original native pgoutput bytes required')
        raw=bytes(row[2]);total+=len(raw)
        require(total<=max_bytes,'Original pgoutput batch exceeds its byte ceiling')
        r=_Reader(raw);kind=r.byte()
        if kind==b'B':
            require(current is None,'Nested pgoutput transaction')
            begin=r.integer(8);stamp=r.integer(8);current=(r.integer(4),begin,stamp)
            operations=[];retained=[raw]
        elif kind==b'R':
            native_id=r.integer(4);schema=r.string();name=r.string();identity=r.byte();count=r.integer(2)
            table=selected.get((schema,name));require(table is not None and identity==b'd','Unselected table or replica identity')
            columns=[]
            for _ in range(count):
                flag=r.integer(1);column=r.string();oid=r.integer(4);modifier=struct.unpack('!i',r.take(4))[0]
                require(flag in (0,1),'Unsupported pgoutput column flag')
                columns.append({'name':column,'typeOid':oid,'typeModifier':modifier,'key':flag==1})
            require(columns==[{key:column[key] for key in ('name','typeOid','typeModifier','key')}
                              for column in table['columns']],'Original pgoutput table columns changed')
            relations[native_id]=table
            if current is not None:retained.append(raw)
        elif kind in (b'I',b'U',b'D'):
            require(current is not None,'pgoutput mutation outside a committed transaction')
            table=relations.get(r.integer(4));require(table is not None,'Missing exact pgoutput relation')
            marker=r.byte();old=None;new=None
            if kind==b'I':
                require(marker==b'N','Invalid insert tuple');new=r.tuple(len(table['columns']))
            else:
                if marker==b'K':old=r.tuple(len(table['columns']))
                else:require(kind==b'U' and marker==b'N','Only exact primary-key replica identity supported')
                if kind==b'U':
                    if old is not None:require(r.byte()==b'N','Missing update tuple')
                    new=r.tuple(len(table['columns']))
            values=old if old is not None else new
            require(all(values[index] is not None and values[index]!=UNCHANGED
                        for index,column in enumerate(table['columns']) if column['key']),
                    'An exact source primary key is required')
            if kind==b'I':require(UNCHANGED not in new,'Insert cannot omit a TOAST value')
            operations.append({'kind':kind.decode(),'schema':table['schema'],'table':table['name'],'old':old,'new':new})
            changes+=1;require(changes<=max_changes,'Source transaction exceeds the selected change ceiling');retained.append(raw)
        elif kind==b'T':
            require(current is not None,'pgoutput truncate outside transaction')
            count=r.integer(4);require(1<=count<=len(tables) and r.integer(1)==0,'Unselected truncate semantics')
            chosen=[]
            for _ in range(count):
                table=relations.get(r.integer(4));require(table is not None,'Unselected truncate relation')
                chosen.append([table['schema'],table['name']])
            require(len({tuple(value) for value in chosen})==len(chosen),'Repeated truncate relation')
            operations.append({'kind':'T','tables':chosen});changes+=count
            require(changes<=max_changes,'Source transaction exceeds its change ceiling');retained.append(raw)
        elif kind==b'C':
            require(current is not None and r.integer(1)==0,'Unexpected pgoutput commit')
            commit,end,stamp=r.integer(8),r.integer(8),r.integer(8)
            require(current[1]==commit and current[2]==stamp and last<commit<end,'Source commit order changed')
            retained.append(raw);sha=hashlib.sha256(b''.join(len(value).to_bytes(4,'big')+value for value in retained)).hexdigest()
            transactions.append(PgTransaction(current[0],lsn(commit),lsn(end),tuple(operations),sha));last=commit;current=None
        else:raise ValueError('Unsupported pgoutput message; no mutation is authorized')
        r.finish()
    require(current is None,'Source transaction is incomplete; no partial apply')
    return tuple(transactions)
