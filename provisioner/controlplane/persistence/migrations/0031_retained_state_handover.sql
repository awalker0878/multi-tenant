-- Authenticated one-time retained-state import. Original execution facts remain
-- historical: no job, approval, grant, native task or successful retry is invented.
CREATE TABLE hosting_controlplane.retained_conversion_keys (
    organization_id text NOT NULL, tenant_id text NOT NULL,
    security_domain_id text NOT NULL, workload_id text NOT NULL,
    scope_digest text NOT NULL CHECK(scope_digest ~ '^[0-9a-f]{64}$'),
    key_id text NOT NULL, purpose text NOT NULL CHECK(purpose IN
        ('IMPORT','CUSTODY','NATIVE','EXCLUSION','OWNER','SECURITY')),
    subject_id text NOT NULL, verifier_role name NOT NULL,
    valid_from timestamptz NOT NULL, valid_until timestamptz NOT NULL,
    PRIMARY KEY(organization_id,tenant_id,scope_digest,key_id,purpose),
    CHECK(valid_until > valid_from)
);
CREATE TABLE hosting_controlplane.retained_conversion_key_revocations (
    organization_id text NOT NULL, tenant_id text NOT NULL,
    scope_digest text NOT NULL, key_id text NOT NULL, purpose text NOT NULL,
    reason_ref text NOT NULL, revoked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(organization_id,tenant_id,scope_digest,key_id,purpose),
    FOREIGN KEY(organization_id,tenant_id,scope_digest,key_id,purpose) REFERENCES
        hosting_controlplane.retained_conversion_keys ON DELETE RESTRICT
);
CREATE TABLE hosting_controlplane.retained_conversion_proofs (
    organization_id text NOT NULL, tenant_id text NOT NULL, event_key text NOT NULL,
    artifact_digest text NOT NULL CHECK(artifact_digest ~ '^[0-9a-f]{64}$'),
    scope_digest text NOT NULL, batch_id text NOT NULL,
    manifest_digest text NOT NULL CHECK(manifest_digest ~ '^[0-9a-f]{64}$'),
    key_id text NOT NULL, purpose text NOT NULL, subject_id text NOT NULL,
    observed_at timestamptz NOT NULL, fresh_until timestamptz NOT NULL,
    envelope jsonb NOT NULL, verified_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(organization_id,tenant_id,event_key),
    FOREIGN KEY(organization_id,tenant_id,scope_digest,key_id,purpose) REFERENCES
        hosting_controlplane.retained_conversion_keys ON DELETE RESTRICT,
    CHECK(fresh_until > observed_at AND fresh_until-observed_at <= interval '5 minutes')
);
CREATE FUNCTION hosting_controlplane.check_retained_conversion_proof()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE k hosting_controlplane.retained_conversion_keys%ROWTYPE; p jsonb;
BEGIN
    SELECT * INTO k FROM hosting_controlplane.retained_conversion_keys
     WHERE organization_id=NEW.organization_id AND tenant_id=NEW.tenant_id
       AND scope_digest=NEW.scope_digest AND key_id=NEW.key_id AND purpose=NEW.purpose;
    p := NEW.envelope->'payload';
    IF NOT FOUND OR current_user<>k.verifier_role OR
       EXISTS(SELECT 1 FROM pg_roles WHERE rolname=current_user AND (rolsuper OR rolbypassrls)) OR
       k.subject_id<>NEW.subject_id OR NOT(k.valid_from<=clock_timestamp() AND clock_timestamp()<k.valid_until) OR
       EXISTS(SELECT 1 FROM hosting_controlplane.retained_conversion_key_revocations r
              WHERE (r.organization_id,r.tenant_id,r.scope_digest,r.key_id,r.purpose)=
                    (k.organization_id,k.tenant_id,k.scope_digest,k.key_id,k.purpose)) OR
       NOT(NEW.observed_at<=clock_timestamp() AND clock_timestamp()<NEW.fresh_until) OR
       (p->>'format') IS DISTINCT FROM 'hosting-retained-conversion-proof/1' OR
       (p->>'batchId') IS DISTINCT FROM NEW.batch_id OR
       (p->>'manifestDigest') IS DISTINCT FROM NEW.manifest_digest OR
       (p->>'scopeDigest') IS DISTINCT FROM NEW.scope_digest OR
       (p->>'purpose') IS DISTINCT FROM NEW.purpose OR
       (p->>'subjectId') IS DISTINCT FROM NEW.subject_id OR
       (p->>'observedAt')::timestamptz IS DISTINCT FROM NEW.observed_at OR
       (p->>'freshUntil')::timestamptz IS DISTINCT FROM NEW.fresh_until OR
       (NEW.envelope->>'keyId') IS DISTINCT FROM NEW.key_id OR
       NOT EXISTS(SELECT 1 FROM hosting_controlplane.evidence_entries e
            WHERE e.organization_id=NEW.organization_id AND e.tenant_id=NEW.tenant_id
              AND e.event_key=NEW.event_key AND e.blob_digest=NEW.artifact_digest
              AND e.evidence_kind='RECOVERY_DECISION' AND e.subject_id=NEW.batch_id)
    THEN RAISE EXCEPTION 'Independent current retained-proof verifier and original evidence required'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER retained_proof_guard BEFORE INSERT ON hosting_controlplane.retained_conversion_proofs
 FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.check_retained_conversion_proof();
CREATE FUNCTION hosting_controlplane.lock_retained_conversion_key_revocation()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
BEGIN
    PERFORM 1 FROM hosting_controlplane.retained_conversion_keys k WHERE
      (k.organization_id,k.tenant_id,k.scope_digest,k.key_id,k.purpose)=
      (NEW.organization_id,NEW.tenant_id,NEW.scope_digest,NEW.key_id,NEW.purpose) FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Original enrolled conversion key required'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER retained_conversion_key_revoke_lock BEFORE INSERT ON hosting_controlplane.retained_conversion_key_revocations
 FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.lock_retained_conversion_key_revocation();

