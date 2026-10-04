-- One cross-tenant budget owner over the existing B09/wave rows. The pool is
-- independently commissioned by the schema owner, never enrolled by a tenant
-- runtime, worker or an HTTP request. No role receives table privileges here.
-- Forced tenant RLS stays in place for callers. Only the non-bypass schema
-- owner inside reviewed definer functions may aggregate these three scheduling
-- tables; no enterprise record, credential or job history gains cross-tenant
-- visibility. Public admission returns a boolean, never other tenants' rows.
DO $$ DECLARE relation text; BEGIN
    FOREACH relation IN ARRAY ARRAY['migration_wave_domains','migration_waves','migration_wave_members'] LOOP
        EXECUTE format('CREATE POLICY enterprise_budget_owner_read ON hosting_controlplane.%I '
            'FOR SELECT USING (current_user=pg_get_userbyid((SELECT relowner FROM pg_class '
            'WHERE oid=%L::regclass)))',relation,'hosting_controlplane.'||relation);
    END LOOP;
END $$;
CREATE TABLE hosting_controlplane.enterprise_wave_pools (
    pool_id text PRIMARY KEY,
    document_digest text NOT NULL CHECK (document_digest ~ '^[0-9a-f]{64}$'),
    document_json jsonb NOT NULL CHECK (jsonb_typeof(document_json)='object'
        AND octet_length(document_json::text)<=262144
        AND document_json->>'format'='hosting-enterprise-wave-pool/1'),
    enrolled_by text NOT NULL,
    enrolled_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (document_json->>'poolId'=pool_id)
);
CREATE TABLE hosting_controlplane.enterprise_wave_pool_domains (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    domain_id text NOT NULL,
    domain_digest text NOT NULL,
    pool_id text NOT NULL REFERENCES hosting_controlplane.enterprise_wave_pools ON DELETE RESTRICT,
    risk_groups jsonb NOT NULL CHECK (jsonb_typeof(risk_groups)='object'),
    PRIMARY KEY (organization_id,tenant_id,domain_id),
    FOREIGN KEY (organization_id,tenant_id,domain_id) REFERENCES
        hosting_controlplane.migration_wave_domains ON DELETE RESTRICT
);
CREATE TABLE hosting_controlplane.enterprise_wave_pool_turns (
    pool_id text PRIMARY KEY REFERENCES hosting_controlplane.enterprise_wave_pools ON DELETE RESTRICT,
    last_organization_id text,
    last_tenant_id text,
    generation bigint NOT NULL DEFAULT 0 CHECK (generation>=0),
    CHECK ((last_organization_id IS NULL)=(last_tenant_id IS NULL))
);
CREATE TABLE hosting_controlplane.enterprise_wave_tickets (
    pool_id text NOT NULL REFERENCES hosting_controlplane.enterprise_wave_pools ON DELETE RESTRICT,
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    domain_id text NOT NULL,
    schedule_digest text NOT NULL,
    member_id text NOT NULL,
    actor_subject text NOT NULL,
    expires_at timestamptz NOT NULL,
    refreshed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (pool_id,organization_id,tenant_id),
    FOREIGN KEY (organization_id,tenant_id,schedule_digest,member_id) REFERENCES
        hosting_controlplane.migration_wave_members ON DELETE RESTRICT,
    FOREIGN KEY (organization_id,tenant_id,domain_id) REFERENCES
        hosting_controlplane.enterprise_wave_pool_domains ON DELETE RESTRICT
);

CREATE FUNCTION hosting_controlplane.project_enterprise_wave_pool() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE item jsonb; declared hosting_controlplane.migration_wave_domains%ROWTYPE;
        budget jsonb; risk jsonb; entry record; group_name text;
