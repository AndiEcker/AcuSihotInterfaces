create or replace function LOBBY.SIHOT_HOTEL(pcAptOrGenAtRs IN varchar2)
  RETURN T_RUL.RUL_SIHOT_HOTEL%type
IS  
  lnPos         number;
  lcResort      T_RU.RU_RESORT%type;
  lnSihotHotel  T_RUL.RUL_SIHOT_HOTEL%type := NULL;

  cursor cLU_HOTELS is
    select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ID = lcResort;
  
  cursor cAP is
    select AP_SIHOT_HOTEL from T_AP where AP_CODE = pcAptOrGenAtRs;
  
BEGIN
  lnPos := instr(pcAptOrGenAtRs, '@');
  if lnPos > 0 then
    lcResort := substr(pcAptOrGenAtRs, lnPos + 1);
    open  cLU_HOTELS;
    fetch cLU_HOTELS into lnSihotHotel;
    close cLU_HOTELS;
  else
    open  cAP;
    fetch cAP into lnSihotHotel;
    close cAP;
  end if;
  return nvl(lnSihotHotel, -96);
END
/*
  ae:10-09-16 V00: first beta - added for SIHOT sync/migration project.
*/;
/


create or replace public synonym F_SIHOT_HOTEL for LOBBY.SIHOT_HOTEL;

grant execute on LOBBY.SIHOT_HOTEL to SALES_00_MASTER;
grant execute on LOBBY.SIHOT_HOTEL to SALES_05_SYSADMIN;
grant execute on LOBBY.SIHOT_HOTEL to SALES_06_DEVELOPER;
grant execute on LOBBY.SIHOT_HOTEL to SALES_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_HOTEL to SALES_11_SUPERASSIST;
grant execute on LOBBY.SIHOT_HOTEL to SALES_15_CENTRAL;
grant execute on LOBBY.SIHOT_HOTEL to SALES_20_CONTRACTS;
grant execute on LOBBY.SIHOT_HOTEL to SALES_30_RESALES;
grant execute on LOBBY.SIHOT_HOTEL to SALES_40_COMPLETIONS;
grant execute on LOBBY.SIHOT_HOTEL to SALES_47_KEYS;
grant execute on LOBBY.SIHOT_HOTEL to SALES_49_MKTSUPER;
grant execute on LOBBY.SIHOT_HOTEL to SALES_50_MARKETING;
grant execute on LOBBY.SIHOT_HOTEL to SALES_52_TELEMARKETING;
grant execute on LOBBY.SIHOT_HOTEL to SALES_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_HOTEL to SALES_56_TOS;
grant execute on LOBBY.SIHOT_HOTEL to SALES_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_HOTEL to SALES_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_HOTEL to SALES_80_EXTERNAL;
grant execute on LOBBY.SIHOT_HOTEL to SALES_95_MARKETING_TRAINING;

grant execute on LOBBY.SIHOT_HOTEL to XL_00_MASTER;
grant execute on LOBBY.SIHOT_HOTEL to XL_05_SYSADMIN;
grant execute on LOBBY.SIHOT_HOTEL to XL_06_DEVELOPER;
grant execute on LOBBY.SIHOT_HOTEL to XL_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_HOTEL to XL_20_RECEPCION;
grant execute on LOBBY.SIHOT_HOTEL to XL_30_HOUSEKEEPING;
grant execute on LOBBY.SIHOT_HOTEL to XL_30_MAINTENANCE;
grant execute on LOBBY.SIHOT_HOTEL to XL_40_MFEES;
grant execute on LOBBY.SIHOT_HOTEL to XL_50_MARKETING;
grant execute on LOBBY.SIHOT_HOTEL to XL_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_HOTEL to XL_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_HOTEL to XL_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_HOTEL to XL_80_EXTERNAL;

grant execute on LOBBY.SIHOT_HOTEL to REPORTER;