CREATE TABLE hosting_controlplane.retained_conversion_batches (
    organization_id text NOT NULL, tenant_id text NOT NULL, batch_id text NOT NULL,
    security_domain_id text NOT NULL, workload_id text NOT NULL,
    scope_digest text NOT NULL, scope jsonb NOT NULL,
    manifest_digest text NOT NULL CHECK(manifest_digest ~ '^[0-9a-f]{64}$'),
    archive_inventory_digest text NOT NULL CHECK(archive_inventory_digest ~ '^[0-9a-f]{64}$'),
    projection_digest text NOT NULL CHECK(projection_digest ~ '^[0-9a-f]{64}$'),
    workload_digest text NOT NULL CHECK(workload_digest ~ '^[0-9a-f]{64}$'),
    workload_revision bigint NOT NULL CHECK(workload_revision>0),
    history_count bigint NOT NULL CHECK(history_count>0),
    source_counts jsonb NOT NULL, source_boundary jsonb NOT NULL,
    import_proof text NOT NULL, custody_proof text NOT NULL,
    native_proof text NOT NULL, exclusion_proof text NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(organization_id,tenant_id,batch_id),
    UNIQUE(organization_id,tenant_id,security_domain_id,workload_id),
    FOREIGN KEY(organization_id,tenant_id,import_proof) REFERENCES hosting_controlplane.retained_conversion_proofs,
    FOREIGN KEY(organization_id,tenant_id,custody_proof) REFERENCES hosting_controlplane.retained_conversion_proofs,
    FOREIGN KEY(organization_id,tenant_id,native_proof) REFERENCES hosting_controlplane.retained_conversion_proofs,
    FOREIGN KEY(organization_id,tenant_id,exclusion_proof) REFERENCES hosting_controlplane.retained_conversion_proofs
);
CREATE TABLE hosting_controlplane.retained_conversion_files (
    organization_id text NOT NULL, tenant_id text NOT NULL, batch_id text NOT NULL,
    source_path text NOT NULL, original_digest text NOT NULL CHECK(original_digest ~ '^[0-9a-f]{64}$'),
    byte_count bigint NOT NULL CHECK(byte_count>=0 AND byte_count<=8388608),
    PRIMARY KEY(organization_id,tenant_id,batch_id,source_path),
    FOREIGN KEY(organization_id,tenant_id,batch_id) REFERENCES hosting_controlplane.retained_conversion_batches
);
CREATE TABLE hosting_controlplane.retained_conversion_bindings (
    organization_id text NOT NULL, tenant_id text NOT NULL, batch_id text NOT NULL,
    platform_family text NOT NULL, endpoint_id text NOT NULL, native_scope_id text NOT NULL,
    resource_kind text NOT NULL, native_id text NOT NULL,
    source_epoch bigint NOT NULL CHECK(source_epoch>0),
    target_epoch bigint NOT NULL CHECK(target_epoch=source_epoch+1),
    PRIMARY KEY(organization_id,tenant_id,batch_id,platform_family,endpoint_id,native_scope_id,resource_kind,native_id),
    FOREIGN KEY(organization_id,tenant_id,batch_id) REFERENCES hosting_controlplane.retained_conversion_batches
);
CREATE TABLE hosting_controlplane.retained_conversion_recovery (
    organization_id text NOT NULL, tenant_id text NOT NULL, batch_id text NOT NULL,
    operation_id text NOT NULL, generation bigint NOT NULL CHECK(generation>0),
    record_format text NOT NULL CHECK(record_format IN
        ('hosting-terraform-attempt/1','hosting-execution-event/1')),
    origin_digest text NOT NULL CHECK(origin_digest ~ '^[0-9a-f]{64}$'),
    original_outcome text NOT NULL CHECK(original_outcome IN
        ('UNKNOWN','LEGACY_APPLIED_REQUIRES_NATIVE_ACCEPTANCE','LEGACY_STEP_COMPLETED')),
    retry_authorized boolean NOT NULL DEFAULT false CHECK(retry_authorized=false),
    PRIMARY KEY(organization_id,tenant_id,batch_id,operation_id,generation),
    FOREIGN KEY(organization_id,tenant_id,batch_id) REFERENCES hosting_controlplane.retained_conversion_batches
);
CREATE TABLE hosting_controlplane.retained_conversion_handovers (
    organization_id text NOT NULL, tenant_id text NOT NULL, batch_id text NOT NULL,
    handover_id text NOT NULL, native_proof text NOT NULL, exclusion_proof text NOT NULL,
    owner_proof text NOT NULL, security_proof text NOT NULL, custody_proof text NOT NULL,
    reconciliation_digest text NOT NULL CHECK(reconciliation_digest ~ '^[0-9a-f]{64}$'),
    native_epochs jsonb NOT NULL, admission_until timestamptz NOT NULL,
    accepted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(organization_id,tenant_id,batch_id),
    UNIQUE(organization_id,tenant_id,handover_id),
    FOREIGN KEY(organization_id,tenant_id,batch_id) REFERENCES hosting_controlplane.retained_conversion_batches,
    FOREIGN KEY(organization_id,tenant_id,native_proof) REFERENCES hosting_controlplane.retained_conversion_proofs,
    FOREIGN KEY(organization_id,tenant_id,exclusion_proof) REFERENCES hosting_controlplane.retained_conversion_proofs,
    FOREIGN KEY(organization_id,tenant_id,owner_proof) REFERENCES hosting_controlplane.retained_conversion_proofs,
    FOREIGN KEY(organization_id,tenant_id,security_proof) REFERENCES hosting_controlplane.retained_conversion_proofs,
    FOREIGN KEY(organization_id,tenant_id,custody_proof) REFERENCES hosting_controlplane.retained_conversion_proofs
);
CREATE TABLE hosting_controlplane.retained_conversion_resolutions (
    organization_id text NOT NULL, tenant_id text NOT NULL, batch_id text NOT NULL,
    operation_id text NOT NULL, generation bigint NOT NULL,
    native_proof text NOT NULL, exclusion_proof text NOT NULL,
    disposition text NOT NULL CHECK(disposition IN ('NO_EFFECT_NO_REPLAY','EFFECT_PRESENT_NO_REPLAY')),
    PRIMARY KEY(organization_id,tenant_id,batch_id,operation_id,generation),
    FOREIGN KEY(organization_id,tenant_id,batch_id,operation_id,generation)
        REFERENCES hosting_controlplane.retained_conversion_recovery,
    FOREIGN KEY(organization_id,tenant_id,batch_id) REFERENCES hosting_controlplane.retained_conversion_handovers
);

