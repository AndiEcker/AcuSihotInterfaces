"""
    SihotOccLogChecker is a tool for to check the SXML_ACUMEN log file (Sihot check-ins/-outs and room moves).

    0.1     first beta.
"""
import datetime
from traceback import print_exc

from ae_console_app import ConsoleApp, uprint, DEBUG_LEVEL_VERBOSE
from ae_db import OraDB
from ae_notification import add_notification_options, init_notification
from acif import ACU_DEF_USR, ACU_DEF_DSN

__version__ = '0.1'

USER_DATE_FORMAT = '%d-%m-%y %H:%M:%S'

startup_date = datetime.datetime.now()

cae = ConsoleApp(__version__, "Sihot SXML interface log file checks and optional Acumen room occupation status fixes")

cae.add_parameter('sxml_log_file_name', help="SXML Logfile name (and path)")

cae.add_option('dateFrom', "Date/time of first checked occupation", startup_date - datetime.timedelta(days=1), 'F')
cae.add_option('dateTill', "Date/time of last checked occupation", startup_date, 'T')
cae.add_option('correctAcumen', "Correct room occupation status (check-in/-out) in Acumen (0=No, 1=Yes)", False, 'A')

cae.add_option('acuUser', "User name of Acumen/Oracle system", ACU_DEF_USR, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", ACU_DEF_DSN, 'd')
'''
cae.add_option('shServerIP', "IP address of the Sihot interface server", 'localhost', 'i')
cae.add_option('shServerPort', "IP port of the Sihot WEB interface", 14777, 'w')
cae.add_option('shTimeout', "Timeout value for TCP/IP connections to Sihot", 1869.6, 't')
cae.add_option('shXmlEncoding', "Charset used for the Sihot xml data", SXML_DEF_ENCODING, 'e')
'''

add_notification_options(cae)


debug_level = cae.get_option('debugLevel')

sxml_log_file_name = cae.get_parameter('sxml_log_file_name')
uprint("SXML log file:", sxml_log_file_name)
date_from = cae.get_option('dateFrom')
date_till = cae.get_option('dateTill')
uprint("Date range including check-ins from", date_from.strftime(USER_DATE_FORMAT),
       'and till/before', date_till.strftime(USER_DATE_FORMAT))
ac_id = cae.get_option('acuDSN')
uprint('Acumen Usr/DSN:', cae.get_option('acuUser'), ac_id)
sys_id = ac_id
'''
sh_id = cae.get_option('shServerIP')
uprint("Server IP/Web-port:", sh_id, cae.get_option('shServerPort'))
uprint("TCP Timeout/XML Encoding:", cae.get_option('shTimeout'), cae.get_option('shXmlEncoding'))
sys_id = ac_id + ("/" + sh_id if sh_id else "")
'''

correct_acumen = cae.get_option('correctAcumen')
if correct_acumen:
    uprint("!!!!  Correcting Acumen Room Occupation Status")


def convert_to_date_options_type(datetime_value):
    return datetime_value if type(date_till) is datetime.datetime else datetime_value.date()


if date_from > date_till:
    uprint("Specified date range is invalid - dateFrom({}) has to be before dateTill({}).".format(date_from, date_till))
    cae.shutdown(18)
elif date_till > convert_to_date_options_type(startup_date):
    uprint("Future arrivals cannot be checked - corrected dateTill({}) will to {}."
           .format(date_till, convert_to_date_options_type(startup_date)))
    date_till = convert_to_date_options_type(startup_date)

max_days_diff = cae.get_config('maxDaysDiff', default_value=3.0)
if max_days_diff:
    uprint("Maximum number of days after/before expected arrival/departure:", max_days_diff)
days_check_in_before = min(cae.get_config('daysCheckInBefore', default_value=0.0), max_days_diff)
if days_check_in_before:
    uprint("Searching for check-ins done maximum {} days before the expected arrival date".format(days_check_in_before))
days_check_out_after = min(cae.get_config('daysCheckOutAfter', default_value=0.5), max_days_diff)   # 0.5 days == 12 hrs
if days_check_out_after:
    uprint("Searching for check-outs done maximum {} days after the expected departure".format(days_check_out_after))


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
'''

notification, warning_notification_emails = init_notification(cae, sys_id)


log_items = list()              # processing log entries
log_errors = list()             # processing errors
notification_lines = list()     # user discrepancies/warnings

ac_rows = list()                # acumen reservation occupation
sh_rows = list()                # sihot reservation requests
room_status = list()            # occupation room status changes (from SXML log file)
ora_db = None


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
    def _filter_ac_rows_by_req_borders(td):
        td_in_before = datetime.timedelta(days=days_check_in_before if days_check_in_before else 0)
        td_out_after = datetime.timedelta(days=days_check_out_after if days_check_out_after else 0)
        if oc in ('CI', 'RI'):
            return [_ for _ in ac_rows if _[3] - td_in_before <= dtt <= _[3] + td and _[5] == rn]
        else:  # oc in ('CO', 'RO')
            return [_ for _ in ac_rows if _[4] - td <= dtt <= _[4] + td_out_after and _[5] == rn]

    def _filter_ac_rows_by_aro():
        return [_ for _ in ac_rows if _[3] <= dtt <= _[4] + datetime.timedelta(hours=12) and _[5] == rn]

    dtt = dt if type(date_from) is datetime.datetime else datetime.datetime(dt.year, dt.month, dt.day)  # trunc datetime
    diff = datetime.timedelta(days=max_days_diff)
    sn = get_xml_element(sent_xml, 'SN')
    dts = dt.strftime(USER_DATE_FORMAT)
    dlv = debug_level >= DEBUG_LEVEL_VERBOSE
    rows = _filter_ac_rows_by_req_borders(diff)
    if len(rows) > 1:
        if dlv:
            add_log_msg("{}:{: >4}@{}#{: <6}  More than one ({}) matching Acumen reservations found; acu/xml: {}/{}"
                        .format(oc, rn, dts, ln, len(rows), rows, sent_xml))
        if sn:      # filter on surname (only given for oc==CI/RM currently)
            rows = [_ for _ in rows if _[2].upper() == sn.upper()]
            if dlv:
                add_log_msg("... {} after filtering by surname {}".format(len(rows), sn))
        while len(rows) != 1 and diff.days > 0:
            diff = datetime.timedelta(days=diff.days - 1)
            rows = _filter_ac_rows_by_req_borders(diff)
            if dlv:
                add_log_msg("... {} after filtering by decremented maxDiffDays to {}".format(len(rows), diff.days))
    elif len(rows) == 0 and oc not in ('CO', 'RO'):     # 1 ARO for several RUs - ignoring checkouts
        if dlv:
            add_log_msg("{}:{: >4}@{}#{: <6}  No Acumen reservation found; xml: {}".format(oc, rn, dts, ln, sent_xml))
        rows = _filter_ac_rows_by_aro()
        if dlv:
            add_log_msg("... {} after checking long ARO for several RUs: {}".format(len(rows), rows))
    if len(rows) > 1:
        add_log_msg("{}:{: >4}@{}#{: <6}  {}more than one ({}) Acumen reservations found: {}"
                    .format(oc, rn, dts, ln, "... still " if dlv else "", len(rows), rows), is_error=True)
    elif len(rows) == 1:
        r = rows[0]
        od = OccData(oc, dt, rn, r[0], r[6], r[3], r[4], r[1] + "/" + r[2] + "=" + r[9] + "#" + str(r[10]))
        room_status.append(od)
        add_log_msg("{}:{: >4}@{}#{: <6}  found Acumen reservation; Occupation/Acumen{} data: {}/{}{}"
                    .format(oc, rn, dts, ln, "/Xml" if dlv else "", od, rows[0], "/" + sent_xml if dlv else ""))
    elif dlv:
        add_log_msg("{}:{: >4}@{}#{: <6}  {}no Acumen reservation found"
                    .format(oc, rn, dts, ln, "... still " if oc not in ('CO', 'RO') else ""))


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
    if cols and 'ARO_TIMEIN' in cols:
        cols['ARO_RECD_KEY'] = cols['ARO_TIMEIN']
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
    return bool(cols)


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
fixable = 0
try:
    with open(sxml_log_file_name, encoding='cp1252') as log_file:
        lines = log_file.readlines()
        op_code = last_line = ''
        added_lines = 0
        last_ts = datetime.datetime.now()
        biggest_gap = datetime.timedelta(days=0)
        first_log_date = None
        for line_no, line_str in enumerate(lines):
            line_str = line_str[:-1]    # remove trailing \n
            time_stamp = get_log_time_stamp(line_str)
            if op_code:
                room_no = get_xml_element(line_str, 'RN')
                if not room_no:     # especially CI has mostly two lines (with RN in the second line)
                    last_line += line_str
                    added_lines += 1
                    continue
                elif last_line:
                    line_str = last_line + line_str
                    line_no -= added_lines
                cae.dprint("\nParse Log Entry:", time_stamp, op_code, line_str, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                check_occ_change(time_stamp, 'RI' if op_code == 'RM' else op_code, room_no, line_str[2:], line_no)
                room_no = get_xml_element(line_str, 'ORN')
                if room_no:
                    check_occ_change(time_stamp, 'RO', room_no, line_str[2:], line_no)
                op_code = last_line = ''
                added_lines = 0
                continue

            if not time_stamp:
                cae.dprint("Empty timestamp in log line, OC={}, line={}".format(op_code, line_str),
                           minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                continue
            if not first_log_date:
                first_log_date = time_stamp
            if time_stamp - last_ts > biggest_gap:
                biggest_gap = time_stamp - last_ts
            last_ts = time_stamp
            tsc = convert_to_date_options_type(time_stamp)
            if tsc < date_from:
                continue
            elif tsc > date_till:
                break
            elif ': onReceive: ' in line_str and line_str[-2:] in ('CI', 'CO', 'RM'):
                op_code = line_str[-2:]
        if convert_to_date_options_type(first_log_date) > date_from:
            cae.dprint("Log file gap between specified begin date {} and {}".format(date_from, first_log_date))
        if convert_to_date_options_type(last_ts) < date_till:
            cae.dprint("Log file gap/cut from end of log file {} till specified end date {}".format(last_ts, date_till))
        cae.dprint("Biggest gap between log entries in specified log file:", biggest_gap)

    add_log_msg("Running " + str(len(room_status)) + " discrepancy checks"
                + (" and data fixes" if correct_acumen else ""), importance=4)
    fixed_aro_codes = list()
    for occ_data in reversed(room_status):  # process reversed to detect&skip multiple occupation changes on same ARO
        if occ_data.aro_code in fixed_aro_codes:
            add_log_msg("Occupation got already fixed; Acumen data: {}".format(occ_data))
            continue
        if check_occ_discrepancies(occ_data):
            fixed_aro_codes.append(occ_data.aro_code)
            fixable += 1

except Exception as ex:
    add_log_msg("Processing interrupted by exception: {}".format(ex), is_error=True, importance=3)
    print_exc()

if ora_db:
    ora_db.close()
add_log_msg("Finished " + str(len(room_status)) + " discrepancy checks"
            + (" and data fixes" if correct_acumen else "") + " - number of fixable AROs=" + str(fixable), importance=4)


send_err = send_err2 = None
if notification:
    subject = "Sihot Occupation Log Checker protocol"
    param_desc = ("FIXING" if correct_acumen else "CHECKING") + " OCC CHANGES BETWEEN " \
        + date_from.strftime(USER_DATE_FORMAT) + " AND " + date_till.strftime(USER_DATE_FORMAT)
    mail_body = str(len(log_items)) + " PROTOCOL ENTRIES WHILE " + param_desc + ":\n\n" + "\n\n".join(log_items)
    send_err = notification.send_notification(mail_body, subject=subject, body_style='plain')
    if send_err:
        add_log_msg(subject + " send error: {}. mail-body={}".format(send_err, mail_body), is_error=True, importance=4)
    if warning_notification_emails and (notification_lines or log_errors):
        subject = "Sihot Occupation Log Checker discrepancies/errors"
        mail_body = str(len(notification_lines)) + " DISCREPANCIES WHILE " + param_desc + ":\n\n" \
            + "\n\n".join(notification_lines) \
            + "\n\n" + str(len(log_errors)) + " ERRORS:\n\n" + "\n\n".join(log_errors)
        send_err2 = notification.send_notification(mail_body, subject=subject, mail_to=warning_notification_emails)
        if send_err2:
            add_log_msg(subject + " send error: {}. mail-body={}".format(send_err2, mail_body), is_error=True,
                        importance=4)

if log_errors or send_err or send_err2:
    cae.shutdown(42)

cae.shutdown()
