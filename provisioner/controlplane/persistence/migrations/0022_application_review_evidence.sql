-- Reuse the independently signed, append-only assessment evidence stream.
-- No browser write, owner assignment, native ownership or execution grant.
ALTER TABLE hosting_controlplane.assessment_inputs
    DROP CONSTRAINT assessment_inputs_kind_check;
ALTER TABLE hosting_controlplane.assessment_inputs
    ADD CONSTRAINT assessment_inputs_kind_check
    CHECK (kind IN ('INSTALLATION', 'ROUTE', 'CONTROL', 'APPLICATION_REVIEW'));
-- Existing RLS, immutable rows, unique bindings and role separation are retained.
-- The separate ingest role needs SELECT on drafts/generations/observations for
-- exact reference validation; deployment grants remain explicit and external.
