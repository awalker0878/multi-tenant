-- B43 schedules reference current B09 plans/jobs; they do not create another
-- queue or approve a workflow. Native budget enrollment and release acceptance
-- use independent commissioner/reconciliation credentials, never HTTP/worker
-- credentials. No role is granted table/function privileges by this migration.
CREATE TABLE hosting_controlplane.migration_wave_domains (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    domain_id text NOT NULL,
    document_digest text NOT NULL CHECK (document_digest ~ '^[0-9a-f]{64}$'),
    document_json text NOT NULL CHECK (octet_length(document_json) BETWEEN 1 AND 131072),
    enrolled_by text NOT NULL,
    enrolled_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id,tenant_id,domain_id),
    CHECK (jsonb_typeof(document_json::jsonb)='object'),
    CHECK (document_json::jsonb->>'format'='hosting-migration-wave-domain/1'),
    CHECK ((document_json::jsonb->>'organizationId') IS NOT DISTINCT FROM organization_id),
    CHECK ((document_json::jsonb->>'tenantId') IS NOT DISTINCT FROM tenant_id),
    CHECK ((document_json::jsonb->>'domainId') IS NOT DISTINCT FROM domain_id)
);
CREATE TABLE hosting_controlplane.migration_wave_domain_scopes (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    platform_family text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    domain_id text NOT NULL,
    PRIMARY KEY (organization_id,tenant_id,platform_family,endpoint_id,native_scope_id),
    FOREIGN KEY (organization_id,tenant_id,domain_id) REFERENCES
        hosting_controlplane.migration_wave_domains(organization_id,tenant_id,domain_id) ON DELETE RESTRICT
);
CREATE FUNCTION hosting_controlplane.project_migration_wave_domain() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE item jsonb;
BEGIN
    IF jsonb_typeof(NEW.document_json::jsonb->'scopes') IS DISTINCT FROM 'array'
        OR jsonb_array_length(NEW.document_json::jsonb->'scopes') NOT BETWEEN 2 AND 64 THEN
        RAISE EXCEPTION 'A wave domain requires a bounded explicit native scope inventory' USING ERRCODE='23514';
    END IF;
    FOR item IN SELECT * FROM jsonb_array_elements(NEW.document_json::jsonb->'scopes') LOOP
        IF (item->'scope'->>'organizationId',item->'scope'->>'tenantId')
            IS DISTINCT FROM (NEW.organization_id,NEW.tenant_id) THEN
            RAISE EXCEPTION 'A wave domain cannot cross tenant scope' USING ERRCODE='23514';
        END IF;
        INSERT INTO hosting_controlplane.migration_wave_domain_scopes
            (organization_id,tenant_id,platform_family,endpoint_id,native_scope_id,domain_id)
            VALUES (NEW.organization_id,NEW.tenant_id,item->'scope'->>'platformFamily',
                item->'scope'->>'endpointId',item->'scope'->>'nativeScopeId',NEW.domain_id)
            ON CONFLICT DO NOTHING;
        IF NOT EXISTS (SELECT 1 FROM hosting_controlplane.migration_wave_domain_scopes s
            WHERE (s.organization_id,s.tenant_id,s.platform_family,s.endpoint_id,s.native_scope_id,s.domain_id)=
                (NEW.organization_id,NEW.tenant_id,item->'scope'->>'platformFamily',
                 item->'scope'->>'endpointId',item->'scope'->>'nativeScopeId',NEW.domain_id)) THEN
            RAISE EXCEPTION 'A native scope already has another wave budget owner' USING ERRCODE='23514';
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$;
CREATE TRIGGER wave_domain_scope_projection AFTER INSERT ON hosting_controlplane.migration_wave_domains
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.project_migration_wave_domain();

