"""
    SihotOccLogChecker is a tool for to check the SXML_ACUMEN log file (Sihot check-ins/-outs and room moves).

    0.1     first beta.
"""
import datetime
from traceback import print_exc
import pprint

from ae_console_app import ConsoleApp, uprint, DEBUG_LEVEL_VERBOSE
from ae_db import OraDB, DEF_USER, DEF_DSN
# from sxmlif import ResSearch, SXML_DEF_ENCODING, PARSE_ONLY_TAG_PREFIX
from ae_notification import Notification

__version__ = '0.1'

SIHOT_DATE_FORMAT = '%d-%m-%y %H:%M:%S'

startup_date = datetime.datetime.now()

PP_DEF_WIDTH = 120
pretty_print = pprint.PrettyPrinter(indent=6, width=PP_DEF_WIDTH, depth=9)

cae = ConsoleApp(__version__, "Sihot SXML interface log file checks and optional Acumen room occupation status fixes")

cae.add_parameter('sxml_log_file_name', help="SXML Logfile name (and path)")

cae.add_option('dateFrom', "Date/time of first checked occupation", startup_date - datetime.timedelta(days=1), 'F')
cae.add_option('dateTill', "Date/time of last checked occupation", startup_date - datetime.timedelta(days=1), 'T')
cae.add_option('correctAcumen', "Correct room occupation status (check-in/-out) in Acumen (0=No, 1=Yes)", False, 'A')

cae.add_option('acuUser', "User name of Acumen/Oracle system", DEF_USER, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", DEF_DSN, 'd')
'''
cae.add_option('serverIP', "IP address of the Sihot interface server", 'localhost', 'i')
cae.add_option('serverPort', "IP port of the Sihot WEB interface", 14777, 'w')
cae.add_option('timeout', "Timeout value for TCP/IP connections to Sihot", 1869.6, 't')
cae.add_option('xmlEncoding', "Charset used for the Sihot xml data", SXML_DEF_ENCODING, 'e')
'''
cae.add_option('smtpServerUri', "SMTP notification server account URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP sender/from address", '', 'f')
cae.add_option('smtpTo', "List/Expression of SMTP receiver/to addresses", list(), 'r')

cae.add_option('warningsMailToAddr', "Warnings SMTP receiver/to addresses (if differs from smtpTo)", list(), 'v')


debug_level = cae.get_option('debugLevel')

sxml_log_file_name = cae.get_parameter('sxml_log_file_name')
uprint("SXML log file:", sxml_log_file_name)
date_from = cae.get_option('dateFrom')
date_till = cae.get_option('dateTill')
uprint("Date range including check-ins from", date_from.strftime(SIHOT_DATE_FORMAT),
       'and till/before', date_till.strftime(SIHOT_DATE_FORMAT))
ac_id = cae.get_option('acuDSN')
uprint('Acumen Usr/DSN:', cae.get_option('acuUser'), ac_id)
sys_id = ac_id
'''
sh_id = cae.get_option('serverIP')
uprint("Server IP/Web-port:", sh_id, cae.get_option('serverPort'))
uprint("TCP Timeout/XML Encoding:", cae.get_option('timeout'), cae.get_option('xmlEncoding'))
sys_id = ac_id + ("/" + sh_id if sh_id else "")
'''

correct_acumen = cae.get_option('correctAcumen')
if correct_acumen:
    uprint("!!!!  Correcting Acumen Room Occupation Status")
if date_from > date_till:
    uprint("Specified date range is invalid - dateFrom({}) has to be before dateTill({}).".format(date_from, date_till))
    cae.shutdown(18)
elif date_till > (startup_date if type(date_till) is datetime.datetime else startup_date.date()):
    uprint("Future arrivals cannot be checked - dateTill({}) has to be before {}.".format(date_till, startup_date))
    cae.shutdown(19)

max_days_diff = cae.get_config('maxDaysDiff', default_value=3)
uprint("Maximum number of days from expected arrival/departure:", max_days_diff)

'''
# fetch given date range in chunks for to prevent timeouts and Sihot server blocking issues
sh_fetch_max_days = min(max(1, cae.get_config('shFetchMaxDays', default_value=7)), 31)
sh_fetch_pause_seconds = cae.get_config('shFetchPauseSeconds', default_value=1)
uprint("Sihot Data Fetch-maximum days (1..31, recommended 1..7)", sh_fetch_max_days,
       " and -pause in seconds between fetches", sh_fetch_pause_seconds)
search_flags = cae.get_config('ResSearchFlags', default_value='ALL-HOTELS')
uprint("Search flags:", search_flags)
search_scope = cae.get_config('ResSearchScope', default_value='NOORDERER;NORATES;NOPERSTYPES')
uprint("Search scope:", search_scope)

# html font is not working in Outlook: <font face="Courier New, Courier, monospace"> ... </font>
msf_beg = cae.get_config('monoSpacedFontBegin', default_value='<pre>')
msf_end = cae.get_config('monoSpacedFontEnd', default_value='</pre>')
'''

notification = warning_notification_emails = None
if cae.get_option('smtpServerUri') and cae.get_option('smtpFrom') and cae.get_option('smtpTo'):
    notification = Notification(smtp_server_uri=cae.get_option('smtpServerUri'),
                                mail_from=cae.get_option('smtpFrom'),
                                mail_to=cae.get_option('smtpTo'),
                                used_system=sys_id,
                                debug_level=cae.get_option('debugLevel'))
    uprint("SMTP Uri/From/To:", cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))
    warning_notification_emails = cae.get_option('warningsMailToAddr')
    if warning_notification_emails:
        uprint("Warnings SMTP receiver address(es):", warning_notification_emails)

