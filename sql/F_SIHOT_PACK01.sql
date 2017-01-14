create or replace function LOBBY.SIHOT_PACK(pcBoardRef IN T_LU.LU_ID%type, pcLuClassPrefix IN T_LU.LU_CLASS%type := NULL)
  RETURN T_RUL.RUL_SIHOT_PACK%type
IS  
  lcPack   T_RUL.RUL_SIHOT_PACK%type := NULL;   -- varchar2(3 Byte);
  lcBoard  T_LU.LU_ID%type;
  lcPrefix T_LU.LU_CLASS%type;
  
  cursor cLuBoard is
    select * from T_LU where LU_CLASS = lcPrefix || 'BOARDS' and LU_ID = lcBoard;
  rLuBoard cLuBoard%rowtype;

BEGIN
  if substr(pcBoardRef, 1, 4) = 'MKT_' then
    lcPrefix := substr(pcBoardRef, 1, 4);
    lcBoard := substr(pcBoardRef, 5);
  else
    lcPrefix := pcLuClassPrefix;
    lcBoard := pcBoardRef;
  end if;
  open  cLuBoard;
  fetch cLuBoard into rLuBoard;
  if cLuBoard%found then
    lcPack := F_SIHOT_NON_MUTAT_PACK(rLuBoard.LU_CHAR, rLuBoard.LU_DESC);
  end if;
  close cLuBoard;
    
  return nvl(lcPack, 'RO');  -- default: ROOM ONLY
END
/*
  ae:27-08-16 V00: first beta - added for SIHOT sync/migration project.
  ae:27-12-16 V01: allow alternatively to pass board with 'MKT_' prefix.
*/;
/


create or replace public synonym F_SIHOT_PACK for LOBBY.SIHOT_PACK;

grant execute on LOBBY.SIHOT_PACK to SALES_00_MASTER;
grant execute on LOBBY.SIHOT_PACK to SALES_05_SYSADMIN;
grant execute on LOBBY.SIHOT_PACK to SALES_06_DEVELOPER;
grant execute on LOBBY.SIHOT_PACK to SALES_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_PACK to SALES_11_SUPERASSIST;
grant execute on LOBBY.SIHOT_PACK to SALES_15_CENTRAL;
grant execute on LOBBY.SIHOT_PACK to SALES_20_CONTRACTS;
grant execute on LOBBY.SIHOT_PACK to SALES_30_RESALES;
grant execute on LOBBY.SIHOT_PACK to SALES_40_COMPLETIONS;
grant execute on LOBBY.SIHOT_PACK to SALES_47_KEYS;
grant execute on LOBBY.SIHOT_PACK to SALES_49_MKTSUPER;
grant execute on LOBBY.SIHOT_PACK to SALES_50_MARKETING;
grant execute on LOBBY.SIHOT_PACK to SALES_52_TELEMARKETING;
grant execute on LOBBY.SIHOT_PACK to SALES_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_PACK to SALES_56_TOS;
grant execute on LOBBY.SIHOT_PACK to SALES_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_PACK to SALES_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_PACK to SALES_80_EXTERNAL;
grant execute on LOBBY.SIHOT_PACK to SALES_95_MARKETING_TRAINING;

grant execute on LOBBY.SIHOT_PACK to XL_00_MASTER;
grant execute on LOBBY.SIHOT_PACK to XL_05_SYSADMIN;
grant execute on LOBBY.SIHOT_PACK to XL_06_DEVELOPER;
grant execute on LOBBY.SIHOT_PACK to XL_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_PACK to XL_20_RECEPCION;
grant execute on LOBBY.SIHOT_PACK to XL_30_HOUSEKEEPING;
grant execute on LOBBY.SIHOT_PACK to XL_30_MAINTENANCE;
grant execute on LOBBY.SIHOT_PACK to XL_40_MFEES;
grant execute on LOBBY.SIHOT_PACK to XL_50_MARKETING;
grant execute on LOBBY.SIHOT_PACK to XL_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_PACK to XL_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_PACK to XL_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_PACK to XL_80_EXTERNAL;

grant execute on LOBBY.SIHOT_PACK to REPORTER;