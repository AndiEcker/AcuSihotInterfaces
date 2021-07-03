
-- check usage of our reservation channels/market sources for BHH, BHC, HMC and PBC for the years 2015 and onwards
select at_rsref as Rsrt, 
      to_char(aro_exp_arrive, 'YYYY') as year,
      count(*) as Cnt, nvl(ro_res_group, 'Other') as Res_Type
      , f_stragg(distinct ARO_ROREF) as Res_Type_Codes
  from t_aro, t_ro, t_ap, t_at
 where aro_roref = ro_code and aro_apref = ap_code and ap_atref = at_code
   and aro_status <> 120 and aro_exp_arrive >= '01-JAN-2015'
   and at_rsref in ('BHH', 'BHC', 'PBC', 'HMC')
 group by at_rsref, 
      to_char(aro_exp_arrive, 'YYYY'),
      nvl(ro_res_group, 'Other') 
 order by at_rsref, 
        to_char(aro_exp_arrive, 'YYYY'),
        count(*) desc, nvl(ro_res_group, 'Other');



-- CHANNEL - 12 records
select distinct RO_RES_GROUP from T_RO where RO_RES_GROUP is not NULL order by RO_RES_GROUP;

-- NN - 4 records
select distinct RO_SP_GROUP from T_RO where RO_SP_GROUP is not NULL order by RO_SP_GROUP;

-- NN2 - 2 records
select distinct RO_RES_CLASS from T_RO where RO_RES_CLASS is not NULL order by RO_RES_CLASS;




--#######################   APARTMENT CATEGORIES   ###################################################################

-- list of all our room categories
select at_generic
     , case at_rci_desc_short when '1 BED DLX' then '1 BED DUPLEX'
                              when '2 BED DLX' then '2 BED DUPLEX D'
                              when '3 BED DLX' then '3 BED DUPLEX' else at_rci_desc_short end as at_rci_desc_short
     , case at_group          when '1 BED DLX' then '1 BED DUPLEX'
                              when '2 BED DLX' then '2 BED DUPLEX D'
                              when '3 BED DLX' then '3 BED DUPLEX' else at_group end as at_group
     -- , f_stragg(at_code) as at_codes
     , f_stragg(' ' || at_rsref || ':' || at_code || ':=' || (select f_stragg(ap_code) from t_ap where ap_atref = at_code)) as RS_AT_Codes_Apts 
  from t_at
 where at_generic is not NULL and at_rci_desc_short is not NULL
   and at_rsref in ('BHH', 'BHC', 'HMC', 'PBC', 'PMA')
group by at_generic
     , case at_rci_desc_short when '1 BED DLX' then '1 BED DUPLEX'
                              when '2 BED DLX' then '2 BED DUPLEX D'
                              when '3 BED DLX' then '3 BED DUPLEX' else at_rci_desc_short end
     , case at_group          when '1 BED DLX' then '1 BED DUPLEX'
                              when '2 BED DLX' then '2 BED DUPLEX D'
                              when '3 BED DLX' then '3 BED DUPLEX' else at_group end
order by at_generic, at_rci_desc_short, at_group;


