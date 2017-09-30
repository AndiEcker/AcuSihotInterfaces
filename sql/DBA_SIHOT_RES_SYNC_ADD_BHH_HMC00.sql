--- VERSION 00: first beta

-- max linesize - limitted by TOAD to 2000 (32767 is maximum for sqlPlus)
SET LINESIZE 32767
-- surpress page separator
SET NEWPAGE 0
SET PAGESIZE 0
-- add dbms_output.put_line onto spool log file
SET SERVEROUTPUT ON
-- trim trailing blanks from line end
SET TRIMSPOOL ON

spool DBA_SIHOT_RES_SYNC_ADD_BHH_HMC00.log
exec P_PROC_SET('DBA_SIHOT_RES_SYNC_ADD_BHH_HMC', '2017_V00', 'dev');


--prompt DDL CHANGES - first two already pre-rolled out on 14-09-2017 and the V_ACU_RES_LOG view on 16-09-2017 (including sync queue data clean-up done by insert into T_SRSL)
--
--@@E_ARO_UPDATE11.sql;
--
--@@F_RH_ARO_APT02.sql;
--
--prompt .. fix unvisible DELETE syncs (has to be done directly after a SihotResSync run for to not pass them to the Sihot system
--
--select 'Unsynced before=' || to_char(count(*)) from V_ACU_RES_UNSYNCED;
--
--@@V_ACU_RES_LOG06.sql;
--
--select 'Unsynced after V_ACU_RES_LOG fix=' || to_char(count(*)) from V_ACU_RES_UNSYNCED;
--
--insert into T_SRSL (SRSL_TABLE, SRSL_PRIMARY, SRSL_ACTION, SRSL_STATUS, SRSL_MESSAGE, SRSL_LOGREF)
--  select 'RU', RUL_PRIMARY, RUL_ACTION, 'SYNCED_FIX', 'manual bulk fix - see DBA_SIHOT_RES_SYNC_ADD_BHH_HMC.sql', RUL_CODE
--    from V_ACU_RES_UNSYNCED;
--
--commit;
--  
--select 'Unsynced after sync queue clean-up=' || to_char(count(*)) from V_ACU_RES_UNSYNCED;
--
--prompt 'Finished  -  End Of Script'
--exec P_PROC_SET('', '', '');
--spool off
--
-- THERE WAS ONE SYNC FROM OUR ACUMEN USERS - see DBA_SIHOT_RES_SYNC_ADD_BHH_HMC00_view_and_data_fix_on_LIVE.log
-- next query found 2 changes - 1st done by Nancy on 16-09-17 12:32:02 with RU_CODE/RUL_PRIMARY==1079508
-- .. and 2nd done by CREATE_PROSPECT at 12:36:37 RUL_PRIMARY==683411
--select * from t_rul
-- order by rul_date desc --code desc
--
---- check in T_SRSL - 1st one was for unsynced GSA resort, so 2nd is the one to delete from T_SRSL
--select * from T_SRSL where srsl_primary = '683411' --1079508'
--
--delete from T_SRSL where srsl_primary = '683411' and srsl_logref = '4916402'
-- AFTER THIS FIX: the deleted T_SRSL record got recreated by the next sync run at 13:02:33 - ALL FINE NOW


prompt initial checking for sync amount and discrepancies (see also at the end of this script - after adding BHH and HMC)

-- nearly 80k
select 'V_ACU_RES_FILTERED count=' || to_char(count(*))
     , 'Future Only=' || sum(case when ARR_DATE >= trunc(sysdate) then 1 end) as Future_Only
     , 'Present And Future=' || sum(case when DEP_DATE >= trunc(sysdate) then 1 end) as Present_And_Future
     , 'Present And Next Month=' || sum(case when DEP_DATE >= trunc(sysdate) and ARR_DATE <= trunc(sysdate) + 31 then 1 end) as Present_Plus_31Days
  from V_ACU_RES_FILTERED;

select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_PACK, RUL_SIHOT_ROOM, RUL_SIHOT_RATE, RUL_SIHOT_CAT, RUL_SIHOT_LAST_CAT, RU_RESORT, RUL_SIHOT_HOTEL, RUL_SIHOT_LAST_HOTEL, RU_RHREF
     , (select LU_NUMBER from T_AP, T_AT, T_LU where AP_ATREF = AT_CODE and AT_RSREF = LU_ID and LU_CLASS = 'SIHOT_HOTELS' and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')) as ROOM_HOTEL
  from V_ACU_RES_FILTERED
 where instr(RUL_SIHOT_PACK || RUL_SIHOT_ROOM || RUL_SIHOT_RATE || RUL_SIHOT_CAT || RUL_SIHOT_LAST_CAT || SIHOT_MKT_SEG, '_') > 0
    or RUL_SIHOT_HOTEL <= 0 or RUL_SIHOT_LAST_HOTEL <= 0
    or RUL_SIHOT_RATE is NULL
    or RUL_SIHOT_ROOM is not NULL and RUL_SIHOT_HOTEL <> nvl((select LU_NUMBER from T_AP, T_AT, T_LU where AP_ATREF = AT_CODE and AT_RSREF = LU_ID and LU_CLASS = 'SIHOT_HOTELS' and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')), -96);

select 'V_ACU_RES_UNSYNCED count=' || to_char(count(*))
     , 'Future Only=' || sum(case when ARR_DATE >= trunc(sysdate) then 1 end) as Future_Only
     , 'Present And Future=' || sum(case when DEP_DATE >= trunc(sysdate) then 1 end) as Present_And_Future
     , 'Present And Next Month=' || sum(case when DEP_DATE >= trunc(sysdate) and ARR_DATE <= trunc(sysdate) + 31 then 1 end) as Present_Plus_31Days
  from V_ACU_RES_UNSYNCED;

select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_PACK, RUL_SIHOT_ROOM, RUL_SIHOT_RATE, RUL_SIHOT_CAT, RUL_SIHOT_LAST_CAT, RU_RESORT, RUL_SIHOT_HOTEL, RUL_SIHOT_LAST_HOTEL, RU_RHREF
  from V_ACU_RES_UNSYNCED where RUL_SIHOT_HOTEL in (2, 3);



prompt DATA CHANGES

prompt add new lookup classes for to transform unit size to sihot cat (only ANY fallback need to specify transforms for all Acumen unit sizes: HOTEL/STUDIO..3 BED)

prompt ... default category fixes for BHC (see Q_TASK_TEST000.sql - line 790)

delete from T_LU where LU_CLASS = 'SIHOT_CATS_BHC' and LU_ID in ('HOTEL', 'HOTEL_757', '2 BED_757', '3 BED_752', '3 BED_757');
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHC', 'HOTEL', 'Hotel Unit', 100, 1, NULL,
          'HOTU', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHC', 'HOTEL_757', 'Hotel Unit High Floor', 103, 1, NULL,
          'HOTU', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHC', '2 BED_757', '3 Bedroom High Floor', 123, 1, NULL,
          '2BSH', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHC', '3 BED_752', '3 Bedroom Duplex', 132, 1, NULL,
          '3BPS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHC', '3 BED_757', '3 Bedroom High Floor', 133, 1, NULL,
          '3BPS', NULL, user, sysdate, user, sysdate);
commit;


prompt ... default category fixes for PBC (see Q_TASK_TEST000.sql - line 790) and removing 2 BED_757 from ANY because it is only used in PBC/BHC and created there explicitly

delete from T_LU where LU_CLASS = 'SIHOT_CATS_ANY' and LU_ID in ('2 BED_757');

delete from T_LU where LU_CLASS = 'SIHOT_CATS_PBC' and LU_ID in ('1 BED_781', '2 BED_781', '3 BED_757', '3 BED_781');
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PBC', '1 BED_781', '1 Bedroom Sea View', 414, 1, NULL,
          '1JNB', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PBC', '2 BED_781', '2 Bedroom Sea View', 424, 1, NULL,
          '22SB', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PBC', '3 BED_757', '3 Bedroom High Floor', 433, 1, NULL,
          '3BPB', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PBC', '3 BED_781', '3 Bedroom Sea View', 435, 1, NULL,
          '3BPB', NULL, user, sysdate, user, sysdate);
commit;


prompt ... BHH overloads

delete from T_LU where LU_CLASS = 'SIHOT_CATS_BHH';
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHH', '1 BED', '1 Bedroom', 211, 1, NULL,
          '1JNP', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHH', '1 BED_752', '1 Bedroom etage/duplex', 212, 1, NULL,
          '1DDP', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHH', '1 BED_757', '1 Bedroom etage/duplex sea view', 213, 1, NULL,
          '1DDS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHH', '1 BED_781', '1 Bedroom view/high floor', 215, 1, NULL,
          '1JNS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHH', '2 BED', '2 Bedroom', 221, 1, NULL,
          '2BSP', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHH', '2 BED_748', '2 Bedroom superior', 222, 1, NULL,
          '2BSS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHH', '2 BED_752', '2 Bedroom duplex pool view', 222, 1, NULL,
          '2DDP', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHH', '2 BED_757', '2 Bedroom High Floor', 224, 1, NULL,
          '2DDP', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHH', '2 BED_781', '2 Bedroom duplex sea view', 225, 1, NULL,
          '2DDS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHH', '3 BED_752', '3 Bedroom duplex', 232, 1, NULL,
          '3BPS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHH', '3 BED_757', '3 Bedroom high floor', 233, 1, NULL,
          '3BPS', NULL, user, sysdate, user, sysdate);
commit;


prompt ... HMC overloads

delete from T_LU where LU_CLASS = 'SIHOT_CATS_HMC';
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', 'STUDIO_757', 'Studio high floor', 303, 1, NULL,
          'STDS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', 'STUDIO_781', 'Studio sea view', 304, 1, NULL,
          'STDS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '1 BED', '1 Bedroom', 311, 1, NULL,
          '1JNP', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '1 BED_752', '1 Bedroom duplex', 312, 1, NULL,
          '1DDS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '1 BED_757', '1 Bedroom view/high floor', 313, 1, NULL,
          '1JNS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '1 BED_781', '1 Bedroom etage/duplex sea view', 314, 1, NULL,
          '1DDS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '2 BED', '2 Bedroom', 321, 1, NULL,
          '2BSP', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '2 BED_748', '2 Bedroom Superior', 322, 1, NULL,
          '2BSS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '2 BED_752', '2 Bedroom Duplex', 323, 1, NULL,
          '2DDO', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '2 BED_757', '2 Bedroom Duplex High Floor', 324, 1, NULL,
          '2BSS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '2 BED_781', '2 Bedroom Duplex Sea View', 325, 1, NULL,
          '2DDS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '3 BED', '3 Bedroom', 331, 1, NULL,
          '3DDS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '3 BED_752', '3 Bedroom duplex', 332, 1, NULL,
          '3DDS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '3 BED_757', '3 Bedroom high floor', 333, 1, NULL,
          '3DDS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '3 BED_781', '3 Bedroom duplex sea view', 334, 1, NULL,
          '3DDS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '4 BED', '4 Bedroom penthouse', 341, 1, NULL,
          '4BPS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '4 BED_752', '4 Bedroom penthouse', 343, 1, NULL,
          '4BPS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_HMC', '4 BED_757', '4 Bedroom high floor', 344, 1, NULL,
          '4BPS', NULL, user, sysdate, user, sysdate);
