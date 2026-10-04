CREATE TABLE tenants (tenant_id text PRIMARY KEY, name text NOT NULL);
CREATE TABLE permits (
    tenant_id text NOT NULL REFERENCES tenants(tenant_id),
    permit_id text NOT NULL,
    title text NOT NULL,
    status text NOT NULL CHECK (status IN ('submitted', 'approved')),
    PRIMARY KEY (tenant_id, permit_id)
);
CREATE TABLE attachments (
    tenant_id text NOT NULL,
    attachment_id text NOT NULL,
    permit_id text NOT NULL,
    path text NOT NULL UNIQUE,
    sha256 text NOT NULL CHECK (length(sha256) = 64),
    bytes integer NOT NULL CHECK (bytes >= 0),
    file_mode text NOT NULL CHECK (file_mode = '0640'),
    PRIMARY KEY (tenant_id, attachment_id),
    FOREIGN KEY (tenant_id, permit_id) REFERENCES permits(tenant_id, permit_id)
);
CREATE TABLE write_markers (
    marker text PRIMARY KEY,
    tenant_id text NOT NULL REFERENCES tenants(tenant_id),
    description text NOT NULL
);
