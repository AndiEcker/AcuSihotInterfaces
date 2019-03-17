create or replace view LOBBY.ACU_RES_UNSYNCED  -- filtered and unsynced reservation migration/sync log and data (if RU got not deleted)
  AS
select *
  from V_ACU_RES_FILTERED
 where not exists (select NULL from T_SRSL where SRSL_TABLE = 'RU' and SRSL_PRIMARY = RUL_PRIMARY and substr(SRSL_STATUS, 1, 6) = 'SYNCED' and SRSL_DATE >= RUL_DATE)
   --- TEST
   --and RU_CODE >= 1018389 -- 180046 are less/equal and 2058 are greater/equal
   --and RU_CODE = 1025884 --1024776  --1027947/TK@BHC --1018389/FB@BHH
   --and RUL_CODE = 4552688 -- adding this fixes the strange wrong RUL_SIHOT_HOTEL value error: 4 or 0 instead of 1
   --and (cd_code = 'B463787' or rul_sihot_room = '3503')
   order by RUL_DATE, RUL_CODE
/*
  ae:12-07-16 first beta of unsynced reservation changes for to be synced to SiHOT.
  ae:20-07-16 V01: removed apartment reservations, refactored for new T_SRSL, migrated resort filter from python project to here and migrated USED/MAINPROC filters onto V_ACU_RES_LOG. - NEVER ROLLED OUT.
  ae:05-08-16 V02: refactored for to use new RU_SIHOT/AP_SIHOT columns (CPA-pseudo resort in BHC/F004..., optimizing and managing ARO overloads) - later also refactored/split in V_ACU_RES_DATA.
  ae:23-09-16 V03: now also allow to import reservation history (but only if room got assigned).
  ae:27-09-16 V04: added ROREF filter for deleted RUs and moved RO_SIHOT_RATE is not NULL filter to V_ACU_RES_CORE because else other resOcc types would also be migrated/synched.
  ae:30-09-16 V05: split into V_ACU_RES_FILTERED.
  ae:17-09-17 V06: added RUL_DATE in order by clause for to ensure correct order for receycled/reused T_RUL records (done by P_RUL_INSERT()).
*/
/


create or replace public synonym V_ACU_RES_UNSYNCED for LOBBY.ACU_RES_UNSYNCED;

grant select on LOBBY.ACU_RES_UNSYNCED to SALES_00_MASTER;
grant select on LOBBY.ACU_RES_UNSYNCED to SALES_05_SYSADMIN;
grant select on LOBBY.ACU_RES_UNSYNCED to SALES_06_DEVELOPER;
grant select on LOBBY.ACU_RES_UNSYNCED to SALES_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_UNSYNCED to SALES_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_UNSYNCED to XL_00_MASTER;
grant select on LOBBY.ACU_RES_UNSYNCED to XL_05_SYSADMIN;
grant select on LOBBY.ACU_RES_UNSYNCED to XL_06_DEVELOPER;
grant select on LOBBY.ACU_RES_UNSYNCED to XL_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_UNSYNCED to XL_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_UNSYNCED to REPORTER;

