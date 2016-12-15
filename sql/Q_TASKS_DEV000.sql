--- for Nitesh for to fix the ARO_CHILDREN value after the bug fix in wPassportList
select (select count(*) from t_pa where pa_aoref = aro_code and round(months_between(trunc(aro_timein), pa_dob) / 12) <= 12 )
     , (select f_stragg(pa_firstname || '(' || pa_dob || ')') from t_pa where pa_aoref = aro_code and round(months_between(trunc(aro_timein), pa_dob) / 12) <= 12 )
     , t_aro.* 
  from t_aro
 where 1=1
   and aro_children <> (select count(*) from t_pa where pa_aoref = aro_code and round(months_between(trunc(aro_timein), pa_dob) / 12) <= 12 )
   -- solo para investigar
   and trunc(sysdate) - 1 between aro_timein and aro_exp_depart
   and f_resort(aro_apref) = 'HMC'
   and aro_roref = 'GE'


update t_aro set aro_children = (select count(*) from t_pa where pa_aoref = aro_code and round(months_between(trunc(aro_timein), pa_dob) / 12) <= 12 )
 where 1=1
   and aro_children <> (select count(*) from t_pa where pa_aoref = aro_code and round(months_between(trunc(aro_timein), pa_dob) / 12) <= 12 )


 
select months_between(sysdate, '1-JAN-2016') from dual 



--- SIHOT CD + RES SYNC

select * from t_arol, t_aro
 where arol_primary = aro_code(+)
   and arol_code in (3348806, 3348567, 3348568)
   and not exists (select NULL from T_ARO x where x.ARO_CODE = AROL_PRIMARY and substr(x.ARO_APREF, -3) = '999')
   --and substr(nvl(ARO_APREF(+), '_'), -3) <> '999'

select max(arol_code) from t_arol where not exists (select NULL from t_aro where aro_code = arol_primary)


select * from t_aro where aro_code = 656131

select rh_ext_book_ref, count(*) from t_rh
 where rh_Status <> 120
 group by rh_Ext_book_ref
 having count(*) > 1
 order by count(*) desc


select * from t_lu where lu_class = 'MKT_TO_RESOCC'

select * from t_ct

select * from t_it

select S_OWNER_SEQ.nextval from dual where 1=1

GRANT SELECT ON SALES.OWNER_SEQ TO SALES_00_MASTER;

select * from V_ACU_RES_LOG


select * from V_ACU_RES_UNSYNCED
 where 1=1
   --and instr(aru_rul_changes, 'RU_RESORT') > 0 
   --and aru_rulref is not null and aru_arolref is not null 
   --and aru_user = 'SALES'
   --and aru_mainproc in ('otAPTS', 'wCheckin') --and length(aru_arol_changes) - length(replace(aru_arol_changes, chr(13), '')) > 1
   and instr(aru_arol_changes, 'ARO_APREF') > 0
   
select * from t_arol where arol_code = 3104443 or (substr(arol_changes, 1, 23) = 'ARO_STATUS (300 >> 320)') -- and arol_mainproc is NULL) 
order by arol_code desc

LOG, t_ru, t_rh, t_aro
where 1=1
   and ARL_RUREF = RU_CODE(+) and RU_STATUS(+) <> 120
   and RU_RHREF = RH_CODE(+) and RH_STATUS(+) <> 120
   and ARL_AROREF = ARO_CODE(+) and ARO_STATUS(+) <> 120
   and (ARL_AROL_CHANGES is NULL or ARL_RUL_CHANGES is NULL)


select ARO_EXP_ARRIVE,replace(replace(replace(ARO_NOTE, chr(13) || chr(10), '|CR|'), chr(13), '|CR|'), chr(10), '|CR|'),ARO_EXP_DEPART,ARO_APREF,'ARO_' || ARO_CODE,ARO_CHILDREN,ARO_ROREF,ARO_ADULTS,ARO_CDREF,RH_EXT_BOOK_REF,ARO_STATUS,AROL_CODE,AROL_ACTION,AROL_CHANGES,F_RESORT(ARO_APREF) from T_AROL, T_ARO, T_RH where AROL_PRIMARY = ARO_CODE(+) and ARO_RHREF = RH_CODE(+) and not exists (select NULL from T_ARO x where x.ARO_CODE = AROL_PRIMARY                 and substr(x.ARO_APREF, -3) = '999') and AROL_CODE > 3348574 
and (F_RESORT(ARO_APREF) in ('BHC', 'PBC') or ( instr(AROL_CHANGES, 'ARO_APREF (') > 0 and AROL_ACTION = 'UPDATE' and F_RESORT(substr(AROL_CHANGES, instr(AROL_CHANGES, 'ARO_APREF (') + 12, 3)) in ('BHC', 'PBC') and F_RESORT(substr(AROL_CHANGES, instr(AROL_CHANGES, 'ARO_APREF (') + 19, 3)) not in ('BHC', 'PBC') )) order by AROL_CODE

select max(AROL_CODE) from T_AROL

select ARU_RULREF, ARU_AROLREF, ARU_RSREF,ARU_APREF,ARU_TO_DATE,ARU_FROM_DATE,ARU_EXT_BOOK_REF,ARU_ROREF,'RH__' || ARU_RHREF,ARU_STATUS,ARU_CDREF,ARU_ACTION,replace(replace(replace(ARU_COMMENT, chr(13) || chr(10), '|CR|'), chr(13), '|CR|'), chr(10), '|CR|'),ARU_CHILDREN,ARU_ADULTS from V_ACU_RES_UNSYNCED where 1=1 and (ARU_RSREF in ('PBC') or ( instr(ARU_RUL_CHANGES, 'RU_RESORT (') > 0 and ARU_ACTION = 'UPDATE' and substr(ARU_RUL_CHANGES, instr(ARU_RUL_CHANGES, 'RU_RESORT (') + 12, 3) in ('PBC') and substr(ARU_RUL_CHANGES, instr(ARU_RUL_CHANGES, 'RU_RESORT (') + 19, 3) not in ('PBC') ) or ( instr(ARU_AROL_CHANGES, 'ARO_APREF (') > 0 and ARU_ACTION = 'UPDATE' and F_RESORT(substr(ARU_AROL_CHANGES, instr(ARU_AROL_CHANGES, 'ARO_APREF (') + 12, 3)) in ('PBC') and F_RESORT(substr(ARU_AROL_CHANGES, instr(ARU_AROL_CHANGES, 'ARO_APREF (') + 19, 3)) not in ('PBC') ))
and ARU_RHREF is NULL

