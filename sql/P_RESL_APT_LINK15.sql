CREATE OR REPLACE PROCEDURE LOBBY.RESL_APT_LINK(
    pnARO_Code  IN number,
    pnRH_Code   IN OUT number,              -- <= 0 means UNLINK and return new RH_CODE
    pnCommit    IN number := 1,             -- 1=commit (if pcProc <> '_'), 0=no commit
    pcProc      IN varchar2 := 'RAC!')      -- calling procedure
IS
  lnStackLen   integer;
  lnML_pnARO   T_ML.ML_CODE%type;
  lnML_pnRH    T_ML.ML_CODE%type;
  lcSource     T_RU.RU_SOURCE%type;
  ldSplit      date;
  lbUnlinkBeg  boolean;

  cursor cARO is
    select * from T_ARO where ARO_CODE = pnARO_Code;
  rARO cARO%rowtype;

  cursor cARO_Range_ARORH is
    select min(ARO_EXP_ARRIVE) dMin, max(ARO_EXP_DEPART) dMax from T_ARO
     where ARO_RHREF = rARO.ARO_RHREF
       and ARO_STATUS <> k.ROCancelled;
  rARO_Range_ARORH cARO_Range_ARORH%rowtype;

  cursor cARO_ChIn is
    select * from T_ARO
     where ARO_RHREF = pnRH_Code
       and ARO_STATUS in (k.ROCheckedIn, k.ROTransferIn);
  rARO_ChIn cARO_ChIn%rowtype;
  
  cursor cRH_pnARO is
    select * from T_RH where RH_CODE = rARO.ARO_RHREF;
  rRH_pnARO cRH_pnARO%rowtype;

  cursor cRH_pnRH is
    select * from T_RH where RH_CODE = pnRH_Code;
  rRH_pnRH cRH_pnRH%rowtype;

  cursor cARO_LeftLast is
    select * from T_ARO
     where ARO_RHREF = pnRH_Code and ARO_EXP_DEPART = rRH_pnRH.RH_TO_DATE and ARO_STATUS <> k.ROCancelled;
  rARO_LeftLast cARO_LeftLast%rowtype;

  cursor cARO_RightFirst is
    select * from T_ARO
     where ARO_RHREF = pnRH_Code and ARO_EXP_ARRIVE = rRH_pnRH.RH_FROM_DATE and ARO_STATUS <> k.ROCancelled;
  rARO_RightFirst cARO_RightFirst%rowtype;

  cursor cRU_pnARO is
    select * from T_RU
      where RU_RHREF = rARO.ARO_RHREF
        and RU_FROM_DATE >= rARO.ARO_EXP_ARRIVE and RU_FROM_DATE < rARO.ARO_EXP_DEPART
        and RU_STATUS <> k.ROCancelled
      order by RU_FROM_DATE;
  rRU_pnARO cRU_pnARO%rowtype;

  cursor cRU_Split is
    select * from T_RU
      where RU_RHREF = rARO.ARO_RHREF
        and RU_FROM_DATE < ldSplit
        and RU_FROM_DATE + RU_DAYS > ldSplit
        and RU_STATUS <> k.ROCancelled;
  rRU T_RU%rowtype;

  cursor cMKT(pnRHRef T_RH.RH_CODE%type) is
    select ML_CODE from T_ML
      where ML_RHREF = pnRHRef
      order by ML_STATUS desc;  --    more secure (with our buggy Mkt system) than: and ML_STATUS <> k.MLCancelled;

  -- exceptions
  date_range_not_contiguous  exception;
  unlink_not_at_begin_or_end exception;
  link_different_mkt_leads   exception;
  link_mkt_to_end            exception;
  requested_unit_split       exception;
  unlink_mkt_from_RH         exception;
  cancelled_record           exception;

  -- LINK: update/extend to_date of the RH record (specified in the 1st param)
  -- .. with the value from the old RH record (specified in the 2nd parameter)
  -- .. AND merge together the request comments of both requests.
  procedure rh_extend (plnRH_Code number, plnRH_Old number)
  is
  begin
    update T_RH set RH_TO_DATE = (select RH_TO_DATE from T_RH where RH_CODE = plnRH_Old),
                    RH_REQUNIT = case when instr(RH_REQUNIT, (select RH_REQUNIT from T_RH where RH_CODE = plnRH_Old)) > 0 then RH_REQUNIT
                                      when instr((select RH_REQUNIT from T_RH where RH_CODE = plnRH_Old), RH_REQUNIT) > 0 then (select RH_REQUNIT from T_RH where RH_CODE = plnRH_Old)
                                                                                                                          else RH_REQUNIT || chr(13) || (select RH_REQUNIT from T_RH where RH_CODE = plnRH_Old) end
      where RH_CODE = plnRH_Code;
  end;

  -- LINK: update RHREF columns in T_ARO and T_RU (could be two or more records)
  procedure rhref_update (plnRH_OldCode number, plnRH_NewCode number)
  is
  begin
    update T_RU set RU_RHREF = plnRH_NewCode
      where RU_RHREF = plnRH_OldCode;
    update T_ARO set ARO_RHREF = plnRH_NewCode
      where ARO_RHREF = plnRH_OldCode;
  end;

  -- LINK: remove now unused request records and debit
  procedure req_delete (plnRH_Code number)
  is
  begin
    delete from T_RH where RH_CODE = plnRH_Code;
  end;

