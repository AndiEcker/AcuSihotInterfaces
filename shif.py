# SIHOT high level interface (based on the low level interfaces provided by sxmlif)
import datetime
import time
from traceback import print_exc

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
    if isinstance(elem_name_or_path, list):
        elem_name_or_path = elem_path_join(elem_name_or_path)
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
            elem_val = elem_def['elemListVal'][arri]
        else:
            elem_val = ""
        if not elem_val and 'elemVal' in elem_def and elem_def['elemVal']:
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


def gds_no(shd):
    return elem_value(shd, 'GDSNO')


def date_range(shd):
    """ determines the check-in/-out values (of type: datetime if SH_PROVIDES_CHECKOUT_TIME else date) """
    if SH_PROVIDES_CHECKOUT_TIME:
        d_str = shd['ARR']['elemVal']
        t_str = shd['ARR-TIME']['elemVal']
        checked_in = datetime.datetime.strptime(d_str + ' ' + t_str, SH_DATE_FORMAT)
        dt_key = 'DEP-TIME'
        if dt_key in shd and 'elemVal' in shd[dt_key] and shd[dt_key]['elemVal']:
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


def gds_no_to_obj_id(cae, hotel_id, gdsno):
    obj_id = None
    rfr = ResFetch(cae).fetch_by_gds_no(hotel_id, gdsno)
    if isinstance(rfr, dict):
        obj_id = elem_value(rfr, 'OBJID')
    return obj_id


def res_no_to_obj_id(cae, hotel_id, res_id, sub_id):
    obj_id = None
    if not sub_id:
        sub_id = '1'
    rfr = ResFetch(cae).fetch_by_res_id(hotel_id, res_id, sub_id)
    if isinstance(rfr, dict):
        obj_id = elem_value(rfr, 'OBJID')
    return obj_id


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
        self.sh_fetch_max_days = None
        self.sh_fetch_pause_seconds = None
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
        self.sh_fetch_max_days = min(max(1, cae.get_config('shFetchMaxDays', default_value=7)), 31)
        self.sh_fetch_pause_seconds = cae.get_config('shFetchPauseSeconds', default_value=1)

        self.search_flags = cae.get_config('ResSearchFlags', default_value='ALL-HOTELS')
        self.search_scope = cae.get_config('ResSearchScope', default_value='NOORDERER;NORATES;NOPERSTYPES')

        self.allowed_mkt_src = cae.get_config('MarketSources', default_value=list())
        self.allowed_mkt_grp = cae.get_config('MarketGroups', default_value=list())

        self.adult_pers_types = cae.get_config('shAdultPersTypes')

    def print_options(self):
        super(ResBulkFetcher, self).print_options()

        uprint("Date range including check-ins from", self.date_from.strftime(SH_DATE_FORMAT),
               'and till/before', self.date_till.strftime(SH_DATE_FORMAT))
        uprint("Sihot Data Fetch-maximum days (1..31, recommended 1..7)", self.sh_fetch_max_days,
               " and -pause in seconds between fetches", self.sh_fetch_pause_seconds)
        uprint("Search flags:", self.search_flags)
        uprint("Search scope:", self.search_scope)
        uprint("Allowed Market Sources:", self.allowed_mkt_src or "ALL")
        uprint("Allowed Market Groups/Channels:", self.allowed_mkt_grp or "ALL")

    def date_range_str(self):
        from_date = self.date_from.strftime(SH_DATE_FORMAT)
        return "ON " + from_date if self.date_till != self.date_from else \
            ("BETWEEN" + from_date + " AND " + self.date_till.strftime(SH_DATE_FORMAT))

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
                    cae.shutdown(3321)
                elif not chunk_rows or not isinstance(chunk_rows, list):
                    uprint(" ***  Unspecified Sihot.PMS reservation search error")
                    cae.shutdown(3324)
                uprint("  ##  Fetched {} reservations from Sihot with arrivals between {} and {} - flags={}, scope={}"
                       .format(len(chunk_rows), chunk_beg, chunk_end, self.search_flags, self.search_scope))
                valid_rows = list()
                for res in chunk_rows:
                    reasons = list()
                    check_in, check_out = date_range(res)
                    if not check_in or not check_out:
                        reasons.append("incomplete check-in={} check-out={}".format(check_in, check_out))
                    if not (self.date_from <= check_in <= self.date_till):
                        reasons.append("arrival {} not between {} and {}"
                                       .format(check_in, self.date_from, self.date_till))
                    mkt_src = elem_value(res, 'MARKETCODE')
                    if self.allowed_mkt_src and mkt_src not in self.allowed_mkt_src:
                        reasons.append("disallowed market source {}".format(mkt_src))
                    mkt_group = elem_value(res, 'CHANNEL')
                    if self.allowed_mkt_grp and mkt_group not in self.allowed_mkt_grp:
                        reasons.append("disallowed market group/channel {}".format(mkt_group))
                    if reasons:
                        self.cae.dprint("  ##  Skipped Sihot reservation:", res, " reason(s):", reasons,
                                        minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                        continue
                    valid_rows.append(res)

                self.all_rows.extend(valid_rows)
                time.sleep(self.sh_fetch_pause_seconds)
        except Exception as ex:
            uprint(" ***  Sihot interface reservation fetch exception:", str(ex))
            print_exc()
            cae.shutdown(3330)

        return self.all_rows


class ResSender:
    def __init__(self, cae):
        self.cae = cae
        self.res_sender = ResToSihot(cae, use_kernel_interface=cae.get_option('useKernelForRes'),
                                     map_res=cae.get_option('mapRes'),
                                     use_kernel_for_new_clients=cae.get_option('useKernelForClient'),
                                     map_client=cae.get_option('mapClient'),
                                     connect_to_acu=False)
        self.debug_level = cae.get_option('debugLevel')

    def send_row(self, crow):
        msg = ""
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
                                .format(crow['RUL_SIHOT_ROOM'], crow['ARR_DATE'].strftime('%d-%m-%Y'),
                                        crow['DEP_DATE'].strftime('%d-%m-%Y'), crow['SIHOT_GDSNO']) \
                      + (" Original error: " + err if self.debug_level >= DEBUG_LEVEL_VERBOSE else "")
        elif self.debug_level >= DEBUG_LEVEL_VERBOSE:
            msg = "Sent res: " + str(crow)
        return err, msg

    def get_res_no(self):
        return obj_id_to_res_no(self.cae, self.res_sender.response.objid)

    def get_warnings(self):
        return self.res_sender.get_warnings()
