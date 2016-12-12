create or replace trigger LOBBY.RH_INSERT
  after insert
on LOBBY.RESERVATION_HEADER referencing OLD as OLD NEW as NEW
for each row
DECLARE
  lcChanges varchar2(2000) := null;
  --lcUser     varchar2(20) := null;
BEGIN
  --lcUser := APPLICATION_USER(:NEW.RH_CBY);
  if :NEW.RH_CODE is not null then
     lcChanges := lcChanges || chr(13) || 'RH_CODE (' || :NEW.RH_CODE || ')';
  end if;
  if :NEW.RH_OWREF is not null then
     lcChanges := lcChanges || chr(13) || 'RH_OWREF (' || :NEW.RH_OWREF || ')';
  end if;
  if :NEW.RH_EXT_BOOK_REF is not null then
     lcChanges := lcChanges || chr(13) || 'RH_EXT_BOOK_REF (' || :NEW.RH_EXT_BOOK_REF || ')';
  end if;
  if :NEW.RH_FROM_DATE is not null then
     lcChanges := lcChanges || chr(13) || 'RH_FROM_DATE (' || to_char(:NEW.RH_FROM_DATE, 'DD MON YYYY') || ')';
  end if;
  if :NEW.RH_TO_DATE is not null then
     lcChanges := lcChanges || chr(13) || 'RH_TO_DATE (' || to_char(:NEW.RH_TO_DATE, 'DD MON YYYY') || ')';
  end if;
  if :NEW.RH_DATE is not null then
     lcChanges := lcChanges || chr(13) || 'RH_DATE (' || :NEW.RH_DATE || ')';
  end if;
  if :NEW.RH_STATUS is not null then
     lcChanges := lcChanges || chr(13) || 'RH_STATUS (' || :NEW.RH_STATUS || ')';
  end if;
  if :NEW.RH_REQUNIT is not null then
     lcChanges := lcChanges || chr(13) || 'RH_REQUNIT (' || :NEW.RH_REQUNIT || ')';
  end if;
  if :NEW.RH_SOURCE is not null then
     lcChanges := lcChanges || chr(13) || 'RH_SOURCE (' || :NEW.RH_SOURCE || ')';
  end if;
  if :NEW.RH_CBY is not null then
     lcChanges := lcChanges || chr(13) || 'RH_CBY (' || :NEW.RH_CBY || ')';
  end if;
  if :NEW.RH_CWHEN is not null then
     lcChanges := lcChanges || chr(13) || 'RH_CWHEN (' || to_char(:NEW.RH_CWHEN,'DD MON YYYY  HH24:MI:SS') || ')';
  end if;
  if :NEW.RH_MODBY is not null then
     lcChanges := lcChanges || chr(13) || 'RH_MODBY (' || :NEW.RH_MODBY || ')';
  end if;
  if :NEW.RH_MODWHEN is not null then
     lcChanges := lcChanges || chr(13) || 'RH_MODWHEN (' || to_char(:NEW.RH_MODWHEN,'DD MON YYYY  HH24:MI:SS') || ')';
  end if;
  if :NEW.RH_ROREF is not null then
     lcChanges := lcChanges || chr(13) || 'RH_ROREF (' || :NEW.RH_ROREF || ')';
  end if;
  if :NEW.RH_GAPS is not null then
     lcChanges := lcChanges || chr(13) || 'RH_GAPS (' || :NEW.RH_GAPS || ')';
  end if;
  if :NEW.RH_EXT_BOOK_DATE is not null then
     lcChanges := lcChanges || chr(13) || 'RH_EXT_BOOK_DATE (' || to_char(:NEW.RH_EXT_BOOK_DATE, 'DD MON YYYY') || ')';
  end if;
  if lcChanges is not null then
     lcChanges := substr(lcChanges,2,1999);
     insert into T_RHL    -- LOBBY.RESERVATION_HEADER_LOG
       values(RESERVATION_HEADER_LOG_SEQ.nextval, USER, 'INSERT', SYSDATE, :NEW.RH_CODE, lcChanges, k.ExecutingMainProc, k.ExecutingSubProc, k.ExecutingAction);
  end if;
END;
/*
   ae:12-02-13  added RH_EXT_BOOK_REF (replacing unused RH_RTREF).
   ae:04-09-13  removed unused RH_NOADULTS/RH_NOCHILD columns.
   ae:09-10-16  V03: added RH_EXT_BOOK_DATE - for sihot migration project and removed time from from/to dates.
*/
/

