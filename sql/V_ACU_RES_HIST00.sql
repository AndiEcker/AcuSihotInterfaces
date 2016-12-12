create or replace view LOBBY.ACU_RES_HIST
  AS
with resorts as (select LU_ID as RS_CODE from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ACTIVE = 1)  -- there is no ANY resort for AROs
select ARO_CODE
     , ARO_CDREF as CD_CODE
     , trunc(ARO_TIMEIN) as ARR_DATE, trunc(ARO_TIMEOUT) as DEP_DATE
     , ARO_APREF
     , ARO_ADULTS as RU_ADULTS, ARO_CHILDREN as RU_CHILDREN
     , ARO_NOTE as NOTE
     , ARO_ROREF, ARO_RHREF
     , ARO_STATUS as SIHOT_STATUS
     , AT_RSREF as RU_RESORT, AT_GENERIC as RU_ATGENERIC
     , F_ARO_RU_CODE(ARO_RHREF, ARO_EXP_ARRIVE, ARO_EXP_DEPART) as RU_CODE
     , RH_EXT_BOOK_REF
  from T_ARO, T_AP, T_AT, T_RH
 where ARO_APREF = AP_CODE and AP_ATREF = AT_CODE
   and ARO_RHREF = RH_CODE
   and ARO_STATUS >= 300 and trunc(ARO_TIMEIN) < trunc(sysdate)
   and AT_RSREF in (select RS_CODE from resorts)
 order by ARO_EXP_ARRIVE
/*
  ae:30-07-16 first beta - UNFINISHED - NOT USED.
*/
/


create or replace public synonym V_ACU_RES_HIST for LOBBY.ACU_RES_HIST;

grant select on LOBBY.ACU_RES_HIST to SALES_00_MASTER;
grant select on LOBBY.ACU_RES_HIST to SALES_05_SYSADMIN;
grant select on LOBBY.ACU_RES_HIST to SALES_06_DEVELOPER;
grant select on LOBBY.ACU_RES_HIST to SALES_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_HIST to SALES_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_HIST to XL_00_MASTER;
grant select on LOBBY.ACU_RES_HIST to XL_05_SYSADMIN;
grant select on LOBBY.ACU_RES_HIST to XL_06_DEVELOPER;
grant select on LOBBY.ACU_RES_HIST to XL_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_HIST to XL_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_HIST to REPORTER;

