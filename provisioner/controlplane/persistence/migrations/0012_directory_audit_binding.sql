-- Bind the live IAM directory generation to the independently checkpointed
-- tenant audit stream. The resolver compares this marker with the current
-- directory row before issuing any principal. Historical enrollments from
-- 0009 receive a marker for their latest signed snapshot during this locked
-- migration; the original session IDs and grants never enter audit details.
LOCK TABLE hosting_controlplane.directory_subjects IN SHARE ROW EXCLUSIVE MODE;
LOCK TABLE hosting_controlplane.directory_sessions IN SHARE ROW EXCLUSIVE MODE;

ALTER TABLE hosting_controlplane.audit_events
    DROP CONSTRAINT audit_events_action_check,
    ADD CONSTRAINT audit_events_action_check CHECK (action IN
        ('RECORD_CREATE', 'RECORD_UPDATE', 'LEASE_ACQUIRE',
         'LEASE_RENEW', 'LEASE_RELEASE', 'WORKER_CERT_ENROLL',
         'WORKER_CERT_ROTATE', 'WORKER_CERT_REVOKE', 'WORKER_REVOKE',
         'DIRECTORY_SYNC'));
CREATE INDEX audit_directory_latest
    ON hosting_controlplane.audit_events
    (organization_id, tenant_id, actor_id, record_id, audit_sequence DESC)
    WHERE action = 'DIRECTORY_SYNC' AND record_kind = 'DirectorySubject';

-- Commit a digest of the complete materialized directory state as well as
-- the signed IAM payload digest. A row-only or session-only selective restore
-- must fail authentication even when the generation number is unchanged.
CREATE FUNCTION hosting_controlplane.directory_state_digest(
    p_issuer text, p_subject text)
RETURNS text LANGUAGE sql STABLE SET search_path = pg_catalog AS $$
    SELECT encode(sha256(convert_to(jsonb_build_object(
        'issuer', d.issuer,
        'subject', d.subject,
        'organizationId', d.organization_id,
        'tenantId', d.tenant_id,
        'identityKind', d.identity_kind,
        'active', d.active,
        'grants', d.grants,
        'generation', d.generation,
        'signedDigest', d.signed_digest,
        'sessions', COALESCE((
            SELECT jsonb_agg(jsonb_build_array(s.session_id,
                to_char(s.expires_at AT TIME ZONE 'UTC',
                        'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')) ORDER BY s.session_id)
              FROM hosting_controlplane.directory_sessions s
             WHERE s.issuer = d.issuer AND s.subject = d.subject
        ), '[]'::jsonb))::text, 'UTF8')), 'hex')
      FROM hosting_controlplane.directory_subjects d
     WHERE d.issuer = p_issuer AND d.subject = p_subject;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.directory_state_digest(text, text)
    FROM PUBLIC;

DO $$
DECLARE
    item record;
BEGIN
    FOR item IN SELECT issuer, subject, organization_id, tenant_id,
                       generation, signed_digest,
                       hosting_controlplane.directory_state_digest(
                           issuer, subject) AS state_digest
                  FROM hosting_controlplane.directory_subjects
                 ORDER BY organization_id, tenant_id, issuer, subject LOOP
        -- The migration owner still enforces FORCE RLS; scope is confined to
        -- this transaction and the chained trigger sees exactly this tenant.
        PERFORM set_config('app.organization_id', item.organization_id, true);
        PERFORM set_config('app.tenant_id', item.tenant_id, true);
        INSERT INTO hosting_controlplane.audit_events
            (organization_id, tenant_id, actor_id, correlation_id, action,
             record_kind, record_id, revision, record_digest, details)
        VALUES (item.organization_id, item.tenant_id,
                'iam-sync:' || item.issuer, item.signed_digest,
                'DIRECTORY_SYNC', 'DirectorySubject', item.subject,
                item.generation, item.signed_digest,
                jsonb_build_object('stateDigest', item.state_digest));
    END LOOP;
END;
$$;
