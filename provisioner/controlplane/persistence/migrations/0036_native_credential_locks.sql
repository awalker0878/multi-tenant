-- Issuance and closure serialize on their original immutable B10 grant.
-- Row locking requires UPDATE privilege; the runtime receives only EXECUTE.
CREATE FUNCTION hosting_controlplane.lock_native_credential_grant(
    p_org text,p_tenant text,p_grant text) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE original text;
BEGIN
    IF p_org IS DISTINCT FROM current_setting('app.organization_id',true)
       OR p_tenant IS DISTINCT FROM current_setting('app.tenant_id',true)
       OR current_setting('transaction_isolation')<>'read committed'
       OR hosting_controlplane.is_site_worker_role()
       OR pg_has_role(session_user,'hosting_site_worker_roles','member') THEN
        RAISE EXCEPTION 'Original credential custody requires the tenant service'
            USING ERRCODE='42501';
    END IF;
    SELECT g.grant_id INTO original FROM hosting_controlplane.worker_grants g
        WHERE (g.organization_id,g.tenant_id,g.grant_id)=(p_org,p_tenant,p_grant)
        FOR UPDATE;
    RETURN original;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.lock_native_credential_grant(text,text,text) FROM PUBLIC;

-- Protect direct SQL append paths as well as the concrete issuer/retirement
-- owner. A concurrent closure must never leave a later credential attempt.
CREATE FUNCTION hosting_controlplane.guard_native_credential_custody_append()
RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,hosting_controlplane AS $$
BEGIN
    IF hosting_controlplane.lock_native_credential_grant(
        NEW.organization_id,NEW.tenant_id,NEW.grant_id) IS NULL THEN
        RAISE EXCEPTION 'Original credential grant is unavailable' USING ERRCODE='42501';
    END IF;
    IF TG_TABLE_NAME='native_credential_attempts' AND EXISTS(
        SELECT 1 FROM hosting_controlplane.native_credential_issuance_closures c
        WHERE (c.organization_id,c.tenant_id,c.grant_id)=
              (NEW.organization_id,NEW.tenant_id,NEW.grant_id)) THEN
        RAISE EXCEPTION 'Original credential issuance is durably closed' USING ERRCODE='42501';
    END IF;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.guard_native_credential_custody_append() FROM PUBLIC;
CREATE TRIGGER native_credential_attempt_serialization BEFORE INSERT
    ON hosting_controlplane.native_credential_attempts FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.guard_native_credential_custody_append();
CREATE TRIGGER native_credential_closure_serialization BEFORE INSERT
    ON hosting_controlplane.native_credential_issuance_closures FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.guard_native_credential_custody_append();
