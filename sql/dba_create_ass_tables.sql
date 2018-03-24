------ TABLE STRUCTURES
---- CLIENT DATA
-- client client ids on external systems
CREATE TABLE clients
(
  cl_pk                   SERIAL PRIMARY KEY,
  cl_ac_id                VARCHAR(12),      -- 83 acumen clients having acu_id + 'D1' + 'P2', e.g. G022570D1P2,
                                            -- .. E127673D1P2, Z000020D1P2, I127633D1P2, but also refs like MAINTENANC
  cl_sf_id                VARCHAR(18),
  cl_sh_id                VARCHAR(15),
  UNIQUE (cl_ac_id, cl_sf_id, cl_sh_id)
);
-- noinspection SqlResolve
SELECT audit.audit_table('clients');

-- client client external references (initially mainly used for to store multiple RCI Ids for each client)
CREATE TABLE external_refs
(
  er_cl_fk                INTEGER NOT NULL REFERENCES clients(cl_pk),
  er_type                 VARCHAR(6) NOT NULL,
  er_id                   VARCHAR(18) NOT NULL,
  UNIQUE (er_cl_fk, er_type, er_id)
);
-- noinspection SqlResolve
SELECT audit.audit_table('external_refs');

-- product
CREATE TABLE product_types
(
  pt_pk                   VARCHAR(3) PRIMARY KEY NOT NULL,  -- RS_CODE
  pt_group                VARCHAR(1) NOT NULL,              -- RS_SIHOT_GUEST_TYPE (O=owner, I=investor, K=keys, E=ELPP)
  pt_name                 VARCHAR(39) NOT NULL              -- RS_NAME
);
-- noinspection SqlResolve
SELECT audit.audit_table('product_types');

CREATE TABLE products
(
  pr_pk                   VARCHAR(12) PRIMARY KEY NOT NULL,
  pr_pt_fk                VARCHAR(3) NOT NULL REFERENCES product_types(pt_pk)
);
-- noinspection SqlResolve
SELECT audit.audit_table('products');

CREATE TABLE client_products
(
  cp_cl_fk                INTEGER NOT NULL REFERENCES clients(cl_pk),
  cp_pr_fk                VARCHAR(12) NOT NULL REFERENCES products(pr_pk),
  PRIMARY KEY (cp_cl_fk, cp_pr_fk)
);
-- noinspection SqlResolve
SELECT audit.audit_table('client_products');



---- HOTEL AND ROOM CONFIGURATION - currently defined/configured in .console_app_env.cfg
-- hotels
CREATE TABLE hotels
(
  ho_pk                   VARCHAR(3) PRIMARY KEY,
  ho_ac_id                VARCHAR(3) NOT NULL,
  UNIQUE (ho_ac_id)
);
-- noinspection SqlResolve
SELECT audit.audit_table('hotels');

INSERT INTO hotels VALUES ('1', 'BHC');
INSERT INTO hotels VALUES ('2', 'BHH');
INSERT INTO hotels VALUES ('3', 'HMC');
INSERT INTO hotels VALUES ('4', 'PBC');
--INSERT INTO hotels VALUES ('999', 'ANY');
COMMIT;


-- still missing: categories, hotel_categories, room_categories)



---- RESERVATION ENVIRONMENT
-- reservation inventory
CREATE TABLE res_inventories
(
  ri_pk                   SERIAL PRIMARY KEY,
  ri_pr_fk                VARCHAR(12) NOT NULL REFERENCES products(pr_pk),
  ri_ho_fk                VARCHAR(3) NOT NULL REFERENCES hotels(ho_pk),
  ri_usage_year           INTEGER NOT NULL,
  ri_inv_type             VARCHAR(3) NOT NULL,
  ri_swapped_product_id   VARCHAR(12),
  ri_granted_to           VARCHAR(3),
  ri_used_points          VARCHAR(9),           -- 'i' prefixed if individual owner points value
  ri_usage_comment        VARCHAR(33),          -- for Esther/Nancy Status Entitlement Usage spreadsheet column
  UNIQUE (ri_ho_fk, ri_pr_fk, ri_usage_year)
);
-- noinspection SqlResolve
SELECT audit.audit_table('res_inventories');

