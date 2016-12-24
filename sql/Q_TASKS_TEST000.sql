-- the nightly job cursor query results in 67 records 
select * from T_ARO
      where ARO_EXP_DEPART <= trunc(SYSDATE)
        and ARO_TIMEIN is not null
        and ARO_TIMEOUT is null
        and ARO_APREF = F_ARO_APT(ARO_AROREF_TO)
        and aro_code in (644659)
      --order by aro_apref

--P_ARO_TRANSFER(rARO_FROM.ARO_CODE, rARO_FROM.ARO_AROREF_TO, 'AUTO');

-- fix/test 2301
exec P_ARO_TRANSFER(656224, 649448, 'AUTO');

-- test first one J705
exec P_ARO_TRANSFER(546967, 637824, 'AUTO');

-- after these were working (65 left) try to re-run the nightly job
exec P_ARO_AUTOTRANSFER_JOB

ORA-12899: value too large for column "SALES"."CLIENT_ALLOC"."CA_APTS" (actual: 259, maximum: 255)
ORA-06512: at "LOBBY.ARO_ALLOC", line 14
ORA-04088: error during execution of trigger 'LOBBY.ARO_ALLOC'
ORA-06512: at "LOBBY.ARO_AUTOTRANSFER_JOB", line 18
ORA-06512: at line 1


-- find the showstopper
select aro_code, aro_aroref_to, aro_apref, ca_apts from T_ARO, t_ca
      where aro_code = ca_aroref_first --and aro_apref <> ca_apts --and length(ca_apts) > 100
        and ARO_EXP_DEPART <= trunc(SYSDATE)
        and ARO_TIMEIN is not null
        and ARO_TIMEOUT is null
        and ARO_APREF = F_ARO_APT(ARO_AROREF_TO)
 order by length(ca_apts) desc

exec P_ARO_TRANSFER(613252, 613253, 'AUTO');

exec P_ARO_TRANSFER(647428, 655982, 'AUTO');

exec P_ARO_TRANSFER(656224, 649448, 'AUTO');


select * from t_ca order by length(ca_apts) desc

exec P_ARO_TRANSFER(644659, 644660, 'AUTO');

edit t_ca where ca_aoref = 644659


-- new CITF testing check
select * from t_log order by log_code desc


--- Keys checking

select cr_type, count(*) from t_cr
group by cr_type
order by count(*) desc

select S_OWNER_SEQ.nextval from dual where 1=1 

select LG_OWPRE from T_LG where LG_COUNTRY in (select CO_CODE from T_CO where CO_ISO2 = :xx)



--- SIHOT TEST

select F_SIHOT_CAT('701') from dual

select F_SIHOT_CAT('2 BED@PBC') from dual

select F_SIHOT_CAT(nvl(RUL_SIHOT_ROOM, (select RU_ATGENERIC || '@' || RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY))) from V_ACU_RES_UNSYNCED where RU_CODE = 967004

select * from V_ACU_CD_UNSYNCED --where upper(substr(CD_CITY, 1, 2)) = 'LC' or upper(CD_CITY) in ('X', 'XX', 'XXX', 'XXXX', 'XXXXX', 'XXXXXX') or (CD_ADD11 is NULL and CD_ADD12 is NULL and CD_ADD13 is NULL and CD_POSTAL is NULL and CD_CITY is NULL)


-- check amount of data to migrate
-- .. 325246 filtered from our 396542 clients (28704 clients filtered because of incomplete/minimal contact data) and (strange) only 102800 unsynced (select count(*) neeeded 17 min!!) but should be same as filtered
-- .. After readding LOG_DATE filter in UNSYNCED the number of records/timing changed: 1-1-2016 => 26407/19 sec, 1-1-2006 => 102800/34s
select count(*) from V_ACU_CD_DATA where not ( upper(substr(nvl(CD_CITY, '_'), 1, 2)) = 'LC' or upper(nvl(CD_CITY, '_')) in ('X', 'XX', 'XXX', 'XXXX', 'XXXXX', 'XXXXXX') or (CD_ADD11 is NULL and CD_ADD12 is NULL and CD_ADD13 is NULL and CD_POSTAL is NULL and CD_CITY is NULL) )

select count(*) from t_cd

-- b4 refact to V02 needed 4 min (102800 records) after 13/8/22/9/8/8 s and with 3* more (306663) records (fixed bug by changing inner to outer join)
select count(*) from V_ACU_CD_UNSYNCED

-- after refact with select *
select * from V_ACU_CD_UNSYNCED

