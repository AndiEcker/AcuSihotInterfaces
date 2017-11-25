# SIHOT high level interface (based on the low level interfaces provided by sxmlif)
import datetime

from sxmlif import AvailCatInfo, ResSearch
from acu_sf_sh_sys_data import AssSysData
from ae_console_app import uprint, DATE_ISO, DEBUG_LEVEL_VERBOSE


def avail_rooms(cae, hotel_ids=None, room_cat_prefix='', day=datetime.date.today()):
    """ accumulating the number of available rooms in all the hotels specified by the hotel_ids list with the room
    category matching the first characters of the specified room_cat_prefix string and for a certain day.

    :param cae:             Console App Environment singleton class instance.
    :param hotel_ids:       Optional list of hotel IDs (leave empty for to get the rooms in all hotels accumulated).
    :param room_cat_prefix: Optional room category prefix string (leave empty for all room categories or pass e.g.
                            'S' for a accumulation of all the Studios or '1J' for all 1 bedroom junior rooms).
    :param day:             Optional day (leave empty for to get the available rooms for today's date).
    :return:                Number of available rooms (negative on overbooking).
    """
    if not hotel_ids:
        # hotel_ids = [1, 2, 3, 4, 999]
        hotel_ids = AssSysData(cae).get_hotel_ids()     # determine list of IDs of all active/valid Sihot-hotels
    day_str = datetime.date.strftime(day, DATE_ISO)
    cat_info = AvailCatInfo(cae)
    rooms = 0
    for hotel_id in hotel_ids:
        if hotel_id == 999:     # unfortunately currently there is no avail data for this pseudo hotel
            rooms -= count_res(cae, hotel_ids=[999], room_cat_prefix=room_cat_prefix, day=day)
        else:
            ret = cat_info.avail_rooms(hotel_id=str(hotel_id), from_date=day, to_date=day)
            for cat_id, cat_data in ret.items():
                if cat_id.startswith(room_cat_prefix):  # True for all room cats if room_cat_prefix is empty string
                    rooms += ret[cat_id][day_str]['AVAIL']
    return rooms


def count_res(cae, hotel_ids=None, room_cat_prefix='', day=datetime.date.today(), res_max_days=27):
    """ counting uncancelled reservations in all the hotels specified by the hotel_ids list with the room
    category matching the first characters of the specified room_cat_prefix string and for a certain day.
    
    :param cae:             Console App Environment singleton class instance.
    :param hotel_ids:       Optional list of hotel IDs (leave empty for to get the rooms in all hotels accumulated).
    :param room_cat_prefix: Optional room category prefix string (leave empty for all room categories or pass e.g.
                            'S' for a accumulation of all the Studios or '1J' for all 1 bedroom junior rooms).
    :param day:             Optional day (leave empty for to get the available rooms for today's date).
    :param res_max_days:    Optional maximum length of reservation (def=27).
    :return:
    """
    if not hotel_ids:
        hotel_ids = AssSysData(cae).get_hotel_ids()     # determine list of IDs of all active/valid Sihot-hotels
    res_len_max_timedelta = datetime.timedelta(days=res_max_days)
    debug_level = cae.get_option('debugLevel')
    count = 0
    res_search = ResSearch(cae)
    for hotel_id in hotel_ids:
        all_rows = res_search.search(hotel_id=str(hotel_id), from_date=day - res_len_max_timedelta, to_date=day)
        if all_rows and isinstance(all_rows, list):
            for row_dict in all_rows:
                res_type = row_dict['RT']['elemVal']
                room_cat = row_dict['CAT']['elemVal']
                checked_in = datetime.datetime.strptime(row_dict['ARR']['elemVal'], DATE_ISO).date()
                checked_out = datetime.datetime.strptime(row_dict['DEP']['elemVal'], DATE_ISO).date()
                skip_reasons = []
                if res_type == 'S':
                    skip_reasons.append("cancelled")
                if res_type == 'E':
                    skip_reasons.append("erroneous")
                if not room_cat.startswith(room_cat_prefix):
                    skip_reasons.append("room cat " + room_cat)
                if not (checked_in <= day < checked_out):
                    skip_reasons.append("out of date range " + str(checked_in) + "..." + str(checked_out))
                if not skip_reasons:
                    count += 1
                elif debug_level >= DEBUG_LEVEL_VERBOSE:
                    uprint("shif.count_res(): skipped {} reservation: {}".format(str(skip_reasons), row_dict))
    return count
