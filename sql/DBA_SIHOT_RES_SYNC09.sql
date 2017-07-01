--- VERSION 00: first beta
--- VERSION 01: refactored T_SRSL (removed RULREF/AROREF and added DATE, PRIMARY and TABLE)
--- VERSION 02: added AP_SIHOT*, RU_SIHOT* and RUL_SIHOT* columns for to support new CPA sub-hotel (16 units like F004) and ARO_APREF data overloads (new resort/unit/cat)
--              and added LG_SIHOT_LANG for the migration/sync mapping.
--- VERSION 03: added real sihot room categories (LU_CLASS=SIHOT_CATS_ANY and SiHOT_CATS_PBC).
--- VERSION 04: speed-up and refactored RUL column initialization and added RO_SIHOT_RES_GROUP/RO_SIHOT_SP_GROUP for to store SIHOT CHANNEL/NN mappings.
--- VERSION 05: moved update of default values to the end of the script and changed STIC default to more detectable values.
--- VERSION 06: after room category and project structure refacturing and revising initiated by me, Gary and supported by the help of KP.
--- VERSION 07: changed to map to new TK/tk contracts - created by Fabi�n (see email from 9-12-2016).
--- VERSION 08: performance tuning of the UPDATE statement for to populate the new T_RUL columns.
--- VERSION 09: more performance tuning and added new procedure P_SIHOT_ALLOC.
 
 
-- max linesize - limitted by TOAD to 2000 (32767 is maximum for sqlPlus)
SET LINESIZE 32767
-- surpress page separator
SET NEWPAGE 0
SET PAGESIZE 0
-- add dbms_output.put_line onto spool log file
SET SERVEROUTPUT ON
-- trim trailing blanks from line end
SET TRIMSPOOL ON

spool DBA_SIHOT_RES_SYNC09.log
exec P_PROC_SET('DBA_SIHOT_RES_SYNC', '2016_V09', 'test');




prompt DATA LOOKUP CHANGES - needed for to populate new columns in following DDL CHANGES section - more DATA CHANGES at the end of this script

-- changed according the new setup done by Fabi�n - see his email from 09/12/2016 11:22

prompt add new lookup class for to transform unit size to sihot cat (only ANY fallback need to specify transforms for all Acumen unit sizes: HOTEL/STUDIO..3 BED)

delete from T_LU where LU_CLASS = 'SIHOT_CATS_ANY';
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_ANY', 'HOTEL', 'Hotel unit sihot category', 001, 1, NULL,
          'HOTU', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_ANY', 'STUDIO', 'Studio unit sihot category', 002, 1, NULL,
          'STDO', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_ANY', '1 BED', '1 Bedroom unit sihot category', 011, 1, NULL,
          '1JNR', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_ANY', '2 BED', '2 Bedroom unit sihot category', 021, 1, NULL,
          '2BSU', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_ANY', '2 BED_757', '2 Bedroom high floor', 023, 1, NULL,
          '2BSH', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_ANY', '3 BED', '3 Bedroom unit sihot category', 031, 1, NULL,
          '3BPS', NULL, user, sysdate, user, sysdate);
commit;


prompt ... BHC overloads

delete from T_LU where LU_CLASS = 'SIHOT_CATS_BHC';
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHC', 'STUDIO_757', 'Studio View/High Floor unit', 102, 1, NULL,
          'STDS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHC', '1 BED_752', '1 Bedroom etage/duplex', 112, 1, NULL,
          '1DSS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHC', '1 BED_757', '1 Bedroom view/high floor', 112, 1, NULL,
          '1JNS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_BHC', '2 BED_752', '2 Bedroom etage/duplex', 122, 1, NULL,
          '2DPU', NULL, user, sysdate, user, sysdate);
commit;


prompt ... PBC overloads

delete from T_LU where LU_CLASS = 'SIHOT_CATS_PBC';
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PBC', 'STUDIO', 'PBC studio unit sihot category', 401, 1, NULL,
          'STDP', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PBC', 'STUDIO_757', 'Studio High Floor unit', 402, 1, NULL,
          'STDH', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PBC', 'STUDIO_781', 'Studio Sea View/Front unit', 403, 1, NULL,
          'STDB', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PBC', '1 BED', '1 Bedroom', 411, 1, NULL,
          '1JNP', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PBC', '1 BED_757', '1 Bedroom High Floor', 412, 1, NULL,
          '1JNH', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PBC', '1 BED_748', '1 Bedroom Sterling', 413, 1, NULL,
          '1STS', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PBC', '2 BED', '2 Bedroom unit sihot category', 421, 1, NULL,
          '2BSP', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PBC', '2 BED_757', '2 Bedroom High Floor', 422, 1, NULL,
          '2BSH', NULL, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_CATS_PBC', '3 BED', '3 Bedroom unit sihot category', 433, 1, NULL,
          '3BPB', NULL, user, sysdate, user, sysdate);
commit;



prompt add new lookup class for to transform RSRef of all the T_RS records with RS_CLASS=='BUILDING' into sihot hotel id

delete from T_LU where LU_CLASS = 'SIHOT_HOTELS';
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'ANY', 'ANY resort sihot hotel id', 0, 1, NULL,
          NULL, 999, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'ARF', 'ARF resort sihot hotel id', 101, 0, NULL,
          NULL, 101, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'BHC', 'BHC resort sihot hotel id', 1, 1, NULL,
          NULL, 1, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'BHH', 'BHH resort sihot hotel id', 2, 0, NULL,
          NULL, 2, user, sysdate, user, sysdate);
--insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
--                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
--  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'CCC', 'CCC resort sihot hotel id', 201, 1, NULL,
--          NULL, 201, user, sysdate, user, sysdate);
--insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
--                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
--  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'CLT', 'CLT resort sihot hotel id', 202, 1, NULL,
--          NULL, 202, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'DBD', 'DBD resort sihot hotel id', 102, 0, NULL,
          NULL, 102, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'GSA', 'GSA resort sihot hotel id', 103, 0, NULL,
          NULL, 103, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'HMC', 'HMC resort sihot hotel id', 3, 0, NULL,
          NULL, 3, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'KGR', 'KGR resort sihot hotel id', 104, 0, NULL,
          NULL, 104, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'LVI', 'LVI resort sihot hotel id', 105, 0, NULL,
          NULL, 105, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'PBC', 'PBC resort sihot hotel id', 4, 1, NULL,
          NULL, 4, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'PLA', 'PLA resort sihot hotel id', 106, 0, NULL,
          NULL, 106, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'PMA', 'PMA resort sihot hotel id', 107, 0, NULL,
          NULL, 107, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'PMY', 'PMY resort sihot hotel id', 108, 0, NULL,
          NULL, 108, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'PSF', 'PSF resort sihot hotel id', 109, 0, NULL,
          NULL, 109, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'RHF', 'RHF resort sihot hotel id', 110, 0, NULL,
          NULL, 110, user, sysdate, user, sysdate);
--insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
--                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
--  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'RIC', 'RIC resort sihot hotel id', 111, 1, NULL,
--          NULL, 111, user, sysdate, user, sysdate);
insert into T_LU ( LU_CODE, LU_CLASS, LU_ID, LU_DESC, LU_ORDER, LU_ACTIVE, LU_DATE,
                   LU_CHAR, LU_NUMBER, LU_CBY, LU_CWHEN, LU_MODBY, LU_MODWHEN )
  values (S_LOOKUP_SEQ.nextval, 'SIHOT_HOTELS', 'CPS', 'CP Suites resort sihot hotel id', 199, 0, NULL,
          NULL, 199, user, sysdate, user, sysdate);
commit;



prompt DDL CHANGES

prompt new T_AP columns for SIHOT hotel id and price category (unit size+apt features) and resort (needed also for the 16 BHC sweets migrated to new CPA-pseudo resort) 

alter table SALES.APTS add (AP_SIHOT_CAT   VARCHAR2(6 BYTE) DEFAULT 'A___' NOT NULL);
alter table SALES.APTS add (AP_SIHOT_HOTEL NUMBER(3)        DEFAULT -1     NOT NULL);

comment on column SALES.APTS.AP_SIHOT_CAT   is 'Unit/Price category in SIHOT system';
comment on column SALES.APTS.AP_SIHOT_HOTEL is 'Hotel Id in SIHOT system';

-- NOTE: basic initialization done in 2nd DATA UPDATES section (after compiling new functions)


prompt new T_CD column for to store SIHOT OBJID

alter table SALES.CLIENT_DETAILS add (CD_SIHOT_OBJID    NUMBER(9));
alter table SALES.CLIENT_DETAILS add (CD_SIHOT_OBJID2   NUMBER(9));

comment on column SALES.CLIENT_DETAILS.CD_SIHOT_OBJID   is 'SIHOT Guest Object ID (after syncronization/migration)';
comment on column SALES.CLIENT_DETAILS.CD_SIHOT_OBJID2  is 'SIHOT Guest Object ID for second person (CD_FNAM2/_SNAM2)';



prompt new T_LG columns for SIHOT hotel language/nationality 

alter table SALES.LANG add (LG_SIHOT_LANG   VARCHAR2(2 BYTE));

comment on column SALES.LANG.LG_SIHOT_LANG is 'Language code/id in SIHOT';

-- missing languages: HUN, ...
update T_LG set LG_SIHOT_LANG = 'HR' where LG_CODE = 'CRO';
update T_LG set LG_SIHOT_LANG = 'EN' where LG_CODE = 'ENG';
update T_LG set LG_SIHOT_LANG = 'FR' where LG_CODE = 'FRE';
update T_LG set LG_SIHOT_LANG = 'DE' where LG_CODE = 'GER';
update T_LG set LG_SIHOT_LANG = 'IT' where LG_CODE = 'ITA';
update T_LG set LG_SIHOT_LANG = 'PL' where LG_CODE = 'POL';
update T_LG set LG_SIHOT_LANG = 'PT' where LG_CODE = 'POR';
update T_LG set LG_SIHOT_LANG = 'ES' where LG_CODE = 'SPA';
update T_LG set LG_SIHOT_LANG = 'SI' where LG_CODE = 'SVN';

commit;


prompt new T_RO columns for to store SIHOT OBJID of agency and rate mapping and for to map SIHOT marketsegments

alter table LOBBY.RESOCC_TYPES add (RO_SIHOT_MKT_SEG           VARCHAR2(2 Byte));
alter table LOBBY.RESOCC_TYPES add (RO_SIHOT_RES_GROUP         VARCHAR2(2 Byte));
alter table LOBBY.RESOCC_TYPES add (RO_SIHOT_SP_GROUP          VARCHAR2(2 Byte));
alter table LOBBY.RESOCC_TYPES add (RO_SIHOT_RATE              VARCHAR2(3 Byte));
alter table LOBBY.RESOCC_TYPES add (RO_SIHOT_AGENCY_OBJID      NUMBER(9));
alter table LOBBY.RESOCC_TYPES add (RO_SIHOT_AGENCY_MC         VARCHAR2(9 Byte));

comment on column LOBBY.RESOCC_TYPES.RO_SIHOT_MKT_SEG        is 'SIHOT Marketsegment mapping (lower case not working in SIHOT)';
comment on column LOBBY.RESOCC_TYPES.RO_SIHOT_RES_GROUP      is 'SIHOT market CHANNEL mapping';
comment on column LOBBY.RESOCC_TYPES.RO_SIHOT_SP_GROUP       is 'SIHOT market NN mapping';
comment on column LOBBY.RESOCC_TYPES.RO_SIHOT_RATE           is 'SIHOT Rate for this Marketsegment';
comment on column LOBBY.RESOCC_TYPES.RO_SIHOT_AGENCY_OBJID   is 'SIHOT company object ID for agency bookings';
comment on column LOBBY.RESOCC_TYPES.RO_SIHOT_AGENCY_MC      is 'SIHOT company matchcode for agency bookings';