BEGIN
    IF ARRAY(SELECT jsonb_object_keys(NEW.document_json) ORDER BY 1) IS DISTINCT FROM
        ARRAY['budget','domains','expiresAt','format','nativeBudgetEvidenceDigest',
            'observedAt','poolId','sharedRiskLimits']
        OR NEW.document_json->>'format' IS DISTINCT FROM 'hosting-enterprise-wave-pool/1'
        OR NEW.document_json->>'poolId' IS DISTINCT FROM NEW.pool_id
        OR jsonb_typeof(NEW.document_json->'nativeBudgetEvidenceDigest') IS DISTINCT FROM 'string'
        OR jsonb_typeof(NEW.document_json->'observedAt') IS DISTINCT FROM 'string'
        OR jsonb_typeof(NEW.document_json->'expiresAt') IS DISTINCT FROM 'string'
        OR jsonb_typeof(NEW.document_json->'domains') IS DISTINCT FROM 'array'
        OR jsonb_array_length(NEW.document_json->'domains') NOT BETWEEN 2 AND 256
        OR jsonb_typeof(NEW.document_json->'budget') IS DISTINCT FROM 'object'
        OR jsonb_typeof(NEW.document_json->'sharedRiskLimits') IS DISTINCT FROM 'object'
        OR NEW.document_json->>'nativeBudgetEvidenceDigest' !~ '^[0-9a-f]{64}$'
        OR (NEW.document_json->>'observedAt')::timestamptz>clock_timestamp()
        OR (NEW.document_json->>'expiresAt')::timestamptz<=clock_timestamp()
        OR (NEW.document_json->>'expiresAt')::timestamptz>
            (NEW.document_json->>'observedAt')::timestamptz+interval '31 days' THEN
        RAISE EXCEPTION 'An enterprise pool requires current complete independent budget enrollment' USING ERRCODE='23514';
    END IF;
    budget:=NEW.document_json->'budget';
    IF ARRAY(SELECT jsonb_object_keys(budget) ORDER BY 1) IS DISTINCT FROM
        ARRAY['block_iops','concurrent_jobs','download_kib_per_second','downtime_seconds',
            'exposed_workloads','risk_units','stage_bytes'] THEN
        RAISE EXCEPTION 'Every enterprise budget dimension is mandatory' USING ERRCODE='23514';
    END IF;
    FOR entry IN SELECT * FROM jsonb_each_text(budget) LOOP
        IF jsonb_typeof(budget->entry.key) IS DISTINCT FROM 'number'
            OR entry.value !~ '^[0-9]+$' OR entry.value::numeric<0
            OR (entry.key<>'downtime_seconds' AND entry.value::numeric<1) THEN
            RAISE EXCEPTION 'Enterprise budgets require bounded nonnegative integers' USING ERRCODE='23514';
        END IF;
    END LOOP;
    IF (budget->>'concurrent_jobs')::numeric>1024 OR (budget->>'exposed_workloads')::numeric>1024
        OR (budget->>'risk_units')::numeric>1000000000 OR (budget->>'stage_bytes')::numeric>1152921504606846976
        OR (budget->>'download_kib_per_second')::numeric>1073741824
        OR (budget->>'block_iops')::numeric>1024000000
        OR (budget->>'downtime_seconds')::numeric>2742681600 THEN
        RAISE EXCEPTION 'Enterprise budget exceeds the reviewed bound' USING ERRCODE='23514';
    END IF;
    FOR item IN SELECT value FROM jsonb_array_elements(NEW.document_json->'domains') LOOP
        SELECT * INTO declared FROM hosting_controlplane.migration_wave_domains d
            WHERE (d.organization_id,d.tenant_id,d.domain_id)=
                (item->>'organizationId',item->>'tenantId',item->>'domainId');
        IF NOT FOUND OR declared.document_digest IS DISTINCT FROM item->>'domainDigest'
            OR jsonb_typeof(item->'riskGroups') IS DISTINCT FROM 'object'
            OR ARRAY(SELECT jsonb_object_keys(item->'riskGroups') ORDER BY 1) IS DISTINCT FROM
                ARRAY(SELECT jsonb_object_keys(declared.document_json::jsonb->'sharedRiskLimits') ORDER BY 1)
            OR (declared.document_json::jsonb->>'expiresAt')::timestamptz<=clock_timestamp() THEN
            RAISE EXCEPTION 'Every pooled domain must exactly match its current independent native budget' USING ERRCODE='23514';
        END IF;
        FOR group_name IN SELECT value FROM jsonb_each_text(item->'riskGroups') LOOP
            IF group_name !~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'
                OR NOT NEW.document_json->'sharedRiskLimits' ? group_name THEN
                RAISE EXCEPTION 'Every native risk group needs a physical aggregate cap' USING ERRCODE='23514';
            END IF;
        END LOOP;
        INSERT INTO hosting_controlplane.enterprise_wave_pool_domains
            (organization_id,tenant_id,domain_id,domain_digest,pool_id,risk_groups)
            VALUES (declared.organization_id,declared.tenant_id,declared.domain_id,
                    declared.document_digest,NEW.pool_id,item->'riskGroups');
    END LOOP;
    IF (SELECT count(DISTINCT (organization_id,tenant_id))
        FROM hosting_controlplane.enterprise_wave_pool_domains WHERE pool_id=NEW.pool_id)<2 THEN
        RAISE EXCEPTION 'An enterprise pool needs distinct tenant authorities' USING ERRCODE='23514';
    END IF;
    FOR entry IN SELECT * FROM jsonb_each_text(NEW.document_json->'sharedRiskLimits') LOOP
        IF jsonb_typeof(NEW.document_json->'sharedRiskLimits'->entry.key) IS DISTINCT FROM 'number'
            OR entry.value !~ '^[1-9][0-9]*$' OR entry.value::numeric>(budget->>'risk_units')::numeric
            OR NOT EXISTS (SELECT 1 FROM hosting_controlplane.enterprise_wave_pool_domains d,
                LATERAL jsonb_each_text(d.risk_groups) g WHERE d.pool_id=NEW.pool_id AND g.value=entry.key) THEN
            RAISE EXCEPTION 'Unknown, unbounded or omitted enterprise risk cap' USING ERRCODE='23514';
        END IF;
    END LOOP;
    INSERT INTO hosting_controlplane.enterprise_wave_pool_turns(pool_id) VALUES(NEW.pool_id);
    RETURN NEW;