-- .. 146295 filtered reservations (PBC+BHC+ANY, from 2006 onwards) and 95742 unsynced (additionally resOcc filtered) ones - of total of 730850 RUs
select count(*) from V_ACU_RES_FILTERED

select count(*) from V_ACU_RES_UNSYNCED

select count(*) from t_ru


update t_ap set ap_sihot_hotel = -1, ap_sihot_cat = 'A___'

update t_rul set rul_sihot_hotel = -2, rul_sihot_cat = 'R___', rul_sihot_pack = 'R_'


-- sync tests C605765/TK/Breakfast/Duplex
select * from V_ACU_CD_UNSYNCED where CD_CODE = 'C605765'

select * from V_ACU_CD_FILTERED where CD_CODE = 'C605765'

select * from t_log where LOG_PRIMARY = 'C605765' order by log_code desc

select * from V_ACU_CD_LOG where LOG_PRIMARY = 'C605765' --order by log_code desc

edit t_cd where cd_sihot_objid is not null


select * from V_ACU_RES_UNSYNCED --where CD_CODE = 'N617081' ---E362344' -- and owner 'Z124007' --RU_ROREF = 'TG' --CD_CODE = 'C605765'
where ARR_DATE >= '12-OCT-2016'

select * from V_ACU_RES_FILTERED where CD_CODE = 'C605765'

select * from V_ACU_RES_LOG where RUL_PRIMARY in (1013229, 1032598)

select * from t_rhl order by rhl_code desc

select * from t_ru where ru_sihot_objid is not null or ru_code in (1013229, 1032598, 1032603)

select * from t_rh where rh_code = 647132

edit t_rh where rh_owref = 'N617081'

select * from t_rul --where rul_primary in (1013229, 1032598) 
order by rul_code desc

select * from t_srsl order by srsl_date desc


-- check to add SF-Ids onto EXT_REFS in V_ACU_CD_DATA
select cd_code
    ,  (select f_stragg(distinct CR_TYPE || '=' || CR_REF) from (select CR_TYPE, CR_REF, CR_CDREF from T_CR where CR_CDREF = CD_CODE 
                                                                  union all select 'SF', MS_SF_ID from T_ML, T_MS where ML_CODE = MS_MLREF and ML_CDREF = CD_CODE and MS_SF_ID is not NULL))
  from t_cd

select * from t_ro where ro_sihot_rate is not null

select cd_code
    ,  (select f_stragg(distinct CR_TYPE || '=' || CR_REF) from (select CR_TYPE, CR_REF, CR_CDREF from T_CR 
                                                                  union all select 'SF', MS_SF_ID, ML_CDREF from T_ML, T_MS where ML_CODE = MS_MLREF and MS_SF_ID is not NULL)  where CR_CDREF = CD_CODE)
  from t_cd

-- sihot error 1001 for RU=1009631 - assume SIHOT is referring to the other reservation (RU=904203) that is already created within SIHOT.PMS
select * from t_ru where ru_code = 1009631

select * from t_ru where ru_cdref = 'Z008475'

select * from t_ru where ru_roref = 'FB' and ru_from_date > '1-JAN-2017' and ru_rhref is not null

select f_key_val(lu_char, 'ShiftId'), f_sihot_pack(LU_ID, case when LU_CLASS = 'MKT_BOARDS' then 'MKT_' end), t_lu.* from t_lu
 where LU_CLASS like '%BOARDS' and lu_active > 0
 order by lu_class desc


-- special requests - including guest surcharge (currently only for ER reservations)

select * from t_px where px_alpha like 'GUEST%'

select * from t_px where px_alpha = 'GUESTSURCH'

select * from t_lu where lu_id like 'GUEST_SURCH%'

select * from t_bt, t_aro where bt_aoref = aro_code and bt_pxref in (651, 652, 653, 693) order by bt_cwhen desc

select * from t_sr where sr_pxref in (651, 652, 653, 693) order by sr_code desc

select * from t_ru where ru_code in (973000)



-- requested apartment features

select * from t_raf, t_aft where raf_aftref = aft_code

select * from t_raf, t_lu
 where substr(lu_class, 1, 11) = 'SIHOT_CATS_' and 

select F_SIHOT_PAID_RAF(RU_CODE), f.* from v_acu_res_filtered f where F_SIHOT_PAID_RAF(RU_CODE) is not NULL

 

select SIHOT_NOTE, SIHOT_TEC_NOTE, V_ACU_RES_FILTERED.* from V_ACU_RES_FILTERED 
 where 1=1
   and ru_roref = 'ER'
   --and (instr(SIHOT_TEC_NOTE, 'AptFeat:') > 0 or instr(SIHOT_TEC_NOTE, 'SpecReq:') > 0)
  order by ARR_DATE desc


