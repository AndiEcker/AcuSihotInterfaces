

prompt reset SIHOT package values within our MKT_/BOARDS lookup classes

update T_LU set LU_CHAR = substr(LU_CHAR, 1, instr(LU_CHAR, ' SIHOT_PACK') - 1)
 where LU_CLASS like '%BOARDS' and instr(LU_CHAR, 'SIHOT_PACK=') > 0;

update T_LU set LU_CHAR = LU_CHAR || ' SIHOT_PACK="' || F_SIHOT_NON_MUTAT_PACK(LU_CHAR, LU_DESC) || '"'
 --select f_key_val(lu_char, 'ShiftId'), f_sihot_pack(LU_ID, case when LU_CLASS = 'MKT_BOARDS' then 'MKT_' end), t_lu.* from t_lu
 where LU_CLASS like '%BOARDS' and instr(LU_CHAR, 'SIHOT_PACK=') = 0;

commit;



prompt new T_AP columns for SIHOT hotel id and price category (unit size+apt features) and resort (needed also for the 16 BHC sweets migrated to new CPA-pseudo resort) 

update T_AP set AP_SIHOT_CAT = 'STDO', AP_SIHOT_HOTEL = 0 where 1=1;

commit;
 
update T_AP set AP_SIHOT_CAT = (select LU_CHAR from T_LU
                                 where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || (select AT_RSREF from T_AT where AT_CODE = AP_ATREF)
                                                                                            and LU_ID = (select AT_GENERIC from T_AT where AT_CODE = AP_ATREF))
                                                       then 'SIHOT_CATS_' || (select AT_RSREF from T_AT where AT_CODE = AP_ATREF) else 'SIHOT_CATS_ANY' end
                                   and LU_ID = (select AT_GENERIC from T_AT where AT_CODE = AP_ATREF)),
                AP_SIHOT_HOTEL = nvl((select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ID = (select AT_RSREF from T_AT where AT_CODE = AP_ATREF)), 0)
 where exists (select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ID = (select AT_RSREF from T_AT where AT_CODE = AP_ATREF))
   and (select AT_GENERIC from T_AT where AT_CODE = AP_ATREF) is not NULL;

commit;



prompt new T_CD column for to store SIHOT OBJID

select CD_CODE, CD_SIHOT_OBJID, CD_SIHOT_OBJID2 from t_cd where CD_SIHOT_OBJID is not NULL or CD_SIHOT_OBJID2 is not NULL;

-- needs 11 min on SP.DEV - with WHERE 1=1 but only 391073 clients?!?!?
update T_CD set CD_SIHOT_OBJID = NULL, CD_SIHOT_OBJID2 = NULL where CD_SIHOT_OBJID is not NULL or CD_SIHOT_OBJID2 is not NULL;

commit;



prompt reset new T_LG columns for SIHOT hotel language/nationality 

update T_LG set LG_SIHOT_LANG = NULL where 1=1;

update T_LG set LG_SIHOT_LANG = 'HR' where LG_CODE = 'CRO';
update T_LG set LG_SIHOT_LANG = 'EN' where LG_CODE = 'ENG';
update T_LG set LG_SIHOT_LANG = 'FR' where LG_CODE = 'FRE';
update T_LG set LG_SIHOT_LANG = 'DE' where LG_CODE = 'GER';
update T_LG set LG_SIHOT_LANG = 'IT' where LG_CODE = 'ITA';
update T_LG set LG_SIHOT_LANG = 'PL' where LG_CODE = 'POL';
update T_LG set LG_SIHOT_LANG = 'PT' where LG_CODE = 'POR';
update T_LG set LG_SIHOT_LANG = 'ES' where LG_CODE = 'SPA';
update T_LG set LG_SIHOT_LANG = 'SI' where LG_CODE = 'SVN';

commit;


prompt reset new T_RO columns for to store SIHOT OBJID of agency and rate mapping

update T_RO set RO_SIHOT_AGENCY_OBJID = NULL, RO_SIHOT_RATE = NULL where 1=1;

update T_RO set RO_SIHOT_AGENCY_OBJID = case when RO_CODE in ('TK', 'tk') then '111' end, RO_SIHOT_RATE = RO_CODE
 where RO_CLASS in ('B', 'R')
   and ( substr(RO_RES_GROUP, 1, 5) = 'Owner' or substr(RO_RES_GROUP, 1, 13) = 'Club Paradiso' or substr(RO_RES_GROUP, 1, 3) = 'RCI' or substr(RO_RES_GROUP, 1, 5) = 'Promo' or RO_CODE in ('TK', 'tk') );
