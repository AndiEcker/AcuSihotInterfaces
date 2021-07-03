ALTER TABLE public.clients
    ADD COLUMN cl_surname character varying(42);

COMMENT ON COLUMN public.clients.cl_surname
    IS 'Surname of client';


ALTER TABLE public.clients
    ADD COLUMN cl_firstname character varying(42);

COMMENT ON COLUMN public.clients.cl_firstname
    IS 'Forename of client';

--select * from clients
-- where length(substr(clients.cl_name::text, strpos(clients.cl_name::text, ' '::text) + 1)) > 42
--    or length(split_part(clients.cl_name::text, ' '::text, 1)) > 42
update clients
   set cl_surname = substr(clients.cl_name::text, strpos(clients.cl_name::text, ' '::text) + 1, 42),
       cl_firstname = split_part(clients.cl_name::text, ' '::text, 1);

DROP VIEW v_clients_refs_owns;
CREATE OR REPLACE VIEW v_clients_refs_owns AS
  SELECT cl_pk, cl_ac_id, cl_sf_id, cl_sh_id
       -- , cl_name
       , cl_surname, cl_firstname
       , cl_email, cl_phone
       , (select string_agg(er_type || '=' || er_id, ',') FROM external_refs WHERE er_cl_fk = cl_pk) as ext_refs
       , (select string_agg(pt_group, '') FROM client_products
          INNER JOIN products ON cp_pr_fk = pr_pk INNER JOIN product_types ON pr_pt_fk = pt_pk
          WHERE cp_cl_fk = cl_pk) as owns
    FROM clients;

COMMENT ON VIEW v_clients_refs_owns IS 'clients extended by external_refs and owned pt_group(s) aggregates';

-- the query for a view to show clients with all duplicate external references is too slow (needs more than 24h)
-- .. therefore providing a separate view for each type of external reference: Acumen, Sf, Sihot, Email, Phone
DROP VIEW v_client_duplicates_ac;
CREATE OR REPLACE VIEW v_client_duplicates_ac AS
  SELECT a.cl_pk AS AssId_A, b.cl_pk AS AssId_B, a.cl_surname AS Name_A, b.cl_surname AS Name_B
       , SUBSTR(CASE WHEN a.cl_ac_id = b.cl_ac_id THEN ', AcuId=' || a.cl_ac_id ELSE '' END
             || CASE WHEN a.cl_sf_id = b.cl_sf_id THEN ', SfId=' || a.cl_sf_id ELSE '' END
             || CASE WHEN a.cl_sh_id = b.cl_sh_id THEN ', ShId=' || a.cl_sh_id ELSE '' END
             || CASE WHEN a.cl_email = b.cl_email THEN ', Email=' || a.cl_email ELSE '' END
             || CASE WHEN a.cl_phone = b.cl_phone THEN ', Phone=' || a.cl_phone ELSE '' END
             , 3) AS duplicates
    FROM clients a INNER JOIN clients b
        ON a.cl_pk < b.cl_pk AND a.cl_ac_id = b.cl_ac_id;

COMMENT ON VIEW v_client_duplicates_ac IS 'clients with duplicate Acumen client reference';

DROP VIEW v_client_duplicates_sf;
CREATE OR REPLACE VIEW v_client_duplicates_sf AS
  SELECT a.cl_pk AS AssId_A, b.cl_pk AS AssId_B, a.cl_surname AS Name_A, b.cl_surname AS Name_B
       , SUBSTR(CASE WHEN a.cl_ac_id = b.cl_ac_id THEN ', AcuId=' || a.cl_ac_id ELSE '' END
             || CASE WHEN a.cl_sf_id = b.cl_sf_id THEN ', SfId=' || a.cl_sf_id ELSE '' END
             || CASE WHEN a.cl_sh_id = b.cl_sh_id THEN ', ShId=' || a.cl_sh_id ELSE '' END
             || CASE WHEN a.cl_email = b.cl_email THEN ', Email=' || a.cl_email ELSE '' END
             || CASE WHEN a.cl_phone = b.cl_phone THEN ', Phone=' || a.cl_phone ELSE '' END
             , 3) AS duplicates
    FROM clients a INNER JOIN clients b
        ON a.cl_pk < b.cl_pk AND a.cl_sf_id = b.cl_sf_id;