select (select f_stragg(ARO_APREF || '=' || ARO_STATUS || '@' || to_char(ARO_EXP_ARRIVE, 'DD-MM')) from T_ARO where ARO_EXP_ARRIVE < DEP_DATE and ARO_EXP_DEPART > ARR_DATE and ARO_RHREF = RHREF and ARO_STATUS <> 120)
     , f_resort(APREF) as APT_RSREF
     , v_acu_res_unsynced.* 
  from v_acu_res_unsynced
 where F_RESORT(APREF) <> RSREF 
 --where aru_arolref = 3300515
 --where instr(action, ' ') > 0
 --where status <> -120
 --where apref is null and arr_date < trunc(sysdate) and STATUS <> 120
   --and exists (select NULL from T_ARO where ARO_EXP_ARRIVE < DEP_DATE and ARO_EXP_DEPART > ARR_DATE and ARO_RHREF = RHREF and ARO_STATUS <> 120)
 order by arl_date desc

select f_resort(NULL) from dual

select * from v_acu_cd_unsynced
 order by acl_date desc


select nvl(LU_CHAR, (select LU_CHAR from T_LU where LU_CLASS = 'SIHOT_CATS_ANY' and LU_ID = '1 BED'))
      from T_LU where LU_CLASS = 'SIHOT_CATS_HMC' and LU_ID = '1 BED'


select LU_CHAR from T_LU where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_HMC' and LU_ID = '1 BED') then 'SIHOT_CATS_HMC' else 'SIHOT_CATS_ANY' end and LU_ID = '1 BED'  

--!!! pseudo clients with >100 requested units, :requests/cancelled (get numbers of requested/cancelled unit recs with query underneath)
--E578974:1385 / 270=Silverpoint Usage 2017 (2=2014...7=2020)
--E578975:1269 / 62=Silverpoint Usage 2018
--E578973: 880 / 471=Silverpoint Usage 2016
--E420545: 371 / 27=Reforma Reforma (~330 Arr<5.7.16 - checked on 23.7.)
--E558549: 167 / 83=Inventory Disney (8 Arr:12.8.-30.12.16)
--E599377: 130 / 0=Fx Vuelo (~180 Arr:6.5.-23.6.16)
--A444440: 122 / 2=RCI Customer Service Registry Collection (CPA) (~130 Reqs-noAROs! all year)
--E590653: 118 / 0=Vuelo Fx (~120 Arr:Feb-May/Jun)
--E422190: 114 / 49=Showflat Showflat (~60 all year)
--E584853: 104 / 0=Vuelo Fx (~110 Arr:Feb-May)
--!!! power clients
--E201327:  77 / 24=Keith&MagAnn Oliver (Dec-Mar, 17! TO/PBC)
--G032598:  66 / 36=Mircea Caranfil (10 TO/HMC)
--E465813:  63 / 6=Reforma cuarto de baño (~30 MA, Apr-Jun)
--Z006723:  58 / 38=Christopher Robin Searle (8 TO/PBC)
--E401893:  55 / 53=To Resort Units Conf Bank 
--B583954:  54 / 6=Asoc. Los Amigoelos (RR=BookingButton, Wk1-16)
--Z134704:  51 / 20=Harold R Bennet (10 TO/PBC)
--Z002671:  47 / 36=Sheila Mildred Harrower (5 TO/PBT)
--Z009834:  47 / 16=Annarosa Scardovi Sala (5 TO/PBC)
--E584097:  46 / 0=Vuelo Desvio Vuelo (15 Arr:Jan)

select ru_cdref, count(*), sum(case when ru_status = 120 then 1 end) from t_ru
 where ru_from_date + ru_days > '01-JAN-2016'
 group by ru_cdref
 order by count(*) desc
 
 
with resorts as (select RS_CODE from T_RS union all select 'ANY' from dual)
select * from V_ACU_RES_LOG
  left outer join T_RU on ARL_RUREF = RU_CODE
  left outer join T_RH on RU_RHREF = RH_CODE  
 where nvl(RU_FROM_DATE + RU_DAYS, ARL_DATE) >= '01-JAN-2016' -- speed-up: removing old reservation requests (before 2016)
   and ( RU_RESORT in (select RS_CODE from resorts)
      or (instr(ARL_RUL_CHANGES, 'RU_RESORT (') > 0 and ARL_ACTION = 'UPDATE'
          and ( substr(ARL_RUL_CHANGES, instr(ARL_RUL_CHANGES, 'RU_RESORT (') + 11, 3) in (select RS_CODE from resorts)
             or substr(ARL_RUL_CHANGES, instr(ARL_RUL_CHANGES, 'RU_RESORT (') + 18, 3) in (select RS_CODE from resorts) )) )
   and not exists (select NULL from T_SRSL where SRSL_TABLE = 'RU' and SRSL_PRIMARY = ARL_RUREF and substr(SRSL_STATUS, 1, 6) = 'SYNCED' and SRSL_DATE > ARL_DATE)
   and RU_CODE is null

-- these 2300 RULs are not included into ARU because of the RU_FROM_DATE filter
select * from t_rul, t_ru 
 where rul_primary = ru_code(+)
   and rul_code between 2570701 and 2573305
 order by rul_code

select * from t_aro where aro_code = 646266

select * from t_srsl 
 where 1=1
   --and substr(srsl_status, 1, 3) = 'ERR'
   --and srsl_message is not Null
 order by srsl_date desc


select ru_resort, count(*) from t_ru
 where ru_resort not in (select RS_CODE from T_RS)
 group by ru_resort
 order by count(*) desc
 
