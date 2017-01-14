create or replace function LOBBY.SIHOT_CAT(pcAptOrGenAtRs IN varchar2)  -- either AP_CODE  or  AT_GENERIC@AT_RSREF[_AFT_CODE]  or  'RU' || RU_CODE  or  'R_' || RU_CODE (last one includes RUL/ARO/PRC/.. overloads)
  RETURN T_RUL.RUL_SIHOT_CAT%type
IS  
  lnPos         number;
  lnRUCode      T_RU.RU_CODE%type;
  lcResort      T_RU.RU_RESORT%type;
  lcRSAft       varchar2(39);
  lcAtGeneric   T_RU.RU_ATGENERIC%type;
  lcAftSuffix   varchar2(12);
  lcSihotCat    T_RUL.RUL_SIHOT_CAT%type := NULL;

  cursor cRU is
    select RU_RESORT, RU_ATGENERIC, 
           F_SIHOT_PAID_RAF(RU_CODE, RU_RESORT, RU_ATGENERIC)
      from T_RU
     where RU_CODE = lnRUCode;

  cursor cRL is
    select case when RU_RESORT = 'ANY' and RUL_SIHOT_ROOM is not NULL then F_RESORT(RUL_SIHOT_ROOM) else RU_RESORT end, RU_ATGENERIC, 
           F_SIHOT_PAID_RAF(RU_CODE, case when RU_RESORT = 'ANY' and RUL_SIHOT_ROOM is not NULL then F_RESORT(RUL_SIHOT_ROOM) else RU_RESORT end, RU_ATGENERIC)
      from T_RU, V_ACU_RES_LOG
     where RU_CODE = RUL_PRIMARY(+)
       and RU_CODE = lnRUCode;

  cursor cLU_AFT_CATS is
    select LU_CHAR from T_LU
     where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || lcResort and LU_ID = lcAtGeneric || lcAftSuffix and LU_ACTIVE = 1) then 'SIHOT_CATS_' || lcResort else 'SIHOT_CATS_ANY' end
       and LU_ID = lcAtGeneric || lcAftSuffix
     order by LU_CLASS desc;

  cursor cLU_CATS is
    select LU_CHAR from T_LU
     where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || lcResort and LU_ID = lcAtGeneric and LU_ACTIVE = 1) then 'SIHOT_CATS_' || lcResort else 'SIHOT_CATS_ANY' end
       and LU_ID = lcAtGeneric;

  cursor cAP is
    select AP_SIHOT_CAT from T_AP where AP_CODE = pcAptOrGenAtRs;
  
BEGIN
  if substr(pcAptOrGenAtRs, 1, 1) = 'R' then
    lnRUCode := to_number(substr(pcAptOrGenAtRs, 3));
    if substr(pcAptOrGenAtRs, 1, 2) = 'RU' then
      open  cRU;
      fetch cRU into lcResort, lcAtGeneric, lcAftSuffix;
      close cRU;
    else                        -- R_ prefix
      open  cRL;
      fetch cRL into lcResort, lcAtGeneric, lcAftSuffix;
      close cRL;
    end if;
    if lcAftSuffix is not NULL then
      open  cLU_AFT_CATS;
      fetch cLU_AFT_CATS into lcSihotCat;
      close cLU_AFT_CATS;
    end if;
    if lcSihotCat is NULL then
      open  cLU_CATS;
      fetch cLU_CATS into lcSihotCat;
      close cLU_CATS;
    end if;
  else
    lnPos := instr(pcAptOrGenAtRs, '@');
    if lnPos > 0 then
      lcAtGeneric := substr(pcAptOrGenAtRs, 1, lnPos - 1);
      lcRSAft := substr(pcAptOrGenAtRs, lnPos + 1);
      lnPos := instr(lcRSAft, '_');
      if lnPos > 0 then
        lcAftSuffix := substr(lcRSAft, lnPos);
        lcResort := substr(lcRSAft, 1, lnPos - 1);
        open  cLU_AFT_CATS;
        fetch cLU_AFT_CATS into lcSihotCat;
        close cLU_AFT_CATS;
      else
        lcResort := lcRSAft;
      end if;
      if lcSihotCat is NULL then
        open  cLU_CATS;
        fetch cLU_CATS into lcSihotCat;
        close cLU_CATS;
      end if;
    else
      open  cAP;
      fetch cAP into lcSihotCat;
      close cAP;
    end if;
  end if;
  return nvl(lcSihotCat, '_C_');
END
/*
  ae:10-09-16 V00: first beta - added for SIHOT sync/migration project.
  ae:28-11-16 V01: added optional apartment feature check and allowing to pass RU code alternatively.
  ae:16-12-16 V02: removed T_RUL overload check from RU<RU_CODE> call (but kept as alternative R_<RU_CODE> call - currently unused). 
*/;
/


create or replace public synonym F_SIHOT_CAT for LOBBY.SIHOT_CAT;

grant execute on LOBBY.SIHOT_CAT to SALES_00_MASTER;
grant execute on LOBBY.SIHOT_CAT to SALES_05_SYSADMIN;
grant execute on LOBBY.SIHOT_CAT to SALES_06_DEVELOPER;
grant execute on LOBBY.SIHOT_CAT to SALES_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_CAT to SALES_11_SUPERASSIST;
grant execute on LOBBY.SIHOT_CAT to SALES_15_CENTRAL;
grant execute on LOBBY.SIHOT_CAT to SALES_20_CONTRACTS;
grant execute on LOBBY.SIHOT_CAT to SALES_30_RESALES;
grant execute on LOBBY.SIHOT_CAT to SALES_40_COMPLETIONS;
grant execute on LOBBY.SIHOT_CAT to SALES_47_KEYS;
grant execute on LOBBY.SIHOT_CAT to SALES_49_MKTSUPER;
grant execute on LOBBY.SIHOT_CAT to SALES_50_MARKETING;
grant execute on LOBBY.SIHOT_CAT to SALES_52_TELEMARKETING;
grant execute on LOBBY.SIHOT_CAT to SALES_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_CAT to SALES_56_TOS;
grant execute on LOBBY.SIHOT_CAT to SALES_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_CAT to SALES_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_CAT to SALES_80_EXTERNAL;
grant execute on LOBBY.SIHOT_CAT to SALES_95_MARKETING_TRAINING;

grant execute on LOBBY.SIHOT_CAT to XL_00_MASTER;
grant execute on LOBBY.SIHOT_CAT to XL_05_SYSADMIN;
grant execute on LOBBY.SIHOT_CAT to XL_06_DEVELOPER;
grant execute on LOBBY.SIHOT_CAT to XL_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_CAT to XL_20_RECEPCION;
grant execute on LOBBY.SIHOT_CAT to XL_30_HOUSEKEEPING;
grant execute on LOBBY.SIHOT_CAT to XL_30_MAINTENANCE;
grant execute on LOBBY.SIHOT_CAT to XL_40_MFEES;
grant execute on LOBBY.SIHOT_CAT to XL_50_MARKETING;
grant execute on LOBBY.SIHOT_CAT to XL_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_CAT to XL_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_CAT to XL_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_CAT to XL_80_EXTERNAL;

grant execute on LOBBY.SIHOT_CAT to REPORTER;
