import datetime
from shif import avail_rooms, count_res


class TestCountRes:
    def test_count_res_sep14_for_any_and_all_cats(self, console_app_env):
        assert count_res(console_app_env, hotel_ids=[999], day=datetime.date(2017, 9, 14)) == 20

    def test_count_res_sep14_for_any_and_stdo_cats(self, console_app_env):
        assert count_res(console_app_env, hotel_ids=[999], room_cat_prefix="STDO", day=datetime.date(2017, 9, 14)) == 16

    def test_count_res_sep14_for_any_and_1jnr_cats(self, console_app_env):
        assert count_res(console_app_env, hotel_ids=[999], room_cat_prefix="1JNR", day=datetime.date(2017, 9, 14)) == 4

    # too slow - needs around 6 minutes
    # def test_count_res_sep14_all_hotels_and_cats(self, console_app_env):
    #     assert count_res(console_app_env, day=datetime.date(2017, 9, 14)) == 906

    # quite slow - needs 1:30 minutes
    def test_count_res_sep14_for_bhc_and_all_cats(self, console_app_env):
        assert count_res(console_app_env, hotel_ids=[1], day=datetime.date(2017, 9, 14)) == 273


class TestAvailRoomsSep14:
    def test_avail_rooms_for_all_hotels_and_cats(self, console_app_env):
        assert avail_rooms(console_app_env, day=datetime.date(2017, 9, 14)) == 165

    def test_avail_rooms_for_bhc_and_all_cats(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1], day=datetime.date(2017, 9, 14)) == 21

    def test_avail_rooms_for_pbc_and_all_cats(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[4], day=datetime.date(2017, 9, 14)) == 53

    def test_avail_rooms_for_bhc_pbc_and_all_cats(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1, 4], day=datetime.date(2017, 9, 14)) == 74

    def test_avail_studios_for_all_hotels(self, console_app_env):
        assert avail_rooms(console_app_env, room_cat_prefix="S", day=datetime.date(2017, 9, 14)) == 17

    def test_avail_studios_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1], room_cat_prefix="S", day=datetime.date(2017, 9, 14)) == 8

    def test_avail_1bed_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1], room_cat_prefix="1", day=datetime.date(2017, 9, 14)) == 5

    def test_avail_1bed_junior_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1], room_cat_prefix="1J", day=datetime.date(2017, 9, 14)) == 4

    def test_avail_2bed_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1], room_cat_prefix="2", day=datetime.date(2017, 9, 14)) == 7

    def test_avail_3bed_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1], room_cat_prefix="3", day=datetime.date(2017, 9, 14)) == 1
        assert avail_rooms(console_app_env, hotel_ids=[1], room_cat_prefix="3BPS", day=datetime.date(2017, 9, 14)) == 1


class TestAvailRoomsSep15:
    def test_avail_rooms_for_all_hotels_and_cats(self, console_app_env):
        assert avail_rooms(console_app_env, day=datetime.date(2017, 9, 15)) == 99

    def test_avail_rooms_for_bhc_and_all_cats(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1], day=datetime.date(2017, 9, 15)) == 21

    def test_avail_rooms_for_pbc_and_all_cats(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[4], day=datetime.date(2017, 9, 15)) == 34

    def test_avail_rooms_for_bhc_pbc_and_all_cats(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1, 4], day=datetime.date(2017, 9, 15)) == 55

    def test_avail_studios_for_all_hotels(self, console_app_env):
        assert avail_rooms(console_app_env, room_cat_prefix="S", day=datetime.date(2017, 9, 15)) == 23

    def test_avail_studios_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1], room_cat_prefix="S", day=datetime.date(2017, 9, 15)) == 11

    def test_avail_1bed_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1], room_cat_prefix="1", day=datetime.date(2017, 9, 15)) == 3

    def test_avail_1bed_junior_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1], room_cat_prefix="1J", day=datetime.date(2017, 9, 15)) == 2

    def test_avail_2bed_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1], room_cat_prefix="2", day=datetime.date(2017, 9, 15)) == 6

    def test_avail_3bed_for_bhc(self, console_app_env):
        assert avail_rooms(console_app_env, hotel_ids=[1], room_cat_prefix="3", day=datetime.date(2017, 9, 15)) == 1
        assert avail_rooms(console_app_env, hotel_ids=[1], room_cat_prefix="3BPS", day=datetime.date(2017, 9, 15)) == 1
