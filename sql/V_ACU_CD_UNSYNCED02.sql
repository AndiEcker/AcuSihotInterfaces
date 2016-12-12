create or replace view LOBBY.ACU_CD_UNSYNCED
  AS
select * from V_ACU_CD_FILTERED
 where not exists (select NULL from T_SRSL where SRSL_TABLE = 'CD' and SRSL_PRIMARY = LOG_PRIMARY and substr(SRSL_STATUS, 1, 6) = 'SYNCED' and SRSL_DATE >= LOG_DATE)
   order by CDL_CODE
/*
  ae:23-07-16 first beta.
  ae:23-09-16 added rentals filter.
  ae:02-10-16 refactored for speed-up and easier use from python (split out V_ACU_CD_FILTERED).
*/
/


create or replace public synonym V_ACU_CD_UNSYNCED for LOBBY.ACU_CD_UNSYNCED;

grant select on LOBBY.ACU_CD_UNSYNCED to SALES_00_MASTER;
grant select on LOBBY.ACU_CD_UNSYNCED to SALES_05_SYSADMIN;
grant select on LOBBY.ACU_CD_UNSYNCED to SALES_06_DEVELOPER;
grant select on LOBBY.ACU_CD_UNSYNCED to SALES_10_SUPERVISOR;
grant select on LOBBY.ACU_CD_UNSYNCED to SALES_60_RESERVATIONS;

grant select on LOBBY.ACU_CD_UNSYNCED to XL_00_MASTER;
grant select on LOBBY.ACU_CD_UNSYNCED to XL_05_SYSADMIN;
grant select on LOBBY.ACU_CD_UNSYNCED to XL_06_DEVELOPER;
grant select on LOBBY.ACU_CD_UNSYNCED to XL_10_SUPERVISOR;
grant select on LOBBY.ACU_CD_UNSYNCED to XL_60_RESERVATIONS;

grant select on LOBBY.ACU_CD_UNSYNCED to REPORTER;

