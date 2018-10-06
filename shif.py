# SIHOT high level interface (based on the low level interfaces provided by sxmlif)
import datetime
import time
from traceback import format_exc, print_exc
import pprint

from ae_console_app import uprint, DEBUG_LEVEL_VERBOSE, full_stack_trace
from sxmlif import (elem_path_values, GuestSearch, ResFetch, ResSearch, ResKernelGet, ResToSihot,
                    SXML_DEF_ENCODING, ELEM_PATH_SEP,
                    USE_KERNEL_FOR_CLIENTS_DEF, MAP_CLIENT_DEF, USE_KERNEL_FOR_RES_DEF, MAP_RES_DEF,
                    ECM_DO_NOT_SEND_CLIENT, ERR_MESSAGE_PREFIX_CONTINUE)

SH_PROVIDES_CHECKOUT_TIME = False  # currently there is no real checkout time available in Sihot
SH_DATE_FORMAT = '%Y-%m-%d %H:%M:%S' if SH_PROVIDES_CHECKOUT_TIME else '%Y-%m-%d'

SH_RES_SUB_SEP = '/'

ELEM_MISSING = "(missing)"
ELEM_EMPTY = "(empty)"


ppf = pprint.PrettyPrinter(indent=12, width=96, depth=9).pformat


def add_sh_options(cae, client_port=None, add_kernel_port=False, add_maps_and_kernel_usage=False):
    cae.add_option('shServerIP', "IP address of the Sihot WEB/KERNEL server", 'localhost', 'i')
    cae.add_option('shServerPort', "IP port of the Sihot WEB interface", 14777, 'w')
    if client_port:
        # default is 14773 for Acumen and 14774 for the Sihot side (always the next higher port number)
        cae.add_option('shClientPort', "IP port of SXML interface provided by this server for Sihot", client_port, 'm')
    if add_kernel_port:
        # e.g. for GuestBulkFetcher we need also the kernel interface port of Sihot
        cae.add_option('shServerKernelPort', "IP port of the KERNEL interface of the Sihot server", 14772, 'k')
    cae.add_option('shTimeout', "Timeout value for TCP/IP connections to Sihot", 1869.6, 't')
    cae.add_option('shXmlEncoding', "Charset used for the Sihot xml data", SXML_DEF_ENCODING, 'e')
    if add_maps_and_kernel_usage:
        cae.add_option('useKernelForClient', "Used interface for clients (0=web, 1=kernel)", USE_KERNEL_FOR_CLIENTS_DEF,
                       'g', choices=(0, 1))
        cae.add_option('mapClient', "Guest/Client mapping of xml to db items", MAP_CLIENT_DEF, 'm')
        cae.add_option('useKernelForRes', "Used interface for reservations (0=web, 1=kernel)", USE_KERNEL_FOR_RES_DEF,
                       'z', choices=(0, 1))
        cae.add_option('mapRes', "Reservation mapping of xml to db items", MAP_RES_DEF, 'n')


def print_sh_options(cae):
    uprint("Sihot server IP/WEB-interface-port:", cae.get_option('shServerIP'), cae.get_option('shServerPort'))
    client_port = cae.get_option('shClientPort')
    if client_port:
        ip_addr = cae.get_config('shClientIP', default_value=cae.get_option('shServerIP'))
        uprint("Sihot client IP/port for listening:", ip_addr, client_port)
    kernel_port = cae.get_option('shServerKernelPort')
    if kernel_port:
        uprint("Sihot server KERNEL-interface-port:", kernel_port)
    uprint("Sihot TCP Timeout/XML Encoding:", cae.get_option('shTimeout'), cae.get_option('shXmlEncoding'))


def guest_data(cae, obj_id):
    guest_search = GuestSearch(cae)
    ret = guest_search.get_guest(obj_id)
    return ret


def elem_path_join(elem_names):
    """
    convert list of element names to element path.
    :param elem_names:  list of element names.
    :return:            element path.
    """
    return ELEM_PATH_SEP.join(elem_names)