END;
$$;
CREATE TRIGGER enterprise_pool_projection AFTER INSERT ON hosting_controlplane.enterprise_wave_pools
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.project_enterprise_wave_pool();

CREATE FUNCTION hosting_controlplane.enterprise_wave_pool_for_domain(org text,tenant text,domain text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE selected text;
BEGIN
    IF hosting_controlplane.is_site_worker_role()
        OR org IS DISTINCT FROM current_setting('app.organization_id',true)
        OR tenant IS DISTINCT FROM current_setting('app.tenant_id',true) THEN
        RAISE EXCEPTION 'Enterprise wave lock requires the authenticated tenant service' USING ERRCODE='42501';
    END IF;
    SELECT d.pool_id INTO selected FROM hosting_controlplane.enterprise_wave_pool_domains d
        WHERE (d.organization_id,d.tenant_id,d.domain_id)=(org,tenant,domain);
    IF FOUND THEN
        -- Locks always precede tenant-domain locks, including raw member UPDATE.
        PERFORM 1 FROM hosting_controlplane.enterprise_wave_pool_turns WHERE pool_id=selected FOR UPDATE;
    END IF;
    RETURN selected;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.enterprise_wave_pool_for_domain(text,text,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION hosting_controlplane.lock_migration_wave_domain(org text,tenant text,domain text)
RETURNS TABLE(document_digest text,document_json text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
BEGIN
    IF hosting_controlplane.is_site_worker_role() OR
        org IS DISTINCT FROM current_setting('app.organization_id',true) OR
        tenant IS DISTINCT FROM current_setting('app.tenant_id',true) THEN
        RAISE EXCEPTION 'Wave admission lock requires the authenticated tenant service' USING ERRCODE='42501';
    END IF;
    PERFORM hosting_controlplane.enterprise_wave_pool_for_domain(org,tenant,domain);
    RETURN QUERY SELECT d.document_digest,d.document_json FROM hosting_controlplane.migration_wave_domains d
        WHERE (d.organization_id,d.tenant_id,d.domain_id)=(org,tenant,domain) FOR UPDATE;
END;
$$;

CREATE FUNCTION hosting_controlplane.enterprise_wave_member_fits(
    pool text,org text,tenant text,schedule text,member text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE selected hosting_controlplane.enterprise_wave_pools%ROWTYPE;
        candidate hosting_controlplane.migration_wave_members%ROWTYPE;
        dimension text; total numeric; group_name text;
BEGIN
    SELECT * INTO selected FROM hosting_controlplane.enterprise_wave_pools WHERE pool_id=pool;
    SELECT m.* INTO candidate FROM hosting_controlplane.migration_wave_members m
        JOIN hosting_controlplane.migration_waves w USING(organization_id,tenant_id,schedule_digest,domain_id)
        JOIN hosting_controlplane.enterprise_wave_pool_domains d USING(organization_id,tenant_id,domain_id)
        WHERE (m.organization_id,m.tenant_id,m.schedule_digest,m.member_id)=(org,tenant,schedule,member)
            AND d.pool_id=pool;
    IF NOT FOUND OR selected.pool_id IS NULL OR candidate.status<>'PENDING' THEN RETURN false; END IF;
    -- A dependency-blocked ticket must not monopolize the fair tenant turn.
    IF EXISTS (
        SELECT 1 FROM hosting_controlplane.migration_waves w
        CROSS JOIN LATERAL jsonb_array_elements(w.definition_json::jsonb->'members') descriptor
        CROSS JOIN LATERAL jsonb_array_elements_text(descriptor.value->'dependsOn') dependency
        LEFT JOIN hosting_controlplane.migration_wave_members predecessor ON
            (predecessor.organization_id,predecessor.tenant_id,predecessor.schedule_digest,predecessor.member_id)=
            (w.organization_id,w.tenant_id,w.schedule_digest,dependency.value)
        WHERE (w.organization_id,w.tenant_id,w.schedule_digest)=(org,tenant,schedule)
            AND descriptor.value->>'memberId'=member
            AND predecessor.status IS DISTINCT FROM 'SUCCEEDED') THEN RETURN false; END IF;
    FOR dimension IN SELECT jsonb_object_keys(selected.document_json->'budget') LOOP
        SELECT COALESCE(sum((m.demand->>dimension)::numeric),0) INTO total
            FROM hosting_controlplane.migration_wave_members m
            JOIN hosting_controlplane.migration_waves w USING(organization_id,tenant_id,schedule_digest,domain_id)
            JOIN hosting_controlplane.enterprise_wave_pool_domains d USING(organization_id,tenant_id,domain_id)
            WHERE d.pool_id=pool AND m.job_id IS NOT NULL AND m.status<>'SUCCEEDED';
        IF total+(candidate.demand->>dimension)::numeric>
            (selected.document_json->'budget'->>dimension)::numeric THEN RETURN false; END IF;
    END LOOP;
    IF EXISTS (SELECT 1 FROM hosting_controlplane.migration_wave_members m
        JOIN hosting_controlplane.migration_waves w USING(organization_id,tenant_id,schedule_digest,domain_id)
        JOIN hosting_controlplane.enterprise_wave_pool_domains d USING(organization_id,tenant_id,domain_id)
        WHERE d.pool_id=pool AND m.job_id IS NOT NULL AND m.status<>'SUCCEEDED'
            AND EXISTS (SELECT 1 FROM jsonb_array_elements_text(m.resource_keys) owned
                JOIN jsonb_array_elements_text(candidate.resource_keys) proposed ON owned.value=proposed.value))
        THEN RETURN false; END IF;
    FOR group_name IN
        SELECT DISTINCT d.risk_groups->>r.value
        FROM hosting_controlplane.migration_waves w
        JOIN hosting_controlplane.enterprise_wave_pool_domains d
            USING(organization_id,tenant_id,domain_id)
        CROSS JOIN LATERAL jsonb_array_elements_text(candidate.risk_groups) r
        WHERE (w.organization_id,w.tenant_id,w.schedule_digest)=(org,tenant,schedule)
    LOOP
        SELECT COALESCE(sum((risk_member.demand->>'risk_units')::numeric),0) INTO total
        FROM (
            SELECT DISTINCT m.organization_id,m.tenant_id,m.schedule_digest,m.member_id,m.demand
            FROM hosting_controlplane.migration_wave_members m
            JOIN hosting_controlplane.migration_waves w USING(organization_id,tenant_id,schedule_digest,domain_id)
            JOIN hosting_controlplane.enterprise_wave_pool_domains d USING(organization_id,tenant_id,domain_id),
                LATERAL jsonb_array_elements_text(m.risk_groups) r
            WHERE d.pool_id=pool AND m.job_id IS NOT NULL AND m.status<>'SUCCEEDED'
                AND d.risk_groups->>r.value=group_name) risk_member;
        IF group_name IS NULL OR NOT selected.document_json->'sharedRiskLimits' ? group_name
            OR total+(candidate.demand->>'risk_units')::numeric>
                (selected.document_json->'sharedRiskLimits'->>group_name)::numeric THEN RETURN false; END IF;
    END LOOP;
    RETURN true;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.enterprise_wave_member_fits(text,text,text,text,text) FROM PUBLIC;

CREATE FUNCTION hosting_controlplane.enterprise_wave_can_admit(
    pool text,org text,tenant text,schedule text,member text,actor text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE selected hosting_controlplane.enterprise_wave_pools%ROWTYPE;
        candidate hosting_controlplane.migration_wave_members%ROWTYPE;
        turn hosting_controlplane.enterprise_wave_pool_turns%ROWTYPE;
        chosen_org text; chosen_tenant text; dimension text; total numeric; group_name text;
        at_time timestamptz;
BEGIN
    SELECT * INTO selected FROM hosting_controlplane.enterprise_wave_pools WHERE pool_id=pool;
    IF selected.pool_id IS NULL THEN RETURN false; END IF;
    SELECT * INTO turn FROM hosting_controlplane.enterprise_wave_pool_turns WHERE pool_id=pool FOR UPDATE;
    at_time:=clock_timestamp();
    SELECT * INTO candidate FROM hosting_controlplane.migration_wave_members m
        WHERE (m.organization_id,m.tenant_id,m.schedule_digest,m.member_id)=(org,tenant,schedule,member);
    IF NOT FOUND OR selected.pool_id IS NULL OR candidate.status<>'PENDING'
        OR (selected.document_json->>'observedAt')::timestamptz>at_time
        OR (selected.document_json->>'expiresAt')::timestamptz<=at_time
        OR NOT EXISTS (SELECT 1 FROM hosting_controlplane.enterprise_wave_tickets t
            WHERE (t.pool_id,t.organization_id,t.tenant_id,t.schedule_digest,t.member_id,t.actor_subject)=
                (pool,org,tenant,schedule,member,actor) AND t.expires_at>at_time) THEN RETURN false; END IF;
    -- One currently eligible ticket per tenant, regardless of split domains/waves.
    -- Expiry releases only eligibility; admitted jobs retain every resource charge.
    SELECT t.organization_id,t.tenant_id INTO chosen_org,chosen_tenant
        FROM hosting_controlplane.enterprise_wave_tickets t
        JOIN hosting_controlplane.migration_wave_members m
            USING(organization_id,tenant_id,schedule_digest,member_id,domain_id)
        JOIN hosting_controlplane.migration_waves w USING(organization_id,tenant_id,schedule_digest,domain_id)
        JOIN hosting_controlplane.migration_wave_domains d USING(organization_id,tenant_id,domain_id)
        CROSS JOIN LATERAL (
            SELECT value FROM jsonb_array_elements(w.definition_json::jsonb->'members')
            WHERE value->>'memberId'=t.member_id) descriptor
        WHERE t.pool_id=pool AND t.expires_at>at_time AND m.status='PENDING'
            AND w.domain_digest=d.document_digest
            AND (d.document_json::jsonb->>'expiresAt')::timestamptz>at_time
            AND (descriptor.value->>'windowStart')::timestamptz<=at_time
            AND at_time+make_interval(secs=>(descriptor.value->>'runtimeSeconds')::integer)
                <=(descriptor.value->>'windowEnd')::timestamptz
            AND hosting_controlplane.enterprise_wave_member_fits(pool,t.organization_id,
                t.tenant_id,t.schedule_digest,t.member_id)
        ORDER BY CASE WHEN turn.last_organization_id IS NULL OR
                (t.organization_id,t.tenant_id)>(turn.last_organization_id,turn.last_tenant_id)
                THEN 0 ELSE 1 END,t.organization_id,t.tenant_id LIMIT 1;
    IF (chosen_org,chosen_tenant) IS DISTINCT FROM (org,tenant) THEN RETURN false; END IF;
    RETURN hosting_controlplane.enterprise_wave_member_fits(pool,org,tenant,schedule,member);
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.enterprise_wave_can_admit(text,text,text,text,text,text) FROM PUBLIC;

CREATE FUNCTION hosting_controlplane.migration_wave_pool_turn(
    org text,tenant text,domain text,schedule text,member text,actor text,until_time timestamptz)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE pool text; at_time timestamptz:=clock_timestamp();
BEGIN
    pool:=hosting_controlplane.enterprise_wave_pool_for_domain(org,tenant,domain);
    IF pool IS NULL THEN RETURN true; END IF;
    IF actor !~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'
        OR until_time<=at_time OR until_time>at_time+interval '30 seconds'
        OR NOT EXISTS (SELECT 1 FROM hosting_controlplane.migration_waves w
            JOIN hosting_controlplane.migration_wave_members m USING(organization_id,tenant_id,schedule_digest)
            WHERE (w.organization_id,w.tenant_id,w.domain_id,w.schedule_digest,m.member_id,m.status)=
                (org,tenant,domain,schedule,member,'PENDING')) THEN
        RAISE EXCEPTION 'A fair turn requires the exact current pending member and bounded authority' USING ERRCODE='23514';
    END IF;
    INSERT INTO hosting_controlplane.enterprise_wave_tickets
        (pool_id,organization_id,tenant_id,domain_id,schedule_digest,member_id,actor_subject,expires_at)
        VALUES(pool,org,tenant,domain,schedule,member,actor,until_time)
        ON CONFLICT (pool_id,organization_id,tenant_id) DO UPDATE SET
            domain_id=EXCLUDED.domain_id,schedule_digest=EXCLUDED.schedule_digest,
            member_id=EXCLUDED.member_id,actor_subject=EXCLUDED.actor_subject,
            expires_at=EXCLUDED.expires_at,refreshed_at=clock_timestamp();
    RETURN hosting_controlplane.enterprise_wave_can_admit(pool,org,tenant,schedule,member,actor);
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.migration_wave_pool_turn(text,text,text,text,text,text,timestamptz) FROM PUBLIC;

CREATE FUNCTION hosting_controlplane.guard_enterprise_wave_admission() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE domain text; pool text; actor text;
BEGIN
    IF OLD.status='PENDING' AND NEW.status='ADMITTED' THEN
        SELECT w.domain_id INTO domain FROM hosting_controlplane.migration_waves w
            WHERE (w.organization_id,w.tenant_id,w.schedule_digest)=
                (NEW.organization_id,NEW.tenant_id,NEW.schedule_digest);
        pool:=hosting_controlplane.enterprise_wave_pool_for_domain(NEW.organization_id,NEW.tenant_id,domain);
        IF pool IS NOT NULL THEN
            SELECT j.actor_subject INTO actor FROM hosting_controlplane.operation_jobs j
                WHERE (j.organization_id,j.tenant_id,j.job_id)=(NEW.organization_id,NEW.tenant_id,NEW.job_id);
            IF NOT hosting_controlplane.enterprise_wave_can_admit(pool,NEW.organization_id,
                NEW.tenant_id,NEW.schedule_digest,NEW.member_id,actor) THEN
                RAISE EXCEPTION 'Enterprise tenant turn or retained resource budget is unavailable' USING ERRCODE='23514';
            END IF;
            UPDATE hosting_controlplane.enterprise_wave_pool_turns SET
                last_organization_id=NEW.organization_id,last_tenant_id=NEW.tenant_id,generation=generation+1
                WHERE pool_id=pool;
            DELETE FROM hosting_controlplane.enterprise_wave_tickets
                WHERE (pool_id,organization_id,tenant_id)=(pool,NEW.organization_id,NEW.tenant_id);
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER zz_enterprise_wave_admission BEFORE UPDATE ON hosting_controlplane.migration_wave_members
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_enterprise_wave_admission();

DO $$
DECLARE relation text;
BEGIN
    FOREACH relation IN ARRAY ARRAY['enterprise_wave_pools','enterprise_wave_pool_domains',
        'enterprise_wave_pool_turns','enterprise_wave_tickets'] LOOP
        EXECUTE format('ALTER TABLE hosting_controlplane.%I ENABLE ROW LEVEL SECURITY',relation);
        EXECUTE format('ALTER TABLE hosting_controlplane.%I FORCE ROW LEVEL SECURITY',relation);
        EXECUTE format('CREATE POLICY enterprise_wave_owner ON hosting_controlplane.%I FOR ALL '
            'USING (current_user = (SELECT pg_get_userbyid(relowner) FROM pg_class '
            'WHERE oid=%L::regclass)) WITH CHECK (current_user = '
            '(SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid=%L::regclass))',
            relation,'hosting_controlplane.'||relation,'hosting_controlplane.'||relation);
    END LOOP;
END;
$$;
CREATE TRIGGER enterprise_pool_immutable BEFORE UPDATE OR DELETE ON hosting_controlplane.enterprise_wave_pools
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
CREATE TRIGGER enterprise_pool_domain_immutable BEFORE UPDATE OR DELETE ON hosting_controlplane.enterprise_wave_pool_domains
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
