create or replace function LOBBY.ARO_RU_CODE (pnRH_Code IN T_RH.RH_CODE%type, pdFrom IN date, pdTo IN date)
  RETURN T_RU.RU_CODE%type
IS
  lnRU_Code  T_RU.RU_CODE%type;
BEGIN
  select nvl((select max(RU_CODE) from T_RU where RU_RHREF = pnRH_Code and RU_FROM_DATE = pdFrom and RU_STATUS <> 120),
             nvl((select max(RU_CODE) from T_RU where RU_RHREF = pnRH_Code and RU_FROM_DATE < pdTo and RU_FROM_DATE + RU_DAYS > pdFrom and RU_STATUS <> 120),
                 (select max(RU_CODE) from T_RU where RU_RHREF = pnRH_Code and RU_FROM_DATE < pdTo and RU_FROM_DATE + RU_DAYS > pdFrom))) 
    into lnRU_Code from dual;
  return lnRU_Code;
END
/*
  ae:06-08-16 V00: first beta - added for SIHOT sync/migration project.
*/;
/


create or replace public synonym F_ARO_RU_CODE for LOBBY.ARO_RU_CODE;

grant execute on LOBBY.ARO_RU_CODE to SALES_00_MASTER;
grant execute on LOBBY.ARO_RU_CODE to SALES_05_SYSADMIN;
grant execute on LOBBY.ARO_RU_CODE to SALES_06_DEVELOPER;
grant execute on LOBBY.ARO_RU_CODE to SALES_10_SUPERVISOR;
grant execute on LOBBY.ARO_RU_CODE to SALES_11_SUPERASSIST;
grant execute on LOBBY.ARO_RU_CODE to SALES_15_CENTRAL;
grant execute on LOBBY.ARO_RU_CODE to SALES_20_CONTRACTS;
grant execute on LOBBY.ARO_RU_CODE to SALES_30_RESALES;
grant execute on LOBBY.ARO_RU_CODE to SALES_40_COMPLETIONS;
grant execute on LOBBY.ARO_RU_CODE to SALES_47_KEYS;
grant execute on LOBBY.ARO_RU_CODE to SALES_49_MKTSUPER;
grant execute on LOBBY.ARO_RU_CODE to SALES_50_MARKETING;
grant execute on LOBBY.ARO_RU_CODE to SALES_52_TELEMARKETING;
grant execute on LOBBY.ARO_RU_CODE to SALES_55_MANAGEMENT;
grant execute on LOBBY.ARO_RU_CODE to SALES_56_TOS;
grant execute on LOBBY.ARO_RU_CODE to SALES_60_RESERVATIONS;
grant execute on LOBBY.ARO_RU_CODE to SALES_70_ACCOUNTING;
grant execute on LOBBY.ARO_RU_CODE to SALES_80_EXTERNAL;
grant execute on LOBBY.ARO_RU_CODE to SALES_95_MARKETING_TRAINING;

grant execute on LOBBY.ARO_RU_CODE to XL_00_MASTER;
grant execute on LOBBY.ARO_RU_CODE to XL_05_SYSADMIN;
grant execute on LOBBY.ARO_RU_CODE to XL_06_DEVELOPER;
grant execute on LOBBY.ARO_RU_CODE to XL_10_SUPERVISOR;
grant execute on LOBBY.ARO_RU_CODE to XL_20_RECEPCION;
grant execute on LOBBY.ARO_RU_CODE to XL_30_HOUSEKEEPING;
grant execute on LOBBY.ARO_RU_CODE to XL_30_MAINTENANCE;
grant execute on LOBBY.ARO_RU_CODE to XL_40_MFEES;
grant execute on LOBBY.ARO_RU_CODE to XL_50_MARKETING;
grant execute on LOBBY.ARO_RU_CODE to XL_55_MANAGEMENT;
grant execute on LOBBY.ARO_RU_CODE to XL_60_RESERVATIONS;
grant execute on LOBBY.ARO_RU_CODE to XL_70_ACCOUNTING;
grant execute on LOBBY.ARO_RU_CODE to XL_80_EXTERNAL;

grant execute on LOBBY.ARO_RU_CODE to REPORTER;