update T_RO set RO_SIHOT_MKT_SEG = 'FG' where RO_CODE = 'fG';
update T_RO set RO_SIHOT_MKT_SEG = 'FO' where RO_CODE = 'fO';
update T_RO set RO_SIHOT_MKT_SEG = 'H1' where RO_CODE = 'hg';
update T_RO set RO_SIHOT_MKT_SEG = 'H2' where RO_CODE = 'hG';
update T_RO set RO_SIHOT_MKT_SEG = 'H3' where RO_CODE = 'hR';
update T_RO set RO_SIHOT_MKT_SEG = 'H5' where RO_CODE = 'hr';
update T_RO set RO_SIHOT_MKT_SEG = 'H6' where RO_CODE = 'hW';
update T_RO set RO_SIHOT_MKT_SEG = 'H7' where RO_CODE = 'hw';
update T_RO set RO_SIHOT_MKT_SEG = 'I1' where RO_CODE = 'ig';
update T_RO set RO_SIHOT_MKT_SEG = 'I2' where RO_CODE = 'iG';
update T_RO set RO_SIHOT_MKT_SEG = 'I3' where RO_CODE = 'ii';
update T_RO set RO_SIHOT_MKT_SEG = 'I4' where RO_CODE = 'iI';
update T_RO set RO_SIHOT_MKT_SEG = 'IW' where RO_CODE = 'iW';
update T_RO set RO_SIHOT_MKT_SEG = 'RG' where RO_CODE = 'rW';
update T_RO set RO_SIHOT_MKT_SEG = 'RN' where RO_CODE = 'Ri';
update T_RO set RO_SIHOT_MKT_SEG = 'RP' where RO_CODE = 'Ro';
update T_RO set RO_SIHOT_MKT_SEG = 'TS' where RO_CODE = 'TC';
update T_RO set RO_SIHOT_MKT_SEG = 'TC' where RO_CODE = 'tk';
update T_RO set RO_SIHOT_MKT_SEG = 'T1' where RO_CODE = 'tc';
commit;

--select distinct RO_RES_GROUP, RO_SIHOT_RES_GROUP from T_RO order by RO_RES_GROUP
update T_RO set RO_SIHOT_RES_GROUP = case RO_RES_GROUP when 'Club Paradiso Guest' then 'CG' 
                                                       when 'Club Paradiso Owner' then 'CO' 
                                                       when 'Other' then 'OT'
                                                       when 'Owner' then 'OW'
                                                       when 'Owner Guest' then 'OG'
                                                       when 'Promo' then 'FB'
                                                       when 'RCI External' then 'RE'
                                                       when 'RCI External Guest' then 'RG'
                                                       when 'RCI Internal' then 'RI'
                                                       when 'RCI Owner Guest' then 'RO'
                                                       when 'Rental External' then 'RR'
                                                       when 'Rental SP' then 'RS'
                                                       end
 where RO_RES_GROUP is not NULL;

--select distinct RO_SIHOT_RES_GROUP from T_RO order by RO_SIHOT_RES_GROUP

commit;

--select distinct RO_SP_GROUP from T_RO order by RO_SP_GROUP
update T_RO set RO_SIHOT_SP_GROUP = case RO_SP_GROUP when 'Rental SP' then 'RS' 
                                                     when 'SP Booking' then 'SB' 
                                                     when 'SP CP Booking' then 'SC'
                                                     when 'SP PB Booking' then 'SP'
                                                     end
 where RO_SP_GROUP is not NULL;

--select distinct RO_SIHOT_SP_GROUP from T_RO order by RO_SIHOT_SP_GROUP

commit;
 

update T_RO set RO_SIHOT_AGENCY_OBJID = case RO_CODE when 'TK' then 27 when 'tk' then 20 end
              , RO_SIHOT_AGENCY_MC = case RO_CODE when 'TK' then 'TCRENT' when 'tk' then 'TCAG' end
              , RO_SIHOT_RATE = nvl(RO_SIHOT_MKT_SEG, RO_CODE)
 where RO_CLASS in ('B', 'R')
   and (   substr(RO_RES_GROUP, 1, 5) = 'Owner' 
        or substr(RO_RES_GROUP, 1, 13) = 'Club Paradiso' 
        or substr(RO_RES_GROUP, 1, 3) = 'RCI' 
        or substr(RO_RES_GROUP, 1, 5) = 'Promo' 
        or RO_CODE in ('TK', 'tk')
        or RO_CODE = 'ER'   -- requested by Esther 03-11-2016
       );

commit;



prompt new T_RS column for easier classification of client to guest transfer in SIHOT interfaces

alter table SALES.RESORTS add (RS_SIHOT_GUEST_TYPE  VARCHAR2(1 BYTE));

comment on column SALES.RESORTS.RS_SIHOT_GUEST_TYPE is 'ID of client type for SIHOT guest/contact classification';

-- first set all to general owner (mainly for to group less import owner types like e.g. tablet, lifestyle, expirience, explorer)
update T_RS set RS_SIHOT_GUEST_TYPE = 'O' where RS_CLASS = 'CONSTRUCT'  or  RS_CLASS = 'BUILDING' and RS_GROUP = 'A';
-- then specify distinguishable client types
update T_RS set RS_SIHOT_GUEST_TYPE = 'I' where RS_CODE in ('PBF', 'TSP');
update T_RS set RS_SIHOT_GUEST_TYPE = 'K' where RS_CODE in ('KEY');
--update T_RS set RS_SIHOT_GUEST_TYPE = 'C' where RS_CODE in ('CPA');

commit;



prompt new T_RU column for to store SIHOT OBJID

alter table LOBBY.REQUESTED_UNIT add (RU_SIHOT_OBJID      NUMBER(9));