-- list of our apartment features
select aft_desc || case when aft_desc = 'Seafront' then '_5' 
                        when aft_desc = 'High Floor' then '_6'
                        when aft_desc = 'Duplex' then '_7' 
                        --when instr(upper(ap_lobby_comment), 'STERL') > 0 then '_7' 
                   end as Apt_Feature
    , at_rsref
    , count(*) as num_apts 
    --, listagg(ap_code, ',') within group (order by ap_code) as Apts  -- TOO LONG
    , f_stragg(''
               || case when aft_desc = 'Seafront' and nvl(ap_quality, -1) <> 5 
                         or aft_desc = 'High Floor' and nvl(ap_quality, -1) <> 6
                         or aft_desc = 'Duplex' and nvl(ap_quality, -1) <> 7 
                         or instr(upper(ap_lobby_comment), 'STERL') > 0 and nvl(ap_quality, -1) <> 7
                       then '@' end
               || ap_code
               || '_' || ap_quality
               || case when instr(upper(ap_lobby_comment), 'STERL') > 0 then 's' end -- 46 apts in PBC but only 30 of them have an AP_QUALITY of 7
              ) as Apts
  from t_aft, t_afr, t_ap, t_at
 where aft_code = afr_aftref and afr_apref = ap_code and ap_atref = at_code
   and at_rsref in ('BHH', 'BHC', 'HMC', 'PBC', 'PMA')
   and aft_desc <> 'Steps'
   -- check first migration setup (only BCH/PBC and paid supplement features (781=Seafront, 752=Duplex, 748=Sterling, 757=High Floor) 
   and at_rsref in ('BHC', 'PBC')
   and ( aft_desc in ('Seafront', 'High Floor', 'Duplex') or instr(upper(ap_lobby_comment), 'STERL') > 0 )
 group by aft_desc, at_rsref
 order by upper(aft_desc), at_rsref;
  


--- check TK apartment features to calculate the room price categories
-- Sea front
select * from t_ap, t_at where ap_atref = at_code and ap_quality = 5 and at_rsref in ('PBC', 'BHC') and substr(ap_sihot_cat, 3, 1) not in ('S');

-- high floor
select * from t_ap, t_at where ap_atref = at_code and ap_quality = 6 and at_rsref in ('PBC', 'BHC') --and substr(ap_sihot_cat, 4, 1) not in ('H')
 --and not exists (select NULL from t_aft

-- duplex(only BHC) and sterling/refurbished(only PBC )
select f_stragg(ap_code || '_' || ap_quality)
     --, ap_lobby_comment
  from t_ap, t_at where ap_atref = at_code 
   and nvl(ap_quality, -1) <> 7 --and at_rsref in ('PBC')--, 'BHC') and substr(ap_sihot_cat, 2, 1) <> case at_rsref when 'BHC' then 'D' when 'PBC' then 'S' else 'x' end
 --and ap_sihot_cat like '1S%'
 and (instr(upper(ap_lobby_comment), 'STERL') > 0 or ap_inv_usage like '*uites*')
--group by ap_quality
--order by lpad(ap_code, 4)


-- double check list of BHC, BHH, HMC, PBC, PMA apartments with their corresponding apartment categories and features
select at_rsref, ap_code, at_generic, at_group, at_rci_desc_short, f_stragg(aft_desc) as Apt_Features
  from t_ap, t_at, t_afr, t_aft
 where ap_atref = at_code and ap_code = afr_apref and afr_aftref = aft_code
   and at_rsref in ('BHH', 'BHC', 'HMC', 'PBC', 'PMA')
 group by at_rsref, ap_code, at_generic, at_group, at_rci_desc_short
 order by at_rsref, ap_code


-- list of unique room categories and features
select at_generic as Beds, at_rci_desc_short as RCI_Category, at_group as Sales_Category 
     , Features as Apt_Features
     , f_stragg(distinct substr(''
                    || case when upper(at_rci_desc_short) like '%OCEAN%' and upper(features) not like '%SEA VIEW%' then ', Sea-View Apt Feature missing' end
                    || case when upper(at_rci_desc_short) not like '%OCEAN%' and upper(features) like '%SEA VIEW%' then ', Sea-View/Ocean RCI Apt Category missing' end
                    --|| case when upper(at_rci_desc_short) like '%2BED2B%' and upper(features) not like '%2 BATHROOMS%' then ', 2-Bathrooms Apt Feature missing' end
                    --|| case when upper(at_rci_desc_short) not like '%2BED2B%' and upper(features) like '%BATHROOMS%' then ', Extra-Bathrooms RCI Apt Category missing' end
                    || case when upper(at_rci_desc_short) like '%DUPLEX%' and upper(features) not like '%DUPLEX%' then ', Duplex Apt Feature missing' end
                    || case when upper(at_rci_desc_short) not like '%DUPLEX%' and upper(features) like '%DUPLEX%' then ', Duplex RCI Apt Category missing' end
                    , 3)) as Discrepancies 
     , f_stragg(ap_code) as Apts 
  from (select at_code, at_rsref
       , at_generic
       , case upper(at_rci_desc_short)
                                when '1 BED DLX' then '1 BED DUPLEX'
                                when '2 BED DLX' then '2 BED DUPLEX D'
                                when '3 BED DLX' then '3 BED DUPLEX'
                                when '1BEDROOM' then '1 BED'
                                when '2BED1BATH' then '2 BED'
                                when '2BED2BATH' then '2 BED'
                                when '2BED2BOCEAN' then '2BEDOCEAN' 
                                else upper(at_rci_desc_short) end as at_rci_desc_short
       , case at_group          when '1 BED DLX' then '1 BED DUPLEX'
                                when '2 BED DLX' then '2 BED DUPLEX D'
                                when '3 BED DLX' then '3 BED DUPLEX' else at_group end as at_group
       , ap_code
        from t_at, t_ap 
       where at_code = ap_atref
         and at_generic is not NULL --and at_rci_desc_short is not NULL
         and at_rsref in ('BHH', 'BHC', 'HMC', 'PBC', 'PMA')
      )
     , (select afr_apref, f_stragg(aft_desc) as Features from t_afr, t_aft
         where afr_aftref = aft_code 
           --and aft_desc not in ('Steps', 'Double Beds', 'Twin Beds', 'Duplex', 'Pool View', 'Country View', 'Garden View', 'Sleep 6', 'High Floor', 'Low Floor', 'Near Lift', 'Easy Access to Pool', 
           --                     'Converted', 'Wheelchair Access', 'Equipped for disabled', 'Walk in Shower', 'No Steps', 'Smoking') 
           and aft_desc in ('Sea View', 'Seafront', 'Duplex') --, '1 ' || '&' || ' 1/2 Bathrooms', '2 Bathrooms', '3 Bathrooms', 'Garden')
         group by afr_apref)
 where ap_code = afr_apref(+)
