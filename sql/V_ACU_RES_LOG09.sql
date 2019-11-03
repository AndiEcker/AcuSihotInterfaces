create or replace view LOBBY.ACU_RES_LOG
  AS
select RUL_CODE, RUL_PRIMARY
     , RUL_ACTION
     , RUL_DATE
     , RUL_CHANGES        -- only needed for P_RUL_INSERT() and sys_core_sh.py (in debug mode)
     , RUL_SIHOT_CAT, RUL_SIHOT_HOTEL, RUL_SIHOT_PACK, RUL_SIHOT_ROOM, RUL_SIHOT_OBJID, RUL_SIHOT_RATE
     --, case when RUL_SIHOT_HOTEL = 4 and length(RUL_SIHOT_ROOM) = 3 then '0' end || RUL_SIHOT_ROOM as SIHOT_ROOM_NO
     --, to_char(RUL_SIHOT_HOTEL) as SIHOT_HOTEL_C
     , RUL_SIHOT_LAST_HOTEL
     --, to_char(RUL_SIHOT_LAST_HOTEL) as SIHOT_LAST_HOTEL_C
     , RUL_SIHOT_LAST_CAT
  from T_RUL l
 where nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin') -- remove Acumen LOBBY actions
   -- NOW REMOVED FROM T_RUL BY DBA_SIHOT_RES_SYNC: and RUL_USER <> 'SALES'        -- removing 8939 entries with AUTOBOOKING user renamings (possibly old support tasks)
   -- NOW EXCLUDED BY INNER JOIN TO T_RH: and (RUL_ACTION <> 'INSERT' or instr(RUL_CHANGES, 'RU_RHREF') > 0) -- exclude pending Marketing requests (unfortunately not working if pending get deleted)
   and (RUL_ACTION = 'UPDATE' and exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY and RU_RHREF is not NULL) or instr(RUL_CHANGES, 'RU_RHREF') > 0)
   -- 5 times quicker with NOT EXISTS then with: and RUL_CODE = (select max(c.RUL_CODE) from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY)  -- excluding past log entries
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)  -- excluding past log entries
   and RUL_DATE >= DATE'2012-01-01'   -- SPEED-UP: exclude reservation log entries before 2017
   and instr(RUL_SIHOT_CAT, '_') = 0
 -- already ordered by V_ACU_RES_UNSYNCED: order by RUL_CODE
/*
  ae:12-07-16 first beta of combined RUL/AROL logs for 2016 and onwards.
  ae:20-07-16 V01: removed apartment reservations after refactoring T_SRSL and migrated USED/MAINPROC filters from V_ACU_RES_UNSYNCED. - NEVER ROLLED OUT
  ae:04-08-16 V02: added RUL_SIHOT columns.
  ae:08-03-17 V03: changed RUL_DATE filter from 2012-01-01 to 2017-01-01 - NEVER ROLLED OUT.
  ae:10-03-17 V04: added SIHOT_LAST_HOTEL_C column and changed RUL_DATE filter from 2012-01-01 to 2017-01-01.
  ae:24-03-17 V05: added RUL_SIHOT_CAT filter for to prevent HOTMOVE errors for unsynced reservations.
  ae:15-09-17 V06: extended filter to include DELETE RUL_ACTIONS separately from UPDATE RUL_ACTIONS into sync queue.
  ae:19-09-17 V07: re-added refactored filter for pending marketing requests.
  ae:28-09-17 V08: changed RUL_DATE filter from 2017-01-01 back to 2012-01-01 - FOR BHH/HMC migration.
  ae:05-10-17 V09: fixed bug for to cancel Sihot reservation if marketing request set back to pending (changed buggy expression "instr(RUL_ACTION, 'RU_RHREF') > 0" into "instr(RUL_CHANGES, 'RU_RHREF') > 0").  
*/
/


create or replace public synonym V_ACU_RES_LOG for LOBBY.ACU_RES_LOG;

grant select on LOBBY.ACU_RES_LOG to SALES_00_MASTER;
grant select on LOBBY.ACU_RES_LOG to SALES_05_SYSADMIN;
grant select on LOBBY.ACU_RES_LOG to SALES_06_DEVELOPER;
grant select on LOBBY.ACU_RES_LOG to SALES_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_LOG to SALES_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_LOG to XL_00_MASTER;
grant select on LOBBY.ACU_RES_LOG to XL_05_SYSADMIN;
grant select on LOBBY.ACU_RES_LOG to XL_06_DEVELOPER;
grant select on LOBBY.ACU_RES_LOG to XL_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_LOG to XL_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_LOG to REPORTER;