COMMENT ON VIEW v_client_duplicates_sf IS 'clients with duplicate Salesforce ID';

DROP VIEW v_client_duplicates_sh;
CREATE OR REPLACE VIEW v_client_duplicates_sh AS
  SELECT a.cl_pk AS AssId_A, b.cl_pk AS AssId_B, a.cl_surname AS Name_A, b.cl_surname AS Name_B
       , SUBSTR(CASE WHEN a.cl_ac_id = b.cl_ac_id THEN ', AcuId=' || a.cl_ac_id ELSE '' END
             || CASE WHEN a.cl_sf_id = b.cl_sf_id THEN ', SfId=' || a.cl_sf_id ELSE '' END
             || CASE WHEN a.cl_sh_id = b.cl_sh_id THEN ', ShId=' || a.cl_sh_id ELSE '' END
             || CASE WHEN a.cl_email = b.cl_email THEN ', Email=' || a.cl_email ELSE '' END
             || CASE WHEN a.cl_phone = b.cl_phone THEN ', Phone=' || a.cl_phone ELSE '' END
             , 3) AS duplicates
    FROM clients a INNER JOIN clients b
        ON a.cl_pk < b.cl_pk AND a.cl_sh_id = b.cl_sh_id;

COMMENT ON VIEW v_client_duplicates_sh IS 'clients with duplicate Sihot guest object ID';

DROP VIEW v_client_duplicates_email;
CREATE OR REPLACE VIEW v_client_duplicates_email AS
  SELECT a.cl_pk AS AssId_A, b.cl_pk AS AssId_B, a.cl_surname AS Name_A, b.cl_surname AS Name_B
       , SUBSTR(CASE WHEN a.cl_ac_id = b.cl_ac_id THEN ', AcuId=' || a.cl_ac_id ELSE '' END
             || CASE WHEN a.cl_sf_id = b.cl_sf_id THEN ', SfId=' || a.cl_sf_id ELSE '' END
             || CASE WHEN a.cl_sh_id = b.cl_sh_id THEN ', ShId=' || a.cl_sh_id ELSE '' END
             || CASE WHEN a.cl_email = b.cl_email THEN ', Email=' || a.cl_email ELSE '' END
             || CASE WHEN a.cl_phone = b.cl_phone THEN ', Phone=' || a.cl_phone ELSE '' END
             , 3) AS duplicates
    FROM clients a INNER JOIN clients b
        ON a.cl_pk < b.cl_pk AND a.cl_email = b.cl_email;

COMMENT ON VIEW v_client_duplicates_email IS 'clients with duplicate email address';

DROP VIEW v_client_duplicates_phone;
CREATE OR REPLACE VIEW v_client_duplicates_phone AS
  SELECT a.cl_pk AS AssId_A, b.cl_pk AS AssId_B, a.cl_surname AS Name_A, b.cl_surname AS Name_B
       , SUBSTR(CASE WHEN a.cl_ac_id = b.cl_ac_id THEN ', AcuId=' || a.cl_ac_id ELSE '' END
             || CASE WHEN a.cl_sf_id = b.cl_sf_id THEN ', SfId=' || a.cl_sf_id ELSE '' END
             || CASE WHEN a.cl_sh_id = b.cl_sh_id THEN ', ShId=' || a.cl_sh_id ELSE '' END
             || CASE WHEN a.cl_email = b.cl_email THEN ', Email=' || a.cl_email ELSE '' END
             || CASE WHEN a.cl_phone = b.cl_phone THEN ', Phone=' || a.cl_phone ELSE '' END
             , 3) AS duplicates
    FROM clients a INNER JOIN clients b
        ON a.cl_pk < b.cl_pk AND a.cl_phone = b.cl_phone;

COMMENT ON VIEW v_client_duplicates_phone IS 'clients with duplicate phone number';


-- finally remove the old client name column
ALTER TABLE public.clients DROP COLUMN cl_name;