log_items = list()              # processing log entries
log_errors = list()             # processing errors
notification_lines = list()     # user discrepancies/warnings

ac_rows = list()                # acumen reservation occupation
sh_rows = list()                # sihot reservation requests
room_status = list()            # occupation room status changes (from SXML log file)


class OccData:
    def __init__(self, oc, ts, rn, aro_code, aro_status, aro_exp_arrive, aro_exp_depart, aro_desc=''):
        super(OccData, self).__init__()
        self.op_code = oc
        self.time_stamp = ts
        self.room_no = rn
        self.aro_code = aro_code
        self.aro_status = aro_status
        self.aro_exp_arrive = aro_exp_arrive
        self.aro_exp_depart = aro_exp_depart
        self.aro_desc = aro_desc

    def __repr__(self):
        return "OccData(" + repr(self.op_code) + ", " + repr(self.time_stamp) + ", " + repr(self.room_no) \
               + ", " + repr(self.aro_code) + ", " + repr(self.aro_status) \
               + ", " + repr(self.aro_exp_arrive) + ", " + repr(self.aro_exp_depart) \
               + ", " + repr(self.aro_desc)  \
               + ")"


def add_log_msg(msg, is_error=False, importance=2):
    global log_errors, log_items
    assert 0 < importance < 5
    if is_error:
        log_errors.append(msg)
    msg = " " * (4 - importance) + ("*" if is_error else "#") * importance + "  " + msg
    log_items.append(msg)
    uprint(msg)


def notification_add_line(msg, is_error=False):
    global notification_lines
    add_log_msg(msg, is_error=is_error)
    notification_lines.append(msg)