CREATE TABLE hosting_controlplane.migration_waves (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    schedule_digest text NOT NULL CHECK (schedule_digest ~ '^[0-9a-f]{64}$'),
    domain_id text NOT NULL,
    domain_digest text NOT NULL CHECK (domain_digest ~ '^[0-9a-f]{64}$'),
    definition_json text NOT NULL CHECK (octet_length(definition_json) BETWEEN 1 AND 2097152),
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id,tenant_id,schedule_digest),
    FOREIGN KEY (organization_id,tenant_id,domain_id) REFERENCES
        hosting_controlplane.migration_wave_domains(organization_id,tenant_id,domain_id) ON DELETE RESTRICT,
    CHECK (jsonb_typeof(definition_json::jsonb)='object'),
    CHECK (definition_json::jsonb->>'format'='hosting-migration-wave/1'),
    CHECK ((definition_json::jsonb->>'organizationId') IS NOT DISTINCT FROM organization_id),
    CHECK ((definition_json::jsonb->>'tenantId') IS NOT DISTINCT FROM tenant_id),
    CHECK ((definition_json::jsonb->>'domainId') IS NOT DISTINCT FROM domain_id),
    CHECK ((definition_json::jsonb->>'domainDigest') IS NOT DISTINCT FROM domain_digest),
    CHECK (jsonb_typeof(definition_json::jsonb->'members')='array'),
    CHECK (jsonb_array_length(definition_json::jsonb->'members') BETWEEN 1 AND 64)
);
CREATE TABLE hosting_controlplane.migration_wave_members (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    schedule_digest text NOT NULL,
    member_id text NOT NULL,
    cohort_id text NOT NULL,
    resource_keys jsonb NOT NULL CHECK (jsonb_typeof(resource_keys)='array' AND jsonb_array_length(resource_keys)>0),
    risk_groups jsonb NOT NULL CHECK (jsonb_typeof(risk_groups)='array' AND jsonb_array_length(risk_groups)>0),
    demand jsonb NOT NULL CHECK (jsonb_typeof(demand)='object'),
    job_id text,
    status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','ADMITTED','HELD','SUCCEEDED')),
    reason text NOT NULL DEFAULT 'PLANNING_ONLY' CHECK (reason IN
        ('PLANNING_ONLY','B09_ADMITTED','WINDOW_EXPIRED','ACCEPTED_RELEASE')),
    claimed_at timestamptz,
    released_at timestamptz,
    PRIMARY KEY (organization_id,tenant_id,schedule_digest,member_id),
    UNIQUE (organization_id,tenant_id,job_id),
    FOREIGN KEY (organization_id,tenant_id,schedule_digest) REFERENCES
        hosting_controlplane.migration_waves(organization_id,tenant_id,schedule_digest) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id,tenant_id,job_id) REFERENCES
        hosting_controlplane.operation_jobs(organization_id,tenant_id,job_id) ON DELETE RESTRICT,
    CHECK ((job_id IS NULL)=(claimed_at IS NULL)),
    CHECK (status NOT IN ('ADMITTED','SUCCEEDED') OR job_id IS NOT NULL),
    CHECK ((status='SUCCEEDED')=(released_at IS NOT NULL))
);
CREATE TABLE hosting_controlplane.migration_wave_resource_claims (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    resource_key text NOT NULL CHECK (resource_key ~ '^[0-9a-f]{64}$'),
    schedule_digest text NOT NULL,
    member_id text NOT NULL,
    released_at timestamptz,
    PRIMARY KEY (organization_id,tenant_id,resource_key,schedule_digest,member_id),
    FOREIGN KEY (organization_id,tenant_id,schedule_digest,member_id) REFERENCES
        hosting_controlplane.migration_wave_members(organization_id,tenant_id,schedule_digest,member_id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX wave_live_native_resource ON hosting_controlplane.migration_wave_resource_claims
    (organization_id,tenant_id,resource_key) WHERE released_at IS NULL;
CREATE TABLE hosting_controlplane.migration_wave_events (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    domain_id text NOT NULL,
    sequence bigint NOT NULL CHECK (sequence>0),
    schedule_digest text NOT NULL,
    member_id text,
    event text NOT NULL CHECK (event IN ('SCHEDULE_REGISTERED','MEMBER_ADMITTED','MEMBER_HELD','MEMBER_RELEASED')),
    reason text NOT NULL CHECK (reason IN ('PLANNING_ONLY','B09_ADMITTED','WINDOW_EXPIRED','ACCEPTED_RELEASE')),
    detail jsonb NOT NULL CHECK (jsonb_typeof(detail)='object' AND octet_length(detail::text)<=4096),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id,tenant_id,domain_id,sequence),
    FOREIGN KEY (organization_id,tenant_id,schedule_digest) REFERENCES
        hosting_controlplane.migration_waves(organization_id,tenant_id,schedule_digest) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id,tenant_id,schedule_digest,member_id) REFERENCES
        hosting_controlplane.migration_wave_members(organization_id,tenant_id,schedule_digest,member_id) ON DELETE RESTRICT
);

