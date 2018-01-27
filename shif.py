# SIHOT high level interface (based on the low level interfaces provided by sxmlif)
import datetime
import time
from traceback import print_exc

from sxmlif import AvailCatInfo, ResSearch, SXML_DEF_ENCODING, ELEM_PATH_SEP, elem_path_values
from acu_sf_sh_sys_data import AssSysData
from ae_console_app import uprint, DATE_ISO, DEBUG_LEVEL_VERBOSE

SIHOT_PROVIDES_CHECKOUT_TIME = False  # currently there is no real checkout time available in Sihot
SIHOT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S' if SIHOT_PROVIDES_CHECKOUT_TIME else '%Y-%m-%d'

ELEM_MISSING = "(missing)"
ELEM_EMPTY = "(empty)"


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
    :param res_max_days:    Optional maximum length of reservation (def=27 days).
    :return:                Number of valid reservations of the specified hotel(s) and room category prefix and
                            with arrivals within the date range day-res_max_days...day.
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


def elem_path_join(elem_names):
    return ELEM_PATH_SEP.join(elem_names)


def elem_value(shd, elem_name_or_path, arri=-1, verbose=False, default_value=None):
    """ get the xml element value from the row_dict variable, using arr_index in case of multiple values """
    is_path = ELEM_PATH_SEP in elem_name_or_path
    elem_nam = elem_name_or_path.rsplit(ELEM_PATH_SEP, 1)[1] if is_path else elem_name_or_path

    elem_val = None
    if elem_nam not in shd:
        elem_val = ELEM_MISSING if verbose else default_value
    elif is_path:
        val_arr = elem_path_values(shd, elem_name_or_path)
        if 0 <= arri < len(val_arr):
            elem_val = val_arr[arri]
    else:
        elem_def = shd[elem_nam]
        if 'elemListVal' in elem_def and len(elem_def['elemListVal']) > arri:
            elem_val = [_ for _ in elem_def['elemListVal'] if _] if arri == -1 else ""
            if not elem_val:
                elem_val = elem_def['elemListVal'][arri]
        else:
            elem_val = ""
        if not elem_val and 'elemVal' in elem_def and elem_def['elemVal']:
            elem_val = elem_def['elemVal']

    if not elem_val:
        elem_val = ELEM_EMPTY if verbose else default_value

    return elem_val


def get_hotel_and_res_id(shd):
    h_id = elem_value(shd, 'RES-HOTEL')
    r_num = elem_value(shd, 'RES-NR')
    s_num = elem_value(shd, 'SUB-NR')
    if not h_id or not r_num:
        return None, None
    return h_id, r_num + ("/" + s_num if s_num else "") + "@" + h_id


def get_pax_count(shd):
    return int(elem_value(shd, 'NOPAX')) + int(elem_value(shd, 'NOCHILDS'))


def get_gds_no(shd):
    return elem_value(shd, 'GDSNO')


def get_apt_wk_yr(shd, cae, arri=-1):
    arr = datetime.datetime.strptime(elem_value(shd, 'ARR'), SIHOT_DATE_FORMAT)
    year, wk = AssSysData(cae).rc_arr_to_year_week(arr)
    apt = elem_value(shd, 'RN', arri=arri)
    return apt, wk, year


def get_date_range(shd):
    """ determines the check-in/-out values (of type: datetime if SIHOT_PROVIDES_CHECKOUT_TIME else date) """
    if SIHOT_PROVIDES_CHECKOUT_TIME:
        d_str = shd['ARR']['elemVal']
        t_str = shd['ARR-TIME']['elemVal']
        checked_in = datetime.datetime.strptime(d_str + ' ' + t_str, SIHOT_DATE_FORMAT)
        dt_key = 'DEP-TIME'
        if dt_key in shd and 'elemVal' in shd[dt_key] and shd[dt_key]['elemVal']:
            d_str = shd['DEP']['elemVal']
            t_str = shd[dt_key]['elemVal']
            checked_out = datetime.datetime.strptime(d_str + ' ' + t_str, SIHOT_DATE_FORMAT)
        else:
            checked_out = None
    else:
        checked_in = datetime.datetime.strptime(shd['ARR']['elemVal'], SIHOT_DATE_FORMAT).date()
        checked_out = datetime.datetime.strptime(shd['DEP']['elemVal'], SIHOT_DATE_FORMAT).date()
    return checked_in, checked_out


def date_range_chunks(date_from, date_till, fetch_max_days):
    one_day = datetime.timedelta(days=1)
    add_days = datetime.timedelta(days=fetch_max_days) - one_day
    chunk_till = date_from - one_day
    while chunk_till < date_till:
        chunk_from = chunk_till + one_day
        chunk_till = min(chunk_from + add_days, date_till)
        yield chunk_from, chunk_till


