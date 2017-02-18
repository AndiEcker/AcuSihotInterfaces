CREATE OR REPLACE FUNCTION SALES.KEY_VAL (pcString IN varchar2, pcKey IN varchar2, pcDefaultValue IN varchar2 := '')
   RETURN varchar2
IS
   ccKeyValSeps constant varchar2(100) := ' ,;~&?/!#"''' || chr(13) || chr(10); 
   lcSeps varchar2(1000);
   lnPos1 integer := -1;
   lnPos2 integer := 0;
BEGIN
   loop
      lnPos1 := instr(substr(pcString, lnPos2 + 1), pcKey || '=') + lnPos1 + 1;
      exit when lnPos1 is NULL or lnPos1 = 0;
      -- check if char left of key is a seperator char, else search more further in pcString
      if lnPos1 = 1 or instr(ccKeyValSeps, substr(pcString, lnPos1-1, 1)) > 0 then
         lnPos1 := lnPos1 + length(pcKey) + 1;
         -- no spaces allowed between key and value!
         lcSeps := substr(pcString, lnPos1, 1);
         if instr('''"', lcSeps) = 0 then -- no enclosed value -  - search end of value / next seperator
            lcSeps := ccKeyValSeps;
         else
            lnPos1 := lnPos1 + 1;
         end if;
         lnPos2 := lnPos1;
         while lnPos2 <= length(pcString) and instr(lcSeps, substr(pcString, lnPos2, 1)) = 0 loop
            lnPos2 := lnPos2 + 1;
         end loop;
         -- RETURN keyval - trim removes closing high comma/apostrophe
         return substr(pcString, lnPos1, lnPos2 - lnPos1);
      end if;
      lnPos2 := lnPos1;
   end loop;
   
   return pcDefaultValue;
END;
/*
  ae:05-12-10 first beta
  ae:21-08-12 added execute grants to all XL user roles.
  ae:10-02-17 V02: fixed bug (endless loop, e.g. with f_key_Val('ctest=1', 'test')) if key is not on pos1 or does not have sep char to the left
              and added chr(13) and chr(10) to seperator chars (ccKeyValSeps).  
*/
/

GRANT EXECUTE ON SALES.KEY_VAL TO SALES_00_MASTER;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_05_SYSADMIN;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_06_DEVELOPER;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_10_SUPERVISOR;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_11_SUPERASSIST;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_15_CENTRAL;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_20_CONTRACTS;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_30_RESALES;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_40_COMPLETIONS;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_50_MARKETING;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_52_TELEMARKETING;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_55_MANAGEMENT;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_56_TOS;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_60_RESERVATIONS;
GRANT EXECUTE ON SALES.KEY_VAL TO SALES_70_ACCOUNTING;

GRANT EXECUTE ON SALES.KEY_VAL TO XL_10_SUPERVISOR;
GRANT EXECUTE ON SALES.KEY_VAL TO XL_20_RECEPCION;
GRANT EXECUTE ON SALES.KEY_VAL TO XL_30_HOUSEKEEPING;
GRANT EXECUTE ON SALES.KEY_VAL TO XL_30_MAINTENANCE;
GRANT EXECUTE ON SALES.KEY_VAL TO XL_40_MFEES;
GRANT EXECUTE ON SALES.KEY_VAL TO XL_50_MARKETING;
GRANT EXECUTE ON SALES.KEY_VAL TO XL_55_MANAGEMENT;
GRANT EXECUTE ON SALES.KEY_VAL TO XL_60_RESERVATIONS;
GRANT EXECUTE ON SALES.KEY_VAL TO XL_70_ACCOUNTING;

drop public synonym F_KEY_VAL;
create or replace public synonym F_KEY_VAL FOR SALES.KEY_VAL;
