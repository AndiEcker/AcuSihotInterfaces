create or replace procedure LOBBY.RUL_INSERT
                            (pcCaller         IN varchar2,
                             pcAction         IN T_RUL.RUL_ACTION%type,
                             pcChanges        IN T_RUL.RUL_CHANGES%type,        -- with leading chr(13) seperator
                             pcBoardRef       IN T_LU.LU_ID%type,
                             pnCode           IN T_RU.RU_CODE%type := NULL,     -- RU_CODE if called from RU trigger or PRC_CODE if called from PRC trigger
                             pcApRef          IN T_ARO.ARO_APREF%type := NULL,  -- only passed from T_ARO triggers (ARO overload)
                             pnRHRef          IN T_RU.RU_RHREF%type := NULL,
                             pdFrom           IN date := NULL,
                             pdTo             IN date := NULL,
                             pcAtGeneric      IN T_RU.RU_ATGENERIC%type := NULL,
                             pcResort         IN T_RU.RU_RESORT%type := NULL,
                             pnObjId          IN T_RUL.RUL_SIHOT_OBJID%type := NULL,
                             pcRate           IN T_RUL.RUL_SIHOT_RATE%type := NULL,
                             pnAFT_Code       IN T_RAF.RAF_AFTREF%type := NULL
                            ) 
IS
  CHANGES_LEN   constant integer := 2000;
  PROC_LEN      constant integer := 50;
  
  lcSihotCat    T_RUL.RUL_SIHOT_CAT%type;
  lnSihotHotel  T_RUL.RUL_SIHOT_HOTEL%type;
  lcApRef       T_ARO.ARO_APREF%type;
  lcRulApRef    T_RUL.RUL_SIHOT_ROOM%type;
  lcAtGeneric   T_RU.RU_ATGENERIC%type;
  lcResort      T_RU.RU_RESORT%type;
  lnRU_Code     T_RU.RU_CODE%type;
  lnRUL_Code    T_RUL.RUL_CODE%type;
  lcBoardRef    T_LU.LU_ID%type;
  lcSihotPack   varchar2(3 byte);
  lcPackPrefix  varchar2(12 byte) := '';
  lnPos         integer;
  lcAction      T_RUL.RUL_ACTION%type;
  lcAFT_Suffix  varchar2(12 byte);
  
  cursor cMkt is
    select ML_RHREF, ML_REQARRIVAL_DATE, ML_REQDEPART_DATE, RU_CODE from T_MS, T_ML, T_RU where MS_MLREF = ML_CODE and ML_CODE = RU_MLREF and MS_PRCREF = pnCode;
  rMkt cMkt%rowtype;
  
  cursor cRU is
    select RU_ATGENERIC, RU_RESORT from T_RU where RU_CODE = lnRU_Code;
  
  cursor cRUL is
    select max(RUL_CODE) from V_ACU_RES_LOG where RUL_PRIMARY = lnRU_Code and length(pcChanges) + length(RUL_CHANGES) <= CHANGES_LEN;
  
  cursor cLog is
    select RUL_SIHOT_ROOM from V_ACU_RES_LOG where RUL_PRIMARY = lnRU_Code;
    
