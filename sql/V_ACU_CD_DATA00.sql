create or replace view LOBBY.ACU_CD_DATA
  AS
select CD_CODE, case when instr(SIHOT_GUEST_TYPE, 'c') > 0 then CD_CODE || 'P2' end as CD_CODE2
     , nvl(trim(CD_SNAM1), 'z') as CD_SNAM1   -- hide this shame in Sihot by moving them to the end of the guest search list
     , case when instr(SIHOT_GUEST_TYPE, 'c') > 0 then nvl(trim(CD_SNAM2), 'y') end as CD_SNAM2 
     , CD_TITL1, CD_FNAM1, CD_DOB1, CD_INDUSTRY1
     , CD_TITL2, CD_FNAM2, CD_DOB2, CD_INDUSTRY2
     , CD_PASSWORD, CD_TYPE 
     , CD_ADD11, CD_ADD12, CD_ADD13, CD_POSTAL, CD_CITY
     , CD_COREF, CD_LGREF
     , CD_HTEL1, CD_WTEL1, CD_FAX, CD_WEXT1, CD_EMAIL, CD_SIGNUP_EMAIL, CD_MOBILE1, CD_LAST_SMS_TEL
     , CD_STATUS, CD_PAF_STATUS
     , CD_SIHOT_OBJID, CD_SIHOT_OBJID2
     , CD_RCI_REF
     -- converted/mapped values
     , F_SIHOT_SALUTATION(CD_TITL1) as SIHOT_SALUTATION1
     , F_SIHOT_SALUTATION(CD_TITL2) as SIHOT_SALUTATION2
     , case when instr(upper(CD_TITL1), 'PROF') > 0 then case when instr(upper(CD_TITL1), 'DR') > 0 then '3' else '2' end
            when instr(upper(CD_TITL1), 'DR') > 0 then '1' end as SIHOT_TITLE1
     , case when instr(upper(CD_TITL2), 'PROF') > 0 then case when instr(upper(CD_TITL2), 'DR') > 0 then '3' else '2' end
            when instr(upper(CD_TITL2), 'DR') > 0 then '1' end as SIHOT_TITLE2
     -- SIHOT GUEST TYPE - alternatively and not mandatory is PERS-TYPE
     -- 0=Accompaniment/Partner of Guest, 1=Guest, 2=Company, 3=Agencies, 4=Sales Office
     -- .. 5=Hotels, 6=Affiliated Company, 7=Tour operators, 8=Airlines, 9=Internals
     , --case when --instr(SIHOT_GUEST_TYPE, 'c') > 0 or  -- first person of couples or
                 --instr(SIHOT_GUEST_TYPE, 'O') > 0 or  -- .. owners (K=Keys Owner) 
       --          instr(SIHOT_GUEST_TYPE, 'I') > 0       -- .. investors get affiliated company and couples get linked 
       --     then '6' else '1' end as SIHOT_GUESTTYPE1   ae:07-12-2016 PROBLEM: Sihot cannot use company in reservation rooming/person list
       '1' as SIHOT_GUESTTYPE1     
     , case when instr(SIHOT_GUEST_TYPE, 'c') > 0 then '0' end as SIHOT_GUESTTYPE2   -- numeric 0/zero would be ignored by interface
     , (select CO_ISO2 from T_CO where CO_CODE = CD_COREF) as SIHOT_COUNTRY
     , (select LG_SIHOT_LANG from T_LG where LG_CODE = CD_LGREF) as SIHOT_LANG
     -- addtional values from other tables
     --, (select f_stragg(distinct CR_TYPE || '=' || CR_REF) from T_CR where CR_CDREF = CD_CODE) as EXT_REFS
     , (select f_stragg(distinct CR_TYPE || '=' || CR_REF) from (select CR_TYPE, CR_REF, CR_CDREF from T_CR 
                                                                 union all 
                                                                 select 'SF', MS_SF_ID, ML_CDREF from T_ML, T_MS where ML_CODE = MS_MLREF and MS_SF_ID is not NULL)
                                                          where CR_CDREF = CD_CODE) as EXT_REFS
     , (select max(MS_SF_ID) from T_ML, T_MS where ML_CODE = MS_MLREF and MS_SF_ID is not NULL and ML_CDREF = CD_CODE) as SIHOT_SF_ID
     , SIHOT_GUEST_TYPE 
  from (select F_SIHOT_GUEST_TYPE(CD_CODE) as SIHOT_GUEST_TYPE, T_CD.* from T_CD)
/*
  ae:27-08-16 first beta - for SIHOT sync/migration project.
*/
/


create or replace public synonym V_ACU_CD_DATA for LOBBY.ACU_CD_DATA;

grant select on LOBBY.ACU_CD_DATA to SALES_00_MASTER;
grant select on LOBBY.ACU_CD_DATA to SALES_05_SYSADMIN;
grant select on LOBBY.ACU_CD_DATA to SALES_06_DEVELOPER;
grant select on LOBBY.ACU_CD_DATA to SALES_10_SUPERVISOR;
grant select on LOBBY.ACU_CD_DATA to SALES_60_RESERVATIONS;

grant select on LOBBY.ACU_CD_DATA to XL_00_MASTER;
grant select on LOBBY.ACU_CD_DATA to XL_05_SYSADMIN;
grant select on LOBBY.ACU_CD_DATA to XL_06_DEVELOPER;
grant select on LOBBY.ACU_CD_DATA to XL_10_SUPERVISOR;
grant select on LOBBY.ACU_CD_DATA to XL_60_RESERVATIONS;

grant select on LOBBY.ACU_CD_DATA to REPORTER;