commit;


prompt activate BHH and HMC hotel lookups

update T_LU set LU_ACTIVE = 1 where LU_CLASS = 'SIHOT_HOTELS' and LU_ID in ('BHH', 'HMC');
commit;


prompt DATA CHANGES - part two

prompt setup Apartment Hotel IDs and room categories 
prompt .. first init all new AP columns first to their default values

update T_AP set AP_SIHOT_CAT = F_SIHOT_CAT((select AT_GENERIC || '@' || AT_RSREF from T_AT where AT_CODE = AP_ATREF)),
                AP_SIHOT_HOTEL = F_SIHOT_HOTEL((select AT_GENERIC || '@' || AT_RSREF from T_AT where AT_CODE = AP_ATREF))
 where (select AT_RSREF from T_AT where AT_CODE = AP_ATREF) in ('BHH', 'HMC')
   and (select AT_GENERIC from T_AT where AT_CODE = AP_ATREF) is not NULL;

commit;


prompt .. then overwrite/setup special apartment categories (non xTIC/HOTU) - first BHH then HMC

--select * from t_ap where ap_sihot_hotel in (2, 3) and instr(ap_sihot_cat, '_') > 0  -- 3503, 3520, 3523,

-- BHH
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J496';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J497';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J498';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J499';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'J500';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'J501';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J502';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J503';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J504';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J505';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J506';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J507';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J508';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J509';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J510';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J511';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J512';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'J514';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = 'J515';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J534';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'J535';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = 'J601';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'J602';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'J603';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'J604';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'J605';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'J606';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'J607';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'J608';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'J609';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'J610';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'J611';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'J612';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'J614';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = 'J615';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J616';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J617';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J618';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J619';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J620';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J621';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'J622';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = 'J636';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = 'J637';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J702';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J703';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J704';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J705';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J706';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J707';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J708';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J709';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J710';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J711';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J712';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J714';
update T_AP set AP_SIHOT_CAT = '1DDP' where AP_CODE = 'J716';
update T_AP set AP_SIHOT_CAT = '1DDP' where AP_CODE = 'J717';
update T_AP set AP_SIHOT_CAT = '1DDP' where AP_CODE = 'J718';
update T_AP set AP_SIHOT_CAT = '1DDP' where AP_CODE = 'J719';
update T_AP set AP_SIHOT_CAT = '1DDP' where AP_CODE = 'J720';
update T_AP set AP_SIHOT_CAT = '1DDP' where AP_CODE = 'J721';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J722';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J723';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J724';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J725';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J726';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J727';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J728';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J729';
update T_AP set AP_SIHOT_CAT = '2DDP' where AP_CODE = 'J730';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = 'J731';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = 'J732';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = 'J733';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = 'J734';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = 'J735';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = 'J736';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = 'J737';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = 'J738';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = 'J739';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = 'J740';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = 'J741';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = 'J742';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J743';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = 'J744';