-- reservations
/* .. columns not included from V_ACU_RES_DATA/_UNSYNCED or indirectly included via clients table
    RU_SOURCE	15	VARCHAR2 (1 Byte)	Y
    RO_RES_GROUP	17	VARCHAR2 (40 Byte)	Y
    RO_RES_CLASS	18	VARCHAR2 (12 Byte)	Y
    RO_SP_GROUP	19	VARCHAR2 (40 Byte)	Y
    RO_SIHOT_RES_GROUP	21	VARCHAR2 (2 Byte)	Y
    RO_SIHOT_SP_GROUP	22	VARCHAR2 (2 Byte)	Y
    RH_GROUP_ID	25	NUMBER (9)	Y
    CD_CODE2	27	VARCHAR2 (12 Byte)	Y
    CD_SIHOT_OBJID	28	NUMBER (9)	Y
    CD_SIHOT_OBJID2	29	NUMBER (9)	Y
    CD_RCI_REF	30	VARCHAR2 (10 Byte)	Y
    OC_SIHOT_OBJID	32	NUMBER	Y
    OC_CODE	33	VARCHAR2 (10 Byte)	Y
    SIHOT_LINK_GROUP	35	VARCHAR2 (97 Byte)	Y
    SIHOT_RES_TYPE	38	CHAR (1 Byte)	Y
    RUL_*  (apart from RUL_SIHOT_PACK)
   .. columns not included from Esther's Reservation_Fields_Salesforce spreadsheet:
    Year (indirectly included via ri_usage_year)
    Week nr(s)	if possible RCI calendar weeks (indirectly included via ri_pr_fk - the value after the hyphen character)
    Nights	amount of nights for the duration of stay (indirectly included via rgr_departure - rgr_arrival)
    Extra Reservation Changes
    Points Value (indirectly included via ri_used_points)
    Apartment Features (indirectly via rgr_room_cat_id)
    Pre-voucher code
    Confirmed Voucher code
    WebPreCki
*/
CREATE TABLE res_groups
(
  rgr_pk                  SERIAL PRIMARY KEY,
  rgr_ho_fk               VARCHAR(3) NOT NULL REFERENCES hotels(ho_pk),   -- SIHOT hotel id (e.g. '1'==BHC, ...)
  rgr_res_id              VARCHAR(18) NOT NULL,     -- SIHOT reservation id (res-number / sub-number)
  rgr_sub_id              VARCHAR(3) NOT NULL,
  rgr_gds_no              VARCHAR(24),              -- opt. SIHOT reservation GDSNO (OBJID not available in RES-SEARCH)
  rgr_order_cl_fk         INTEGER REFERENCES clients(cl_pk),
  rgr_used_ri_fk          INTEGER REFERENCES res_inventories(ri_pk),
  rgr_rci_deposit_ri_fk   INTEGER REFERENCES res_inventories(ri_pk),
  rgr_status              VARCHAR(3) NOT NULL,
  rgr_adults              INTEGER NOT NULL DEFAULT 2,
  rgr_children            INTEGER NOT NULL DEFAULT 0,
  rgr_arrival             DATE,
  rgr_departure           DATE,
  rgr_mkt_segment         VARCHAR(3),
  rgr_mkt_group           VARCHAR(3),
  rgr_room_cat_id         VARCHAR(6),
  rgr_room_rate           VARCHAR(3),
  rgr_payment_inst        VARCHAR(3),
  rgr_ext_book_id         VARCHAR(21),
  rgr_ext_book_day        DATE,
  rgr_comment             VARCHAR(540),
  rgr_long_comment        VARCHAR(3999),
  rgr_time_in             TIMESTAMP,
  rgr_time_out            TIMESTAMP,
  rgr_created_by          VARCHAR(18) NOT NULL DEFAULT user,
  rgr_created_when        TIMESTAMP NOT NULL DEFAULT current_timestamp,
  rgr_last_change         TIMESTAMP NOT NULL DEFAULT current_timestamp,   -- upsert of external system (mostly Sihot)
  rgr_last_sync           TIMESTAMP,                                      -- last sync to Salesforce
  UNIQUE (rgr_ho_fk, rgr_res_id, rgr_sub_id)
);
-- noinspection SqlResolve
SELECT audit.audit_table('res_groups');

CREATE OR REPLACE FUNCTION rgr_modified()
RETURNS TRIGGER AS $$
BEGIN
    NEW.rgr_last_change = now();
    RETURN NEW;
END;
$$ language 'plpgsql';
CREATE TRIGGER rgr_modified_trigger BEFORE UPDATE ON res_groups FOR EACH ROW EXECUTE PROCEDURE rgr_modified();

CREATE TABLE res_group_clients
(
  rgc_rgr_fk              INTEGER NOT NULL REFERENCES res_groups(rgr_pk),
  rgc_room_seq            INTEGER NOT NULL DEFAULT 0,
  rgc_pers_seq            INTEGER NOT NULL DEFAULT 0,
  rgc_surname             VARCHAR(42) NOT NULL,
  rgc_firstname           VARCHAR(42) NOT NULL,
  rgc_email               VARCHAR(42),
  rgc_phone               VARCHAR(42),
  rgc_dob                 DATE,
  rgc_auto_generated      VARCHAR(1) NOT NULL DEFAULT '1',
  rgc_occup_cl_fk         INTEGER REFERENCES clients(cl_pk),  -- referencing Sihot guest as Salesforce client
  rgc_flight_arr_comment  VARCHAR(42),      -- arrival airport, airline and flight number
  rgc_flight_arr_time     TIME,             -- ETA
  rgc_flight_dep_comment  VARCHAR(42),
  rgc_flight_dep_time     TIME,
  rgc_pers_type           VARCHAR(3) NOT NULL DEFAULT '1A',
  rgc_sh_pack             VARCHAR(3),
  rgc_room_id             VARCHAR(6),
  UNIQUE (rgc_rgr_fk, rgc_room_seq, rgc_pers_seq)
);
-- noinspection SqlResolve
SELECT audit.audit_table('res_group_clients');


------ VIEWS
---- CLIENT VIEWS
-- view for AssSysDate.cl_fetch_all() extending clients table with external refs and pt_group aggregates
CREATE OR REPLACE VIEW v_clients_refs_owns AS
  SELECT cl_pk, cl_ac_id, cl_sf_id, cl_sh_id
       , (select string_agg(er_type || '=' || er_id, ',') FROM external_refs WHERE er_cl_fk = cl_pk) as ext_refs
       , (select string_agg(pt_group, '') FROM client_products
          INNER JOIN products ON cp_pr_fk = pr_pk INNER JOIN product_types ON pr_pt_fk = pt_pk
          WHERE cp_cl_fk = cl_pk) as owns
    FROM clients;

COMMENT ON VIEW v_clients_refs_owns IS 'clients extended by external_refs and owned pt_group(s) aggregates';