select ap_code, f_resort(ap_code), f_resort(ap_code, 'C') from t_ap where ap_code like '%999'



select RUL_CODE as ARL_RULREF
     , RUL_USER as ARL_USER, RUL_ACTION as ARL_ACTION, RUL_MAINPROC as ARL_MAINPROC, RUL_DATE as ARL_DATE
     , RUL_PRIMARY as ARL_RUREF, RUL_CHANGES as ARL_RUL_CHANGES
  
  
select * from T_RUL
 where upper(RUL_MAINPROC) in ('WCHECKIN') -- remove Acumen LOBBY actions
   and RUL_MAINPROC not in ('wCheckIn', 'wCheckin')
   
   
   and RUL_DATE >= '01-JAN-2016'
   


-- V_ACU_CD_UNSYNCED

select * from V_ACU_CD_UNSYNCED

 where cd_code is null
 

select * from T_SRSL
 where 1=1
   --and substr(srsl_status, 1, 3) = 'ERR'


select * --CD_EMAIL,CD_TYPE,CD_PASSWORD,CD_MOBILE1,CD_POSTAL,CD_WEXT1,CD_SIGNUP_EMAIL,COUNTRY,CD_ADD11,CD_LGREF,CD_LAST_SMS_TEL,CD_DOB1,CD_STATUS,1,CD_PAF_STATUS,CD_FNAM1,CD_WTEL1,CD_CITY,CD_HTEL1,CD_CODE,CD_SNAM1,CD_POSTAL,CD_TITL1,CD_FAX
  from V_ACU_CD_UNSYNCED 
 --where CD_CODE like 'E392032'

select * from t_cd where
 --cd_code = 'E128745'
 cd_sihot_objid is not null
--CD_CODE = 'E605832'

select * from t_ru
 where ru_sihot_objid is not null
 order by ru_sihot_objid


 
select * from V_ACU_RES_UNSYNCED where CDREF like 'E578973' -- and CDREF is not NULL

select RU_SIHOT_OBJID,CD_SIHOT_OBJID as CD1,CD_SIHOT_OBJID as CD1,1 as SH_NOROOMS,SIHOT_CAT,SIHOT_HOTEL,SIHOT_ROOM,ARR_DATE,DEP_DATE,ADULTS + CHILDREN as PAX,replace(replace(replace(NOTE, chr(13) || chr(10), '|CR|'), chr(13), '|CR|'), chr(10), '|CR|') as NOTE,ROREF,'RU__' || RU_CODE as SH_GDSNO,EXT_BOOK_REF,ACTION,STATUS,RULREF,RU_CODE,CDREF from V_ACU_RES_UNSYNCED where CDREF like 'E578973'


select CD_CODE,nvl(RO_SIHOT_AGENCY_OBJID, CD_SIHOT_OBJID) as SH_OBJID,1 as SH_NOROOMS,RUL_SIHOT_CAT,RU_SIHOT_CAT,RUL_SIHOT_HOTEL,RUL_SIHOT_ROOM,ARR_DATE,DEP_DATE,RU_ADULTS,RU_CHILDREN,replace(replace(replace(NOTE, chr(13) || chr(10), '|CR|'), chr(13), '|CR|'), chr(10), '|CR|') as NOTE,RU_ROREF,'RU__' || RU_CODE as SH_GDSNO,RH_EXT_BOOK_REF,CD_CODE2 as SH_CDREF2,RUL_ACTION,SIHOT_STATUS,nvl((select max(RUL_CODE) from T_RUL where RUL_PRIMARY = RU_CODE), 0) as RUL_CODE,RU_CODE,RU_SIHOT_OBJID,CD_SIHOT_OBJID from V_ACU_RES_UNFILTERED where CD_CODE like 'N532290'

select * from T_RU where RU_STATUS <> 120 and RU_CDREF = 'N532290'

select RU_RHREF, ru_from_date from t_ru where ru_status <> 120 and ru_rhref = NULL group by ru_rhref, ru_from_date having count(*) > 1


select CD_CODE,nvl(RO_SIHOT_AGENCY_OBJID, CD_SIHOT_OBJID) as SH_OBJID,'RH__' || RU_RHREF as SH_GDSNO,RH_EXT_BOOK_REF,RH_GROUP_ID as SH_EXT_KEY,'IGNORE-OVERBOOKING;NO-FALLBACK-TO-ERRONEOUS' as SH_FLAGS,case when RU_ROREF in ('TK', 'tk') then 'K' else '1' end as SH_RES_TYPE,RUL_SIHOT_CAT,RU_SIHOT_CAT,nvl(RO_SIHOT_RATE, RU_ROREF) as RO_SIHOT_RATE,'Y' as SH_RATE_Y,'0' as SH_PAYMENT_INST,RUL_SIHOT_HOTEL,RUL_SIHOT_ROOM,ARR_DATE,DEP_DATE,1 as SH_NOROOMS,RU_ADULTS,RU_CHILDREN,replace(replace(replace(NOTE, chr(13) || chr(10), '|CR|'), chr(13), '|CR|'), chr(10), '|CR|') as NOTE,RU_ROREF,RU_SOURCE,RO_RES_GROUP,' ' || RU_FLIGHT_PICKUP || ' ' || RU_FLIGHT_AIRPORT || RU_FLIGHT_NO as SH_EXT_REF,RU_FLIGHT_LANDS,RU_FLIGHT_LANDS,CD_CODE as SH_CDREF1,CD_SIHOT_OBJID as SH_OBJID2,RU_CODE as SH_ROOM_SEQ,0 as SH_PERS_SEQ,CD_CODE2 as SH_CDREF2,CD_SIHOT_OBJID2 as SH_OBJID2,RU_CODE as SH_ROOM_SEQ2,1 as SH_PERS_SEQ2,RUL_ACTION,nvl(RU_STATUS, 120) as RU_STATUS,RUL_CODE,RU_CODE,RU_SIHOT_OBJID,CD_SIHOT_OBJID 

