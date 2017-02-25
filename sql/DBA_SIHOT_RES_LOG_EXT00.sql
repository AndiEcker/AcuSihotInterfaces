--- VERSION 00: 

-- max linesize - limitted by TOAD to 2000 (32767 is maximum for sqlPlus)
SET LINESIZE 32767
-- surpress page separator
SET NEWPAGE 0
SET PAGESIZE 0
-- add dbms_output.put_line onto spool log file
SET SERVEROUTPUT ON
-- trim trailing blanks from line end
SET TRIMSPOOL ON

spool DBA_SIHOT_RES_LOG_EXT00.log
exec P_PROC_SET('DBA_SIHOT_RES_LOG_EXT', '2017_V00', 'dev');


prompt DDL CHANGES

@@F_RH_ARO_APT01.sql;

@@P_RESL_APT_LINK15.sql;
@@P_RUL_INSERT04.sql;
@@P_RH_RUL_INSERT00.sql;

@@E_ARO_DELETE07.sql;
@@E_ARO_INSERT06.sql;
@@E_ARO_UPDATE10.sql;
@@E_PRC_UPDATE07.sql;
@@E_RAF_CHANGE01.sql;
@@E_RH_UPDATE06.sql;
@@E_RU_UPDATE04.sql;
@@E_RU_INSERT03.sql;
@@E_RU_DELETE03.sql;


prompt 'Finished  -  End Of Script'
exec P_PROC_SET('', '', '');
spool off