BEGIN
  -- setup procedure env
  lnStackLen := F_PROC_STACK_ON('RESL_APT_LINK');
  if pcProc <> '_' then
    P_PROC_SET(pcProc, 'RESL_APT_LINK', 'ARO=' || pnARO_Code || '; RH=' || pnRH_Code);
  end if;

  -- fetch ARO record to [un]link
  open  cARO;
  fetch cARO into rARO;
  close cARO;
  if rARO.ARO_STATUS = k.ROCancelled then
    raise cancelled_record;
  end if;

  if pnRH_Code > 0 then        -- LINK to pnRH_Code
    -- fetch date ranges to find first RH record and check for Mkt references and overlaps/gaps
	  open  cRH_pnARO;
	  fetch cRH_pnARO into rRH_pnARO;
	  close cRH_pnARO;
    open  cMKT(rRH_pnARO.RH_CODE);
    fetch cMKT into lnML_pnARO;
    close cMKT;

    open  cRH_pnRH;
    fetch cRH_pnRH into rRH_pnRH;
    close cRH_pnRH;
    if rRH_pnRH.RH_STATUS = k.ROCancelled then
      raise cancelled_record;
    end if;
    open  cMKT(rRH_pnRH.RH_CODE);
    fetch cMKT into lnML_pnRH;
    close cMKT;

    if nvl(lnML_pnRH,0) <> nvl(lnML_pnARO,0) and (nvl(lnML_pnRH,0) > 0 and nvl(lnML_pnARO,0) > 0) then
      raise link_different_mkt_leads;

    elsif rRH_pnRH.RH_TO_DATE = rRH_pnARO.RH_FROM_DATE then
      if nvl(lnML_pnARO,0) > 0 then
        raise link_mkt_to_end;
      end if;
      -- update ARO_MOVING_TO
      open  cARO_LeftLast;
      fetch cARO_LeftLast into rARO_LeftLast;
      if cARO_LeftLast%found then
        -- replaced UPDATE with proc call (to also update ARO_AROREF_TO column on autotransfer)
        --update T_ARO set ARO_MOVING_TO = case when rARO.ARO_APREF = rARO_LeftLast.ARO_APREF then 'a:' end || rARO.ARO_APREF
        -- where ARO_CODE = rARO_LeftLast.ARO_CODE;  -- and rARO.ARO_EXP_ARRIVE = rRH_pnARO.RH_FROM_DATE
        P_ARO_MOVING_TO_UPDATE(rARO_LeftLast.ARO_CODE, rARO.ARO_APREF);
      end if;
      close cARO_LeftLast;
      -- extend pnRH_Code record and delete pnARO_RHREF record
      rh_extend(pnRH_Code, rARO.ARO_RHREF);
      rhref_update(rARO.ARO_RHREF, pnRH_Code);
      req_delete(rARO.ARO_RHREF);
      -- check ARO_STATUS change if previous apts checked in (at least one)
      open  cARO_ChIn;
      fetch cARO_ChIn into rARO_ChIn;  -- don't overwrite rARO (used for protocol)
      if cARO_ChIn%found then
        update T_ARO set ARO_STATUS = k.ROOnSiteNotOcc
          where ARO_CODE = pnARO_Code and ARO_STATUS < k.ROCheckedIn;
      end if;
      close cARO_ChIn;

    elsif rRH_pnARO.RH_TO_DATE = rRH_pnRH.RH_FROM_DATE then
      if nvl(lnML_pnRH,0) > 0 then
        raise link_mkt_to_end;
      end if;
      -- update ARO_MOVING_TO
      open  cARO_RightFirst;
      fetch cARO_RightFirst into rARO_RightFirst;
      if cARO_RightFirst%found then
        -- replaced UPDATE with proc call (to also update ARO_AROREF_TO column on autotransfer)
        --update T_ARO set ARO_MOVING_TO = case when rARO.ARO_APREF = rARO_RightFirst.ARO_APREF then 'a:' end || rARO_RightFirst.ARO_APREF
        -- where ARO_CODE = pnARO_Code; -- and ARO_EXP_DEPART = rRH_pnARO.RH_TO_DATE;
        P_ARO_MOVING_TO_UPDATE(pnARO_Code, rARO_RightFirst.ARO_APREF);
      end if;
      close cARO_RightFirst;
      -- extend pnARO_RHREF record and delete pnRH_Code record
      rh_extend(rARO.ARO_RHREF, pnRH_Code);
      rhref_update(pnRH_Code, rARO.ARO_RHREF);
      req_delete(pnRH_Code);
    else
      raise date_range_not_contiguous;
    end if;

  else                          --  UNLINK
	  -- fetch date range of all ARO records under this header
	  open  cARO_Range_ARORH;
	  fetch cARO_Range_ARORH into rARO_Range_ARORH;
	  close cARO_Range_ARORH;
    -- check unlink at end/begin of whole res., determine split day
    if rARO.ARO_EXP_ARRIVE = rARO_Range_ARORH.dMin then
      ldSplit := rARO.ARO_EXP_DEPART;
      lbUnlinkBeg := true;
    elsif rARO.ARO_EXP_DEPART = rARO_Range_ARORH.dMax then
      ldSplit := rARO.ARO_EXP_ARRIVE;
      lbUnlinkBeg := false;
    else
      raise unlink_not_at_begin_or_end;
    end if;

    -- check to split RU record (for now under same RH - update later)
    open  cRU_Split;
    fetch cRU_Split into rRU;
    if cRU_Split%found then  -- don't split RU record anymore - user has to correct or split the requests/credits manually
      raise requested_unit_split;
    end if;
    close cRU_Split;

    -- RU/RH and also determine RH_SOURCE value
    open  cRH_pnARO;
    fetch cRH_pnARO into rRH_pnARO;  -- old RH (date range, ...)
    open  cRU_pnARO;
    fetch cRU_pnARO into rRU;
    if cRU_pnARO%found then
      lcSource := rRU.RU_SOURCE;
    elsif cRH_pnARO%found then
      lcSource := rRH_pnARO.RH_SOURCE; -- keep old value
    else
      lcSource := '#';  -- rare error value (will do no harm in RH, would in RU)
    end if;
    close cRH_pnARO;
    close cRU_pnARO;

    -- prevent to unlink mkt requested unit record (because ML links to it via ML_RHREF)
    if rRU.RU_MLREF is not NULL then
      raise unlink_mkt_from_RH;
    end if;

    
    -- UNLINK BOOKING SECTION:
    -- insert new RH record
    select S_RESERVATION_HEADER_SEQ.nextval into pnRH_Code from dual;
    insert into T_RH (RH_CODE, RH_OWREF, RH_EXT_BOOK_REF, RH_FROM_DATE, RH_TO_DATE,
                      RH_DATE, RH_STATUS, RH_REQUNIT, RH_SOURCE, RH_CBY, RH_CWHEN,
                      RH_ROREF, RH_GAPS, RH_GROUP_ID)
      values (pnRH_Code, rRH_pnARO.RH_OWREF, rRH_pnARO.RH_EXT_BOOK_REF, rARO.ARO_EXP_ARRIVE, rARO.ARO_EXP_DEPART,
              sysdate, rRH_pnARO.RH_STATUS, rRH_pnARO.RH_REQUNIT, lcSource, user, sysdate,
              rARO.ARO_ROREF, 0, rRH_pnARO.RH_GROUP_ID);


    -- update RU_RHREFs (could be two or more RU records)
    if lbUnlinkBeg then                    -- unlink the first apt
      update T_RU set RU_RHREF = pnRH_Code
        where RU_RHREF = rRH_pnARO.RH_CODE
          and RU_FROM_DATE + RU_DAYS <= rARO.ARO_EXP_DEPART;
    else                                   -- unlink the last apt
      update T_RU set RU_RHREF = pnRH_Code
        where RU_RHREF = rRH_pnARO.RH_CODE
          and RU_FROM_DATE >= rARO.ARO_EXP_ARRIVE
          and RU_STATUS <> k.ROCancelled;  -- leave cancelled RUs with intial RH/arrival
    end if;

    -- update ARO_RHREF to move ARO record to newly created RH/header
    update T_ARO set ARO_RHREF = pnRH_Code
      where ARO_CODE = pnARO_Code;

    -- shorten existing RH record and remove auto-transfer (if exists)
    if lbUnlinkBeg then
      update T_RH set RH_FROM_DATE = rARO.ARO_EXP_DEPART
        where RH_CODE = rARO.ARO_RHREF;
      -- update ARO_MOVING_TO (only remove auto-transfer flag if exists)
      update T_ARO set ARO_MOVING_TO = substr(ARO_MOVING_TO, 3)
       where ARO_CODE = pnARO_Code and substr(ARO_MOVING_TO, 1, 2) = 'a:';
      -- reset OnSiteNotOcc status for all the ARO records up to the end of the now second part of the RH
      update T_ARO set ARO_STATUS = k.ROConfirmed
       where ARO_RHREF = rARO.ARO_RHREF and ARO_STATUS = k.ROOnSiteNotOcc;
    else  -- Unlink from the end
      update T_RH set RH_TO_DATE = rARO.ARO_EXP_ARRIVE
        where RH_CODE = rARO.ARO_RHREF;
      -- update ARO_MOVING_TO (only remove auto-transfer flag if exists) for the other AROs under the old header
      update T_ARO set ARO_MOVING_TO = case when substr(ARO_MOVING_TO, 1, 2) = 'a:' then substr(ARO_MOVING_TO, 3)
                                                                                    else ARO_MOVING_TO end
        where ARO_RHREF = rARO.ARO_RHREF and ARO_EXP_DEPART = rARO.ARO_EXP_ARRIVE and ARO_STATUS <> k.ROCancelled;
      -- reset onsite/haveToTransfer ARO_STATUS (if set) for the unlinked ARO
      update T_ARO set ARO_STATUS = k.ROConfirmed
        where ARO_CODE = pnARO_Code and ARO_STATUS = k.ROOnSiteNotOcc;
    end if;

  end if;  -- unlink

  -- proc clean up
  lnStackLen := F_PROC_STACK_OFF(lnStackLen);
  if pcProc <> '_' then
    P_PROC_SET();
    if pnCommit = 1 then
      commit;
    end if;
  end if;

 EXCEPTION
  WHEN date_range_not_contiguous then
    pnRH_Code := -1;
    P_PROC_SET();
    lnStackLen := F_PROC_STACK_OFF(lnStackLen);
    RAISE_APPLICATION_ERROR(-20000,'RESL_APT_LINK: Reservations not linkable, because they are not contiguous (either overlaps or has gaps)! Req1='
                                   || rRH_pnRH.RH_FROM_DATE || '..' || rRH_pnRH.RH_TO_DATE || ', Req2='
                                   || rRH_pnARO.RH_FROM_DATE || '..' || rRH_pnARO.RH_TO_DATE);

  WHEN unlink_not_at_begin_or_end then
    pnRH_Code := -2;
    P_PROC_SET();
    lnStackLen := F_PROC_STACK_OFF(lnStackLen);
    RAISE_APPLICATION_ERROR(-20000,'RESL_APT_LINK: Reservations can only be unlinked from the beginning (' || rARO_Range_ARORH.dMin
                                   || ') or end (' || rARO_Range_ARORH.dMax || ') of the whole reservation date range!');

  WHEN link_different_mkt_leads then
    pnRH_Code := -3;
    P_PROC_SET();
    lnStackLen := F_PROC_STACK_OFF(lnStackLen);
    RAISE_APPLICATION_ERROR(-20000,'RESL_APT_LINK: Reservations based on different Marketing leads (' || lnML_pnARO || ',' || lnML_pnRH
                                   || ') cannot be linked together!');

  WHEN link_mkt_to_end then
    pnRH_Code := -4;
    P_PROC_SET();
    lnStackLen := F_PROC_STACK_OFF(lnStackLen);
    RAISE_APPLICATION_ERROR(-20000,'RESL_APT_LINK: Marketing reservations can only be linked together if either this reservation is the first occupancy '
                                   || 'or if both apartment reservations are based on the same Marketing lead!');

  WHEN requested_unit_split then
    pnRH_Code := -5;
    P_PROC_SET();
    lnStackLen := F_PROC_STACK_OFF(lnStackLen);
    RAISE_APPLICATION_ERROR(-20000,'RESL_APT_LINK: Reservation cannot be unlinked because neither the begin nor the end of the Requested Unit date range ('
                                   || rRU.RU_FROM_DATE || '..' || to_date(rRU.RU_FROM_DATE + rRU.RU_DAYS) || ') is matching the split date ('
                                   || ldSplit || ') of the Apartment reservation. Please first split/correct the Requested Unit record in order '
                                   || 'to start on the ' || ldSplit || ' and then try again to unlink!');

  WHEN unlink_mkt_from_RH then
    pnRH_Code := -6;
    P_PROC_SET();
    lnStackLen := F_PROC_STACK_OFF(lnStackLen);
    RAISE_APPLICATION_ERROR(-20000,'RESL_APT_LINK: You cannot unlink this apartment from this Marketing Request. Please try to unlink the other '
                                   || 'Apartment reservation(s) from the ' || case when lbUnlinkBeg then 'end' else 'begin' end
                                   || ' of the request instead!');

  WHEN cancelled_record then
    pnRH_Code := -7;
    P_PROC_SET();
    lnStackLen := F_PROC_STACK_OFF(lnStackLen);
    RAISE_APPLICATION_ERROR(-20000,'RESL_APT_LINK: Either the request or the apartment reservation got meanwhile cancelled by another user. '
                                   || 'Please first refresh your data and then try again!');