select * from V_ACU_RES_UNFILTERED

 where CD_CODE = 'N532290';

select * from T_RUL where RUL_MAINPROC in ('wCheckIn', 'wCheckin') -- remove Acumen LOBBY actions
order by rul_date desc


select REGEXP_SUBSTR('test', '[^,]+', 1, 1), ext_refs from V_ACU_CD_DATA where CD_CODE like 'E396693'


update t_cd set cd_sihot_objid = NULL where cd_sihot_objid <= 294

-- count==390859
select --CD_SIHOT_OBJID,CD_SIHOT_OBJID2,CD_CODE,CD_CODE2,SIHOT_SALUTATION1,SIHOT_SALUTATION2,SIHOT_TITLE1,SIHOT_TITLE2,SIHOT_GUESTTYPE1,SIHOT_GUESTTYPE2,CD_SNAM1,CD_SNAM2,CD_FNAM1,CD_FNAM2,CD_ADD11,nvl(CD_ADD12, CD_ADD13) as CD_ADD12,CD_POSTAL,CD_CITY,SIHOT_COUNTRY,SIHOT_LANG,SIHOT_GUEST_TYPE || ' ExtRefs=' || EXT_REFS as SH_COMMENT,CD_HTEL1,CD_WTEL1,CD_FAX,CD_WEXT1,CD_EMAIL,CD_SIGNUP_EMAIL,CD_MOBILE1,CD_LAST_SMS_TEL,'1A' as SH_PTYPE,CD_DOB1,CD_DOB2,CD_INDUSTRY1,CD_INDUSTRY2,CD_PASSWORD,substr(EXT_REFS, 1, instr(EXT_REFS, '=') - 1) as EXT_REF_TYPE1,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 1), '[^=]+', 1, 2) as EXT_REF_ID1,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 2), '[^=]+', 1, 1) as EXT_REF_TYPE2,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 2), '[^=]+', 1, 2) as EXT_REF_ID2,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 3), '[^=]+', 1, 1) as EXT_REF_TYPE3,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 3), '[^=]+', 1, 2) as EXT_REF_ID3,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 4), '[^=]+', 1, 1) as EXT_REF_TYPE4,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 4), '[^=]+', 1, 2) as EXT_REF_ID4,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 5), '[^=]+', 1, 1) as EXT_REF_TYPE5,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 5), '[^=]+', 1, 2) as EXT_REF_ID5,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 6), '[^=]+', 1, 1) as EXT_REF_TYPE6,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 6), '[^=]+', 1, 2) as EXT_REF_ID6,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 7), '[^=]+', 1, 1) as EXT_REF_TYPE7,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 7), '[^=]+', 1, 2) as EXT_REF_ID7,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 8), '[^=]+', 1, 1) as EXT_REF_TYPE8,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 8), '[^=]+', 1, 2) as EXT_REF_ID8,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 9), '[^=]+', 1, 1) as EXT_REF_TYPE9,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 9), '[^=]+', 1, 2) as EXT_REF_ID9,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 10), '[^=]+', 1, 1) as EXT_REF_TYPE10,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 10), '[^=]+', 1, 2) as EXT_REF_ID10,EXT_REFS,LOG_CODE,CD_STATUS,CD_PAF_STATUS 
 count(*) from V_ACU_CD_UNSYNCED where 1=1

-- count=391073
select count(*) from t_cd

SELECT USERENV ('language') FROM DUAL 

select * from t_cd where cd_code = 'E003378' -- no CD_SNAM1/FNAM1

select * from t_cd where cd_code like 'R222193'

select * from t_cd where cd_sihot_objid is not null

select * from t_log where log_primary = 'R222193' order by log_code desc

update t_cd set CD_SIHOT_OBJID = NULL, CD_SIHOT_OBJID2 = NULL where CD_CODE = 'R222193'



-- strange AP_CODE(7) but ARO_ARPREF(10) and there is one rec with length 8 - ARO=41832  -- similar size discrepancy with CUA_WKREF and WK_CODE
delete from t_aro where aro_code = 41832
select * from t_cua where not exists (select NULL from t_wk where wk_code = cua_wkref) --- ahhh because of the old PBHC memberships



select * from t_ru where ru_code = 999014

select * from t_ap where ap_sihot_cat = 'STPR'

update t_ap set ap_sihot_cat = 'STIC' where ap_sihot_cat = 'STPR'

select * from t_ap where ap_sihot_hotel = 0


select * from t_rul where rul_sihot_cat = 'STPR'

update t_rul set rul_sihot_cat = 'STIC' where rul_sihot_cat = 'STPR'

select * from t_rul where rul_sihot_hotel = 0

update t_rul set rul_sihot_hotel = 999 where rul_sihot_hotel = 0


