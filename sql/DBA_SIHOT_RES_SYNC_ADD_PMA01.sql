--- VERSION 00: first beta
--- VERSION 01: post-roll-out fixes (never used, only for to prepare roll-out of other CPA resorts)

-- Other system configuration changes for to add a new resort:
-- * .console_app_env.cfg: configure new resort in INI vars hotelIds, resortCats
--  and in section RcResortIds.
-- * add new hotel and room categories to Salesforce.

-- max linesize - limitted by TOAD to 2000 (32767 is maximum for sqlPlus)
SET LINESIZE 32767
-- surpress page separator
SET NEWPAGE 0
SET PAGESIZE 0
-- add dbms_output.put_line onto spool log file
SET SERVEROUTPUT ON
-- trim trailing blanks from line end
SET TRIMSPOOL ON

spool DBA_SIHOT_RES_SYNC_ADD_PMA00.log
exec P_PROC_SET('DBA_SIHOT_RES_SYNC_ADD_PMA', '2019_V00', 'dev');


prompt initial checking for sync amount and discrepancies (see also at the end of this script - after adding new resort)

-- nearly 80k
select 'V_ACU_RES_FILTERED count=' || to_char(count(*))
     , 'Future Only=' || sum(case when ARR_DATE >= trunc(sysdate) then 1 end) as Future_Only
     , 'Present And Future=' || sum(case when DEP_DATE >= trunc(sysdate) then 1 end) as Present_And_Future
     , 'Present And Next Month=' || sum(case when DEP_DATE >= trunc(sysdate) and ARR_DATE <= trunc(sysdate) + 31 then 1 end) as Present_Plus_31Days
  from V_ACU_RES_FILTERED
 where exists (select NULL from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = RUL_SIHOT_ROOM and AT_RSREF = 'PMA')
       or RUL_SIHOT_HOTEL = '107';

