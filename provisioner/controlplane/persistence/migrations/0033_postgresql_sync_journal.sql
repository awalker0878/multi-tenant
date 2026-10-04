-- Installed both by the control-plane migrator and, independently, the selected
-- native PostgreSQL17 database commissioner. No operational login is elevated.
-- Native target commits are atomic with the selected application table effects.
CREATE SCHEMA hosting_sync;
REVOKE ALL ON SCHEMA hosting_sync FROM PUBLIC;
CREATE TABLE hosting_sync.streams (
    stream_id text PRIMARY KEY CHECK(stream_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    dataset_id text NOT NULL,
    selection_digest text NOT NULL CHECK(selection_digest ~ '^[0-9a-f]{64}$'),
    login_role text NOT NULL CHECK(login_role ~ '^[a-z][a-z0-9_]{0,62}$'),
    read_role text NOT NULL CHECK(read_role ~ '^[a-z][a-z0-9_]{0,62}$' AND read_role<>login_role),
    subscription_name text NOT NULL CHECK(subscription_name ~ '^[a-z][a-z0-9_]{0,62}$'),
    enabled boolean NOT NULL DEFAULT false,
    valid_until timestamptz NOT NULL
);
CREATE TABLE hosting_sync.source_streams (
    stream_id text PRIMARY KEY,
    dataset_id text NOT NULL,
    selection_digest text NOT NULL CHECK(selection_digest ~ '^[0-9a-f]{64}$'),
    read_role text NOT NULL CHECK(read_role ~ '^[a-z][a-z0-9_]{0,62}$'),
    publication_name text NOT NULL CHECK(publication_name ~ '^[a-z][a-z0-9_]{0,62}$'),
    slot_name text NOT NULL CHECK(slot_name ~ '^[a-z][a-z0-9_]{0,62}$'),
    max_rows integer NOT NULL CHECK(max_rows BETWEEN 1 AND 1000),
    max_bytes integer NOT NULL CHECK(max_bytes BETWEEN 1 AND 4194304),
    enabled boolean NOT NULL DEFAULT false,
    valid_until timestamptz NOT NULL
);
CREATE TABLE hosting_sync.commits (
    stream_id text NOT NULL REFERENCES hosting_sync.streams ON DELETE RESTRICT,
    end_lsn pg_lsn NOT NULL,
    transaction_digest text NOT NULL CHECK(transaction_digest ~ '^[0-9a-f]{64}$'),
    selection_digest text NOT NULL CHECK(selection_digest ~ '^[0-9a-f]{64}$'),
    kind text NOT NULL CHECK(kind IN ('INITIAL','INCREMENTAL')),
    committed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(stream_id,end_lsn)
);
CREATE TABLE hosting_sync.writer_fences (
    stream_id text PRIMARY KEY CHECK(stream_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    dataset_id text NOT NULL,
    selection_digest text NOT NULL CHECK(selection_digest ~ '^[0-9a-f]{64}$'),
    fence_role text NOT NULL CHECK(fence_role ~ '^[a-z][a-z0-9_]{0,62}$'),
    writer_roles text[] NOT NULL CHECK(cardinality(writer_roles) BETWEEN 1 AND 16),
    enabled boolean NOT NULL DEFAULT false,
    valid_until timestamptz NOT NULL
);
CREATE FUNCTION hosting_sync.immutable() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,hosting_sync AS $$
BEGIN
    IF TG_TABLE_NAME IN ('streams','writer_fences','source_streams') AND TG_OP='UPDATE' AND
        (to_jsonb(NEW)-'enabled') IS NOT DISTINCT FROM (to_jsonb(OLD)-'enabled') THEN RETURN NEW; END IF;
    RAISE EXCEPTION 'Original database synchronization identity is immutable' USING ERRCODE='23514';
END; $$;
CREATE TRIGGER streams_identity BEFORE UPDATE OR DELETE ON hosting_sync.streams FOR EACH ROW EXECUTE FUNCTION hosting_sync.immutable();
CREATE TRIGGER commits_identity BEFORE UPDATE OR DELETE ON hosting_sync.commits FOR EACH ROW EXECUTE FUNCTION hosting_sync.immutable();
CREATE TRIGGER fences_identity BEFORE UPDATE OR DELETE ON hosting_sync.writer_fences FOR EACH ROW EXECUTE FUNCTION hosting_sync.immutable();
CREATE TRIGGER source_identity BEFORE UPDATE OR DELETE ON hosting_sync.source_streams FOR EACH ROW EXECUTE FUNCTION hosting_sync.immutable();
DO $$ DECLARE t text; BEGIN
    FOREACH t IN ARRAY ARRAY['streams','commits','writer_fences','source_streams'] LOOP
        EXECUTE format('REVOKE ALL ON hosting_sync.%I FROM PUBLIC',t);
        EXECUTE format('ALTER TABLE hosting_sync.%I ENABLE ROW LEVEL SECURITY',t);
        EXECUTE format('ALTER TABLE hosting_sync.%I FORCE ROW LEVEL SECURITY',t);
        EXECUTE format('CREATE POLICY native_sync_owner ON hosting_sync.%I USING(current_user=pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid=%L::regclass))) WITH CHECK(current_user=pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid=%L::regclass)))',t,'hosting_sync.'||t,'hosting_sync.'||t);
    END LOOP;
END; $$;
CREATE FUNCTION hosting_sync.current_fence(stream text,selection_digest text) RETURNS hosting_sync.writer_fences
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_sync AS $$
DECLARE original hosting_sync.writer_fences%ROWTYPE; role_name text; native_role record;
BEGIN
    SELECT * INTO original FROM hosting_sync.writer_fences WHERE stream_id=stream FOR SHARE;
    IF NOT FOUND OR NOT original.enabled OR original.valid_until<=clock_timestamp()
        OR original.selection_digest IS DISTINCT FROM selection_digest
        OR current_setting('role') IS DISTINCT FROM original.fence_role
        OR NOT pg_has_role(session_user,original.fence_role,'SET')
        OR cardinality(original.writer_roles)<>(SELECT count(DISTINCT r) FROM unnest(original.writer_roles) r) THEN
        RAISE EXCEPTION 'Current exact commissioned database fence owner unavailable' USING ERRCODE='42501';
    END IF;
    FOREACH role_name IN ARRAY original.writer_roles LOOP
        SELECT * INTO native_role FROM pg_roles WHERE rolname=role_name;
        IF NOT FOUND OR role_name !~ '^[a-z][a-z0-9_]{0,62}$' OR role_name=original.fence_role
            OR native_role.rolsuper OR native_role.rolbypassrls OR native_role.rolcreaterole
            OR native_role.rolcreatedb OR native_role.rolreplication
            OR EXISTS(SELECT 1 FROM pg_auth_members WHERE member=native_role.oid
                OR (roleid=native_role.oid AND NOT(member=(SELECT oid FROM pg_roles WHERE rolname=current_user)
                    AND admin_option AND NOT inherit_option AND NOT set_option)))
            OR EXISTS(SELECT 1 FROM pg_database WHERE datdba=native_role.oid) THEN
            RAISE EXCEPTION 'Application writer has privileged or delegated native authority' USING ERRCODE='42501';
        END IF;
    END LOOP;
    RETURN original;
END; $$;
CREATE FUNCTION hosting_sync.fence_application_writers(stream text,selection_digest text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_sync AS $$
DECLARE original hosting_sync.writer_fences%ROWTYPE; role_name text; backend record;
BEGIN
    original:=hosting_sync.current_fence(stream,selection_digest);
    IF EXISTS(SELECT 1 FROM pg_prepared_xacts WHERE database=current_database()) THEN
        RAISE EXCEPTION 'Prepared transactions have no independently contained outcome' USING ERRCODE='55000';
    END IF;
    -- A committed native NOLOGIN rule blocks restart of these exact approved
    -- application clients. PostgreSQL remains running for the owned CDC reader.
    FOREACH role_name IN ARRAY original.writer_roles LOOP
        EXECUTE format('ALTER ROLE %I NOLOGIN',role_name);
    END LOOP;
    FOR backend IN SELECT pid FROM pg_stat_activity WHERE datname=current_database()
        AND usename=ANY(original.writer_roles) AND pid<>pg_backend_pid() LOOP
        IF NOT pg_terminate_backend(backend.pid,1000) THEN
            RAISE EXCEPTION 'Original database application backend remains active' USING ERRCODE='55000';
        END IF;
    END LOOP;
    PERFORM pg_stat_clear_snapshot();
    IF EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND usename=ANY(original.writer_roles))
        OR EXISTS(SELECT 1 FROM pg_prepared_xacts WHERE database=current_database()) THEN
        RAISE EXCEPTION 'Database writer or prepared transaction remains uncontained' USING ERRCODE='55000';
    END IF;
    RETURN jsonb_build_object('state','SELECTED_APPLICATION_WRITERS_FENCED','writerRoles',original.writer_roles,
        'applicationLoginAllowed',false,'activeApplicationSessions',0,'preparedTransactions',0,
        'databaseRunning',true,'datasetId',original.dataset_id,'selectionDigest',original.selection_digest);
END; $$;
CREATE FUNCTION hosting_sync.inspect_writer_fence(stream text,selection_digest text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_sync AS $$
DECLARE original hosting_sync.writer_fences%ROWTYPE; active_sessions integer; login_count integer; prepared integer;
BEGIN
    original:=hosting_sync.current_fence(stream,selection_digest);
    SELECT count(*) INTO active_sessions FROM pg_stat_activity WHERE datname=current_database() AND usename=ANY(original.writer_roles);
    SELECT count(*) INTO login_count FROM pg_roles WHERE rolname=ANY(original.writer_roles) AND rolcanlogin;
    SELECT count(*) INTO prepared FROM pg_prepared_xacts WHERE database=current_database();
    RETURN jsonb_build_object('state',CASE WHEN active_sessions=0 AND login_count=0 AND prepared=0
        THEN 'SELECTED_APPLICATION_WRITERS_FENCED' ELSE 'WRITER_EXCLUSION_UNKNOWN' END,
        'writerRoles',original.writer_roles,'applicationLoginAllowed',login_count<>0,
        'activeApplicationSessions',active_sessions,'preparedTransactions',prepared,'databaseRunning',true,
        'datasetId',original.dataset_id,'selectionDigest',original.selection_digest);
END; $$;
CREATE FUNCTION hosting_sync.current_stream(stream text) RETURNS hosting_sync.streams
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_sync AS $$
DECLARE original hosting_sync.streams%ROWTYPE;
BEGIN
    SELECT * INTO original FROM hosting_sync.streams WHERE stream_id=stream FOR SHARE;
    IF NOT FOUND OR NOT original.enabled OR original.valid_until<=clock_timestamp()
        OR current_setting('role') NOT IN (original.login_role,original.read_role)
        OR NOT pg_has_role(session_user,current_setting('role'),'SET') THEN
        RAISE EXCEPTION 'Current exact native stream owner is unavailable' USING ERRCODE='42501';
    END IF;
    RETURN original;
END; $$;
CREATE FUNCTION hosting_sync.record_commit(stream text,position text,transaction_digest text,selection_digest text,kind text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_sync AS $$
DECLARE original hosting_sync.streams%ROWTYPE;
BEGIN
    original:=hosting_sync.current_stream(stream);
    IF current_setting('role') IS DISTINCT FROM original.login_role
        OR original.selection_digest IS DISTINCT FROM selection_digest OR transaction_digest IS NULL
        OR transaction_digest !~ '^[0-9a-f]{64}$' OR kind IS NULL OR kind NOT IN ('INITIAL','INCREMENTAL')
        OR position IS NULL OR position !~ '^[0-9A-F]{1,8}/[0-9A-F]{1,8}$' THEN
        RAISE EXCEPTION 'Exact original committed transaction is required' USING ERRCODE='23514';
    END IF;
    INSERT INTO hosting_sync.commits(stream_id,end_lsn,transaction_digest,selection_digest,kind)
        VALUES(stream,position::pg_lsn,transaction_digest,selection_digest,kind);
    RETURN 'COMMIT_RECORDED';
END; $$;
CREATE FUNCTION hosting_sync.inspect_commit(stream text,position text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_sync AS $$
DECLARE original hosting_sync.streams%ROWTYPE; result jsonb;
BEGIN
    original:=hosting_sync.current_stream(stream);
    SELECT jsonb_build_object('transactionDigest',c.transaction_digest,'selectionDigest',c.selection_digest,
        'kind',c.kind,'recordedAt',c.committed_at) INTO result FROM hosting_sync.commits c
        WHERE c.stream_id=stream AND c.end_lsn=position::pg_lsn;
    RETURN result;
END; $$;
CREATE FUNCTION hosting_sync.inspect_subscription(stream text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_sync AS $$
DECLARE original hosting_sync.streams%ROWTYPE; result jsonb;
BEGIN
    original:=hosting_sync.current_stream(stream);
    -- No operational login receives the secret-bearing subconninfo column.
    -- The independently commissioned owner returns only this stream's boolean
    -- empty-connection predicate and fixed nonsecret subscription metadata.
    SELECT jsonb_build_array(subenabled,subslotname,subpublications,subbinary,substream,subtwophasestate,
        subdisableonerr,subpasswordrequired,subrunasowner,suborigin,subfailover,subskiplsn::text,
        subconninfo='',pg_get_userbyid(subowner),oid::bigint) INTO result FROM pg_subscription
        WHERE subdbid=(SELECT oid FROM pg_database WHERE datname=current_database())
        AND subname=original.subscription_name;
    RETURN result;
END; $$;
REVOKE ALL ON FUNCTION hosting_sync.immutable() FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_sync.current_stream(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_sync.record_commit(text,text,text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_sync.inspect_commit(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_sync.inspect_subscription(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_sync.current_fence(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_sync.fence_application_writers(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_sync.inspect_writer_fence(text,text) FROM PUBLIC;

CREATE FUNCTION hosting_sync.peek_source(stream text,selection_digest text)
RETURNS TABLE(position text,transaction_id xid,message bytea)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_sync AS $$
DECLARE original hosting_sync.source_streams%ROWTYPE;
BEGIN
    SELECT * INTO original FROM hosting_sync.source_streams WHERE stream_id=stream FOR SHARE;
    IF NOT FOUND OR NOT original.enabled OR original.valid_until<=clock_timestamp()
        OR original.selection_digest IS DISTINCT FROM selection_digest
        OR current_setting('role') IS DISTINCT FROM original.read_role
        OR NOT pg_has_role(session_user,original.read_role,'SET') THEN
        RAISE EXCEPTION 'Current independently enrolled selected source reader unavailable' USING ERRCODE='42501';
    END IF;
    RETURN QUERY SELECT lsn::text,xid,CASE WHEN sum(octet_length(data)) OVER()<=original.max_bytes THEN data ELSE NULL END
        FROM (SELECT * FROM pg_logical_slot_peek_binary_changes(original.slot_name,NULL,original.max_rows,
            'proto_version','1','publication_names',original.publication_name,'binary','false','messages','false',
            'streaming','false','two_phase','false') LIMIT original.max_rows*4+65) bounded;
END; $$;
REVOKE ALL ON FUNCTION hosting_sync.peek_source(text,text) FROM PUBLIC;
CREATE FUNCTION hosting_sync.inspect_directory(stream text,selection_digest text) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_sync AS $$
DECLARE authorized boolean;
BEGIN
    SELECT EXISTS(SELECT 1 FROM hosting_sync.source_streams s WHERE s.stream_id=stream
        AND s.selection_digest=inspect_directory.selection_digest AND s.enabled AND s.valid_until>clock_timestamp()
        AND current_setting('role')=s.read_role AND pg_has_role(session_user,s.read_role,'SET'))
        OR EXISTS(SELECT 1 FROM hosting_sync.streams s WHERE s.stream_id=stream
        AND s.selection_digest=inspect_directory.selection_digest AND s.enabled AND s.valid_until>clock_timestamp()
        AND current_setting('role')=s.read_role AND pg_has_role(session_user,s.read_role,'SET')) INTO authorized;
    IF NOT authorized THEN RAISE EXCEPTION 'The exact current directory observer is unavailable' USING ERRCODE='42501'; END IF;
    RETURN current_setting('data_directory');
END; $$;
REVOKE ALL ON FUNCTION hosting_sync.inspect_directory(text,text) FROM PUBLIC;

-- Standalone native databases have no hosting_controlplane schema. The same
-- packaged revision adds only original B10 credential custody closure when
-- installed by the actual control-plane migration owner.
DO $$ BEGIN
    IF to_regnamespace('hosting_controlplane') IS NOT NULL THEN
        CREATE TABLE hosting_controlplane.native_credential_issuance_closures (
            organization_id text NOT NULL,
            tenant_id text NOT NULL,
            grant_id text NOT NULL,
            operation_id text NOT NULL,
            selection_digest text NOT NULL CHECK(selection_digest ~ '^[0-9a-f]{64}$'),
            closed_by text NOT NULL,
            closed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            PRIMARY KEY(organization_id,tenant_id,grant_id),
            FOREIGN KEY(organization_id,tenant_id,grant_id)
                REFERENCES hosting_controlplane.worker_grants(organization_id,tenant_id,grant_id) ON DELETE RESTRICT
        );
        REVOKE ALL ON hosting_controlplane.native_credential_issuance_closures FROM PUBLIC;
        ALTER TABLE hosting_controlplane.native_credential_issuance_closures ENABLE ROW LEVEL SECURITY;
        ALTER TABLE hosting_controlplane.native_credential_issuance_closures FORCE ROW LEVEL SECURITY;
        CREATE POLICY credential_closure_tenant ON hosting_controlplane.native_credential_issuance_closures
            USING(organization_id=current_setting('app.organization_id',true) AND tenant_id=current_setting('app.tenant_id',true))
            WITH CHECK(organization_id=current_setting('app.organization_id',true) AND tenant_id=current_setting('app.tenant_id',true));
        CREATE TRIGGER credential_closure_immutable BEFORE UPDATE OR DELETE
            ON hosting_controlplane.native_credential_issuance_closures FOR EACH ROW EXECUTE FUNCTION hosting_sync.immutable();
    END IF;
END; $$;
