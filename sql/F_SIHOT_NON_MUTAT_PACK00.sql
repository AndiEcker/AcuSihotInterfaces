create or replace function LOBBY.SIHOT_NON_MUTAT_PACK(pcLuChar IN T_LU.LU_CHAR%type, pcLuDesc IN T_LU.LU_DESC%type := NULL)
  RETURN T_RUL.RUL_SIHOT_PACK%type
IS  
  lcPack   T_RUL.RUL_SIHOT_PACK%type := NULL;   -- varchar2(3 Byte);
  
BEGIN
  lcPack := F_KEY_VAL(pcLuChar, 'SIHOT_PACK');
  if lcPack is NULL then  -- board sihot package lookup key vals not initialized (should not happen - only needed for initial setup/rollout)
    if F_KEY_VAL(pcLuChar, 'Lunch_Meal', '0') = '1' then  -- FULL BOARD or ALL INCLUSIVE (or LUNCH ONLY - no longer needed because is direct charge in Acumen)
      lcPack := case when instr(upper(pcLuDesc), 'ALL INC') > 0 then 'AI' else 'FB' end;
                     --when F_KEY_VAL(pcLuChar, 'Breakfast_Meal', '0') = '1' then 'FB'
                     --when F_KEY_VAL(pcLuChar, 'Dinner_Meal', '0') = '1' then 'Ld' else 'LO' end;
    elsif F_KEY_VAL(pcLuChar, 'Dinner_Meal', '0') = '1' then  -- HALF BOARD (or DINNER ONLY - no longer needed)
      lcPack := 'HB'; --case when F_KEY_VAL(rLuBoard.LU_CHAR, 'Breakfast_Meal', '0') = '1' then 'HB' else 'DO' end;
    elsif F_KEY_VAL(pcLuChar, 'Breakfast_Meal', '0') = '1' then  -- BED+BREAKFAST
      lcPack := 'BB';
    end if;
  end if;
    
  return nvl(lcPack, 'RO');  -- default: ROOM ONLY
END
/*
  ae:27-08-16 V00: first beta - added for SIHOT sync/migration project (actually only used in DBA_SIHOT_RES_SYNC for to prevent ORA-04091 mutation error).
*/;
/


create or replace public synonym F_SIHOT_NON_MUTAT_PACK for LOBBY.SIHOT_NON_MUTAT_PACK;

grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_00_MASTER;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_05_SYSADMIN;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_06_DEVELOPER;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_11_SUPERASSIST;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_15_CENTRAL;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_20_CONTRACTS;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_30_RESALES;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_40_COMPLETIONS;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_47_KEYS;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_49_MKTSUPER;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_50_MARKETING;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_52_TELEMARKETING;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_56_TOS;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_80_EXTERNAL;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to SALES_95_MARKETING_TRAINING;

grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to XL_00_MASTER;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to XL_05_SYSADMIN;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to XL_06_DEVELOPER;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to XL_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to XL_20_RECEPCION;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to XL_30_HOUSEKEEPING;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to XL_30_MAINTENANCE;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to XL_40_MFEES;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to XL_50_MARKETING;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to XL_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to XL_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to XL_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to XL_80_EXTERNAL;

grant execute on LOBBY.SIHOT_NON_MUTAT_PACK to REPORTER;