comment on column LOBBY.REQUESTED_UNIT.RU_SIHOT_OBJID   is 'SIHOT Reservation Object ID (after syncronization/migration)';



prompt new T_RUL columns for data needed for RU/ARO cancellation/deletions and ARO apartment overloads

--alter table LOBBY.REQUESTED_UNIT_LOG add (RUL_SIHOT_GDSID VARCHAR2(9 BYTE) DEFAULT 'RH_' NOT NULL);
alter table LOBBY.REQUESTED_UNIT_LOG add (RUL_SIHOT_CAT   VARCHAR2(6 BYTE) DEFAULT 'R___' NOT NULL);
alter table LOBBY.REQUESTED_UNIT_LOG add (RUL_SIHOT_HOTEL NUMBER(3)        DEFAULT -2     NOT NULL);
alter table LOBBY.REQUESTED_UNIT_LOG add (RUL_SIHOT_PACK  VARCHAR2(3 BYTE) DEFAULT 'R_'   NOT NULL);
alter table LOBBY.REQUESTED_UNIT_LOG add (RUL_SIHOT_ROOM  VARCHAR2(7 BYTE));
alter table LOBBY.REQUESTED_UNIT_LOG add (RUL_SIHOT_OBJID NUMBER(9));
alter table LOBBY.REQUESTED_UNIT_LOG add (RUL_SIHOT_RATE  VARCHAR2(3 BYTE));

comment on table LOBBY.REQUESTED_UNIT_LOG is 'Requested Units Log';
comment on column LOBBY.REQUESTED_UNIT_LOG.RUL_SIHOT_CAT   is 'Unit/Price category in SIHOT system - overloaded if associated ARO exists';
comment on column LOBBY.REQUESTED_UNIT_LOG.RUL_SIHOT_HOTEL is 'Hotel Id in SIHOT system - overloaded if associated ARO exists';
comment on column LOBBY.REQUESTED_UNIT_LOG.RUL_SIHOT_ROOM  is 'Booked apartment (AP_CODE) if associated ARO record exits else NULL';
comment on column LOBBY.REQUESTED_UNIT_LOG.RUL_SIHOT_OBJID is 'RU_SIHOT_OBJID value (for to detect if deleted RU got passed into SIHOT PMS)';
comment on column LOBBY.REQUESTED_UNIT_LOG.RUL_SIHOT_PACK  is 'Booked package/arrangement - overloaded if associated ARO/PRC exits';
comment on column LOBBY.REQUESTED_UNIT_LOG.RUL_SIHOT_RATE  is 'Market seqment price rate - used for filtering (also if RU record is deleted)';

create index LOBBY.RUL_PRIMARY on LOBBY.REQUESTED_UNIT_LOG (RUL_PRIMARY) logging noparallel;

-- NOTE: basic initialization done in 2nd DATA UPDATES section (after compiling new functions)


prompt new table for to store the synchronization log

--drop table LOBBY.SIHOT_RES_SYNC_LOG cascade constraints;

create table LOBBY.SIHOT_RES_SYNC_LOG
  (
    SRSL_TABLE      VARCHAR2(6)            NOT NULL,
    SRSL_PRIMARY    VARCHAR2(12 BYTE)      NOT NULL,
    SRSL_ACTION     VARCHAR2(15 BYTE)      NOT NULL,
    SRSL_STATUS     VARCHAR2(12 BYTE)      NOT NULL,
    SRSL_DATE       DATE default sysdate   NOT NULL,
    SRSL_LOGREF     NUMBER(10)             NOT NULL,    -- NOT USED FOR UNSYNCED VIEWS - only informativ for debugging
    SRSL_MESSAGE    VARCHAR2(1999 BYTE)                 -- 27-06-2017 13:38 changed size from 1998 to 1999
  )
  TABLESPACE LOBBY
  PCTUSED    0
  PCTFREE    10
  INITRANS   1
  MAXTRANS   255
  STORAGE    (
              INITIAL          64K
              NEXT             1M
              MINEXTENTS       1
              MAXEXTENTS       UNLIMITED
              PCTINCREASE      0
              BUFFER_POOL      DEFAULT
             )
  LOGGING 
  NOCOMPRESS 
  NOCACHE
  NOPARALLEL
  MONITORING;

comment on column LOBBY.SIHOT_RES_SYNC_LOG.SRSL_TABLE is 'Acumen Table ID (RU/ARO/CD)';
comment on column LOBBY.SIHOT_RES_SYNC_LOG.SRSL_PRIMARY is 'Acumen Table Primary Key (RU_CODE, ARO_CODE or CD_CODE)';
comment on column LOBBY.SIHOT_RES_SYNC_LOG.SRSL_ACTION is 'Initiated Action/OC=operation-code Onto SiHOT PMS (for CD also action of Person2)';
comment on column LOBBY.SIHOT_RES_SYNC_LOG.SRSL_STATUS is 'Final Status/Response of SiHOT PMS (synchronized if substr(,1,6)=''SYNCED'', else ''ERR[SiHOT-RC-code]'')';
comment on column LOBBY.SIHOT_RES_SYNC_LOG.SRSL_DATE is 'Date/Time of the insert into this log table';
comment on column LOBBY.SIHOT_RES_SYNC_LOG.SRSL_LOGREF is 'Audit Trail Log Id (for debugging only) - Primary Key of either RUL/Requested Unit Log, AROL/Apartment Reservation Log or LOG/Client Details Log';
comment on column LOBBY.SIHOT_RES_SYNC_LOG.SRSL_MESSAGE is 'Final Message/Response of SiHOT PMS (taken from the SiHOT MSG response xml element)';


create or replace public synonym T_SRSL for LOBBY.SIHOT_RES_SYNC_LOG;


GRANT DELETE, INSERT, SELECT, UPDATE ON LOBBY.SIHOT_RES_SYNC_LOG TO SALES_00_MASTER;
GRANT SELECT, INSERT, UPDATE ON LOBBY.SIHOT_RES_SYNC_LOG TO SALES_05_SYSADMIN;
GRANT DELETE, INSERT, SELECT, UPDATE ON LOBBY.SIHOT_RES_SYNC_LOG TO SALES_06_DEVELOPER;