CREATE FUNCTION hosting_controlplane.check_retained_conversion_batch()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE p record; seen_subjects text[]:=ARRAY[]::text[]; seen_keys text[]:=ARRAY[]::text[]; expected text;
BEGIN
    FOR i IN 1..4 LOOP
      expected:=(ARRAY['IMPORT','CUSTODY','NATIVE','EXCLUSION'])[i];
      SELECT e.*,k.valid_until INTO p FROM hosting_controlplane.retained_conversion_proofs e
        JOIN hosting_controlplane.retained_conversion_keys k ON
          (k.organization_id,k.tenant_id,k.scope_digest,k.key_id,k.purpose)=
          (e.organization_id,e.tenant_id,e.scope_digest,e.key_id,e.purpose)
        WHERE e.organization_id=NEW.organization_id AND e.tenant_id=NEW.tenant_id AND
          e.event_key=(ARRAY[NEW.import_proof,NEW.custody_proof,NEW.native_proof,NEW.exclusion_proof])[i]
          AND e.purpose=expected AND e.batch_id=NEW.batch_id AND e.manifest_digest=NEW.manifest_digest
          AND e.scope_digest=NEW.scope_digest AND k.security_domain_id=NEW.security_domain_id AND k.workload_id=NEW.workload_id
          AND e.observed_at<=clock_timestamp() AND clock_timestamp()<e.fresh_until
          AND k.valid_from<=clock_timestamp() AND clock_timestamp()<k.valid_until
          AND NOT EXISTS(SELECT 1 FROM hosting_controlplane.retained_conversion_key_revocations r WHERE
            (r.organization_id,r.tenant_id,r.scope_digest,r.key_id,r.purpose)=
            (e.organization_id,e.tenant_id,e.scope_digest,e.key_id,e.purpose)) FOR SHARE OF e,k;
      IF NOT FOUND OR p.subject_id=ANY(seen_subjects) OR p.key_id=ANY(seen_keys)
      THEN RAISE EXCEPTION 'Exact independently authenticated original import facts required'; END IF;
      seen_subjects:=array_append(seen_subjects,p.subject_id); seen_keys:=array_append(seen_keys,p.key_id);
      IF i=1 AND ((p.envelope->'statement'->>'projectionDigest') IS DISTINCT FROM NEW.projection_digest OR
          (p.envelope->'statement'->>'archiveInventoryDigest') IS DISTINCT FROM NEW.archive_inventory_digest OR
          (p.envelope->'statement'->'sourceCounts') IS DISTINCT FROM NEW.source_counts OR
          (p.envelope->'statement'->>'workloadDigest') IS DISTINCT FROM NEW.workload_digest OR
          (p.envelope->'statement'->>'canonicalHistoryCount')::bigint IS DISTINCT FROM NEW.history_count)
      THEN RAISE EXCEPTION 'Canonical original import commitment differs'; END IF;
      IF i=2 AND ((p.envelope->'statement'->>'originalManifestSha256') IS DISTINCT FROM NEW.manifest_digest OR
          (p.envelope->'statement'->>'archiveInventoryDigest') IS DISTINCT FROM NEW.archive_inventory_digest OR
          (p.envelope->'statement'->'sourceBoundary') IS DISTINCT FROM NEW.source_boundary OR
          (p.envelope->'statement'->'sourceCounts') IS DISTINCT FROM NEW.source_counts)
      THEN RAISE EXCEPTION 'Original custody/high-water commitment differs'; END IF;
      IF i=3 AND ((p.envelope->'statement'->>'complete') IS DISTINCT FROM 'true' OR
          jsonb_typeof(p.envelope->'statement'->'bindings') IS DISTINCT FROM 'array' OR
          jsonb_array_length(p.envelope->'statement'->'bindings')=0 OR
          jsonb_typeof(p.envelope->'statement'->'tasks') IS DISTINCT FROM 'array')
      THEN RAISE EXCEPTION 'Complete explicitly observed original-native inventory required'; END IF;
      IF i=4 AND ((p.envelope->'statement'->>'allExcluded') IS DISTINCT FROM 'true' OR
          (p.envelope->'statement'->>'queuedRequestsExcluded') IS DISTINCT FROM 'true' OR
          jsonb_typeof(p.envelope->'statement'->'oldWriters') IS DISTINCT FROM 'array' OR
          jsonb_array_length(p.envelope->'statement'->'oldWriters')=0 OR
          EXISTS(SELECT 1 FROM jsonb_array_elements(p.envelope->'statement'->'oldWriters') x
            WHERE (x->>'frozen') IS DISTINCT FROM 'true' OR (x->>'epoch') IS NULL OR (x->>'epoch')::bigint<=0))
      THEN RAISE EXCEPTION 'Every actual old writer/submission path must be excluded'; END IF;
    END LOOP;
    IF (NEW.scope->>'organizationId',NEW.scope->>'tenantId',NEW.scope->>'securityDomainId',NEW.scope->>'workloadId')
      IS DISTINCT FROM (NEW.organization_id,NEW.tenant_id,NEW.security_domain_id,NEW.workload_id)
    THEN RAISE EXCEPTION 'Retained scope differs from canonical owner'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER retained_conversion_batch_guard BEFORE INSERT ON hosting_controlplane.retained_conversion_batches
 FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.check_retained_conversion_batch();
