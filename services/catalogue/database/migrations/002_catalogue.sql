-- P03 owned state; execute once with the controlled migrator.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE catalogue_owner;
CREATE TABLE IF NOT EXISTS app.catalogue_references (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, kind text NOT NULL CHECK(kind IN ('environment','wsd','security-domain')),
 name varchar(200) NOT NULL, version bigint NOT NULL CHECK(version>0), retired boolean NOT NULL DEFAULT false,
 UNIQUE(tenant_id,id), UNIQUE(tenant_id,kind,name)
);
CREATE TABLE IF NOT EXISTS app.catalogue_reference_versions (
 tenant_id uuid NOT NULL, reference_id uuid NOT NULL, version bigint NOT NULL CHECK(version>0), definition jsonb NOT NULL,
 actor_id uuid NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(tenant_id,reference_id,version), FOREIGN KEY(tenant_id,reference_id) REFERENCES app.catalogue_references(tenant_id,id)
);
CREATE TABLE IF NOT EXISTS app.catalogue_applications (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, name varchar(200) NOT NULL, version bigint NOT NULL CHECK(version>0),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), UNIQUE(tenant_id,id)
);
CREATE INDEX IF NOT EXISTS catalogue_applications_page ON app.catalogue_applications(tenant_id,id);
CREATE TABLE IF NOT EXISTS app.catalogue_workloads (
 tenant_id uuid NOT NULL, id uuid NOT NULL, application_id uuid NOT NULL,
 PRIMARY KEY(tenant_id,id), UNIQUE(tenant_id,application_id,id),
 FOREIGN KEY(tenant_id,application_id) REFERENCES app.catalogue_applications(tenant_id,id)
);
CREATE TABLE IF NOT EXISTS app.catalogue_deployments (
 tenant_id uuid NOT NULL, id uuid NOT NULL, application_id uuid NOT NULL, environment_id uuid NOT NULL, current_revision_id uuid,
 PRIMARY KEY(tenant_id,id), UNIQUE(tenant_id,application_id,environment_id), UNIQUE(tenant_id,application_id,id),
 FOREIGN KEY(tenant_id,application_id) REFERENCES app.catalogue_applications(tenant_id,id),
 FOREIGN KEY(tenant_id,environment_id) REFERENCES app.catalogue_references(tenant_id,id)
);
CREATE TABLE IF NOT EXISTS app.catalogue_revisions (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, application_id uuid NOT NULL, deployment_id uuid NOT NULL,
 sequence bigint NOT NULL CHECK(sequence>0), parent_id uuid, actor_id uuid NOT NULL, digest char(64) NOT NULL,
 canonical_intent text NOT NULL CHECK(octet_length(canonical_intent)<=262144), created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(tenant_id,application_id,id), UNIQUE(tenant_id,application_id,deployment_id,id), UNIQUE(tenant_id,application_id,sequence),
 FOREIGN KEY(tenant_id,application_id,deployment_id) REFERENCES app.catalogue_deployments(tenant_id,application_id,id),
 FOREIGN KEY(tenant_id,application_id,deployment_id,parent_id) REFERENCES app.catalogue_revisions(tenant_id,application_id,deployment_id,id)
);
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='catalogue_current_revision' AND conrelid='app.catalogue_deployments'::regclass) THEN
ALTER TABLE app.catalogue_deployments ADD CONSTRAINT catalogue_current_revision FOREIGN KEY(tenant_id,application_id,id,current_revision_id)
 REFERENCES app.catalogue_revisions(tenant_id,application_id,deployment_id,id) DEFERRABLE INITIALLY DEFERRED;
END IF; END $$;
CREATE INDEX IF NOT EXISTS catalogue_revisions_page ON app.catalogue_revisions(tenant_id,application_id,sequence DESC);
CREATE TABLE IF NOT EXISTS app.catalogue_revision_references (
 tenant_id uuid NOT NULL, application_id uuid NOT NULL, revision_id uuid NOT NULL, reference_id uuid NOT NULL, reference_version bigint NOT NULL,
 PRIMARY KEY(tenant_id,revision_id,reference_id),
 FOREIGN KEY(tenant_id,application_id,revision_id) REFERENCES app.catalogue_revisions(tenant_id,application_id,id),
 FOREIGN KEY(tenant_id,reference_id,reference_version) REFERENCES app.catalogue_reference_versions(tenant_id,reference_id,version)
);
CREATE TABLE IF NOT EXISTS app.catalogue_revision_workloads (
 tenant_id uuid NOT NULL, application_id uuid NOT NULL, revision_id uuid NOT NULL, workload_id uuid NOT NULL,
 PRIMARY KEY(tenant_id,revision_id,workload_id),
 FOREIGN KEY(tenant_id,application_id,revision_id) REFERENCES app.catalogue_revisions(tenant_id,application_id,id),
 FOREIGN KEY(tenant_id,application_id,workload_id) REFERENCES app.catalogue_workloads(tenant_id,application_id,id)
);
CREATE TABLE IF NOT EXISTS app.catalogue_commands (
 tenant_id uuid NOT NULL, actor_id uuid NOT NULL, command_key uuid NOT NULL, fingerprint char(64) NOT NULL,
 response jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY(tenant_id,actor_id,command_key)
);
CREATE TABLE IF NOT EXISTS app.catalogue_audit (
 event_id uuid PRIMARY KEY, tenant_id uuid NOT NULL, actor_id uuid NOT NULL, resource_id uuid NOT NULL, sequence bigint NOT NULL,
 event_type text NOT NULL, envelope text NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(tenant_id,resource_id,sequence)
);
CREATE TABLE IF NOT EXISTS app.catalogue_outbox (
 event_id uuid PRIMARY KEY REFERENCES app.catalogue_audit(event_id), envelope text NOT NULL,
 resource_id uuid NOT NULL, sequence bigint NOT NULL, queued_at timestamptz NOT NULL DEFAULT clock_timestamp(), published_at timestamptz
);
CREATE INDEX IF NOT EXISTS catalogue_outbox_pending ON app.catalogue_outbox(queued_at,event_id) WHERE published_at IS NULL;
GRANT SELECT,INSERT ON app.catalogue_reference_versions,app.catalogue_workloads,app.catalogue_revisions,app.catalogue_revision_references,
 app.catalogue_revision_workloads,app.catalogue_commands,app.catalogue_audit,app.catalogue_outbox TO catalogue_runtime;
GRANT SELECT,INSERT ON app.catalogue_references,app.catalogue_applications,app.catalogue_deployments TO catalogue_runtime;
GRANT UPDATE(version,retired) ON app.catalogue_references TO catalogue_runtime;
GRANT UPDATE(version) ON app.catalogue_applications TO catalogue_runtime;
GRANT UPDATE(current_revision_id) ON app.catalogue_deployments TO catalogue_runtime;
GRANT UPDATE(published_at) ON app.catalogue_outbox TO catalogue_runtime;
COMMIT;