-- count(*) doesn't show overflow error and results in 101267 records (plus the ~400 already migrated ones)
select * --CD_CODE,nvl(RO_SIHOT_AGENCY_OBJID, CD_SIHOT_OBJID) as SH_OBJID,RU_RHREF || '/' || RU_CODE as SH_GDSNO,RH_EXT_BOOK_REF,case when RH_GROUP_ID > 0 then 'Grp' || RH_GROUP_ID end as SH_GROUP_ID,case when RU_ROREF in ('TK', 'tk') then 'K' else '1' end as SH_RES_TYPE,RUL_SIHOT_CAT,RU_SIHOT_CAT,RUL_SIHOT_PACK as SH_SIHOT_PACK,RUL_SIHOT_HOTEL,SIHOT_ROOM_NO,ARR_DATE,DEP_DATE,RU_ADULTS + RU_CHILDREN as SH_PAX,RU_CHILDREN,NOTE,RU_ROREF,RU_SOURCE,RO_RES_GROUP,RO_SP_GROUP,trim(' ' || RU_FLIGHT_PICKUP || ' ' || RU_FLIGHT_AIRPORT || RU_FLIGHT_NO) as SH_EXT_REF,RU_FLIGHT_LANDS,RU_FLIGHT_LANDS,RU_ADULTS,RU_CHILDREN,CD_CODE as SH_CDREF1,CD_SIHOT_OBJID as SH_CD_OBJID1,SIHOT_ROOM_SEQ,RUL_SIHOT_PACK as SH_SIHOT_PACK1,CD_CODE2 as SH_CDREF2,CD_SIHOT_OBJID2 as SH_CD_OBJID2,SIHOT_ROOM_SEQ,RUL_SIHOT_PACK as SH_SIHOT_PACK2,'Pax ' || case when CD_CODE2 is NULL then '2' else '3' end as SH_PAX3_NAME,SIHOT_ROOM_SEQ,case when CD_CODE2 is NULL then '1' else '2' end as SH_PERS_SEQ3,RUL_SIHOT_PACK as SH_SIHOT_PACK3,'Pax ' || case when CD_CODE2 is NULL then '3' else '4' end as SH_PAX4_NAME,SIHOT_ROOM_SEQ,case when CD_CODE2 is NULL then '2' else '3' end as SH_PERS_SEQ4,RUL_SIHOT_PACK as SH_SIHOT_PACK4,RUL_ACTION,nvl(RU_STATUS, 120) as RU_STATUS,RUL_CODE,RU_CODE,RU_SIHOT_OBJID,RU_FLIGHT_PICKUP,RO_SIHOT_AGENCY_OBJID,CD_CODE2,CD_SIHOT_OBJID,CD_SIHOT_OBJID2 
from V_ACU_RES_UNSYNCED --where 1=1

select * --CD_CODE,nvl(RO_SIHOT_AGENCY_OBJID, CD_SIHOT_OBJID) as SH_OBJID,RU_RHREF || '/' || RU_CODE as SH_GDSNO,RH_EXT_BOOK_REF,case when RH_GROUP_ID > 0 then 'Grp' || RH_GROUP_ID end as SH_GROUP_ID,case when RU_ROREF in ('TK', 'tk') then 'K' else '1' end as SH_RES_TYPE,RUL_SIHOT_CAT,RU_SIHOT_CAT,RUL_SIHOT_PACK as SH_SIHOT_PACK,RUL_SIHOT_HOTEL,SIHOT_ROOM_NO,ARR_DATE,DEP_DATE,RU_ADULTS + RU_CHILDREN as SH_PAX,RU_CHILDREN,NOTE,RU_ROREF,RU_SOURCE,RO_RES_GROUP,RO_SP_GROUP,trim(' ' || RU_FLIGHT_PICKUP || ' ' || RU_FLIGHT_AIRPORT || RU_FLIGHT_NO) as SH_EXT_REF,RU_FLIGHT_LANDS,RU_FLIGHT_LANDS,RU_ADULTS,RU_CHILDREN,CD_CODE as SH_CDREF1,CD_SIHOT_OBJID as SH_CD_OBJID1,SIHOT_ROOM_SEQ,RUL_SIHOT_PACK as SH_SIHOT_PACK1,CD_CODE2 as SH_CDREF2,CD_SIHOT_OBJID2 as SH_CD_OBJID2,SIHOT_ROOM_SEQ,RUL_SIHOT_PACK as SH_SIHOT_PACK2,'Pax ' || case when CD_CODE2 is NULL then '2' else '3' end as SH_PAX3_NAME,SIHOT_ROOM_SEQ,case when CD_CODE2 is NULL then '1' else '2' end as SH_PERS_SEQ3,RUL_SIHOT_PACK as SH_SIHOT_PACK3,'Pax ' || case when CD_CODE2 is NULL then '3' else '4' end as SH_PAX4_NAME,SIHOT_ROOM_SEQ,case when CD_CODE2 is NULL then '2' else '3' end as SH_PERS_SEQ4,RUL_SIHOT_PACK as SH_SIHOT_PACK4,RUL_ACTION,nvl(RU_STATUS, 120) as RU_STATUS,RUL_CODE,RU_CODE,RU_SIHOT_OBJID,RU_FLIGHT_PICKUP,RO_SIHOT_AGENCY_OBJID,CD_CODE2,CD_SIHOT_OBJID,CD_SIHOT_OBJID2 
from V_ACU_RES_LOG where 1=1


-- changed oracle number columns size to prevent OCI-22053 overflow error (in TOAD ORA-01455: converting column overlows integer datatype)

--ALTER TABLE LOBBY.SIHOT_RES_SYNC_LOG MODIFY(SRSL_LOGREF NUMBER(10));
alter table LOBBY.SIHOT_RES_SYNC_LOG rename column SRSL_LOGREF to C_OLD;
alter table LOBBY.SIHOT_RES_SYNC_LOG add SRSL_LOGREF NUMBER(10);
update LOBBY.SIHOT_RES_SYNC_LOG set SRSL_LOGREF = C_OLD;
commit;
alter table LOBBY.SIHOT_RES_SYNC_LOG drop column C_OLD;


--alter table LOBBY.REQUESTED_UNIT_LOG modify (RUL_SIHOT_OBJID NUMBER(9));
alter table LOBBY.REQUESTED_UNIT_LOG rename column RUL_SIHOT_OBJID to C_OLD;
alter table LOBBY.REQUESTED_UNIT_LOG add RUL_SIHOT_OBJID NUMBER(9);
update LOBBY.REQUESTED_UNIT_LOG set RUL_SIHOT_OBJID = C_OLD;
commit;
alter table LOBBY.REQUESTED_UNIT_LOG drop column C_OLD;


--alter table LOBBY.REQUESTED_UNIT modify (RU_SIHOT_OBJID      NUMBER(9));
alter table LOBBY.REQUESTED_UNIT rename column RU_SIHOT_OBJID to C_OLD;
alter table LOBBY.REQUESTED_UNIT add RU_SIHOT_OBJID NUMBER(9);
update LOBBY.REQUESTED_UNIT set RU_SIHOT_OBJID = C_OLD;
commit;
alter table LOBBY.REQUESTED_UNIT drop column C_OLD;


