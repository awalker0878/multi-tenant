-- Console-owned session/cache inventory. Run as console_migrator, before replicas.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE console_owner;
CREATE TABLE IF NOT EXISTS app.sessions (
    id varchar(255) PRIMARY KEY,
    user_id varchar(255),
    ip_address varchar(45),
    user_agent text,
    payload text NOT NULL,
    last_activity integer NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_activity ON app.sessions(last_activity);
CREATE TABLE IF NOT EXISTS app.cache (
    key varchar(255) PRIMARY KEY,
    value text NOT NULL,
    expiration integer NOT NULL
);
CREATE TABLE IF NOT EXISTS app.cache_locks (
    key varchar(255) PRIMARY KEY,
    owner varchar(255) NOT NULL,
    expiration integer NOT NULL
);
GRANT SELECT,INSERT,UPDATE,DELETE ON app.sessions,app.cache,app.cache_locks TO console_runtime;
COMMIT;
