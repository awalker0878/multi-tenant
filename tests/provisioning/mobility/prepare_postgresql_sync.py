"""Create disposable PostgreSQL17 engine fixtures, never operational authority.

The setup connection is an explicit test administrator. Each native effect test
uses a separately isolated non-administrator connection. This fixture does not
commission live worker identities, Vault roles, platform or method qualification.
"""
import os
from pathlib import Path
import re

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict,make_conninfo

PREFIX='HOSTING_TEST_POSTGRES_DATABASE_SYNC_'


def settings():
    if os.environ.get(PREFIX+'ISOLATED')!='1':
        raise ValueError('Explicit disposable database sync isolation marker required')
    values={key:os.environ[PREFIX+key+'_DSN'] for key in ('SETUP','SOURCE','TARGET','FENCE','WRITER','SOURCE_READER','TARGET_READER')}
    parsed={key:conninfo_to_dict(value) for key,value in values.items()}
    for key in ('SOURCE','TARGET','FENCE','WRITER','SOURCE_READER','TARGET_READER'):
        row=parsed[key]
        if not (re.fullmatch('hosting_test_sync_[a-z_]+',row.get('dbname',''))
                and re.fullmatch('hosting_test_sync_[a-z_]+',row.get('user',''))
                and row.get('password') and row['user']!=parsed['SETUP'].get('user')):
            raise ValueError('Disposable test database and isolated native role names required')
    if len({parsed[key]['user'] for key in ('SOURCE','TARGET','FENCE','WRITER','SOURCE_READER','TARGET_READER')})!=6:
        raise ValueError('Separate source, target, fence and application test roles required')
    if (parsed['SOURCE']['dbname']==parsed['TARGET']['dbname'] or any(
            parsed[key]['dbname']!=parsed['SOURCE']['dbname'] for key in ('FENCE','WRITER','SOURCE_READER'))
            or parsed['TARGET_READER']['dbname']!=parsed['TARGET']['dbname']):
        raise ValueError('Separate disposable source/target databases required')
    return values,parsed


def native_admin(dsn,database):
    return psycopg.connect(make_conninfo(dsn,dbname=database),autocommit=True)


def owner_role(parsed,key):
    """Private non-login native owner behind each isolated fixture login."""
    return parsed[key]['user']+'_owner'


def helper_role(parsed,key):return parsed[key]['user']+'_helper'