--alter table LOBBY.RESOCC_TYPES modify (RO_SIHOT_AGENCY_OBJID      NUMBER(9));
alter table LOBBY.RESOCC_TYPES rename column RO_SIHOT_AGENCY_OBJID to C_OLD;
alter table LOBBY.RESOCC_TYPES add RO_SIHOT_AGENCY_OBJID NUMBER(9);
update LOBBY.RESOCC_TYPES set RO_SIHOT_AGENCY_OBJID = C_OLD;
commit;
alter table LOBBY.RESOCC_TYPES drop column C_OLD;


--alter table SALES.CLIENT_DETAILS modify (CD_SIHOT_OBJID    NUMBER(9));
alter table SALES.CLIENT_DETAILS rename column CD_SIHOT_OBJID to C_OLD;
alter table SALES.CLIENT_DETAILS add CD_SIHOT_OBJID NUMBER(9);
update SALES.CLIENT_DETAILS set CD_SIHOT_OBJID = C_OLD;
commit;
alter table SALES.CLIENT_DETAILS drop column C_OLD;


--alter table SALES.CLIENT_DETAILS modify (CD_SIHOT_OBJID2   NUMBER(9));
alter table SALES.CLIENT_DETAILS rename column CD_SIHOT_OBJID2 to C_OLD;
alter table SALES.CLIENT_DETAILS add CD_SIHOT_OBJID2 NUMBER(9);
update SALES.CLIENT_DETAILS set CD_SIHOT_OBJID2 = C_OLD;
commit;
alter table SALES.CLIENT_DETAILS drop column C_OLD;


-- ALREADY On SP.WORLD -------------

--alter table LOBBY.REQUESTED_UNIT modify (RU_ATTYPEVALUE   NUMBER(9));
--select max(RU_ATTYPEVALUE) from T_RU -- 60

alter table LOBBY.REQUESTED_UNIT rename column RU_ATTYPEVALUE to C_OLD;
alter table LOBBY.REQUESTED_UNIT add RU_ATTYPEVALUE NUMBER(3);

update LOBBY.REQUESTED_UNIT set RU_ATTYPEVALUE = C_OLD where C_OLD is not NULL;

commit;

alter table LOBBY.REQUESTED_UNIT drop column C_OLD;

COMMENT ON COLUMN LOBBY.REQUESTED_UNIT.RU_ATTYPEVALUE IS 'Apt Type Value weighting';


--alter table LOBBY.RESERVATION_HEADER modify (RH_GROUP_ID   NUMBER(9));
alter table LOBBY.RESERVATION_HEADER rename column RH_GROUP_ID to C_OLD;
alter table LOBBY.RESERVATION_HEADER add RH_GROUP_ID NUMBER(9);
update LOBBY.RESERVATION_HEADER set RH_GROUP_ID = C_OLD where C_OLD is not NULL;
commit;
alter table LOBBY.RESERVATION_HEADER drop column C_OLD;

COMMENT ON COLUMN LOBBY.RESERVATION_HEADER.RH_GROUP_ID is 'Same ID/sequence number for grouped requests (Family, travel group, ...)';


-- sync tests

select LU_ID as RS_CODE from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ACTIVE = 1


select * from V_ACU_CD_DATA where cd_code = 'Z001114'

select * from 

edit t_ru a --where --ru_from_date > sysdate and 
 where ru_children > 2 and ru_rhref is not null
 and exists (select NULL from V_ACU_RES_UNSYNCED b where b.RU_CODE = a.RU_CODE) 
order by ru_children desc

-- 182103 records on DEV, after refact: 151597 -- also correct on split with: and RU_CODE >= 1018389 -- 180046 are less/equal and 2058 are greater/equal
-- .. but with cx_Oracle I get different row counts: 307594, 308042, 307719, after refact: 154300 ...
-- changed RU 1018389 from ANY to BHC
select count(*) from V_ACU_RES_UNSYNCED 

select * from V_ACU_RES_UNSYNCED where 1=1 --RU_CODE = 1025884

select RUL_CODE, to_char(RUL_SIHOT_HOTEL) as HOT, CD_CODE,to_char(nvl(RO_SIHOT_AGENCY_OBJID, CD_SIHOT_OBJID)) as SH_OBJID,RU_RHREF || '/' || RU_CODE as SH_GDSNO,RH_EXT_BOOK_REF,case when RH_GROUP_ID > 0 then 'Grp' || RH_GROUP_ID end as SH_GROUP_ID,case when RU_ROREF in ('TK', 'tk') then 'K' else '1' end as SH_RES_TYPE,RUL_SIHOT_CAT,RU_SIHOT_CAT,RUL_SIHOT_PACK,SIHOT_HOTEL_C,SIHOT_ROOM_NO,ARR_DATE,DEP_DATE,RU_ADULTS,RU_CHILDREN,NOTE,SIHOT_MKT_SEG,RU_SOURCE,RO_SIHOT_SP_GROUP,RO_SIHOT_RES_GROUP,RO_RES_CLASS,trim(' ' || RU_FLIGHT_PICKUP || ' ' || RU_FLIGHT_AIRPORT || RU_FLIGHT_NO) as SH_EXT_REF,RU_FLIGHT_LANDS,RU_FLIGHT_LANDS,RU_ADULTS,RU_CHILDREN,CD_CODE as SH_CDREF1,CD_SIHOT_OBJID as SH_CD_OBJID1,SIHOT_ROOM_SEQ,RUL_SIHOT_PACK,CD_CODE2 as SH_CDREF2,CD_SIHOT_OBJID2 as SH_CD_OBJID2,SIHOT_ROOM_SEQ,RUL_SIHOT_PACK,'Adult ' || case when CD_CODE2 is NULL then '2' else '3' end as SH_PAX3_NAME,SIHOT_ROOM_SEQ,case when CD_CODE2 is NULL then '1' else '2' end as SH_PERS_SEQ3,RUL_SIHOT_PACK,'Adult ' || case when CD_CODE2 is NULL then '3' else '4' end as SH_PAX4_NAME,SIHOT_ROOM_SEQ,case when CD_CODE2 is NULL then '2' else '3' end as SH_PERS_SEQ4,RUL_SIHOT_PACK,'Adult ' || case when CD_CODE2 is NULL then '4' else '5' end as SH_PAX5_NAME,SIHOT_ROOM_SEQ,case when CD_CODE2 is NULL then '3' else '4' end as SH_PERS_SEQ5,RUL_SIHOT_PACK,'Adult ' || case when CD_CODE2 is NULL then '5' else '6' end as SH_PAX6_NAME,SIHOT_ROOM_SEQ,case when CD_CODE2 is NULL then '4' else '5' end as SH_PERS_SEQ6,RUL_SIHOT_PACK,SIHOT_ROOM_SEQ,RUL_SIHOT_PACK,SIHOT_ROOM_SEQ,RUL_SIHOT_PACK,SIHOT_ROOM_SEQ,RUL_SIHOT_PACK,SIHOT_ROOM_SEQ,RUL_SIHOT_PACK,RUL_ACTION,RU_STATUS,RUL_CODE,RU_CODE,RU_SIHOT_OBJID,RU_FLIGHT_PICKUP,RO_SIHOT_AGENCY_OBJID,CD_CODE2,CD_SIHOT_OBJID,CD_SIHOT_OBJID2 from V_ACU_RES_UNSYNCED where 1=1