GRANT INSERT, SELECT, UPDATE ON LOBBY.SIHOT_RES_SYNC_LOG TO SALES_10_SUPERVISOR;
GRANT INSERT, SELECT ON LOBBY.SIHOT_RES_SYNC_LOG TO SALES_11_SUPERASSIST;
GRANT INSERT, SELECT ON LOBBY.SIHOT_RES_SYNC_LOG TO SALES_60_RESERVATIONS;

GRANT INSERT, SELECT, UPDATE ON LOBBY.SIHOT_RES_SYNC_LOG TO XL_00_MASTER;
GRANT INSERT, SELECT, UPDATE ON LOBBY.SIHOT_RES_SYNC_LOG TO XL_05_SYSADMIN;
GRANT INSERT, SELECT, UPDATE ON LOBBY.SIHOT_RES_SYNC_LOG TO XL_06_DEVELOPER;
GRANT INSERT, SELECT, UPDATE ON LOBBY.SIHOT_RES_SYNC_LOG TO XL_10_SUPERVISOR;
GRANT INSERT, SELECT ON LOBBY.SIHOT_RES_SYNC_LOG TO XL_60_RESERVATIONS;


prompt new functions for to handle SIHOT id translation and ARO/PRC overloads

@@F_ARO_RU_CODE00.sql;
@@F_RU_ARO_APT00.sql;
@@F_RU_ARO_BOARD01.sql;
@@F_SIHOT_CAT02.sql;
@@F_SIHOT_GUEST_TYPE00.sql;
@@F_SIHOT_HOTEL00.sql;
@@F_SIHOT_NON_MUTAT_PACK00.sql;
@@F_SIHOT_PACK01.sql;
@@F_SIHOT_PAID_RAF00.sql;
@@F_SIHOT_SALUTATION00.sql;



prompt add new views for the data and logs of T_CD (T_LOG), T_RU, T_ARO and T_RH (for the last two in T_RUL)

@@V_ACU_CD_LOG01.sql;
@@V_ACU_CD_DATA00.sql;
@@V_ACU_CD_UNFILTERED00.sql;
@@V_ACU_CD_FILTERED00.sql;
@@V_ACU_CD_UNSYNCED02.sql;

@@V_ACU_RES_LOG02.sql;
@@V_ACU_RES_DATA03.sql;
@@V_ACU_RES_UNFILTERED02.sql;
@@V_ACU_RES_FILTERED01.sql;
--@@V_ACU_RES_HIST00.sql;   NO LONGER NEEDED (never fully finished/tested)
@@V_ACU_RES_UNSYNCED05.sql;


prompt new procedure for RUL insert/update and for to populate the new RUL_SIHOT columns

@@P_RUL_INSERT02.sql;
@@P_SIHOT_ALLOC00.sql;


prompt extend RU/ARO triggers for to populate the new RUL_SIHOT* columns (executed after creation of new functions and views because they are needed) 

@@E_ARO_DELETE06.sql;
@@E_ARO_INSERT05.sql;
@@E_ARO_UPDATE09.sql;

@@E_CD_SIHOT_OBJIDS00.sql;

@@E_RAF_CHANGE00.sql;

@@E_RH_INSERT03.sql;
@@E_RH_UPDATE05.sql;

@@E_RU_DELETE02.sql;
@@E_RU_INSERT02.sql;
@@E_RU_UPDATE03.sql;

@@E_PRC_UPDATE06.sql;





prompt DATA CHANGES - part two

prompt setup Apartment Hotel IDs and room categories 
prompt .. first init all new AP columns first to their default values

update T_AP set AP_SIHOT_CAT = F_SIHOT_CAT((select AT_GENERIC || '@' || AT_RSREF from T_AT where AT_CODE = AP_ATREF)),
                AP_SIHOT_HOTEL = F_SIHOT_HOTEL((select AT_GENERIC || '@' || AT_RSREF from T_AT where AT_CODE = AP_ATREF))
 where exists (select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ID = (select AT_RSREF from T_AT where AT_CODE = AP_ATREF))
   and (select AT_GENERIC from T_AT where AT_CODE = AP_ATREF) is not NULL;

commit;


prompt .. then overwrite/setup special apartment categories (non xTIC/HOTU) - first BHC then PBC