CREATE FUNCTION hosting_controlplane.check_retained_conversion_binding()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE b hosting_controlplane.retained_conversion_batches%ROWTYPE; binding jsonb;
BEGIN
    SELECT * INTO b FROM hosting_controlplane.retained_conversion_batches WHERE organization_id=NEW.organization_id
      AND tenant_id=NEW.tenant_id AND batch_id=NEW.batch_id FOR SHARE;
    binding:=jsonb_build_object('platformFamily',NEW.platform_family,'endpointId',NEW.endpoint_id,
      'nativeScopeId',NEW.native_scope_id,'resourceKind',NEW.resource_kind,'nativeId',NEW.native_id);
    IF NOT FOUND OR (b.scope->>'platformFamily',b.scope->>'endpointId',b.scope->>'nativeScopeId') IS DISTINCT FROM
      (NEW.platform_family,NEW.endpoint_id,NEW.native_scope_id) OR
      NOT EXISTS(SELECT 1 FROM hosting_controlplane.retained_conversion_proofs p,
          LATERAL jsonb_array_elements(p.envelope->'statement'->'nativeEpochs') x
        WHERE p.organization_id=NEW.organization_id AND p.tenant_id=NEW.tenant_id AND p.event_key=b.import_proof
          AND x=jsonb_build_object('binding',binding,'sourceEpoch',NEW.source_epoch,'targetEpoch',NEW.target_epoch)) OR
      NOT EXISTS(SELECT 1 FROM hosting_controlplane.retained_conversion_proofs p,
          LATERAL jsonb_array_elements(p.envelope->'statement'->'bindings') x
        WHERE p.organization_id=NEW.organization_id AND p.tenant_id=NEW.tenant_id AND p.event_key=b.native_proof
          AND x->'binding'=binding)
      OR NEW.source_epoch IS DISTINCT FROM (SELECT max((x->>'epoch')::bigint)
        FROM hosting_controlplane.retained_conversion_proofs p,
          LATERAL jsonb_array_elements(p.envelope->'statement'->'oldWriters') x
        WHERE p.organization_id=NEW.organization_id AND p.tenant_id=NEW.tenant_id AND p.event_key=b.exclusion_proof)
    THEN RAISE EXCEPTION 'Native identity/epoch was not independently observed and committed'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER retained_conversion_binding_guard BEFORE INSERT ON hosting_controlplane.retained_conversion_bindings
 FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.check_retained_conversion_binding();