def elem_value(shd, elem_name_or_path, arri=0, verbose=False, default_value=None):
    """
    get the xml element value from the shd row_dict variable, using array index (arri) in case of multiple values

    :param shd:                 dict of sihot data row with the element names as the dict keys.
    :param elem_name_or_path:   either single element name (str), element path (str) or list of path element names.
    :param arri:                index of element array value (starting with 0).
    :param verbose:             pass True to get ELEM_EMPTY/ELEM_MISSING pseudo values instead of default_value value.
    :param default_value:       default element value.
    :return:                    element value.
    """
    elem_path = ""
    if isinstance(elem_name_or_path, list):
        if len(elem_name_or_path) > 1:
            elem_path = elem_path_join(elem_name_or_path)
        else:
            elem_name_or_path = elem_name_or_path[0]
    elif ELEM_PATH_SEP in elem_name_or_path:
        elem_path = elem_name_or_path
    elem_nam = elem_path.rsplit(ELEM_PATH_SEP, 1)[1] if elem_path else elem_name_or_path

    elem_val = None
    if elem_nam not in shd:
        elem_val = ELEM_MISSING if verbose else default_value
    elif elem_path:
        val_arr = elem_path_values(shd, elem_path)
        if 0 <= arri < len(val_arr):
            elem_val = val_arr[arri]
    else:
        elem_def = shd[elem_nam]
        if 'elemListVal' in elem_def and len(elem_def['elemListVal']) > arri:
            elem_val = elem_def['elemListVal'][arri]
        else:
            elem_val = ""
        if not elem_val and elem_def.get('elemVal'):
            elem_val = elem_def['elemVal']

    if not elem_val:
        elem_val = ELEM_EMPTY if verbose else default_value

    return elem_val


def hotel_and_res_id(shd):
    ho_id = elem_value(shd, 'RES-HOTEL')
    res_nr = elem_value(shd, 'RES-NR')
    sub_nr = elem_value(shd, 'SUB-NR')
    if not ho_id or not res_nr:
        return None, None
    return ho_id, res_nr + (SH_RES_SUB_SEP + sub_nr if sub_nr else '') + '@' + ho_id


def pax_count(shd):
    adults = elem_value(shd, 'NOPAX')
    if not adults:
        adults = 0
    else:
        adults = int(adults)
    children = elem_value(shd, 'NOCHILDS')
    if not children:
        children = 0
    else:
        children = int(children)
    return adults + children


def gds_number(shd):
    return elem_value(shd, 'GDSNO')


def date_range(shd):
    """ determines the check-in/-out values (of type: datetime if SH_PROVIDES_CHECKOUT_TIME else date) """
    if SH_PROVIDES_CHECKOUT_TIME:
        d_str = shd['ARR']['elemVal']
        t_str = shd['ARR-TIME']['elemVal']
        checked_in = datetime.datetime.strptime(d_str + ' ' + t_str, SH_DATE_FORMAT)
        dt_key = 'DEP-TIME'
        if dt_key in shd and shd[dt_key].get('elemVal'):
            d_str = shd['DEP']['elemVal']
            t_str = shd[dt_key]['elemVal']
            checked_out = datetime.datetime.strptime(d_str + ' ' + t_str, SH_DATE_FORMAT)
        else:
            checked_out = None
    else:
        checked_in = datetime.datetime.strptime(shd['ARR']['elemVal'], SH_DATE_FORMAT).date()
        checked_out = datetime.datetime.strptime(shd['DEP']['elemVal'], SH_DATE_FORMAT).date()
    return checked_in, checked_out


def date_range_chunks(date_from, date_till, fetch_max_days):
    one_day = datetime.timedelta(days=1)
    add_days = datetime.timedelta(days=fetch_max_days) - one_day
    chunk_till = date_from - one_day
    while chunk_till < date_till:
        chunk_from = chunk_till + one_day
        chunk_till = min(chunk_from + add_days, date_till)
        yield chunk_from, chunk_till


def gds_no_to_ids(cae, hotel_id, gdsno):
    ids = dict(ResHotelId=hotel_id, ResGdsNo=gdsno)
    rfr = ResFetch(cae).fetch_by_gds_no(hotel_id, gdsno)
    if isinstance(rfr, dict):
        ids['ResObjId'] = elem_value(rfr, ['SIHOT-Document', 'RESERVATION', 'OBJID'])
        ids['ResResId'] = elem_value(rfr, 'RES-NR')
        ids['ResSubId'] = elem_value(rfr, 'SUB-NR')
        ids['ResSfId'] = elem_value(rfr, 'NN2')
    return ids


def gds_no_to_obj_id(cae, hotel_id, gdsno):
    return gds_no_to_ids(cae, hotel_id, gdsno).get('ResObjId')


