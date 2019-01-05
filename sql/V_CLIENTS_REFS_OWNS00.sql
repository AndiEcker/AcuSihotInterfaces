create or replace view LOBBY.CLIENTS_REFS_OWNS
  AS
select CD_CODE as CODE
     , nvl(CD_SF_ID1, (select max(MS_SF_ID) from T_ML, T_MS where ML_CODE = MS_MLREF and MS_SF_ID is not NULL and ML_CDREF = CD_CODE)) as SF_ID
     , to_char(CD_SIHOT_OBJID) as SH_ID
     , CD_FNAM1 || ' ' || CD_SNAM1 as NAME
     , F_EMAIL_CLEANED(CD_EMAIL) as EMAIL
     , nvl(CD_HTEL1, nvl(CD_MOBILE1, CD_WTEL1 || CD_WEXT1)) as PHONE
     , CD_RCI_REF as RCI_REF
     , (select f_stragg(distinct CR_TYPE || '=' || CR_REF) from (select DISTINCT decode(CR_TYPE, 'RCIP', 'RCI', 'SPX', 'RCI', 'KEYS', 'RCI', CR_TYPE) as CR_TYPE, CR_REF, CR_CDREF from T_CR 
                                                                 union all 
                                                                 select 'SF', MS_SF_ID, ML_CDREF from T_ML, T_MS where ML_CODE = MS_MLREF and MS_SF_ID is not NULL
                                                                 union
                                                                 select 'SF', CD_SF_ID1, CD_CODE from T_CD where CD_SF_ID1 is not NULL
                                                                 union
                                                                 select 'SF', CD_SF_ID2, CD_CODE from T_CD where CD_SF_ID2 is not NULL)
                                                          where CR_CDREF = CD_CODE) as EXT_REFS
  --   , SIHOT_GUEST_TYPE as OWNS
  --from (select F_SIHOT_GUEST_TYPE(CD_CODE) as SIHOT_GUEST_TYPE, T_CD.* from T_CD)
       , F_SIHOT_GUEST_TYPE(CD_CODE) as OWNS
  from T_CD
 where substr(CD_CODE, 1, 1) <> 'A' and (CD_SNAM1 is not NULL or CD_FNAM1 is not NULL)
UNION ALL
select CD_CODE || 'P2' as CODE
     , CD_SF_ID2 as SF_ID
     , to_char(CD_SIHOT_OBJID2) as SH_ID
     , CD_FNAM2 || ' ' || CD_SNAM2 as NAME
     , F_EMAIL_CLEANED(CD_EMAIL, 1) as EMAIL
     , NULL as PHONE
     , NULL as RCI_REF
     , NULL as EXT_REFS
     , NULL as OWNS
  from T_CD
 where substr(CD_CODE, 1, 1) <> 'A' and (CD_SNAM2 is not NULL or CD_FNAM2 is not NULL)
/*
  ae:03-01-19 first beta - for SysDataMan/ae_sys_data refactoring.
*/
/


create or replace public synonym V_CLIENTS_REFS_OWNS for LOBBY.CLIENTS_REFS_OWNS;

grant select on LOBBY.CLIENTS_REFS_OWNS to SALES_00_MASTER;
grant select on LOBBY.CLIENTS_REFS_OWNS to SALES_05_SYSADMIN;
grant select on LOBBY.CLIENTS_REFS_OWNS to SALES_06_DEVELOPER;
grant select on LOBBY.CLIENTS_REFS_OWNS to SALES_10_SUPERVISOR;
grant select on LOBBY.CLIENTS_REFS_OWNS to SALES_60_RESERVATIONS;

grant select on LOBBY.CLIENTS_REFS_OWNS to XL_00_MASTER;
grant select on LOBBY.CLIENTS_REFS_OWNS to XL_05_SYSADMIN;
grant select on LOBBY.CLIENTS_REFS_OWNS to XL_06_DEVELOPER;
grant select on LOBBY.CLIENTS_REFS_OWNS to XL_10_SUPERVISOR;
grant select on LOBBY.CLIENTS_REFS_OWNS to XL_60_RESERVATIONS;

grant select on LOBBY.CLIENTS_REFS_OWNS to REPORTER;