-- HMC 
update T_AP set AP_SIHOT_CAT = '4BPS' where AP_CODE = '3503';
update T_AP set AP_SIHOT_CAT = '4BPS' where AP_CODE = '3520';
update T_AP set AP_SIHOT_CAT = '4BPS' where AP_CODE = '3523';


update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '1203';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '1204';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '1205';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '1301';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '1302';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '1303';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '1304';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '2101';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '2102';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '2103';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '2104';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '2105';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '2106';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '2201';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '2202';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '2203';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '2204';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '2205';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '2206';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = '2301';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '2302';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '2303';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '2304';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '2305';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '2306';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '3101';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '3102';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '3103';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '3104';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '3110';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3111';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3112';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3114';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3115';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3116';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '3117';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3134';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3135';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '3137';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3201';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '3202';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '3203';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '3204';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '3210';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3211';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3212';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3214';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3215';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3216';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3234';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3235';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '3237';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3301';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '3302';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '3303';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3304';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3310';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3311';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '3312';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '3314';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '3315';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3318';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3319';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3320';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3321';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3322';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3323';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3324';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3325';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3326';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3328';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3329';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3331';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3332';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3334';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '3335';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '3337';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3401';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3402';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3403';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3404';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3405';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3406';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3407';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3408';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3409';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3410';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3411';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3412';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3414';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3415';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3416';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3418';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3419';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3420';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3422';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3423';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3424';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3425';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3426';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3427';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3428';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3429';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3430';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3431';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3432';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3433';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3434';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3435';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3436';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3437';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3501';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3502';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3504';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '3505';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3510';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3511';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3512';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '3514';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3515';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3518';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3525';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3526';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '3528';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '3529';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3531';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '3532';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '3534';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '3535';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '3536';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '3537';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = '3618';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = '3625';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = '3626';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = '3631';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = '3632';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '4101';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '4103';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '4104';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '4105';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '4106';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '4108';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '4201';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '4203';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '4204';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '4205';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '4206';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '4208';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '4301';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '4303';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '4304';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '4306';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '4308';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '4403';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '4404';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '4406';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '4408';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '4501';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '4502';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '4503';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '4504';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '4505';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '4506';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '4507';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '4508';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '5102';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '5103';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '5106';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '5107';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '5118';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '5119';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '5122';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '5123';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '5201';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '5202';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '5218';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '5219';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '5220';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '5221';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '5222';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '5223';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '5224';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '5225';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '5317';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '5319';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '5320';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '5322';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '5324';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '5401';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '5402';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '5404';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '5418';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '5419';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '5422';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '5423';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5501';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5502';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5503';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5504';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5505';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5506';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5507';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5508';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5509';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5510';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5511';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5512';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5514';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5515';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5516';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5517';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5518';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5519';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5520';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5521';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5522';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5523';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5524';
update T_AP set AP_SIHOT_CAT = '1DDS' where AP_CODE = '5525';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6101';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6102';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '6103';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '6104';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6105';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6106';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6107';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6108';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6109';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6110';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6111';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6112';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6114';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6115';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6201';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6202';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = '6203';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = '6204';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6205';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6206';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6207';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6208';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6209';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6210';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6211';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6212';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6214';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = '6215';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = '6301';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = '6302';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = '6305';
update T_AP set AP_SIHOT_CAT = '2DDS' where AP_CODE = '6306';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '6307';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '6308';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '6309';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '6310';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '6311';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '6312';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '6314';
update T_AP set AP_SIHOT_CAT = '2DDO' where AP_CODE = '6315';


