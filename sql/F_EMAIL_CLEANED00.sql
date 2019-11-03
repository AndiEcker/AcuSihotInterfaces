create or replace function SALES.EMAIL_CLEANED( p_email IN varchar2, p_2nd_line IN number := 0 )
  return varchar2
is
  -- invalid characters in our Acumen email addresses (full check done later by sys_data_sf.py/correct_email())
  l_inval   varchar2(4000) := chr(10) || chr(13) || chr(9) || ' (),:;<>[\]';
  l_email   varchar2(4000);
  l_offset  number;
begin
  -- remove invalid characters from begin/end
  l_email := ltrim(rtrim(p_email, l_inval), l_inval);
  
  -- check for multiple emails (separated with CR and/or LF)
  l_offset := instr(l_email, chr(13));
  if l_offset = 0 then
    l_offset := instr(l_email, chr(10));
  end if;
  if l_offset > 0 then
    if p_2nd_line = 0 then
      l_email := substr(l_email, 1, l_offset - 1);
    else
      l_email := substr(l_email, l_offset);
    end if;
  elsif p_2nd_line != 0 then
    l_email := '';
  end if;

  if l_email is not NULL then
    -- remove invalid characters within the email address
    l_offset := 1;  
    loop
      l_email := replace(l_email, substr(l_inval, l_offset, 1));
      exit when l_offset >= length(l_inval);
      l_offset := l_offset + 1;
    end loop;
  
    -- suppress emails containing CLIENTHASNOEMAIL
    if instr(upper(l_email), 'CLIENTHASNOEMAIL') > 0 then
      l_email := '';    -- NULL
    end if;
  end if;
  
  return l_email; 
end
/*
  ae:19-04-18 V00: first rolled out beta.
*/;
/

create or replace public synonym F_EMAIL_CLEANED for SALES.EMAIL_CLEANED;

grant execute on SALES.EMAIL_CLEANED to SALES_00_MASTER;
grant execute on SALES.EMAIL_CLEANED to SALES_05_SYSADMIN;
grant execute on SALES.EMAIL_CLEANED to SALES_06_DEVELOPER;
grant execute on SALES.EMAIL_CLEANED to SALES_10_SUPERVISOR;
grant execute on SALES.EMAIL_CLEANED to SALES_11_SUPERASSIST;
grant execute on SALES.EMAIL_CLEANED to SALES_15_CENTRAL;
grant execute on SALES.EMAIL_CLEANED to SALES_20_CONTRACTS;
grant execute on SALES.EMAIL_CLEANED to SALES_30_RESALES;
grant execute on SALES.EMAIL_CLEANED to SALES_40_COMPLETIONS;
grant execute on SALES.EMAIL_CLEANED to SALES_47_KEYS;
grant execute on SALES.EMAIL_CLEANED to SALES_49_MKTSUPER;
grant execute on SALES.EMAIL_CLEANED to SALES_50_MARKETING;
grant execute on SALES.EMAIL_CLEANED to SALES_52_TELEMARKETING;
grant execute on SALES.EMAIL_CLEANED to SALES_55_MANAGEMENT;
grant execute on SALES.EMAIL_CLEANED to SALES_56_TOS;
grant execute on SALES.EMAIL_CLEANED to SALES_60_RESERVATIONS;
grant execute on SALES.EMAIL_CLEANED to SALES_70_ACCOUNTING;
grant execute on SALES.EMAIL_CLEANED to SALES_80_EXTERNAL;
grant execute on SALES.EMAIL_CLEANED to SALES_95_MARKETING_TRAINING;

grant execute on SALES.EMAIL_CLEANED to XL_00_MASTER;
grant execute on SALES.EMAIL_CLEANED to XL_05_SYSADMIN;
grant execute on SALES.EMAIL_CLEANED to XL_06_DEVELOPER;
grant execute on SALES.EMAIL_CLEANED to XL_10_SUPERVISOR;
grant execute on SALES.EMAIL_CLEANED to XL_20_RECEPCION;
grant execute on SALES.EMAIL_CLEANED to XL_30_HOUSEKEEPING;
grant execute on SALES.EMAIL_CLEANED to XL_30_MAINTENANCE;
grant execute on SALES.EMAIL_CLEANED to XL_40_MFEES;
grant execute on SALES.EMAIL_CLEANED to XL_50_MARKETING;
grant execute on SALES.EMAIL_CLEANED to XL_55_MANAGEMENT;
grant execute on SALES.EMAIL_CLEANED to XL_60_RESERVATIONS;
grant execute on SALES.EMAIL_CLEANED to XL_70_ACCOUNTING;
grant execute on SALES.EMAIL_CLEANED to XL_80_EXTERNAL;

grant execute on SALES.EMAIL_CLEANED to REPORTER;
