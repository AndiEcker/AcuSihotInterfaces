create or replace view LOBBY.ACU_RES_LOG
  AS
select RUL_CODE, RUL_PRIMARY, RUL_ACTION, RUL_DATE
     , RUL_CHANGES        -- only needed for P_RUL_INSERT()
     , RUL_SIHOT_CAT, RUL_SIHOT_HOTEL, RUL_SIHOT_PACK, RUL_SIHOT_ROOM, RUL_SIHOT_OBJID, RUL_SIHOT_RATE
     , case when RUL_SIHOT_HOTEL = 4 and length(RUL_SIHOT_ROOM) = 3 then '0' end || RUL_SIHOT_ROOM as SIHOT_ROOM_NO
     , to_char(RUL_SIHOT_HOTEL) as SIHOT_HOTEL_C  -- fixing OCI-22054: underflow error
  from T_RUL l
 where nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin') -- remove Acumen LOBBY actions
   -- NOW REMOVED FROM T_RUL BY DBA_SIHOT_RES_SYNC: and RUL_USER <> 'SALES'        -- removing 8939 entries with AUTOBOOKING user renamings (possibly old support tasks)
   -- NOW EXCLUDED BY INNER JOIN TO T_RH: and (RUL_ACTION <> 'INSERT' or instr(RUL_CHANGES, 'RU_RHREF') > 0) -- exclude pending Marketing requests
   -- 5 times quicker with NOT EXISTS then with:
   --and RUL_CODE = (select max(c.RUL_CODE) from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY)  -- excluding past log entries
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and c.RUL_CODE > l.RUL_CODE)  -- excluding past log entries
   and RUL_DATE >= DATE'2012-01-01'   -- SPEED-UP: exclude reservatio log entries before 2012
 -- already ordered by V_ACU_RES_UNSYNCED: order by RUL_CODE
/*
  ae:12-07-16 first beta of combined RUL/AROL logs for 2016 and onwards.
  ae:20-07-16 V01: removed apartment reservations after refactoring T_SRSL and migrated USED/MAINPROC filters from V_ACU_RES_UNSYNCED. - NEVER ROLLED OUT
  ae:04-08-16 V02: added RUL_SIHOT columns.
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