update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'A101';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'A102';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'A103';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'A105';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'A106';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'A107';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'A108';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = 'A109';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = 'A110';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'A115';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'A116';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'A117';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'A118';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'A119'; -- 1JNS
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'A120'; -- 1JNS
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'A121';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'A122';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'A123';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'A124';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = 'A200';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'A201';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'A202';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'A203';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'A205';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'A206';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'A207';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'A208';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = 'A209';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = 'A210';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'A211';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'A212';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'A214';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'A215';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'A216';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'A217';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'A218';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = 'A219';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = 'A220';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = 'A221';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = 'A222';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = 'A223';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = 'A224';
update T_AP set AP_SIHOT_CAT = '2XSS' where AP_CODE = 'A301';
update T_AP set AP_SIHOT_CAT = '2XSS' where AP_CODE = 'A302';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'B001';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'B002';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'B003';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'B101';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'B102';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'B103'; -- 1JNS
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'B104'; -- 1JNS
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'B105';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'B106';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'B107';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'B108';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'B201';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'B202';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'B203';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'B204';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'B205';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'B206';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'B207';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'B208';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'C101';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'C102';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'C103';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'C104';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'C105';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'C106';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'C107';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'C108';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'C201';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'C202';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'C203';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'C204';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'C205';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'C206';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'C207';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'C208';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'D101';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'D102';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'D103';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'D104';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'D105';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'D106';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'D107';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'D108';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'D201';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'D202';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'D203';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'D204';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'D205';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'D206';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'D207';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'D208';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'E102';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'E103';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'E104';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'E105';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'E106';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'E107';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'E202';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'E203';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'E204';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'E205';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'E206';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'E207';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'E301';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'E302';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'E303';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'E304';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'E305';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'E306';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'E307';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'E401';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'E402';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'E403';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'E404';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'E405';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'E406';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'E407';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'F001';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'F002';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'F003';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'F004';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'F005';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'F006';
update T_AP set AP_SIHOT_CAT = 'HOTU' where AP_CODE = 'F007';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'F101';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'F102';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'F103';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'F104';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'F105';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'F106';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'F201';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'F202';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'F203';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'F204';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'F205';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'F206';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = 'F301';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = 'F302';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'F303';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = 'F304';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'F305';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = 'F306';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'F401';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'F402';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'F403';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'F404';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'F405';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'F406';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G001';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G002';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G003';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G004';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G005';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'G006';
update T_AP set AP_SIHOT_CAT = 'HOTU' where AP_CODE = 'G007';
update T_AP set AP_SIHOT_CAT = 'HOTU' where AP_CODE = 'G008';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G101';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G102';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G103';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G104';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G105';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G106';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G201';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G202';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G203';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G204';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G205';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'G206';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = 'G301';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'G302';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = 'G303';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = 'G304';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = 'G305';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = 'G306';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'G400';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'G401';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'G402';
update T_AP set AP_SIHOT_CAT = '1DSS' where AP_CODE = 'G403';
update T_AP set AP_SIHOT_CAT = '3BPS' where AP_CODE = 'G404';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'H001';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'H002';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'H003';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'H004';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'H005';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'H006';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'H007';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'H008';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'H009';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'H010';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'H011';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'H012';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'H014';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'H015';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'H016';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'H017';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'H018';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'H019';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'H020';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'H021';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'H022';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'H023';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'H101';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'H102';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'H103';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'H104';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'H105';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'H106';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'H107';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'H108';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'H110';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = 'H111';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = 'H112';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'H114';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = 'H115';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = 'H116';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = 'H201';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = 'H202';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = 'H203';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = 'H204';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = 'H205';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = 'H206';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = 'H207';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = 'H208';
update T_AP set AP_SIHOT_CAT = '2DPU' where AP_CODE = 'H210';
update T_AP set AP_SIHOT_CAT = '2DPU' where AP_CODE = 'H211';
update T_AP set AP_SIHOT_CAT = '2DPU' where AP_CODE = 'H212';
update T_AP set AP_SIHOT_CAT = '2DPU' where AP_CODE = 'H214';
update T_AP set AP_SIHOT_CAT = '2DPU' where AP_CODE = 'H215';
update T_AP set AP_SIHOT_CAT = '2DPU' where AP_CODE = 'H216';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'I001';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'I002';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'I003';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'I004';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'I005';
update T_AP set AP_SIHOT_CAT = 'STDO' where AP_CODE = 'I006';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'I101';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'I102';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'I103';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'I104';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'I201';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'I202';
update T_AP set AP_SIHOT_CAT = '1JNR' where AP_CODE = 'I203';
update T_AP set AP_SIHOT_CAT = '2BSU' where AP_CODE = 'I204';

commit;