def main():
    values,parsed=settings()
    with psycopg.connect(values['SETUP'],autocommit=True) as admin:
        if not admin.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user').fetchone()[0]:
            raise ValueError('Only the disposable fixture setup administrator may provision roles')
        version,wal,slots,senders=admin.execute("SELECT current_setting('server_version_num')::int,current_setting('wal_level'),current_setting('max_replication_slots')::int,current_setting('max_wal_senders')::int").fetchone()
        if not (170000<=version<180000 and wal=='logical' and slots>=16 and senders>=16):
            raise ValueError('PostgreSQL17 fixture requires logical WAL and at least sixteen slots/senders')
        for key in ('SOURCE','TARGET'):
            db=sql.Identifier(parsed[key]['dbname'])
            admin.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(db))
            admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0 ENCODING {}').format(db,sql.Literal('UTF8')))
            admin.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(db))
        for key in ('SOURCE','TARGET','FENCE','WRITER','SOURCE_READER','TARGET_READER'):
            row=parsed[key];name=sql.Identifier(row['user'])
            exists=admin.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(row['user'],)).fetchone()
            command='ALTER ROLE' if exists else 'CREATE ROLE'
            admin.execute(sql.SQL(command+' {} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB {} PASSWORD {}').format(
                name,sql.SQL('REPLICATION' if key=='SOURCE' else 'NOREPLICATION'),sql.Literal(row['password'])))
            admin.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(row['dbname']),name))
            if key!='WRITER':
                owner=owner_role(parsed,key)
                exists=admin.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(owner,)).fetchone()
                command='ALTER ROLE' if exists else 'CREATE ROLE'
                admin.execute(sql.SQL(command+' {} NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB {}').format(
                    sql.Identifier(owner),sql.SQL('REPLICATION' if key=='SOURCE' else 'NOREPLICATION')))
                admin.execute(sql.SQL('GRANT {} TO {} WITH INHERIT FALSE,SET TRUE,ADMIN FALSE').format(sql.Identifier(owner),name))
        for key in ('SOURCE','TARGET'):
            admin.execute(sql.SQL('GRANT CREATE ON DATABASE {} TO {}').format(
                sql.Identifier(parsed[key]['dbname']),sql.Identifier(owner_role(parsed,key))))
        admin.execute(sql.SQL('GRANT pg_create_subscription TO {}').format(sql.Identifier(owner_role(parsed,'TARGET'))))
        for key in ('SOURCE','TARGET'):
            helper=helper_role(parsed,key)
            exists=admin.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(helper,)).fetchone()
            command='ALTER ROLE' if exists else 'CREATE ROLE'
            admin.execute(sql.SQL(command+' {} NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB {} {}').format(sql.Identifier(helper),
                sql.SQL('CREATEROLE' if key=='SOURCE' else 'NOCREATEROLE'),sql.SQL('REPLICATION' if key=='SOURCE' else 'NOREPLICATION')))
            admin.execute(sql.SQL('GRANT pg_read_all_settings TO {}').format(sql.Identifier(helper)))
            if key=='SOURCE':
                admin.execute(sql.SQL('GRANT pg_signal_backend TO {}').format(sql.Identifier(helper)))
                admin.execute(sql.SQL('GRANT {} TO {} WITH ADMIN TRUE,INHERIT FALSE,SET FALSE').format(
                    sql.Identifier(parsed['WRITER']['user']),sql.Identifier(helper)))
    migration=Path(__file__).resolve().parents[3]/'provisioner/controlplane/persistence/migrations/0033_postgresql_sync_journal.sql'
    for key in ('SOURCE','TARGET'):
        with native_admin(values['SETUP'],parsed[key]['dbname']) as admin:
            admin.execute(migration.read_text())
            helper=sql.Identifier(helper_role(parsed,key))
            for name in ('streams','commits','writer_fences','source_streams'):
                admin.execute(sql.SQL('ALTER TABLE hosting_sync.{} OWNER TO {}').format(sql.Identifier(name),helper))
            for name,arguments in {'immutable':'','current_fence':'text,text','fence_application_writers':'text,text',
                'inspect_writer_fence':'text,text','current_stream':'text','record_commit':'text,text,text,text,text',
                'inspect_commit':'text,text','inspect_subscription':'text','peek_source':'text,text','inspect_directory':'text,text'}.items():
                admin.execute(sql.SQL('ALTER FUNCTION hosting_sync.{}({}) OWNER TO {}').format(
                    sql.Identifier(name),sql.SQL(arguments),helper))
            admin.execute(sql.SQL('ALTER SCHEMA hosting_sync OWNER TO {}').format(helper))
            admin.execute(sql.SQL('GRANT SELECT(subenabled,subslotname,subpublications,subbinary,substream,subtwophasestate,subdisableonerr,subpasswordrequired,subrunasowner,suborigin,subfailover,subskiplsn,subconninfo,subowner,oid,subdbid,subname) ON pg_catalog.pg_subscription TO {}').format(helper))
            owner=sql.Identifier(owner_role(parsed,key))
            reader=sql.Identifier(owner_role(parsed,key+'_READER'))
            admin.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            admin.execute(sql.SQL('GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO {}').format(owner))
            admin.execute(sql.SQL('GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO {}').format(reader))
            admin.execute(sql.SQL('GRANT USAGE ON SCHEMA hosting_sync TO {}').format(owner))
            admin.execute(sql.SQL('GRANT USAGE ON SCHEMA hosting_sync TO {}').format(reader))
            admin.execute(sql.SQL('GRANT EXECUTE ON FUNCTION hosting_sync.inspect_directory(text,text) TO {}').format(reader))
            if key=='TARGET':
                admin.execute(sql.SQL('GRANT EXECUTE ON FUNCTION hosting_sync.record_commit(text,text,text,text,text),hosting_sync.inspect_commit(text,text),hosting_sync.inspect_subscription(text) TO {}').format(owner))
                admin.execute(sql.SQL('GRANT EXECUTE ON FUNCTION hosting_sync.inspect_commit(text,text),hosting_sync.inspect_subscription(text) TO {}').format(reader))
            else:
                fencer=sql.Identifier(owner_role(parsed,'FENCE'))
                admin.execute(sql.SQL('GRANT USAGE ON SCHEMA hosting_sync TO {}').format(fencer))
                admin.execute(sql.SQL('GRANT EXECUTE ON FUNCTION hosting_sync.fence_application_writers(text,text),hosting_sync.inspect_writer_fence(text,text) TO {}').format(fencer))
                admin.execute(sql.SQL('GRANT EXECUTE ON FUNCTION hosting_sync.peek_source(text,text) TO {}').format(reader))
    print('Disposable PostgreSQL17 native engine roles and private helpers prepared')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
