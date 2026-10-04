-- B10 custody must survive a control-plane-only dump/restore. The native
-- database sync schema is commissioned and backed up separately; it cannot
-- own a trigger needed to restore the control-plane closure history.
DROP TRIGGER credential_closure_immutable
    ON hosting_controlplane.native_credential_issuance_closures;
CREATE TRIGGER credential_closure_immutable BEFORE UPDATE OR DELETE
    ON hosting_controlplane.native_credential_issuance_closures FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
