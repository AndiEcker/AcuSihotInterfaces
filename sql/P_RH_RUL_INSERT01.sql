create or replace procedure LOBBY.RH_RUL_INSERT
                            (pcCaller         IN varchar2,
                             pcAction         IN T_RUL.RUL_ACTION%type,
                             pcChanges        IN T_RUL.RUL_CHANGES%type,        -- with leading chr(13) seperator
                             pcBoardRef       IN T_LU.LU_ID%type,
                             pnCode           IN T_RU.RU_CODE%type := NULL,     -- RU_CODE if called from RU trigger or PRC_CODE if called from PRC trigger or NULL if called from ARO/RH/RAF
                             pcApRef          IN T_ARO.ARO_APREF%type := NULL,  -- only passed from T_ARO triggers (ARO overload)
                             pnRHRef          IN T_RU.RU_RHREF%type := NULL,
                             pdFrom           IN date := NULL,
                             pdTo             IN date := NULL
                            ) 
IS
  cursor cRU is
    select RU_CODE, RU_RHREF, RU_FROM_DATE, RU_DAYS, RU_BOARDREF, RU_ATGENERIC, RU_RESORT, RU_SIHOT_OBJID
         , RO_SIHOT_RATE
      from T_RU, T_RO
     where RU_ROREF = RO_CODE
       and RU_FROM_DATE < pdTo and RU_FROM_DATE + RU_DAYS > pdFrom and greatest(pdTo - RU_FROM_DATE, RU_FROM_DATE + RU_DAYS - pdFrom) >= RU_DAYS / 2 
       and RU_RHREF = pnRHRef;
  rRU cRU%rowtype;
  
  cursor cARO is
    select F_RH_ARO_APT(rRU.RU_RHREF, rRU.RU_FROM_DATE, rRU.RU_FROM_DATE + rRU.RU_DAYS) as ARO_APREF from dual;
  rARO cARO%rowtype;

BEGIN
  for rRU in cRU loop
    if pcCaller <> 'A' then    -- determine allocated apt if called from PRC or RH (not from ARO to prevent mutating trigger)
      open  cARO;
      fetch cARO into rARO;
      close cARO;
    end if;
    P_RUL_INSERT(pcCaller, pcAction, pcChanges, nvl(pcBoardRef, rRU.RU_BOARDREF), nvl(pnCode, rRU.RU_CODE), nvl(rARO.ARO_APREF, pcApRef),
                 rRU.RU_RHREF, rRU.RU_FROM_DATE, rRU.RU_FROM_DATE + rRU.RU_DAYS, rRU.RU_ATGENERIC, rRU.RU_RESORT, rRU.RU_SIHOT_OBJID, rRU.RO_SIHOT_RATE);
  end loop;
END
/*
  ae:19-02-17 V00: first beta to call P_RUL_INSERT() for each RU chunk (<= 7 days) associated to an ARO/PRC/RH with > 7 days.
  ae:11-03-17 V01: removed unused parameters pcAtGeneric, pcResort, pnObjId and pcRate.
*/;
/


create or replace public synonym P_RH_RUL_INSERT for LOBBY.RH_RUL_INSERT;


grant execute on LOBBY.RH_RUL_INSERT to SALES_00_MASTER;
grant execute on LOBBY.RH_RUL_INSERT to SALES_05_SYSADMIN;
grant execute on LOBBY.RH_RUL_INSERT to SALES_06_DEVELOPER;
grant execute on LOBBY.RH_RUL_INSERT to SALES_10_SUPERVISOR;
grant execute on LOBBY.RH_RUL_INSERT to SALES_11_SUPERASSIST;
grant execute on LOBBY.RH_RUL_INSERT to SALES_15_CENTRAL;
grant execute on LOBBY.RH_RUL_INSERT to SALES_20_CONTRACTS;
grant execute on LOBBY.RH_RUL_INSERT to SALES_30_RESALES;
grant execute on LOBBY.RH_RUL_INSERT to SALES_40_COMPLETIONS;
grant execute on LOBBY.RH_RUL_INSERT to SALES_47_KEYS;
grant execute on LOBBY.RH_RUL_INSERT to SALES_49_MKTSUPER;
grant execute on LOBBY.RH_RUL_INSERT to SALES_50_MARKETING;
grant execute on LOBBY.RH_RUL_INSERT to SALES_51_TMSUPER;
grant execute on LOBBY.RH_RUL_INSERT to SALES_52_TELEMARKETING;
grant execute on LOBBY.RH_RUL_INSERT to SALES_55_MANAGEMENT;
grant execute on LOBBY.RH_RUL_INSERT to SALES_56_TOS;
grant execute on LOBBY.RH_RUL_INSERT to SALES_58_RECEPTION;
grant execute on LOBBY.RH_RUL_INSERT to SALES_60_RESERVATIONS;
grant execute on LOBBY.RH_RUL_INSERT to SALES_70_ACCOUNTING;
grant execute on LOBBY.RH_RUL_INSERT to SALES_80_EXTERNAL;
grant execute on LOBBY.RH_RUL_INSERT to SALES_95_MARKETING_TRAINING;

grant execute on LOBBY.RH_RUL_INSERT to XL_00_MASTER;
grant execute on LOBBY.RH_RUL_INSERT to XL_05_SYSADMIN;
grant execute on LOBBY.RH_RUL_INSERT to XL_06_DEVELOPER;
grant execute on LOBBY.RH_RUL_INSERT to XL_10_SUPERVISOR;
grant execute on LOBBY.RH_RUL_INSERT to XL_20_RECEPCION;
grant execute on LOBBY.RH_RUL_INSERT to XL_30_HOUSEKEEPING;
grant execute on LOBBY.RH_RUL_INSERT to XL_30_MAINTENANCE;
grant execute on LOBBY.RH_RUL_INSERT to XL_40_MFEES;
grant execute on LOBBY.RH_RUL_INSERT to XL_50_MARKETING;
grant execute on LOBBY.RH_RUL_INSERT to XL_55_MANAGEMENT;
grant execute on LOBBY.RH_RUL_INSERT to XL_60_RESERVATIONS;
grant execute on LOBBY.RH_RUL_INSERT to XL_70_ACCOUNTING;
grant execute on LOBBY.RH_RUL_INSERT to XL_80_EXTERNAL;
