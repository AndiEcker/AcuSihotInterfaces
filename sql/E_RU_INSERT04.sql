create or replace trigger LOBBY.RU_INSERT
AFTER INSERT
ON LOBBY.REQUESTED_UNIT REFERENCING OLD AS OLD NEW AS NEW
FOR EACH ROW
DECLARE
  lcChanges varchar2(2000) := null;
  lcRate    T_RUL.RUL_SIHOT_RATE%type;
  
  cursor cRO is
    select RO_SIHOT_RATE from T_RO where RO_CODE = :NEW.RU_ROREF;

BEGIN

  if :NEW.RU_CODE is not null then
    lcChanges := lcChanges || chr(13) || 'RU_CODE (' || :NEW.RU_CODE || ')';
  end if;
  if :NEW.RU_CDREF is not null then
    lcChanges := lcChanges || chr(13) || 'RU_CDREF (' || :NEW.RU_CDREF || ')';
  end if;
  if :NEW.RU_MLREF is not null then
    lcChanges := lcChanges || chr(13) || 'RU_MLREF (' || :NEW.RU_MLREF || ')';
  end if;
  if :NEW.RU_RHREF is not null then
    lcChanges := lcChanges || chr(13) || 'RU_RHREF (' || :NEW.RU_RHREF || ')';
  end if;
  if :NEW.RU_UAREF is not null then
    lcChanges := lcChanges || chr(13) || 'RU_UAREF (' || :NEW.RU_UAREF || ')';
  end if;
  if :NEW.RU_ROREF is not null then
    lcChanges := lcChanges || chr(13) || 'RU_ROREF (' || :NEW.RU_ROREF || ')';
  end if;

  if :NEW.RU_EXT_APT is not null then
    lcChanges := lcChanges || chr(13) || 'RU_EXT_APT (' || :NEW.RU_EXT_APT || ')';
  end if;
  if :NEW.RU_ATGENERIC is not null then
    lcChanges := lcChanges || chr(13) || 'RU_ATGENERIC (' || :NEW.RU_ATGENERIC || ')';
  end if;
  if :NEW.RU_RESORT is not null then
    lcChanges := lcChanges || chr(13) || 'RU_RESORT (' || :NEW.RU_RESORT || ')';
  end if;
  if :NEW.RU_ATTYPEVALUE is not null then
    lcChanges := lcChanges || chr(13) || 'RU_ATTYPEVALUE (' || :NEW.RU_ATTYPEVALUE || ')';
  end if;
  if :NEW.RU_STATUS is not null then
    lcChanges := lcChanges || chr(13) || 'RU_STATUS (' || :NEW.RU_STATUS || ')';
  end if;
  if :NEW.RU_SOURCE is not null then
    lcChanges := lcChanges || chr(13) || 'RU_SOURCE (' || :NEW.RU_SOURCE || ')';
  end if;
  if :NEW.RU_FROM_DATE is not null then
    lcChanges := lcChanges || chr(13) || 'RU_FROM_DATE (' || to_char(:NEW.RU_FROM_DATE, 'DD-MM-YY') || ')';
  end if;
  if :NEW.RU_DAYS is not null then
    lcChanges := lcChanges || chr(13) || 'RU_DAYS (' || :NEW.RU_DAYS || ')';
  end if;
  if :NEW.RU_FLIGHT_NO is not null then
    lcChanges := lcChanges || chr(13) || 'RU_FLIGHT_NO (' || :NEW.RU_FLIGHT_NO || ')';
  end if;
  if :NEW.RU_FLIGHT_LANDS is not null then
    lcChanges := lcChanges || chr(13) || 'RU_FLIGHT_LANDS (' || :NEW.RU_FLIGHT_LANDS || ')';
  end if;
  if :NEW.RU_FLIGHT_PICKUP is not null then
    lcChanges := lcChanges || chr(13) || 'RU_FLIGHT_PICKUP (' || :NEW.RU_FLIGHT_PICKUP || ')';
  end if;
  if :NEW.RU_ADULTS is not null then
    lcChanges := lcChanges || chr(13) || 'RU_ADULTS (' || :NEW.RU_ADULTS || ')';
  end if;
  if :NEW.RU_CHILDREN is not null then
    lcChanges := lcChanges || chr(13) || 'RU_CHILDREN (' || :NEW.RU_CHILDREN || ')';
  end if;
  if :NEW.RU_BOARDREF is not null then
    lcChanges := lcChanges || chr(13) || 'RU_BOARDREF (' || :NEW.RU_BOARDREF || ')';
  end if;

  if :NEW.RU_CWHEN is not null then
    lcChanges := lcChanges || chr(13) || 'RU_CWHEN (' || to_char(:NEW.RU_CWHEN,'DD-MON-YYYY HH24:MI:SS') || ')';
  end if;
  if :NEW.RU_CBY is not null then
    lcChanges := lcChanges || chr(13) || 'RU_CBY (' || :NEW.RU_CBY || ')';
  end if;
  if :NEW.RU_MODWHEN is not null then
    lcChanges := lcChanges || chr(13) || 'RU_MODWHEN (' || to_char(:NEW.RU_MODWHEN,'DD-MON-YYYY HH24:MI:SS') || ')';
  end if;
  if :NEW.RU_MODBY is not null then
    lcChanges := lcChanges || chr(13) || 'RU_MODBY (' || :NEW.RU_MODBY || ')';
  end if;
  if :NEW.RU_SIHOT_OBJID is not null then
    lcChanges := lcChanges || chr(13) || 'RU_SIHOT_OBJID (' || :NEW.RU_SIHOT_OBJID || ')';
  end if;

  if lcChanges is not null then
    open  cRO;
    fetch cRO into lcRate;
    close cRO;
    P_RUL_INSERT('R', 'INSERT', lcChanges, :NEW.RU_BOARDREF, :NEW.RU_CODE, NULL, :NEW.RU_RHREF, :NEW.RU_FROM_DATE, :NEW.RU_FROM_DATE + :NEW.RU_DAYS, :NEW.RU_ATGENERIC, :NEW.RU_RESORT, :NEW.RU_SIHOT_OBJID, lcRate);
  end if;
END
/*
  ae:22-05-06 first beta version
  ae:10-01-07 removed RU_AROREF/RU_APREF/RU_FIXED/RU_ATFIXED/RU_RSFIXED, added RU_EXT_APT.
  ae:09-09-12 V01: added RU_BOARDREF.
  ae:05-08-16 V02: added population of the new RUL_SIHOT* columns.
  ae:21-02-17 V03: added pcCaller parameter to call of P_RUL_INSERT().
  ae:05-12-17 V04: added to_char(, 'DD-MM-YY') to ensure correct string format of the RU_FROM_DATE value.
*/;
/

