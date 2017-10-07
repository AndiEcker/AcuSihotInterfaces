create or replace view LOBBY.ACU_RES_DATA -- unfiltered reservation data
  AS
select RU_CODE
     , RU_STATUS
     , RU_RESORT, RU_ATGENERIC
     , RU_FROM_DATE as ARR_DATE, RU_FROM_DATE + RU_DAYS as DEP_DATE
     , RU_ADULTS, RU_CHILDREN
     , RU_RHREF, RU_ROREF
     , RU_FLIGHT_AIRPORT, RU_FLIGHT_NO, to_char(RU_FLIGHT_LANDS, 'HH24:MI:SS') as RU_FLIGHT_LANDS, RU_FLIGHT_PICKUP
     --, RU_BOARDREF                  -- ordered meal plan - no longer needed since we are having RUL_SIHOT_PACK
     , upper(RU_SOURCE) as RU_SOURCE  -- merge member source ('o') with owner source ('O')
     , RU_SIHOT_OBJID
     , RO_RES_GROUP, RO_RES_CLASS, RO_SP_GROUP, RO_SIHOT_RATE
     --, RO_SIHOT_AGENCY_OBJID, RO_SIHOT_AGENCY_MC
     , RO_SIHOT_RES_GROUP, RO_SIHOT_SP_GROUP
     , RH_EXT_BOOK_REF, RH_EXT_BOOK_DATE
     --, RH_FROM_DATE, RH_TO_DATE
     , RH_GROUP_ID
     , RU_CDREF as CD_CODE, CD_CODE2
     , CD_SIHOT_OBJID, CD_SIHOT_OBJID2
     , CD_RCI_REF
     ---- calculated columns
     --, to_char(RU_CODE) as SIHOT_GDSNO -- we have to use RH_EXT_BOOK_REF for Thomas Cook bookings for to be in sync with SihotResImport (this one is not having a RU code) 
     , case when RU_ROREF in ('TK', 'tk') then 'TC' || RH_EXT_BOOK_REF else to_char(RU_CODE) end as SIHOT_GDSNO
     , case when RO_SIHOT_AGENCY_OBJID is not NULL then RO_SIHOT_AGENCY_OBJID
            when RU_CDREF <> RH_OWREF then (select CD_SIHOT_OBJID from T_CD where CD_CODE = RH_OWREF) end as OC_SIHOT_OBJID
     , case when RO_SIHOT_AGENCY_MC is not NULL then RO_SIHOT_AGENCY_MC 
            when RU_CDREF <> RH_OWREF then RH_OWREF end as OC_CODE
     , nvl(RO_SIHOT_MKT_SEG, RU_ROREF) as SIHOT_MKT_SEG
     , trim(case when RU_CDREF <> RH_OWREF then RH_OWREF end
         || case when RU_FROM_DATE <> RH_FROM_DATE or RU_FROM_DATE + RU_DAYS <> RH_TO_DATE 
                 then ' ' || case when RU_FROM_DATE <> RH_FROM_DATE then '<' end || RU_RHREF || case when RU_FROM_DATE + RU_DAYS <> RH_TO_DATE then '>' end end
         || case when RH_GROUP_ID > 0 then ' grp' || RH_GROUP_ID end) as SIHOT_LINK_GROUP
     , replace(replace(replace(RH_REQUNIT, chr(13) || chr(10), '|CR|'), chr(13), '|CR|'), chr(10), '|CR|')
       || case when exists (select NULL from T_RAF where RAF_RUREF = RU_CODE)
               then '|CR|AptFeat: ' || (select listagg(AFT_DESC, ', ') within group (order by AFT_DESC) from T_RAF, T_AFT where RAF_AFTREF = AFT_CODE and RAF_RUREF = RU_CODE) end
       || case when exists (select NULL from T_SR where SR_WHICHTABLE = 'RU' and SR_RDREF = RU_CODE)
               then '|CR|SpecReq: ' || (select listagg(PX_ALPHA, ', ') within group (order by PX_ALPHA) from T_SR, T_PX where SR_PXREF = PX_CODE and SR_WHICHTABLE = 'RU' and SR_RDREF = RU_CODE) end
       as SIHOT_TEC_NOTE
     , ltrim(
       replace(replace(replace(RH_REQUNIT, chr(13), ' '), chr(10), ' '), '  ', ' ')
       || case when exists (select NULL from T_RAF where RAF_RUREF = RU_CODE)
               then ' [Apt.Feat!]' end
       || case when exists (select NULL from T_SR where SR_WHICHTABLE = 'RU' and SR_RDREF = RU_CODE)
               then ' {Special Req!}' end
       )
       as SIHOT_NOTE   -- COMMENT is a reserverd key word for Oracle
     -- with any analytic function the query needs more than 17 minutes on SP.DEV - even with the WHEN CASE optimazation
     --, case when RU_FROM_DATE = RH_FROM_DATE then 1 else dense_rank() over (partition by RU_RHREF order by RU_FROM_DATE) end
     --, case when RU_FROM_DATE = RH_FROM_DATE then 1 else row_number() over (partition by RU_RHREF order by RU_FROM_DATE) end 
     --, RU_CODE  -- no longer needed because we can anyway not have a separate market segment for each requested apt-week (RU)
     --, '0' as SIHOT_ROOM_SEQ
     , case when abs(RU_STATUS) = 120 or RU_RHREF is NULL then 'S'
            --when RU_FROM_DATE > trunc(sysdate) and substr(RO_RES_GROUP, 1, 5) = 'Owner' and RU_RESORT <> 'BHC' then '5'  --- has to be changed if RUL_SIHOT_HOTEL differs
            --when RU_FROM_DATE > trunc(sysdate) and RU_ROREF in ('TK', 'tk') then 'K'   -- or use 'L' 
            else '1' end as SIHOT_RES_TYPE
     --, case when RU_FROM_DATE > trunc(sysdate) and RU_ROREF in ('TK', 'tk') then  case RU_RESORT  when 'BHC' then case RU_ROREF when 'TK' then 11 when 'tk' then 12 end
     --                                                                                             when 'PBC' then case RU_ROREF when 'TK' then 12 when 'tk' then 13 end end 
     --end as SIHOT_ALLOTMENT_NO  -- has to be changed if RUL_SIHOT_HOTEL differs - MEANWHILE CONFIGERED VIA CFG FILE
     --, case when RU_ROREF in ('TK', 'tk') then '1' else '0' end as SIHOT_PAYMENT_INST   -- MEANWHILE CONFIGERED VIA CFG FILE
     , '0' as SIHOT_PAYMENT_INST
     -- optional (now includeed into TEC-COMMENT): requested apartment features and special requests
     --, (select listagg(AFT_DESC, ',') within group (order by AFT_DESC) from T_RAF, T_AFT where RAF_AFTREF = AFT_CODE and RAF_RUREF = RU_CODE) as SIHOT_REQ_APT_FEATURES
     --, (select listagg(PX_ALPHA, ',') within group (order by PX_ALPHA) from T_SR, T_PX where SR_PXREF = PX_CODE and (SR_WHICHTABLE = 'RU' and SR_RDREF = RU_CODE  --or  SR_WHICHTABLE = 'RD' and SR_RDREF = F_ARO_CODE() ))
     --  )) as SIHOT_SPECIAL_REQS
  from T_RU
  inner join T_RO on RU_ROREF = RO_CODE
  inner join V_ACU_CD_DATA on RU_CDREF = CD_CODE
  left outer join T_RH on RU_RHREF = RH_CODE
