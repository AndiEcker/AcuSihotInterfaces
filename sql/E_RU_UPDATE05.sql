create or replace trigger LOBBY.RU_UPDATE
AFTER UPDATE
ON T_RU
REFERENCING OLD AS OLD NEW AS NEW
FOR EACH ROW
DECLARE
  lcChanges varchar2(2000) := null;
  lcWKCode  T_CUA.CUA_WKREF%type;
  lcRate    T_RUL.RUL_SIHOT_RATE%type;
  
  cursor cCUA_CR is
    select least(c.CUA_WKREF) from T_CUA d, T_CUA c
     where d.CUA_TRANS_GROUP = c.CUA_TRANS_GROUP and d.CUA_CODE = :NEW.RU_UAREF;

  cursor cRO is
    select RO_SIHOT_RATE from T_RO where RO_CODE = :NEW.RU_ROREF;
  
BEGIN
  open  cCUA_CR;
  fetch cCUA_CR into lcWKCode;
  close cCUA_CR;
  
  if :NEW.RU_CODE<>:OLD.RU_CODE then
    lcChanges := lcChanges || chr(13) || 'RU_CODE (' || :OLD.RU_CODE || ' >> ' || :NEW.RU_CODE || ')';
  end if;
  if    ( :NEW.RU_CDREF is null and :OLD.RU_CDREF is not null )
     or ( :NEW.RU_CDREF is not null and :OLD.RU_CDREF is null )
     or :NEW.RU_CDREF<>:OLD.RU_CDREF then
    lcChanges := lcChanges || chr(13) || 'RU_CDREF (' || :OLD.RU_CDREF || ' >> ' || :NEW.RU_CDREF || ')';
  end if;
  if    ( :NEW.RU_MLREF is null and :OLD.RU_MLREF is not null )
     or ( :NEW.RU_MLREF is not null and :OLD.RU_MLREF is null )
     or :NEW.RU_MLREF<>:OLD.RU_MLREF then
    P_INSERT_LOG_ENTRY('UPDATE', 'REQUESTED_UNIT', 'RU_MLREF', :NEW.RU_CODE, :OLD.RU_MLREF, :NEW.RU_MLREF, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RU_MLREF (' || :OLD.RU_MLREF || ' >> ' || :NEW.RU_MLREF || ')';
  end if;
  if    ( :NEW.RU_RHREF is null and :OLD.RU_RHREF is not null )
     or ( :NEW.RU_RHREF is not null and :OLD.RU_RHREF is null )
     or :NEW.RU_RHREF<>:OLD.RU_RHREF then
    P_INSERT_LOG_ENTRY('UPDATE', 'REQUESTED_UNIT', 'RU_RHREF', :NEW.RU_CODE, :OLD.RU_RHREF, :NEW.RU_RHREF, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RU_RHREF (' || :OLD.RU_RHREF || ' >> ' || :NEW.RU_RHREF || ')';
  end if;
  if    ( :NEW.RU_UAREF is null and :OLD.RU_UAREF is not null )
     or ( :NEW.RU_UAREF is not null and :OLD.RU_UAREF is null )
     or :NEW.RU_UAREF<>:OLD.RU_UAREF then
    P_INSERT_LOG_ENTRY('UPDATE', 'REQUESTED_UNIT', 'RU_UAREF', :NEW.RU_CODE, :OLD.RU_UAREF, :NEW.RU_UAREF, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RU_UAREF (' || :OLD.RU_UAREF || ' >> ' || :NEW.RU_UAREF || ')';
  end if;
  if    ( :NEW.RU_ROREF is null and :OLD.RU_ROREF is not null )
     or ( :NEW.RU_ROREF is not null and :OLD.RU_ROREF is null )
     or :NEW.RU_ROREF<>:OLD.RU_ROREF then
    P_INSERT_LOG_ENTRY('UPDATE', 'REQUESTED_UNIT', 'RU_ROREF', :NEW.RU_CODE, :OLD.RU_ROREF, :NEW.RU_ROREF, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RU_ROREF (' || :OLD.RU_ROREF || ' >> ' || :NEW.RU_ROREF || ')';
  end if;
  if    ( :NEW.RU_EXT_APT is null and :OLD.RU_EXT_APT is not null )
     or ( :NEW.RU_EXT_APT is not null and :OLD.RU_EXT_APT is null )
     or :NEW.RU_EXT_APT <> :OLD.RU_EXT_APT then
    P_INSERT_LOG_ENTRY('UPDATE', 'REQUESTED_UNIT', 'RU_EXT_APT', :NEW.RU_CODE, :OLD.RU_EXT_APT, :NEW.RU_EXT_APT, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RU_EXT_APT (' || :OLD.RU_EXT_APT || ' >> ' || :NEW.RU_EXT_APT || ')';
  end if;
  if    ( :NEW.RU_ATGENERIC is null and :OLD.RU_ATGENERIC is not null )
     or ( :NEW.RU_ATGENERIC is not null and :OLD.RU_ATGENERIC is null )
     or :NEW.RU_ATGENERIC<>:OLD.RU_ATGENERIC then
    P_INSERT_LOG_ENTRY('UPDATE', 'REQUESTED_UNIT', 'RU_ATGENERIC', :NEW.RU_CODE, :OLD.RU_ATGENERIC, :NEW.RU_ATGENERIC, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RU_ATGENERIC (' || :OLD.RU_ATGENERIC || ' >> ' || :NEW.RU_ATGENERIC || ')';
  end if;
  if    ( :NEW.RU_RESORT is null and :OLD.RU_RESORT is not null )
     or ( :NEW.RU_RESORT is not null and :OLD.RU_RESORT is null )
     or :NEW.RU_RESORT<>:OLD.RU_RESORT then
    P_INSERT_LOG_ENTRY('UPDATE', 'REQUESTED_UNIT', 'RU_RESORT', :NEW.RU_CODE, :OLD.RU_RESORT, :NEW.RU_RESORT, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RU_RESORT (' || :OLD.RU_RESORT || ' >> ' || :NEW.RU_RESORT || ')';
  end if;

  if    ( :NEW.RU_ATTYPEVALUE is null and :OLD.RU_ATTYPEVALUE is not null )
     or ( :NEW.RU_ATTYPEVALUE is not null and :OLD.RU_ATTYPEVALUE is null )
     or :NEW.RU_ATTYPEVALUE<>:OLD.RU_ATTYPEVALUE then
    P_INSERT_LOG_ENTRY('UPDATE', 'REQUESTED_UNIT', 'RU_ATTYPEVALUE', :NEW.RU_CODE, :OLD.RU_ATTYPEVALUE, :NEW.RU_ATTYPEVALUE, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RU_ATTYPEVALUE (' || :OLD.RU_ATTYPEVALUE || ' >> ' || :NEW.RU_ATTYPEVALUE || ')';
  end if;
  if    ( :NEW.RU_STATUS is null and :OLD.RU_STATUS is not null )
     or ( :NEW.RU_STATUS is not null and :OLD.RU_STATUS is null )
     or :NEW.RU_STATUS<>:OLD.RU_STATUS then
    P_INSERT_LOG_ENTRY('UPDATE', 'REQUESTED_UNIT', 'RU_STATUS', :NEW.RU_CODE, :OLD.RU_STATUS, :NEW.RU_STATUS, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RU_STATUS (' || :OLD.RU_STATUS || ' >> ' || :NEW.RU_STATUS || ')';
  end if;
  if    ( :NEW.RU_SOURCE is null and :OLD.RU_SOURCE is not null )
     or ( :NEW.RU_SOURCE is not null and :OLD.RU_SOURCE is null )
     or :NEW.RU_SOURCE<>:OLD.RU_SOURCE then
    P_INSERT_LOG_ENTRY('UPDATE', 'REQUESTED_UNIT', 'RU_SOURCE', :NEW.RU_CODE, :OLD.RU_SOURCE, :NEW.RU_SOURCE, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RU_SOURCE (' || :OLD.RU_SOURCE || ' >> ' || :NEW.RU_SOURCE || ')';
  end if;
  if    ( :NEW.RU_FROM_DATE is null and :OLD.RU_FROM_DATE is not null )
     or ( :NEW.RU_FROM_DATE is not null and :OLD.RU_FROM_DATE is null )
     or :NEW.RU_FROM_DATE<>:OLD.RU_FROM_DATE then
    P_INSERT_LOG_ENTRY('UPDATE', 'REQUESTED_UNIT', 'RU_FROM_DATE', :NEW.RU_CODE, :OLD.RU_FROM_DATE, :NEW.RU_FROM_DATE, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RU_FROM_DATE (' || to_char(:OLD.RU_FROM_DATE, 'DD-MM-YY') || ' >> ' || to_char(:NEW.RU_FROM_DATE, 'DD-MM-YY') || ')';
  end if;
  if    ( :NEW.RU_DAYS is null and :OLD.RU_DAYS is not null )
     or ( :NEW.RU_DAYS is not null and :OLD.RU_DAYS is null )
     or :NEW.RU_DAYS<>:OLD.RU_DAYS then
    P_INSERT_LOG_ENTRY('UPDATE', 'REQUESTED_UNIT', 'RU_DAYS', :NEW.RU_CODE, :OLD.RU_DAYS, :NEW.RU_DAYS, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RU_DAYS (' || :OLD.RU_DAYS || ' >> ' || :NEW.RU_DAYS || ')';
  end if;
  if    ( :NEW.RU_FLIGHT_NO is null and :OLD.RU_FLIGHT_NO is not null )
     or ( :NEW.RU_FLIGHT_NO is not null and :OLD.RU_FLIGHT_NO is null )
     or :NEW.RU_FLIGHT_NO<>:OLD.RU_FLIGHT_NO then
    lcChanges := lcChanges || chr(13) || 'RU_FLIGHT_NO (' || :OLD.RU_FLIGHT_NO || ' >> ' || :NEW.RU_FLIGHT_NO || ')';
  end if;
  if    ( :NEW.RU_FLIGHT_LANDS is null and :OLD.RU_FLIGHT_LANDS is not null )
     or ( :NEW.RU_FLIGHT_LANDS is not null and :OLD.RU_FLIGHT_LANDS is null )
     or :NEW.RU_FLIGHT_LANDS<>:OLD.RU_FLIGHT_LANDS then
    lcChanges := lcChanges || chr(13) || 'RU_FLIGHT_LANDS (' || :OLD.RU_FLIGHT_LANDS || ' >> ' || :NEW.RU_FLIGHT_LANDS || ')';
  end if;
  if    ( :NEW.RU_FLIGHT_AIRPORT is null and :OLD.RU_FLIGHT_AIRPORT is not null )
     or ( :NEW.RU_FLIGHT_AIRPORT is not null and :OLD.RU_FLIGHT_AIRPORT is null )
     or :NEW.RU_FLIGHT_AIRPORT<>:OLD.RU_FLIGHT_AIRPORT then
    lcChanges := lcChanges || chr(13) || 'RU_FLIGHT_AIRPORT (' || :OLD.RU_FLIGHT_AIRPORT || ' >> ' || :NEW.RU_FLIGHT_AIRPORT || ')';
  end if;
  if    ( :NEW.RU_FLIGHT_PICKUP is null and :OLD.RU_FLIGHT_PICKUP is not null )
     or ( :NEW.RU_FLIGHT_PICKUP is not null and :OLD.RU_FLIGHT_PICKUP is null )
     or :NEW.RU_FLIGHT_PICKUP<>:OLD.RU_FLIGHT_PICKUP then
    lcChanges := lcChanges || chr(13) || 'RU_FLIGHT_PICKUP (' || :OLD.RU_FLIGHT_PICKUP || ' >> ' || :NEW.RU_FLIGHT_PICKUP || ')';
  end if;
  if    ( :NEW.RU_ADULTS is null and :OLD.RU_ADULTS is not null )
     or ( :NEW.RU_ADULTS is not null and :OLD.RU_ADULTS is null )
     or :NEW.RU_ADULTS<>:OLD.RU_ADULTS then
    lcChanges := lcChanges || chr(13) || 'RU_ADULTS (' || :OLD.RU_ADULTS || ' >> ' || :NEW.RU_ADULTS || ')';
  end if;
  if    ( :NEW.RU_CHILDREN is null and :OLD.RU_CHILDREN is not null )
     or ( :NEW.RU_CHILDREN is not null and :OLD.RU_CHILDREN is null )
     or :NEW.RU_CHILDREN<>:OLD.RU_CHILDREN then
    lcChanges := lcChanges || chr(13) || 'RU_CHILDREN (' || :OLD.RU_CHILDREN || ' >> ' || :NEW.RU_CHILDREN || ')';
  end if;
  if    ( :NEW.RU_BOARDREF is null and :OLD.RU_BOARDREF is not null )
     or ( :NEW.RU_BOARDREF is not null and :OLD.RU_BOARDREF is null )
     or :NEW.RU_BOARDREF<>:OLD.RU_BOARDREF then
    P_INSERT_LOG_ENTRY('UPDATE', 'REQUESTED_UNIT', 'RU_BOARDREF', :NEW.RU_CODE, :OLD.RU_BOARDREF, :NEW.RU_BOARDREF, lcWKCode);
    lcChanges := lcChanges || chr(13) || 'RU_BOARDREF (' || :OLD.RU_BOARDREF || ' >> ' || :NEW.RU_BOARDREF || ')';
  end if;

  if    ( :NEW.RU_CBY is null and :OLD.RU_CBY is not null )
     or ( :NEW.RU_CBY is not null and :OLD.RU_CBY is null )
     or :NEW.RU_CBY<>:OLD.RU_CBY then
    lcChanges := lcChanges || chr(13) || 'RU_CBY (' || :OLD.RU_CBY || ' >> ' || :NEW.RU_CBY || ')';
  end if;
  if    ( :NEW.RU_CWHEN is null and :OLD.RU_CWHEN is not null )
     or ( :NEW.RU_CWHEN is not null and :OLD.RU_CWHEN is null )
     or :NEW.RU_CWHEN<>:OLD.RU_CWHEN then
    lcChanges := lcChanges || chr(13) || 'RU_CWHEN (' || to_char(:OLD.RU_CWHEN,'DD MON YYYY  HH24:MI:SS') || ' >> ' || to_char(:NEW.RU_CWHEN,'DD MON YYYY  HH24:MI:SS') || ')';
  end if;
  if    ( :NEW.RU_MODBY is null and :OLD.RU_MODBY is not null )
     or ( :NEW.RU_MODBY is not null and :OLD.RU_MODBY is null )
     or :NEW.RU_MODBY<>:OLD.RU_MODBY then
    lcChanges := lcChanges || chr(13) || 'RU_MODBY (' || :OLD.RU_MODBY || ' >> ' || :NEW.RU_MODBY || ')';
  end if;
  if    ( :NEW.RU_MODWHEN is null and :OLD.RU_MODWHEN is not null )
     or ( :NEW.RU_MODWHEN is not null and :OLD.RU_MODWHEN is null )
     or :NEW.RU_MODWHEN<>:OLD.RU_MODWHEN then
    lcChanges := lcChanges || chr(13) || 'RU_MODWHEN (' || to_char(:OLD.RU_MODWHEN,'DD MON YYYY  HH24:MI:SS') || ' >> ' || to_char(:NEW.RU_MODWHEN,'DD MON YYYY  HH24:MI:SS') || ')';
  end if;

  if    ( :NEW.RU_SIHOT_OBJID is null and :OLD.RU_SIHOT_OBJID is not null )
     or ( :NEW.RU_SIHOT_OBJID is not null and :OLD.RU_SIHOT_OBJID is null )
     or :NEW.RU_SIHOT_OBJID<>:OLD.RU_SIHOT_OBJID then
    lcChanges := lcChanges || chr(13) || 'RU_SIHOT_OBJID (' || to_char(:OLD.RU_SIHOT_OBJID) || ' >> ' || to_char(:NEW.RU_SIHOT_OBJID) || ')';
  end if;

  if lcChanges is not null then
    open  cRO;
    fetch cRO into lcRate;
    close cRO;
    P_RUL_INSERT('R', 'UPDATE', lcChanges, :NEW.RU_BOARDREF, :NEW.RU_CODE, NULL, :NEW.RU_RHREF, :NEW.RU_FROM_DATE, :NEW.RU_FROM_DATE + :NEW.RU_DAYS, :NEW.RU_ATGENERIC, :NEW.RU_RESORT, :NEW.RU_SIHOT_OBJID, lcRate);
  end if;

END
/*
  ae:22-04-06 fixed LOG_TABLE bug (was CLIENT_USAGE_AC) and added NULL detection for
              all NULLable columns.
  ae:22-05-06 added debug log table entries (T_RUL)
  ae:10-01-07 removed RU_AROREF/RU_APREF/RU_FIXED/RU_ATFIXED/RU_RSFIXED, added RU_EXT_APT.
  ae:09-09-12 added RU_BOARDREF.
  ae:12-06-14 V01: refactored and extended logging into T_LOG by using P_INSERT_LOG_ENTRY instead of insert into T_LOG.
  ae:05-08-16 V02: added population of the new RUL_SIHOT* columns and added log for new RU_SIHOT_OBJID column.
  ae:02-10-16 V03: added RU_FLIGHT_AIRPORT column and.
  ae:21-02-17 V04: added pcCaller parameter to call of P_RUL_INSERT().
  ae:05-12-17 V05: added to_char(, 'DD-MM-YY') for to ensure correct string format of the RU_FROM_DATE value.
*/;
/