commit;



prompt reset new T_RS column for easier classification of client to guest transfer in SIHOT interfaces

update T_RS set RS_SIHOT_GUEST_TYPE = NULL where 1=1;

-- first set all to general owner (mainly for to group less import owner types like e.g. tablet, lifestyle, expirience, explorer)
update T_RS set RS_SIHOT_GUEST_TYPE = 'O' where RS_CLASS = 'CONSTRUCT' or RS_CLASS = 'BUILDING' and RS_GROUP = 'A';
-- then specify distinguishable client types
update T_RS set RS_SIHOT_GUEST_TYPE = 'I' where RS_CODE in ('PBF', 'TSP');
update T_RS set RS_SIHOT_GUEST_TYPE = 'K' where RS_CODE in ('KEY');
--update T_RS set RS_SIHOT_GUEST_TYPE = 'C' where RS_CODE in ('CPA');

commit;



prompt reset new T_RU column for to store SIHOT OBJID

select ru_code, ru_sihot_objid from t_ru where ru_sihot_objid is not NULL;

update T_RU set RU_SIHOT_OBJID = NULL where RU_SIHOT_OBJID is not NULL;

commit;



prompt populate/resert new T_RUL columns for data needed for RU/ARO cancellation/deletions and ARO apartment overloads

update T_RUL set RUL_SIHOT_CAT = 'STDO', RUL_SIHOT_HOTEL = 0, RUL_SIHOT_ROOM = NULL, RUL_SIHOT_OBJID = NULL, RUL_SIHOT_PACK = 'RO' where 1=1;

commit;


--- runs 11 minutes on SP.DEV and (RARO RARO RARO) without the and 1=1 it shows a missing expression error
update T_RUL set RUL_SIHOT_CAT = nvl((select LU_CHAR from T_LU
                                       where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY)
                                                                                                  and LU_ID = (select RU_ATGENERIC from T_RU where RU_CODE = RUL_PRIMARY))
                                                             then 'SIHOT_CATS_' || (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY) else 'SIHOT_CATS_ANY' end
                                         and LU_ID = (select RU_ATGENERIC from T_RU where RU_CODE = RUL_PRIMARY)), 'STIC'),  -- nvl needed for deleted RUs and for 20 cancelled RUs from 2014 with 'Sterling Suites' in RU_ATGENERIC - see line 138 in Q_SIHOT_SETUP2.sql
                 RUL_SIHOT_HOTEL = (select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ID = (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY)),
                 RUL_SIHOT_ROOM = F_RU_ARO_APT((select RU_RHREF from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE from T_RU where RU_CODE = RUL_PRIMARY), (select RU_FROM_DATE + RU_DAYS from T_RU where RU_CODE = RUL_PRIMARY)),
                 RUL_SIHOT_OBJID = (select RU_SIHOT_OBJID from T_RU where RU_CODE = RUL_PRIMARY),
                 RUL_SIHOT_PACK = case when F_SIHOT_PACK((select PRC_BOARDREF1 from T_RU, T_ML, T_MS, T_PRC where RU_MLREF = ML_CODE and ML_CODE = MS_MLREF and MS_PRCREF = PRC_CODE and RU_CODE = RUL_PRIMARY), 'MKT_') != 'RO' 
                                       then F_SIHOT_PACK((select PRC_BOARDREF1 from T_RU, T_ML, T_MS, T_PRC where RU_MLREF = ML_CODE and ML_CODE = MS_MLREF and MS_PRCREF = PRC_CODE and RU_CODE = RUL_PRIMARY), 'MKT_')
                                       --else F_SIHOT_PACK(nvl((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS) from T_RU where RU_CODE = RUL_PRIMARY),
                                       --                      (select RU_BOARDREF from T_RU where RU_CODE = RUL_PRIMARY)))
                                       when (select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS) from T_RU where RU_CODE = RUL_PRIMARY) != 'RO'
                                       then F_SIHOT_PACK((select F_RU_ARO_BOARD(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS) from T_RU where RU_CODE = RUL_PRIMARY))
                                       else F_SIHOT_PACK((select RU_BOARDREF from T_RU where RU_CODE = RUL_PRIMARY)) 
                                       end
 where exists (select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ID = (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY))
   and (select RU_ATGENERIC from T_RU where RU_CODE = RUL_PRIMARY) is not NULL
   and 1=1;

commit;


prompt truncate table for to store the synchronization log

select * from T_SRSL;

delete from T_SRSL where 1=1;

commit;

--truncate table T_SRSL;
