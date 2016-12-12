drop user SIHOT_INTERFACE;

create user SIHOT_INTERFACE
  identified by <password>
  default tablespace users
  temporary tablespace TEMP
  profile default
  account unlock;

grant connect to SIHOT_INTERFACE;
grant SALES_60_RESERVATIONS to SIHOT_INTERFACE;
alter user SIHOT_INTERFACE default role all;

-- 3 System Privileges for SIHOT_INTERFACE (copied from REPORTER but not needed)
--  GRANT CREATE PROCEDURE TO SIHOT_INTERFACE;
--  GRANT CREATE PUBLIC SYNONYM TO SIHOT_INTERFACE;
--  GRANT CREATE SYNONYM TO SIHOT_INTERFACE;

-- 1 Tablespace Quota for SIHOT_INTERFACE 
alter user SIHOT_INTERFACE quota 100M on USERS;