select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_PACK, RUL_SIHOT_ROOM, RUL_SIHOT_RATE, RUL_SIHOT_CAT, RUL_SIHOT_LAST_CAT, RU_RESORT, RUL_SIHOT_HOTEL, RUL_SIHOT_LAST_HOTEL, RU_RHREF, RU_ROREF, CD_CODE, OC_CODE
     , (select LU_NUMBER from T_AP, T_AT, T_LU where AP_ATREF = AT_CODE and AT_RSREF = LU_ID and LU_CLASS = 'SIHOT_HOTELS' and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')) as ROOM_HOTEL
  from V_ACU_RES_FILTERED
 where instr(RUL_SIHOT_PACK || RUL_SIHOT_ROOM || RUL_SIHOT_RATE || RUL_SIHOT_CAT || RUL_SIHOT_LAST_CAT || SIHOT_MKT_SEG, '_') > 0
    or RUL_SIHOT_HOTEL <= 0 or RUL_SIHOT_LAST_HOTEL <= 0
    or RUL_SIHOT_RATE is NULL
    or RUL_SIHOT_ROOM is not NULL and RUL_SIHOT_HOTEL <> nvl((select LU_NUMBER from T_AP, T_AT, T_LU where AP_ATREF = AT_CODE and AT_RSREF = LU_ID and LU_CLASS = 'SIHOT_HOTELS' and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')), -96);


prompt V_ACU_RES_UNFILTERED check query

select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_PACK, RUL_SIHOT_ROOM, RUL_SIHOT_RATE, RUL_SIHOT_CAT, RUL_SIHOT_LAST_CAT, RU_RESORT, RUL_SIHOT_HOTEL, RUL_SIHOT_LAST_HOTEL, RU_RHREF, RU_ROREF, CD_CODE, OC_CODE
     , (select LU_NUMBER from T_AP, T_AT, T_LU where AP_ATREF = AT_CODE and AT_RSREF = LU_ID and LU_CLASS = 'SIHOT_HOTELS' and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')) as ROOM_HOTEL
  from V_ACU_RES_UNFILTERED
 where instr(RUL_SIHOT_PACK || RUL_SIHOT_ROOM || RUL_SIHOT_RATE || RUL_SIHOT_CAT || RUL_SIHOT_LAST_CAT || SIHOT_MKT_SEG, '_') > 0
    or RUL_SIHOT_HOTEL <= 0 or RUL_SIHOT_LAST_HOTEL <= 0
    or RUL_SIHOT_RATE is NULL
    or RUL_SIHOT_ROOM is not NULL and RUL_SIHOT_HOTEL <> nvl((select LU_NUMBER from T_AP, T_AT, T_LU where AP_ATREF = AT_CODE and AT_RSREF = LU_ID and LU_CLASS = 'SIHOT_HOTELS' and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')), -96);

prompt double directly check against T_RU if missing all|2019+|future reservations

select 'T_RU count=' || to_char(count(*))
     , 'Future Only=' || sum(case when RU_FROM_DATE >= trunc(sysdate) then 1 end) as Future_Only
     , 'Present And Future=' || sum(case when RU_FROM_DATE + RU_DAYS >= trunc(sysdate) then 1 end) as Present_And_Future
     , 'Present And Next Month=' || sum(case when RU_FROM_DATE + RU_DAYS >= trunc(sysdate) and RU_FROM_DATE <= trunc(sysdate) + 31 then 1 end) as Present_Plus_31Days
  from T_RU
 where ru_status <> 120
   and (ru_resort = 'PMA'
        or exists (select NULL from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = F_RH_ARO_APT(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS) and AT_RSREF = 'PMA')
        );
 
select ru_code, ru_boardref, F_RH_ARO_APT(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS) as room, ru_roref, ru_atgeneric, ru_resort, ru_rhref, ru_cdref
     --, (select f_stragg(RUL_CODE) from T_RUL where RUL_PRIMARY = ru_code) as RUL_CODES
     --, (select f_stragg(srsl_status || '@' || srsl_date) from t_srsl where srsl_primary = to_char(ru_code)) as SRSL_ENTRIES
  from t_ru
 where ru_status <> 120
   and (ru_resort = 'PMA'
        or exists (select NULL from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = F_RH_ARO_APT(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS) and AT_RSREF = 'PMA')
        -- uncomment to triple-check (VERY VERY SLOW): or exists (select NULL from V_ACU_RES_LOG where RUL_PRIMARY = RU_CODE and RUL_SIHOT_HOTEL = 107)
       )
   -- additional filters for discrep checks
--   and ( not exists (select NULL from t_srsl where srsl_primary = to_char(ru_code) and srsl_date > DATE'2019-03-13' and substr(srsl_status, 1, 6) = 'SYNCED')
--        or ru_sihot_objid is NULL )
--   and ru_from_date + ru_days > DATE'2019-01-01' --2016-01-01'
--   and exists (select NULL from t_ro where ro_code = ru_roref and ro_sihot_rate is not NULL)
 order by ru_from_date desc;


prompt UNSYNCED check

select 'V_ACU_RES_UNSYNCED count=' || to_char(count(*))
     , 'Future Only=' || sum(case when ARR_DATE >= trunc(sysdate) then 1 end) as Future_Only
     , 'Present And Future=' || sum(case when DEP_DATE >= trunc(sysdate) then 1 end) as Present_And_Future
     , 'Present And Next Month=' || sum(case when DEP_DATE >= trunc(sysdate) and ARR_DATE <= trunc(sysdate) + 31 then 1 end) as Present_Plus_31Days
  from V_ACU_RES_UNSYNCED;

select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_PACK, RUL_SIHOT_ROOM, RUL_SIHOT_RATE, RUL_SIHOT_CAT, RUL_SIHOT_LAST_CAT, RU_RESORT, RUL_SIHOT_HOTEL, RUL_SIHOT_LAST_HOTEL, RU_RHREF
  from V_ACU_RES_UNSYNCED where RUL_SIHOT_HOTEL in (107);



prompt DATA CHANGES

prompt ... insert resort configuration overloads

delete from T_LU where LU_CLASS = 'SIHOT_CATS_PMA';
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PMA', '1 BED', '1 Bedroom', 711, 1, NULL,
          '1JNR', NULL, user, sysdate, user, sysdate);

insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PMA', '2 BED', '2 Bedroom', 721, 1, NULL,
          '2BSU', NULL, user, sysdate, user, sysdate);
-- finally not used because of the RCI allotment/contract overbooking problem
--insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
--                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
--  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PMA', '2 BED_752', '2 Bedroom duplex', 722, 1, NULL,
--          '2DDO', NULL, user, sysdate, user, sysdate);


insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PMA', '3 BED', '3 Bedroom', 731, 1, NULL,
          '3BPS', NULL, user, sysdate, user, sysdate);

insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PMA', '4 BED', '4 Bedroom', 741, 1, NULL,
          '4BPS', NULL, user, sysdate, user, sysdate);
commit;


prompt activate new resort in sihot hotel lookups

update T_LU set LU_ACTIVE = 1 where LU_CLASS = 'SIHOT_HOTELS' and LU_ID in ('PMA');
commit;


prompt DATA CHANGES - part two

prompt setup Apartment Hotel IDs and room categories 
prompt .. first init all new AP columns first to their default values

update T_AP set AP_SIHOT_CAT = F_SIHOT_CAT((select AT_GENERIC || '@' || AT_RSREF from T_AT where AT_CODE = AP_ATREF)),
                AP_SIHOT_HOTEL = F_SIHOT_HOTEL((select AT_GENERIC || '@' || AT_RSREF from T_AT where AT_CODE = AP_ATREF))
 where (select AT_RSREF from T_AT where AT_CODE = AP_ATREF) in ('PMA')
   and (select AT_GENERIC from T_AT where AT_CODE = AP_ATREF) is not NULL;

commit;


prompt .. then overwrite/setup special apartment categories (non xTIC/HOTU)

--
select * from t_ap where ap_sihot_hotel in (107) --and instr(ap_sihot_cat, '_') > 0
 order by ap_code;

-- PMA
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'L14';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'L15';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'L16';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'L17';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'L18';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'L19';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'L20';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'L21';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'L22';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'L23';
update T_AP set AP_SIHOT_CAT = '4BPS' where AP_CODE = 'L24';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'M01';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'M02';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'W01';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'W02';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'W03';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'W04';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'W05';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'W06';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'W07';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'W08';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'W09';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'W10';
update T_AP set AP_SIHOT_CAT = '3BPS' where AP_CODE = 'W11';
update T_AP set AP_SIHOT_CAT = '3BPS' where AP_CODE = 'W12';

commit;


prompt init RUL columns - first the last room category ...

update T_RUL l set RUL_SIHOT_LAST_CAT = RUL_SIHOT_CAT
 where instr(RUL_SIHOT_CAT, '_') = 0 and instr(RUL_SIHOT_LAST_CAT, '_') > 0
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)
   and exists (select NULL from V_ACU_RES_FILTERED f where f.RUL_CODE = l.RUL_CODE)
   and exists (select NULL from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = RUL_SIHOT_ROOM and AT_RSREF = 'PMA');

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
   and exists (select NULL from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = RUL_SIHOT_ROOM and AT_RSREF = 'PMA')
   ;