group by at_generic, at_rci_desc_short, at_group, features
     --, aft_desc
order by 1, 2, 3, 4 --at_generic, at_rci_desc_short, at_group, features


-- query for Mirella with all PBC apartments
select ap_code, at_group, at_rci_desc_short
  from t_ap, t_at
 where ap_atref = at_code
   and at_rsref = 'PBC'
 order by 1


-- check lookups
select LU_NUMBER as sihot_hotel_id, nvl(rs_name, 'ANY pseudo hotel'), LU_ID as short_acu_id from T_LU, T_RS where LU_CLASS = 'SIHOT_HOTELS' and LU_ID = RS_CODE(+) order by lu_number

select * from t_ap, t_at
 where ap_atref = at_code
   and not exists --(select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ID = (select AT_RSREF from T_AT where AT_CODE = AP_ATREF))
 (select LU_CHAR from T_LU
                                 where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || (select AT_RSREF from T_AT where AT_CODE = AP_ATREF)
                                                                                            and LU_ID = (select AT_GENERIC from T_AT where AT_CODE = AP_ATREF))
                                                       then 'SIHOT_CATS_' || (select AT_RSREF from T_AT where AT_CODE = AP_ATREF) else 'SIHOT_CATS_ANY' end
                                   and LU_ID = (select AT_GENERIC from T_AT where AT_CODE = AP_ATREF))


