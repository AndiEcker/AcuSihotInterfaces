create or replace trigger SALES.PRC_UPDATE AFTER UPDATE ON T_PRC REFERENCING NEW AS NEW OLD AS OLD FOR EACH ROW
DECLARE  -- ORACLE showing wrong line number - even if you put this line at the end of the last one
  lcAction  T_LOG.LOG_ACTION%type := 'UPDATE';
  pcTable   T_LOG.LOG_TABLE%type := 'PROSPECTS';
  pcColumn  T_LOG.LOG_COLUMN%type;
  pcPrimary T_LOG.LOG_PRIMARY%type := :NEW.PRC_CODE;
  
  cursor cML is
    select ML_RHREF, ML_REQARRIVAL_DATE, ML_REQDEPART_DATE from T_ML, T_MS where ML_CODE = MS_MLREF and MS_PRCREF = :NEW.PRC_CODE;
  rML cML%rowtype;
    
BEGIN
  if    ( :NEW.PRC_TMREF is NULL and :OLD.PRC_TMREF is not NULL )
     or ( :NEW.PRC_TMREF is not NULL and :OLD.PRC_TMREF is NULL )
     or :NEW.PRC_TMREF <> :OLD.PRC_TMREF then
    pcColumn := 'PRC_TMREF';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_TMREF, :NEW.PRC_TMREF, '');
    if (:NEW.PRC_TMREF is not NULL) then
      insert into t_pal
      (pal_timestamp, pal_prcref, pal_tmref, pal_rerun_count)
      values
      (systimestamp, :new.prc_code, :new.prc_tmref, :new.prc_rerun_counter);
    end if;
  end if;
  -- PRC_STATUS
  if    ( :NEW.PRC_STATUS is NULL and :OLD.PRC_STATUS is not NULL )
     or ( :NEW.PRC_STATUS is not NULL and :OLD.PRC_STATUS is NULL )
     or :NEW.PRC_STATUS <> :OLD.PRC_STATUS then
    pcColumn := 'PRC_STATUS';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_STATUS, :NEW.PRC_STATUS, '');
  end if;
  --NAME1
  if    ( :NEW.PRC_FNAM1 || :NEW.PRC_SNAM1 is NULL and :OLD.PRC_FNAM1 || :OLD.PRC_SNAM1 is not NULL )
     or ( :NEW.PRC_FNAM1 || :NEW.PRC_SNAM1 is not NULL and :OLD.PRC_FNAM1 || :OLD.PRC_SNAM1 is NULL )
     or :NEW.PRC_FNAM1 || :NEW.PRC_SNAM1 <> :OLD.PRC_FNAM1 || :OLD.PRC_SNAM1 then
    pcColumn := 'PRC_NAME1';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_FNAM1 || ' ' || :OLD.PRC_SNAM1, :NEW.PRC_FNAM1 || ' ' || :NEW.PRC_SNAM1, '');
  end if;
  -- NAME2
  if    ( :NEW.PRC_FNAM2 || :NEW.PRC_SNAM2 is NULL and :OLD.PRC_FNAM2 || :OLD.PRC_SNAM2 is not NULL )
     or ( :NEW.PRC_FNAM2 || :NEW.PRC_SNAM2 is not NULL and :OLD.PRC_FNAM2 || :OLD.PRC_SNAM2 is NULL )
     or :NEW.PRC_FNAM2 || :NEW.PRC_SNAM2 <> :OLD.PRC_FNAM2 || :OLD.PRC_SNAM2 then
    pcColumn := 'PRC_NAME2';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_FNAM2 || ' ' || :OLD.PRC_SNAM2, :NEW.PRC_FNAM2 || ' ' || :NEW.PRC_SNAM2, '');
  end if;
  -- HTEL
  if    ( :NEW.PRC_HTEL1 is NULL and :OLD.PRC_HTEL1 is not NULL )
     or ( :NEW.PRC_HTEL1 is not NULL and :OLD.PRC_HTEL1 is NULL )
     or :NEW.PRC_HTEL1 <> :OLD.PRC_HTEL1 then
    pcColumn := 'PRC_HTEL1';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_HTEL1, :NEW.PRC_HTEL1, '');
  end if;
  --WTEL
  if    ( :NEW.PRC_WTEL1 is NULL and :OLD.PRC_WTEL1 is not NULL )
     or ( :NEW.PRC_WTEL1 is not NULL and :OLD.PRC_WTEL1 is NULL )
     or :NEW.PRC_WTEL1 <> :OLD.PRC_WTEL1 then
    pcColumn := 'PRC_WTEL1';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_WTEL1, :NEW.PRC_WTEL1, '');
  end if;
  -- MTEL
  if    ( :NEW.PRC_MTEL1 is NULL and :OLD.PRC_MTEL1 is not NULL )
     or ( :NEW.PRC_MTEL1 is not NULL and :OLD.PRC_MTEL1 is NULL )
     or :NEW.PRC_MTEL1 <> :OLD.PRC_MTEL1 then
    pcColumn := 'PRC_MTEL1';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_MTEL1, :NEW.PRC_MTEL1, '');
  end if;
  -- EMAIL
  if    ( :NEW.PRC_EMAIL is NULL and :OLD.PRC_EMAIL is not NULL )
     or ( :NEW.PRC_EMAIL is not NULL and :OLD.PRC_EMAIL is NULL )
     or :NEW.PRC_EMAIL <> :OLD.PRC_EMAIL then
    pcColumn := 'PRC_EMAIL';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_EMAIL, :NEW.PRC_EMAIL, '');
  end if;
  -- LOCKED_COLS
  if    ( :NEW.PRC_LOCKED_COLS is NULL and :OLD.PRC_LOCKED_COLS is not NULL )
     or ( :NEW.PRC_LOCKED_COLS is not NULL and :OLD.PRC_LOCKED_COLS is NULL )
     or :NEW.PRC_LOCKED_COLS <> :OLD.PRC_LOCKED_COLS then
    pcColumn := 'PRC_LOCKED_COLS';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_LOCKED_COLS, :NEW.PRC_LOCKED_COLS, '');
  end if;
  -- CLIENT COMMENTS
  if    ( :NEW.PRC_CLIENT_COMMENTS is NULL and :OLD.PRC_CLIENT_COMMENTS is not NULL )
     or ( :NEW.PRC_CLIENT_COMMENTS is not NULL and :OLD.PRC_CLIENT_COMMENTS is NULL )
     or :NEW.PRC_CLIENT_COMMENTS <> :OLD.PRC_CLIENT_COMMENTS then
    pcColumn := 'PRC_CLIENT_COMMENTS';
    P_INSERT_LOG_DIFF_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_CLIENT_COMMENTS, :NEW.PRC_CLIENT_COMMENTS);
  end if;
  -- FLIGHT COMMENTS
  if    ( :NEW.PRC_FLIGHT_COMMENTS is NULL and :OLD.PRC_FLIGHT_COMMENTS is not NULL )
     or ( :NEW.PRC_FLIGHT_COMMENTS is not NULL and :OLD.PRC_FLIGHT_COMMENTS is NULL )
     or :NEW.PRC_FLIGHT_COMMENTS <> :OLD.PRC_FLIGHT_COMMENTS then
    pcColumn := 'PRC_FLIGHT_COMMENTS';
    P_INSERT_LOG_DIFF_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_FLIGHT_COMMENTS, :NEW.PRC_FLIGHT_COMMENTS);
  end if;
  -- FLYBUY generator
  if    ( :NEW.PRC_FLYBUY is NULL and :OLD.PRC_FLYBUY is not NULL )
     or ( :NEW.PRC_FLYBUY is not NULL and :OLD.PRC_FLYBUY is NULL )
     or :NEW.PRC_FLYBUY <> :OLD.PRC_FLYBUY then
    pcColumn := 'PRC_FLYBUY';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_FLYBUY, :NEW.PRC_FLYBUY, '');
  end if;
  -- meal plan
  if    ( :NEW.PRC_BOARDREF1 is NULL and :OLD.PRC_BOARDREF1 is not NULL )
     or ( :NEW.PRC_BOARDREF1 is not NULL and :OLD.PRC_BOARDREF1 is NULL )
     or :NEW.PRC_BOARDREF1 <> :OLD.PRC_BOARDREF1 then
    pcColumn := 'PRC_BOARDREF1';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_BOARDREF1, :NEW.PRC_BOARDREF1, '');
    open  cML;
    fetch cML into rML;
    close cML;
    if rML.ML_RHREF is not NULL then
      P_RH_RUL_INSERT('M', 'UPDATE', chr(13) || 'PRC_BOARDREF1 (' || :OLD.PRC_BOARDREF1 || ' >> ' || :NEW.PRC_BOARDREF1 || ')', 'MKT_' || :NEW.PRC_BOARDREF1, :NEW.PRC_CODE, NULL, 
                      rML.ML_RHREF, rML.ML_REQARRIVAL_DATE, rML.ML_REQDEPART_DATE);
    end if;
  end if;
  if    ( :NEW.PRC_MEAL_BEGIN1 is NULL and :OLD.PRC_MEAL_BEGIN1 is not NULL )
     or ( :NEW.PRC_MEAL_BEGIN1 is not NULL and :OLD.PRC_MEAL_BEGIN1 is NULL )
     or :NEW.PRC_MEAL_BEGIN1 <> :OLD.PRC_MEAL_BEGIN1 then
    pcColumn := 'PRC_MEAL_BEGIN1';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_MEAL_BEGIN1, :NEW.PRC_MEAL_BEGIN1, '');
  end if;
  if    ( :NEW.PRC_MEAL_END1 is NULL and :OLD.PRC_MEAL_END1 is not NULL )
     or ( :NEW.PRC_MEAL_END1 is not NULL and :OLD.PRC_MEAL_END1 is NULL )
     or :NEW.PRC_MEAL_END1 <> :OLD.PRC_MEAL_END1 then
    pcColumn := 'PRC_MEAL_END1';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_MEAL_END1, :NEW.PRC_MEAL_END1, '');
  end if;
  if    ( :NEW.PRC_BOARDREF2 is NULL and :OLD.PRC_BOARDREF2 is not NULL )
     or ( :NEW.PRC_BOARDREF2 is not NULL and :OLD.PRC_BOARDREF2 is NULL )
     or :NEW.PRC_BOARDREF2 <> :OLD.PRC_BOARDREF2 then
    pcColumn := 'PRC_BOARDREF2';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_BOARDREF2, :NEW.PRC_BOARDREF2, '');
  end if;
  if    ( :NEW.PRC_MEAL_BEGIN2 is NULL and :OLD.PRC_MEAL_BEGIN2 is not NULL )
     or ( :NEW.PRC_MEAL_BEGIN2 is not NULL and :OLD.PRC_MEAL_BEGIN2 is NULL )
     or :NEW.PRC_MEAL_BEGIN2 <> :OLD.PRC_MEAL_BEGIN2 then
    pcColumn := 'PRC_MEAL_BEGIN2';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_MEAL_BEGIN2, :NEW.PRC_MEAL_BEGIN2, '');
  end if;
  if    ( :NEW.PRC_MEAL_END2 is NULL and :OLD.PRC_MEAL_END2 is not NULL )
     or ( :NEW.PRC_MEAL_END2 is not NULL and :OLD.PRC_MEAL_END2 is NULL )
     or :NEW.PRC_MEAL_END2 <> :OLD.PRC_MEAL_END2 then
    pcColumn := 'PRC_MEAL_END2';
    P_INSERT_LOG_ENTRY (lcAction, pcTable, pcColumn, pcPrimary, :OLD.PRC_MEAL_END2, :NEW.PRC_MEAL_END2, '');
  end if;
END;
/*
  ae:  18-08-2008 first beta version.
  grs: 27-02-2010 added the insert into the PROSPECT_ASSIGN_LOG.
  grs: 15-05-2010 added name and phone number checks.
  gf:  28-02-2013 added email checks.
  ae:  15-04-2013 added log entries for PRC_LOCKED_COLS.
  ae:  02-05-2013 added log entries for flight and client comments (PRC_FLIGHT_COMMENTS/PRC_CLIENT_COMMENTS)
              AND removed OF <columns> clause from trigger declaration for to fix non-logged PRC_LOCKED_COLS.
  ae:  04-08-2013 added log entries for PRC_FLYBUY column (see TrackIt WO #91675).
  ae:  09-12-2014 added log entries for new mkt. meal plan (PRC_BOARDREF1/2 and PRC_MEAL_BEGIN1/2/_END1/2).
  ae:  21-02-2017 V07: changed to call newly added P_RH_RUL_INSERT() instead of P_RUL_INSERT() and added pcCaller parameter to call of P_RUL_INSERT(). 
*/
/