commit;

prompt .. then set HOTEL ... 23 rows only (2:30 min on SP.DEV)
 
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
   and 1=1
   and exists (select NULL from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = RUL_SIHOT_ROOM and AT_RSREF = 'PMA');

commit;


prompt .. then set CAT 

----- using F_SIHOT_CAT() slowed down this update to several days - for to speedup update will be done divided into several smaller chunks/cases
--update T_RUL l
--             set RUL_SIHOT_CAT = F_SIHOT_CAT(nvl(ltrim(RUL_SIHOT_ROOM, '0'), 'RU' || RUL_PRIMARY))  -- nvl needed for deleted RUs and for 20 cancelled RUs from 2014 with 'Sterling Suites' in RU_ATGENERIC - see line 138 in Q_SIHOT_SETUP2.sql
-- where RUL_DATE >= DATE'2012-01-01'
--   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)
--   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
--   and 1=1;

prompt ... first all the ones with ARO/room associated and set to room category = 250k rows in 32 sec on SP.TEST

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
   and RUL_SIHOT_CAT <> (select AP_SIHOT_CAT from T_AP where AP_CODE = ltrim(RUL_SIHOT_ROOM, '0'))
   and exists (select NULL from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = RUL_SIHOT_ROOM and AT_RSREF = 'PMA');

commit;

prompt ... then the ones without requested apt features = 14,5k rows

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
                                           and RU_ATGENERIC in ('HOTEL', 'STUDIO', '1 BED', '2 BED', '3 BED', '4 BED')
                                           and RU_RESORT in ('PMA')
              )
   and RUL_SIHOT_ROOM is NULL
   and RUL_SIHOT_RATE is not NULL 
   and not exists (select NULL from T_RAF where RAF_RUREF = RUL_PRIMARY)
   and RUL_SIHOT_CAT <> (select LU_CHAR from T_LU, T_RU where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end and LU_ID = RU_ATGENERIC and RU_CODE = RUL_PRIMARY)
   and exists (select NULL from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = RUL_SIHOT_ROOM and AT_RSREF = 'PMA');