update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '126';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '127';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '128';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '129';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '130';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '131';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '132';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '133';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '134';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '210';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '211';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '212';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '214';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '215';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '216';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '217';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '218';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '219';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '220';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '221';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '222';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '223';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '224';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '225';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '226';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '227';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '228';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '229';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '230';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '231';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '232';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '233';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '234';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '235';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '236';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '237';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '316';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '317';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '318';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '319';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '320';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '321';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '322';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '323';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '324';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '325';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '326';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '327';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '328';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '329';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '330';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '331';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '332';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '333';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '334';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '335';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '336';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '337';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '401'; -- 22SB
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '402'; -- 1JNB
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '403';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '404';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '405';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '406';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '407';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '408';
update T_AP set AP_SIHOT_CAT = '22SB' where AP_CODE = '409';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '410';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '411';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '412';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '414';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '415';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '416';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '417';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '418';
update T_AP set AP_SIHOT_CAT = 'STDP' where AP_CODE = '419';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '420';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '421';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '422';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '423';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '424';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '425';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '426';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '427';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '428';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '429';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '430';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '431';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '432';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '433';
update T_AP set AP_SIHOT_CAT = '2BSP' where AP_CODE = '434';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '435';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '436';
update T_AP set AP_SIHOT_CAT = '1JNP' where AP_CODE = '437';
update T_AP set AP_SIHOT_CAT = '22SB' where AP_CODE = '501';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '502';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '503';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '504';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '505';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '506';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '507';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '508';
update T_AP set AP_SIHOT_CAT = '22SB' where AP_CODE = '509';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '510';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '511';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '512';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '514';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '515';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '516';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '517';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '518';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '519';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '520';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '521';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '522';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '523';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '524';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '525';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '526';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '527';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '528';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '529';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '530';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '531';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '532';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '533';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '534';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '535';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '536';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '537';
update T_AP set AP_SIHOT_CAT = '22SB' where AP_CODE = '601';
update T_AP set AP_SIHOT_CAT = '1JNB' where AP_CODE = '602';
update T_AP set AP_SIHOT_CAT = '1JNB' where AP_CODE = '603';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '604';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '605';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '606';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '607';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '608';
update T_AP set AP_SIHOT_CAT = '22SB' where AP_CODE = '609';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '610';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '611';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '612';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '614';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '615';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '616';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '617';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '618';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '619';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '620'; --2BSP
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '621';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '622';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '623';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '624'; --2BSS
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '625';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '626';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '627';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '628';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '629';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '630';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '631';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '632';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '633';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '634';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '635';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '636';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '637';
update T_AP set AP_SIHOT_CAT = '22SB' where AP_CODE = '701';
update T_AP set AP_SIHOT_CAT = '1JNB' where AP_CODE = '702';
update T_AP set AP_SIHOT_CAT = '1JNB' where AP_CODE = '703';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '704';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '705';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '706';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '707';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '708';
update T_AP set AP_SIHOT_CAT = '22SB' where AP_CODE = '709';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '710';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '711';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '712';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '714';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '715';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '716';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '717';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '718';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '719';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '720'; --2BSP
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '721';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '722';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '723';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '724'; --2BSS
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '725';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '726';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '727';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '728';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '729';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '730';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '731';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '732';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '733';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '734';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '735';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '736';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '737';
update T_AP set AP_SIHOT_CAT = '22SB' where AP_CODE = '801';
update T_AP set AP_SIHOT_CAT = '1JNB' where AP_CODE = '802';
update T_AP set AP_SIHOT_CAT = '1JNB' where AP_CODE = '803';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '804';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '805';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '806';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '807';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '808';
update T_AP set AP_SIHOT_CAT = '22SB' where AP_CODE = '809';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '810';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '811';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '812';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '814';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '815';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '816';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '817';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '818';
update T_AP set AP_SIHOT_CAT = 'STDS' where AP_CODE = '819';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '820';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '821';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '822';
update T_AP set AP_SIHOT_CAT = '1JNS' where AP_CODE = '823';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '824';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '825';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '826';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '827';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '828';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '829';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '830';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '831';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '832';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '833';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '834';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '835';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '836';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '837';
update T_AP set AP_SIHOT_CAT = '3BPB' where AP_CODE = '903';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '906';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '907';
update T_AP set AP_SIHOT_CAT = 'STDB' where AP_CODE = '908';
update T_AP set AP_SIHOT_CAT = '22SB' where AP_CODE = '909';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '910';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '911';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '912';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '914';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '915';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '916';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '917';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '918';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '919';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '920';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '921';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = '922';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = '923';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '924';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '925';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '926';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '927';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '928';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '929';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '930';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '931';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '932';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '933';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '934';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '935';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '936';
update T_AP set AP_SIHOT_CAT = '2BPB' where AP_CODE = '1007';
update T_AP set AP_SIHOT_CAT = '22SB' where AP_CODE = '1009';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '1010';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '1011';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '1012';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '1014';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '1015';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '1016';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '1017';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '1018';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '1019';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '1020';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '1021';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = '1022';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = '1023';
update T_AP set AP_SIHOT_CAT = '2STS' where AP_CODE = '1024';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '1025';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '1026';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '1027';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '1028';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '1029';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '1030';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '1031';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '1032';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '1033';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '1034';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '1035';
update T_AP set AP_SIHOT_CAT = '1STS' where AP_CODE = '1036';
update T_AP set AP_SIHOT_CAT = '2BPB' where AP_CODE = '1114';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '1116';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '1117';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '1118';
update T_AP set AP_SIHOT_CAT = 'STDH' where AP_CODE = '1119';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '1120';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '1121';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = '1122';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = '1123';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '1124';
update T_AP set AP_SIHOT_CAT = '2BSS' where AP_CODE = '1125';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = '1126';
update T_AP set AP_SIHOT_CAT = '22SS' where AP_CODE = '1127';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '1220';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '1221';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = '1222';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = '1223';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '1224';
update T_AP set AP_SIHOT_CAT = '2BSH' where AP_CODE = '1225';
update T_AP set AP_SIHOT_CAT = '1JNH' where AP_CODE = '1226';
update T_AP set AP_SIHOT_CAT = '22SS' where AP_CODE = '1227';

commit;



prompt setup SIHOT package values within our MKT_/BOARDS lookup classes

update T_LU set LU_CHAR = substr(LU_CHAR, 1, instr(LU_CHAR, ' SIHOT_PACK=') - 1)
 where LU_CLASS like '%BOARDS' and instr(LU_CHAR, 'SIHOT_PACK=') > 0;

update T_LU set LU_CHAR = LU_CHAR || ' SIHOT_PACK="' || F_SIHOT_NON_MUTAT_PACK(LU_CHAR, LU_DESC) 
                          || case when LU_CLASS = 'MKT_BOARDS' then 'W' end || '"'
 --select f_key_val(lu_char, 'ShiftId'), f_sihot_pack(LU_ID, case when LU_CLASS = 'MKT_BOARDS' then 'MKT_' end), t_lu.* from t_lu
 where LU_CLASS like '%BOARDS' and instr(LU_CHAR, 'SIHOT_PACK=') = 0;

commit;



prompt remove old support task entries between 2010 and 2014

delete from T_RUL where RUL_USER = 'SALES';

commit;


prompt init new RUL columns - (RARO RARO RARO) without the and 1=1 it shows a missing expression error

prompt .. first set only hotel room no (for to calculate later CAT/HOTEL based on the room), RATE and OBJID - needed 7:39 on SP.DEV
 
update T_RUL l
             set RUL_SIHOT_ROOM = F_RU_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY))
               , RUL_SIHOT_OBJID = (select RU_SIHOT_OBJID from T_RU where RU_CODE = RUL_PRIMARY)
               , RUL_SIHOT_RATE = (select RO_SIHOT_RATE from T_RU, T_RO where RU_ROREF = RO_CODE and RU_CODE = RUL_PRIMARY)
 where RUL_DATE >= DATE'2012-01-01'   -- SPEED-UP: exclude reservatio log entries before 2012
   and exists (select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ID = (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY))
   and (select RU_ATGENERIC from T_RU where RU_CODE = RUL_PRIMARY) is not NULL
   -- opti (only update the newest ones / used by V_ACU_RES_LOG - need exact same filter/where expression)
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and c.RUL_CODE > l.RUL_CODE)  -- excluding past log entries
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   -- exclude invalid clients, cancellations in the past and also pending MKT records (RU_RHREF is not NULL) and prevent to include/flag invalid ones with non-empty RUL_SIHOT_RATE
   and exists (select NULL from T_RU, V_ACU_CD_DATA where RU_CODE = RUL_PRIMARY and RU_CDREF = CD_CODE 
                                                      and RU_FROM_DATE + RU_DAYS >= DATE'2012-01-01' and (RU_STATUS <> 120 or RU_FROM_DATE + RU_DAYS > trunc(sysdate)) and RU_RHREF is not NULL) 
   and 1=1;

