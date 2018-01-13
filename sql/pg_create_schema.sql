-- client contact
CREATE TABLE contacts
(
  co_pk                   SERIAL PRIMARY KEY,
  co_sf_contact_id        VARCHAR(18) NOT NULL,
  co_sh_guest_id          VARCHAR(15),
  co_sh_match_code        VARCHAR(18)
);

-- client contact external references (initially mainly used for to store multiple RCI Ids for each contact)
CREATE TABLE external_refs
(
  er_co_fk                INTEGER NOT NULL REFERENCES contacts(co_pk),
  er_type                 VARCHAR(3) NOT NULL,
  er_id                   VARCHAR(18) NOT NULL
);

-- product
CREATE TABLE product_types
(
  pt_pk                   VARCHAR(3) PRIMARY KEY NOT NULL,
  pt_name                 VARCHAR(39) NOT NULL
);

CREATE TABLE products
(
  pr_pk                   VARCHAR(12) PRIMARY KEY NOT NULL,
  pr_pt_fk                VARCHAR(3) NOT NULL REFERENCES product_types(pt_pk)
);

CREATE TABLE contact_products
(
  cp_co_fk                INTEGER NOT NULL REFERENCES contacts(co_pk),
  cp_pr_fk                VARCHAR(12) NOT NULL REFERENCES products(pr_pk),
  PRIMARY KEY (cp_co_fk, cp_pr_fk)
);

-- reservation inventory
CREATE TABLE res_inv
(
  ri_pk                   SERIAL PRIMARY KEY,
  ri_pr_fk                VARCHAR(12) NOT NULL REFERENCES products(pr_pk),
  ri_hotel_id             VARCHAR(3) NOT NULL,
  ri_usage_year           INTEGER NOT NULL,
  ri_inv_type             VARCHAR(3) NOT NULL,
  ri_usage_comment        VARCHAR(33),          -- for Esther/Nancy Status Entitlement Usage spreadsheet column
  ri_swapped_product_id   VARCHAR(12),
  ri_granted_to           VARCHAR(3),
  ri_used_points          INTEGER,
  UNIQUE (ri_hotel_id, ri_pr_fk, ri_usage_year)
);

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
    Nights	amount of nights for the duration of stay (indirectly included via rd_departure - rd_arrival)
    Extra Reservation Changes
    Points Value (indirectly included via ri_used_points)
    Apartment Features (indirectly via rd_room_cat_id)
    Pre-voucher code
    Confirmed Voucher code
    WebPreCki
*/
CREATE TABLE res_data
(
  rd_pk                   INTEGER PRIMARY KEY NOT NULL,   -- SIHOT reservation object ID
  rd_occup_co_fk          INTEGER NOT NULL REFERENCES contacts(co_pk),
  rd_order_co_fk          INTEGER NOT NULL REFERENCES contacts(co_pk),
  rd_used_ri_fk           INTEGER REFERENCES res_inv(ri_pk),
  rd_rci_deposit_ri_fk    INTEGER REFERENCES res_inv(ri_pk),
  rd_sh_gds_id            VARCHAR(42) NOT NULL,
  rd_sh_res_id            VARCHAR(18) NOT NULL,           -- SIHOT reservation number / sub-number
  rd_arrival              DATE NOT NULL,
  rd_departure            DATE NOT NULL,
  rd_status               VARCHAR(3) NOT NULL,
  rd_adults               INTEGER NOT NULL DEFAULT 2,
  rd_children             INTEGER NOT NULL DEFAULT 0,
  rd_mkt_segment          VARCHAR(3) NOT NULL,
  rd_hotel_id             VARCHAR(3) NOT NULL,
  rd_room_cat_id          VARCHAR(6) NOT NULL,
  rd_room_id              VARCHAR(6),
  rd_sh_rate              VARCHAR(3),
  rd_sh_pack              VARCHAR(3),
  rd_payment_inst         VARCHAR(3),
  rd_ext_book_id          VARCHAR(21),
  rd_ext_book_day         DATE,
  rd_flight_airport       VARCHAR(42),
  rd_flight_number        VARCHAR(12),
  rd_flight_landing_time  TIME,
  rd_flight_pickup        INTEGER,
  rd_comment              VARCHAR(540),
  rd_long_comment         VARCHAR(3999),
  rd_time_in              TIMESTAMP,
  rd_time_out             TIMESTAMP,
  rd_created_by           VARCHAR(18),
  rd_created_when         TIMESTAMP NOT NULL DEFAULT current_timestamp,
  rd_last_change          TIMESTAMP NOT NULL DEFAULT current_timestamp,
  rd_last_sync            TIMESTAMP
);