commit;

prompt ... then the ones with requested apt features and category overload == 3 rows in 2 sec

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
                                           and RU_ATGENERIC in ('HOTEL', 'STUDIO', '1 BED', '2 BED', '3 BED', '4 BED')
                                           and RU_RESORT in ('PMA')
              )
   and RUL_SIHOT_ROOM is NULL
   and RUL_SIHOT_RATE is not NULL 
   and exists (select NULL from T_LU, T_RU, T_RAF
                                   where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end
                                     and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and RU_CODE = RAF_RUREF
                                     and RU_CODE = RUL_PRIMARY)
   and RUL_SIHOT_CAT <> (select max(LU_CHAR) from T_LU, T_RU, T_RAF where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and RU_CODE = RAF_RUREF and RU_CODE = RUL_PRIMARY)
   and exists (select NULL from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = RUL_SIHOT_ROOM and AT_RSREF = 'PMA');

commit;


prompt ... finally set all other invalid CATS (containing _) to the default room size cat

update T_RUL l
             set RUL_SIHOT_CAT = (select max(LU_CHAR) from T_LU, T_RU
                                   where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end
                                     and LU_ID = RU_ATGENERIC
                                     and RU_CODE = RUL_PRIMARY)
--select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_ROOM, F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1) as RH_ARO_APT, (select RU_ATGENERIC || '@' || RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY) as RU_GEN, (select AT_GENERIC || '@' || AT_RSREF from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')) as AT_GEN, (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY) as RU_RESORT, (select AP_SIHOT_CAT from T_AP where AP_CODE = F_RH_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY), pnSihotFormat => 1)) as AP_SIHOT_CAT, RUL_SIHOT_CAT, (select max(LU_CHAR) from T_LU, T_RU where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end and LU_ID = RU_ATGENERIC and RU_CODE = RUL_PRIMARY) as LU_SIHOT_CAT, (select RU_ATGENERIC || '@' || RU_RESORT || '/' || RU_CDREF from T_RU where RU_CODE = RUL_PRIMARY) as REQ_DATA from T_RUL l
 where RUL_DATE >= DATE'2012-01-01'
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and (c.RUL_ACTION = l.RUL_ACTION or c.RUL_ACTION <> 'DELETE' and l.RUL_ACTION <> 'DELETE') and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   and exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY and RU_STATUS <> 120) 
   and ( exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY and RU_STATUS <> 120 and RU_RESORT in ('PMA')) or RUL_SIHOT_HOTEL = 107 ) 
   and RUL_SIHOT_RATE is not NULL 
   and instr(RUL_SIHOT_CAT, '_') > 0
   and exists (select NULL from T_LU, T_RU
                where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end
                  and LU_ID = RU_ATGENERIC
                  and RU_CODE = RUL_PRIMARY);

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
   and RUL_SIHOT_PACK <> F_SIHOT_PACK((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'x') from T_RU where RU_CODE = RUL_PRIMARY), case when (select substr(F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'x'), 1, 4) from T_RU where RU_CODE = RUL_PRIMARY) = 'MKT_' then 'MKT_' else '' end)
   and exists (select NULL from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = RUL_SIHOT_ROOM and AT_RSREF = 'PMA');

commit;



prompt double-checking for sync amount and discrepancies

-- nearly 80k
select 'V_ACU_RES_FILTERED count=' || to_char(count(*))
     , 'Future Only=' || sum(case when ARR_DATE >= trunc(sysdate) then 1 end) as Future_Only
     , 'Present And Future=' || sum(case when DEP_DATE >= trunc(sysdate) then 1 end) as Present_And_Future
     , 'Present And Next Month=' || sum(case when DEP_DATE >= trunc(sysdate) and ARR_DATE <= trunc(sysdate) + 31 then 1 end) as Present_Plus_31Days
  from V_ACU_RES_FILTERED;