-- check for overlapping ARO (for populate new RUL_SIHOT_ROOM column

select * from t_aro a
 where exists (select NULL from t_aro b where b.aro_rhref = a.aro_rhref and b.aro_exp_arrive = a.aro_exp_arrive and b.aro_code <> a.aro_code and b.aro_status <> 120  and trunc(b.ARO_TIMEOUT) > b.ARO_EXP_ARRIVE and trunc(nvl(b.ARO_RECD_KEY, b.ARO_TIMEIN)) < trunc(b.ARO_TIMEOUT))
   and a.aro_status <> 120 and trunc(a.ARO_TIMEOUT) > a.ARO_EXP_ARRIVE and trunc(nvl(a.ARO_RECD_KEY, a.ARO_TIMEIN)) < trunc(a.ARO_TIMEOUT)
 order by aro_exp_arrive desc


-- not category for RU/RUL records
select * from T_RU where F_RU_ARO_APT(RU_RHREF, RU_FROM_DATE, RU_FROM_DATE + RU_DAYS) is null

select * from t_rul, t_ru where rul_primary = ru_code
  and (select LU_CHAR from T_LU
                                   where LU_CLASS = case when exists (select NULL from T_LU where LU_CLASS = 'SIHOT_CATS_' || (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY)
                                                                                              and LU_ID = (select RU_ATGENERIC from T_RU where RU_CODE = RUL_PRIMARY))
                                                         then 'SIHOT_CATS_' || (select RU_RESORT from T_RU where RU_CODE = RUL_PRIMARY) else 'SIHOT_CATS_ANY' end
                                     and LU_ID = (select RU_ATGENERIC from T_RU where RU_CODE = RUL_PRIMARY)) is NULL





--####################################   PRODUCTS   ##############################################################

-- list of our products

select substr(s.md_desc, 1, 18) as Spa_Desc, substr(e.md_desc, 1, 18) as Eng_Desc, substr(g.md_desc, 1, 18) as Ger_Desc, substr(f.md_desc, 1, 18) as Fre_Desc
     , px_rsref, px_trading_as, px_charge, px_deposit, --px_drcr, 
     px_group, px_accounting_group
     --, px_pos_code, px_accounting_code   ALLWAYS NULL
     --, px_exclude_rule, px_nocharge_rule
     --, px_discount_rule                  ALLWAYS ZERO
     , px_alpha as ACUMEN_SHORT_CODE
     --, (select f_stragg(bt_cwhen) from t_bt where bt_pxref = px_code) as ventas
  from t_px, t_md s, t_md e, t_md g, t_md f
 where px_alpha = s.md_foreign_cref(+) and s.md_foreign_table(+) = 'PRODUCTS_XL' and s.md_lgref(+) = 'SPA'
   and px_alpha = e.md_foreign_cref(+) and e.md_foreign_table(+) = 'PRODUCTS_XL' and e.md_lgref(+) = 'ENG'
   and px_alpha = f.md_foreign_cref(+) and f.md_foreign_table(+) = 'PRODUCTS_XL' and f.md_lgref(+) = 'FRE'
   and px_alpha = g.md_foreign_cref(+) and g.md_foreign_table(+) = 'PRODUCTS_XL' and g.md_lgref(+) = 'GER'
   --and px_accounting_code is not NULL
   --and px_discount_rule <> 0
   and px_drcr = 'DR'
   --and px_rsref <> substr(px_trading_as, 1, 3)
 order by px_drcr, s.md_desc


edit t_md where substr(md_desc, 1, 1) = chr(9)

-- there are some/18 products without a description text (see at the end of the previous query) that could be removed (not migrated to SiHOT)
select t_px.*
    , (select f_stragg(bt_cwhen) from t_bt where bt_pxref = px_code) as ventas
  from t_px
 where not exists (select NULL from t_md where md_foreign_cref = px_alpha) -- and md_foreign_table = 'PRODUCTS_XL'
 

-- mealplans for our sihot arrangement/packages

-- Marketing meals

select distinct --LU_ID as BOARDID,
       resort, pax_type, '7 Days' as Price_Per, lpad('??? �', 12) as Amount,
       LU_DESC as BOARDDESC,
       --F_KEY_VAL(LU_CHAR, 'ShiftId', '_') as BOARDSHIFT,
       to_number(F_KEY_VAL(LU_CHAR, 'Breakfast_Meal', '0'))
         as BOARDBREAKFAST,
       to_number(F_KEY_VAL(LU_CHAR, 'Lunch_Meal', '0'))
         as BOARDLUNCH,
       to_number(F_KEY_VAL(LU_CHAR, 'Dinner_Meal', '0'))
         as BOARDDINNER
       , ' ' as px_alpha
  from T_LU, (select 'Adults' as pax_type from dual union select 'Children' from dual), (select 'BHC' as resort from dual union select 'BHH' from dual union select 'HMC' from dual)
 where LU_CLASS = 'MKT_BOARDS'
union all
-- Direct Sale Mealplans
select distinct
       PX_RSREF as resort,
       pax_type, 
       case substr(px_alpha, 10, 1) when '0' then 'Daily' when '1' then '1 Day' else substr(px_alpha, 10, 1) || ' Days' end as Price_Per, lpad(to_char(px_charge) || ' �', 12) as Amount,  
       f_stragg(BoardDesc) as board_descs, 
       --f_stragg(BoardId) as board_ids, f_stragg(BoardShift) as Shifts, 
       BoardBreakfast, BoardLunch, BoardDinner
       --, px_code
       , px_alpha
  from (select case when substr(PX_ALPHA, 6, 1) = 'A' then 'Adults'
                    when substr(PX_ALPHA, 6, 1) = 'C' then 'Children' end as pax_type,
               substr(PX_ALPHA, 7, 3) as BT_BoardIds,
               PX_RSREF, PX_CHARGE, px_code
               , px_alpha
          from T_PX
         where substr(PX_ALPHA, 1, 5) = 'xMeal'
        ),
       (select LU_ID as BoardId, LU_DESC as BoardDesc,
               F_KEY_VAL(LU_CHAR, 'ShiftId', '_') as BoardShift,
               to_number(F_KEY_VAL(LU_CHAR, 'Breakfast_Meal', '0')) as BoardBreakfast,
               to_number(F_KEY_VAL(LU_CHAR, 'Lunch_Meal', '0')) as BoardLunch,
               to_number(F_KEY_VAL(LU_CHAR, 'Dinner_Meal', '0')) as BoardDinner
          from T_LU
         where LU_CLASS = 'BOARDS'
       )
 where instr(BT_BoardIds, BoardId) > 0 --and BT_Shift = BoardShift
 group by PX_RSREF, substr(px_alpha, 10, 1),
       BoardBreakfast, BoardLunch, BoardDinner,
       pax_type, PX_CHARGE, px_code
       , px_alpha
 order by 1, 4, 5, 2


select * from t_lu where lu_class like '%BOARDS' and upper(lu_desc) like '%ALL INC%' 


select * --BOARDID, BOARDDESC, RU_CODE 
from V_BOARD_MKT_MEALS
 where ru_code = 1020249
 order by ml_day



-- to be setup in SIHOT.PMS
select ro_code as MKT_SEG, ro_sihot_rate as RATE_SEG, ro_desc as SIHOT_MKT_SEG_DESC from t_ro where ro_sihot_rate is not null
 order by ro_desc
 

 
---############################  MARKETING CODES  #########################################################


--- overview over the 163 market source (reservation/occupation types) of the Acumen system
select RO_CODE as Short_Code, RO_SIHOT_MKT_SEG, RO_SIHOT_RATE, RO_DESC, RO_RES_GROUP, RO_INV_GROUP, RO_RES_CLASS, RO_SP_GROUP, CM_NAME as Commision_Mkt_Group
--     , substr(''
--          || case when RO_CM_REF_MKT is not NULL and CM_NAME is NULL then ', invalid CommGroupRef=' || RO_CM_REF_MKT end
--          , 3) as Discrepancies
  from T_RO, T_CM
 where 1=1
   --and ro_cm_ref_mkt = cm_ref(+) and cm_type(+) = 'M'
   and case when instr(ro_cm_ref_mkt, ',') > 0 then substr(ro_cm_ref_mkt, 1, instr(ro_cm_ref_mkt, ',') - 1) else ro_cm_ref_mkt end = cm_ref(+) and cm_type(+) = 'M'
   and RO_SIHOT_RATE is not NULL
 order by RO_DESC


-- grouped version using RO_RES_GROUP (AcuMktSourcesGrouped.xls)
select nvl(RO_RES_GROUP, 'Other') as Mkt_Group, count(*) as Booking_Types, f_stragg(ro_code) as Included_Short_Codes
  from t_ro
 group by nvl(RO_RES_GROUP, 'Other')
 order by 1


-- fixed wrong ro_cm_ref_mkt = 'GUEST' for PT type: changed to 'GEST'
update t_ro set ro_cm_ref_mkt = 'GEST' where ro_code = 'PT'



--#######################   USERS  (for training/holiday planning)  #########################################################

select distinct us_dept from t_us 

select nvl(us_dept, 'Div/Others') as dept, count(*) as users_in_dept, f_stragg(us_name) as user_names
  from t_us, dba_users
 where us_name = username
   and account_status = 'OPEN'
   and exists (select NULL from dba_role_privs
                where grantee = username 
                  and granted_role in ('XL_10_SUPERVISOR', 'XL_60_RESERVATIONS', 'XL_70_ACCOUNTING', 'SALES_60_RESERVATIONS', 'XL_20_RECEPCION', 'XL_30_HOUSEKEEPING', 'XL_30_MAINTENANCE', 'XL_80_EXTERNAL'))
   and us_name not in ('MFEE', 'FONEPOINT') -- FONEPOINT==Centralita/Char
 group by us_dept
 order by count(*) desc, us_dept
 

-- active users - sent by Geno on 10-08-16 15:41
SELECT GRANTEE, account_status,
 LTRIM(MAX(SYS_CONNECT_BY_PATH(GRANTED_ROLE,',')) KEEP (DENSE_RANK LAST ORDER BY curr),',') AS role_names 
FROM (SELECT GRANTEE, account_status, GRANTED_ROLE, ROW_NUMBER() OVER (PARTITION BY GRANTEE ORDER BY GRANTED_ROLE) AS curr,  ROW_NUMBER() OVER (PARTITION BY GRANTEE ORDER BY GRANTED_ROLE) -1 AS prev 
              FROM dba_role_privs r  INNER JOIN  dba_users u  ON  r.grantee = u.username 
      WHERE 1=1
        and u.account_status  in  ('OPEN' )  -- there are 'OPEN', 'LOCKED', 'EXPIRED ' || '&' || LOCKED'
        --AND u.username in ('ASORGON','CJENKINS','DHOWARD', 'JGERNON','PWALLBRIDGE'))'
        --and R.GRANTEd_ROLE   IN  ('SALES_49_MKTSUPER', 'SALES_50_MARKETING','SALES_51_TMSUPER','SALES_52_TELEMARKETING')  
        --and R.GRANTEd_ROLE NOT IN ('SALES_30_RESALES')
      )
