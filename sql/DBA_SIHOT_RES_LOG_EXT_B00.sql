--- VERSION 00: fixing hotel moves (determining and deleting/cancelling reservation for previous hotel) - planned roll out on 14-03-2017

-- max linesize - limitted by TOAD to 2000 (32767 is maximum for sqlPlus)
SET LINESIZE 32767
-- surpress page separator
SET NEWPAGE 0
SET PAGESIZE 0
-- add dbms_output.put_line onto spool log file
SET SERVEROUTPUT ON
-- trim trailing blanks from line end
SET TRIMSPOOL ON

spool DBA_SIHOT_RES_LOG_EXT_B00.log
exec P_PROC_SET('DBA_SIHOT_RES_LOG_EXT_B', '2017_V00', 'dev');


prompt DDL CHANGES

prompt add new columns to T_RUL for to store last hotel id and room category and changed RUL_SIHOT_ROOM (now Sihot Room number with leading zero for 3-digit PBC rooms)

alter table LOBBY.REQUESTED_UNIT_LOG add (RUL_SIHOT_LAST_CAT   VARCHAR2(6 BYTE) DEFAULT 'L___' NOT NULL);
alter table LOBBY.REQUESTED_UNIT_LOG add (RUL_SIHOT_LAST_HOTEL NUMBER(3)        DEFAULT -3  NOT NULL);

comment on column LOBBY.REQUESTED_UNIT_LOG.RUL_SIHOT_LAST_CAT   is 'Previous Unit/Price category in SIHOT system - overloaded if associated ARO exists';
comment on column LOBBY.REQUESTED_UNIT_LOG.RUL_SIHOT_LAST_HOTEL is 'Previous Hotel Id in SIHOT system - overloaded if associated ARO exists';

comment on column LOBBY.REQUESTED_UNIT_LOG.RUL_SIHOT_ROOM  is 'Booked apartment (AP_CODE as Sihot room number - with leading zero for 3-digit PBC rooms) if associated ARO record exits else NULL';


prompt compile changed views, procedures and trigger

@@F_SIHOT_CAT03.sql;

@@V_ACU_RES_LOG04.sql;
@@V_ACU_RES_FILTERED05.sql;

@@P_RH_RUL_INSERT01.sql;
@@P_RUL_INSERT05.sql;

@@E_ARO_DELETE08.sql;

prompt recompile also unchanged views for to update the * columns

@@V_ACU_RES_UNFILTERED02.sql;
@@V_ACU_RES_UNSYNCED05.sql;


prompt DATA CHANGES

prompt initialize new column RUL_SIHOT_LAST_HOTEL - need 3:28 on SP.DEV

update T_RUL set RUL_SIHOT_LAST_HOTEL = RUL_SIHOT_HOTEL, RUL_SIHOT_LAST_CAT = RUL_SIHOT_CAT
 where 1=1;

commit;

prompt change RUL_SIHOT_ROOM to Sihot room number format (adding leading zero for 3-digit PBC room numbers)

update T_RUL set RUL_SIHOT_ROOM = '0' || RUL_SIHOT_ROOM
 where RUL_SIHOT_HOTEL = 4 and length(RUL_SIHOT_ROOM) = 3;
 
commit;


prompt 'Finished  -  End Of Script'
exec P_PROC_SET('', '', '');
spool off