-- Only a separately configured operating/reconciliation reviewer may INSERT.
-- These references retain independent transfer-stop, exclusion and shared-risk
-- receipts. Construction of a JSON object or a SUCCEEDED projection is not an
-- acceptance. The scheduler has SELECT only, and never creates these receipts.
CREATE TABLE hosting_controlplane.migration_wave_release_acceptances (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    schedule_digest text NOT NULL,
    member_id text NOT NULL,
    job_id text NOT NULL,
    plan_digest text NOT NULL CHECK (plan_digest ~ '^[0-9a-f]{64}$'),
    start_payload_digest text NOT NULL CHECK (start_payload_digest ~ '^[0-9a-f]{64}$'),
    completion_event_sequence bigint NOT NULL CHECK (completion_event_sequence>1),
    completion_evidence_digest text NOT NULL CHECK (completion_evidence_digest ~ '^[0-9a-f]{64}$'),
    transfer_stopped_evidence_digest text NOT NULL CHECK (transfer_stopped_evidence_digest ~ '^[0-9a-f]{64}$'),
    owner_exclusion_evidence_digest text NOT NULL CHECK (owner_exclusion_evidence_digest ~ '^[0-9a-f]{64}$'),
    shared_risk_cleared_evidence_digest text NOT NULL CHECK (shared_risk_cleared_evidence_digest ~ '^[0-9a-f]{64}$'),
    acceptance_digest text NOT NULL CHECK (acceptance_digest ~ '^[0-9a-f]{64}$'),
    observed_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    accepted_by text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id,tenant_id,schedule_digest,member_id),
    FOREIGN KEY (organization_id,tenant_id,schedule_digest,member_id) REFERENCES
        hosting_controlplane.migration_wave_members(organization_id,tenant_id,schedule_digest,member_id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id,tenant_id,job_id,completion_event_sequence) REFERENCES
        hosting_controlplane.job_events(organization_id,tenant_id,job_id,sequence) ON DELETE RESTRICT,
    CHECK (expires_at>observed_at AND expires_at<=observed_at+interval '1 hour')
);

CREATE FUNCTION hosting_controlplane.migration_wave_release_payload_is_current(
    a hosting_controlplane.migration_wave_release_acceptances,at_time timestamptz) RETURNS boolean
LANGUAGE sql SET search_path=pg_catalog,hosting_controlplane AS $$
    SELECT EXISTS (
        SELECT 1 FROM hosting_controlplane.migration_wave_members m
        JOIN hosting_controlplane.migration_waves w USING(organization_id,tenant_id,schedule_digest)
        JOIN hosting_controlplane.operation_jobs j ON (j.organization_id,j.tenant_id,j.job_id)=
            (a.organization_id,a.tenant_id,a.job_id)
        JOIN hosting_controlplane.job_events e ON (e.organization_id,e.tenant_id,e.job_id,e.sequence)=
            (a.organization_id,a.tenant_id,a.job_id,a.completion_event_sequence)
        JOIN hosting_controlplane.job_outbox o ON (o.organization_id,o.tenant_id,o.job_id)=
            (a.organization_id,a.tenant_id,a.job_id)
        CROSS JOIN LATERAL (
            SELECT value FROM jsonb_array_elements(w.definition_json::jsonb->'members')
            WHERE value->>'memberId'=m.member_id
        ) member_doc
        WHERE (m.organization_id,m.tenant_id,m.schedule_digest,m.member_id)=
            (a.organization_id,a.tenant_id,a.schedule_digest,a.member_id)
        AND a.job_id=m.job_id AND a.plan_digest=j.plan_digest AND j.status='SUCCEEDED'
        AND j.last_event_sequence=a.completion_event_sequence
        AND e.status='SUCCEEDED' AND e.detail->>'evidenceDigest'=a.completion_evidence_digest
        AND e.recorded_at<=(member_doc.value->>'windowEnd')::timestamptz
        AND o.delivered_at IS NOT NULL AND o.start_run_id IS NOT NULL
        AND o.start_payload_digest=a.start_payload_digest
        AND a.observed_at<=at_time AND a.expires_at>at_time
        -- Missing native intent/observation inventory cannot mean zero work.
        AND EXISTS (SELECT 1 FROM hosting_controlplane.native_operation_intents i
            WHERE (i.organization_id,i.tenant_id,i.job_id)=(a.organization_id,a.tenant_id,a.job_id))
        AND NOT EXISTS (
            SELECT 1 FROM hosting_controlplane.native_operation_intents i
            WHERE (i.organization_id,i.tenant_id,i.job_id)=(a.organization_id,a.tenant_id,a.job_id)
            AND (i.state<>'RESOLVED' OR NOT EXISTS (
                SELECT 1 FROM hosting_controlplane.native_operation_observations n
                WHERE (n.organization_id,n.tenant_id,n.operation_id)=(i.organization_id,i.tenant_id,i.operation_id)
                AND n.evidence_digest=i.resolution_evidence_digest AND n.outcome=i.outcome
                AND n.native_quiesced AND n.observed_at<=a.observed_at
                AND n.observed_at>=a.observed_at-interval '5 minutes'
                AND n.observation_id=(SELECT latest.observation_id
                    FROM hosting_controlplane.native_operation_observations latest
                    WHERE (latest.organization_id,latest.tenant_id,latest.operation_id)=
                        (i.organization_id,i.tenant_id,i.operation_id)
                    ORDER BY latest.observed_at DESC,latest.recorded_at DESC,latest.observation_id DESC LIMIT 1))))
        AND NOT EXISTS (SELECT 1 FROM hosting_controlplane.native_containment_holds h
            WHERE EXISTS (SELECT 1 FROM hosting_controlplane.native_operation_intents i
                WHERE (i.organization_id,i.tenant_id,i.job_id)=(a.organization_id,a.tenant_id,a.job_id)
                AND (i.platform_family,i.endpoint_id,i.native_scope_id,i.resource_kind,i.native_id)=
                    (h.platform_family,h.endpoint_id,h.native_scope_id,h.resource_kind,h.native_id))
            OR EXISTS (SELECT 1 FROM hosting_controlplane.native_operation_intents i
                JOIN hosting_controlplane.native_operation_observations n
                    USING(organization_id,tenant_id,operation_id)
                CROSS JOIN LATERAL jsonb_array_elements(n.created_native_bindings) binding
                WHERE (i.organization_id,i.tenant_id,i.job_id)=(a.organization_id,a.tenant_id,a.job_id)
                AND (binding.value->>'platform_family',binding.value->>'endpoint_id',binding.value->>'native_scope_id',
                    binding.value->>'resource_kind',binding.value->>'native_id')=
                    (h.platform_family,h.endpoint_id,h.native_scope_id,h.resource_kind,h.native_id)))
    );
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.migration_wave_release_payload_is_current(
    hosting_controlplane.migration_wave_release_acceptances,timestamptz) FROM PUBLIC;

