create or replace view LOBBY.ACU_CD_FILTERED
  AS
select V_ACU_CD_LOG.*
     , V_ACU_CD_DATA.*
  from V_ACU_CD_DATA
  left outer join V_ACU_CD_LOG on CD_CODE = LOG_PRIMARY  -- CD is different to RU: some CD recs have no log entry and get never deleted
 where CD_SNAM1 is not NULL   -- filter out empty records around CD_CODE x200000 
   -- exclude rental clients with incomplete/wrong address
   and not (   upper(substr(nvl(CD_CITY, '_'), 1, 2)) = 'LC'
            or upper(nvl(CD_CITY, '_')) in ('X', 'XX', 'XXX', 'XXXX', 'XXXXX', 'XXXXXX') 
            or (CD_ADD11 is NULL and CD_ADD12 is NULL and CD_ADD13 is NULL and CD_POSTAL is NULL and CD_CITY is NULL) )
/*
  ae:02-10-16 first beta.
*/
/


create or replace public synonym V_ACU_CD_FILTERED for LOBBY.ACU_CD_FILTERED;

grant select on LOBBY.ACU_CD_FILTERED to SALES_00_MASTER;
grant select on LOBBY.ACU_CD_FILTERED to SALES_05_SYSADMIN;
grant select on LOBBY.ACU_CD_FILTERED to SALES_06_DEVELOPER;
grant select on LOBBY.ACU_CD_FILTERED to SALES_10_SUPERVISOR;
grant select on LOBBY.ACU_CD_FILTERED to SALES_60_RESERVATIONS;

grant select on LOBBY.ACU_CD_FILTERED to XL_00_MASTER;
grant select on LOBBY.ACU_CD_FILTERED to XL_05_SYSADMIN;
grant select on LOBBY.ACU_CD_FILTERED to XL_06_DEVELOPER;
grant select on LOBBY.ACU_CD_FILTERED to XL_10_SUPERVISOR;
grant select on LOBBY.ACU_CD_FILTERED to XL_60_RESERVATIONS;

grant select on LOBBY.ACU_CD_FILTERED to REPORTER;