-- find FB examples with board: F468913, G616870, F614205, V576425, I615916

select * from V_ACU_RES_FILTERED
 where 1=1
   --and ru_roref = 'FB' and rul_sihot_pack <> 'RO'
   --and rul_sihot_hotel = 999
   --and cd_code = 'E543935'
   --and ru_code = 739201 --60218
   and substr(ro_res_group, 1, 5) = 'Owner'
 order by arr_date desc

select * from t_rul where rul_sihot_hotel  = 999

select * from t_ru  where ru_code = 60218

select rul_sihot_hotel as sihot_hotel_id, to_char(arr_date, 'YYYY') as occ_year, rul_sihot_cat as sihot_room_cat, count(*) as weeks
  from V_ACU_RES_FILTERED
 where substr(ro_res_group, 1, 5) = 'Owner' and arr_date < sysdate
 group by rul_sihot_hotel, to_char(arr_date, 'YYYY'), rul_sihot_cat
 order by rul_sihot_hotel, to_char(arr_date, 'YYYY'), rul_sihot_cat

select F_SIHOT_CAT(RU_ATGENERIC || '@' || case when SIHOT_ROOM_NO is not NULL and RU_RESORT = 'ANY'
                                               then F_RESORT(RUL_SIHOT_ROOM) else RU_RESORT end), V_ACU_RES_UNFILTERED.* from V_ACU_RES_UNFILTERED
 where ru_code in (565256, 724494, 1032509) --309737

select *   from t_cd where cd_sihot_objid = 47898


select * from V_ACU_RES_FILTERED where CD_CODE = 'E499163'

select * from V_ACU_RES_UNSYNCED --where CD_CODE = 'E374408'

select * from t_ro where ro_code = 'TK'

select * from t_rs where rs_code in ('BHH', 'BHC', 'HMC', 'PBC')


-- check SIHOT apartment categories
select * from t_ap where 1=1
   --and ap_sihot_hotel > 0 
   and instr(nvl(ap_sihot_cat, '_'), '_') > 0 and f_resort(ap_code) in ('BHC', 'PBC')

select * from v_acu_res_filtered --t_rul
 where 1=1
  --and instr(nvl(rul_sihot_cat, '_'), '_') > 0 and rul_sihot_hotel in (1, 4)
  --and rh_ext_book_ref = 'VN21982001' and RUL_CODE = 4785629
  --and F_SIHOT_CAT('RU' || RU_CODE) <> RUL_SIHOT_CAT
  and RU_CODE in (991385, 652856)

select * from t_ru where ru_sihot_objid is not null

select * from T_SRSL --where srsl_status like 'SYNCED%'
 order by srsl_date desc

select * from t_arol
 order by arol_date desc
 
select rh_ext_book_ref, t_rh.* from t_rh where rh_roref = 'TK' --and instr(rh_requnit, '-E') > 0 
  and rh_ext_book_ref = 'VN21982001'
 order by rh_from_date desc

select * from t_cd where cd_sihot_objid = 103750 --103 --is not null
or cd_code in ('E516605', 'E516886')

select * from t_ru where ru_cdref = 'E513040' or ru_rhref = 416452

select * from V_ACU_RES_UNSYNCED
 where 1=1
   --and F_SIHOT_CAT('RU' || RU_CODE) <> RUL_SIHOT_CAT  --RUNS FOREVER!!!!
   --and RU_CODE in (991385, 652856)
   and SIHOT_GDSNO = 'TC21300009'


select * from t_rh where rh_ext_book_ref = 'VS10531164'
or rh_owref in ('E516605', 'E516886')

select * from t_rh where not exists (select NULL from t_cd where cd_code = rh_owref) and rh_status <> 120 order by rh_from_Date desc

select * from t_aro where aro_rhref = 640159

update t_rul set rul_date = rul_date - 365 where rul_code in (4937292, 4937474, 4945868)

select * from t_prc, t_ml, t_ms where ml_code = ms_mlref and ms_prcref = prc_code and ml_cdref = 'F498638'

select * from t_lu where lu_class = 'MKT_BOARDS' or lu_class = 'BOARDS' and lu_id in ('B', 'H', 'F')

-- fix RH records with invalid orderer
update t_rh set rh_owref = (select RU_CDREF from T_RU where RU_RHREF = RH_CODE and RU_STATUS <> 120 and RU_FROM_DATE = RH_FROM_DATE)
 where rh_owref in ('E516605', 'E516886', 'E516686')
   and exists (select NULL from v_acu_res_unsynced where ru_rhref = RH_CODE)