'''
ELEM_MISSING = "(missing)"
ELEM_EMPTY = "(empty)"

def get_col_val(shd, col_nam, arri=-1, verbose=False, default_value=None):
    """ get the column value from the row_dict variable, using arr_index in case of multiple values """
    if col_nam not in shd:
        col_val = ELEM_MISSING if verbose else default_value
    else:
        col_def = shd[col_nam]
        if 'elemListVal' in col_def and len(col_def['elemListVal']) > arri:
            col_val = [_ for _ in col_def['elemListVal'] if _] if arri == -1 else ""
            if not col_val:
                col_val = col_def['elemListVal'][arri]
        else:
            col_val = ""
        if not col_val and 'elemVal' in col_def and col_def['elemVal']:
            col_val = col_def['elemVal']
        if not col_val:
            col_val = ELEM_EMPTY if verbose else default_value

    return col_val


def get_hotel_and_res_id(shd):
    h_id = get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'RES-HOTEL')
    r_num = get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'RES-NR')
    s_num = get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'SUB-NR')
    if not h_id or not r_num:
        return None, None
    return h_id, r_num + ("/" + s_num if s_num else "") + "@" + h_id


def get_date_range(shd):
    """ determines the check-in/-out values (of type: datetime if SIHOT_PROVIDES_CHECKOUT_TIME else date) """
    if SIHOT_PROVIDES_CHECKOUT_TIME:
        d_str = shd['ARR']['elemVal']
        t_str = shd['ARR-TIME']['elemVal']
        checked_in = datetime.datetime.strptime(d_str + ' ' + t_str, SIHOT_DATE_FORMAT)
        dt_key = PARSE_ONLY_TAG_PREFIX + 'DEP-TIME'
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


def name_is_valid(name):
    if name:
        name = name.lower()
    return name not in ("adult 1", "adult 2", "adult 3", "adult 4", "adult 5", "adult 6",
                        "child 1", "child 1", "child 2", "child 4", "no name", "not specified", "", None)


def valid_name_indexes(shd):
    indexes = list()
    if 'NAME' in shd and 'NAME2' in shd:
        col_def1 = shd['NAME']
        col_def2 = shd['NAME2']
        if 'elemListVal' in col_def1 and 'elemListVal' in col_def2:
            for idx, name in enumerate(col_def1['elemListVal']):
                if len(col_def2['elemListVal']) > idx:
                    name2 = col_def2['elemListVal'][idx]
                    if name and name_is_valid(name) and name2 and name_is_valid(name2):
                        indexes.append(idx)
        if not indexes and 'elemVal' in col_def1 and col_def1['elemVal'] and name_is_valid(col_def1['elemVal']) \
                and 'elemVal' in col_def2 and col_def2['elemVal'] and name_is_valid(col_def2['elemVal']):
            col_def1['elemListVal'] = [col_def1['elemVal']]
            col_def2['elemListVal'] = [col_def2['elemVal']]
            indexes.append(0)
    return indexes


def date_range_chunks():
    one_day = datetime.timedelta(days=1)
    add_days = datetime.timedelta(days=sh_fetch_max_days) - one_day
    chunk_till = date_from - one_day
    while chunk_till < date_till:
        chunk_from = chunk_till + one_day
        chunk_till = min(chunk_from + add_days, date_till)
        yield chunk_from, chunk_till
'''


def get_log_time_stamp(log_line):
    try:
        # time stamp format 'yyyymmdd hhmmss.f', e.g. '20170203 102848.677')
        date_time = datetime.datetime.strptime(log_line[:19], '%Y%m%d %H%M%S.%f')
    except ValueError:
        date_time = None
    return date_time


def get_xml_element(xml, element_name):
    ret = ''
    beg = xml.find('<' + element_name + '>')
    if beg >= 0:
        end = xml.find('</' + element_name + '>', beg + 1)
        if end >= 0:
            ret = xml[beg + len(element_name) + 2:end]
    return ret


def check_occ_change(dt, oc, rn, sent_xml, ln):
    def _filter_ac_rows(d):
        if oc in ('CI', 'RI'):
            return [_ for _ in ac_rows if _[3] - d <= dtc <= _[3] + d and _[5] == rn]
        else:  # oc in ('CO', 'RO')
            return [_ for _ in ac_rows if _[4] - d <= dtc <= _[4] + d and _[5] == rn]

    dtc = datetime.datetime(dt.year, dt.month, dt.day) if type(date_from) is datetime.date else dt
    diff = datetime.timedelta(days=max_days_diff)
    rows = _filter_ac_rows(diff)
    sn = get_xml_element(sent_xml, 'SN')
    if len(rows) > 1:
        if debug_level >= DEBUG_LEVEL_VERBOSE:
            add_log_msg("More than one ({}) matching Acumen reservations found: {}".format(len(rows), rows))
        if sn:      # filter on surname (only given for oc==CI/RM currently)
            rows = [_ for _ in rows if _[2].upper() == sn.upper()]
            if debug_level >= DEBUG_LEVEL_VERBOSE:
                add_log_msg("... {} after filtering by surname {}".format(len(rows), sn))
        while len(rows) != 1 and diff.days > 0:
            diff = datetime.timedelta(days=diff.days - 1)
            rows = _filter_ac_rows(diff)
            if debug_level >= DEBUG_LEVEL_VERBOSE:
                add_log_msg("... {} after filtering by decremented maxDiffDays to {}".format(len(rows), diff.days))
    dts = dt.strftime(SIHOT_DATE_FORMAT)
    if len(rows) > 1:
        add_log_msg("{}:{: >4}@{}#{: <6}  More than one Acumen reservation found: {}".format(oc, rn, dts, ln, rows),
                    is_error=True)
    elif len(rows) == 1:
        r = rows[0]
        od = OccData(oc, dt, rn, r[0], r[6], r[3], r[4], r[1] + "/" + r[2] + "=" + r[9] + "#" + str(r[10]))
        room_status.append(od)
        add_log_msg("{}:{: >4}@{}#{: <6}  Occupation/Acumen data: {}/{}".format(oc, rn, dts, ln, od, rows[0]))
    elif debug_level >= DEBUG_LEVEL_VERBOSE:
        add_log_msg("{}:{: >4}@{}#{: <6}  No Acumen reservation found".format(oc, rn, dts, ln))


