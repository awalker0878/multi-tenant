\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE assurance_owner;
CREATE TABLE app.evidence_uploads (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, job uuid NOT NULL, digest text NOT NULL,
 fingerprint text NOT NULL, metadata text NOT NULL, content text NOT NULL,
 uploaded_at bigint NOT NULL, retention_until bigint NOT NULL,
 UNIQUE(tenant,job,digest), CHECK(retention_until>uploaded_at), CHECK(octet_length(content)<=65536)
);
CREATE TABLE app.evidence_records (
 id uuid PRIMARY KEY REFERENCES app.evidence_uploads(id), tenant uuid NOT NULL,
 job uuid NOT NULL, receipt text NOT NULL
);
CREATE TABLE app.evidence_reviews (
 id uuid PRIMARY KEY, evidence uuid NOT NULL REFERENCES app.evidence_records(id),
 reviewer uuid NOT NULL, decision text NOT NULL CHECK(decision IN ('accepted_simulation','rejected')),
 recorded_at bigint NOT NULL
);
REVOKE ALL ON app.evidence_uploads,app.evidence_records,app.evidence_reviews FROM assurance_runtime;
GRANT SELECT,INSERT ON app.evidence_uploads,app.evidence_records,app.evidence_reviews TO assurance_runtime;
COMMIT;
