create or replace function LOBBY.SIHOT_PAID_RAF(pnRU_Code IN T_RU.RU_CODE%type, 
                                                pcResort IN T_RU.RU_RESORT%type := NULL,
                                                pcAtGeneric IN T_RU.RU_ATGENERIC%type := NULL) 
  RETURN varchar2
IS  
  lcAtGeneric   T_RU.RU_ATGENERIC%type;
  lcResort      T_RU.RU_RESORT%type;
  lnAFT_Code    T_RAF.RAF_AFTREF%type;

  cursor cRU is
    select RU_RESORT, RU_ATGENERIC from T_RU where RU_CODE = pnRU_Code;
    
  cursor cRAF is
    select RAF_AFTREF
      from T_RAF, T_LU
     where substr(LU_CLASS, 1, 11) = 'SIHOT_CATS_' and substr(LU_CLASS, 12, 3) in (lcResort, 'ANY') 
       and substr(LU_ID, 1, length(lcAtGeneric)) = lcAtGeneric and substr(LU_ID, length(lcAtGeneric) + 2) = to_char(RAF_AFTREF)
       and RAF_RUREF = pnRU_Code
     order by RAF_AFTREF desc, substr(LU_CLASS, 12, 3) desc;  -- order to return smallest feature first and lcResort before ANY
    
BEGIN
  if pcResort is NULL then
    open  cRU;
    fetch cRU into lcResort, lcAtGeneric;
    close cRU;
  else
    lcResort := pcResort;
    lcAtGeneric := pcAtGeneric;
  end if;
  
  open  cRAF;
  fetch cRAF into lnAFT_Code;
  close cRAF;
  
  return case when lnAFT_Code is not NULL then '_' || to_char(lnAFT_Code) end;
END
/*
  ae:28-11-16 V00: first beta.
*/;
/


create or replace public synonym F_SIHOT_PAID_RAF for LOBBY.SIHOT_PAID_RAF;

grant execute on LOBBY.SIHOT_PAID_RAF to SALES_00_MASTER;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_05_SYSADMIN;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_06_DEVELOPER;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_11_SUPERASSIST;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_15_CENTRAL;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_20_CONTRACTS;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_30_RESALES;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_40_COMPLETIONS;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_47_KEYS;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_49_MKTSUPER;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_50_MARKETING;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_52_TELEMARKETING;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_56_TOS;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_80_EXTERNAL;
grant execute on LOBBY.SIHOT_PAID_RAF to SALES_95_MARKETING_TRAINING;

grant execute on LOBBY.SIHOT_PAID_RAF to XL_00_MASTER;
grant execute on LOBBY.SIHOT_PAID_RAF to XL_05_SYSADMIN;
grant execute on LOBBY.SIHOT_PAID_RAF to XL_06_DEVELOPER;
grant execute on LOBBY.SIHOT_PAID_RAF to XL_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_PAID_RAF to XL_20_RECEPCION;
grant execute on LOBBY.SIHOT_PAID_RAF to XL_30_HOUSEKEEPING;
grant execute on LOBBY.SIHOT_PAID_RAF to XL_30_MAINTENANCE;
grant execute on LOBBY.SIHOT_PAID_RAF to XL_40_MFEES;
grant execute on LOBBY.SIHOT_PAID_RAF to XL_50_MARKETING;
grant execute on LOBBY.SIHOT_PAID_RAF to XL_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_PAID_RAF to XL_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_PAID_RAF to XL_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_PAID_RAF to XL_80_EXTERNAL;

grant execute on LOBBY.SIHOT_PAID_RAF to REPORTER;