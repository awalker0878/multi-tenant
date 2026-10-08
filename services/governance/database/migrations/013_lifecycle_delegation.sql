\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
ALTER TABLE app.actor_delegations DROP CONSTRAINT actor_delegations_audience_check;
ALTER TABLE app.actor_delegations ADD CONSTRAINT actor_delegations_audience_check
 CHECK (audience IN ('catalogue','inventory','planning','assurance','lifecycle'));
COMMIT;
