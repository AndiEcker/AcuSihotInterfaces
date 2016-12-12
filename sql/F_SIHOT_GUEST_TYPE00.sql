create or replace function LOBBY.SIHOT_GUEST_TYPE(pcCD_Code IN T_CD.CD_CODE%type)
  RETURN varchar2
IS  
  lcType   varchar2(2000 Byte);

BEGIN
  -- return a string with classification flags/characters for the Acumen client in pcCD_Code - needed by V_ACU_CD_DATA for to determine the value SIHOT guest type (0...9)
  select (select listagg(RS_SIHOT_GUEST_TYPE) within group (order by RS_SIHOT_GUEST_TYPE)    -- acumen client/owner type(s): O=Owner, I=Investor, K=Keys Client
            from (select distinct RS_SIHOT_GUEST_TYPE from T_DW, T_RS where DW_OWREF = pcCD_Code and F_RESORT(DW_WKREF) = RS_CODE 
                                                                        and (DW_STATUS in (770, 790) or DW_STATUS = 540 and nvl(DW_INOUT, 0) = 0) 
                                                                        and RS_SIHOT_GUEST_TYPE is not NULL))
                                                                                             -- plus RENTAL reservation check
         || case when (select count(*) from T_ARO, T_RO where ARO_ROREF = RO_CODE and ARO_CDREF = pcCD_Code and ARO_STATUS <> 120 and RO_CM_REF_MKT = 'PBRE') > 0 then 'R' end
                                                                                              -- plus single/couple check
         || case when (select 1 from T_CD where CD_CODE = pcCD_Code and CD_FNAM2 is NULL and CD_SNAM2 is NULL) = 1 then 's'   -- single person
                                                                                                                   else 'c' end  -- couple
    into lcType from dual;
    
  return lcType;
END
/*
  ae:27-08-16 V00: first beta - added for SIHOT sync/migration project.
*/;
/


create or replace public synonym F_SIHOT_GUEST_TYPE for LOBBY.SIHOT_GUEST_TYPE;

grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_00_MASTER;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_05_SYSADMIN;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_06_DEVELOPER;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_11_SUPERASSIST;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_15_CENTRAL;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_20_CONTRACTS;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_30_RESALES;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_40_COMPLETIONS;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_47_KEYS;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_49_MKTSUPER;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_50_MARKETING;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_52_TELEMARKETING;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_56_TOS;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_80_EXTERNAL;
grant execute on LOBBY.SIHOT_GUEST_TYPE to SALES_95_MARKETING_TRAINING;

grant execute on LOBBY.SIHOT_GUEST_TYPE to XL_00_MASTER;
grant execute on LOBBY.SIHOT_GUEST_TYPE to XL_05_SYSADMIN;
grant execute on LOBBY.SIHOT_GUEST_TYPE to XL_06_DEVELOPER;
grant execute on LOBBY.SIHOT_GUEST_TYPE to XL_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_GUEST_TYPE to XL_20_RECEPCION;
grant execute on LOBBY.SIHOT_GUEST_TYPE to XL_30_HOUSEKEEPING;
grant execute on LOBBY.SIHOT_GUEST_TYPE to XL_30_MAINTENANCE;
grant execute on LOBBY.SIHOT_GUEST_TYPE to XL_40_MFEES;
grant execute on LOBBY.SIHOT_GUEST_TYPE to XL_50_MARKETING;
grant execute on LOBBY.SIHOT_GUEST_TYPE to XL_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_GUEST_TYPE to XL_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_GUEST_TYPE to XL_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_GUEST_TYPE to XL_80_EXTERNAL;

grant execute on LOBBY.SIHOT_GUEST_TYPE to REPORTER;