END
/*
  ae:11-07-06 first alpha version (taken from wResView.$[Un]LinkReservation*())
  ae:06-08-06 added RU date range extension on link and added WEEK_REQ on unlink
  ae:20-08-06 RU records not gets changed anymore; pnCommit added; In LINKs now
              always the first (date range) RH record will be extended, check
              and don't allow gaps/overlaps...
  ae:21-08-06 when unlink the new created RH record gets now the status from
              the old one. Also added pldFrom/To to rh_extend().
  ae:10-09-06 split RU record on unlink, fixed some bugs.
  ae:23-09-06 refactored RESL_WEEK_*() parameters
  ae:26-09-06 restricted linking: no RH overlaps allowed - user have first to shorten RH/RU
              else we resulting in double RU records and with the linking/deletion the user
              could erroneously loose a lot of RU data (also deletion code is very complex)
  ae:29-09-06 fixed a UNLINK bug updating RU_AROREF (used lnRU_Code instead of pnARO_Code)
              and now ARO_STATUS gets set back to 200 if 220 (OnSiteNotOccupied)
  ae:03-11-06 now updates also UA_RHREF; added in local procedure rhref_update()
  ae:10-01-07 removed RU_AROREF/RU_APREF
          AND set ARO_STATUS on link with checkedin to 220 (OnSiteNotOccupied)
          AND update UA_RHREF also on unlink.
  ae:18-03-07 removed T_UA.UA_RHREF update (not needed anymore).
  ae:08-04-07 added pnTransGroup, pnAptValue, pcComment parameter to RESL_WEEK_MANAGE call
          AND enhanced the exception error messages.
  ae:19-12-07 cosmetic changes only (changed overlap error message).
  ae:01-12-09 removed debit/RU split (unlink), fixed bug with RU split (unlink) and added Mkt checking (link).
  ae:08-09-09 changed PROC_STACK* calls to use public synonym.
  ae:15-09-11 rh_extend(): merge request comments (RH_REQUNIT) of joined requests together while preventing double comments.
  ae:21-07-13 added update of ARO_MOVING_TO on linkage including automatic auto-transfer option and remove of auto-transfer flag on delinkage.
  ae:25-07-13 replaced UPDATE of ARO_MOVING_TO with P_ARO_MOVING_TO_UPDATE() proc call (to also update ARO_AROREF_TO column on autotransfer).
  ae:04-09-13 removed unused RH_NOADULTS/RH_NOCHILD columns.
  ae:26-02-14 fixed wrong RH_OWREF and missing ext. book ref / group id on UNLINK, detect cancellations and refactored (removed unused CUA cursors;-).
  ae:29-04-14 changed updating table order on UNLINK to prevent error raise in triggers RH_RU_FROM_SYNC/RH_RU_TO_SYNC (before:RH RU ARO now:RU ARO RH)
          AND removed update/overwrite of RU_CDREF (with ARO_CDREF value) on UNLINK.
  ae:14-03-15 fixed bug to reset ARO_STATUS from OnSiteNotOcc to Confirmed also if unlinked from begin of the reservation request/RH (see WO #18341).
  ae:19-02-16 V14: fixed bug to reset ARO_STATUS from OnSiteNotOcc to Confirmed also if unlinked from end of the reservation request/RH (see WO #30481).
  ae:21-02-17 V15: changed order of update from first ARO then RU to first RU then ARO in rhref_update() (in main procedure code was already like this) to fix bug in E_ARO_UPDATE10.sql in the Sihot interface.
*/;
/

