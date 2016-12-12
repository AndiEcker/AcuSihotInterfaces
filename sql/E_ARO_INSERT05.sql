create or replace trigger LOBBY.ARO_INSERT
  AFTER INSERT
ON LOBBY.APT_RES_OCC REFERENCING OLD AS OLD NEW AS NEW
for each row
DECLARE
  lcChanges varchar2(2000) := null;
BEGIN

  if :NEW.ARO_CODE is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_CODE (' || :NEW.ARO_CODE || ')';
  end if;
  if :NEW.ARO_RHREF is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_RHREF (' || :NEW.ARO_RHREF || ')';
  end if;
  if :NEW.ARO_ROREF is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_ROREF (' || :NEW.ARO_ROREF || ')';
  end if;
  if :NEW.ARO_APREF is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_APREF (' || :NEW.ARO_APREF || ')';
  end if;
  if :NEW.ARO_CDREF is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_CDREF (' || :NEW.ARO_CDREF || ')';
  end if;
  if :NEW.ARO_AROREF_FROM is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_AROREF_FROM (' || :NEW.ARO_AROREF_FROM || ')';
  end if;
  if :NEW.ARO_AROREF_TO is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_AROREF_TO (' || :NEW.ARO_AROREF_TO || ')';
  end if;

  if :NEW.ARO_STATUS is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_STATUS (' || :NEW.ARO_STATUS || ')';
  end if;
  if :NEW.ARO_EXP_ARRIVE is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_EXP_ARRIVE (' || :NEW.ARO_EXP_ARRIVE || ')';
  end if;
  if :NEW.ARO_EXP_DEPART is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_EXP_DEPART (' || :NEW.ARO_EXP_DEPART || ')';
  end if;
  if :NEW.ARO_TIMEIN is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_TIMEIN (' || to_char(:NEW.ARO_TIMEIN,'DD MON YYYY  HH24:MI') || ')';
  end if;
  if :NEW.ARO_TIMEOUT is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_TIMEOUT (' || to_char(:NEW.ARO_TIMEOUT,'DD MON YYYY  HH24:MI') || ')';
  end if;
  if :NEW.ARO_RECD_KEY is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_RECD_KEY (' || to_char(:NEW.ARO_RECD_KEY,'DD MON YYYY  HH24:MI') || ')';
  end if;
  if :NEW.ARO_ADULTS is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_ADULTS (' || :NEW.ARO_ADULTS || ')';
  end if;
  if :NEW.ARO_CHILDREN is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_CHILDREN (' || :NEW.ARO_CHILDREN || ')';
  end if;
  if :NEW.ARO_BABIES is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_BABIES (' || :NEW.ARO_BABIES || ')';
  end if;
  if :NEW.ARO_WHOS_HERE_CLIENT is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_WHOS_HERE_CLIENT (' || :NEW.ARO_WHOS_HERE_CLIENT || ')';
  end if;
  if :NEW.ARO_CC_SWIPED is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_CC_SWIPED (' || :NEW.ARO_CC_SWIPED || ')';
  end if;
  if :NEW.ARO_PHONE is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_PHONE (' || :NEW.ARO_PHONE || ')';
  end if;
  if :NEW.ARO_PHONE_BALANCE is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_PHONE_BALANCE (' || :NEW.ARO_PHONE_BALANCE || ')';
  end if;
  if :NEW.ARO_MOVING_TO is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_MOVING_TO (' || :NEW.ARO_MOVING_TO || ')';
  end if;
  if :NEW.ARO_NOTE is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_NOTE (' || :NEW.ARO_NOTE || ')';
  end if;
  if :NEW.ARO_BOARDREF is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_BOARDREF (' || :NEW.ARO_BOARDREF || ')';
  end if;

  if :NEW.ARO_CBY is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_CBY (' || :NEW.ARO_CBY || ')';
  end if;
  if :NEW.ARO_CWHEN is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_CWHEN (' || to_char(:NEW.ARO_CWHEN,'DD MON YYYY  HH24:MI:SS') || ')';
  end if;
  if :NEW.ARO_MODBY is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_MODBY (' || :NEW.ARO_MODBY || ')';
  end if;
  if :NEW.ARO_MODWHEN is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_MODWHEN (' || to_char(:NEW.ARO_MODWHEN,'DD MON YYYY  HH24:MI:SS') || ')';
  end if;

  if :NEW.ARO_BOARD_ADULTS is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_BOARD_ADULTS (' || :NEW.ARO_BOARD_ADULTS || ')';
  end if;
  if :NEW.ARO_BOARD_CHILDREN is not null then
    lcChanges := lcChanges || chr(13) || 'ARO_BOARD_CHILDREN (' || :NEW.ARO_BOARD_CHILDREN || ')';
  end if;

  if lcChanges is not null then
    insert into T_AROL --LOBBY.APT_RES_OCC_LOG
      values(APT_RES_OCC_LOG_SEQ.nextval, USER, 'INSERT', SYSDATE, :NEW.ARO_CODE, substr(lcChanges, 2, 1999),
               case when k.ExecutingMainProc is not NULL then k.ExecutingMainProc when k.ProcedureStack is not NULL then substr(k.ProcedureStack, 1, 50)  else sys_context('USERENV', 'host') end,
               case when k.ExecutingSubProc is not NULL then k.ExecutingSubProc   when k.ProcedureStack is not NULL then substr(k.ProcedureStack, 51, 50) else sys_context('USERENV', 'os_user') end,
               case when k.ExecutingAction is not NULL then k.ExecutingAction     when k.ProcedureStack is not NULL then substr(k.ProcedureStack, 101,50) else sys_context('USERENV', 'sessionid') end);
    P_RUL_INSERT('UPDATE', lcChanges, :NEW.ARO_BOARDREF, NULL, :NEW.ARO_APREF, :NEW.ARO_RHREF, :NEW.ARO_EXP_ARRIVE, :NEW.ARO_EXP_DEPART);
  end if;
END
/*
    jm:23-05-10 removed redundant aro_flight cols logging
    ae:09-09-12 added ARO_BOARDREF.
    ae:18-09-13 added ARO_BABIES.
    ae:06-03-15 V04: added ARO_BOARD_ADULTS and ARO_BOARD_CHILDREN.
    ae:06-08-15 V05: added population of the new RUL_SIHOT* columns.
*/
;
/

