create or replace trigger SALES.RAF_CHANGE
  AFTER INSERT or UPDATE or DELETE
ON T_RAF -- SALES.REQUEST_APT_FEATURES
REFERENCING NEW AS NEW OLD AS OLD
FOR EACH ROW
DECLARE
  lnPrimary T_RAF.RAF_RUREF%type;
  lnAftRef  T_RAF.RAF_AFTREF%type;
  lcAction  T_LOG.LOG_ACTION%type;
  lcRate    T_RO.RO_SIHOT_RATE%type;
  
  cursor cRU is
    select * from T_RU where RU_CODE = lnPrimary;
  rRU cRU%rowtype;
  
  cursor cRO is
    select RO_SIHOT_RATE from T_RO where RO_CODE = rRU.RU_ROREF;
  
BEGIN
  if deleting then
    lnPrimary := :OLD.RAF_RUREF;
    lnAftRef := :OLD.RAF_AFTREF;
    lcAction := 'DELETE';
  else
    lnPrimary := :NEW.RAF_RUREF;
    lnAftRef := :NEW.RAF_AFTREF;
    lcAction := case when inserting then 'INSERT' else 'UPDATE' end;
  end if;
  open  cRU;
  fetch cRU into rRU;
  close cRU;
  open  cRO;
  fetch cRO into lcRate;
  close cRO;
  P_RUL_INSERT('UPDATE', 'RAF_' || lcAction || ' (' || lnAftRef || ')', rRU.RU_BOARDREF, lnPrimary, NULL, rRU.RU_RHREF, rRU.RU_FROM_DATE, rRU.RU_FROM_DATE + rRU.RU_DAYS, rRU.RU_ATGENERIC, rRU.RU_RESORT, rRU.RU_SIHOT_OBJID, lcRate, lnAftRef);
END;
/*
  ae:28-11-2016 first beta version.
*/
/