/*
  ae:12-09-16 first beta for SiHOT migration/sync project.
  ae:27-09-16 V01: added market source groups RO_SIHOT_RES_GROUP/RO_SIHOT_SP_GROUP.
  ae:05-10-16 V02: renamed from V_ACU_RES_CORE to V_ACU_RES_DATA (similar to the V_ACU_CD_* views).
  ae:01-11-16 V03: added new SIHOT_-columns (reservation type, allotment-no, special requests, guest surcharge, apartment features).
  ae:20-09-17 V04: removed most of the hard-coded TK/tk/TC exceptions (now done via cfg settings).
  ae:05-10-17 V05: fixed bug for to cancel Sihot reservation if marketing request set back to pending (changed join to T_RH from inner to left outer and res type to 'S' if RU_RHREF is NULL).  
*/
/


create or replace public synonym V_ACU_RES_DATA for LOBBY.ACU_RES_DATA;

grant select on LOBBY.ACU_RES_DATA to SALES_00_MASTER;
grant select on LOBBY.ACU_RES_DATA to SALES_05_SYSADMIN;
grant select on LOBBY.ACU_RES_DATA to SALES_06_DEVELOPER;
grant select on LOBBY.ACU_RES_DATA to SALES_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_DATA to SALES_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_DATA to XL_00_MASTER;
grant select on LOBBY.ACU_RES_DATA to XL_05_SYSADMIN;
grant select on LOBBY.ACU_RES_DATA to XL_06_DEVELOPER;
grant select on LOBBY.ACU_RES_DATA to XL_10_SUPERVISOR;
grant select on LOBBY.ACU_RES_DATA to XL_60_RESERVATIONS;

grant select on LOBBY.ACU_RES_DATA to REPORTER;