CREATE FUNCTION hosting_controlplane.migration_wave_release_is_current(
    org text,tenant text,schedule text,member text,at_time timestamptz) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE acceptance hosting_controlplane.migration_wave_release_acceptances%ROWTYPE;
BEGIN
    IF org IS DISTINCT FROM current_setting('app.organization_id',true) OR
        tenant IS DISTINCT FROM current_setting('app.tenant_id',true) OR hosting_controlplane.is_site_worker_role() THEN
        RAISE EXCEPTION 'Wave release requires the authenticated tenant service' USING ERRCODE='42501';
    END IF;
    SELECT * INTO acceptance FROM hosting_controlplane.migration_wave_release_acceptances
        WHERE (organization_id,tenant_id,schedule_digest,member_id)=(org,tenant,schedule,member);
    IF NOT FOUND THEN RETURN false; END IF;
    RETURN hosting_controlplane.migration_wave_release_payload_is_current(acceptance,at_time);
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.migration_wave_release_is_current(text,text,text,text,timestamptz) FROM PUBLIC;

CREATE FUNCTION hosting_controlplane.guard_migration_wave_release() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE member_row hosting_controlplane.migration_wave_members%ROWTYPE;
        job_row hosting_controlplane.operation_jobs%ROWTYPE;
        event_row hosting_controlplane.job_events%ROWTYPE;
        start_row hosting_controlplane.job_outbox%ROWTYPE;
