create or replace function SALES.CONST_VALUE_NUM (constant_name IN varchar2)
  return NUMBER deterministic
AS
   res number; 
BEGIN
   execute immediate 'begin :res := ' || constant_name || '; end;' using out res;     
   return res;
END
/*
  ae:03-05-17 V00: first beta
*/;
/

create or replace public synonym F_CONST_VALUE_NUM for SALES.CONST_VALUE_NUM;


grant execute on SALES.CONST_VALUE_NUM to SALES_00_MASTER;
grant execute on SALES.CONST_VALUE_NUM to SALES_05_SYSADMIN;
grant execute on SALES.CONST_VALUE_NUM to SALES_06_DEVELOPER;
grant execute on SALES.CONST_VALUE_NUM to SALES_10_SUPERVISOR;
grant execute on SALES.CONST_VALUE_NUM to SALES_11_SUPERASSIST;
grant execute on SALES.CONST_VALUE_NUM to SALES_15_CENTRAL;
grant execute on SALES.CONST_VALUE_NUM to SALES_20_CONTRACTS;
grant execute on SALES.CONST_VALUE_NUM to SALES_30_RESALES;
grant execute on SALES.CONST_VALUE_NUM to SALES_40_COMPLETIONS;
grant execute on SALES.CONST_VALUE_NUM to SALES_47_KEYS;
grant execute on SALES.CONST_VALUE_NUM to SALES_49_MKTSUPER;
grant execute on SALES.CONST_VALUE_NUM to SALES_50_MARKETING;
grant execute on SALES.CONST_VALUE_NUM to SALES_51_TMSUPER;
grant execute on SALES.CONST_VALUE_NUM to SALES_52_TELEMARKETING;
grant execute on SALES.CONST_VALUE_NUM to SALES_55_MANAGEMENT;
grant execute on SALES.CONST_VALUE_NUM to SALES_56_TOS;
grant execute on SALES.CONST_VALUE_NUM to SALES_58_RECEPTION;
grant execute on SALES.CONST_VALUE_NUM to SALES_60_RESERVATIONS;
grant execute on SALES.CONST_VALUE_NUM to SALES_70_ACCOUNTING;
grant execute on SALES.CONST_VALUE_NUM to SALES_80_EXTERNAL;
grant execute on SALES.CONST_VALUE_NUM to SALES_95_MARKETING_TRAINING;

grant execute on SALES.CONST_VALUE_NUM to XL_00_MASTER;
grant execute on SALES.CONST_VALUE_NUM to XL_05_SYSADMIN;
grant execute on SALES.CONST_VALUE_NUM to XL_06_DEVELOPER;
grant execute on SALES.CONST_VALUE_NUM to XL_10_SUPERVISOR;
grant execute on SALES.CONST_VALUE_NUM to XL_20_RECEPCION;
grant execute on SALES.CONST_VALUE_NUM to XL_30_HOUSEKEEPING;
grant execute on SALES.CONST_VALUE_NUM to XL_30_MAINTENANCE;
grant execute on SALES.CONST_VALUE_NUM to XL_40_MFEES;
grant execute on SALES.CONST_VALUE_NUM to XL_50_MARKETING;
grant execute on SALES.CONST_VALUE_NUM to XL_55_MANAGEMENT;
grant execute on SALES.CONST_VALUE_NUM to XL_60_RESERVATIONS;
grant execute on SALES.CONST_VALUE_NUM to XL_70_ACCOUNTING;
grant execute on SALES.CONST_VALUE_NUM to XL_80_EXTERNAL;
