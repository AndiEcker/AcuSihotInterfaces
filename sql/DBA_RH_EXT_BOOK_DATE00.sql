--- VERSION 00: 
-- Omnis changes:
-- o CORE.RESERVATION_HEADER: added new column RH_EXT_BOOK_DATE.
-- o RESERVA.oImport.$RecReqBook(): added code line to pass RH_EXT_BOOK_DATE value from import data to oRequest.irRH.
-- o RESERVA.oRequest.$Save(): save new column RH_EXT_BOOK_DATE via P_RESL_WEEK_REQ() or irRH.$update().
-- o RESERVA.oTourOpImport.TkRecLoadLine(): loadddd date from column 26 into new column RH_EXT_BOOK_DATE.


-- max linesize - limitted by TOAD to 2000 (32767 is maximum for sqlPlus)
SET LINESIZE 32767
-- surpress page separator
SET NEWPAGE 0
SET PAGESIZE 0
-- add dbms_output.put_line onto spool log file
SET SERVEROUTPUT ON
-- trim trailing blanks from line end
SET TRIMSPOOL ON

spool DBA_RH_EXT_BOOK_DATE.log
exec P_PROC_SET('DBA_RH_EXT_BOOK_DATE', '2016_V00', 'dev');


prompt DDL CHANGES

alter table LOBBY.RESERVATION_HEADER add (RH_EXT_BOOK_DATE DATE);
comment on column LOBBY.RESERVATION_HEADER.RH_EXT_BOOK_DATE is 'External booking purchasing date';


@@P_RESL_WEEK_REQ08.sql;



prompt DATA CHANGES

prompt initialize RH_EXT_BOOK_DATE for all historical TK reservations to the day before import (which is correct for most the cases)

update T_RH set RH_EXT_BOOK_DATE = trunc(RH_CWHEN - 1)
 where RH_ROREF in ('tk', 'TK');

commit;

prompt 'Finished  -  End Of Script'
exec P_PROC_SET('', '', '');
spool off