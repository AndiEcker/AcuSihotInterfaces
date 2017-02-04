create or replace view LOBBY.ACU_RES_FILTERED  -- filtered reservation migration/sync log and data (if RU got not deleted)
  AS
with resorts as (select LU_ID as RS_CODE, LU_NUMBER as HOTEL_ID from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ACTIVE = 1)
-- USING select *  from V_ACU_RES_DATA instead of outer joining here slows down the query from 
select V_ACU_RES_LOG.*
     , V_ACU_RES_DATA.*
  from V_ACU_RES_LOG
       left outer join V_ACU_RES_DATA on RUL_PRIMARY = RU_CODE
 where ( RU_CODE is NULL or ARR_DATE >= trunc(sysdate) or RUL_SIHOT_ROOM is not NULL )                             -- only migrate past reservations if room was assigned
   and ( (RUL_ACTION <> 'DELETE' and nvl(RU_STATUS, 0) <> 120) or RUL_SIHOT_OBJID is not NULL)  -- sync only res deletions/cancelations when res got already migrated/synced into SIHOT
   -- filtering hotels - since having RUL_SIHOT_HOTEL the RUL_CHANGES hotel filter is no longer needed
   --and ( exists (select NULL from resorts where RS_CODE = nvl(RU_RESORT, '_'))
   --   or ( RUL_ACTION = 'DELETE' and exists (select NULL from resorts where RS_CODE = substr(RUL_CHANGES, instr(RUL_CHANGES, 'RU_RESORT (') + 11, 3) ) ) )
   and exists (select NULL from resorts where HOTEL_ID = RUL_SIHOT_HOTEL)
   -- filtering resOcc types (SIHOT market segments) - since added RUL_SIHOT_RATE the RUL_CHANGES filter is no longer needed
   and RUL_SIHOT_RATE is not NULL
   --and ( RO_SIHOT_RATE is not NULL  -- only active market sources/resOcc types will be migrated/synced
   --   or ( RUL_ACTION = 'DELETE' and exists (select NULL from resoccs where RO_CODE = substr(RUL_CHANGES, instr(RUL_CHANGES, 'RU_ROREF (') + 10, 2) ) ) )
   -- ignoring reservation requests (and changes) with stays before 2012
   and (RU_CODE is NULL or DEP_DATE > DATE'2012-01-01')
   -- added filter for to block Thomas Cook bookings without a external booking ref (RH_EXT_BOOK_REF)
   and (RU_CODE is NULL or RU_ROREF not in ('TK', 'tk') or RH_EXT_BOOK_REF is not NULL) 
   -- exclude also bookings data are excluded via ACU_RES_DATA filter (e.g. A000xxx clients)
   and (RU_CODE is not NULL or not exists (select NULL from T_RU x where x.RU_CODE = RUL_PRIMARY))
/*
  ae:30-09-16 first beta of unsynced reservation changes for to be synced to SiHOT (split out of V_ACU_RES_UNSYNCED).
  ae:05-10-16 V01: extracted from V_ACU_RES_DATA (now renamed to V_ACU_RES_UNFILTERED).
  ae:25-01-17 V02: added filter for to prevent empty external booking ref for TK bookings.
  ae:02-02-17 V03: fixed bug to not include deleted RU records (by adding RU_CODE is NULL to the newly added TK booking filter).
*/
/


create or replace public synonym V_ACU_RES_FILTERED for LOBBY.ACU_RES_FILTERED;

grant select on LOBBY.ACU_RES_FILTERED to SALES_00_MASTER;
grant select on LOBBY.ACU_RES_FILTERED to SALES_05_SYSADMIN;
grant select on LOBBY.ACU_RES_FILTERED to SALES_06_DEVELOPER;
grant select on LOBBY.ACU_RES_FILTERED to SALES_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_FILTERED to SALES_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_FILTERED to XL_00_MASTER;
grant select on LOBBY.ACU_RES_FILTERED to XL_05_SYSADMIN;
grant select on LOBBY.ACU_RES_FILTERED to XL_06_DEVELOPER;
grant select on LOBBY.ACU_RES_FILTERED to XL_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_FILTERED to XL_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_FILTERED to REPORTER;

