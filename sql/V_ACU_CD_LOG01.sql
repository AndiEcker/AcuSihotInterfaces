create or replace view LOBBY.ACU_CD_LOG
  AS
select LOG_CODE as CDL_CODE, LOG_PRIMARY, LOG_DATE
  from T_LOG l
 where LOG_TABLE = 'CLIENT_DETAILS'
   and LOG_PRIMARY not like 'A%' and instr('0123456789', substr(LOG_PRIMARY, 2, 1)) > 0 and length(LOG_PRIMARY) = 7 -- excluding MAINTAIN and other pseudo clients
   and LOG_CODE = (select max(m.LOG_CODE) from T_LOG m where m.LOG_TABLE = l.LOG_TABLE and m.LOG_PRIMARY = l.LOG_PRIMARY)  -- excluding past log entries
   and LOG_DATE >= DATE'2006-01-01' -- speed-up: removing old/outdated log entries
/*
  ae:23-07-16 first beta.
  ae:02-10-16 refactored for speed-up.
*/
/


create or replace public synonym V_ACU_CD_LOG for LOBBY.ACU_CD_LOG;

grant select on LOBBY.ACU_CD_LOG to SALES_00_MASTER;
grant select on LOBBY.ACU_CD_LOG to SALES_05_SYSADMIN;
grant select on LOBBY.ACU_CD_LOG to SALES_06_DEVELOPER;
grant select on LOBBY.ACU_CD_LOG to SALES_10_SUPERVISOR;
grant select on LOBBY.ACU_CD_LOG to SALES_60_RESERVATIONS;

grant select on LOBBY.ACU_CD_LOG to XL_00_MASTER;
grant select on LOBBY.ACU_CD_LOG to XL_05_SYSADMIN;
grant select on LOBBY.ACU_CD_LOG to XL_06_DEVELOPER;
grant select on LOBBY.ACU_CD_LOG to XL_10_SUPERVISOR;
grant select on LOBBY.ACU_CD_LOG to XL_60_RESERVATIONS;

grant select on LOBBY.ACU_CD_LOG to REPORTER;