BEGIN
    SELECT * INTO member_row FROM hosting_controlplane.migration_wave_members
        WHERE (organization_id,tenant_id,schedule_digest,member_id)=
            (NEW.organization_id,NEW.tenant_id,NEW.schedule_digest,NEW.member_id) FOR SHARE;
    SELECT * INTO job_row FROM hosting_controlplane.operation_jobs
        WHERE (organization_id,tenant_id,job_id)=(NEW.organization_id,NEW.tenant_id,NEW.job_id) FOR SHARE;
    SELECT * INTO event_row FROM hosting_controlplane.job_events
        WHERE (organization_id,tenant_id,job_id,sequence)=
            (NEW.organization_id,NEW.tenant_id,NEW.job_id,NEW.completion_event_sequence);
    SELECT * INTO start_row FROM hosting_controlplane.job_outbox
        WHERE (organization_id,tenant_id,job_id)=(NEW.organization_id,NEW.tenant_id,NEW.job_id) FOR SHARE;
    IF member_row.job_id IS DISTINCT FROM NEW.job_id OR member_row.status NOT IN ('ADMITTED','HELD')
        OR job_row.plan_digest IS DISTINCT FROM NEW.plan_digest OR job_row.status IS DISTINCT FROM 'SUCCEEDED'
        OR job_row.last_event_sequence IS DISTINCT FROM NEW.completion_event_sequence
        OR event_row.status IS DISTINCT FROM 'SUCCEEDED'
        OR (event_row.detail->>'evidenceDigest') IS DISTINCT FROM NEW.completion_evidence_digest
        OR start_row.start_payload_digest IS DISTINCT FROM NEW.start_payload_digest
        OR start_row.start_run_id IS NULL OR start_row.delivered_at IS NULL
        OR NEW.observed_at>clock_timestamp() OR NEW.observed_at<clock_timestamp()-interval '5 minutes'
        OR NEW.expires_at<=clock_timestamp() THEN
        RAISE EXCEPTION 'Release acceptance requires the exact current completed original job and independent owner receipts' USING ERRCODE='23514';
    END IF;
    IF NOT hosting_controlplane.migration_wave_release_payload_is_current(NEW,clock_timestamp()) THEN
        RAISE EXCEPTION 'Independent release cannot omit, inherit or assume quiescent native inventory' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER wave_release_original_job BEFORE INSERT ON hosting_controlplane.migration_wave_release_acceptances
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_migration_wave_release();

CREATE FUNCTION hosting_controlplane.guard_migration_wave_member() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE wave_row hosting_controlplane.migration_waves%ROWTYPE;
        domain_row hosting_controlplane.migration_wave_domains%ROWTYPE;
        member_doc jsonb; budget jsonb; demand_key text; risk text; current_total numeric;
        job_row hosting_controlplane.operation_jobs%ROWTYPE;