GROUP BY GRANTEE, account_status 
CONNECT BY prev = PRIOR curr AND GRANTEE = PRIOR GRANTEE 
START WITH curr = 1

select * from dba_users



--###############    SALUTATIONS/TITLES    ####################################

select CD_TITL, count(*)
     , (select f_stragg(LG_CODE || '(' || LG_TITLE1 || '/' || LG_TITLE2 || ')') from T_LG where LG_TITLE1 = CD_TITL or LG_TITLE2 = CD_TITL) as Nationalities
  from (select CD_TITL1 as CD_TITL from T_CD where CD_TITL1 is not NULL union all select CD_TITL2 from T_CD where CD_TITL2 is not NULL)
 group by CD_TITL
-- having count(*) > 260
 order by count(*) desc
 

select LG_TITLE1, LG_TITLE2, LG_CODE from T_LG

select * from T_CD where CD_TITL1 is not null and F_SIHOT_SALUTATION(CD_TITL1) is NULL

select * from T_CD where CD_TITL2 is not null and F_SIHOT_SALUTATION(CD_TITL2) is NULL

select * from t_cd where instr(upper(cd_titl1), 'DR') > 0 and exists (select NULL from t_dw where dw_owref = cd_code) and exists (select NULL from t_ru where ru_cdref = cd_code and ru_from_date > sysdate)



