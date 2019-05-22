-- need to first drop all views that are containing this column
DROP VIEW v_clients_refs_owns;

-- extend firstname from 42 to 45 characters
ALTER TABLE public.clients
    ALTER COLUMN cl_firstname TYPE character varying (45) COLLATE pg_catalog."default";

ALTER TABLE public.res_group_clients
    ALTER COLUMN rgc_firstname TYPE character varying (45) COLLATE pg_catalog."default";

-- finally recreate the depending view
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
