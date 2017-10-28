create or replace procedure LOBBY.SIHOT_ALLOC
                            (pcExtraInfo      IN OUT varchar2,                  -- IN: sihot xml request, OUT: ARO changes
                             pcAction         IN varchar2,                      -- CI=Check-in, CO=Check-out, RM=Room move/Transfer
                             pcApt            IN T_AP.AP_CODE%type,             -- new Acumen apartment number (for 3-digit PBC apartments without leading zero/0)
                             pcOldApt         IN T_AP.AP_CODE%type := NULL      -- old Acumen apartment number
                            ) 
IS
  lcCheckOutInfo    varchar2(2000) := '';
  lcCheckInInfo     varchar2(2000) := '';
BEGIN
  
  if pcAction in ('CO', 'RM') then
    select f_stragg(to_char(ARO_CODE) || ':' || ARO_APREF || '=' || to_char(ARO_STATUS) || '@' || to_char(ARO_EXP_ARRIVE, 'DD-MM-YY')) into lcCheckOutInfo from T_ARO
     where ARO_STATUS in (300, 330) and ARO_APREF = nvl(pcOldApt, pcApt) and trunc(sysdate) between ARO_EXP_DEPART - k.SihotRoomChangeMaxDaysDiff and ARO_EXP_DEPART;
    update T_ARO set ARO_TIMEOUT = sysdate,
                     ARO_STATUS = case when pcAction = 'RM' then 320 else 390 end
     where ARO_STATUS in (300, 330) and ARO_APREF = nvl(pcOldApt, pcApt) and trunc(sysdate) between ARO_EXP_DEPART - k.SihotRoomChangeMaxDaysDiff and ARO_EXP_DEPART;
  end if;        
  if pcAction in ('CI', 'RM') then
    select f_stragg(to_char(ARO_CODE) || ':' || ARO_APREF || '=' || to_char(ARO_STATUS) || '@' || to_char(ARO_EXP_ARRIVE, 'DD-MM-YY')) into lcCheckInInfo from T_ARO
     where ARO_STATUS in (150, 190, 200, 220) and ARO_APREF = pcApt and trunc(sysdate) between ARO_EXP_ARRIVE and ARO_EXP_ARRIVE + k.SihotRoomChangeMaxDaysDiff;
    update T_ARO set ARO_TIMEIN = sysdate, 
                     ARO_RECD_KEY = sysdate + 1 / (24 * 60),
                     ARO_STATUS = case when pcAction = 'RM' then 330 else 300 end
     where ARO_STATUS in (150, 190, 200, 220) and ARO_APREF = pcApt and trunc(sysdate) between ARO_EXP_ARRIVE and ARO_EXP_ARRIVE + k.SihotRoomChangeMaxDaysDiff;
  end if;
  pcExtraInfo := substr(case when lcCheckOutInfo is not NULL then 'CO' || lcCheckOutInfo end || case when lcCheckInInfo is not NULL then 'CI' || lcCheckInInfo end
                        || ' Req' || pcExtraInfo, 1, 1995);
END
/*
  ae:14-12-16 first beta - for SIHOT sync/migration project.
  ae:03-02-17 changed the valid check-in/-out date range from exp_arrive..depart to arrive..arrive+2 for checkin and depart-2..depart for checkouts - QD HOTFIX.
  ae:08-02-17 V02: added IN OUT parameter.
  ae:21-02-17 V03: added population of ARO_RECD_KEY for to not show blue dots in Acumen Lobby window (for Marian). 
  ae:15-03-17 V04: extended valid date range offset from 2 to 4 days - see WO #42288 from Esther.
  ae:03-05-17 V05: using k package constant for the maximum days of difference between expected and real arrival/departure (see also P_SIHOT_ALLOC()).
  ae:16-05-17 V06: added Sihot request to pcExtraInfo OUT value for to be added to the T_SRSL.SRSL_MESSAGE column for debugging.
  ae:24-10-17 V07: QuickAndDirtyFix: added status 150 and 190 to valid not-occupied apt statuses (found recently 53 of them all RCIs and the 150 ones only for 2017+ occupancy - STRANGE!!!).
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
