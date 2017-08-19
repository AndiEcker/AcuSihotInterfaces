class TestSystem:
    def test_post_info_message_to_sihot(self, post_message):
        ret = post_message.post_message('test_config running TestSystem')
        assert ret == ''

    def test_config_dict_german_language(self, config_dict, db_connected):
        db_connected.select('T_LG', ['LG_SIHOT_LANG'], "LG_CODE = 'GER'")
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
                            "F_RESORT(AP_CODE) = 'BHC' and AP_SIHOT_CAT is not NULL")
        rows = db_connected.fetch_all()
        db_connected.close()
        cat_room_dict = cat_rooms.get_cat_rooms(hotel_id='1')
        err = ''
        for ap_code, ap_sihot_cat in rows:
            if ap_code not in cat_room_dict[ap_sihot_cat]:
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
                            "F_RESORT(AP_CODE) = 'PBC' and AP_SIHOT_CAT is not NULL")
        rows = db_connected.fetch_all()
        db_connected.close()
        cat_room_dict = cat_rooms.get_cat_rooms(hotel_id='4')
        err = ''
        for ap_code, ap_sihot_cat in rows:
            if len(ap_code) == 3:
                ap_code = '0' + ap_code
            if ap_code not in cat_room_dict[ap_sihot_cat]:
                sh_cat = ''
                for k, v in cat_room_dict.items():
                    if ap_code in v:
                        sh_cat += '/' + k
                err += "\n{} is room category {} in Acumen but {} in Sihot".format(ap_code, ap_sihot_cat, sh_cat[1:])
        assert not err

        for cat, rooms in cat_room_dict.items():
            for r in rooms:
                if r[0] != 'V' or cat != 'VR':  # exclude Sihot virtual rooms (which doesn't exist in Acumen)
                    if r[0] == '0':
                        r = r[1:]
                    found = [r for a, c in rows if r == a and c == cat]
                    if not found:
                        err += "\nroom {} / {} not configured/found in Acumen".format(r, cat)
        assert not err


class TestTourOps:
    def test_get_thomas_cook_ag_objid_by_matchcode(self, guest_info, db_connected):
        db_connected.select('T_RO', ['RO_SIHOT_AGENCY_OBJID', 'RO_SIHOT_AGENCY_MC'], "RO_CODE = 'tk'")
        rows = db_connected.fetch_all()
        db_connected.close()
        obj_id = str(rows[0][0])
        mc = rows[0][1]                                     # == 'TCAG'
        assert mc == 'TCAG'
        ret = guest_info.get_objid_by_matchcode(mc)         # tk rental (AG)
        assert ret == obj_id                                # == '20'

    def test_get_thomas_cook_rental_objid_by_matchcode(self, guest_info, db_connected):
        db_connected.select('T_RO', ['RO_SIHOT_AGENCY_OBJID', 'RO_SIHOT_AGENCY_MC'], "RO_CODE = 'TK'")
        rows = db_connected.fetch_all()
        db_connected.close()
        obj_id = str(rows[0][0])
        mc = rows[0][1]                                     # == 'TCRENT'
        assert mc == 'TCRENT'
        ret = guest_info.get_objid_by_matchcode(mc)         # TK rentals
        assert ret == obj_id                                # == '27'

    def test_config_data_get_agency(self, guest_info, config_data):
        mc = config_data.get_ro_agency_matchcode('TK')
        obj_id = guest_info.get_objid_by_matchcode(mc)
        objid = str(config_data.get_ro_agency_objid('TK'))
        assert obj_id == objid


