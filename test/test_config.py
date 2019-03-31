class TestTourOps:
    def test_missing_agencies_in_sihot(self, db_connected, client_search):
        db_connected.select('T_RO', ['RO_SIHOT_AGENCY_OBJID', 'RO_SIHOT_AGENCY_MC'],
                            where_group_order="RO_SIHOT_AGENCY_OBJID is not NULL or RO_SIHOT_AGENCY_MC is not NULL")
        rows = db_connected.fetch_all()
        db_connected.close()
        ags = client_search.search_clients(guest_type='7', field_names=('AcuId', 'ShId'))

        failures = list()
        for row in rows:
            assert row[0] > 0, "Acumen Agency object id is not specified for matchcode {}".format(row[1])
            assert row[1], "Acumen Agency match code is not specified for obj-id {}".format(row[0])
            for sha in ags:
                if sha['ShId'] == str(row[0]) and sha['AcuId'] == row[1]:
                    break
            else:
                failures.append("Acumen Object-ID {} or Matchcode {} not found in Sihot agencies"
                                .format(row[0], row[1]))
        if failures:
            print("Acumen agencies", rows)
            print("Sihot agencies", ags)
            for f in failures:
                print(f)
        assert not failures

    def test_missing_agencies_in_acumen(self, client_search, db_connected):
        ags = client_search.search_clients(guest_type='7', field_names=('AcuId', 'ShId'))
        db_connected.select('T_RO', ['RO_SIHOT_AGENCY_OBJID', 'RO_SIHOT_AGENCY_MC'],
                            where_group_order="RO_SIHOT_AGENCY_OBJID is not NULL or RO_SIHOT_AGENCY_MC is not NULL")
        rows = db_connected.fetch_all()
        db_connected.close()

        failures = list()
        for sha in ags:
            if not sha['AcuId']:
                continue            # skip guests wrongly configured (missing Matchcode)
            assert sha['ShId'], "Sihot Agency object id is not specified for matchcode {}".format(sha['MATCHCODE'])
            for row in rows:
                if sha['ShId'] == str(row[0]) and sha['AcuId'] == row[1]:
                    break
            else:
                failures.append("Sihot Object-ID {} or Matchcode {} not found in Acumen agencies"
                                .format(sha['ShId'], sha['AcuId']))
        if failures:
            print("Sihot agencies", ags)
            print("Acumen agencies", rows)
            for f in failures:
                print(f)
        assert not failures

    def test_get_thomas_cook_ag_objid_by_matchcode(self, client_search, db_connected):
        db_connected.select('T_RO', ['RO_SIHOT_AGENCY_OBJID', 'RO_SIHOT_AGENCY_MC'], where_group_order="RO_CODE = 'tk'")
        rows = db_connected.fetch_all()
        db_connected.close()
        obj_id = str(rows[0][0])
        mc = rows[0][1]                                     # == 'TCAG'
        assert mc == 'TCAG'
        ret = client_search.client_id_by_matchcode(mc)      # tk rental (AG)
        assert ret == obj_id                                # == '20'

    def test_get_thomas_cook_rental_objid_by_matchcode(self, client_search, db_connected):
        db_connected.select('T_RO', ['RO_SIHOT_AGENCY_OBJID', 'RO_SIHOT_AGENCY_MC'], where_group_order="RO_CODE = 'TK'")
        rows = db_connected.fetch_all()
        db_connected.close()
        obj_id = str(rows[0][0])
        mc = rows[0][1]                                     # == 'TCRENT'
        assert mc == 'TCRENT'
        ret = client_search.client_id_by_matchcode(mc)      # TK rentals
        assert ret == obj_id                                # == '27'

    def test_config_data_get_thomas_cook_agency(self, client_search, ass_sys_data):
        mc = ass_sys_data.ro_agency_matchcode('TK')
        obj_id = client_search.client_id_by_matchcode(mc)
        objid = str(ass_sys_data.ro_agency_objid('TK'))
        assert obj_id == objid

    def test_get_thomas_cook_by_surname(self, client_search):
        obj_ids = client_search.search_clients(surname='Thomas Cook Northern Europe')
        obj_id = client_search.client_id_by_matchcode('TCRENT')      # TK rentals
        assert obj_ids[0] == obj_id

    def test_get_objids_by_email(self, client_search):
        obj_ids = client_search.search_clients(email='info@opentravelservice.com')
        obj_id = client_search.client_id_by_matchcode('OTS')         # Open Travel Service AG
        assert obj_id in obj_ids
        obj_id = client_search.client_id_by_matchcode('SF')          # strange: Sumar Ferdir has same email
        assert obj_id in obj_ids


