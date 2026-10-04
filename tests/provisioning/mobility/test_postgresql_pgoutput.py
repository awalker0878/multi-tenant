"""Wire-level PostgreSQL17 decoding limits and whole-transaction semantics."""
import copy
import struct
import unittest

from provisioner.migration.postgresql_pgoutput import decode_transactions,lsn,lsn_number,UNCHANGED

TABLE={'schema':'app','name':'accounts','columns':[
    {'name':'id','typeOid':23,'typeModifier':-1,'key':True,'notNull':True},
    {'name':'body','typeOid':25,'typeModifier':-1,'key':False,'notNull':False}]}


def relation(table=TABLE,identity=b'd'):
    parts=[b'R',struct.pack('!I',41),table['schema'].encode()+b'\0',table['name'].encode()+b'\0',identity,
           struct.pack('!H',len(table['columns']))]
    for column in table['columns']:
        parts.extend([bytes([int(column['key'])]),column['name'].encode()+b'\0',struct.pack('!Ii',column['typeOid'],column['typeModifier'])])
    return b''.join(parts)


def values(*fields):
    result=struct.pack('!H',len(fields))
    for value in fields:
        if value is None:result+=b'n'
        elif value==UNCHANGED:result+=b'u'
        else:
            raw=value.encode();result+=b't'+struct.pack('!I',len(raw))+raw
    return result


def transaction(*mutations,point=100,xid=7,relation_message=None):
    rows=[b'B'+struct.pack('!QQI',point,1234,xid),relation() if relation_message is None else relation_message,*mutations,
          b'C'+struct.pack('!BQQQ',0,point,point+10,1234)]
    return [('0/64',xid,row) for row in rows]


class PgoutputTests(unittest.TestCase):
    def test_committed_insert_update_key_change_delete_and_null(self):
        inserts=b'I'+struct.pack('!I',41)+b'N'+values('1','snow ☃')
        update=b'U'+struct.pack('!I',41)+b'K'+values('1',None)+b'N'+values('2',None)
        delete=b'D'+struct.pack('!I',41)+b'K'+values('2',None)
        result=decode_transactions(transaction(inserts,update,delete),[TABLE])
        self.assertEqual(len(result),1);self.assertEqual((result[0].xid,result[0].commit_lsn,result[0].end_lsn),(7,'0/64','0/6E'))
        self.assertEqual([value['kind'] for value in result[0].operations],['I','U','D'])
        self.assertEqual(result[0].operations[1]['old'],['1',None]);self.assertEqual(result[0].operations[1]['new'],['2',None])
        self.assertEqual(len(result[0].digest),64)

    def test_unchanged_toast_update_preserves_value(self):
        mutation=b'U'+struct.pack('!I',41)+b'N'+values('1',UNCHANGED)
        self.assertEqual(decode_transactions(transaction(mutation),[TABLE])[0].operations[0]['new'],['1',UNCHANGED])

    def test_complete_multiple_transactions_and_selected_truncate(self):
        truncate=b'T'+struct.pack('!IBI',1,0,41)
        result=decode_transactions(transaction(truncate)+transaction(point=200,xid=8),[TABLE])
        self.assertEqual(result[0].operations,({'kind':'T','tables':[['app','accounts']]},))
        self.assertEqual(result[1].operations,())

    def test_partial_or_unknown_messages_refuse_every_transaction(self):
        inserts=b'I'+struct.pack('!I',41)+b'N'+values('1','data')
        for rows in (transaction(inserts)[:-1],transaction(inserts)+[('0/70',1,b'O'+b'\0'*20)],
                     transaction(inserts)+transaction(inserts,point=100),transaction(inserts)[:1]*2):
            with self.subTest(rows=rows),self.assertRaises(ValueError):decode_transactions(rows,[TABLE])

    def test_native_schema_changed_full_identity_or_binary_refused(self):
        changed=copy.deepcopy(TABLE);changed['columns'][1]['typeOid']=23
        for message in (relation(changed),relation(identity=b'f'),relation()+b'!',b'R\0'):
            with self.subTest(message=message),self.assertRaises(ValueError):decode_transactions(transaction(relation_message=message),[TABLE])
        binary=b'I'+struct.pack('!I',41)+b'N'+struct.pack('!H',2)+b'b'+struct.pack('!I',1)+b'1'+b'n'
        with self.assertRaises(ValueError):decode_transactions(transaction(binary),[TABLE])

    def test_no_primary_key_insert_toast_and_truncate_cascade_refused(self):
        for mutation in (b'I'+struct.pack('!I',41)+b'N'+values(None,'data'),
                         b'I'+struct.pack('!I',41)+b'N'+values('1',UNCHANGED),
                         b'T'+struct.pack('!IBI',1,1,41)):
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):decode_transactions(transaction(mutation),[TABLE])

    def test_actual_wire_byte_and_change_ceiling_precedes_apply(self):
        inserts=b'I'+struct.pack('!I',41)+b'N'+values('1','data')
        for limits in ({'max_changes':1},{'max_bytes':10}):
            with self.subTest(limits=limits),self.assertRaises(ValueError):decode_transactions(transaction(inserts,inserts),[TABLE],**limits)

    def test_lsn_bounds_and_canonical_positions(self):
        for value in (0,2**32,2**64-1):self.assertEqual(lsn_number(lsn(value)),value)
        for value in ('0/ff','0/G','0/100000000','',None):
            with self.subTest(value=value),self.assertRaises(ValueError):lsn_number(value)


if __name__=='__main__':unittest.main()