def check_occ_discrepancies(od):
    wrn = list()
    cols = None         # T_ARO columns to be updated
    msg = dict(CI="Check-In", CO="Check-Out", RI="Room-Move-Transfer-In", RO="Room-Move-Transfer-Out")[od.op_code]
    if od.op_code in ('CI', 'RI'):
        if od.aro_status not in (300, 330):
            if od.aro_status in (320, 390):
                wrn.append("already checked-out - status={}".format(od.aro_status))
            else:
                cols = dict(ARO_STATUS=300 if od.op_code == 'CI' else 330, ARO_TIMEIN=od.time_stamp, ARO_TIMEOUT=None)
    else:       # if od.op_code in ('CO', 'RO'):
        if od.aro_status not in (320, 390):
            if od.aro_status in (300, 330):
                cols = dict(ARO_STATUS=390, ARO_TIMEOUT=od.time_stamp)
            else:
                cols = dict(ARO_STATUS=390 if od.op_code == 'CO' else 320, ARO_TIMEIN=od.aro_exp_arrive,
                            ARO_TIMEOUT=od.time_stamp)
                wrn.append("TimeIn missing too - status={}".format(od.aro_status))
    if cols and debug_level >= DEBUG_LEVEL_VERBOSE:
        msg += " FIX=" + str(cols)
    if cols or wrn:
        if "#None" in od.aro_desc:
            wrn.append("No GdsNo")
        elif "," in od.aro_desc[od.aro_desc.find("#"):]:
            wrn.append("Multiple GdsNos")
        if wrn:
            msg += " (" + ", ".join(wrn) + ")"
        notification_add_line("Missing {}: {}".format(msg, od))
    if cols and correct_acumen:
        err = ora_db.update('T_ARO', cols, "ARO_CODE = :aro_code", bind_vars=dict(aro_code=od.aro_code))
        if err:
            notification_add_line("Error {} in correcting missing {}: {}".format(err, msg, od), is_error=True)
            ora_db.rollback()
        else:
            notification_add_line("Successfully fixed missing {}: {}".format(msg, od))
            ora_db.commit()


add_log_msg("Fetching reservations from Acumen", importance=4)
try:
    ora_db = OraDB(cae.get_option('acuUser'), cae.get_option('acuPassword'), cae.get_option('acuDSN'),
                   debug_level=cae.get_option('debugLevel'))
    err_msg = ora_db.connect()
    if not err_msg:
        err_msg = ora_db.select('T_ARO inner join T_CD on ARO_CDREF = CD_CODE',
                                ['ARO_CODE', 'ARO_CDREF', 'CD_SNAM1', 'ARO_EXP_ARRIVE', 'ARO_EXP_DEPART',
                                 "case when F_RESORT(ARO_APREF) = 'PBC' and length(ARO_APREF) = 3 then"
                                 " '0' end || ARO_APREF as ARO_APREF",
                                 'ARO_STATUS', 'ARO_TIMEIN', 'ARO_TIMEOUT', 'ARO_ROREF',
                                 "(select f_stragg(RU_CODE) from T_RU where RU_RHREF = ARO_RHREF and RU_STATUS <> 120"
                                 " and RU_FROM_DATE < least(ARO_EXP_DEPART, trunc(:till) + :days)"
                                 " and RU_FROM_DATE + RU_DAYS > greatest(ARO_EXP_ARRIVE, trunc(:beg) - :days))"
                                 " as GDS_NOS"],
                                "ARO_EXP_ARRIVE < trunc(:till) + :days and ARO_EXP_DEPART > trunc(:beg) - :days"
                                " and ARO_STATUS <> 120 and F_RESORT(ARO_APREF)"
                                " in (select LU_ID from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ACTIVE = 1)"
                                " order by ARO_EXP_ARRIVE desc",    # order to have old room last for RM
                                bind_vars=dict(beg=date_from, till=date_till, days=max_days_diff))

    if err_msg:
        add_log_msg(err_msg, is_error=True, importance=3)
    else:
        ac_rows = ora_db.fetch_all()
except Exception as ex:
    add_log_msg("Acumen reservation fetch exception: {}".format(ex), is_error=True, importance=3)
    print_exc()

