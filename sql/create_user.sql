-- Initial Postgresql user - created programatically (see also AssCahceSync.py - lines 161 ff)
-- CREATE USER ass_interfaces WITH
--   LOGIN
--  NOSUPERUSER
--  INHERIT
--  NOCREATEDB
--  NOCREATEROLE
--  NOREPLICATION;

-- ipython notebook user (created manually within PgAdmin4)
CREATE USER itdev_support WITH
	LOGIN
	NOSUPERUSER
	NOCREATEDB
	NOCREATEROLE
	INHERIT
	NOREPLICATION
	CONNECTION LIMIT -1
	PASSWORD 'xxxxxx';

COMMENT ON ROLE itdev_support IS 'used e.g. for owner exchanges and suspensions (ipython notebooks)';

-- .. while the following changes (done programatically for ass_interfaces user were not done for itdev_support user)!!!
--GRANT ALL PRIVILEGES ON DATABASE ass_cache to itdev_support;
--ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO itdev_support;
--ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO itdev_support;
--ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO itdev_support;




-- USER ACCOUNT admin_sql
-- created manually on test

CREATE USER admin_sql WITH
	LOGIN
	SUPERUSER
	CREATEDB
	CREATEROLE
	INHERIT
	REPLICATION
	CONNECTION LIMIT -1
	PASSWORD 'xxxxxx';
GRANT postgres TO admin_sql WITH ADMIN OPTION;


-- copied SQL from pgAdmin from live (after moving to db2v.acumen.es)
CREATE USER admin_sql WITH
  LOGIN
  SUPERUSER
  INHERIT
  CREATEDB
  CREATEROLE
  REPLICATION;

GRANT postgres TO admin_sql WITH ADMIN OPTION;

