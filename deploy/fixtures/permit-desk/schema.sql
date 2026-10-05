BEGIN;
SET ROLE pd_owner;
CREATE SCHEMA app AUTHORIZATION pd_owner;
CREATE TABLE app.fixture_schema(version integer PRIMARY KEY CHECK(version=1));
INSERT INTO app.fixture_schema VALUES(1);
CREATE TABLE app.tenants(tenant_id text PRIMARY KEY CHECK(tenant_id IN ('t_demo','t_other')));
INSERT INTO app.tenants VALUES('t_demo'),('t_other');
CREATE TABLE app.permits (
  tenant_id text NOT NULL REFERENCES app.tenants,
  permit_id text NOT NULL CHECK(permit_id ~ '^[a-z][a-z0-9_]{0,47}$'),
  title text NOT NULL CHECK(length(title) BETWEEN 1 AND 120),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(tenant_id,permit_id)
);
CREATE TABLE app.attachments (
  tenant_id text NOT NULL,
  permit_id text NOT NULL,
  object_key text UNIQUE NOT NULL CHECK(object_key=tenant_id || '--' || permit_id || '.bin'),
  sha256 text NOT NULL CHECK(sha256 ~ '^[0-9a-f]{64}$'),
  bytes integer NOT NULL CHECK(bytes BETWEEN 1 AND 65536),
  PRIMARY KEY(tenant_id,permit_id),
  FOREIGN KEY(tenant_id,permit_id) REFERENCES app.permits(tenant_id,permit_id)
);
COMMIT;