-- HMC - second run
update T_AP set AP_SIHOT_CAT = '3DDS' where AP_CODE = '3601';
update T_AP set AP_SIHOT_CAT = '3DDS' where AP_CODE = '3602';
update T_AP set AP_SIHOT_CAT = '3DDS' where AP_CODE = '3603';
update T_AP set AP_SIHOT_CAT = '3DDS' where AP_CODE = '3604';
update T_AP set AP_SIHOT_CAT = '3DDS' where AP_CODE = '3610';
update T_AP set AP_SIHOT_CAT = '3DDS' where AP_CODE = '3611';
update T_AP set AP_SIHOT_CAT = '3DDS' where AP_CODE = '3612';
update T_AP set AP_SIHOT_CAT = '3DDS' where AP_CODE = '3614';
update T_AP set AP_SIHOT_CAT = '3DDS' where AP_CODE = '3615';
update T_AP set AP_SIHOT_CAT = '3DDS' where AP_CODE = '3616';
update T_AP set AP_SIHOT_CAT = '3DDS' where AP_CODE = '6303';
update T_AP set AP_SIHOT_CAT = '3DDS' where AP_CODE = '6304';

commit;


prompt init RUL columns - (RARO RARO RARO) without the and 1=1 it shows a missing expression error

prompt .. first fix invalid data, like e.g. wrong apartment number for PBC rooms (missing leading zero) and values with underscore/_ in RUL_SIHOT_LAST_CAT