BEGIN
    SELECT * INTO wave_row FROM hosting_controlplane.migration_waves
        WHERE (organization_id,tenant_id,schedule_digest)=(NEW.organization_id,NEW.tenant_id,NEW.schedule_digest);
    PERFORM 1 FROM hosting_controlplane.lock_migration_wave_domain(
        NEW.organization_id,NEW.tenant_id,wave_row.domain_id);
    SELECT * INTO domain_row FROM hosting_controlplane.migration_wave_domains
        WHERE (organization_id,tenant_id,domain_id)=(NEW.organization_id,NEW.tenant_id,wave_row.domain_id);
    SELECT value INTO member_doc FROM jsonb_array_elements(wave_row.definition_json::jsonb->'members')
        WHERE value->>'memberId'=NEW.member_id;
    IF member_doc IS NULL OR NEW.cohort_id IS DISTINCT FROM member_doc->'plan'->'spec'->'source'->>'securityDomainId'
        OR wave_row.domain_digest IS DISTINCT FROM domain_row.document_digest THEN
        RAISE EXCEPTION 'Wave member requires its exact retained definition and known budget owner' USING ERRCODE='23514';
    END IF;
    IF TG_OP='INSERT' THEN
        IF NEW.status<>'PENDING' OR NEW.job_id IS NOT NULL OR NEW.reason<>'PLANNING_ONLY' THEN
            RAISE EXCEPTION 'A saved schedule is planning only' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END IF;
    IF (NEW.organization_id,NEW.tenant_id,NEW.schedule_digest,NEW.member_id,NEW.cohort_id,
        NEW.resource_keys,NEW.risk_groups,NEW.demand) IS DISTINCT FROM
       (OLD.organization_id,OLD.tenant_id,OLD.schedule_digest,OLD.member_id,OLD.cohort_id,
        OLD.resource_keys,OLD.risk_groups,OLD.demand)
       OR (OLD.job_id IS NOT NULL AND NEW.job_id IS DISTINCT FROM OLD.job_id)
       OR (OLD.claimed_at IS NOT NULL AND NEW.claimed_at IS DISTINCT FROM OLD.claimed_at) THEN
        RAISE EXCEPTION 'Wave member identity, resource and original job binding is immutable' USING ERRCODE='23514';
    END IF;
    IF OLD.status='PENDING' AND NEW.status='ADMITTED' THEN
        SELECT * INTO job_row FROM hosting_controlplane.operation_jobs
            WHERE (organization_id,tenant_id,job_id)=(NEW.organization_id,NEW.tenant_id,NEW.job_id);
        IF job_row.status IS DISTINCT FROM 'QUEUED'
            OR job_row.plan_id IS DISTINCT FROM member_doc->'plan'->'metadata'->>'planId'
            OR job_row.plan_digest IS DISTINCT FROM member_doc->'plan'->'metadata'->>'planDigest'
            OR job_row.plan_revision IS DISTINCT FROM (member_doc->'plan'->'metadata'->>'revision')::bigint
            OR clock_timestamp()<(member_doc->>'windowStart')::timestamptz
            OR clock_timestamp()+(member_doc->>'runtimeSeconds')::bigint*interval '1 second'>(member_doc->>'windowEnd')::timestamptz
            OR clock_timestamp()>=(domain_row.document_json::jsonb->>'expiresAt')::timestamptz
            OR clock_timestamp()<(domain_row.document_json::jsonb->>'observedAt')::timestamptz
            OR NEW.reason<>'B09_ADMITTED' OR NEW.claimed_at IS NULL THEN
            RAISE EXCEPTION 'Admission requires the current exact B09 job and complete usable window' USING ERRCODE='23514';
        END IF;
        IF EXISTS (SELECT 1 FROM jsonb_array_elements_text(member_doc->'dependsOn') dep
            WHERE NOT EXISTS (SELECT 1 FROM hosting_controlplane.migration_wave_members previous
                WHERE (previous.organization_id,previous.tenant_id,previous.schedule_digest,previous.member_id)=
                    (NEW.organization_id,NEW.tenant_id,NEW.schedule_digest,dep.value) AND previous.status='SUCCEEDED')) THEN
            RAISE EXCEPTION 'Dependencies require independently accepted completion' USING ERRCODE='23514';
        END IF;
        budget=domain_row.document_json::jsonb->'budget';
        FOR demand_key IN SELECT jsonb_object_keys(budget) LOOP
            SELECT COALESCE(SUM((m.demand->>demand_key)::numeric),0) INTO current_total
                FROM hosting_controlplane.migration_wave_members m
                JOIN hosting_controlplane.migration_waves w USING(organization_id,tenant_id,schedule_digest)
                WHERE (m.organization_id,m.tenant_id,w.domain_id)=(NEW.organization_id,NEW.tenant_id,wave_row.domain_id)
                    AND m.job_id IS NOT NULL AND m.status<>'SUCCEEDED';
            IF (NEW.demand->>demand_key) IS NULL OR (NEW.demand->>demand_key)::numeric<0
                OR current_total+(NEW.demand->>demand_key)::numeric>(budget->>demand_key)::numeric THEN
                RAISE EXCEPTION 'Native-domain concurrency, exposure, downtime, risk or transfer budget exhausted' USING ERRCODE='23514';
            END IF;
        END LOOP;
        FOR risk IN SELECT jsonb_array_elements_text(NEW.risk_groups) LOOP
            SELECT COALESCE(SUM((m.demand->>'risk_units')::numeric),0) INTO current_total
                FROM hosting_controlplane.migration_wave_members m
                JOIN hosting_controlplane.migration_waves w USING(organization_id,tenant_id,schedule_digest)
                WHERE (m.organization_id,m.tenant_id,w.domain_id)=(NEW.organization_id,NEW.tenant_id,wave_row.domain_id)
                    AND m.job_id IS NOT NULL AND m.status<>'SUCCEEDED' AND m.risk_groups ? risk;
            IF (domain_row.document_json::jsonb->'sharedRiskLimits'->>risk) IS NULL
                OR current_total+(NEW.demand->>'risk_units')::numeric>
                    (domain_row.document_json::jsonb->'sharedRiskLimits'->>risk)::numeric THEN
                RAISE EXCEPTION 'Shared native failure-domain risk budget exhausted' USING ERRCODE='23514';
            END IF;
        END LOOP;
    ELSIF NEW.status='HELD' AND OLD.status IN ('PENDING','ADMITTED') AND NEW.reason='WINDOW_EXPIRED' THEN
        IF clock_timestamp()+(CASE WHEN OLD.status='PENDING' THEN (member_doc->>'runtimeSeconds')::bigint ELSE 0 END)*interval '1 second'
            <(member_doc->>'windowEnd')::timestamptz THEN
            RAISE EXCEPTION 'A usable window cannot be marked expired' USING ERRCODE='23514';
        END IF;
    ELSIF NEW.status='SUCCEEDED' AND OLD.status IN ('ADMITTED','HELD') AND NEW.reason='ACCEPTED_RELEASE' THEN
        IF NOT hosting_controlplane.migration_wave_release_is_current(NEW.organization_id,NEW.tenant_id,
                NEW.schedule_digest,NEW.member_id,clock_timestamp()) THEN
            RAISE EXCEPTION 'Uncertain or unaccepted native work retains every wave charge' USING ERRCODE='23514';
        END IF;
    ELSE
        RAISE EXCEPTION 'Wave member state transition is forbidden' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER wave_member_transition BEFORE INSERT OR UPDATE ON hosting_controlplane.migration_wave_members
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_migration_wave_member();
CREATE TRIGGER wave_member_no_delete BEFORE DELETE ON hosting_controlplane.migration_wave_members
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