class TestSystem:
    def test_post_info_message_to_sihot(self, post_message):
        ret = post_message.post_message('test_config running TestSystem')
        assert ret == ''

    def test_config_dict_german_language(self, config_dict, db_connected):
        db_connected.select('T_LG', ['LG_SIHOT_LANG'], where_group_order="LG_CODE = 'GER'")
        rows = db_connected.fetch_all()
        db_connected.close()
        lang_id = str(rows[0][0])   # == 'DE'
        # config types documented on page 163 in WEB interface V9: '10' is for Language comboboxes
        kvs = config_dict.get_key_values(config_type='10', hotel_id='1')
        assert lang_id in kvs

    def test_config_missing_acu_mkt_seg(self, config_dict, db_connected):
        mss = config_dict.get_key_values(config_type='MA', hotel_id='1')
        db_connected.select('T_RO', ['nvl(RO_SIHOT_MKT_SEG, RO_CODE)'])
        ros = db_connected.fetch_all()
        db_connected.close()
        not_found_ros = list()
        for ms in mss:
            for ro in ros:
                if ms == ro[0]:
                    break
            else:
                not_found_ros.append(ms)
        assert not not_found_ros

    def test_config_mkt_seg_hotel_diffs(self, config_dict):
        mss1 = config_dict.get_key_values(config_type='MA', hotel_id='1')
        mss4 = config_dict.get_key_values(config_type='MA', hotel_id='4')
        ms_diff = list()
        for ms1 in mss1:
            for ms4 in mss4:
                if ms1 == ms4:
                    break
            else:
                ms_diff.append(ms1)
        for ms4 in mss4:
            for ms1 in mss1:
                if ms4 == ms1:
                    break
            else:
                ms_diff.append(ms4)
        assert not ms_diff

    def test_cat_rooms_bhc(self, cat_rooms, db_connected):      # see also TestRoomCat class further down
        db_connected.select('T_AP', ['AP_CODE', 'AP_SIHOT_CAT'],
                            where_group_order="F_RESORT(AP_CODE) = 'BHC' and AP_SIHOT_CAT is not NULL")
        rows = db_connected.fetch_all()
        db_connected.close()
        cat_room_dict = cat_rooms.get_cat_rooms(hotel_id='1')
        assert isinstance(cat_room_dict, dict)
        err = ''
        for ap_code, ap_sihot_cat in rows:
            if ap_sihot_cat not in cat_room_dict:
                err += "\nroom category {} from Acumen is not defined in Sihot".format(ap_sihot_cat)
            elif ap_code not in cat_room_dict[ap_sihot_cat]:
                sh_cat = ''
                for k, v in cat_room_dict.items():
                    if ap_code in v:
                        sh_cat += '/' + k
                err += "\n{} is room category {} in Acumen but {} in Sihot".format(ap_code, ap_sihot_cat, sh_cat[1:])
        assert not err

        for cat, rooms in cat_room_dict.items():
            for r in rooms:
                if r[0] != 'V' or cat != 'VR':  # exclude Sihot virtual rooms (which doesn't exist in Acumen)
                    found = [r for a, c in rows if r == a and c == cat]
                    if not found:
                        err += "\nroom {} with category {} not configured/found in Acumen".format(r, cat)
        assert not err

    def test_cat_rooms_pbc(self, cat_rooms, db_connected):
        db_connected.select('T_AP', ['AP_CODE', 'AP_SIHOT_CAT'],
                            where_group_order="F_RESORT(AP_CODE) = 'PBC' and AP_SIHOT_CAT is not NULL")
        rows = db_connected.fetch_all()
        db_connected.close()
        cat_room_dict = cat_rooms.get_cat_rooms(hotel_id='4')
        assert isinstance(cat_room_dict, dict)
        err = ''
        for ap_code, ap_sihot_cat in rows:
            if len(ap_code) == 3:
                ap_code = '0' + ap_code
            if ap_sihot_cat not in cat_room_dict:
                err += "\nroom category {} from Acumen is not defined in Sihot".format(ap_sihot_cat)
            elif ap_code not in cat_room_dict[ap_sihot_cat] and ap_code != '0233':  # TODO: 0233 is not in SH-response
                sh_cat = ''
                for k, v in cat_room_dict.items():
                    if ap_code in v:
                        sh_cat += '/' + k
                err += "\n{} is room category {} in Acumen but {} in Sihot".format(ap_code, ap_sihot_cat, sh_cat[1:])
        print(err)
        assert not err

        for cat, rooms in cat_room_dict.items():
            for r in rooms:
                if r[0] != 'V' or cat != 'VR':  # exclude Sihot virtual rooms (which doesn't exist in Acumen)
                    if r[0] == '0':
                        r = r[1:]
                    found = [r for a, c in rows if r == a and c == cat]
                    if not found:
                        err += "\nroom {} / {} not configured/found in Acumen".format(r, cat)
        print(err)
        assert not err

    def test_cat_rooms_bhh(self, cat_rooms, db_connected):
        db_connected.select('T_AP', ['AP_CODE', 'AP_SIHOT_CAT'],
                            where_group_order="F_RESORT(AP_CODE) = 'BHH' and AP_SIHOT_CAT is not NULL")
        rows = db_connected.fetch_all()
        db_connected.close()
        cat_room_dict = cat_rooms.get_cat_rooms(hotel_id='2')
        assert isinstance(cat_room_dict, dict)
        err = ''
        for ap_code, ap_sihot_cat in rows:
            if ap_sihot_cat not in cat_room_dict:
                err += "\nroom category {} from Acumen is not defined in Sihot".format(ap_sihot_cat)
            elif ap_code not in cat_room_dict[ap_sihot_cat]:
                sh_cat = ''
                for k, v in cat_room_dict.items():
                    if ap_code in v:
                        sh_cat += '/' + k
                err += "\n{} is room category {} in Acumen but {} in Sihot".format(ap_code, ap_sihot_cat, sh_cat[1:])
        assert not err

        for cat, rooms in cat_room_dict.items():
            for r in rooms:
                if r[0] != 'V' or cat != 'VR':  # exclude Sihot virtual rooms (which doesn't exist in Acumen)
                    found = [r for a, c in rows if r == a and c == cat]
                    if not found:
                        err += "\nroom {} with category {} not configured/found in Acumen".format(r, cat)
        assert not err

    def test_cat_rooms_hmc(self, cat_rooms, db_connected):
        db_connected.select('T_AP', ['AP_CODE', 'AP_SIHOT_CAT'],
                            where_group_order="F_RESORT(AP_CODE) = 'HMC' and AP_SIHOT_CAT is not NULL")
        rows = db_connected.fetch_all()
        db_connected.close()
        cat_room_dict = cat_rooms.get_cat_rooms(hotel_id='3')
        assert isinstance(cat_room_dict, dict)
        err = sql = ''
        for ap_code, ap_sihot_cat in rows:
            if ap_sihot_cat not in cat_room_dict:
                err += "\nroom category {} from Acumen is not defined in Sihot".format(ap_sihot_cat)
            elif ap_code not in cat_room_dict[ap_sihot_cat]:
                sh_cat = ''
                for k, v in cat_room_dict.items():
                    if ap_code in v:
                        sh_cat += '/' + k
                err += "\n{} is room category {} in Acumen but {} in Sihot".format(ap_code, ap_sihot_cat, sh_cat[1:])
                sql += "\nupdate T_AP set AP_SIHOT_CAT = '{}' where AP_CODE = '{}';".format(sh_cat[1:], ap_code)
        print(sql)
        assert not err

        for cat, rooms in cat_room_dict.items():
            for r in rooms:
                if r[0] != 'V' or cat != 'VR':  # exclude Sihot virtual rooms (which doesn't exist in Acumen)
                    found = [r for a, c in rows if r == a and c == cat]
                    if not found:
                        err += "\nroom {} with category {} not configured/found in Acumen".format(r, cat)
        assert not err