update T_RUL l set RUL_SIHOT_ROOM = '0' || RUL_SIHOT_ROOM
 where RUL_SIHOT_HOTEL in (-2, 4)
   -- opti (only update the newest ones / used by V_ACU_RES_LOG - need exact same filter/where expression)
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)
   and exists (select NULL from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = RUL_SIHOT_ROOM and AT_RSREF = 'PBC')
   and length(RUL_SIHOT_ROOM) = 3;
 
commit;

update T_RUL l set RUL_SIHOT_LAST_CAT = RUL_SIHOT_CAT
 where instr(RUL_SIHOT_CAT, '_') = 0 and instr(RUL_SIHOT_LAST_CAT, '_') > 0
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)
   and exists (select NULL from V_ACU_RES_FILTERED f where f.RUL_CODE = l.RUL_CODE); 

commit;



prompt .. then set only hotel room no (for to calculate later CAT/HOTEL based on the room), RATE and OBJID - needed 7:39 on SP.DEV
 
update T_RUL l
   set RUL_SIHOT_ROOM = F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1)
     , RUL_SIHOT_OBJID = (select RU_SIHOT_OBJID from T_RU where RU_CODE = RUL_PRIMARY)
     , RUL_SIHOT_RATE = (select RO_SIHOT_RATE from T_RU, T_RO where RU_ROREF = RO_CODE and RU_CODE = RUL_PRIMARY)
--select RUL_PRIMARY, (select RU_CDREF from T_RU where RU_CODE = RUL_PRIMARY) as RU_CDREF, (select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY) as RU_RHREF, (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY) as RU_FROM_DATE, (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY) as RU_TO_DATE, RUL_SIHOT_ROOM, F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1) as RH_ARO_APT, RUL_SIHOT_HOTEL, RUL_SIHOT_OBJID, (select RU_SIHOT_OBJID from T_RU where RU_CODE = RUL_PRIMARY) as RU_SIHOT_OBJID, RUL_SIHOT_RATE, (select RO_SIHOT_RATE from T_RU, T_RO where RU_ROREF = RO_CODE and RU_CODE = RUL_PRIMARY)as RO_SIHOT_RATE from t_rul l
 where RUL_DATE >= DATE'2012-01-01'   -- SPEED-UP: exclude reservatio log entries before 2012
   and exists (select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ID = (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY))
   and (select RU_ATGENERIC from T_RU where RU_CODE = RUL_PRIMARY) is not NULL
   -- opti (only update the newest ones / used by V_ACU_RES_LOG - need exact same filter/where expression)
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)  -- excluding past log entries
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   -- exclude invalid clients, cancellations in the past and also pending MKT records (RU_RHREF is not NULL) and prevent to include/flag invalid ones with non-empty RUL_SIHOT_RATE
   and exists (select NULL from T_RU, V_ACU_CD_DATA where RU_CODE = RUL_PRIMARY and RU_CDREF = CD_CODE 
                                                      and RU_FROM_DATE + RU_DAYS >= DATE'2012-01-01' and (RU_STATUS <> 120 or RU_FROM_DATE + RU_DAYS > trunc(sysdate)) and RU_RHREF is not NULL) 
   -- most discrepancies are from the SIHOT_ROOM value - only one discrepancy on the SIHOT_OBJID=1058520  B627146  09/05/2017  16/05/2017    5102  80904  80903  FB  FB
   and (RUL_SIHOT_ROOM <> F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1)
        or RUL_SIHOT_OBJID <> (select RU_SIHOT_OBJID from T_RU where RU_CODE = RUL_PRIMARY)
        or RUL_SIHOT_RATE <> (select RO_SIHOT_RATE from T_RU, T_RO where RU_ROREF = RO_CODE and RU_CODE = RUL_PRIMARY))
   --and 1=1
   --
   --order by (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY)
   ;

commit;

prompt .. then set HOTEL = 23 rows only (2:30 min on SP.DEV)
 