CREATE FUNCTION hosting_controlplane.guard_migration_wave_claim() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE member_row hosting_controlplane.migration_wave_members%ROWTYPE;
BEGIN
    SELECT * INTO member_row FROM hosting_controlplane.migration_wave_members
        WHERE (organization_id,tenant_id,schedule_digest,member_id)=
            (NEW.organization_id,NEW.tenant_id,NEW.schedule_digest,NEW.member_id);
    IF TG_OP='INSERT' THEN
        IF member_row.status IS DISTINCT FROM 'ADMITTED' OR NOT member_row.resource_keys ? NEW.resource_key
            OR NEW.released_at IS NOT NULL THEN
            RAISE EXCEPTION 'Resource claim requires the exact admitted member' USING ERRCODE='23514';
        END IF;
    ELSIF (NEW.organization_id,NEW.tenant_id,NEW.resource_key,NEW.schedule_digest,NEW.member_id)
        IS DISTINCT FROM (OLD.organization_id,OLD.tenant_id,OLD.resource_key,OLD.schedule_digest,OLD.member_id)
        OR OLD.released_at IS NOT NULL OR NEW.released_at IS NULL OR member_row.status<>'SUCCEEDED' THEN
        RAISE EXCEPTION 'Resource claims release only after independent accepted completion' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER wave_claim_transition BEFORE INSERT OR UPDATE ON hosting_controlplane.migration_wave_resource_claims
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_migration_wave_claim();
CREATE TRIGGER wave_claim_no_delete BEFORE DELETE ON hosting_controlplane.migration_wave_resource_claims
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

