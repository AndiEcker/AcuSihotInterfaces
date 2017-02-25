-- renamed F_RH_ARO_APT() into F_RH_ARO_APT()
drop function LOBBY.RU_ARO_APT;

create or replace function LOBBY.RH_ARO_APT (pnRH_Code IN T_RH.RH_CODE%type, pdFrom IN date, pdTo IN date)
  RETURN T_AP.AP_CODE%type
IS
  lcApt     T_ARO.ARO_APREF%type := NULL;
  lcLastApt T_ARO.ARO_APREF%type;
  
  cursor cARO is
    select * from T_ARO where ARO_RHREF = pnRH_Code and ARO_EXP_ARRIVE < pdTo and ARO_EXP_DEPART > pdFrom and ARO_STATUS <> 120
     order by nvl(ARO_RECD_KEY, nvl(ARO_TIMEIN, ARO_EXP_ARRIVE));
     
BEGIN
  if pdFrom > trunc(sysdate) then
    -- optimizing for future arrivals (there is no problem with duplicate AROs with the same expected arrival date)
    select nvl((select ARO_APREF from T_ARO where ARO_RHREF = pnRH_Code and ARO_EXP_ARRIVE = pdFrom and ARO_STATUS <> 120),
               (select max(ARO_APREF) from T_ARO where ARO_RHREF = pnRH_Code and ARO_EXP_ARRIVE < pdTo and ARO_EXP_DEPART > pdFrom and ARO_STATUS <> 120)) 
      into lcApt from dual;
  else
    -- Lobby/Reception can create duplicate AROs e.g. if the client doesn't like the apartment and get transferred to a new one (on arrival or next day)
    for rARO in cARO loop
      lcLastApt := rARO.ARO_APREF;
      if rARO.ARO_EXP_ARRIVE = pdFrom and trunc(nvl(rARO.ARO_TIMEOUT, rARO.ARO_EXP_DEPART)) = pdTo then
        lcApt := rARO.ARO_APREF;
        exit;    -- exact match no further checks needed - exit the loop
      elsif trunc(nvl(rARO.ARO_RECD_KEY, nvl(rARO.ARO_TIMEIN, rARO.ARO_EXP_ARRIVE))) < trunc(rARO.ARO_TIMEOUT) then  -- skip duplicate res done by transfer on first day into other apt
        lcApt := rARO.ARO_APREF; -- found apt but maybe there is a more actual one after (loop cursor ordered by arrival date)
      end if;
    end loop;
    if lcApt is Null then
      lcApt := lcLastApt;
    end if;
  end if;
  
  return lcApt;
END
/*
  ae:05-08-16 V00: first beta - added for SIHOT sync/migration project.
  ae:21-02-17 V01: changed name from F_RU_ARO_APT() into F_RH_ARO_APT().
*/;
/


create or replace public synonym F_RH_ARO_APT for LOBBY.RH_ARO_APT;

grant execute on LOBBY.RH_ARO_APT to SALES_00_MASTER;
grant execute on LOBBY.RH_ARO_APT to SALES_05_SYSADMIN;
grant execute on LOBBY.RH_ARO_APT to SALES_06_DEVELOPER;
grant execute on LOBBY.RH_ARO_APT to SALES_10_SUPERVISOR;
grant execute on LOBBY.RH_ARO_APT to SALES_11_SUPERASSIST;
grant execute on LOBBY.RH_ARO_APT to SALES_15_CENTRAL;
grant execute on LOBBY.RH_ARO_APT to SALES_20_CONTRACTS;
grant execute on LOBBY.RH_ARO_APT to SALES_30_RESALES;
grant execute on LOBBY.RH_ARO_APT to SALES_40_COMPLETIONS;
grant execute on LOBBY.RH_ARO_APT to SALES_47_KEYS;
grant execute on LOBBY.RH_ARO_APT to SALES_49_MKTSUPER;
grant execute on LOBBY.RH_ARO_APT to SALES_50_MARKETING;
grant execute on LOBBY.RH_ARO_APT to SALES_52_TELEMARKETING;
grant execute on LOBBY.RH_ARO_APT to SALES_55_MANAGEMENT;
grant execute on LOBBY.RH_ARO_APT to SALES_56_TOS;
grant execute on LOBBY.RH_ARO_APT to SALES_60_RESERVATIONS;
grant execute on LOBBY.RH_ARO_APT to SALES_70_ACCOUNTING;
grant execute on LOBBY.RH_ARO_APT to SALES_80_EXTERNAL;
grant execute on LOBBY.RH_ARO_APT to SALES_95_MARKETING_TRAINING;

grant execute on LOBBY.RH_ARO_APT to XL_00_MASTER;
grant execute on LOBBY.RH_ARO_APT to XL_05_SYSADMIN;
grant execute on LOBBY.RH_ARO_APT to XL_06_DEVELOPER;
grant execute on LOBBY.RH_ARO_APT to XL_10_SUPERVISOR;
grant execute on LOBBY.RH_ARO_APT to XL_20_RECEPCION;
grant execute on LOBBY.RH_ARO_APT to XL_30_HOUSEKEEPING;
grant execute on LOBBY.RH_ARO_APT to XL_30_MAINTENANCE;
grant execute on LOBBY.RH_ARO_APT to XL_40_MFEES;
grant execute on LOBBY.RH_ARO_APT to XL_50_MARKETING;
grant execute on LOBBY.RH_ARO_APT to XL_55_MANAGEMENT;
grant execute on LOBBY.RH_ARO_APT to XL_60_RESERVATIONS;
grant execute on LOBBY.RH_ARO_APT to XL_70_ACCOUNTING;
grant execute on LOBBY.RH_ARO_APT to XL_80_EXTERNAL;

grant execute on LOBBY.RH_ARO_APT to REPORTER;