select RUL_CODE, RU_CODE, to_char(RUL_SIHOT_HOTEL) as HOT, SIHOT_HOTEL_C from V_ACU_RES_UNSYNCED where 1=1

select * from V_ACU_RES_DATA where RU_CODE = 1025884

select * from V_ACU_RES_LOG 
--t_rul
 where RUL_PRIMARY = 1025884

edit t_rul where rul_primary = 1025884 order by rul_code

select nvl(F_SIHOT_CAT(nvl(RUL_SIHOT_ROOM, (select RU_ATGENERIC || '@' || RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY))), 'STIC') as RUL_SIHOT_CAT,
                 nvl(F_SIHOT_HOTEL(nvl(RUL_SIHOT_ROOM, (select RU_ATGENERIC || '@' || RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY))), 999) as RUL_SIHOT_HOTEL,
                 case when F_SIHOT_PACK((select PRC_BOARDREF1 from T_RU, T_ML, T_MS, T_PRC where RU_MLREF = ML_CODE and ML_CODE = MS_MLREF and MS_PRCREF = PRC_CODE and RU_CODE = RUL_PRIMARY), 'MKT_') != 'RO' 
                                       then F_SIHOT_PACK((select PRC_BOARDREF1 from T_RU, T_ML, T_MS, T_PRC where RU_MLREF = ML_CODE and ML_CODE = MS_MLREF and MS_PRCREF = PRC_CODE and RU_CODE = RUL_PRIMARY), 'MKT_')
                                       --else F_SIHOT_PACK(nvl((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS) from T_RU where RU_CODE = RUL_PRIMARY),
                                       --                      (select RU_BOARDREF from T_RU where RU_CODE = RUL_PRIMARY)))
                                       when (select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS) from T_RU where RU_CODE = RUL_PRIMARY) != 'RO'
                                       then F_SIHOT_PACK((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS) from T_RU where RU_CODE = RUL_PRIMARY))
                                       else F_SIHOT_PACK((select RU_BOARDREF from T_RU where RU_CODE = RUL_PRIMARY)) 
                                       end as RUL_SIHOT_PACK
     , RU_RESORT, RU_ATGENERIC
 from T_RUL, T_RU
 where RUL_PRIMARY = RU_CODE
   and exists (select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ID = (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY))
   and (select RU_ATGENERIC from T_RU where RU_CODE = RUL_PRIMARY) is not NULL
   and RUL_CODE = 4552688


--select * from t_ru where RU_CODE = 1018389


select * from t_ro where ro_sihot_agency_objid = 9141

select * from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ACTIVE = 1

edit t_lu where lu_class = 'SIHOT_HOTELS'



with resorts as (select LU_ID as RS_CODE from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ACTIVE = 1),
     resoccs as (select RO_SIHOT_RATE from T_RO where RO_SIHOT_RATE is not NULL)
select substr(RUL_CHANGES, instr(RUL_CHANGES, 'RU_RESORT (') + 11, 3), T_RUL.* from T_RUL 
 where ( RUL_ACTION <> 'DELETE' and substr(RUL_CHANGES, instr(RUL_CHANGES, 'RU_RESORT (') + 11, 3) in (select RS_CODE from resorts) )
   --and exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY)

select * from t_ro where ro_code <> ro_sihot_rate

-- 18:26 minutes to fetch no rows
select * from v_acu_res_unsynced --where ru_resort not in ('ANY', 'BHC', 'PBC')


-- check requested apartment for to determine correct room category for TK reservations
select * from t_ru, t_raf, t_aft
 where ru_code = raf_ruref and raf_aftref = aft_code
   and ru_roref = 'TK'
 order by ru_from_date desc



-- check test_sxmlif.py values

select * from t_cd where cd_code = 'E226360'

select * from v_acu_cd_log where log_primary = 'E610488'

select * from t_log where log_primary = 'E436263'

select * from v_acu_cd_data where cd_code = 'E436263'
   and not ( upper(substr(nvl(CD_CITY, '_'), 1, 2)) = 'LC' or upper(nvl(CD_CITY, '_')) in ('X', 'XX', 'XXX', 'XXXX', 'XXXXX', 'XXXXXX') or (CD_ADD11 is NULL and CD_ADD12 is NULL and CD_ADD13 is NULL and CD_POSTAL is NULL and CD_CITY is NULL) )


select * from v_acu_cd_unsynced --where cd_code = 'E436263'