create or replace public synonym P_RESL_APT_LINK FOR LOBBY.RESL_APT_LINK;

grant execute on LOBBY.RESL_APT_LINK to SALES_00_MASTER;
grant execute on LOBBY.RESL_APT_LINK to SALES_05_SYSADMIN;
grant execute on LOBBY.RESL_APT_LINK to SALES_06_DEVELOPER;
grant execute on LOBBY.RESL_APT_LINK to SALES_10_SUPERVISOR;
grant execute on LOBBY.RESL_APT_LINK to SALES_30_RESALES;
grant execute on LOBBY.RESL_APT_LINK to SALES_40_COMPLETIONS;
grant execute on LOBBY.RESL_APT_LINK to SALES_49_MKTSUPER;
grant execute on LOBBY.RESL_APT_LINK to SALES_50_MARKETING;
grant execute on LOBBY.RESL_APT_LINK to SALES_52_TELEMARKETING;
grant execute on LOBBY.RESL_APT_LINK to SALES_55_MANAGEMENT;
grant execute on LOBBY.RESL_APT_LINK to SALES_60_RESERVATIONS;
grant execute on LOBBY.RESL_APT_LINK to SALES_70_ACCOUNTING;
grant execute on LOBBY.RESL_APT_LINK to XL_60_RESERVATIONS;