select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_PACK, RUL_SIHOT_ROOM, RUL_SIHOT_RATE, RUL_SIHOT_CAT, RUL_SIHOT_LAST_CAT, RU_RESORT, RUL_SIHOT_HOTEL, RUL_SIHOT_LAST_HOTEL, RU_RHREF, RU_ROREF, CD_CODE, OC_CODE
     , (select LU_NUMBER from T_AP, T_AT, T_LU where AP_ATREF = AT_CODE and AT_RSREF = LU_ID and LU_CLASS = 'SIHOT_HOTELS' and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')) as ROOM_HOTEL
  from V_ACU_RES_FILTERED
 where ( instr(RUL_SIHOT_PACK || RUL_SIHOT_ROOM || RUL_SIHOT_RATE || RUL_SIHOT_CAT || RUL_SIHOT_LAST_CAT || SIHOT_MKT_SEG, '_') > 0
    or RUL_SIHOT_HOTEL <= 0 or RUL_SIHOT_LAST_HOTEL <= 0
    or RUL_SIHOT_RATE is NULL
    or RUL_SIHOT_ROOM is not NULL and RUL_SIHOT_HOTEL <> nvl((select LU_NUMBER from T_AP, T_AT, T_LU where AP_ATREF = AT_CODE and 			AT_RSREF = LU_ID and LU_CLASS = 'SIHOT_HOTELS' and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')), -96) )
   and exists (select NULL from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = RUL_SIHOT_ROOM and AT_RSREF = 'PMA');

prompt same check query but from V_ACU_RES_UNFILTERED

select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_PACK, RUL_SIHOT_ROOM, RUL_SIHOT_RATE, RUL_SIHOT_CAT, RUL_SIHOT_LAST_CAT, RU_RESORT, RUL_SIHOT_HOTEL, RUL_SIHOT_LAST_HOTEL, RU_RHREF, RU_ROREF, CD_CODE, OC_CODE
     , (select LU_NUMBER from T_AP, T_AT, T_LU where AP_ATREF = AT_CODE and AT_RSREF = LU_ID and LU_CLASS = 'SIHOT_HOTELS' and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')) as ROOM_HOTEL
  from V_ACU_RES_UNFILTERED
 where ( instr(RUL_SIHOT_PACK || RUL_SIHOT_ROOM || RUL_SIHOT_RATE || RUL_SIHOT_CAT || RUL_SIHOT_LAST_CAT || SIHOT_MKT_SEG, '_') > 0
    or RUL_SIHOT_HOTEL <= 0 or RUL_SIHOT_LAST_HOTEL <= 0
    or RUL_SIHOT_RATE is NULL
    or RUL_SIHOT_ROOM is not NULL and RUL_SIHOT_HOTEL <> nvl((select LU_NUMBER from T_AP, T_AT, T_LU where AP_ATREF = AT_CODE and       AT_RSREF = LU_ID and LU_CLASS = 'SIHOT_HOTELS' and AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')), -96) )
   and exists (select NULL from T_AP, T_AT where AP_ATREF = AT_CODE and AP_CODE = RUL_SIHOT_ROOM and AT_RSREF = 'PMA');

select 'V_ACU_RES_UNSYNCED count=' || to_char(count(*))
     , 'Future Only=' || sum(case when ARR_DATE >= trunc(sysdate) then 1 end) as Future_Only
     , 'Present And Future=' || sum(case when DEP_DATE >= trunc(sysdate) then 1 end) as Present_And_Future
     , 'Present And Next Month=' || sum(case when DEP_DATE >= trunc(sysdate) and ARR_DATE <= trunc(sysdate) + 31 then 1 end) as Present_Plus_31Days
  from V_ACU_RES_UNSYNCED;

select RUL_CODE, RUL_PRIMARY, RUL_SIHOT_PACK, RUL_SIHOT_ROOM, RUL_SIHOT_RATE, RUL_SIHOT_CAT, RUL_SIHOT_LAST_CAT, RU_RESORT, RUL_SIHOT_HOTEL, RUL_SIHOT_LAST_HOTEL, RU_RHREF
  from V_ACU_RES_UNSYNCED where RUL_SIHOT_HOTEL in (107);


prompt EXTRA check for still missing PMA syncs of future reservations (for correct double-checking results please run again after first sync process has finished)

select * from t_ru
 where ru_from_date + ru_days > DATE'2019-01-01' --2016-01-01'
   and ru_status <> 120
   and (ru_resort = 'PMA' or f_resort(F_RH_ARO_APT(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS)) = 'PMA')
   and ( not exists (select NULL from t_srsl where srsl_primary = to_char(ru_code) and srsl_date > DATE'2019-03-13' and substr(srsl_status, 1, 6) = 'SYNCED')
        or ru_sihot_objid is NULL )
   and exists (select NULL from t_ro where ro_code = ru_roref and ro_sihot_rate is not NULL)
 order by ru_from_date desc;
 


prompt 'Finished  -  End Of Script'
exec P_PROC_SET('', '', '');
spool off