select * from v_acu_cd_data
 where cd_code in ('E469707', 'E595140', 'E595140P2') or cd_snam2 = '.'
 
 
 --- fix problematic client data

update t_cd set cd_fnam1 = trim('.' from trim(cd_fnam1))
              , cd_snam1 = trim('.' from trim(cd_snam1))
              , cd_fnam2 = trim('.' from trim(cd_fnam2))
              , cd_snam2 = trim('.' from trim(cd_snam2))
 where trim('.' from trim(cd_fnam1)) is null
    or trim('.' from trim(cd_snam1)) is null
    or trim('.' from trim(cd_fnam2)) is null
    or trim('.' from trim(cd_snam2)) is null

--- check roll out of Sihot sync system

select * from v_acu_res_unfiltered where sihot_gdsno in ('652856', '991385', 'TC21300009')

select * from v_acu_cd_data where cd_code2 is not null and cd_snam2 is NULL

select * from v_acu_res_log where nvl(rul_sihot_hotel, -1) < 0

select * from T_AP, T_RUL where AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')

select * from T_RUL l left outer join t_ru on RUL_PRIMARY = RU_CODE
                                     -- ignoring reservation requests (and changes) with stays before 2012
                                     --and RU_FROM_DATE > DATE'2012-01-01'
 where 1=1 --rul_primary = ru_code
   and not exists (select AP_SIHOT_CAT from T_AP where AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')) -- and AP_SIHOT_CAT is not NULL)
   and RUL_DATE >= DATE'2012-01-01'
   and (RU_FROM_DATE is NULL or RU_FROM_DATE < DATE'2012-01-01')
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   --and exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY and RU_FROM_DATE >= DATE'2012-01-01') 
   and RUL_SIHOT_ROOM is not NULL;

--delete from t_ru where ru_code = 250314
--delete from t_rul where rul_code = 4946856

select * from T_RUL l
 where (select AP_SIHOT_CAT from T_AP where AP_CODE = ltrim(RUL_SIHOT_ROOM, '0')) is NULL
   and not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   -- Date speed-up on log/arrival dates - to support RU delete (outer join to T_RU) check RU arr date with not exists
   and RUL_DATE >= DATE'2012-01-01'
   and not exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY and RU_FROM_DATE < DATE'2012-01-01') 
   and RUL_SIHOT_ROOM is not NULL;


select (select LU_CHAR from T_LU, T_RU
                                   where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end
                                     and LU_ID = RU_ATGENERIC
                                     and RU_CODE = RUL_PRIMARY) as CAT
      , (select RU_ATGENERIC || '@' || RU_RESORT from t_ru where ru_code = rul_primary) as RU_VALS
      , l.*
  from T_RUL l
 where not exists (select NULL from T_RUL c where c.RUL_PRIMARY = l.RUL_PRIMARY and c.RUL_CODE > l.RUL_CODE)
   and nvl(RUL_MAINPROC, '_') not in ('wCheckIn', 'wCheckin')
   -- Date speed-up on log/arrival dates - to support RU delete (outer join to T_RU) check RU arr date with not exists
   and RUL_DATE >= DATE'2012-01-01'
   and not exists (select NULL from T_RU where RU_CODE = RUL_PRIMARY 
                                           and ( RU_FROM_DATE < DATE'2012-01-01')
   --                                           or RU_ATGENERIC not in ('HOTEL', 'STUDIO', '1 BED', '2 BED', '3 BED', '4 BED')
     --                                         or RU_RESORT not in ('ANY', 'BHC', 'PBC', 'BHH', 'HMC')
                                               )
   and RUL_SIHOT_ROOM is NULL
   and not exists (select NULL from T_RAF where RAF_RUREF = RUL_PRIMARY)
   and RUL_SIHOT_CAT = 'R___'



select (select f_stragg(LU_CHAR) from T_LU, T_RU, T_RAF
                                   where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end
                                     and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and RU_CODE = RAF_RUREF
                                     and RU_CODE = RUL_PRIMARY
                                   --order by LU_CLASS desc
      ) as CAT, T_RUL.*
  from T_RUL
 where (select count(*) from T_LU, T_RU, T_RAF
                                   where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || RU_RESORT and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and LU_ACTIVE = 1) then 'SIHOT_CATS_' || RU_RESORT else 'SIHOT_CATS_ANY' end
                                     and LU_ID = RU_ATGENERIC || '_' || RAF_AFTREF and RU_CODE = RAF_RUREF
                                     and RU_CODE = RUL_PRIMARY) > 1


select * from v_acu_res_filtered

select * from t_srsl