--##############  CLIENT TYPE CLASSIFICATION (ACL_SIHOT_GUEST_TYPE)

select * from t_rs
 where rs_class = 'CONSTRUCT' or rs_class = 'BUILDING' and rs_group = 'A' order by rs_shortid


select cd_code
     , replace(f_stragg(distinct (select RS_SIHOT_GUEST_TYPE from T_RS where RS_CODE = F_RESORT(DW_WKREF))), ',', '')
     -- LISTAGG doesn't work either result is too long but DISTINCT is not supported: listagg(distinct (select RS_SIHOT_GUEST_TYPE from T_RS where RS_CODE = F_RESORT(DW_WKREF)), '') within group (order by 1) 
  from T_DW, T_CD where DW_OWREF = CD_CODE and (DW_STATUS in (770, 790) or DW_STATUS = 540 and nvl(DW_INOUT, 0) = 0) and f_resort(DW_WKREF) in (select RS_CODE from T_RS where RS_SIHOT_GUEST_TYPE is not NULL) --'PBF', 'TSP')
  group by cd_code

select cd_code
     , replace((select f_stragg(distinct RS_SIHOT_GUEST_TYPE) from T_DW, T_RS where DW_OWREF = CD_CODE and F_RESORT(DW_WKREF) = RS_CODE and (DW_STATUS in (770, 790) or DW_STATUS = 540 and nvl(DW_INOUT, 0) = 0) and RS_SIHOT_GUEST_TYPE is not NULL), ',', '')
     --, replace((select listagg(RS_SIHOT_GUEST_TYPE) within group (order by 1) from (select distinct RS_SIHOT_GUEST_TYPE from T_DW, T_RS where DW_OWREF = CD_CODE and F_RESORT(DW_WKREF) = RS_CODE and (DW_STATUS in (770, 790) or DW_STATUS = 540 and nvl(DW_INOUT, 0) = 0) and RS_SIHOT_GUEST_TYPE is not NULL)) , ',', '')
     --, replace(listagg((select distinct RS_SIHOT_GUEST_TYPE from T_RS where exists (select NULL from T_DW where DW_OWREF = CD_CODE and F_RESORT(DW_WKREF) = RS_CODE and (DW_STATUS in (770, 790) or DW_STATUS = 540 and nvl(DW_INOUT, 0) = 0)) and RS_SIHOT_GUEST_TYPE is not NULL)) within group (order by 1) , ',', '')
  from T_CD
  group by cd_code