class TestRoomCat:
    def test_room_cat_bhc_studio(self, config_data):
        assert config_data.get_room_cat('E102') == 'STDP'
        assert config_data.get_room_cat('A103') == 'STDO'
        assert config_data.get_room_cat('F206') == 'STDS'

    def test_room_cat_bhc_1bed(self, config_data):
        assert config_data.get_room_cat('A102') == '1JNR'
        assert config_data.get_room_cat('A119') == '1JNR'   # '1JNS'
        assert config_data.get_room_cat('E404') == '1DSS'

    def test_room_cat_bhc_2bed(self, config_data):
        assert config_data.get_room_cat('H101') == '2BSU'
        assert config_data.get_room_cat('H202') == '2BSH'
        assert config_data.get_room_cat('H112') == '2BSP'

    def test_room_cat_pbc_studio(self, config_data):
        assert config_data.get_room_cat('211') == 'STDP'
        assert config_data.get_room_cat('511') == 'STDS'
        assert config_data.get_room_cat('911') == 'STDH'

    def test_room_cat_pbc_1bed(self, config_data):
        assert config_data.get_room_cat('126') == '1JNP'
        assert config_data.get_room_cat('535') == '1STS'
        assert config_data.get_room_cat('922') == '1JNH'

    def test_room_cat_pbc_2bed(self, config_data):
        assert config_data.get_room_cat('334') == '2BSP'
        assert config_data.get_room_cat('401') == '2STS'    # '22SB'
        assert config_data.get_room_cat('925') == '2BSH'
        assert config_data.get_room_cat('924') == '2STS'

    def test_room_size_bhc_studio(self, config_data):
        assert config_data.get_size_cat('BHC', 'STUDIO') == 'STDO'
        assert config_data.get_size_cat('BHC', 'STUDIO', [752, 781, 748]) == 'STDO'
        assert config_data.get_size_cat('BHC', 'STUDIO', [757, 781, 748]) == 'STDS'
        assert config_data.get_size_cat('BHC', 'STUDIO', [757, 781, 748], allow_any=False) == 'STDS'
        assert config_data.get_size_cat('BHC', 'STUDIO', [752, 781, 748], allow_any=False) is None

    def test_room_size_bhc_1bed(self, config_data):
        assert config_data.get_size_cat('BHC', '1 BED') == '1JNR'
        assert config_data.get_size_cat('BHC', '1 BED', [752, 781, 748]) == '1DSS'
        assert config_data.get_size_cat('BHC', '1 BED', [757, 781, 748]) == '1JNS'

    def test_room_size_bhc_2bed(self, config_data):
        assert config_data.get_size_cat('BHC', '2 BED') == '2BSU'
        assert config_data.get_size_cat('BHC', '2 BED', [752, 781, 748]) == '2DPU'
        assert config_data.get_size_cat('BHC', '2 BED', [757, 781, 748]) == '2BSH'

    def test_room_size_pbc_studio(self, config_data):
        assert config_data.get_size_cat('PBC', 'STUDIO') == 'STDP'
        assert config_data.get_size_cat('PBC', 'STUDIO', [752, 781, 748]) == 'STDB'
        assert config_data.get_size_cat('PBC', 'STUDIO', [757, 748]) == 'STDH'
        assert config_data.get_size_cat('PBC', 'STUDIO', [757, 781, 748], allow_any=False) == 'STDB'
        assert config_data.get_size_cat('PBC', 'STUDIO', [752, 757, 748]) == 'STDH'
        assert config_data.get_size_cat('PBC', 'STUDIO', [752, 757, 781, 748], allow_any=False) == 'STDB'

    def test_room_size_pbc_1bed(self, config_data):
        assert config_data.get_size_cat('PBC', '1 BED') == '1JNP'
        assert config_data.get_size_cat('PBC', '1 BED', [752, 781, 748]) == '1STS'  # Sterling
        assert config_data.get_size_cat('PBC', '1 BED', [757, 781]) == '1JNH'

    def test_room_size_pbc_2bed(self, config_data):
        assert config_data.get_size_cat('PBC', '2 BED') == '2BSP'
        assert config_data.get_size_cat('PBC', '2 BED', [752, 781, 748]) == '2BSP'
        assert config_data.get_size_cat('PBC', '2 BED', [757, 781, 748]) == '2BSH'

    # following two tests added from TC contract setup - see Fabian's email from 21-11-2016 14:56
    def test_room_size_fabian_setup_bhc(self, config_data):
        assert config_data.get_size_cat('BHC', 'STUDIO') == 'STDO'
        assert config_data.get_size_cat('BHC', 'STUDIO', [757]) == 'STDS'

        assert config_data.get_size_cat('BHC', '1 BED') == '1JNR'
        assert config_data.get_size_cat('BHC', '1 BED', [752]) == '1DSS'
        assert config_data.get_size_cat('BHC', '1 BED', [757]) == '1JNS'

        assert config_data.get_size_cat('BHC', '2 BED') == '2BSU'
        assert config_data.get_size_cat('BHC', '2 BED', [752]) == '2DPU'

    def test_room_size_fabian_setup_pbc(self, config_data):
        assert config_data.get_size_cat('PBC', 'STUDIO') == 'STDP'
        assert config_data.get_size_cat('PBC', 'STUDIO', [757]) == 'STDH'
        assert config_data.get_size_cat('PBC', 'STUDIO', [781]) == 'STDB'  # Seafront

        assert config_data.get_size_cat('PBC', '1 BED') == '1JNP'
        assert config_data.get_size_cat('PBC', '1 BED', [757]) == '1JNH'
        assert config_data.get_size_cat('PBC', '1 BED', [748]) == '1STS'

        assert config_data.get_size_cat('PBC', '2 BED') == '2BSP'
        assert config_data.get_size_cat('PBC', '2 BED', [757]) == '2BSH'