BEGIN
  lcAction := pcAction;
  -- determine caller and if either lcApRef or lcAtGeneric/lcResort need to be fetched
  if pcCaller = 'R' then         -- called from T_RU or R_RH-update triggers
    lnRU_Code := pnCode;
    lcApRef := F_RH_ARO_APT(pnRHRef, pdFrom, pdTo);
    if lcApRef is NULL then
      lcAtGeneric := pcAtGeneric;
      lcResort := pcResort;
    end if;
  elsif pcCaller = 'A' then   -- called from T_ARO triggers
    lnRU_Code := pnCode;    -- F_ARO_RU_CODE(pnRHRef, pdFrom, pdTo) incorrect for multiple RUs per ARO (now determined correctly by P_RH_RUL_INSERT() and passed into pnCode)
    if pcAction = 'DELETE' then   -- .. with DELETE action or cancellation (ARO_STATUS => 120): wipe RUL_SIHOT_ROOM column
      open  cRU;
      fetch cRU into lcAtGeneric, lcResort;
      close cRU;
      lcAction := 'UPDATE';
    else                          -- .. for all other actions: populate RUL_SIHOT_ROOM with lcApRef and RUL_SIHOT_CAT/_HOTEL with ARO overloads
      lcApRef := pcApRef;
    end if;
  else                            -- called from T_PRC update trigger (only board updates)
    open  cMkt;
    fetch cMkt into rMkt;
    close cMkt;
    lnRU_Code := rMkt.RU_CODE;
    if pcApRef is NULL then
      open  cRU;
      fetch cRU into lcAtGeneric, lcResort;
      close cRU;
    else
      lcApRef := pcApRef;
    end if;
  end if;

  -- translate lcAtGeneric/lcResort or lcApRef overload into SIHOT values
  if lcApRef is not NULL then
    lcSihotCat := F_SIHOT_CAT(lcApRef);
    lnSihotHotel := F_SIHOT_HOTEL(lcApRef);
  else
    --select RUL_SIHOT_ROOM into lcRulApRef from V_ACU_RES_LOG where RUL_PRIMARY = lnRU_Code;
    open  cLog;
    fetch cLog into lcRulApRef;
    close cLog;
    if lcResort = 'ANY' and lcRulApRef is not NULL then
      lcResort := F_RESORT(lcRulApRef);
    end if;
    if pnAFT_Code is NULL then
      lcAFT_Suffix := F_SIHOT_PAID_RAF(lnRU_Code, lcResort, lcAtGeneric);
    else
      lcAFT_Suffix := '_' || to_char(pnAFT_Code);
    end if;
    lcSihotCat := F_SIHOT_CAT(lcAtGeneric || '@' || lcResort || lcAFT_Suffix);
    lnSihotHotel := F_SIHOT_HOTEL('@' || lcResort);
  end if;
  
  -- translate board ref into SIHOT package value - last trigger is always overwriting
  lcBoardRef := pcBoardRef;
  if nvl(lcBoardRef, 'N') = 'N' then   -- called from RU/RH/PRC and apartment exists - check for ARO board overload
    if pcCaller = 'M' then
      lcBoardRef := F_RU_ARO_BOARD(rMkt.ML_RHREF, rMkt.ML_REQARRIVAL_DATE, rMkt.ML_REQDEPART_DATE, pcCaller);
    else
      lcBoardRef := F_RU_ARO_BOARD(pnRHRef, pdFrom, pdTo, pcCaller);
    end if;
  end if;
  lnPos := instr(lcBoardRef, '_'); 
  if lnPos >= 2 then  -- >=2 for to not confuse with BOARDREF='_'
    lcPackPrefix := substr(lcBoardRef, 1, lnPos);
    lcBoardRef := substr(lcBoardRef, lnPos + 1);
  elsif pcCaller = 'M' then
    lcPackPrefix := 'MKT_';   -- actually not needed because PRC_UPDATE is always adding this prefix
  end if;
  lcSihotPack := F_SIHOT_PACK(lcBoardRef, lcPackPrefix);
  
  -- insert log entry or on T_ARO trigger call try first to update SIHOT columns of unsynced RUL record either with ARO/PRC overloads or current RU values
  if pcCaller != 'R' then
    -- for better receycling use V_ACU_RES_LOG not _UNSYNCED: select RUL_CODE into lnRUL_Code from V_ACU_RES_UNSYNCED where RU_CODE = lnRU_Code;
    open  cRUL;
    fetch cRUL into lnRUL_Code;
    close cRUL;
  end if;
  if lnRUL_Code is not NULL then
    update T_RUL set RUL_USER = USER,
                     RUL_ACTION = lcAction,
                     RUL_DATE = sysdate,     -- reset ARL_DATE value for to be synchronized  
                     RUL_CHANGES = substr(pcChanges || chr(13) || RUL_CHANGES, 2, CHANGES_LEN),
                     RUL_MAINPROC = substr(k.ExecutingMainProc || pcCaller || RUL_MAINPROC, 1, PROC_LEN), 
                     RUL_SUBPROC = substr(k.ExecutingSubProc || pcCaller || RUL_SUBPROC, 1, PROC_LEN), 
                     RUL_SPACTION = substr(k.ExecutingAction || pcCaller || RUL_SPACTION, 1, PROC_LEN), 
                     RUL_SIHOT_CAT = lcSihotCat, 
                     RUL_SIHOT_HOTEL = lnSihotHotel, 
                     RUL_SIHOT_PACK = lcSihotPack,
                     RUL_SIHOT_ROOM = lcApRef,
                     RUL_SIHOT_OBJID = case when pnObjId is not NULL then pnObjId else RUL_SIHOT_OBJID end,
                     RUL_SIHOT_RATE = case when pcRate is not NULL then pcRate else RUL_SIHOT_RATE end
     where RUL_CODE = lnRUL_Code;
  elsif lnRU_Code is not NULL then
    insert into T_RUL (RUL_CODE, RUL_USER, RUL_ACTION, RUL_DATE, RUL_PRIMARY, 
                       RUL_CHANGES, RUL_MAINPROC, RUL_SUBPROC, RUL_SPACTION, 
                       RUL_SIHOT_CAT, RUL_SIHOT_HOTEL, RUL_SIHOT_PACK, 
                       RUL_SIHOT_ROOM, RUL_SIHOT_OBJID, RUL_SIHOT_RATE)
      values(S_REQUESTED_UNIT_LOG_SEQ.nextval, USER, lcAction, SYSDATE, lnRU_Code, 
             substr(pcChanges, 2, CHANGES_LEN), k.ExecutingMainProc, k.ExecutingSubProc, k.ExecutingAction,
             lcSihotCat, lnSihotHotel, lcSihotPack, 
             lcApRef, pnObjId, pcRate);
  else
    P_SENDMAIL('Sales.System@silverpoint.com', 'Andreas.Ecker@signallia.com', 'Insert NULL into RUL_PRIMARY',
               'Caller=' || pcCaller || ' Usr=' || USER || ' Act=' || lcAction || case when pcAction <> lcAction then '(' || pcAction || ')' end || ' Date=' || sysdate 
               || ' Changes=[' || substr(pcChanges, 2) || '] ProcStack=[' || trim(k.ExecutingMainProc) || '/' || trim(k.ExecutingSubProc) || '/' || trim(k.ExecutingAction) || '] Code=' || pnCode
               || ' Cat=' || lcSihotCat || ' AftSuff=' || lcAFT_Suffix || ' Hot=' || lnSihotHotel
               || ' Pack=' || lcSihotPack || case when lcPackPrefix is not NULL then ':' || lcPackPrefix end || ' Board=' || lcBoardRef 
               || ' Apt=' || lcApRef || case when pcApRef <> nvl(lcApRef, '_') then '(' || pcApRef || ')' end || case when lcRulApRef <> nvl(lcApRef, '_') then '(Rul:' || lcRulApRef || ')' end 
               || ' RS=' || lcResort || case when pcResort <> lcResort then '(' || pcResort || ')' end
               || ' Gen=' || lcAtGeneric || case when pcAtGeneric <> lcAtGeneric then '(' || pcAtGeneric || ')' end 
               || ' Rh=' || pnRHRef || case when rMkt.ML_RHREF <> pnRHRef then '(' || rMkt.ML_RHREF || ')' end
               || ' Arr=' || pdFrom || case when rMkt.ML_REQARRIVAL_DATE <> pdFrom then '(' || rMkt.ML_REQARRIVAL_DATE || ')' end
               || ' Dep=' || pdTo || case when rMkt.ML_REQDEPART_DATE <> pdTo then '(' || rMkt.ML_REQDEPART_DATE || ')' end 
               || ' ObjId=' || pnObjId || ' Rate=' || pcRate || ' Aft=' || pnAFT_Code);
  end if;
