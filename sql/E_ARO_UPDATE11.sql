create or replace trigger LOBBY.ARO_UPDATE
  AFTER UPDATE
ON LOBBY.APT_RES_OCC REFERENCING OLD AS OLD NEW AS NEW
for each row
DECLARE
  lcChanges varchar2(2000) := null;
  lnWeek    T_TS.TS_WEEK%type;
  lcWKCode  T_WK.WK_CODE%type;
  
  cursor cTS is
    select TS_WEEK from T_TS
     where TS_WEEK_BEGIN <= :NEW.ARO_EXP_ARRIVE and TS_WEEK_END > :NEW.ARO_EXP_ARRIVE;
  
BEGIN
  open  cTS;
  fetch cTS into lnWeek;
  close cTS;
  lcWKCode := :NEW.ARO_APREF || '-' || lpad(lnWeek, 2, '0');
  
  if :NEW.ARO_CODE<>:OLD.ARO_CODE then
    lcChanges := lcChanges || chr(13) || 'ARO_CODE (' || :OLD.ARO_CODE || ' >> ' || :NEW.ARO_CODE || ')';
  end if;
  if :NEW.ARO_RHREF<>:OLD.ARO_RHREF then
    P_INSERT_LOG_ENTRY('UPDATE', 'APT_RES_OCC', 'ARO_RHREF', :NEW.ARO_CODE, :OLD.ARO_RHREF, :NEW.ARO_RHREF, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'ARO_RHREF (' || :OLD.ARO_RHREF || ' >> ' || :NEW.ARO_RHREF || ')';
  end if;
  if    ( :NEW.ARO_ROREF is null and :OLD.ARO_ROREF is not null )
     or ( :NEW.ARO_ROREF is not null and :OLD.ARO_ROREF is null )
     or :NEW.ARO_ROREF<>:OLD.ARO_ROREF then
    P_INSERT_LOG_ENTRY('UPDATE', 'APT_RES_OCC', 'ARO_ROREF', :NEW.ARO_CODE, :OLD.ARO_ROREF, :NEW.ARO_ROREF, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'ARO_ROREF (' || :OLD.ARO_ROREF || ' >> ' || :NEW.ARO_ROREF || ')';
    if :OLD.ARO_TIMEIN is not NULL then -- already checked in
      -- we may need to update the allocation record
      PK_ALLOC.APT_RO_CHANGE(:NEW.ARO_CODE, :NEW.ARO_APREF, :NEW.ARO_ROREF, :NEW.ARO_RHREF);
    elsif :OLD.ARO_ROREF in ('FB', 'FR', 'MO', 'MR') and :NEW.ARO_ROREF in ('KA', 'KD', 'KF', 'KN', 'KP', 'KU') then  -- hard-coded because Oracle doesn't allow sub-queries here: in (select CT_ROREF from T_CT) then
      -- added notification to reservation@signallia+Esther+Vanessa==MKT_TO_RES mail group if client changed from flybuy to keys - see WO #35105 
      P_SEND_EMAIL('MKT_TO_RES', 'Upgrade of flybuy client to Keys', 
                   'The resOcc type of the apartment reservation for client ' || :NEW.ARO_CDREF || ' in ' || :NEW.ARO_APREF || ' arriving on ' || :NEW.ARO_EXP_ARRIVE 
                   || ' got changed from ' || :OLD.ARO_ROREF || ' to ' || :NEW.ARO_ROREF || '. Please check if the apartment quality is ok for this Keys client and possibly move this reservation to a better apartment.');
    end if;
  end if;
  if    ( :NEW.ARO_APREF is null and :OLD.ARO_APREF is not null )
     or ( :NEW.ARO_APREF is not null and :OLD.ARO_APREF is null )
     or :NEW.ARO_APREF<>:OLD.ARO_APREF then
    P_INSERT_LOG_ENTRY('UPDATE', 'APT_RES_OCC', 'ARO_APREF', :NEW.ARO_CODE, :OLD.ARO_APREF, :NEW.ARO_APREF, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'ARO_APREF (' || :OLD.ARO_APREF || ' >> ' || :NEW.ARO_APREF || ')';
  end if;
  if    ( :NEW.ARO_CDREF is null and :OLD.ARO_CDREF is not null )
     or ( :NEW.ARO_CDREF is not null and :OLD.ARO_CDREF is null )
     or :NEW.ARO_CDREF<>:OLD.ARO_CDREF then
    lcChanges := lcChanges || chr(13) || 'ARO_CDREF (' || :OLD.ARO_CDREF || ' >> ' || :NEW.ARO_CDREF || ')';
  end if;
  if    ( :NEW.ARO_AROREF_FROM is null and :OLD.ARO_AROREF_FROM is not null )
     or ( :NEW.ARO_AROREF_FROM is not null and :OLD.ARO_AROREF_FROM is null )
     or :NEW.ARO_AROREF_FROM<>:OLD.ARO_AROREF_FROM then
    lcChanges := lcChanges || chr(13) || 'ARO_AROREF_FROM (' || :OLD.ARO_AROREF_FROM || ' >> ' || :NEW.ARO_AROREF_FROM || ')';
  end if;
  if    ( :NEW.ARO_AROREF_TO is null and :OLD.ARO_AROREF_TO is not null )
     or ( :NEW.ARO_AROREF_TO is not null and :OLD.ARO_AROREF_TO is null )
     or :NEW.ARO_AROREF_TO<>:OLD.ARO_AROREF_TO then
    lcChanges := lcChanges || chr(13) || 'ARO_AROREF_TO (' || :OLD.ARO_AROREF_TO || ' >> ' || :NEW.ARO_AROREF_TO || ')';
  end if;
  if    ( :NEW.ARO_STATUS is null and :OLD.ARO_STATUS is not null )
     or ( :NEW.ARO_STATUS is not null and :OLD.ARO_STATUS is null )
     or :NEW.ARO_STATUS<>:OLD.ARO_STATUS then
    P_INSERT_LOG_ENTRY('UPDATE', 'APT_RES_OCC', 'ARO_STATUS', :NEW.ARO_CODE, :OLD.ARO_STATUS, :NEW.ARO_STATUS, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'ARO_STATUS (' || :OLD.ARO_STATUS || ' >> ' || :NEW.ARO_STATUS || ')';
  end if;
  if    ( :NEW.ARO_EXP_ARRIVE is null and :OLD.ARO_EXP_ARRIVE is not null )
     or ( :NEW.ARO_EXP_ARRIVE is not null and :OLD.ARO_EXP_ARRIVE is null )
     or :NEW.ARO_EXP_ARRIVE<>:OLD.ARO_EXP_ARRIVE then
    P_INSERT_LOG_ENTRY('UPDATE', 'APT_RES_OCC', 'ARO_EXP_ARRIVE', :NEW.ARO_CODE, :OLD.ARO_EXP_ARRIVE, :NEW.ARO_EXP_ARRIVE, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'ARO_EXP_ARRIVE (' || :OLD.ARO_EXP_ARRIVE || ' >> ' || :NEW.ARO_EXP_ARRIVE || ')';
  end if;
  if    ( :NEW.ARO_EXP_DEPART is null and :OLD.ARO_EXP_DEPART is not null )
     or ( :NEW.ARO_EXP_DEPART is not null and :OLD.ARO_EXP_DEPART is null )
     or :NEW.ARO_EXP_DEPART<>:OLD.ARO_EXP_DEPART then
    P_INSERT_LOG_ENTRY('UPDATE', 'APT_RES_OCC', 'ARO_EXP_DEPART', :NEW.ARO_CODE, :OLD.ARO_EXP_DEPART, :NEW.ARO_EXP_DEPART, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'ARO_EXP_DEPART (' || :OLD.ARO_EXP_DEPART || ' >> ' || :NEW.ARO_EXP_DEPART || ')';
  end if;
  if    ( :NEW.ARO_TIMEIN is null and :OLD.ARO_TIMEIN is not null )
     or ( :NEW.ARO_TIMEIN is not null and :OLD.ARO_TIMEIN is null )
     or :NEW.ARO_TIMEIN<>:OLD.ARO_TIMEIN then
    P_INSERT_LOG_ENTRY('UPDATE', 'APT_RES_OCC', 'ARO_TIMEIN', :NEW.ARO_CODE, :OLD.ARO_TIMEIN, :NEW.ARO_TIMEIN, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'ARO_TIMEIN (' || to_char(:OLD.ARO_TIMEIN,'DD MON YYYY  HH24:MI') || ' >> ' || to_char(:NEW.ARO_TIMEIN,'DD MON YYYY  HH24:MI') || ')';
  end if;
  if    ( :NEW.ARO_TIMEOUT is null and :OLD.ARO_TIMEOUT is not null )
     or ( :NEW.ARO_TIMEOUT is not null and :OLD.ARO_TIMEOUT is null )
     or :NEW.ARO_TIMEOUT<>:OLD.ARO_TIMEOUT then
    P_INSERT_LOG_ENTRY('UPDATE', 'APT_RES_OCC', 'ARO_TIMEOUT', :NEW.ARO_CODE, :OLD.ARO_TIMEOUT, :NEW.ARO_TIMEOUT, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'ARO_TIMEOUT (' || to_char(:OLD.ARO_TIMEOUT,'DD MON YYYY  HH24:MI') || ' >> ' || to_char(:NEW.ARO_TIMEOUT,'DD MON YYYY  HH24:MI') || ')';
  end if;
  if    ( :NEW.ARO_RECD_KEY is null and :OLD.ARO_RECD_KEY is not null )
     or ( :NEW.ARO_RECD_KEY is not null and :OLD.ARO_RECD_KEY is null )
     or :NEW.ARO_RECD_KEY<>:OLD.ARO_RECD_KEY then
    lcChanges := lcChanges || chr(13) || 'ARO_RECD_KEY (' || to_char(:OLD.ARO_RECD_KEY,'DD MON YYYY  HH24:MI') || ' >> ' || to_char(:NEW.ARO_RECD_KEY,'DD MON YYYY  HH24:MI') || ')';
  end if;
  if    ( :NEW.ARO_ADULTS is null and :OLD.ARO_ADULTS is not null )
     or ( :NEW.ARO_ADULTS is not null and :OLD.ARO_ADULTS is null )
     or :NEW.ARO_ADULTS<>:OLD.ARO_ADULTS then
    lcChanges := lcChanges || chr(13) || 'ARO_ADULTS (' || :OLD.ARO_ADULTS || ' >> ' || :NEW.ARO_ADULTS || ')';
  end if;
  if    ( :NEW.ARO_CHILDREN is null and :OLD.ARO_CHILDREN is not null )
     or ( :NEW.ARO_CHILDREN is not null and :OLD.ARO_CHILDREN is null )
     or :NEW.ARO_CHILDREN<>:OLD.ARO_CHILDREN then
    lcChanges := lcChanges || chr(13) || 'ARO_CHILDREN (' || :OLD.ARO_CHILDREN || ' >> ' || :NEW.ARO_CHILDREN || ')';
  end if;
  if    ( :NEW.ARO_BABIES is null and :OLD.ARO_BABIES is not null )
     or ( :NEW.ARO_BABIES is not null and :OLD.ARO_BABIES is null )
     or :NEW.ARO_BABIES<>:OLD.ARO_BABIES then
    lcChanges := lcChanges || chr(13) || 'ARO_BABIES (' || :OLD.ARO_BABIES || ' >> ' || :NEW.ARO_BABIES || ')';
  end if;
  if    ( :NEW.ARO_WHOS_HERE_CLIENT is null and :OLD.ARO_WHOS_HERE_CLIENT is not null )
     or ( :NEW.ARO_WHOS_HERE_CLIENT is not null and :OLD.ARO_WHOS_HERE_CLIENT is null )
     or :NEW.ARO_WHOS_HERE_CLIENT<>:OLD.ARO_WHOS_HERE_CLIENT then
    lcChanges := lcChanges || chr(13) || 'ARO_WHOS_HERE_CLIENT (' || :OLD.ARO_WHOS_HERE_CLIENT || ' >> ' || :NEW.ARO_WHOS_HERE_CLIENT || ')';
  end if;
  if    ( :NEW.ARO_CC_SWIPED is null and :OLD.ARO_CC_SWIPED is not null )
     or ( :NEW.ARO_CC_SWIPED is not null and :OLD.ARO_CC_SWIPED is null )
     or :NEW.ARO_CC_SWIPED<>:OLD.ARO_CC_SWIPED then
    lcChanges := lcChanges || chr(13) || 'ARO_CC_SWIPED (' || :OLD.ARO_CC_SWIPED || ' >> ' || :NEW.ARO_CC_SWIPED || ')';
  end if;
  if    ( :NEW.ARO_PHONE is null and :OLD.ARO_PHONE is not null )
     or ( :NEW.ARO_PHONE is not null and :OLD.ARO_PHONE is null )
     or :NEW.ARO_PHONE<>:OLD.ARO_PHONE then
    lcChanges := lcChanges || chr(13) || 'ARO_PHONE (' || :OLD.ARO_PHONE || ' >> ' || :NEW.ARO_PHONE || ')';
  end if;
  if    ( :NEW.ARO_PHONE_BALANCE is null and :OLD.ARO_PHONE_BALANCE is not null )
     or ( :NEW.ARO_PHONE_BALANCE is not null and :OLD.ARO_PHONE_BALANCE is null )
     or :NEW.ARO_PHONE_BALANCE<>:OLD.ARO_PHONE_BALANCE then
    lcChanges := lcChanges || chr(13) || 'ARO_PHONE_BALANCE (' || :OLD.ARO_PHONE_BALANCE || ' >> ' || :NEW.ARO_PHONE_BALANCE || ')';
  end if;
  if    ( :NEW.ARO_MOVING_TO is null and :OLD.ARO_MOVING_TO is not null )
     or ( :NEW.ARO_MOVING_TO is not null and :OLD.ARO_MOVING_TO is null )
     or :NEW.ARO_MOVING_TO<>:OLD.ARO_MOVING_TO then
    P_INSERT_LOG_ENTRY('UPDATE', 'APT_RES_OCC', 'ARO_MOVING_TO', :NEW.ARO_CODE, :OLD.ARO_MOVING_TO, :NEW.ARO_MOVING_TO, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'ARO_MOVING_TO (' || :OLD.ARO_MOVING_TO || ' >> ' || :NEW.ARO_MOVING_TO || ')';
  end if;
  if    ( :NEW.ARO_NOTE is null and :OLD.ARO_NOTE is not null )
     or ( :NEW.ARO_NOTE is not null and :OLD.ARO_NOTE is null )
     or :NEW.ARO_NOTE<>:OLD.ARO_NOTE then
    lcChanges := lcChanges || chr(13) || 'ARO_NOTE (' || :OLD.ARO_NOTE || ' >> ' || :NEW.ARO_NOTE || ')';
  end if;
  if    ( :NEW.ARO_BOARDREF is null and :OLD.ARO_BOARDREF is not null )
     or ( :NEW.ARO_BOARDREF is not null and :OLD.ARO_BOARDREF is null )
     or :NEW.ARO_BOARDREF<>:OLD.ARO_BOARDREF then
    P_INSERT_LOG_ENTRY('UPDATE', 'APT_RES_OCC', 'ARO_BOARDREF', :NEW.ARO_CODE, :OLD.ARO_BOARDREF, :NEW.ARO_BOARDREF, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'ARO_BOARDREF (' || :OLD.ARO_BOARDREF || ' >> ' || :NEW.ARO_BOARDREF || ')';
  end if;

  if    ( :NEW.ARO_CBY is null and :OLD.ARO_CBY is not null )
     or ( :NEW.ARO_CBY is not null and :OLD.ARO_CBY is null )
     or :NEW.ARO_CBY<>:OLD.ARO_CBY then
    lcChanges := lcChanges || chr(13) || 'ARO_CBY (' || :OLD.ARO_CBY || ' >> ' || :NEW.ARO_CBY || ')';
  end if;
  if    ( :NEW.ARO_CWHEN is null and :OLD.ARO_CWHEN is not null )
     or ( :NEW.ARO_CWHEN is not null and :OLD.ARO_CWHEN is null )
     or :NEW.ARO_CWHEN<>:OLD.ARO_CWHEN then
    lcChanges := lcChanges || chr(13) || 'ARO_CWHEN (' || to_char(:OLD.ARO_CWHEN,'DD MON YYYY  HH24:MI:SS') || ' >> ' || to_char(:NEW.ARO_CWHEN,'DD MON YYYY  HH24:MI:SS') || ')';
  end if;
  
  if    ( :NEW.ARO_BOARD_ADULTS is null and :OLD.ARO_BOARD_ADULTS is not null )
     or ( :NEW.ARO_BOARD_ADULTS is not null and :OLD.ARO_BOARD_ADULTS is null )
     or :NEW.ARO_BOARD_ADULTS<>:OLD.ARO_BOARD_ADULTS then
    lcChanges := lcChanges || chr(13) || 'ARO_BOARD_ADULTS (' || :OLD.ARO_BOARD_ADULTS || ' >> ' || :NEW.ARO_BOARD_ADULTS || ')';
  end if;
  if    ( :NEW.ARO_BOARD_CHILDREN is null and :OLD.ARO_BOARD_CHILDREN is not null )
     or ( :NEW.ARO_BOARD_CHILDREN is not null and :OLD.ARO_BOARD_CHILDREN is null )
     or :NEW.ARO_BOARD_CHILDREN<>:OLD.ARO_BOARD_CHILDREN then
    lcChanges := lcChanges || chr(13) || 'ARO_BOARD_CHILDREN (' || :OLD.ARO_BOARD_CHILDREN || ' >> ' || :NEW.ARO_BOARD_CHILDREN || ')';
  end if;

  if lcChanges is not null then
    insert into T_AROL --LOBBY.APT_RES_OCC_LOG
      values(APT_RES_OCC_LOG_SEQ.nextval, USER, 'UPDATE', SYSDATE, :NEW.ARO_CODE, substr(lcChanges, 2, 1999), k.ExecutingMainProc, k.ExecutingSubProc, k.ExecutingAction);
    -- don't sync check-ins, transfers nor check-outs (mostly done within Sihot and changed in T_ARO by AcuServer - see AcuServer.py/alloc_trigger())
    if not (:OLD.ARO_STATUS >= 300 or :NEW.ARO_STATUS >= 300) then
      -- deallocate apt on request linking (P_RESL_APT_LINK()), shrinked date range or room deallocation
      if :OLD.ARO_RHREF <> :NEW.ARO_RHREF 
      or :OLD.ARO_EXP_ARRIVE < :NEW.ARO_EXP_ARRIVE or :OLD.ARO_EXP_DEPART > :NEW.ARO_EXP_DEPART
      or :NEW.ARO_STATUS = 120 and :OLD.ARO_STATUS <> 120 then
        P_RH_RUL_INSERT('A', 'DELETE', lcChanges, :OLD.ARO_BOARDREF, NULL, :OLD.ARO_APREF, :OLD.ARO_RHREF, :OLD.ARO_EXP_ARRIVE, :OLD.ARO_EXP_DEPART);
      end if;
      if not (:NEW.ARO_STATUS = 120 and :OLD.ARO_STATUS <> 120) then
        P_RH_RUL_INSERT('A', 'UPDATE', lcChanges, :NEW.ARO_BOARDREF, NULL, :NEW.ARO_APREF, :NEW.ARO_RHREF, :NEW.ARO_EXP_ARRIVE, :NEW.ARO_EXP_DEPART);
      end if;
    end if;
  end if;
END
/*
  ae:10-01-08 changed to use PK_ALLOC on ARO_ROREF change after apt. checkin.
  jm:23-05-10 removed redundant aro_flight cols logging
  ae:09-09-12 added ARO_BOARDREF.
  ae:18-09-13 added ARO_BABIES.
  ae:12-06-14 added log entries for T_LOG.
  ae:06-03-15 added ARO_BOARD_ADULTS and ARO_BOARD_CHILDREN.
  ae:19-07-16 V08: added notification on change of resOcc type from flybuy to keys.
  ae:06-08-15 V09: added population of the new RUL_SIHOT* columns and unsync-block on apt. check-in.
  ae:21-02-17 V10: changed to call newly added P_RH_RUL_INSERT() instead of P_RUL_INSERT() and added pcCaller parameter to call of P_RUL_INSERT().
  ae:14-09-17 V11: added if statement to prevent call of P_RH_RUL_INSERT() on ARO cancellation.
*/;
/