def res_no_to_ids(cae, hotel_id, res_id, sub_id):
    ret = dict(ResHotelId=hotel_id, ResResId=res_id, ResSubId=sub_id)
    rfr = ResFetch(cae).fetch_by_res_id(hotel_id, res_id, sub_id)
    if isinstance(rfr, dict):
        ret['ResObjId'] = elem_value(rfr, ['SIHOT-Document', 'RESERVATION', 'OBJID'])
        ret['ResGdsNo'] = elem_value(rfr, 'GDSNO')
        ret['ResSfId'] = elem_value(rfr, 'NN2')
    else:
        ret = rfr
    return ret


def res_no_to_obj_id(cae, hotel_id, res_id, sub_id):
    return res_no_to_ids(cae, hotel_id, res_id, sub_id).get('ResObjId')


def res_search(cae, date_from, date_till=None, mkt_sources=None, mkt_groups=None, max_los=28,
               search_flags='', search_scope='', chunk_pause=1):
    """
    search reservations with the criteria specified by the parameters.

    :param cae:             instance of the application environment specifying searched Sihot server.
    :param date_from:       date of first day of included arrivals.
    :param date_till:       date of last day of included arrivals.
    :param mkt_sources:     list of market source codes.
    :param mkt_groups:      list of market group codes.
    :param max_los:         integer with maximum length of stay.
    :param search_flags:    string with search flag words (separated with semicolon).
    :param search_scope:    string with search scope words (separated with semicolon).
    :param chunk_pause:     integer with seconds to pause between fetch of date range chunks.
    :return:                string with error message if error or list of Sihot reservations.
    """
    if not date_till:
        date_till = date_from

    err_msg = ""
    all_rows = list()
    try:
        rs = ResSearch(cae)
        # the from/to date range filter of WEB ResSearch filters the arrival date only (not date range/departure)
        # adding flag ;WITH-PERSONS results in getting the whole reservation duplicated for each PAX in rooming list
        # adding scope NOORDERER prevents to include/use LANG/COUNTRY/NAME/EMAIL of orderer
        for chunk_beg, chunk_end in date_range_chunks(date_from, date_till, max_los):
            chunk_rows = rs.search(from_date=chunk_beg, to_date=chunk_end, flags=search_flags,
                                   scope=search_scope)
            if chunk_rows and isinstance(chunk_rows, str):
                err_msg = "Sihot.PMS reservation search error: {}".format(chunk_rows)
                break
            elif not chunk_rows or not isinstance(chunk_rows, list):
                err_msg = "Unspecified Sihot.PMS reservation search error"
                break
            cae.dprint("  ##  Fetched {} reservations from Sihot with arrivals between {} and {} - flags={}, scope={}"
                       .format(len(chunk_rows), chunk_beg, chunk_end, search_flags, search_scope))
            valid_rows = list()
            for res in chunk_rows:
                reasons = list()
                check_in, check_out = date_range(res)
                if not check_in or not check_out:
                    reasons.append("incomplete check-in={} check-out={}".format(check_in, check_out))
                if not (date_from <= check_in <= date_till):
                    reasons.append("arrival {} not between {} and {}".format(check_in, date_from, date_till))
                mkt_src = elem_value(res, 'MARKETCODE')
                if mkt_sources and mkt_src not in mkt_sources:
                    reasons.append("disallowed market source {}".format(mkt_src))
                mkt_group = elem_value(res, 'CHANNEL')
                if mkt_groups and mkt_group not in mkt_groups:
                    reasons.append("disallowed market group/channel {}".format(mkt_group))
                if reasons:
                    cae.dprint("  ##  Skipped Sihot reservation:", res, " reason(s):", reasons,
                               minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                    continue
                valid_rows.append(res)

            all_rows.extend(valid_rows)
            time.sleep(chunk_pause)
    except Exception as ex:
        err_msg = "Sihot interface reservation fetch exception: {}\n{}".format(ex, format_exc())

    return err_msg or all_rows


def obj_id_to_res_no(cae, obj_id):
    """
    using RESERVATION-GET oc from KERNEL interface (see 7.3 in SIHOT KERNEL interface doc).
    :param cae:         Console App Environment instance.
    :param obj_id:      Sihot Reservation Object Id.
    :return:            reservation number as tuple of (hotel_id, res_id, sub_id) or None if not found
    """
    return ResKernelGet(cae).fetch_res_no(obj_id)


class BulkFetcherBase:
    def __init__(self, cae, add_kernel_port=True):
        self.cae = cae
        self.add_kernel_port = add_kernel_port
        self.debug_level = None
        self.startup_date = cae.startup_beg if SH_PROVIDES_CHECKOUT_TIME else cae.startup_beg.date()
        self.all_rows = None

    def add_options(self):
        add_sh_options(self.cae, add_kernel_port=self.add_kernel_port)

    def load_options(self):
        self.debug_level = self.cae.get_option('debugLevel')

    def print_options(self):
        print_sh_options(self.cae)


class GuestBulkFetcher(BulkFetcherBase):
    """
    WIP/NotUsed/NoTests: the problem is with GUEST-SEARCH is that there is no way to bulk fetch all guests
    because the search criteria is not providing range search for to split in slices. Fetching all 600k clients
    is resulting in a timeout error after 30 minutes (the Sihot interface 'shTimeout' option value)
    """
    def fetch_all(self):
        cae = self.cae
        self.all_rows = list()
        try:
            guest_search = GuestSearch(cae)
            search_criteria = dict(SH_FLAGS='FIND-ALSO-DELETED-GUESTS', SORT='GUEST-NR')
            search_criteria['MAX-ELEMENTS'] = 600000
            # MATCH-SM (holding the Salesforce/SF client ID) is not available in Kernel GUEST-SEARCH (only GUEST-GET)
            self.all_rows = guest_search.search_guests(search_criteria, ['MATCHCODE', 'OBJID', 'MATCH-SM'])
        except Exception as ex:
            uprint(" ***  Sihot interface guest bulk fetch exception:", str(ex))
            print_exc()
            cae.shutdown(2130)

        return self.all_rows


class ResBulkFetcher(BulkFetcherBase):
    def __init__(self, cae, allow_future_arrivals=True):
        super(ResBulkFetcher, self).__init__(cae, add_kernel_port=False)

        self.allow_future_arrivals = allow_future_arrivals

        self.date_from = None
        self.date_till = None
        self.max_length_of_stay = None
        self.fetch_chunk_pause_seconds = None
        self.search_flags = None
        self.search_scope = None
        self.allowed_mkt_src = None
        self.allowed_mkt_grp = None

        self.adult_pers_types = None

    def add_options(self):
        super(ResBulkFetcher, self).add_options()
        self.cae.add_option('dateFrom', "Date" + ("/time" if SH_PROVIDES_CHECKOUT_TIME else "") +
                            " of first arrival", self.startup_date - datetime.timedelta(days=1), 'F')
        self.cae.add_option('dateTill', "Date" + ("/time" if SH_PROVIDES_CHECKOUT_TIME else "") +
                            " of last arrival", self.startup_date - datetime.timedelta(days=1), 'T')

    def load_options(self):
        super(ResBulkFetcher, self).load_options()

        cae = self.cae
        self.date_from = cae.get_option('dateFrom')
        self.date_till = cae.get_option('dateTill')
        if self.date_from > self.date_till:
            uprint("Specified date range is invalid - dateFrom({}) has to be before dateTill({})."
                   .format(self.date_from, self.date_till))
            cae.shutdown(3318)
        elif not self.allow_future_arrivals and self.date_till > self.startup_date:
            uprint("Future arrivals cannot be migrated - dateTill({}) has to be before {}.".format(self.date_till,
                                                                                                   self.startup_date))
            cae.shutdown(3319)

        # fetch given date range in chunks for to prevent timeouts and Sihot server blocking issues
        self.max_length_of_stay = min(max(1, cae.get_config('shFetchMaxDays', default_value=7)), 31)
        self.fetch_chunk_pause_seconds = cae.get_config('shFetchPauseSeconds', default_value=1)

        self.search_flags = cae.get_config('ResSearchFlags', default_value='ALL-HOTELS')
        self.search_scope = cae.get_config('ResSearchScope', default_value='NOORDERER;NORATES;NOPERSTYPES')

        self.allowed_mkt_src = cae.get_config('MarketSources', default_value=list())
        self.allowed_mkt_grp = cae.get_config('MarketGroups', default_value=list())

        self.adult_pers_types = cae.get_config('shAdultPersTypes')

    def print_options(self):
        super(ResBulkFetcher, self).print_options()

        uprint("Date range including check-ins from", self.date_from.strftime(SH_DATE_FORMAT),
               'and till/before', self.date_till.strftime(SH_DATE_FORMAT))
        uprint("Sihot Data Fetch-maximum days (1..31, recommended 1..7)", self.max_length_of_stay,
               " and -pause in seconds between fetches", self.fetch_chunk_pause_seconds)
        uprint("Search flags:", self.search_flags)
        uprint("Search scope:", self.search_scope)
        uprint("Allowed Market Sources:", self.allowed_mkt_src or "ALL")
        uprint("Allowed Market Groups/Channels:", self.allowed_mkt_grp or "ALL")

    def date_range_str(self):
        from_date = self.date_from.strftime(SH_DATE_FORMAT)
        return "ON " + from_date if self.date_till != self.date_from else \
            ("BETWEEN" + from_date + " AND " + self.date_till.strftime(SH_DATE_FORMAT))

    def fetch_all(self):
        self.all_rows = res_search(self.cae, self.date_from, self.date_till,
                                   mkt_sources=self.allowed_mkt_src, mkt_groups=self.allowed_mkt_grp,
                                   max_los=self.max_length_of_stay,
                                   search_flags=self.search_flags, search_scope=self.search_scope,
                                   chunk_pause=self.fetch_chunk_pause_seconds)
        return self.all_rows


class ResSender:
    def __init__(self, cae):
        self.cae = cae
        self.res_sender = ResToSihot(cae)
        self.debug_level = cae.get_option('debugLevel')

    @staticmethod
    def complete_res_data(crow):
        """
        complete reservation data row (crow) with the default values (specified in row_def underneath), while
        the following fields are mandatory:
            ResHotelId, ResArrival, ResDeparture, ResRoomCat, ResMktSegment, ResOrdererMc, ResGdsNo.

        :param crow:    reservation data row (dict).
        :return:        completed reservation data row (new dict).

        These fields will not be completed/changed at all:
            ResRoomNo, ResNote, ResLongNote, ResFlightNo (flight no), ResAllotmentNo, ResVoucherNo.

        optional fields:
            ResOrdererId (alternatively usable instead of matchcode value ResOrdererMc).
            ResAdult1Surname and ResAdult1Forename (surname and firstname)
            ResAdult2Surname and ResAdult2Forename ( ... )
        optional auto-populated fields (==default value):
            ShId (==ResOrdererId)
            ResAction (=='INSERT')
            ResBooked (==today)
            ResPriceCat (==ResRoomCat)
            ResBoard (=='RO')
            ResAccount (==1)
            ResSource (=='A')
            ResRateSegment (==ResMktSegment)
            ResMktGroup (=='RS')
            ResAdults (==2)
            ResChildren (==0)

        """
        row_def = dict(ResStatus='1',
                       AcId=crow.get('ResOrdererMc', ''),
                       ShId=crow.get('ResOrdererId', ''),
                       ResAction='INSERT',
                       ResBooked=datetime.datetime.today(),
                       ResPriceCat=crow.get('ResRoomCat', ''),
                       ResBoard='RO',    # room only (no board/meal-plan)
                       ResAccount=1,
                       ResSource='A',
                       ResRateSegment=crow.get('ResMktSegment', ''),
                       ResMktGroup='RS',
                       ResAdults=2,
                       ResChildren=0,
                       )
        row_def.update(crow)

        return row_def

    def send_row(self, crow):
        msg = ""
        crow = self.complete_res_data(crow)
        try:
            err = self.res_sender.send_row_to_sihot(crow, ensure_client_mode=ECM_DO_NOT_SEND_CLIENT)
        except Exception as ex:
            err = "ResSender.send_row() exception: {}".format(full_stack_trace(ex))
        if err:
            if err.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                msg = "Ignoring error sending res: " + str(crow)
                err = ""
            elif 'setDataRoom not available!' in err:  # was: 'A_Persons::setDataRoom not available!'
                err = "Apartment {} occupied between {} and {} - created GDS-No {} for manual allocation." \
                                .format(crow['ResRoomNo'], crow['ResArrival'].strftime('%d-%m-%Y'),
                                        crow['ResDeparture'].strftime('%d-%m-%Y'), crow['ResGdsNo']) \
                      + (" Original error: " + err if self.debug_level >= DEBUG_LEVEL_VERBOSE else "")
        elif self.debug_level >= DEBUG_LEVEL_VERBOSE:
            msg = "Sent res: " + str(crow)
        return err, msg

    def get_res_no(self):
        return obj_id_to_res_no(self.cae, self.res_sender.response.objid)

    def get_warnings(self):
        return self.res_sender.get_warnings()
