create or replace view LOBBY.ACU_RES_CORE -- unfiltered reservation data
  AS
select RU_CODE
     , RU_STATUS
     , RU_RESORT, RU_ATGENERIC
     , RU_FROM_DATE as ARR_DATE, RU_FROM_DATE + RU_DAYS as DEP_DATE
     , RU_ADULTS, RU_CHILDREN
     , RU_RHREF, RU_ROREF
     , RU_FLIGHT_AIRPORT, RU_FLIGHT_NO, RU_FLIGHT_LANDS, RU_FLIGHT_PICKUP
     --, RU_BOARDREF                  -- ordered meal plan - no longer needed since we are having RUL_SIHOT_PACK
     , upper(RU_SOURCE) as RU_SOURCE  -- merge member source ('o') with owner source ('O')
     , RU_SIHOT_OBJID
     , RO_RES_GROUP, RO_RES_CLASS, RO_SP_GROUP, RO_SIHOT_RATE
     --, RO_SIHOT_AGENCY_OBJID, RO_SIHOT_AGENCY_MC
     , RO_SIHOT_RES_GROUP, RO_SIHOT_SP_GROUP
     , RH_EXT_BOOK_REF
     --, RH_FROM_DATE, RH_TO_DATE
     , RH_GROUP_ID
     , RU_CDREF as CD_CODE, CD_CODE2
     , CD_SIHOT_OBJID, CD_SIHOT_OBJID2
     , CD_RCI_REF
     ---- caldulated columns
     , case when RO_SIHOT_AGENCY_OBJID is not NULL then RO_SIHOT_AGENCY_OBJID
            when RU_CDREF <> RH_OWREF then (select CD_SIHOT_OBJID from T_CD where CD_CODE = RH_OWREF) end as OC_SIHOT_OBJID
     , case when RO_SIHOT_AGENCY_MC is not NULL then RO_SIHOT_AGENCY_MC 
            when RU_CDREF <> RH_OWREF then RH_OWREF end as OC_CODE
     , F_SIHOT_CAT(RU_ATGENERIC || '@' || RU_RESORT) as SIHOT_CAT -- ordered CAT (==PCAT element)
     , nvl(RO_SIHOT_MKT_SEG, RU_ROREF) as SIHOT_MKT_SEG
     , trim(case when RU_CDREF <> RH_OWREF then RH_OWREF end
         || case when RU_FROM_DATE <> RH_FROM_DATE or RU_FROM_DATE + RU_DAYS <> RH_TO_DATE 
                 then ' ' || case when RU_FROM_DATE <> RH_FROM_DATE then '<' end || RU_RHREF || case when RU_FROM_DATE + RU_DAYS <> RH_TO_DATE then '>' end end
                      || case when RH_GROUP_ID > 0 then ' grp' || RH_GROUP_ID end) as SIHOT_LINK_GROUP
     , replace(replace(replace(RH_REQUNIT, chr(13) || chr(10), '|CR|'), chr(13), '|CR|'), chr(10), '|CR|') as SIHOT_TEC_NOTE   -- COMMENT is a reserverd key word for Oracle
     , replace(replace(replace(RH_REQUNIT, chr(13), ''), chr(10), ''), '  ', ' ') as SIHOT_NOTE   -- COMMENT is a reserverd key word for Oracle
     -- with any analytic function the query needs more than 17 minutes on SP.DEV - even with the WHEN CASE optimazation
     --, case when RU_FROM_DATE = RH_FROM_DATE then 1 else dense_rank() over (partition by RU_RHREF order by RU_FROM_DATE) end
     --, case when RU_FROM_DATE = RH_FROM_DATE then 1 else row_number() over (partition by RU_RHREF order by RU_FROM_DATE) end 
     --, RU_CODE  -- no longer needed because we can anyway not have a separate market segment for each room (RU)
     , '0' as SIHOT_ROOM_SEQ
  from T_RU
  inner join T_RO on RU_ROREF = RO_CODE
  inner join T_RH on RU_RHREF = RH_CODE
  inner join V_ACU_CD_DATA on RU_CDREF = CD_CODE
/*
  ae:12-09-16 first beta for SiHOT migration/sync project.
  ae:27-09-16 V01: added market source groups RO_SIHOT_RES_GROUP/RO_SIHOT_SP_GROUP.
*/
/


create or replace public synonym V_ACU_RES_CORE for LOBBY.ACU_RES_CORE;

grant select on LOBBY.ACU_RES_CORE to SALES_00_MASTER;
grant select on LOBBY.ACU_RES_CORE to SALES_05_SYSADMIN;
grant select on LOBBY.ACU_RES_CORE to SALES_06_DEVELOPER;
grant select on LOBBY.ACU_RES_CORE to SALES_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_CORE to SALES_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_CORE to XL_00_MASTER;
grant select on LOBBY.ACU_RES_CORE to XL_05_SYSADMIN;
grant select on LOBBY.ACU_RES_CORE to XL_06_DEVELOPER;
grant select on LOBBY.ACU_RES_CORE to XL_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_CORE to XL_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_CORE to REPORTER;

