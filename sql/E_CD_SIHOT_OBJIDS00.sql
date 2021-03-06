create or replace trigger SALES.CD_SIHOT_OBJIDS
  after update on T_CD   -- SALES.CLIENT_DETAILS
  referencing new as NEW old as OLD
  for each row
  when (  (NEW.CD_SIHOT_OBJID <> OLD.CD_SIHOT_OBJID) or (NEW.CD_SIHOT_OBJID is NULL and OLD.CD_SIHOT_OBJID is not NULL) or (NEW.CD_SIHOT_OBJID is not NULL and OLD.CD_SIHOT_OBJID is NULL)
       or (NEW.CD_SIHOT_OBJID2 <> OLD.CD_SIHOT_OBJID2) or (NEW.CD_SIHOT_OBJID2 is NULL and OLD.CD_SIHOT_OBJID2 is not NULL) or (NEW.CD_SIHOT_OBJID2 is not NULL and OLD.CD_SIHOT_OBJID2 is NULL) 
       )
BEGIN
  if (:NEW.CD_SIHOT_OBJID <> :OLD.CD_SIHOT_OBJID) or (:NEW.CD_SIHOT_OBJID is NULL and :OLD.CD_SIHOT_OBJID is not NULL) or (:NEW.CD_SIHOT_OBJID is not NULL and :OLD.CD_SIHOT_OBJID is NULL) then
    P_INSERT_LOG_ENTRY ('UPDATE', 'CLIENT_DETAILS', 'CD_SIHOT_OBJID', :NEW.CD_CODE, :OLD.CD_SIHOT_OBJID, :NEW.CD_SIHOT_OBJID, NULL);
  end if;
  if (:NEW.CD_SIHOT_OBJID2 <> :OLD.CD_SIHOT_OBJID2) or (:NEW.CD_SIHOT_OBJID2 is NULL and :OLD.CD_SIHOT_OBJID2 is not NULL) or (:NEW.CD_SIHOT_OBJID2 is not NULL and :OLD.CD_SIHOT_OBJID2 is NULL) then
    P_INSERT_LOG_ENTRY ('UPDATE', 'CLIENT_DETAILS', 'CD_SIHOT_OBJID2', :NEW.CD_CODE, :OLD.CD_SIHOT_OBJID2, :NEW.CD_SIHOT_OBJID2, NULL);
  end if;
END
/*
   ae:26-03-2015  first beta.
*/;
/


