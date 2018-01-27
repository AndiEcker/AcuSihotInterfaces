-- client contact
CREATE TABLE contacts
(
  co_pk                   SERIAL PRIMARY KEY,
  co_sf_contact_id        VARCHAR(18),
  co_sh_guest_id          VARCHAR(15),
  co_sh_match_code        VARCHAR(18)
);
-- noinspection SqlResolve
SELECT audit.audit_table('contacts');

-- client contact external references (initially mainly used for to store multiple RCI Ids for each contact)
CREATE TABLE external_refs
(
  er_co_fk                INTEGER NOT NULL REFERENCES contacts(co_pk),
  er_type                 VARCHAR(6) NOT NULL,
  er_id                   VARCHAR(18) NOT NULL
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

CREATE TABLE contact_products
(
  cp_co_fk                INTEGER NOT NULL REFERENCES contacts(co_pk),
  cp_pr_fk                VARCHAR(12) NOT NULL REFERENCES products(pr_pk),
  PRIMARY KEY (cp_co_fk, cp_pr_fk)
);
-- noinspection SqlResolve
SELECT audit.audit_table('contact_products');

-- reservation inventory
CREATE TABLE res_inventories
(
  ri_pk                   SERIAL PRIMARY KEY,
  ri_pr_fk                VARCHAR(12) NOT NULL REFERENCES products(pr_pk),
  ri_hotel_id             VARCHAR(3) NOT NULL,
  ri_usage_year           INTEGER NOT NULL,
  ri_inv_type             VARCHAR(3) NOT NULL,
  ri_swapped_product_id   VARCHAR(12),
  ri_granted_to           VARCHAR(3),
  ri_used_points          VARCHAR(9),           -- 'i' prefixed if individual owner points value
  ri_usage_comment        VARCHAR(33),          -- for Esther/Nancy Status Entitlement Usage spreadsheet column
  UNIQUE (ri_hotel_id, ri_pr_fk, ri_usage_year)
);
-- noinspection SqlResolve
SELECT audit.audit_table('res_inventories');

-- reservations
/* .. columns not included from V_ACU_RES_DATA/_UNSYNCED or indirectly included via contacts table
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
  rgr_pk                  INTEGER PRIMARY KEY NOT NULL,   -- SIHOT reservation GDSNO (OBJID not available in RES-SEARCH)
  rgr_order_co_fk         INTEGER NOT NULL REFERENCES contacts(co_pk),
  rgr_used_ri_fk          INTEGER REFERENCES res_inventories(ri_pk),
  rgr_rci_deposit_ri_fk   INTEGER REFERENCES res_inventories(ri_pk),
  rgr_sh_res_id           VARCHAR(18),                    -- SIHOT reservation number / sub-number
  rgr_arrival             DATE NOT NULL,
  rgr_departure           DATE NOT NULL,
  rgr_status              VARCHAR(3) NOT NULL,
  rgr_adults              INTEGER NOT NULL DEFAULT 2,
  rgr_children            INTEGER NOT NULL DEFAULT 0,
  rgr_mkt_segment         VARCHAR(3) NOT NULL,
  rgr_mkt_group           VARCHAR(3) NOT NULL,
  rgr_hotel_id            VARCHAR(3) NOT NULL,
  rgr_room_cat_id         VARCHAR(6) NOT NULL,
  rgr_sh_rate             VARCHAR(3),
  rgr_payment_inst        VARCHAR(3),
  rgr_ext_book_id         VARCHAR(21),
  rgr_ext_book_day        DATE,
  rgr_comment             VARCHAR(540),
  rgr_long_comment        VARCHAR(3999),
  rgr_time_in             TIMESTAMP,
  rgr_time_out            TIMESTAMP,
  rgr_created_by          VARCHAR(18) NOT NULL DEFAULT user,
  rgr_created_when        TIMESTAMP NOT NULL DEFAULT current_timestamp,
  rgr_last_change         TIMESTAMP NOT NULL DEFAULT current_timestamp,
  rgr_last_sync           TIMESTAMP
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

CREATE TABLE res_group_contacts
(
  rgc_rgr_fk              INTEGER NOT NULL,
  rgc_surname             VARCHAR(42) NOT NULL,
  rgc_firstname           VARCHAR(42) NOT NULL,
  rgc_email               VARCHAR(42),
  rgc_phone               VARCHAR(42),
  rgc_dob                 DATE,
  rgc_auto_generated      VARCHAR(1) NOT NULL DEFAULT '1',
  rgc_occup_co_fk         INTEGER REFERENCES contacts(co_pk),  -- referencing Sihot guest as Salesforce contact
  rgc_flight_arr_comment  VARCHAR(42),      -- arrival airport, airline and flight number
  rgc_flight_arr_time     TIME,             -- ETA
  rgc_flight_dep_comment  VARCHAR(42),
  rgc_flight_dep_time     TIME,
  rgc_room_seq            INTEGER NOT NULL DEFAULT 0,
  rgc_pers_seq            INTEGER NOT NULL DEFAULT 0,
  rgc_pers_type           VARCHAR(3) NOT NULL DEFAULT '1A',
  rgc_sh_pack             VARCHAR(3),
  rgc_room_id             VARCHAR(6)
);
-- noinspection SqlResolve
SELECT audit.audit_table('res_group_contacts');
