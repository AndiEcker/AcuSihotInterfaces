create or replace view LOBBY.ACU_RES_UNFILTERED  -- unfiltered outer joined reservation log to core reservation data
  AS
select V_ACU_RES_LOG.*
     , V_ACU_RES_DATA.*
  from V_ACU_RES_LOG 
       left outer join V_ACU_RES_DATA on RUL_PRIMARY = RU_CODE
/*
  ae:12-09-16 first beta for SiHOT migration/sync project.
  ae:27-09-16 V01: removed RU_STATUS <> 120 and other filters
  ae:05-10-16 V02: renamed from V_ACU_RES_DATA to V_ACU_RES_UNFILTERED and V_ACU_RES_CORE to V_ACU_RES_DATA (similar to the V_ACU_CD_* views).
*/
/


create or replace public synonym V_ACU_RES_UNFILTERED for LOBBY.ACU_RES_UNFILTERED;

grant select on LOBBY.ACU_RES_UNFILTERED to SALES_00_MASTER;
grant select on LOBBY.ACU_RES_UNFILTERED to SALES_05_SYSADMIN;
grant select on LOBBY.ACU_RES_UNFILTERED to SALES_06_DEVELOPER;
grant select on LOBBY.ACU_RES_UNFILTERED to SALES_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_UNFILTERED to SALES_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_UNFILTERED to XL_00_MASTER;
grant select on LOBBY.ACU_RES_UNFILTERED to XL_05_SYSADMIN;
grant select on LOBBY.ACU_RES_UNFILTERED to XL_06_DEVELOPER;
grant select on LOBBY.ACU_RES_UNFILTERED to XL_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_UNFILTERED to XL_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_UNFILTERED to REPORTER;

