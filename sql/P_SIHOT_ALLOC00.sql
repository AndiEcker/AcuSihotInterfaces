create or replace procedure LOBBY.SIHOT_ALLOC
                            (pcAction         IN varchar,                       -- CI=Check-in, CO=Check-out, RM=Room move/Transfer
                             pcApt            IN T_AP.AP_CODE%type              -- Acumen apartment number (for 3-digit PBC apartments without leading zero/0)
                            ) 
IS

BEGIN
  if pcAction in ('CO', 'RM') then
    update T_ARO set ARO_TIMEOUT = sysdate,
                     ARO_STATUS = case when pcAction = 'RM' then 320 else 390 end
     where ARO_STATUS = 300 and ARO_APREF = pcApt and trunc(sysdate) between ARO_EXP_ARRIVE and ARO_EXP_DEPART;
  end if;        
  if pcAction in ('CI', 'RM') then
    update T_ARO set ARO_TIMEIN = sysdate,
                     ARO_STATUS = case when pcAction = 'RM' then 330 else 300 end
     where ARO_STATUS = 200 and ARO_APREF = pcApt and trunc(sysdate) between ARO_EXP_ARRIVE and ARO_EXP_DEPART;
  end if;
END
/*
  ae:14-12-16 first beta - for SIHOT sync/migration project.
*/;
/


create or replace public synonym P_SIHOT_ALLOC for LOBBY.SIHOT_ALLOC;


grant execute on LOBBY.SIHOT_ALLOC to SALES_00_MASTER;
grant execute on LOBBY.SIHOT_ALLOC to SALES_05_SYSADMIN;
grant execute on LOBBY.SIHOT_ALLOC to SALES_06_DEVELOPER;
grant execute on LOBBY.SIHOT_ALLOC to SALES_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_ALLOC to SALES_11_SUPERASSIST;
grant execute on LOBBY.SIHOT_ALLOC to SALES_15_CENTRAL;
grant execute on LOBBY.SIHOT_ALLOC to SALES_20_CONTRACTS;
grant execute on LOBBY.SIHOT_ALLOC to SALES_30_RESALES;
grant execute on LOBBY.SIHOT_ALLOC to SALES_40_COMPLETIONS;
grant execute on LOBBY.SIHOT_ALLOC to SALES_47_KEYS;
grant execute on LOBBY.SIHOT_ALLOC to SALES_49_MKTSUPER;
grant execute on LOBBY.SIHOT_ALLOC to SALES_50_MARKETING;
grant execute on LOBBY.SIHOT_ALLOC to SALES_51_TMSUPER;
grant execute on LOBBY.SIHOT_ALLOC to SALES_52_TELEMARKETING;
grant execute on LOBBY.SIHOT_ALLOC to SALES_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_ALLOC to SALES_56_TOS;
grant execute on LOBBY.SIHOT_ALLOC to SALES_58_RECEPTION;
grant execute on LOBBY.SIHOT_ALLOC to SALES_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_ALLOC to SALES_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_ALLOC to SALES_80_EXTERNAL;
grant execute on LOBBY.SIHOT_ALLOC to SALES_95_MARKETING_TRAINING;

grant execute on LOBBY.SIHOT_ALLOC to XL_00_MASTER;
grant execute on LOBBY.SIHOT_ALLOC to XL_05_SYSADMIN;
grant execute on LOBBY.SIHOT_ALLOC to XL_06_DEVELOPER;
grant execute on LOBBY.SIHOT_ALLOC to XL_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_ALLOC to XL_20_RECEPCION;
grant execute on LOBBY.SIHOT_ALLOC to XL_30_HOUSEKEEPING;
grant execute on LOBBY.SIHOT_ALLOC to XL_30_MAINTENANCE;
grant execute on LOBBY.SIHOT_ALLOC to XL_40_MFEES;
grant execute on LOBBY.SIHOT_ALLOC to XL_50_MARKETING;
grant execute on LOBBY.SIHOT_ALLOC to XL_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_ALLOC to XL_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_ALLOC to XL_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_ALLOC to XL_80_EXTERNAL;