'''
add_log_msg("Fetching reservations from Sihot", importance=4)
try:
    res_search = ResSearch(cae)
    # the from/to date range filter of WEB ResSearch is filtering the arrival date only (not date range/departure)
    # adding flag ;WITH-PERSONS results in getting the whole reservation duplicated for each PAX in rooming list
    # adding scope NOORDERER prevents to include/use LANG/COUNTRY/NAME/EMAIL of orderer
    for chunk_beg, chunk_end in date_range_chunks():
        chunk_rows = res_search.search(from_date=chunk_beg, to_date=chunk_end, flags=search_flags, scope=search_scope)
        if chunk_rows and isinstance(chunk_rows, str):
            add_log_msg("Sihot.PMS reservation search error: {}".format(chunk_rows), is_error=True, importance=3)
        elif not chunk_rows or not isinstance(chunk_rows, list):
            add_log_msg("Unspecified Sihot.PMS reservation search error", is_error=True, importance=3)
        else:
            add_log_msg("Fetched {} reservations from Sihot with arrivals between {} and {} - flags={}, scope={}"
                        .format(len(chunk_rows), chunk_beg, chunk_end, search_flags, search_scope), is_error=True)
            sh_rows.extend(chunk_rows)
            time.sleep(sh_fetch_pause_seconds)
except Exception as ex:
    add_log_msg("Sihot interface reservation fetch exception:".format(ex), is_error=True, importance=4)
    print_exc()
'''

# process log file
add_log_msg("Processing log file " + sxml_log_file_name, importance=4)
try:
    with open(sxml_log_file_name, encoding='cp1252') as log_file:
        lines = log_file.readlines()
        op_code = last_line = ''
        for line_no, line_str in enumerate(lines):
            line_str = line_str[:-1]    # remove trailing \n
            if op_code:
                room_no = get_xml_element(line_str, 'RN')
                if not room_no:     # especially CI has mostly two lines (with RN in the second line)
                    last_line += line_str
                    continue
                elif last_line:
                    line_str = last_line + line_str
                cae.dprint("\nParse Log Entry:", time_stamp, op_code, line_str, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                check_occ_change(time_stamp, 'RI' if op_code == 'RM' else op_code, room_no, line_str[2:], line_no)
                room_no = get_xml_element(line_str, 'ORN')
                if room_no:
                    check_occ_change(time_stamp, 'RO', room_no, line_str[2:], line_no)
                op_code = last_line = ''
                continue

            time_stamp = get_log_time_stamp(line_str)
            if not time_stamp:
                continue
            tsc = time_stamp.date() if type(date_from) is datetime.date else time_stamp
            if tsc < date_from:
                continue
            elif tsc > date_till:
                break
            elif ': onReceive: ' in line_str and line_str[-2:] in ('CI', 'CO', 'RM'):
                op_code = line_str[-2:]

    add_log_msg("Running " + str(len(room_status)) + " discrepancy checks"
                + (" and data fixes" if correct_acumen else ""), importance=4)
    for occ_data in room_status:
        check_occ_discrepancies(occ_data)
except Exception as ex:
    add_log_msg("Processing interrupted by exception: {}".format(ex), is_error=True, importance=3)
    print_exc()

add_log_msg("Finished " + str(len(room_status)) + " discrepancy checks"
            + (" and data fixes" if correct_acumen else ""), importance=4)


send_err = send_err2 = None
if notification:
    subject = "Sihot Occupation Log Checker protocol [" + sys_id + "]"
    mail_body = str(len(log_items)) + " PROTOCOL ENTRIES:\n\n" + "\n\n".join(log_items)
    send_err = notification.send_notification(mail_body, subject=subject)
    if send_err:
        add_log_msg(subject + " send error: {}. mail-body={}".format(send_err, mail_body), is_error=True, importance=4)
    if warning_notification_emails and (notification_lines or log_errors):
        mail_body = str(len(notification_lines)) + " DISCREPANCIES:\n\n" + "\n\n".join(notification_lines) \
                    + "\n\n" + str(len(log_errors)) + " ERRORS:\n\n" + "\n\n".join(log_errors)
        subject = "Sihot Occupation Log Checker discrepancies/errors [" + sys_id + "]"
        send_err2 = notification.send_notification(mail_body, subject=subject, mail_to=warning_notification_emails)
        if send_err2:
            add_log_msg(subject + " send error: {}. mail-body={}".format(send_err2, mail_body), is_error=True,
                        importance=4)

if log_errors or send_err or send_err2:
    cae.shutdown(42)

cae.shutdown()