update T_RUL l
   set RUL_SIHOT_HOTEL = F_SIHOT_HOTEL(nvl(ltrim(RUL_SIHOT_ROOM, '0'), nvl(F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1), (select RU_ATGENERIC || '@' || RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY))))
--select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_ROOM, F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1) as RH_ARO_APT, (select RU_ATGENERIC || '@' || RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY) as RU_GEN, (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY) as RU_RESORT, RUL_SIHOT_HOTEL, F_SIHOT_HOTEL(nvl(ltrim(RUL_SIHOT_ROOM, '0'), nvl(F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1), (select RU_ATGENERIC || '@' || RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY)))) as NEW_HOTEL_NEW from T_RUL l
 where RUL_DATE >= DATE'2012-01-01'
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   and not exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY and RU_FROM_DATE + RU_DAYS < DATE'2012-01-01')
   and RUL_SIHOT_RATE is not NULL
   and RUL_SIHOT_HOTEL <> F_SIHOT_HOTEL(nvl(ltrim(RUL_SIHOT_ROOM, '0'), nvl(F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1), (select RU_ATGENERIC || '@' || RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY))))
   and F_SIHOT_HOTEL(nvl(ltrim(RUL_SIHOT_ROOM, '0'), nvl(F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1), (select RU_ATGENERIC || '@' || RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY)))) > 0
   and 1=1;

commit;


prompt .. then set CAT 

----- using F_SIHOT_CAT() slowed down this update to several days - for to speedup update will be done divided into several smaller chunks/cases
--update T_RUL l
--             set RUL_SIHOT_CAT = F_SIHOT_CAT(nvl(ltrim(RUL_SIHOT_ROOM, '0'), 'RU' || RUL_PRIMARY))  -- nvl needed for deleted RUs and for 20 cancelled RUs from 2014 with 'Sterling Suites' in RU_ATGENERIC - see line 138 in Q_SIHOT_SETUP2.sql
-- where RUL_DATE >= DATE'2012-01-01'
--   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)
--   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
--   and 1=1;

-- first all the ones with ARO/room associated and set to room's category = 250k rows in 32 sec on SP.TEST
update T_RUL l
   set RUL_SIHOT_CAT = (select AP_SIHOT_CAT from T_AP where AP_CODE = ltrim(RUL_SIHOT_ROOM, '0'))
--select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_ROOM, F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1) as RH_ARO_APT, (select RU_ATGENERIC || '@' || RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY) as RU_GEN, (select AT_GENERIC || '@' || AT_RSREF from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')) as AT_GEN, (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY) as RU_RESORT, RUL_SIHOT_CAT, (select AP_SIHOT_CAT from T_AP where AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')) as AP_SIHOT_CAT from T_RUL l
 where not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   -- Date speed-up on log/arrival dates - to support RU delete (outer join to T_RU) check RU arr date with not exists
   and RUL_DATE >= DATE'2012-01-01'
   and not exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY and RU_FROM_DATE + RU_DAYS < DATE'2012-01-01') 
   and RUL_SIHOT_ROOM is not NULL
   and RUL_SIHOT_RATE is not NULL 
   and exists (select NULL from T_AP where AP_CODE = ltrim(RUL_SIHOT_ROOM, '0'))
   and RUL_SIHOT_CAT <> (select AP_SIHOT_CAT from T_AP where AP_CODE = ltrim(RUL_SIHOT_ROOM, '0'));

commit;

-- then the ones without requested apt features = 14,5k rows
update T_RUL l
             set RUL_SIHOT_CAT = (select LU_CHAR from T_LU, T_RU
                                   where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end
                                     and LU_ID = RU_ATGENERIC
                                     and RU_CODE = RUL_PRIMARY)
--select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_ROOM, F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1) as RH_ARO_APT, (select RU_ATGENERIC || '@' || RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY) as RU_GEN, (select AT_GENERIC || '@' || AT_RSREF from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')) as AT_GEN, (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY) as RU_RESORT, (select AP_SIHOT_CAT from T_AP where AP_CODE = F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1)) as AP_SIHOT_CAT, RUL_SIHOT_CAT, (select LU_CHAR from T_LU, T_RU where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end and LU_ID = RU_ATGENERIC and RU_CODE = RUL_PRIMARY) as LU_SIHOT_CAT from T_RUL l
 where not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   -- Date speed-up on log/arrival dates - to support RU delete (outer join to T_RU) check RU arr date with not exists
   and RUL_DATE >= DATE'2012-01-01'
   and exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY 
                                           and RU_FROM_DATE + RU_DAYS >= DATE'2012-01-01'
                                           and RU_ATGENERIC in ('HOTEL', 'STUDIO', '1 BED', '2 BED', '3 BED') --, '4 BED')
                                           and RU_RESORT in ('BHH', 'HMC')
              )
   and RUL_SIHOT_ROOM is NULL
   and RUL_SIHOT_RATE is not NULL 
   and not exists (select NULL from T_RAF where RAF_RUREF = RUL_PRIMARY)
   and RUL_SIHOT_CAT <> (select LU_CHAR from T_LU, T_RU where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end and LU_ID = RU_ATGENERIC and RU_CODE = RUL_PRIMARY);

