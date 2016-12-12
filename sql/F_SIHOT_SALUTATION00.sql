create or replace function LOBBY.SIHOT_SALUTATION (pcTitle IN T_CD.CD_TITL1%type)
  RETURN varchar2
IS
  SIHOT_SALUTATION_COMPANY constant varchar2(1) := '6'; -- 0=Company(reserved), 6=Affiliated Company
  SIHOT_SALUTATION_MISTER  constant varchar2(1) := '1';
  SIHOT_SALUTATION_MISSES  constant varchar2(1) := '2';
  SIHOT_SALUTATION_MR_MRS  constant varchar2(1) := '3';
  
  lcSalutation  varchar2(1);  -- now determines only the sex of the person: '1'==Male, '2'=Femaile but co-mapped in Sihot with nationality gives then the real salutation
  
  cursor cTitle1 is
    select SIHOT_SALUTATION_MISTER from T_LG where LG_TITLE1 = pcTitle;
  cursor cTitle2 is
    select SIHOT_SALUTATION_MISSES from T_LG where LG_TITLE2 = pcTitle;
BEGIN
  -- rename/remap typos of manually entered salutations (to match LG_TITLE1/2 values in T_LG) - see lines 223++ in Q_SIHOT_SETUP1.sql
  if upper(pcTitle) in    ('CAPT', 'LORD', 'MAJOR', 'MR', 'MR D', 'MAJOR', 'SGT',       -- Mr
                           'HERRA',                                                     -- Herra/FIN
                           'SIGNOR', 'SIG', 'SR', 'SNR', 'SRE', 'SEÑORA',               -- Sr/ITA+POR+SPA
                           'HERR', 'HR', 'DR', 'HERR DR', 'ING', 'PROF', 'HER', 'HERRN', 'HEER'  -- Herr/SCA+GER
                        ) then
    lcSalutation := SIHOT_SALUTATION_MISTER;
  elsif upper(pcTitle) in ('MRS', 'MRS', 'MISS', 'MS', 'MSR', 'MSS', 'LADY', 'MISSES',  -- Mrs
                           'MELLE', 'MLLE', 'MLE', 'M/MME', 'MEJ',                      -- Mme
                           'MERV',                                                      -- Mevr/DUT
                           'FRAU', 'FR', 'FRAU DR',                                     -- Frau
                           'FRU', 'FRK', 'FRÖKEN', 'NEITI',                             -- Fru/SCA
                           'ROUVA',                                                     -- Rouva/FIN
                           'SIGNORA', 'SIGRA', 'SIG RA', 'SIG.RA', 'SIG. RA', 'SIG.NA', 'SRA', 'SNRA'  -- Sra/ITA+POR+SPA
                           ) then 
    lcSalutation := SIHOT_SALUTATION_MISSES;
  else
    open  cTitle2;
    fetch cTitle2 into lcSalutation;
    if cTitle2%notfound then
      open  cTitle1;
      fetch cTitle1 into lcSalutation;
      close cTitle1;
    end if;
    close cTitle2;
  end if;
  
  return lcSalutation;  -- nvl(lcSalutation, SIHOT_SALUTATION_COMPANY)
END
/*
  ae:23-08-16 V00: first beta - added for SIHOT sync/migration project.
*/;
/


create or replace public synonym F_SIHOT_SALUTATION for LOBBY.SIHOT_SALUTATION;

grant execute on LOBBY.SIHOT_SALUTATION to SALES_00_MASTER;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_05_SYSADMIN;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_06_DEVELOPER;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_11_SUPERASSIST;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_15_CENTRAL;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_20_CONTRACTS;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_30_RESALES;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_40_COMPLETIONS;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_47_KEYS;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_49_MKTSUPER;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_50_MARKETING;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_52_TELEMARKETING;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_56_TOS;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_80_EXTERNAL;
grant execute on LOBBY.SIHOT_SALUTATION to SALES_95_MARKETING_TRAINING;

grant execute on LOBBY.SIHOT_SALUTATION to XL_00_MASTER;
grant execute on LOBBY.SIHOT_SALUTATION to XL_05_SYSADMIN;
grant execute on LOBBY.SIHOT_SALUTATION to XL_06_DEVELOPER;
grant execute on LOBBY.SIHOT_SALUTATION to XL_10_SUPERVISOR;
grant execute on LOBBY.SIHOT_SALUTATION to XL_20_RECEPCION;
grant execute on LOBBY.SIHOT_SALUTATION to XL_30_HOUSEKEEPING;
grant execute on LOBBY.SIHOT_SALUTATION to XL_30_MAINTENANCE;
grant execute on LOBBY.SIHOT_SALUTATION to XL_40_MFEES;
grant execute on LOBBY.SIHOT_SALUTATION to XL_50_MARKETING;
grant execute on LOBBY.SIHOT_SALUTATION to XL_55_MANAGEMENT;
grant execute on LOBBY.SIHOT_SALUTATION to XL_60_RESERVATIONS;
grant execute on LOBBY.SIHOT_SALUTATION to XL_70_ACCOUNTING;
grant execute on LOBBY.SIHOT_SALUTATION to XL_80_EXTERNAL;

grant execute on LOBBY.SIHOT_SALUTATION to REPORTER;