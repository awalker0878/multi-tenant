-- One separately commissioned PostgreSQL coordinator for all discovery hosts.
-- Only its owner sees cross-tenant counts. Collectors receive their own admission
-- receipt, never another tenant's identities. Expiry does not release a lease.
CREATE TABLE hosting_controlplane.discovery_fleets (
    fleet_id text PRIMARY KEY CHECK (fleet_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    policy_digest text NOT NULL CHECK (policy_digest ~ '^[0-9a-f]{64}$'),
    fence_key_digest text NOT NULL CHECK (fence_key_digest ~ '^[0-9a-f]{64}$'),
    enabled boolean NOT NULL DEFAULT false,
    valid_until timestamptz NOT NULL
);
CREATE TABLE hosting_controlplane.discovery_fleet_limits (
    fleet_id text NOT NULL REFERENCES hosting_controlplane.discovery_fleets ON DELETE RESTRICT,
    bucket_id text NOT NULL CHECK (bucket_id ~ '^[0-9a-f]{64}$'),
    bucket_kind text NOT NULL CHECK (bucket_kind IN ('TOTAL','ORGANIZATION','TENANT','WSD','ENDPOINT')),
    max_concurrent integer NOT NULL CHECK (max_concurrent BETWEEN 1 AND 1024),
    min_interval_ms integer NOT NULL CHECK (min_interval_ms BETWEEN 1 AND 15000),
    max_started bigint NOT NULL CHECK (max_started BETWEEN 1 AND 1000000000),
    PRIMARY KEY (fleet_id,bucket_id)
);
CREATE TABLE hosting_controlplane.discovery_fleet_workers (
    fleet_id text NOT NULL REFERENCES hosting_controlplane.discovery_fleets ON DELETE RESTRICT,
    worker_id text NOT NULL CHECK (worker_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    login_role text NOT NULL CHECK (login_role ~ '^[a-z][a-z0-9_]{0,62}$'),
    service_digest text NOT NULL CHECK (service_digest ~ '^[0-9a-f]{64}$'),
    enabled boolean NOT NULL DEFAULT false,
    valid_until timestamptz NOT NULL,
    PRIMARY KEY (fleet_id,worker_id), UNIQUE (fleet_id,login_role)
);
CREATE TABLE hosting_controlplane.discovery_fleet_scopes (
    fleet_id text NOT NULL,
    worker_id text NOT NULL,
    organization_id text NOT NULL, tenant_id text NOT NULL, site_id text NOT NULL,
    security_domain_id text NOT NULL, endpoint_id text NOT NULL,
    native_scope_id text NOT NULL, platform_family text NOT NULL,
    environment_id text NOT NULL, collector_id text NOT NULL,
    bucket_ids text[] NOT NULL CHECK (cardinality(bucket_ids)=5),
    PRIMARY KEY (fleet_id,worker_id,organization_id,tenant_id,environment_id),
    FOREIGN KEY (fleet_id,worker_id) REFERENCES hosting_controlplane.discovery_fleet_workers ON DELETE RESTRICT,
    CHECK (platform_family IN ('vmware','nutanix','openstack'))
);
CREATE TABLE hosting_controlplane.discovery_fleet_leases (
    fleet_id text NOT NULL REFERENCES hosting_controlplane.discovery_fleets ON DELETE RESTRICT,
    lease_id text NOT NULL CHECK (lease_id ~ '^[0-9a-f]{32}$'),
    worker_id text NOT NULL, instance_id text NOT NULL CHECK (instance_id ~ '^[0-9a-f]{32}$'),
    service_digest text NOT NULL CHECK (service_digest ~ '^[0-9a-f]{64}$'),
    request_digest text NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    request_json jsonb NOT NULL CHECK (octet_length(request_json::text)<=8192),
    bucket_ids text[] NOT NULL CHECK (cardinality(bucket_ids)=5),
    started_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
    PRIMARY KEY (fleet_id,lease_id),
    FOREIGN KEY (fleet_id,worker_id) REFERENCES hosting_controlplane.discovery_fleet_workers ON DELETE RESTRICT,
    CHECK (started_at<expires_at AND expires_at-started_at<=interval '15 seconds')
);
CREATE INDEX discovery_fleet_lease_buckets ON hosting_controlplane.discovery_fleet_leases USING gin(bucket_ids);
CREATE TABLE hosting_controlplane.discovery_fleet_closes (
    fleet_id text NOT NULL, lease_id text NOT NULL,
    worker_id text NOT NULL, instance_id text NOT NULL, service_digest text NOT NULL,
    request_digest text NOT NULL,
    outcome text NOT NULL CHECK (outcome IN ('LOCAL_SOCKET_CLOSED','INDEPENDENT_WORKER_FENCED')),
    observed_at timestamptz NOT NULL,
    observer_role text NOT NULL, receipt_json jsonb,
    PRIMARY KEY (fleet_id,lease_id),
    FOREIGN KEY (fleet_id,lease_id) REFERENCES hosting_controlplane.discovery_fleet_leases ON DELETE RESTRICT,
    CHECK ((outcome='INDEPENDENT_WORKER_FENCED')=(receipt_json IS NOT NULL)),
    CHECK (receipt_json IS NULL OR octet_length(receipt_json::text)<=8192)
);
CREATE TABLE hosting_controlplane.discovery_fleet_fencers (
    fleet_id text NOT NULL REFERENCES hosting_controlplane.discovery_fleets ON DELETE RESTRICT,
    login_role text NOT NULL CHECK (login_role ~ '^[a-z][a-z0-9_]{0,62}$'),
    fence_key_digest text NOT NULL CHECK (fence_key_digest ~ '^[0-9a-f]{64}$'),
    service_digest text NOT NULL CHECK (service_digest ~ '^[0-9a-f]{64}$'),
    enabled boolean NOT NULL DEFAULT false, valid_until timestamptz NOT NULL,
    PRIMARY KEY (fleet_id,login_role)
);

-- Deployment policy and enrollment are commissioned by a separate owner. Only
-- enabling/revoking the finite enrollment changes; scope/limits cannot be reset
-- by a collector or by updating an enrolled policy. Recommission a new fleet ID.
CREATE FUNCTION hosting_controlplane.guard_discovery_fleet_enrollment() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,hosting_controlplane AS $$
BEGIN
    IF (to_jsonb(NEW)-'enabled') IS DISTINCT FROM (to_jsonb(OLD)-'enabled') THEN
        RAISE EXCEPTION 'Fleet enrollment identity is immutable' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
DO $$ DECLARE t text; BEGIN
    FOREACH t IN ARRAY ARRAY['discovery_fleets','discovery_fleet_workers','discovery_fleet_fencers'] LOOP
        EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE ON hosting_controlplane.%I FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_discovery_fleet_enrollment()',t||'_identity',t);
        EXECUTE format('CREATE TRIGGER %I BEFORE DELETE ON hosting_controlplane.%I FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes()',t||'_no_delete',t);
    END LOOP;
    FOREACH t IN ARRAY ARRAY['discovery_fleet_limits','discovery_fleet_scopes','discovery_fleet_leases','discovery_fleet_closes'] LOOP
        EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON hosting_controlplane.%I FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes()',t||'_immutable',t);
    END LOOP;
    FOREACH t IN ARRAY ARRAY['discovery_fleets','discovery_fleet_limits','discovery_fleet_workers','discovery_fleet_scopes','discovery_fleet_leases','discovery_fleet_closes','discovery_fleet_fencers'] LOOP
        EXECUTE format('REVOKE ALL ON hosting_controlplane.%I FROM PUBLIC',t);
        EXECUTE format('ALTER TABLE hosting_controlplane.%I ENABLE ROW LEVEL SECURITY',t);
        EXECUTE format('ALTER TABLE hosting_controlplane.%I FORCE ROW LEVEL SECURITY',t);
        EXECUTE format('CREATE POLICY fleet_owner_only ON hosting_controlplane.%I USING (current_user=pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid=%L::regclass))) WITH CHECK (current_user=pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid=%L::regclass)))',t,'hosting_controlplane.'||t,'hosting_controlplane.'||t);
    END LOOP;
END; $$;

CREATE FUNCTION hosting_controlplane.discovery_fleet_admit(fleet text,worker text,service text,request text,digest text)
RETURNS TABLE(status text,lease_id text,started_at timestamptz,expires_at timestamptz)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE f hosting_controlplane.discovery_fleets%ROWTYPE;
    w hosting_controlplane.discovery_fleet_workers%ROWTYPE;
    s hosting_controlplane.discovery_fleet_scopes%ROWTYPE;
    lim hosting_controlplane.discovery_fleet_limits%ROWTYPE;
    doc jsonb; at_time timestamptz; expiration timestamptz; active_count bigint; starts bigint; last_start timestamptz;
BEGIN
    IF request IS NULL OR digest IS NULL OR service IS NULL OR octet_length(request)>8192 OR digest !~ '^[0-9a-f]{64}$'
        OR encode(sha256(convert_to(request,'UTF8')),'hex') IS DISTINCT FROM digest THEN
        RAISE EXCEPTION 'Invalid bounded fleet request' USING ERRCODE='23514';
    END IF;
    doc:=request::jsonb;
    IF jsonb_typeof(doc)<>'object' OR (SELECT count(*) FROM jsonb_object_keys(doc))<>14
        OR NOT doc ?& ARRAY['format','leaseId','instanceId','organizationId','tenantId','siteId','securityDomainId','endpointId','nativeScopeId','platformFamily','environmentId','collectorId','campaignDigest','expiresAt']
        OR EXISTS (SELECT 1 FROM jsonb_each(doc) WHERE jsonb_typeof(value) IS DISTINCT FROM 'string')
        OR doc->>'format'<>'hosting-discovery-fleet-read/1'
        OR doc->>'leaseId' !~ '^[0-9a-f]{32}$' OR doc->>'instanceId' !~ '^[0-9a-f]{32}$'
        OR doc->>'campaignDigest' !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'Invalid fleet request identity' USING ERRCODE='23514';
    END IF;
    -- This row serializes *all* dimensions together, never a best-effort count
    -- from several hosts or a tenant-filtered aggregate.
    SELECT * INTO f FROM hosting_controlplane.discovery_fleets WHERE fleet_id=fleet FOR UPDATE;
    at_time:=clock_timestamp();
    SELECT * INTO w FROM hosting_controlplane.discovery_fleet_workers WHERE fleet_id=fleet AND worker_id=worker;
    IF NOT FOUND OR w.login_role<>session_user OR NOT w.enabled OR w.valid_until<=at_time
        OR service IS DISTINCT FROM w.service_digest OR f.fleet_id IS NULL OR NOT f.enabled OR f.valid_until<=at_time
        OR hosting_controlplane.is_site_worker_role() THEN
        RAISE EXCEPTION 'Fleet service enrollment is unavailable' USING ERRCODE='42501';
    END IF;
    SELECT * INTO s FROM hosting_controlplane.discovery_fleet_scopes WHERE fleet_id=fleet AND worker_id=worker
        AND organization_id=doc->>'organizationId' AND tenant_id=doc->>'tenantId'
        AND environment_id=doc->>'environmentId' AND site_id=doc->>'siteId'
        AND security_domain_id=doc->>'securityDomainId' AND endpoint_id=doc->>'endpointId'
        AND native_scope_id=doc->>'nativeScopeId' AND platform_family=doc->>'platformFamily'
        AND collector_id=doc->>'collectorId';
    IF NOT FOUND THEN RAISE EXCEPTION 'Fleet scope is not enrolled' USING ERRCODE='42501'; END IF;
    -- Bucket identities are derived here as well as at enrollment. A malformed
    -- commissioning row cannot accidentally split the TOTAL or shared endpoint.
    IF s.bucket_ids IS DISTINCT FROM ARRAY[
        encode(sha256(convert_to(jsonb_build_array('TOTAL')::text,'UTF8')),'hex'),
        encode(sha256(convert_to(jsonb_build_array('ORGANIZATION',s.organization_id)::text,'UTF8')),'hex'),
        encode(sha256(convert_to(jsonb_build_array('TENANT',s.organization_id,s.tenant_id)::text,'UTF8')),'hex'),
        encode(sha256(convert_to(jsonb_build_array('WSD',s.organization_id,s.tenant_id,s.site_id,s.security_domain_id)::text,'UTF8')),'hex'),
        encode(sha256(convert_to(jsonb_build_array('ENDPOINT',s.organization_id,s.site_id,s.platform_family,s.endpoint_id)::text,'UTF8')),'hex')
    ] THEN RAISE EXCEPTION 'Fleet bucket identities are inconsistent' USING ERRCODE='23514'; END IF;
    expiration:=(doc->>'expiresAt')::timestamptz;
    IF expiration IS NULL OR expiration<=at_time OR expiration-at_time>interval '15 seconds' THEN
        RAISE EXCEPTION 'Fleet read deadline is invalid' USING ERRCODE='23514';
    END IF;
    IF EXISTS (SELECT 1 FROM hosting_controlplane.discovery_fleet_leases l WHERE l.fleet_id=fleet AND l.lease_id=doc->>'leaseId') THEN
        RETURN QUERY SELECT 'LEASE_OUTCOME_UNKNOWN'::text,doc->>'leaseId',NULL::timestamptz,NULL::timestamptz; RETURN;
    END IF;
    IF (SELECT count(*) FROM hosting_controlplane.discovery_fleet_limits l WHERE l.fleet_id=fleet AND l.bucket_id=ANY(s.bucket_ids))<>5
        OR (SELECT count(DISTINCT bucket_kind) FROM hosting_controlplane.discovery_fleet_limits l WHERE l.fleet_id=fleet AND l.bucket_id=ANY(s.bucket_ids))<>5 THEN
        RAISE EXCEPTION 'All fleet limit dimensions must be enrolled' USING ERRCODE='23514';
    END IF;
    FOR lim IN SELECT * FROM hosting_controlplane.discovery_fleet_limits l WHERE l.fleet_id=fleet AND l.bucket_id=ANY(s.bucket_ids) LOOP
        SELECT count(*),max(l.started_at),count(*) FILTER (WHERE c.lease_id IS NULL)
            INTO starts,last_start,active_count FROM hosting_controlplane.discovery_fleet_leases l
            LEFT JOIN hosting_controlplane.discovery_fleet_closes c USING(fleet_id,lease_id)
            WHERE l.fleet_id=fleet AND lim.bucket_id=ANY(l.bucket_ids);
        IF last_start>at_time THEN RAISE EXCEPTION 'Fleet coordinator clock regressed' USING ERRCODE='23514'; END IF;
        IF starts>=lim.max_started OR active_count>=lim.max_concurrent
            OR last_start+make_interval(secs=>lim.min_interval_ms::double precision/1000)>at_time THEN
            RETURN QUERY SELECT 'THROTTLED'::text,NULL::text,NULL::timestamptz,NULL::timestamptz; RETURN;
        END IF;
    END LOOP;
    INSERT INTO hosting_controlplane.discovery_fleet_leases VALUES(fleet,doc->>'leaseId',worker,doc->>'instanceId',service,digest,doc,s.bucket_ids,at_time,expiration);
    RETURN QUERY SELECT 'LEASE_STARTED'::text,doc->>'leaseId',at_time,expiration;
END; $$;

CREATE FUNCTION hosting_controlplane.discovery_fleet_close(fleet text,worker text,service text,instance text,lease text,digest text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE w hosting_controlplane.discovery_fleet_workers%ROWTYPE; l hosting_controlplane.discovery_fleet_leases%ROWTYPE; at_time timestamptz;
BEGIN
    PERFORM 1 FROM hosting_controlplane.discovery_fleets WHERE fleet_id=fleet FOR UPDATE;
    at_time:=clock_timestamp();
    SELECT * INTO w FROM hosting_controlplane.discovery_fleet_workers WHERE fleet_id=fleet AND worker_id=worker;
    IF NOT FOUND OR w.login_role<>session_user OR NOT w.enabled OR w.valid_until<=at_time OR w.service_digest IS DISTINCT FROM service
        OR hosting_controlplane.is_site_worker_role() THEN
        RAISE EXCEPTION 'Current closing worker is unavailable' USING ERRCODE='42501';
    END IF;
    SELECT * INTO l FROM hosting_controlplane.discovery_fleet_leases WHERE fleet_id=fleet AND lease_id=lease;
    IF NOT FOUND OR (l.worker_id,l.instance_id,l.service_digest,l.request_digest) IS DISTINCT FROM (worker,instance,service,digest) THEN
        RAISE EXCEPTION 'Closing identity differs from original read' USING ERRCODE='42501';
    END IF;
    IF EXISTS (SELECT 1 FROM hosting_controlplane.discovery_fleet_closes WHERE fleet_id=fleet AND lease_id=lease) THEN RETURN 'ALREADY_CLOSED'; END IF;
    INSERT INTO hosting_controlplane.discovery_fleet_closes VALUES(fleet,lease,worker,instance,service,digest,'LOCAL_SOCKET_CLOSED',at_time,session_user,NULL);
    RETURN 'LOCAL_SOCKET_CLOSED';
END; $$;

CREATE FUNCTION hosting_controlplane.discovery_fleet_inspect(fleet text,worker text,service text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE w hosting_controlplane.discovery_fleet_workers%ROWTYPE; f hosting_controlplane.discovery_fleets%ROWTYPE; result jsonb;
BEGIN
    SELECT * INTO w FROM hosting_controlplane.discovery_fleet_workers WHERE fleet_id=fleet AND worker_id=worker;
    SELECT * INTO f FROM hosting_controlplane.discovery_fleets WHERE fleet_id=fleet;
    IF w.worker_id IS NULL OR w.login_role<>session_user OR NOT w.enabled OR w.valid_until<=clock_timestamp()
        OR w.service_digest IS DISTINCT FROM service OR hosting_controlplane.is_site_worker_role() THEN
        RAISE EXCEPTION 'Fleet worker is not current' USING ERRCODE='42501';
    END IF;
    SELECT jsonb_agg(jsonb_build_object('leaseId',l.lease_id,'instanceId',l.instance_id,'requestDigest',l.request_digest,
        'startedAt',l.started_at,'expiresAt',l.expires_at,'status',CASE WHEN c.lease_id IS NOT NULL THEN c.outcome
        WHEN l.expires_at<=clock_timestamp() THEN 'EXPIRED_OUTCOME_UNKNOWN' ELSE 'READ_OUTCOME_UNKNOWN' END) ORDER BY l.started_at)
        INTO result FROM (SELECT * FROM hosting_controlplane.discovery_fleet_leases WHERE fleet_id=fleet AND worker_id=worker ORDER BY started_at DESC LIMIT 128) l
        LEFT JOIN hosting_controlplane.discovery_fleet_closes c USING(fleet_id,lease_id);
    RETURN jsonb_build_object('policyDigest',f.policy_digest,'enabled',f.enabled AND f.valid_until>clock_timestamp(),'leases',coalesce(result,'[]'::jsonb));
END; $$;

CREATE FUNCTION hosting_controlplane.discovery_fleet_fenced_close(fleet text,receipt text,key_digest text,service text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE proof jsonb; doc jsonb; l hosting_controlplane.discovery_fleet_leases%ROWTYPE;
    existing hosting_controlplane.discovery_fleet_closes%ROWTYPE; at_time timestamptz;
BEGIN
    IF receipt IS NULL OR service IS NULL OR key_digest IS NULL OR octet_length(receipt)>8192 THEN
        RAISE EXCEPTION 'Fence receipt is oversized or incomplete' USING ERRCODE='23514'; END IF;
    proof:=receipt::jsonb; doc:=proof->'receipt';
    IF jsonb_typeof(proof)<>'object' OR (SELECT count(*) FROM jsonb_object_keys(proof))<>2
        OR NOT proof ?& ARRAY['receipt','signature'] OR jsonb_typeof(doc)<>'object'
        OR jsonb_typeof(proof->'signature')<>'string'
        OR (SELECT count(*) FROM jsonb_object_keys(doc))<>13
        OR NOT doc ?& ARRAY['format','fleetId','leaseId','workerId','instanceId','serviceDigest','requestDigest','observerId','observationId','observedAt','expiresAt','oldProcessExcluded','oldSocketsClosed']
        OR EXISTS (SELECT 1 FROM jsonb_each(doc) WHERE key NOT IN ('oldProcessExcluded','oldSocketsClosed')
            AND jsonb_typeof(value) IS DISTINCT FROM 'string') THEN
        RAISE EXCEPTION 'Fence receiver must retain original signed proof' USING ERRCODE='23514';
    END IF;
    PERFORM 1 FROM hosting_controlplane.discovery_fleets WHERE fleet_id=fleet AND fence_key_digest=key_digest FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Fence key is not enrolled' USING ERRCODE='42501'; END IF;
    at_time:=clock_timestamp();
    IF NOT EXISTS (SELECT 1 FROM hosting_controlplane.discovery_fleet_fencers WHERE fleet_id=fleet AND login_role=session_user
        AND enabled AND valid_until>at_time AND fence_key_digest=key_digest AND service_digest=service)
        OR hosting_controlplane.is_site_worker_role() THEN
        RAISE EXCEPTION 'Independent fence receiver is not current' USING ERRCODE='42501';
    END IF;
    IF doc->>'format' IS DISTINCT FROM 'hosting-discovery-fleet-fence-receipt/1' OR doc->>'fleetId' IS DISTINCT FROM fleet
        OR (doc->>'observedAt')::timestamptz>at_time OR at_time>=(doc->>'expiresAt')::timestamptz
        OR at_time-(doc->>'observedAt')::timestamptz>interval '5 minutes'
        OR (doc->>'expiresAt')::timestamptz-(doc->>'observedAt')::timestamptz>interval '15 minutes'
        OR doc->'oldProcessExcluded' IS DISTINCT FROM 'true'::jsonb OR doc->'oldSocketsClosed' IS DISTINCT FROM 'true'::jsonb THEN
        RAISE EXCEPTION 'Fence receipt is stale or incomplete' USING ERRCODE='23514';
    END IF;
    SELECT * INTO l FROM hosting_controlplane.discovery_fleet_leases WHERE fleet_id=fleet AND lease_id=doc->>'leaseId';
    IF NOT FOUND OR (l.worker_id,l.instance_id,l.service_digest,l.request_digest)
        IS DISTINCT FROM (doc->>'workerId',doc->>'instanceId',doc->>'serviceDigest',doc->>'requestDigest') THEN
        RAISE EXCEPTION 'Fence receipt differs from original read' USING ERRCODE='23514';
    END IF;
    SELECT * INTO existing FROM hosting_controlplane.discovery_fleet_closes WHERE fleet_id=fleet AND lease_id=l.lease_id;
    IF FOUND THEN
        IF existing.outcome<>'INDEPENDENT_WORKER_FENCED' OR existing.receipt_json IS DISTINCT FROM proof THEN
            RAISE EXCEPTION 'Read already has another immutable close receipt' USING ERRCODE='23514';
        END IF;
        RETURN 'INDEPENDENT_WORKER_FENCED';
    END IF;
    INSERT INTO hosting_controlplane.discovery_fleet_closes VALUES(fleet,l.lease_id,l.worker_id,l.instance_id,l.service_digest,l.request_digest,
        'INDEPENDENT_WORKER_FENCED',at_time,session_user,proof);
    RETURN 'INDEPENDENT_WORKER_FENCED';
END; $$;

REVOKE ALL ON FUNCTION hosting_controlplane.guard_discovery_fleet_enrollment() FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.discovery_fleet_admit(text,text,text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.discovery_fleet_close(text,text,text,text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.discovery_fleet_inspect(text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.discovery_fleet_fenced_close(text,text,text,text) FROM PUBLIC;