class TestRoomCat:
    def test_room_cat_bhc_studio(self, ass_sys_data):
        assert ass_sys_data.cat_by_room('E102') == 'STDP'
        assert ass_sys_data.cat_by_room('A103') == 'STDO'
        assert ass_sys_data.cat_by_room('F206') == 'STDS'

    def test_room_cat_bhc_1bed(self, ass_sys_data):
        assert ass_sys_data.cat_by_room('A102') == '1JNR'
        assert ass_sys_data.cat_by_room('A119') == '1JNR'   # '1JNS'
        assert ass_sys_data.cat_by_room('E404') == '1DSS'

    def test_room_cat_bhc_2bed(self, ass_sys_data):
        assert ass_sys_data.cat_by_room('H101') == '2BSU'
        assert ass_sys_data.cat_by_room('H202') == '2BSH'
        assert ass_sys_data.cat_by_room('H112') == '2BSP'

    def test_room_cat_pbc_studio(self, ass_sys_data):
        assert ass_sys_data.cat_by_room('211') == 'STDP'
        assert ass_sys_data.cat_by_room('511') == 'STDS'
        assert ass_sys_data.cat_by_room('911') == 'STDH'

    def test_room_cat_pbc_1bed(self, ass_sys_data):
        assert ass_sys_data.cat_by_room('126') == '1JNP'
        assert ass_sys_data.cat_by_room('535') == '1STS'
        assert ass_sys_data.cat_by_room('922') == '1JNH'

    def test_room_cat_pbc_2bed(self, ass_sys_data):
        assert ass_sys_data.cat_by_room('334') == '2BSP'
        assert ass_sys_data.cat_by_room('401') == '2WSB'    # '22SB' then 2STS and now 2WSB (June 2018)
        assert ass_sys_data.cat_by_room('925') == '2BSH'
        assert ass_sys_data.cat_by_room('924') == '2WSS'

    def test_room_size_bhc_studio(self, ass_sys_data):
        assert ass_sys_data.cat_by_size('1', 'STUDIO') == 'STDO'
        assert ass_sys_data.cat_by_size('1', 'STUDIO', [752, 781, 748]) == 'STDO'
        assert ass_sys_data.cat_by_size('1', 'STUDIO', [757, 781, 748]) == 'STDS'
        assert ass_sys_data.cat_by_size('1', 'STUDIO', [757, 781, 748], allow_any=False) == 'STDS'
        assert ass_sys_data.cat_by_size('1', 'STUDIO', [752, 781, 748], allow_any=False) is None

    def test_room_size_bhc_1bed(self, ass_sys_data):
        assert ass_sys_data.cat_by_size('1', '1 BED') == '1JNR'
        assert ass_sys_data.cat_by_size('1', '1 BED', [752, 781, 748]) == '1DSS'
        assert ass_sys_data.cat_by_size('1', '1 BED', [757, 781, 748]) == '1JNS'

    def test_room_size_bhc_2bed(self, ass_sys_data):
        assert ass_sys_data.cat_by_size('1', '2 BED') == '2BSU'
        assert ass_sys_data.cat_by_size('1', '2 BED', [752, 781, 748]) == '2DPU'
        assert ass_sys_data.cat_by_size('1', '2 BED', [757, 781, 748]) == '2BSH'

    def test_room_size_pbc_studio(self, ass_sys_data):
        assert ass_sys_data.cat_by_size('4', 'STUDIO') == 'STDP'
        assert ass_sys_data.cat_by_size('4', 'STUDIO', [752, 781, 748]) == 'STDB'
        assert ass_sys_data.cat_by_size('4', 'STUDIO', [757, 748]) == 'STDH'
        assert ass_sys_data.cat_by_size('4', 'STUDIO', [757, 781, 748], allow_any=False) == 'STDB'
        assert ass_sys_data.cat_by_size('4', 'STUDIO', [752, 757, 748]) == 'STDH'
        assert ass_sys_data.cat_by_size('4', 'STUDIO', [752, 757, 781, 748], allow_any=False) == 'STDB'

    def test_room_size_pbc_1bed(self, ass_sys_data):
        assert ass_sys_data.cat_by_size('4', '1 BED') == '1JNP'
        assert ass_sys_data.cat_by_size('4', '1 BED', [752, 781, 748]) == '1JNB'  # Sterling
        assert ass_sys_data.cat_by_size('4', '1 BED', [757, 781]) == '1JNB'

    def test_room_size_pbc_2bed(self, ass_sys_data):
        assert ass_sys_data.cat_by_size('4', '2 BED') == '2BSP'
        assert ass_sys_data.cat_by_size('4', '2 BED', [752, 781, 748]) == '22SB'
        assert ass_sys_data.cat_by_size('4', '2 BED', [757, 781, 748]) == '22SB'

    # following two tests added from TC contract setup - see Fabian's email from 21-11-2016 14:56
    def test_room_size_fabian_setup_bhc(self, ass_sys_data):
        assert ass_sys_data.cat_by_size('1', 'STUDIO') == 'STDO'
        assert ass_sys_data.cat_by_size('1', 'STUDIO', [757]) == 'STDS'

        assert ass_sys_data.cat_by_size('1', '1 BED') == '1JNR'
        assert ass_sys_data.cat_by_size('1', '1 BED', [752]) == '1DSS'
        assert ass_sys_data.cat_by_size('1', '1 BED', [757]) == '1JNS'

        assert ass_sys_data.cat_by_size('1', '2 BED') == '2BSU'
        assert ass_sys_data.cat_by_size('1', '2 BED', [752]) == '2DPU'

    def test_room_size_fabian_setup_pbc(self, ass_sys_data):
        assert ass_sys_data.cat_by_size('4', 'STUDIO') == 'STDP'
        assert ass_sys_data.cat_by_size('4', 'STUDIO', [757]) == 'STDH'
        assert ass_sys_data.cat_by_size('4', 'STUDIO', [781]) == 'STDB'  # Seafront

        assert ass_sys_data.cat_by_size('4', '1 BED') == '1JNP'
        assert ass_sys_data.cat_by_size('4', '1 BED', [757]) == '1JNH'
        assert ass_sys_data.cat_by_size('4', '1 BED', [748]) == '1STS'

        assert ass_sys_data.cat_by_size('4', '2 BED') == '2BSP'
        assert ass_sys_data.cat_by_size('4', '2 BED', [757]) == '2BSH'