class ResBulkFetcher:
    def __init__(self, cae, allow_future_arrivals=True):
        self.cae = cae
        self.allow_future_arrivals = allow_future_arrivals
        self.startup_date = cae.startup_beg if SIHOT_PROVIDES_CHECKOUT_TIME else cae.startup_beg.date()

        self.debug_level = None
        self.date_from = None
        self.date_till = None
        self.sh_fetch_max_days = None
        self.sh_fetch_pause_seconds = None
        self.search_flags = None
        self.search_scope = None
        self.allowed_mkt_src = None
        self.allowed_mkt_grp = None

        self.adult_pers_types = None

        self.all_rows = None

    def add_options(self):
        cae = self.cae
        cae.add_option('serverIP', "IP address of the Sihot interface server", 'localhost', 'i')
        cae.add_option('serverPort', "IP port of the Sihot WEB interface", 14777, 'w')
        cae.add_option('timeout', "Timeout value for TCP/IP connections to Sihot", 1869.6, 't')
        cae.add_option('xmlEncoding', "Charset used for the Sihot xml data", SXML_DEF_ENCODING, 'e')

        cae.add_option('dateFrom', "Date" + ("/time" if SIHOT_PROVIDES_CHECKOUT_TIME else "") +
                       " of first arrival", self.startup_date - datetime.timedelta(days=1), 'F')
        cae.add_option('dateTill', "Date" + ("/time" if SIHOT_PROVIDES_CHECKOUT_TIME else "") +
                       " of last arrival", self.startup_date - datetime.timedelta(days=1), 'T')

    def load_config(self):
        cae = self.cae
        self.debug_level = cae.get_option('debugLevel')

        self.date_from = cae.get_option('dateFrom')
        self.date_till = cae.get_option('dateTill')
        if self.date_from > self.date_till:
            uprint("Specified date range is invalid - dateFrom({}) has to be before dateTill({})."
                   .format(self.date_from, self.date_till))
            cae.shutdown(318)
        elif not self.allow_future_arrivals and self.date_till > self.startup_date:
            uprint("Future arrivals cannot be migrated - dateTill({}) has to be before {}.".format(self.date_till,
                                                                                                   self.startup_date))
            cae.shutdown(319)

        # fetch given date range in chunks for to prevent timeouts and Sihot server blocking issues
        self.sh_fetch_max_days = min(max(1, cae.get_config('shFetchMaxDays', default_value=7)), 31)
        self.sh_fetch_pause_seconds = cae.get_config('shFetchPauseSeconds', default_value=1)

        self.search_flags = cae.get_config('ResSearchFlags', default_value='ALL-HOTELS')
        self.search_scope = cae.get_config('ResSearchScope', default_value='NOORDERER;NORATES;NOPERSTYPES')

        self.allowed_mkt_src = cae.get_config('MarketSources', default_value=list())
        self.allowed_mkt_grp = cae.get_config('MarketGroups', default_value=list())

        self.adult_pers_types = cae.get_config('shAdultPersTypes')

    def print_config(self):
        cae = self.cae
        uprint("Sihot Server IP/Web-port:", cae.get_option('serverIP'), cae.get_option('serverPort'))
        uprint("Sihot TCP Timeout/XML Encoding:", cae.get_option('timeout'), cae.get_option('xmlEncoding'))
        uprint("Date range including check-ins from", self.date_from.strftime(SIHOT_DATE_FORMAT),
               'and till/before', self.date_till.strftime(SIHOT_DATE_FORMAT))
        uprint("Sihot Data Fetch-maximum days (1..31, recommended 1..7)", self.sh_fetch_max_days,
               " and -pause in seconds between fetches", self.sh_fetch_pause_seconds)
        uprint("Search flags:", self.search_flags)
        uprint("Search scope:", self.search_scope)
        uprint("Allowed Market Sources:", self.allowed_mkt_src or "ALL")
        uprint("Allowed Market Groups/Channels:", self.allowed_mkt_grp or "ALL")

    def date_range_str(self):
        from_date = self.date_from.strftime(SIHOT_DATE_FORMAT)
        return "ON " + from_date if self.date_till != self.date_from else \
            ("BETWEEN" + from_date + " AND " + self.date_till.strftime(SIHOT_DATE_FORMAT))

    def fetch_all(self):
        cae = self.cae
        self.all_rows = list()
        try:
            res_search = ResSearch(cae)
            # the from/to date range filter of WEB ResSearch filters the arrival date only (not date range/departure)
            # adding flag ;WITH-PERSONS results in getting the whole reservation duplicated for each PAX in rooming list
            # adding scope NOORDERER prevents to include/use LANG/COUNTRY/NAME/EMAIL of orderer
            for chunk_beg, chunk_end in date_range_chunks(self.date_from, self.date_till, self.sh_fetch_max_days):
                chunk_rows = res_search.search(from_date=chunk_beg, to_date=chunk_end, flags=self.search_flags,
                                               scope=self.search_scope)
                if chunk_rows and isinstance(chunk_rows, str):
                    uprint(" ***  Sihot.PMS reservation search error:", chunk_rows)
                    cae.shutdown(321)
                elif not chunk_rows or not isinstance(chunk_rows, list):
                    uprint(" ***  Unspecified Sihot.PMS reservation search error")
                    cae.shutdown(324)
                uprint("  ##  Fetched {} reservations from Sihot with arrivals between {} and {} - flags={}, scope={}"
                       .format(len(chunk_rows), chunk_beg, chunk_end, self.search_flags, self.search_scope))
                for res in chunk_rows:
                    errors = list()
                    check_in, check_out = get_date_range(res)
                    if not check_in or not check_out:
                        errors.append("incomplete check-in={} check-out={}".format(check_in, check_out))
                    if not (self.date_from <= check_in <= self.date_till):
                        errors.append("arrival {} not between {} and {}"
                                      .format(check_in, self.date_from, self.date_till))
                    mkt_src = elem_value(res, 'MARKETCODE')
                    if self.allowed_mkt_src and mkt_src not in self.allowed_mkt_src:
                        errors.append("disallowed market source {}".format(mkt_src))
                    mkt_group = elem_value(res, 'CHANNEL')
                    if self.allowed_mkt_grp and mkt_group not in self.allowed_mkt_grp:
                        errors.append("disallowed market group/channel {}".format(mkt_group))
                    if errors:
                        uprint(errors)
                        cae.shutdown(327)

                self.all_rows.extend(chunk_rows)
                time.sleep(self.sh_fetch_pause_seconds)
        except Exception as ex:
            uprint(" ***  Sihot interface reservation fetch exception:", str(ex))
            print_exc()
            cae.shutdown(330)

        return self.all_rows
