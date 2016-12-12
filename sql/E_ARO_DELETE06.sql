create or replace trigger LOBBY.ARO_DELETE
  BEFORE DELETE
ON LOBBY.APT_RES_OCC REFERENCING OLD AS OLD NEW AS NEW
for each row
DECLARE
  lcChanges varchar2(2000) := null;
BEGIN

  if :OLD.ARO_CODE is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_CODE (' || :OLD.ARO_CODE || ')';
  end if;
  if :OLD.ARO_RHREF is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_RHREF (' || :OLD.ARO_RHREF || ')';
  end if;
  if :OLD.ARO_ROREF is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_ROREF (' || :OLD.ARO_ROREF || ')';
  end if;
  if :OLD.ARO_APREF is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_APREF (' || :OLD.ARO_APREF || ')';
  end if;
  if :OLD.ARO_CDREF is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_CDREF (' || :OLD.ARO_CDREF || ')';
  end if;
  if :OLD.ARO_AROREF_FROM is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_AROREF_FROM (' || :OLD.ARO_AROREF_FROM || ')';
  end if;
  if :OLD.ARO_AROREF_TO is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_AROREF_TO (' || :OLD.ARO_AROREF_TO || ')';
  end if;

  if :OLD.ARO_STATUS is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_STATUS (' || :OLD.ARO_STATUS || ')';
  end if;
  if :OLD.ARO_EXP_ARRIVE is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_EXP_ARRIVE (' || :OLD.ARO_EXP_ARRIVE || ')';
  end if;
  if :OLD.ARO_EXP_DEPART is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_EXP_DEPART (' || :OLD.ARO_EXP_DEPART || ')';
  end if;
  if :OLD.ARO_TIMEIN is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_TIMEIN (' || to_char(:OLD.ARO_TIMEIN,'DD MON YYYY  HH24:MI') || ')';
  end if;
  if :OLD.ARO_TIMEOUT is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_TIMEOUT (' || to_char(:OLD.ARO_TIMEOUT,'DD MON YYYY  HH24:MI') || ')';
  end if;
  if :OLD.ARO_RECD_KEY is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_RECD_KEY (' || to_char(:OLD.ARO_RECD_KEY,'DD MON YYYY  HH24:MI') || ')';
  end if;
  if :OLD.ARO_ADULTS is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_ADULTS (' || :OLD.ARO_ADULTS || ')';
  end if;
  if :OLD.ARO_CHILDREN is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_CHILDREN (' || :OLD.ARO_CHILDREN || ')';
  end if;
  if :OLD.ARO_BABIES is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_BABIES (' || :OLD.ARO_BABIES || ')';
  end if;
  if :OLD.ARO_WHOS_HERE_CLIENT is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_WHOS_HERE_CLIENT (' || :OLD.ARO_WHOS_HERE_CLIENT || ')';
  end if;
  if :OLD.ARO_CC_SWIPED is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_CC_SWIPED (' || :OLD.ARO_CC_SWIPED || ')';
  end if;
  if :OLD.ARO_PHONE is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_PHONE (' || :OLD.ARO_PHONE || ')';
  end if;
  if :OLD.ARO_PHONE_BALANCE is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_PHONE_BALANCE (' || :OLD.ARO_PHONE_BALANCE || ')';
  end if;
  if :OLD.ARO_MOVING_TO is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_MOVING_TO (' || :OLD.ARO_MOVING_TO || ')';
  end if;
  if :OLD.ARO_NOTE is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_NOTE (' || :OLD.ARO_NOTE || ')';
  end if;
  if :OLD.ARO_BOARDREF is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_BOARDREF (' || :OLD.ARO_BOARDREF || ')';
  end if;

  if :OLD.ARO_CBY is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_CBY (' || :OLD.ARO_CBY || ')';
  end if;
  if :OLD.ARO_CWHEN is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_CWHEN (' || to_char(:OLD.ARO_CWHEN,'DD MON YYYY  HH24:MI:SS') || ')';
  end if;
  if :OLD.ARO_MODBY is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_MODBY (' || :OLD.ARO_MODBY || ')';
  end if;
  if :OLD.ARO_MODWHEN is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_MODWHEN (' || to_char(:OLD.ARO_MODWHEN,'DD MON YYYY  HH24:MI:SS') || ')';
  end if;
  
  if :OLD.ARO_BOARD_ADULTS is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_BOARD_ADULTS (' || :OLD.ARO_BOARD_ADULTS || ')';
  end if;
  if :OLD.ARO_BOARD_CHILDREN is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_BOARD_CHILDREN (' || :OLD.ARO_BOARD_CHILDREN || ')';
  end if;

  if lcChanges is not null then
    insert into T_AROL --LOBBY.APT_RES_OCC_LOG
      values(APT_RES_OCC_LOG_SEQ.nextval, USER, 'DELETE', SYSDATE, :OLD.ARO_CODE, substr(lcChanges, 2, 1999), k.ExecutingMainProc, k.ExecutingSubProc, k.ExecutingAction);
    P_RUL_INSERT('DELETE', lcChanges, :OLD.ARO_BOARDREF, NULL, :OLD.ARO_APREF, :OLD.ARO_RHREF, :OLD.ARO_EXP_ARRIVE, :OLD.ARO_EXP_DEPART);
  end if;
END
/*
    jm:23-05-10 removed redundant aro_flight cols logging
    ae:09-09-12 added ARO_BOARDREF.
    ae:18-09-13 added ARO_BABIES.
    ae:06-03-15 V05: added ARO_BOARD_ADULTS and ARO_BOARD_CHILDREN.
    ae:06-08-16 V06: added population of the new RUL_SIHOT* columns.
*/
;
/