CREATE FUNCTION hosting_controlplane.retained_conversion_state(p_org text,p_tenant text,p_batch text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE b hosting_controlplane.retained_conversion_batches%ROWTYPE; answer jsonb;
BEGIN
    IF (p_org,p_tenant) IS DISTINCT FROM (current_setting('app.organization_id',true),
        current_setting('app.tenant_id',true)) THEN RAISE EXCEPTION 'Exact retained tenant context required'; END IF;
    SELECT * INTO b FROM hosting_controlplane.retained_conversion_batches
     WHERE organization_id=p_org AND tenant_id=p_tenant AND batch_id=p_batch FOR SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Retained batch is not visible'; END IF;
    SELECT jsonb_build_object('batchId',b.batch_id,'manifestDigest',b.manifest_digest,
        'projectionDigest',b.projection_digest,'archiveInventoryDigest',b.archive_inventory_digest,
        'sourceCounts',b.source_counts,'sourceBoundary',b.source_boundary,
        'workload',(SELECT jsonb_build_object('revision',r.revision,'digest',r.record_digest)
          FROM hosting_controlplane.enterprise_records r WHERE r.organization_id=p_org AND r.tenant_id=p_tenant
            AND r.record_kind='Workload' AND r.record_id=b.workload_id),
        'historyCount',(SELECT count(*) FROM hosting_controlplane.enterprise_record_history r
          WHERE r.organization_id=p_org AND r.tenant_id=p_tenant AND r.record_kind='Workload'
            AND r.record_id=b.workload_id),
        'fileCount',(SELECT count(*) FROM hosting_controlplane.retained_conversion_files f
          WHERE f.organization_id=p_org AND f.tenant_id=p_tenant AND f.batch_id=p_batch),
        'nativeEpochs',COALESCE((SELECT jsonb_agg(jsonb_build_object('binding',jsonb_build_object(
          'platformFamily',n.platform_family,'endpointId',n.endpoint_id,'nativeScopeId',n.native_scope_id,
          'resourceKind',n.resource_kind,'nativeId',n.native_id),'sourceEpoch',n.source_epoch,
          'targetEpoch',n.target_epoch,'currentEpoch',o.lease_epoch,'currentWorker',o.worker_id,
          'currentDeadline',o.lease_expires_at) ORDER BY n.platform_family,n.endpoint_id,n.native_scope_id,
          n.resource_kind,n.native_id) FROM hosting_controlplane.retained_conversion_bindings n
          LEFT JOIN hosting_controlplane.native_ownership o USING(platform_family,endpoint_id,native_scope_id,resource_kind,native_id)
          WHERE n.organization_id=p_org AND n.tenant_id=p_tenant AND n.batch_id=p_batch),'[]'::jsonb),
        'recovery',COALESCE((SELECT jsonb_agg(jsonb_build_object('operationId',r.operation_id,'generation',r.generation,
          'originDigest',r.origin_digest,'outcome',r.original_outcome) ORDER BY r.operation_id,r.generation)
          FROM hosting_controlplane.retained_conversion_recovery r WHERE r.organization_id=p_org AND r.tenant_id=p_tenant
            AND r.batch_id=p_batch),'[]'::jsonb),
        'workflowHighWater',COALESCE((SELECT jsonb_agg(jsonb_build_object('jobId',j.job_id,'planDigest',j.plan_digest,
          'status',j.status,'sequence',j.last_event_sequence,'originalStarts',(SELECT COALESCE(jsonb_agg(
            jsonb_build_object('outboxId',x.outbox_id,'deliveredAt',x.delivered_at,'runId',x.start_run_id,
              'startPayloadDigest',x.start_payload_digest,'firstAttempt',x.first_start_attempted_at,
              'namespace',x.start_namespace,'retentionUntil',x.start_retention_until,
              'payload',encode(sha256(convert_to(x.payload::text,'UTF8')),'hex')) ORDER BY x.outbox_id),'[]'::jsonb)
            FROM hosting_controlplane.job_outbox x WHERE x.organization_id=j.organization_id AND x.tenant_id=j.tenant_id
              AND x.job_id=j.job_id)) ORDER BY j.job_id)
          FROM hosting_controlplane.operation_jobs j JOIN hosting_controlplane.job_workload_bindings p
            ON p.organization_id=j.organization_id AND p.tenant_id=j.tenant_id AND p.job_id=j.job_id
              WHERE j.organization_id=p_org AND j.tenant_id=p_tenant
                AND p.workload_id=b.workload_id),'[]'::jsonb)) INTO answer;
    RETURN answer;
END $$;

CREATE FUNCTION hosting_controlplane.retained_conversion_write_is_admitted(p_org text,p_tenant text,p_wsd text,p_workload text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE b hosting_controlplane.retained_conversion_batches%ROWTYPE; h hosting_controlplane.retained_conversion_handovers%ROWTYPE;
    k record;
BEGIN
    IF (p_org,p_tenant) IS DISTINCT FROM (current_setting('app.organization_id',true),current_setting('app.tenant_id',true))
    THEN RAISE EXCEPTION 'Exact retained tenant context required'; END IF;
    SELECT * INTO b FROM hosting_controlplane.retained_conversion_batches WHERE organization_id=p_org
      AND tenant_id=p_tenant AND security_domain_id=p_wsd AND workload_id=p_workload FOR SHARE;
    IF NOT FOUND THEN RETURN true; END IF;
    SELECT * INTO h FROM hosting_controlplane.retained_conversion_handovers WHERE organization_id=p_org
      AND tenant_id=p_tenant AND batch_id=b.batch_id;
    IF NOT FOUND OR clock_timestamp()>=h.admission_until THEN RETURN false; END IF;
    IF (SELECT count(*) FROM hosting_controlplane.retained_conversion_files f WHERE f.organization_id=p_org
        AND f.tenant_id=p_tenant AND f.batch_id=b.batch_id)<>(b.source_counts->>'files')::bigint OR
      NOT EXISTS(SELECT 1 FROM hosting_controlplane.enterprise_record_history r WHERE r.organization_id=p_org
        AND r.tenant_id=p_tenant AND r.record_kind='Workload' AND r.record_id=p_workload
        AND r.revision=b.workload_revision AND r.record_digest=b.workload_digest)
    THEN RETURN false; END IF;
    FOR k IN SELECT x.* FROM hosting_controlplane.retained_conversion_keys x
      JOIN hosting_controlplane.retained_conversion_proofs p ON
        (x.organization_id,x.tenant_id,x.scope_digest,x.key_id,x.purpose)=
        (p.organization_id,p.tenant_id,p.scope_digest,p.key_id,p.purpose)
      WHERE p.organization_id=p_org AND p.tenant_id=p_tenant
        AND p.event_key IN(h.native_proof,h.exclusion_proof,h.owner_proof,h.security_proof,h.custody_proof)
      ORDER BY x.scope_digest,x.key_id,x.purpose FOR SHARE OF x LOOP
      IF clock_timestamp()>=k.valid_until THEN RETURN false; END IF;
    END LOOP;
    IF EXISTS(SELECT 1 FROM hosting_controlplane.retained_conversion_proofs p
        LEFT JOIN hosting_controlplane.retained_conversion_keys k ON
          (k.organization_id,k.tenant_id,k.scope_digest,k.key_id,k.purpose)=
          (p.organization_id,p.tenant_id,p.scope_digest,p.key_id,p.purpose)
        WHERE p.organization_id=p_org AND p.tenant_id=p_tenant
          AND p.event_key IN(h.native_proof,h.exclusion_proof,h.owner_proof,h.security_proof,h.custody_proof)
          AND (k.key_id IS NULL OR clock_timestamp()>=k.valid_until OR
            EXISTS(SELECT 1 FROM hosting_controlplane.retained_conversion_key_revocations r WHERE
              (r.organization_id,r.tenant_id,r.scope_digest,r.key_id,r.purpose)=
              (p.organization_id,p.tenant_id,p.scope_digest,p.key_id,p.purpose)))) THEN RETURN false; END IF;
    IF EXISTS(SELECT 1 FROM hosting_controlplane.retained_conversion_bindings n
        LEFT JOIN hosting_controlplane.native_ownership o USING(platform_family,endpoint_id,native_scope_id,resource_kind,native_id)
        WHERE n.organization_id=p_org AND n.tenant_id=p_tenant AND n.batch_id=b.batch_id
          AND (o.lease_epoch IS NULL OR o.lease_epoch<n.target_epoch OR
            (o.organization_id,o.tenant_id,o.security_domain_id,o.workload_id) IS DISTINCT FROM
            (p_org,p_tenant,p_wsd,p_workload))) THEN RETURN false; END IF;
    IF EXISTS(SELECT 1 FROM hosting_controlplane.retained_conversion_recovery r
        WHERE r.organization_id=p_org AND r.tenant_id=p_tenant AND r.batch_id=b.batch_id
          AND NOT EXISTS(SELECT 1 FROM hosting_controlplane.retained_conversion_resolutions s WHERE
            (s.organization_id,s.tenant_id,s.batch_id,s.operation_id,s.generation)=
            (r.organization_id,r.tenant_id,r.batch_id,r.operation_id,r.generation))) THEN RETURN false; END IF;
    RETURN true;
END $$;

CREATE FUNCTION hosting_controlplane.guard_retained_native_owner()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE b hosting_controlplane.retained_conversion_batches%ROWTYPE; n hosting_controlplane.retained_conversion_bindings%ROWTYPE;
BEGIN
    SELECT * INTO b FROM hosting_controlplane.retained_conversion_batches WHERE organization_id=NEW.organization_id
      AND tenant_id=NEW.tenant_id AND security_domain_id=NEW.security_domain_id AND workload_id=NEW.workload_id FOR SHARE;
    IF NOT FOUND THEN RETURN NEW; END IF;
    SELECT * INTO n FROM hosting_controlplane.retained_conversion_bindings WHERE organization_id=NEW.organization_id
      AND tenant_id=NEW.tenant_id AND batch_id=b.batch_id AND
      (platform_family,endpoint_id,native_scope_id,resource_kind,native_id)=
      (NEW.platform_family,NEW.endpoint_id,NEW.native_scope_id,NEW.resource_kind,NEW.native_id);
    IF TG_OP='INSERT' AND NEW.worker_id IS NULL AND NEW.lease_expires_at IS NULL
      AND NEW.lease_epoch=n.source_epoch AND n.native_id IS NOT NULL
    THEN RETURN NEW; END IF;
    IF TG_OP='UPDATE' AND OLD.worker_id IS NULL AND NEW.worker_id IS NULL AND
       OLD.lease_expires_at IS NULL AND NEW.lease_expires_at IS NULL AND OLD.lease_epoch=n.source_epoch
       AND NEW.lease_epoch=n.target_epoch AND EXISTS(SELECT 1 FROM hosting_controlplane.retained_conversion_handovers h
         WHERE h.organization_id=NEW.organization_id AND h.tenant_id=NEW.tenant_id AND h.batch_id=b.batch_id)
    THEN RETURN NEW; END IF;
    IF NOT hosting_controlplane.retained_conversion_write_is_admitted(NEW.organization_id,NEW.tenant_id,
      NEW.security_domain_id,NEW.workload_id) THEN RAISE EXCEPTION 'Converted native scope is observation-only'; END IF;
    IF TG_OP='UPDATE' AND NEW.lease_epoch<>OLD.lease_epoch AND NEW.lease_epoch<>OLD.lease_epoch+1
    THEN RAISE EXCEPTION 'Converted native epoch must advance exactly once'; END IF;
    IF TG_OP='UPDATE' AND OLD.worker_id IS NULL AND NEW.worker_id IS NULL AND NEW.lease_epoch<>OLD.lease_epoch
    THEN RAISE EXCEPTION 'An idle converted epoch requires authenticated handover'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER retained_native_owner_guard BEFORE INSERT OR UPDATE ON hosting_controlplane.native_ownership
 FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_retained_native_owner();

CREATE FUNCTION hosting_controlplane.accept_retained_conversion_handover(
    p_org text,p_tenant text,p_batch text,p_handover text,p_native text,p_exclusion text,
    p_owner text,p_security text,p_custody text,p_state_digest text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE b hosting_controlplane.retained_conversion_batches%ROWTYPE; p record; expected_purpose text;
    ids text[]; owners text[]; keys text[]; state jsonb; epochs jsonb; native_body jsonb;
    owner_body jsonb; exclusion_body jsonb; custody_body jsonb; deadline timestamptz; key_deadline timestamptz;
    n record; recovery record; task jsonb; original_native jsonb; original_exclusion jsonb;
BEGIN
    IF (p_org,p_tenant) IS DISTINCT FROM (current_setting('app.organization_id',true),current_setting('app.tenant_id',true))
    THEN RAISE EXCEPTION 'Exact retained tenant context required'; END IF;
    SELECT * INTO b FROM hosting_controlplane.retained_conversion_batches WHERE organization_id=p_org
      AND tenant_id=p_tenant AND batch_id=p_batch FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Retained batch is not visible'; END IF;
    IF EXISTS(SELECT 1 FROM hosting_controlplane.retained_conversion_handovers h WHERE h.organization_id=p_org
      AND h.tenant_id=p_tenant AND h.batch_id=p_batch) THEN
      IF EXISTS(SELECT 1 FROM hosting_controlplane.retained_conversion_handovers h WHERE h.organization_id=p_org
        AND h.tenant_id=p_tenant AND h.batch_id=p_batch AND h.handover_id=p_handover AND h.native_proof=p_native
        AND h.exclusion_proof=p_exclusion AND h.owner_proof=p_owner AND h.security_proof=p_security AND h.custody_proof=p_custody)
      THEN RETURN false; END IF;
      RAISE EXCEPTION 'Retained batch already has another handover';
    END IF;
    ids:=ARRAY[p_native,p_exclusion,p_owner,p_security,p_custody]; owners:=ARRAY[]::text[]; keys:=ARRAY[]::text[];
    FOR i IN 1..5 LOOP
      expected_purpose:=(ARRAY['NATIVE','EXCLUSION','OWNER','SECURITY','CUSTODY'])[i];
      SELECT e.*,k.valid_until AS key_until INTO p FROM hosting_controlplane.retained_conversion_proofs e
        JOIN hosting_controlplane.retained_conversion_keys k ON
          (k.organization_id,k.tenant_id,k.scope_digest,k.key_id,k.purpose)=
          (e.organization_id,e.tenant_id,e.scope_digest,e.key_id,e.purpose)
        WHERE e.organization_id=p_org AND e.tenant_id=p_tenant AND e.event_key=ids[i]
          AND e.purpose=expected_purpose AND e.batch_id=p_batch AND e.manifest_digest=b.manifest_digest
          AND e.scope_digest=b.scope_digest AND e.observed_at<=clock_timestamp() AND clock_timestamp()<e.fresh_until
          AND k.valid_from<=clock_timestamp() AND clock_timestamp()<k.valid_until
          AND NOT EXISTS(SELECT 1 FROM hosting_controlplane.retained_conversion_key_revocations r WHERE
            (r.organization_id,r.tenant_id,r.scope_digest,r.key_id,r.purpose)=
            (e.organization_id,e.tenant_id,e.scope_digest,e.key_id,e.purpose)) FOR SHARE OF e,k;
      IF NOT FOUND OR p.subject_id=ANY(owners) OR p.key_id=ANY(keys)
      THEN RAISE EXCEPTION 'Five distinct current independently verified handover proofs required'; END IF;
      owners:=array_append(owners,p.subject_id); keys:=array_append(keys,p.key_id);
      key_deadline:=LEAST(COALESCE(key_deadline,p.key_until),p.key_until);
      IF i=1 THEN native_body:=p.envelope->'statement';
      ELSIF i=2 THEN exclusion_body:=p.envelope->'statement';
      ELSIF i=3 THEN owner_body:=p.envelope->'statement';
      ELSIF i=4 AND owner_body IS DISTINCT FROM p.envelope->'statement'
      THEN RAISE EXCEPTION 'Owner and security reviewers must accept the same exact handover';
      ELSIF i=5 THEN custody_body:=p.envelope->'statement'; END IF;
    END LOOP;
    PERFORM 1 FROM hosting_controlplane.enterprise_records r WHERE r.organization_id=p_org AND r.tenant_id=p_tenant
      AND r.record_kind='Workload' AND r.record_id=b.workload_id FOR SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Original canonical workload is missing'; END IF;
    FOR n IN SELECT o.* FROM hosting_controlplane.retained_conversion_bindings x
      JOIN hosting_controlplane.native_ownership o USING(platform_family,endpoint_id,native_scope_id,resource_kind,native_id)
      WHERE x.organization_id=p_org AND x.tenant_id=p_tenant AND x.batch_id=p_batch
      ORDER BY x.platform_family,x.endpoint_id,x.native_scope_id,x.resource_kind,x.native_id FOR UPDATE OF o LOOP
      IF n.worker_id IS NOT NULL OR n.lease_expires_at IS NOT NULL OR
        (n.organization_id,n.tenant_id,n.security_domain_id,n.workload_id) IS DISTINCT FROM
        (p_org,p_tenant,b.security_domain_id,b.workload_id)
      THEN RAISE EXCEPTION 'Retained native owner is active, foreign or uncertain'; END IF;
    END LOOP;
    state:=hosting_controlplane.retained_conversion_state(p_org,p_tenant,p_batch);
    SELECT envelope->'statement' INTO original_native FROM hosting_controlplane.retained_conversion_proofs
      WHERE organization_id=p_org AND tenant_id=p_tenant AND event_key=b.native_proof;
    SELECT envelope->'statement' INTO original_exclusion FROM hosting_controlplane.retained_conversion_proofs
      WHERE organization_id=p_org AND tenant_id=p_tenant AND event_key=b.exclusion_proof;
    IF encode(sha256(convert_to(state::text,'UTF8')),'hex')<>p_state_digest OR
      (owner_body->>'reconciliationDigest') IS DISTINCT FROM p_state_digest OR
      (native_body->>'reconciliationDigest') IS DISTINCT FROM p_state_digest OR
      (exclusion_body->>'reconciliationDigest') IS DISTINCT FROM p_state_digest OR
      (custody_body->>'archiveInventoryDigest') IS DISTINCT FROM b.archive_inventory_digest OR
      (custody_body->'sourceBoundary') IS DISTINCT FROM b.source_boundary OR
      (exclusion_body->>'allExcluded') IS DISTINCT FROM 'true' OR
      (exclusion_body->>'queuedRequestsExcluded') IS DISTINCT FROM 'true' OR
      (exclusion_body->>'nativeTasksQuiesced') IS DISTINCT FROM 'true'
      OR (exclusion_body->'oldWriters') IS DISTINCT FROM original_exclusion->'oldWriters'
      OR (exclusion_body->>'retainedFreezeDigest') IS DISTINCT FROM original_exclusion->>'retainedFreezeDigest'
      OR (native_body->>'complete') IS DISTINCT FROM 'true'
      OR (native_body->>'retainedNativeDigest') IS DISTINCT FROM original_native->>'retainedNativeDigest'
      OR (native_body->'bindings') IS DISTINCT FROM original_native->'bindings'
      OR jsonb_typeof(native_body->'tasks') IS DISTINCT FROM 'array'
      OR jsonb_array_length(native_body->'bindings')<>jsonb_array_length(state->'nativeEpochs')
      OR jsonb_array_length(native_body->'tasks')<>jsonb_array_length(state->'recovery')
      OR EXISTS(SELECT 1 FROM jsonb_array_elements(native_body->'tasks') x GROUP BY x->>'operationId',x->>'generation' HAVING count(*)<>1)
    THEN RAISE EXCEPTION 'Original bytes, high-water marks, native state or exclusion do not agree'; END IF;
    SELECT jsonb_agg(jsonb_build_object('binding',jsonb_build_object('platformFamily',platform_family,
      'endpointId',endpoint_id,'nativeScopeId',native_scope_id,'resourceKind',resource_kind,'nativeId',native_id),
      'sourceEpoch',source_epoch,'targetEpoch',target_epoch) ORDER BY platform_family,endpoint_id,native_scope_id,resource_kind,native_id)
      INTO epochs FROM hosting_controlplane.retained_conversion_bindings WHERE organization_id=p_org AND tenant_id=p_tenant AND batch_id=p_batch;
    IF epochs IS NULL OR (owner_body->'nativeEpochs') IS DISTINCT FROM epochs OR
      (state->'workload'->>'digest') IS DISTINCT FROM b.workload_digest OR
      (state->>'historyCount')::bigint<>b.history_count OR
      (state->>'fileCount')::bigint<>(b.source_counts->>'files')::bigint OR
      EXISTS(SELECT 1 FROM jsonb_array_elements(state->'nativeEpochs') x WHERE
        x->>'currentEpoch' IS NULL OR (x->>'currentEpoch')::bigint<>(x->>'sourceEpoch')::bigint) OR
      EXISTS(SELECT 1 FROM jsonb_array_elements(state->'workflowHighWater') x WHERE x->>'status' NOT IN ('SUCCEEDED','FAILED','CANCELLED')) OR
      EXISTS(SELECT 1 FROM hosting_controlplane.native_operation_intents i JOIN hosting_controlplane.retained_conversion_bindings x USING
        (platform_family,endpoint_id,native_scope_id,resource_kind,native_id) WHERE x.organization_id=p_org
          AND x.tenant_id=p_tenant AND x.batch_id=p_batch AND i.state<>'RESOLVED') OR
      EXISTS(SELECT 1 FROM hosting_controlplane.native_containment_holds i JOIN hosting_controlplane.retained_conversion_bindings x USING
        (platform_family,endpoint_id,native_scope_id,resource_kind,native_id) WHERE x.organization_id=p_org AND x.tenant_id=p_tenant AND x.batch_id=p_batch)
    THEN RAISE EXCEPTION 'Original records, epochs, workflows or canonical native recovery are held'; END IF;
    deadline:=(owner_body->>'writeAdmissionUntil')::timestamptz;
    IF deadline IS NULL OR deadline<=clock_timestamp() OR deadline>clock_timestamp()+interval '1 hour' OR deadline>key_deadline
    THEN RAISE EXCEPTION 'Bounded fresh scope-specific write handover is required'; END IF;
    INSERT INTO hosting_controlplane.retained_conversion_handovers VALUES
      (p_org,p_tenant,p_batch,p_handover,p_native,p_exclusion,p_owner,p_security,p_custody,p_state_digest,epochs,deadline,clock_timestamp());
    FOR recovery IN SELECT * FROM hosting_controlplane.retained_conversion_recovery WHERE organization_id=p_org
      AND tenant_id=p_tenant AND batch_id=p_batch ORDER BY operation_id,generation LOOP
      SELECT x INTO task FROM jsonb_array_elements(native_body->'tasks') x
        WHERE x->>'operationId'=recovery.operation_id AND (x->>'generation')::bigint=recovery.generation;
      IF task IS NULL OR task->>'outcome' NOT IN ('NO_EFFECT','EFFECT_PRESENT') OR
         (task->>'nativeQuiesced') IS DISTINCT FROM 'true'
      THEN RAISE EXCEPTION 'Every original start requires independent current native no-replay disposition'; END IF;
      INSERT INTO hosting_controlplane.retained_conversion_resolutions VALUES
        (p_org,p_tenant,p_batch,recovery.operation_id,recovery.generation,p_native,p_exclusion,
         CASE task->>'outcome' WHEN 'NO_EFFECT' THEN 'NO_EFFECT_NO_REPLAY' ELSE 'EFFECT_PRESENT_NO_REPLAY' END);
    END LOOP;
    UPDATE hosting_controlplane.native_ownership o SET lease_epoch=x.target_epoch,updated_at=clock_timestamp()
      FROM hosting_controlplane.retained_conversion_bindings x WHERE x.organization_id=p_org AND x.tenant_id=p_tenant
        AND x.batch_id=p_batch AND (o.platform_family,o.endpoint_id,o.native_scope_id,o.resource_kind,o.native_id)=
          (x.platform_family,x.endpoint_id,x.native_scope_id,x.resource_kind,x.native_id) AND o.lease_epoch=x.source_epoch
        AND o.worker_id IS NULL AND o.lease_expires_at IS NULL;
    IF NOT hosting_controlplane.retained_conversion_write_is_admitted(p_org,p_tenant,b.security_domain_id,b.workload_id)
    THEN RAISE EXCEPTION 'Retained epoch advance did not reconcile'; END IF;
    RETURN true;
END $$;

DO $$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['retained_conversion_keys','retained_conversion_key_revocations','retained_conversion_proofs',
    'retained_conversion_batches','retained_conversion_files','retained_conversion_bindings','retained_conversion_recovery',
    'retained_conversion_handovers','retained_conversion_resolutions'] LOOP
    EXECUTE format('ALTER TABLE hosting_controlplane.%I ENABLE ROW LEVEL SECURITY',t);
    EXECUTE format('ALTER TABLE hosting_controlplane.%I FORCE ROW LEVEL SECURITY',t);
    EXECUTE format('CREATE POLICY conversion_tenant_scope ON hosting_controlplane.%I USING
      (organization_id=current_setting(''app.organization_id'',true) AND tenant_id=current_setting(''app.tenant_id'',true))
      WITH CHECK(organization_id=current_setting(''app.organization_id'',true) AND tenant_id=current_setting(''app.tenant_id'',true))',t);
    EXECUTE format('CREATE TRIGGER conversion_append_only BEFORE UPDATE OR DELETE ON hosting_controlplane.%I
      FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes()',t);
    EXECUTE format('REVOKE ALL ON hosting_controlplane.%I FROM PUBLIC',t);
  END LOOP;
END $$;
REVOKE ALL ON FUNCTION hosting_controlplane.check_retained_conversion_proof() FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.guard_retained_native_owner() FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.lock_retained_conversion_key_revocation() FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.check_retained_conversion_batch() FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.check_retained_conversion_binding() FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.retained_conversion_state(text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.retained_conversion_write_is_admitted(text,text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.accept_retained_conversion_handover(text,text,text,text,text,text,text,text,text,text) FROM PUBLIC;