select CD_SIHOT_OBJID,CD_SIHOT_OBJID2,CD_CODE,CD_CODE2,SIHOT_SALUTATION1,SIHOT_SALUTATION2,SIHOT_TITLE1,SIHOT_TITLE2,SIHOT_GUESTTYPE1,SIHOT_GUESTTYPE2,CD_SNAM1,CD_SNAM2,CD_FNAM1,CD_FNAM2,CD_ADD11,nvl(CD_ADD12, CD_ADD13) as CD_ADD12,CD_POSTAL,CD_CITY,SIHOT_COUNTRY,SIHOT_LANG,SIHOT_GUEST_TYPE || ' ExtRefs=' || EXT_REFS as SH_COMMENT,CD_HTEL1,CD_WTEL1,CD_FAX,CD_WEXT1,CD_EMAIL,CD_SIGNUP_EMAIL,CD_MOBILE1,CD_LAST_SMS_TEL,'1A' as SH_PTYPE,CD_DOB1,CD_DOB2,CD_INDUSTRY1,CD_INDUSTRY2,CD_PASSWORD,CD_RCI_REF,substr(EXT_REFS, 1, instr(EXT_REFS, '=') - 1) as EXT_REF_TYPE1,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 1), '[^=]+', 1, 2) as EXT_REF_ID1,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 2), '[^=]+', 1, 1) as EXT_REF_TYPE2,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 2), '[^=]+', 1, 2) as EXT_REF_ID2,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 3), '[^=]+', 1, 1) as EXT_REF_TYPE3,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 3), '[^=]+', 1, 2) as EXT_REF_ID3,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 4), '[^=]+', 1, 1) as EXT_REF_TYPE4,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 4), '[^=]+', 1, 2) as EXT_REF_ID4,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 5), '[^=]+', 1, 1) as EXT_REF_TYPE5,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 5), '[^=]+', 1, 2) as EXT_REF_ID5,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 6), '[^=]+', 1, 1) as EXT_REF_TYPE6,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 6), '[^=]+', 1, 2) as EXT_REF_ID6,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 7), '[^=]+', 1, 1) as EXT_REF_TYPE7,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 7), '[^=]+', 1, 2) as EXT_REF_ID7,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 8), '[^=]+', 1, 1) as EXT_REF_TYPE8,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 8), '[^=]+', 1, 2) as EXT_REF_ID8,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 9), '[^=]+', 1, 1) as EXT_REF_TYPE9,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 9), '[^=]+', 1, 2) as EXT_REF_ID9,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 10), '[^=]+', 1, 1) as EXT_REF_TYPE10,regexp_substr(regexp_substr(EXT_REFS, '[^,]+', 1, 10), '[^=]+', 1, 2) as EXT_REF_ID10,EXT_REFS from V_ACU_CD_DATA where CD_CODE = 'E486009'

--- RES


select * from v_acu_res_log where 

select * from t_rul --where rul_sihot_rate is null --rul_action = 'DELETE' 
order by rul_code desc

select * from v_ACU_RES_UNFILTERED a where cd_code = 'E226360'
 and not exists (select null from v_acu_res_unsynced b where cd_code = 'E226360' and a.RUL_PRIMARY = b.RUL_PRIMARY)
order by arr_date

-- select all needs 2:39/2:27 min. on DEV before split/refactoring into V_ACU_RES_FILTERED it needs 2:34/2:39
select * from v_acu_res_unsynced --where cd_code = 'N616715' --E436263' --'

-- 146304 recs on 03-10 14:30, BHC=59901  ANY=14
select * from v_acu_res_filtered
where sihot_hotel_c = '999'

select count(*) from v_acu_res_filtered where ru_roref = 'TK' and arr_date >= trunc(sysdate)

--instr(SIHOT_NOTE, '€') > 0
--ru_status = 120 and 
--rul_action = 'DELETE'
where oc_code is not null
order by arr_date desc

select * from t_ru where 1=1 --ru_rhref = '475168' --
--ru_cdref = 'E226360'
--not exists (select NULL from t_cd where cd_code = ru_cdref) -- 881 RUss with missing CD
and exists (select NULL from t_rh where rh_code = ru_rhref)
and exists (select NULL from t_ro where ro_code = ru_roref)
and exists (select NULL from t_cd where cd_code = ru_cdref)
and not exists (select NULL from V_ACU_RES_UNFILTERED d where d.ru_code = t_ru.ru_code) 
--and ru_from_date >= DATE'2006-01-01' -- 266646
--and ru_roref = 'TK'
order by ru_from_date desc

select * from t_aro where aro_cdref = 'N532290'
 and (ARO_PHONE = 'N' or 1=1)

-- migrating speed: start 30-09: ~1300 clients per hour, 30t in 24h, ab 01-10 (same migration run/batch): 70t in 21h 
select * from t_srsl 
--where srsl_message is not null
order by srsl_date desc

select * from t_cd where cd_sihot_objid is not null

select * from t_ru where ru_sihot_objid is not Null

select * from T_LU where LU_CLASS = 'SIHOT_HOTELS'

edit t_cd where cd_code = 'Y203585'

select * from t_ro where ro_code = 'BK'

select * from t_rul where rul_sihot_rate is not null and exists (select NULL from T_RU, T_RO where RU_ROREF = RO_CODE and RO_SIHOT_RATE is null and RU_CODE = RUL_PRIMARY)


--- investigate on bug with empty OBJID in WEB.RES PERSON blocks 1 and 2

select * from v_acu_res_unfiltered
 where cd_sihot_objid is not NULL and length(cd_sihot_objid) <= 1
 
select * from t_ru where ru_code = 1013229



-- implement direct import  of TK/RCI reservations (SihotRessImport.py)
select * from  T_LU where lu_id = 'IMP_FROM' -- lu_class = 'TK_ADMIN'


-- test sihot setup

select * from t_ap where ap_sihot_cat is not null and f_resort(ap_code) in ('BHC', 'PBC-')

update t_ap set ap_sihot_cat = '_' || ap_sihot_Cat where exists (select NULL from t_at where at_code = ap_atref and at_rsref in ('BHC', '-PBC'))

select * from t_ap where ap_sihot_cat like '_%' and length(ap_sihot_cat) > 4

select * from t_rul, t_ru
 where 1=1
    --and (select RU_ATGENERIC from T_RU where RU_CODE = RUL_PRIMARY) is not NULL
   and RU_CODE = RUL_PRIMARY and RU_ATGENERIC is NULL