CREATE FUNCTION hosting_controlplane.lock_migration_wave_domain(org text,tenant text,domain text)
RETURNS TABLE(document_digest text,document_json text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
BEGIN
    IF hosting_controlplane.is_site_worker_role() OR
        org IS DISTINCT FROM current_setting('app.organization_id',true) OR
        tenant IS DISTINCT FROM current_setting('app.tenant_id',true) THEN
        RAISE EXCEPTION 'Wave admission lock requires the authenticated tenant service' USING ERRCODE='42501';
    END IF;
    RETURN QUERY SELECT d.document_digest,d.document_json FROM hosting_controlplane.migration_wave_domains d
        WHERE (d.organization_id,d.tenant_id,d.domain_id)=(org,tenant,domain) FOR UPDATE;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.lock_migration_wave_domain(text,text,text) FROM PUBLIC;

-- A site SQL credential receives this exact-job read instead of schedule table
-- SELECT. It cannot make an invisible affiliated job appear unaffiliated. The
-- session binding is checked before any definer-only table visibility is used.
CREATE FUNCTION hosting_controlplane.migration_wave_job_window(org text,tenant text,job text)
RETURNS TABLE(member_status text,selected_domain_digest text,current_domain_digest text,
    budget_start timestamptz,budget_end timestamptz,window_start timestamptz,window_end timestamptz,
    runtime_seconds bigint,plan_id text,plan_revision bigint,plan_digest text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
BEGIN
    IF org IS DISTINCT FROM current_setting('app.organization_id',true) OR
        tenant IS DISTINCT FROM current_setting('app.tenant_id',true) OR
        (hosting_controlplane.is_site_worker_role() AND
            NOT hosting_controlplane.site_worker_job_visible(org,tenant,job)) THEN
        RAISE EXCEPTION 'Wave window read requires the exact authenticated tenant/site job' USING ERRCODE='42501';
    END IF;
    RETURN QUERY SELECT m.status,w.domain_digest,d.document_digest,
        (d.document_json::jsonb->>'observedAt')::timestamptz,
        (d.document_json::jsonb->>'expiresAt')::timestamptz,
        (member_doc.value->>'windowStart')::timestamptz,
        (member_doc.value->>'windowEnd')::timestamptz,
        (member_doc.value->>'runtimeSeconds')::bigint,
        member_doc.value->'plan'->'metadata'->>'planId',
        (member_doc.value->'plan'->'metadata'->>'revision')::bigint,
        member_doc.value->'plan'->'metadata'->>'planDigest'
        FROM hosting_controlplane.migration_wave_members m
        JOIN hosting_controlplane.migration_waves w USING(organization_id,tenant_id,schedule_digest)
        JOIN hosting_controlplane.migration_wave_domains d USING(organization_id,tenant_id,domain_id)
        CROSS JOIN LATERAL (
            SELECT value FROM jsonb_array_elements(w.definition_json::jsonb->'members')
            WHERE value->>'memberId'=m.member_id
        ) member_doc
        WHERE (m.organization_id,m.tenant_id,m.job_id)=(org,tenant,job);
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.migration_wave_job_window(text,text,text) FROM PUBLIC;

DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['migration_wave_domains','migration_wave_domain_scopes',
        'migration_waves','migration_wave_members','migration_wave_resource_claims',
        'migration_wave_events','migration_wave_release_acceptances'] LOOP
        EXECUTE format('REVOKE ALL ON hosting_controlplane.%I FROM PUBLIC',table_name);
        EXECUTE format('ALTER TABLE hosting_controlplane.%I ENABLE ROW LEVEL SECURITY',table_name);
        EXECUTE format('ALTER TABLE hosting_controlplane.%I FORCE ROW LEVEL SECURITY',table_name);
        EXECUTE format('CREATE POLICY wave_tenant ON hosting_controlplane.%I '
            ||'USING (organization_id=current_setting(''app.organization_id'',true) AND tenant_id=current_setting(''app.tenant_id'',true)) '
            ||'WITH CHECK (organization_id=current_setting(''app.organization_id'',true) AND tenant_id=current_setting(''app.tenant_id'',true))',table_name);
        IF table_name IN ('migration_wave_domains','migration_waves','migration_wave_members') THEN
            -- Only a trusted table-owner definer may read these for an already
            -- checked site job. A site login cannot SET ROLE to that owner.
            EXECUTE format('CREATE POLICY wave_read ON hosting_controlplane.%I AS RESTRICTIVE FOR SELECT '
                ||'USING (NOT hosting_controlplane.is_site_worker_role() OR current_user=pg_get_userbyid('
                ||'(SELECT relowner FROM pg_class WHERE oid=%L::regclass)))',
                table_name,'hosting_controlplane.'||table_name);
            EXECUTE format('CREATE POLICY wave_insert ON hosting_controlplane.%I AS RESTRICTIVE FOR INSERT '
                ||'WITH CHECK (NOT hosting_controlplane.is_site_worker_role())',table_name);
            EXECUTE format('CREATE POLICY wave_update ON hosting_controlplane.%I AS RESTRICTIVE FOR UPDATE '
                ||'USING (NOT hosting_controlplane.is_site_worker_role()) WITH CHECK (NOT hosting_controlplane.is_site_worker_role())',table_name);
            EXECUTE format('CREATE POLICY wave_delete ON hosting_controlplane.%I AS RESTRICTIVE FOR DELETE '
                ||'USING (NOT hosting_controlplane.is_site_worker_role())',table_name);
        ELSE
            EXECUTE format('CREATE POLICY wave_no_site_worker ON hosting_controlplane.%I AS RESTRICTIVE FOR ALL '
                ||'USING (NOT hosting_controlplane.is_site_worker_role()) WITH CHECK (NOT hosting_controlplane.is_site_worker_role())',table_name);
        END IF;
    END LOOP;
    FOREACH table_name IN ARRAY ARRAY['migration_wave_domains','migration_wave_domain_scopes',
        'migration_waves','migration_wave_events','migration_wave_release_acceptances'] LOOP
        EXECUTE format('CREATE TRIGGER wave_append_only BEFORE UPDATE OR DELETE ON hosting_controlplane.%I '
            ||'FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes()',table_name);
    END LOOP;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.project_migration_wave_domain(),
    hosting_controlplane.guard_migration_wave_release(),hosting_controlplane.guard_migration_wave_member(),
    hosting_controlplane.guard_migration_wave_claim() FROM PUBLIC;