END
/*
  ae:06-08-16 first beta - for SIHOT sync/migration project.
  ae:28-11-16 V01: refactored call to F_SIHOT_CAT for to support one paid requested apartment feature.
  ae:27-12-16 V02: added lcCaller parameter to call of F_RU_ARO_BOARD to prevent mutating PRC cursor.
  ae:11-01-17 V03: prevent INSERT into RUL if RUL_PRIMARY value is NULL and added temporary notification for further checkings. 
  ae:21-02-17 V04: changed to detect T_ARO call by pnCode is NULL (instead of pcApRef is not NULL) because now P_RH_RUL_INSERT() is passing always the current associated apartment and added pcCaller parameter (replacing lcCaller). 
*/;
/


create or replace public synonym P_RUL_INSERT for LOBBY.RUL_INSERT;


grant execute on LOBBY.RUL_INSERT to SALES_00_MASTER;
grant execute on LOBBY.RUL_INSERT to SALES_05_SYSADMIN;
grant execute on LOBBY.RUL_INSERT to SALES_06_DEVELOPER;
grant execute on LOBBY.RUL_INSERT to SALES_10_SUPERVISOR;
grant execute on LOBBY.RUL_INSERT to SALES_11_SUPERASSIST;
grant execute on LOBBY.RUL_INSERT to SALES_15_CENTRAL;
grant execute on LOBBY.RUL_INSERT to SALES_20_CONTRACTS;
grant execute on LOBBY.RUL_INSERT to SALES_30_RESALES;
grant execute on LOBBY.RUL_INSERT to SALES_40_COMPLETIONS;
grant execute on LOBBY.RUL_INSERT to SALES_47_KEYS;
grant execute on LOBBY.RUL_INSERT to SALES_49_MKTSUPER;
grant execute on LOBBY.RUL_INSERT to SALES_50_MARKETING;
grant execute on LOBBY.RUL_INSERT to SALES_51_TMSUPER;
grant execute on LOBBY.RUL_INSERT to SALES_52_TELEMARKETING;
grant execute on LOBBY.RUL_INSERT to SALES_55_MANAGEMENT;
grant execute on LOBBY.RUL_INSERT to SALES_56_TOS;
grant execute on LOBBY.RUL_INSERT to SALES_58_RECEPTION;
grant execute on LOBBY.RUL_INSERT to SALES_60_RESERVATIONS;
grant execute on LOBBY.RUL_INSERT to SALES_70_ACCOUNTING;
grant execute on LOBBY.RUL_INSERT to SALES_80_EXTERNAL;
grant execute on LOBBY.RUL_INSERT to SALES_95_MARKETING_TRAINING;

grant execute on LOBBY.RUL_INSERT to XL_00_MASTER;
grant execute on LOBBY.RUL_INSERT to XL_05_SYSADMIN;
grant execute on LOBBY.RUL_INSERT to XL_06_DEVELOPER;
grant execute on LOBBY.RUL_INSERT to XL_10_SUPERVISOR;
grant execute on LOBBY.RUL_INSERT to XL_20_RECEPCION;
grant execute on LOBBY.RUL_INSERT to XL_30_HOUSEKEEPING;
grant execute on LOBBY.RUL_INSERT to XL_30_MAINTENANCE;
grant execute on LOBBY.RUL_INSERT to XL_40_MFEES;
grant execute on LOBBY.RUL_INSERT to XL_50_MARKETING;
grant execute on LOBBY.RUL_INSERT to XL_55_MANAGEMENT;
grant execute on LOBBY.RUL_INSERT to XL_60_RESERVATIONS;
grant execute on LOBBY.RUL_INSERT to XL_70_ACCOUNTING;
grant execute on LOBBY.RUL_INSERT to XL_80_EXTERNAL;