select cd_code, cd_sihot_objid, f_sihot_guest_type(cd_code), v_acu_cd_unsynced.* from v_acu_cd_unsynced where  cd_code in ('E007434')

select * from t_ro where ro_cm_ref_mkt = 'PBRE' or RO_RES_GROUP = 'Rental SP' or RO_SP_GROUP = 'Rental SP'


select * from T_SRSL where srsl_logref is not null order by srsl_date desc

select * from v_acu_cd_log where acl_cdref  in ('E007434')

select ACL_DATE, SRSL_DATE, ACL_CDREF, ACL_CDLREF, SRSL_LOGREF, SRSL_STATUS, SRSL_ACTION, SRSL_MESSAGE --*   
  from V_ACU_CD_LOG
  left outer join T_SRSL on SRSL_TABLE = 'CD' and SRSL_PRIMARY = ACL_CDREF and SRSL_DATE < ACL_DATE and substr(SRSL_STATUS, 1, 6) = 'SYNCED' 
  left outer join V_ACU_CD_DATA on ACL_CDREF = CD_CODE
 where ACL_DATE >= '01-JUL-2016' -- speed-up: removing old/outdated log entries (before July 2016)
   and acl_cdref in ('E007434')
   order by ACL_CDLREF desc, ACL_DATE desc, ACL_CDLREF

select * from V_ACU_CD_UNSYNCED where CDREF in ('E007434')

update t_srsl set srsl_logref = -1 where srsl_logref is NULL

select * from t_cd where cd_sihot_objid = 294

--##############  EXTERNAL REFS/IDs FOR CLIENT

select distinct cr_type as ACU_TYPE, substr(cr_type, 1, 1) || substr(cr_type, -1) as SIHOT_TYPE, lu_desc as Description from t_cr, t_lu where cr_type = lu_id and lu_class = 'CLIENT_REF_TYPES'
 order by 2

select distinct cr_type from t_cr

-- check max. number of ext refs (see e.g. E396693=10, E355076=7, E261114=7 or E200548=6)
select cr_cdref, count(*) from t_cr
 group by cr_cdref
 order by count(*) desc)
