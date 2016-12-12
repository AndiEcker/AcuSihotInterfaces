create or replace trigger LOBBY.RH_UPDATE
  after update
on LOBBY.RESERVATION_HEADER referencing old as OLD new as NEW
for each row
DECLARE
  lcChanges   varchar2(2000) := null;
  lcRUChanges varchar2(2000) := null;
  lcWKCode    T_WK.WK_CODE%type;
  
  cursor cCUA_CR is
    select least(c.CUA_WKREF) from T_RU, T_CUA d, T_CUA c
     where RU_RHREF = :NEW.RH_CODE and RU_FROM_DATE = :OLD.RH_FROM_DATE and RU_STATUS <> 120
       and d.CUA_CODE = RU_UAREF and d.CUA_TRANS_GROUP = c.CUA_TRANS_GROUP;
  
  cursor cRU is
    select RU_CODE, RU_RHREF, RU_FROM_DATE, RU_DAYS, RU_BOARDREF, RU_ATGENERIC, RU_RESORT, RU_SIHOT_OBJID
         , RO_SIHOT_RATE
      from T_RU, T_RO
     where RU_ROREF = RO_CODE and RU_RHREF = :NEW.RH_CODE;
   
BEGIN
  open  cCUA_CR;
  fetch cCUA_CR into lcWKCode;
  close cCUA_CR;
  
  if :NEW.RH_CODE <> :OLD.RH_CODE then
     lcChanges := lcChanges || chr(13) || 'RH_CODE (' || :OLD.RH_CODE || ' >> ' || :NEW.RH_CODE || ')';
  end if;
  if    ( :NEW.RH_OWREF is null and :OLD.RH_OWREF is not null )
     or ( :NEW.RH_OWREF is not null and :OLD.RH_OWREF is null )
     or :NEW.RH_OWREF <> :OLD.RH_OWREF then
    P_INSERT_LOG_ENTRY('UPDATE', 'RESERVATION_HEADER', 'RH_OWREF', :NEW.RH_CODE, :OLD.RH_OWREF, :NEW.RH_OWREF, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RH_OWREF (' || :OLD.RH_OWREF || ' >> ' || :NEW.RH_OWREF || ')';
    lcRUChanges := lcRUChanges || chr(13) || 'RH_OWREF (' || :OLD.RH_OWREF || ' >> ' || :NEW.RH_OWREF || ')';
  end if;
  if    ( :NEW.RH_EXT_BOOK_REF is null and :OLD.RH_EXT_BOOK_REF is not null )
     or ( :NEW.RH_EXT_BOOK_REF is not null and :OLD.RH_EXT_BOOK_REF is null )
     or :NEW.RH_EXT_BOOK_REF <> :OLD.RH_EXT_BOOK_REF then
    lcChanges := lcChanges || chr(13) || 'RH_EXT_BOOK_REF (' || :OLD.RH_EXT_BOOK_REF || ' >> ' || :NEW.RH_EXT_BOOK_REF || ')';
    lcRUChanges := lcRUChanges || chr(13) || 'RH_EXT_BOOK_REF (' || :OLD.RH_EXT_BOOK_REF || ' >> ' || :NEW.RH_EXT_BOOK_REF || ')';
  end if;
  if    ( :NEW.RH_FROM_DATE is null and :OLD.RH_FROM_DATE is not null )
     or ( :NEW.RH_FROM_DATE is not null and :OLD.RH_FROM_DATE is null )
     or :NEW.RH_FROM_DATE <> :OLD.RH_FROM_DATE then
    P_INSERT_LOG_ENTRY('UPDATE', 'RESERVATION_HEADER', 'RH_FROM_DATE', :NEW.RH_CODE, :OLD.RH_FROM_DATE, :NEW.RH_FROM_DATE, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RH_FROM_DATE (' || :OLD.RH_FROM_DATE || ' >> ' || :NEW.RH_FROM_DATE || ')';
  end if;
  if    ( :NEW.RH_TO_DATE is null and :OLD.RH_TO_DATE is not null )
     or ( :NEW.RH_TO_DATE is not null and :OLD.RH_TO_DATE is null )
     or :NEW.RH_TO_DATE <> :OLD.RH_TO_DATE then
    P_INSERT_LOG_ENTRY('UPDATE', 'RESERVATION_HEADER', 'RH_TO_DATE', :NEW.RH_CODE, :OLD.RH_TO_DATE, :NEW.RH_TO_DATE, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RH_TO_DATE (' || :OLD.RH_TO_DATE || ' >> ' || :NEW.RH_TO_DATE || ')';
  end if;
  if    ( :NEW.RH_DATE is null and :OLD.RH_DATE is not null )
     or ( :NEW.RH_DATE is not null and :OLD.RH_DATE is null )
     or :NEW.RH_DATE <> :OLD.RH_DATE then
    lcChanges := lcChanges || chr(13) || 'RH_DATE (' || :OLD.RH_DATE || ' >> ' || :NEW.RH_DATE || ')';
  end if;
  if    ( :NEW.RH_STATUS is null and :OLD.RH_STATUS is not null )
     or ( :NEW.RH_STATUS is not null and :OLD.RH_STATUS is null )
     or :NEW.RH_STATUS <> :OLD.RH_STATUS then
    P_INSERT_LOG_ENTRY('UPDATE', 'RESERVATION_HEADER', 'RH_STATUS', :NEW.RH_CODE, :OLD.RH_STATUS, :NEW.RH_STATUS, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RH_STATUS (' || :OLD.RH_STATUS || '  >> ' || :NEW.RH_STATUS || ')';
  end if;
  if    ( :NEW.RH_REQUNIT is null and :OLD.RH_REQUNIT is not null )
     or ( :NEW.RH_REQUNIT is not null and :OLD.RH_REQUNIT is null )
     or :NEW.RH_REQUNIT <> :OLD.RH_REQUNIT then
    lcChanges := lcChanges || chr(13) || 'RH_REQUNIT (' || :OLD.RH_REQUNIT || ' >> ' || :NEW.RH_REQUNIT || ')';
    lcRUChanges := lcRUChanges || chr(13) || 'RH_REQUNIT (' || :OLD.RH_REQUNIT || ' >> ' || :NEW.RH_REQUNIT || ')';
  end if;
  if    ( :NEW.RH_SOURCE is null and :OLD.RH_SOURCE is not null )
     or ( :NEW.RH_SOURCE is not null and :OLD.RH_SOURCE is null )
     or :NEW.RH_SOURCE <> :OLD.RH_SOURCE then
    P_INSERT_LOG_ENTRY('UPDATE', 'RESERVATION_HEADER', 'RH_SOURCE', :NEW.RH_CODE, :OLD.RH_SOURCE, :NEW.RH_SOURCE, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RH_SOURCE (' || :OLD.RH_SOURCE || ' >> ' || :NEW.RH_SOURCE || ')';
  end if;
  if    ( :NEW.RH_CBY is null and :OLD.RH_CBY is not null )
     or ( :NEW.RH_CBY is not null and :OLD.RH_CBY is null )
     or :NEW.RH_CBY <> :OLD.RH_CBY then
    lcChanges := lcChanges || chr(13) || 'RH_CBY (' || :OLD.RH_CBY || ' >> ' || :NEW.RH_CBY || ')';
  end if;
  if    ( :NEW.RH_CWHEN is null and :OLD.RH_CWHEN is not null )
     or ( :NEW.RH_CWHEN is not null and :OLD.RH_CWHEN is null )
     or :NEW.RH_CWHEN <> :OLD.RH_CWHEN then
    lcChanges := lcChanges || chr(13) || 'RH_CWHEN (' || to_char(:OLD.RH_CWHEN,'DD MON YYYY  HH24:MI:SS') || ' >> ' || to_char(:NEW.RH_CWHEN,'DD MON YYYY  HH24:MI:SS') || ')';
  end if;
  if    ( :NEW.RH_MODBY is null and :OLD.RH_MODBY is not null )
     or ( :NEW.RH_MODBY is not null and :OLD.RH_MODBY is null )
     or :NEW.RH_MODBY <> :OLD.RH_MODBY then
    lcChanges := lcChanges || chr(13) || 'RH_MODBY (' || :OLD.RH_MODBY || ' >> ' || :NEW.RH_MODBY || ')';
  end if;
  if    ( :NEW.RH_MODWHEN is null and :OLD.RH_MODWHEN is not null )
     or ( :NEW.RH_MODWHEN is not null and :OLD.RH_MODWHEN is null )
     or :NEW.RH_MODWHEN <> :OLD.RH_MODWHEN then
    lcChanges := lcChanges || chr(13) || 'RH_MODWHEN (' || to_char(:OLD.RH_MODWHEN, 'DD MON YYYY  HH24:MI:SS') || ' >> ' || to_char(:NEW.RH_MODWHEN, 'DD MON YYYY  HH24:MI:SS') || ')';
  end if;
  if    ( :NEW.RH_ROREF is null and :OLD.RH_ROREF is not null )
     or ( :NEW.RH_ROREF is not null and :OLD.RH_ROREF is null )
     or :NEW.RH_ROREF <> :OLD.RH_ROREF then
    P_INSERT_LOG_ENTRY('UPDATE', 'RESERVATION_HEADER', 'RH_ROREF', :NEW.RH_CODE, :OLD.RH_ROREF, :NEW.RH_ROREF, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RH_ROREF (' || :OLD.RH_ROREF || ' >> ' || :NEW.RH_ROREF || ')';
  end if;
  if    ( :NEW.RH_GAPS is null and :OLD.RH_GAPS is not null )
     or ( :NEW.RH_GAPS is not null and :OLD.RH_GAPS is null )
     or :NEW.RH_GAPS <> :OLD.RH_GAPS then
    lcChanges := lcChanges || chr(13) || 'RH_GAPS (' || :OLD.RH_GAPS || ' >> ' || :NEW.RH_GAPS || ')';
  end if;
  if    ( :NEW.RH_GROUP_ID is null and :OLD.RH_GROUP_ID is not null )
     or ( :NEW.RH_GROUP_ID is not null and :OLD.RH_GROUP_ID is null )
     or :NEW.RH_GROUP_ID <> :OLD.RH_GROUP_ID then
    P_INSERT_LOG_ENTRY('UPDATE', 'RESERVATION_HEADER', 'RH_GROUP_ID', :NEW.RH_CODE, :OLD.RH_GROUP_ID, :NEW.RH_GROUP_ID, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RH_GROUP_ID (' || :OLD.RH_GROUP_ID || ' >> ' || :NEW.RH_GROUP_ID || ')';
    lcRUChanges := lcRUChanges || chr(13) || 'RH_GROUP_ID (' || :OLD.RH_GROUP_ID || ' >> ' || :NEW.RH_GROUP_ID || ')';
  end if;
  if    ( :NEW.RH_EXT_BOOK_DATE is null and :OLD.RH_EXT_BOOK_DATE is not null )
     or ( :NEW.RH_EXT_BOOK_DATE is not null and :OLD.RH_EXT_BOOK_DATE is null )
     or :NEW.RH_EXT_BOOK_DATE <> :OLD.RH_EXT_BOOK_DATE then
    P_INSERT_LOG_ENTRY('UPDATE', 'RESERVATION_HEADER', 'RH_EXT_BOOK_DATE', :NEW.RH_CODE, :OLD.RH_EXT_BOOK_DATE, :NEW.RH_EXT_BOOK_DATE, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RH_EXT_BOOK_DATE (' || to_char(:OLD.RH_EXT_BOOK_DATE, 'DD MON YYYY  HH24:MI:SS') || ' >> ' || to_char(:NEW.RH_EXT_BOOK_DATE, 'DD MON YYYY  HH24:MI:SS') || ')';
    lcRUChanges := lcChanges || chr(13) || 'RH_EXT_BOOK_DATE (' || to_char(:OLD.RH_EXT_BOOK_DATE, 'DD MON YYYY  HH24:MI:SS') || ' >> ' || to_char(:NEW.RH_EXT_BOOK_DATE, 'DD MON YYYY  HH24:MI:SS') || ')';
  end if;
  if lcChanges is not NULL then
    lcChanges := substr(lcChanges, 2, 1999);
    insert into T_RHL -- LOBBY.RESERVATION_HEADER_LOG
      values (RESERVATION_HEADER_LOG_SEQ.nextval, USER, 'UPDATE', SYSDATE, :OLD.RH_CODE, lcChanges, k.ExecutingMainProc, k.ExecutingSubProc, k.ExecutingAction);
    if lcRUChanges is not NULL then
      -- P_RUL_INSERT() does this for us: lcRUChanges := substr(lcRUChanges, 2, 1999);
      for rRU in cRU loop
        P_RUL_INSERT('UPDATE', lcRUChanges, rRU.RU_BOARDREF, rRU.RU_CODE, NULL, rRU.RU_RHREF, rRU.RU_FROM_DATE, rRU.RU_FROM_DATE + rRU.RU_DAYS, rRU.RU_ATGENERIC, rRU.RU_RESORT, rRU.RU_SIHOT_OBJID, rRU.RO_SIHOT_RATE);
      end loop;
    end if;
  end if;
END;
/*
   ae:06-11-12  added RH_GROUP_ID column.
   ae:12-02-13  added RH_EXT_BOOK_REF (replacing unused RH_RTREF).
   ae:04-09-13  removed unused RH_NOADULTS/RH_NOCHILD columns.
   ae:12-06-14  added log entries for T_LOG.
   ae:07-10-16  V05: added call to P_RUL_INSERT() for sihot sync project.
*/
/