commit;

-- then finally the ones with requested apt features and category overload == 3 rows in 2 sec
update T_RUL l
             set RUL_SIHOT_CAT = (select max(LU_CHAR) from T_LU, T_RU, T_RAF
                                   where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end
                                     and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and RU_CODE = RAF_RUREF
                                     and RU_CODE = RUL_PRIMARY)
--select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_ROOM, F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1) as RH_ARO_APT, (select RU_ATGENERIC || '@' || RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY) as RU_GEN, (select AT_GENERIC || '@' || AT_RSREF from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')) as AT_GEN, (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY) as RU_RESORT, (select AP_SIHOT_CAT from T_AP where AP_CODE = F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1)) as AP_SIHOT_CAT, RUL_SIHOT_CAT, (select max(LU_CHAR) from T_LU, T_RU, T_RAF where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and RU_CODE = RAF_RUREF and RU_CODE = RUL_PRIMARY) as LU_SIHOT_CAT from T_RUL l
 where RUL_DATE >= DATE'2012-01-01'
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   and exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY 
                                           and RU_FROM_DATE + RU_DAYS >= DATE'2012-01-01'
                                           and RU_ATGENERIC in ('HOTEL', 'STUDIO', '1 BED', '2 BED', '3 BED') --, '4 BED')
                                           and RU_RESORT in ('BHH', 'HMC')
              )
   and RUL_SIHOT_ROOM is NULL
   and RUL_SIHOT_RATE is not NULL 
   and exists (select NULL from T_LU, T_RU, T_RAF
                                   where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end
                                     and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and RU_CODE = RAF_RUREF
                                     and RU_CODE = RUL_PRIMARY)
   and RUL_SIHOT_CAT <> (select max(LU_CHAR) from T_LU, T_RU, T_RAF where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and RU_CODE = RAF_RUREF and RU_CODE = RUL_PRIMARY);

commit;


prompt .. then finally set PACK (7 min on SP.TEST2, 3 min on SP.DEV)
 
--update T_RUL l
--             set RUL_SIHOT_PACK = case when F_SIHOT_PACK((select PRC_BOARDREF1 from T_RU, T_MS, T_PRC where RU_MLREF = MS_MLREF and MS_PRCREF = PRC_CODE and RU_CODE = RUL_PRIMARY), 'MKT_') != 'RO' 
--                                       then F_SIHOT_PACK((select PRC_BOARDREF1 from T_RU, T_MS, T_PRC where RU_MLREF = MS_MLREF and MS_PRCREF = PRC_CODE and RU_CODE = RUL_PRIMARY), 'MKT_')
--                                       --else F_SIHOT_PACK(nvl((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS) from T_RU where RU_CODE = RUL_PRIMARY),
--                                       --                      (select RU_BOARDREF from T_RU where RU_CODE = RUL_PRIMARY)))
--                                       when (select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'R') from T_RU where RU_CODE = RUL_PRIMARY) != 'RO'
--                                       then F_SIHOT_PACK((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'R') from T_RU where RU_CODE = RUL_PRIMARY))
--                                       else F_SIHOT_PACK((select RU_BOARDREF from T_RU where RU_CODE = RUL_PRIMARY)) 
--                                       end
-- where RUL_DATE >= DATE'2012-01-01'
--   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)
--   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
--   and exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY and RU_FROM_DATE + RU_DAYS >= DATE'2012-01-01') 
--   and 1=1;

update T_RUL l
             --OLD: set RUL_SIHOT_PACK = F_SIHOT_PACK((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'R') from T_RU where RU_CODE = RUL_PRIMARY))
             set RUL_SIHOT_PACK = F_SIHOT_PACK((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'x') from T_RU where RU_CODE = RUL_PRIMARY), case when (select substr(F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'x'), 1, 4) from T_RU where RU_CODE = RUL_PRIMARY) = 'MKT_' then 'MKT_' else '' end)
