from db import OraDB


class Data:
    def __init__(self, acu_user, acu_password, acu_dsn):
        db = OraDB(usr=acu_user, pwd=acu_password, dsn=acu_dsn)
        db.connect()

        any_cats = self.load_view(db, 'T_LU', ['LU_ID', 'LU_CHAR'], "LU_CLASS = 'SIHOT_CATS_ANY'")
        bhc_cats = self.load_view(db, 'T_LU', ['LU_ID', 'LU_CHAR'], "LU_CLASS = 'SIHOT_CATS_BHC'")
        pbc_cats = self.load_view(db, 'T_LU', ['LU_ID', 'LU_CHAR'], "LU_CLASS = 'SIHOT_CATS_PBC'")
        self.resort_cats = {'ANY': any_cats, 'BHC': bhc_cats, 'PBC': pbc_cats}

        self.ap_cats = self.load_view(db, 'T_AP', ['AP_CODE', 'AP_SIHOT_CAT'], "F_RESORT(AP_CODE) in ('BHC', 'PBC')")

        self.ro_agencies = self.load_view(db, 'T_RO', ['RO_CODE', 'RO_SIHOT_AGENCY_OBJID', 'RO_SIHOT_AGENCY_MC'],
                                          "RO_SIHOT_AGENCY_OBJID is not NULL")

        db.close()

    @staticmethod
    def load_view(db, view, cols, where):
        err_msg = db.select(view, cols, where)
        if err_msg:
            print(err_msg)
        return db.fetch_all()

    def get_ro_agency_objid(self, ro_code):
        return next((cols[1] for cols in self.ro_agencies if cols[0] == ro_code), None)

    def get_ro_agency_matchcode(self, ro_code):
        return next((cols[2] for cols in self.ro_agencies if cols[0] == ro_code), None)

    def get_size_cat(self, rs_code, ap_size, ap_feats=None, allow_any=True):
        found = None
        if ap_feats:  # optional list of apartment feature ids (AFT_CODEs)
            var = 2 ** len(ap_feats)  # all possible ordered variations of apt features
            ap_feats = [str(ft) for ft in sorted(ap_feats)]
        for resort in [rs_code] + (['ANY'] if rs_code != 'ANY' and allow_any else []):
            view = self.resort_cats[resort]
            if not view:
                continue
            key = ap_size
            if ap_feats:
                key += '_' + '_'.join(ap_feats)
            found = next((cols[1] for cols in view if cols[0] == key), None)

            if not found and ap_feats:
                for deg in range(var - 1):
                    key = ap_size \
                          + ('' if var - deg - 2 == 0 else '_') \
                          + '_'.join([ft for no, ft in enumerate(ap_feats) if 2 ** no & var - deg - 2])
                    found = next((cols[1] for cols in view if cols[0] == key), None)
                    if found:
                        break

            if found:
                break

        return found

    def get_room_cat(self, room_no):
        return next((cols[1] for cols in self.ap_cats if cols[0] == room_no), None)