commit;

prompt .. then set HOTEL = 400k rows in 1min20 on SP.TEST
 
update T_RUL l
             set RUL_SIHOT_HOTEL = F_SIHOT_HOTEL(nvl(RUL_SIHOT_ROOM, (select RU_ATGENERIC || '@' || RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY)))
 where RUL_DATE >= DATE'2012-01-01'
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   and not exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY and RU_FROM_DATE + RU_DAYS < DATE'2012-01-01')
   and RUL_SIHOT_RATE is not NULL 
   and 1=1;

commit;


prompt .. then set CAT 

----- using F_SIHOT_CAT() slowed down this update to several days - for to speedup update will be done divided into several smaller chunks/cases
--update T_RUL l
--             set RUL_SIHOT_CAT = F_SIHOT_CAT(nvl(RUL_SIHOT_ROOM, 'RU' || RUL_PRIMARY))  -- nvl needed for deleted RUs and for 20 cancelled RUs from 2014 with 'Sterling Suites' in RU_ATGENERIC - see line 138 in Q_SIHOT_SETUP2.sql
-- where RUL_DATE >= DATE'2012-01-01'
--   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and c.RUL_CODE > l.RUL_CODE)
--   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
--   and 1=1;

-- first all the ones with ARO/room associated and set to room's category = 250k rows in 32 sec on SP.TEST
update T_RUL l
             set RUL_SIHOT_CAT = (select AP_SIHOT_CAT from T_AP where AP_CODE = RUL_SIHOT_ROOM)
 where not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   -- Date speed-up on log/arrival dates - to support RU delete (outer join to T_RU) check RU arr date with not exists
   and RUL_DATE >= DATE'2012-01-01'
   and not exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY and RU_FROM_DATE + RU_DAYS < DATE'2012-01-01') 
   and RUL_SIHOT_ROOM is not NULL
   and RUL_SIHOT_RATE is not NULL 
   and exists (select NULL from T_AP where AP_CODE = RUL_SIHOT_ROOM);

commit;

-- then the ones without requested apt features = 45k rows in 8 sec on SP.TEST
update T_RUL l
             set RUL_SIHOT_CAT = (select LU_CHAR from T_LU, T_RU
                                   where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end
                                     and LU_ID = RU_ATGENERIC
                                     and RU_CODE = RUL_PRIMARY)
 where not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   -- Date speed-up on log/arrival dates - to support RU delete (outer join to T_RU) check RU arr date with not exists
   and RUL_DATE >= DATE'2012-01-01'
   and exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY 
                                           and RU_FROM_DATE + RU_DAYS >= DATE'2012-01-01'
                                           and RU_ATGENERIC in ('HOTEL', 'STUDIO', '1 BED', '2 BED', '3 BED') --, '4 BED')
                                           and RU_RESORT in ('ANY', 'BHC', 'PBC') --, 'BHH', 'HMC')
              )
   and RUL_SIHOT_ROOM is NULL
   and RUL_SIHOT_RATE is not NULL 
   and not exists (select NULL from T_RAF where RAF_RUREF = RUL_PRIMARY);

commit;

-- then finally the ones with requested apt features and category overload == 1k rows in 5 sec
update T_RUL l
             set RUL_SIHOT_CAT = (select max(LU_CHAR) from T_LU, T_RU, T_RAF
                                   where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end
                                     and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and RU_CODE = RAF_RUREF
                                     and RU_CODE = RUL_PRIMARY)
 where RUL_DATE >= DATE'2012-01-01'
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   and exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY 
                                           and RU_FROM_DATE + RU_DAYS >= DATE'2012-01-01'
                                           and RU_ATGENERIC in ('HOTEL', 'STUDIO', '1 BED', '2 BED', '3 BED') --, '4 BED')
                                           and RU_RESORT in ('ANY', 'BHC', 'PBC') --, 'BHH', 'HMC')
              )
   and RUL_SIHOT_ROOM is NULL
   and RUL_SIHOT_RATE is not NULL 
   and exists (select NULL from T_LU, T_RU, T_RAF
                                   where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end
                                     and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and RU_CODE = RAF_RUREF
                                     and RU_CODE = RUL_PRIMARY);

commit;


prompt .. then finally set PACK (7 min on SP.TEST2, )
 
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
--   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and c.RUL_CODE > l.RUL_CODE)
--   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
--   and exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY and RU_FROM_DATE + RU_DAYS >= DATE'2012-01-01') 
--   and 1=1;

update T_RUL l
             set RUL_SIHOT_PACK = F_SIHOT_PACK((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'R') from T_RU where RU_CODE = RUL_PRIMARY))
--select F_SIHOT_PACK((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'R') from T_RU where RU_CODE = RUL_PRIMARY)), l.* from t_rul l
 where RUL_DATE >= DATE'2012-01-01'
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   and exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY and RU_FROM_DATE + RU_DAYS >= DATE'2012-01-01')
   --and RUL_SIHOT_PACK <> F_SIHOT_PACK((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS, 'R') from T_RU where RU_CODE = RUL_PRIMARY))
   and RUL_SIHOT_RATE is not NULL 
   and 1=1;

commit;


-- check log on uninitialized cats and hots
--select * from v_acu_res_log where rul_sihot_cat = 'R___' and exists (select NULL from T_RU where RU_CODE = rul_primary) and trunc(rul_date) != '6-OCT-2016'
--
select * from v_acu_res_filtered where (instr(rul_sihot_cat, '_') > 0 or rul_sihot_hotel <= 0);



prompt 'Finished  -  End Of Script'
exec P_PROC_SET('', '', '');
spool off