--select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_RATE, (select RU_ROREF from T_RU where RU_CODE = RUL_PRIMARY) as RU_ROREF, (select RU_BOARDREF from T_RU where RU_CODE = RUL_PRIMARY) as RU_BOARD, (select f_stragg(ARO_BOARDREF) from T_RU, T_ARO where RU_RHREF = ARO_RHREF and RU_FROM_DATE < ARO_EXP_DEPART and RU_FROM_DATE + RU_DAYS > ARO_EXP_ARRIVE and ARO_STATUS <> 120 and RU_CODE = RUL_PRIMARY) as ARO_BOARDS, (select f_stragg(PRC_BOARDREF1) from T_RU, T_ML, T_MS, T_PRC where RU_RHREF = ML_RHREF and ML_CODE = MS_MLREF and MS_PRCREF = PRC_CODE and RU_FROM_DATE < ML_REQDEPART_DATE and RU_FROM_DATE + RU_DAYS > ML_REQARRIVAL_DATE and RU_CODE = RUL_PRIMARY) as MKT_BOARDS,  RUL_SIHOT_PACK, F_SIHOT_PACK((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'x') from T_RU where RU_CODE = RUL_PRIMARY), case when (select substr(F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'x'), 1, 4) from T_RU where RU_CODE = RUL_PRIMARY) = 'MKT_' then 'MKT_' else '' end) from t_rul l 
 where RUL_DATE >= DATE'2012-01-01'
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   and exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY and RU_FROM_DATE + RU_DAYS >= DATE'2012-01-01')
   and RUL_SIHOT_RATE is not NULL 
   and RUL_SIHOT_PACK <> F_SIHOT_PACK((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'x') from T_RU where RU_CODE = RUL_PRIMARY), case when (select substr(F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'x'), 1, 4) from T_RU where RU_CODE = RUL_PRIMARY) = 'MKT_' then 'MKT_' else '' end);

commit;



prompt double-checking for sync amount and discrepancies

-- nearly 80k
select 'V_ACU_RES_FILTERED count=' || to_char(count(*))
     , 'Future Only=' || sum(case when ARR_DATE >= trunc(sysdate) then 1 end) as Future_Only
     , 'Present And Future=' || sum(case when DEP_DATE >= trunc(sysdate) then 1 end) as Present_And_Future
     , 'Present And Next Month=' || sum(case when DEP_DATE >= trunc(sysdate) and ARR_DATE <= trunc(sysdate) + 31 then 1 end) as Present_Plus_31Days
  from V_ACU_RES_FILTERED;

select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_PACK, RUL_SIHOT_ROOM, RUL_SIHOT_RATE, RUL_SIHOT_CAT, RUL_SIHOT_LAST_CAT, RU_RESORT, RUL_SIHOT_HOTEL, RUL_SIHOT_LAST_HOTEL, RU_RHREF
     , (select LU_NUMBER from T_AP, T_AT, T_LU where AP_ATREF = AT_CODE and AT_RSREF = LU_ID and LU_CLASS = 'SIHOT_HOTELS' and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')) as ROOM_HOTEL
  from V_ACU_RES_FILTERED
 where instr(RUL_SIHOT_PACK || RUL_SIHOT_ROOM || RUL_SIHOT_RATE || RUL_SIHOT_CAT || RUL_SIHOT_LAST_CAT || SIHOT_MKT_SEG, '_') > 0
    or RUL_SIHOT_HOTEL <= 0 or RUL_SIHOT_LAST_HOTEL <= 0
    or RUL_SIHOT_RATE is NULL
    or RUL_SIHOT_ROOM is not NULL and RUL_SIHOT_HOTEL <> nvl((select LU_NUMBER from T_AP, T_AT, T_LU where AP_ATREF = AT_CODE and AT_RSREF = LU_ID and LU_CLASS = 'SIHOT_HOTELS' and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')), -96);

select 'V_ACU_RES_UNSYNCED count=' || to_char(count(*))
     , 'Future Only=' || sum(case when ARR_DATE >= trunc(sysdate) then 1 end) as Future_Only
     , 'Present And Future=' || sum(case when DEP_DATE >= trunc(sysdate) then 1 end) as Present_And_Future
     , 'Present And Next Month=' || sum(case when DEP_DATE >= trunc(sysdate) and ARR_DATE <= trunc(sysdate) + 31 then 1 end) as Present_Plus_31Days
  from V_ACU_RES_UNSYNCED;

select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_PACK, RUL_SIHOT_ROOM, RUL_SIHOT_RATE, RUL_SIHOT_CAT, RUL_SIHOT_LAST_CAT, RU_RESORT, RUL_SIHOT_HOTEL, RUL_SIHOT_LAST_HOTEL, RU_RHREF
  from V_ACU_RES_UNSYNCED where RUL_SIHOT_HOTEL in (2, 3);


prompt 'Finished  -  End Of Script'
exec P_PROC_SET('', '', '');
spool off


