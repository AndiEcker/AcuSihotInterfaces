create or replace trigger LOBBY.RU_DELETE
BEFORE DELETE
ON LOBBY.REQUESTED_UNIT 
REFERENCING NEW AS NEW OLD AS OLD
FOR EACH ROW
DECLARE
  lcChanges varchar2(2000) := null;
  lcRate    T_RUL.RUL_SIHOT_RATE%type;
  
  cursor cRO is
    select RO_SIHOT_RATE from T_RO where RO_CODE = :OLD.RU_ROREF;

BEGIN

  if :OLD.RU_CODE is not null then
    lcChanges := lcChanges || chr(13) || 'RU_CODE (' || :OLD.RU_CODE || ')';
  end if;
  if :OLD.RU_CDREF is not null then
    lcChanges := lcChanges || chr(13) || 'RU_CDREF (' || :OLD.RU_CDREF || ')';
  end if;
  if :OLD.RU_MLREF is not null then
    lcChanges := lcChanges || chr(13) || 'RU_MLREF (' || :OLD.RU_MLREF || ')';
  end if;
  if :OLD.RU_RHREF is not null then
    lcChanges := lcChanges || chr(13) || 'RU_RHREF (' || :OLD.RU_RHREF || ')';
  end if;
  if :OLD.RU_UAREF is not null then
    lcChanges := lcChanges || chr(13) || 'RU_UAREF (' || :OLD.RU_UAREF || ')';
  end if;
  if :OLD.RU_ROREF is not null then
    lcChanges := lcChanges || chr(13) || 'RU_ROREF (' || :OLD.RU_ROREF || ')';
  end if;
  if :OLD.RU_EXT_APT is not null then
    lcChanges := lcChanges || chr(13) || 'RU_EXT_APT (' || :OLD.RU_EXT_APT || ')';
  end if;
  if :OLD.RU_ATGENERIC is not null then
    lcChanges := lcChanges || chr(13) || 'RU_ATGENERIC (' || :OLD.RU_ATGENERIC || ')';
  end if;
  if :OLD.RU_RESORT is not null then
    lcChanges := lcChanges || chr(13) || 'RU_RESORT (' || :OLD.RU_RESORT || ')';
  end if;

  if :OLD.RU_ATTYPEVALUE is not null then
    lcChanges := lcChanges || chr(13) || 'RU_ATTYPEVALUE (' || :OLD.RU_ATTYPEVALUE || ')';
  end if;
  if :OLD.RU_STATUS is not null then
    lcChanges := lcChanges || chr(13) || 'RU_STATUS (' || :OLD.RU_STATUS || ')';
  end if;
  if :OLD.RU_SOURCE is not null then
    lcChanges := lcChanges || chr(13) || 'RU_SOURCE (' || :OLD.RU_SOURCE || ')';
  end if;
  if :OLD.RU_FROM_DATE is not null then
    lcChanges := lcChanges || chr(13) || 'RU_FROM_DATE (' || to_char(:OLD.RU_FROM_DATE, 'DD-MM-YY') || ')';
  end if;
  if :OLD.RU_DAYS is not null then
    lcChanges := lcChanges || chr(13) || 'RU_DAYS (' || :OLD.RU_DAYS || ')';
  end if;
  if :OLD.RU_FLIGHT_NO is not null then
    lcChanges := lcChanges || chr(13) || 'RU_FLIGHT_NO (' || :OLD.RU_FLIGHT_NO || ')';
  end if;
  if :OLD.RU_FLIGHT_LANDS is not null then
    lcChanges := lcChanges || chr(13) || 'RU_FLIGHT_LANDS (' || :OLD.RU_FLIGHT_LANDS || ')';
  end if;
  if :OLD.RU_FLIGHT_PICKUP is not null then
    lcChanges := lcChanges || chr(13) || 'RU_FLIGHT_PICKUP (' || :OLD.RU_FLIGHT_PICKUP || ')';
  end if;
  if :OLD.RU_ADULTS is not null then
    lcChanges := lcChanges || chr(13) || 'RU_ADULTS (' || :OLD.RU_ADULTS || ')';
  end if;
  if :OLD.RU_CHILDREN is not null then
    lcChanges := lcChanges || chr(13) || 'RU_CHILDREN (' || :OLD.RU_CHILDREN || ')';
  end if;
  if :OLD.RU_BOARDREF is not null then
    lcChanges := lcChanges || chr(13) || 'RU_BOARDREF (' || :OLD.RU_BOARDREF || ')';
  end if;

  if :OLD.RU_CBY is not null then
    lcChanges := lcChanges || chr(13) || 'RU_CBY (' || :OLD.RU_CBY || ')';
  end if;
  if :OLD.RU_CWHEN is not null then
    lcChanges := lcChanges || chr(13) || 'RU_CWHEN (' || to_char(:OLD.RU_CWHEN,'DD MON YYYY  HH24:MI:SS') || ')';
  end if;
  if :OLD.RU_MODBY is not null then
    lcChanges := lcChanges || chr(13) || 'RU_MODBY (' || :OLD.RU_MODBY || ')';
  end if;
  if :OLD.RU_MODWHEN is not null then
    lcChanges := lcChanges || chr(13) || 'RU_MODWHEN (' || to_char(:OLD.RU_MODWHEN,'DD MON YYYY  HH24:MI:SS') || ')';
  end if;

  if :OLD.RU_SIHOT_OBJID is not null then
    lcChanges := lcChanges || chr(13) || 'RU_SIHOT_OBJID (' || :OLD.RU_SIHOT_OBJID || ')';
  end if;

  if lcChanges is not null then
    open  cRO;
    fetch cRO into lcRate;
    close cRO;
    P_RUL_INSERT('R', 'DELETE', lcChanges, :OLD.RU_BOARDREF, :OLD.RU_CODE, NULL, :OLD.RU_RHREF, :OLD.RU_FROM_DATE, :OLD.RU_FROM_DATE + :OLD.RU_DAYS, :OLD.RU_ATGENERIC, :OLD.RU_RESORT, :OLD.RU_SIHOT_OBJID, lcRate);
  end if;
END
/*
  ae:22-05-06 first beta version
  ae:10-01-07 removed RU_AROREF/RU_APREF/RU_FIXED/RU_ATFIXED/RU_RSFIXED, added RU_EXT_APT.
  ae:09-09-12 V01: added RU_BOARDREF.
  ae:05-08-16 V02: added population of the new RUL_SIHOT* columns.
  ae:21-02-17 V03: added pcCaller parameter to call of P_RUL_INSERT().
  ae:05-12-17 V04: added to_char(, 'DD-MM-YY') for to ensure correct string format of the RU_FROM_DATE value.
*/;
/




