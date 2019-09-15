"""
    SihotOccLogChecker is a tool for to check the SXML_ACUMEN/_ASSCACHE log file (Sihot check-ins/-outs and room moves).

    0.1     first beta.
    0.2     added AssCache as second fixable system.
"""
import datetime
from traceback import format_exc

from ae.core import DEBUG_LEVEL_VERBOSE
from ae.console_app import ConsoleApp
from ae_db.db import OraDB, PostgresDB
from ass_sys_data import add_ass_options, init_ass_data

__version__ = '0.2'

USER_DATE_FORMAT = '%d-%m-%y %H:%M:%S'

startup_date = datetime.datetime.now()

cae = ConsoleApp("Sihot SXML interface log file checks and Acumen/AssCache occupation status fixes")

cae.add_argument('sxml_log_file_name', help="SXML Logfile name (and path, e.g. SXML_ACUMEN.log or SXML_ASSCACHE.log)")

cae.add_opt('dateFrom', "Date/time of first checked occupation", startup_date - datetime.timedelta(days=1), 'F')
cae.add_opt('dateTill', "Date/time of last checked occupation", startup_date, 'T')
cae.add_opt('correctSystem', "Correct room occupation status (check-in/-out) in (Acu=Acumen, Ass=AssCache)", '', 'A')

ass_options = add_ass_options(cae)


debug_level = cae.get_opt('debugLevel')

sxml_log_file_name = cae.get_argument('sxml_log_file_name')
cae.po("SXML log file:", sxml_log_file_name)
date_from = cae.get_opt('dateFrom')
date_till = cae.get_opt('dateTill')
cae.po("Date range including check-ins from", date_from.strftime(USER_DATE_FORMAT),
           "and till/before", date_till.strftime(USER_DATE_FORMAT))
correct_system = cae.get_opt('correctSystem')
if correct_system:
    cae.po("!!!!  Correcting {} Room Occupation Status".format(correct_system))


def convert_to_date_options_type(datetime_value):
    return datetime_value if type(date_till) is datetime.datetime else datetime_value.date()


if date_from > date_till:
    cae.po("Specified date range is invalid - dateFrom({}) has to be before dateTill({})."
           .format(date_from, date_till))
    cae.shutdown(18)
elif date_till > convert_to_date_options_type(startup_date):
    cae.po("Future arrivals cannot be checked - corrected dateTill({}) will to {}."
           .format(date_till, convert_to_date_options_type(startup_date)))
    date_till = convert_to_date_options_type(startup_date)

max_days_diff = cae.get_var('maxDaysDiff', default_value=3.0)
if max_days_diff:
    cae.po("Maximum number of days after/before expected arrival/departure:", max_days_diff)
days_check_in_before = min(cae.get_var('daysCheckInBefore', default_value=0.0), max_days_diff)
if days_check_in_before:
    cae.po("Searching for check-ins done maximum {} days before the expected arrival date"
           .format(days_check_in_before))
days_check_out_after = min(cae.get_var('daysCheckOutAfter', default_value=0.5), max_days_diff)   # 0.5 days == 12 hrs
if days_check_out_after:
    cae.po("Searching check-outs done maximum {} days after the expected departure".format(days_check_out_after))


'''
# fetch given date range in chunks for to prevent timeouts and Sihot server blocking issues
sh_fetch_max_days = min(max(1, cae.get_var('shFetchMaxDays', default_value=7)), 31)
sh_fetch_pause_seconds = cae.get_var('shFetchPauseSeconds', default_value=1)
po("Sihot Data Fetch-maximum days (1..31, recommended 1..7)", sh_fetch_max_days,
       " and -pause in seconds between fetches", sh_fetch_pause_seconds)
search_flags = cae.get_var('ResSearchFlags', default_value='ALL-HOTELS')
po("Search flags:", search_flags)
search_scope = cae.get_var('ResSearchScope', default_value='NOORDERER;NORATES;NOPERSTYPES')
po("Search scope:", search_scope)
'''

ass_data = init_ass_data(cae, ass_options)
notification = ass_data['notification']
notification_warning_emails = ass_data['warningEmailAddresses']


op_descriptions = dict(CI="Check-In", CO="Check-Out", RI="Room-Move-Transfer-In", RO="Room-Move-Transfer-Out")
log_items = list()              # processing log entries
log_errors = list()             # processing errors
notification_lines = list()     # user discrepancies/warnings

db_rows = list()                # database reservation occupation
# sh_rows = list()                # sihot reservation requests
room_status = list()            # occupation room status changes (from SXML log file)
sys_db = None


class OccData:
    def __init__(self, op_code, time_stamp, room_no, res_id, res_status, res_arrival, res_departure,
                 res_time_in, res_time_out,
                 res_desc='', res_hotel_id='', res_no='', sub_no=''):
        super(OccData, self).__init__()
        self.op_code = op_code
        self.time_stamp = time_stamp
        self.room_no = room_no
        self.res_id = res_id
        self.res_status = res_status
        self.res_arrival = res_arrival
        self.res_departure = res_departure
        self.res_time_in = res_time_in
        self.res_time_out = res_time_out
        self.res_desc = res_desc
        self.res_hotel_id = res_hotel_id
        self.res_no = res_no
        self.sub_no = sub_no

    def __repr__(self):
        return "OccData(" + repr(self.op_code) + ", " + repr(self.time_stamp) + ", " + repr(self.room_no) \
               + ", " + repr(self.res_id) + ", " + repr(self.res_status) \
               + ", " + repr(self.res_arrival) + ", " + repr(self.res_departure) \
               + ", " + repr(self.res_time_in) + ", " + repr(self.res_time_out) \
               + ", " + repr(self.res_desc)  \
               + (", " + repr(self.res_no) + '/' + repr(self.sub_no) + '@' + repr(self.res_hotel_id)
                  if correct_system == 'Ass' else '')  \
               + ")"


def add_log_msg(msg, is_error=False, importance=2):
    global log_errors, log_items
    assert 0 < importance < 5
    if is_error:
        log_errors.append(msg)
    msg = " " * (4 - importance) + ("*" if is_error else "#") * importance + "  " + msg
    log_items.append(msg)
    cae.po(msg)


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


def check_occ_change(dt, op_code, room_no, sent_xml, ln):
    def _filter_rows_by_req_borders(td):
        td_in_before = datetime.timedelta(days=days_check_in_before if days_check_in_before else 0)
        td_out_after = datetime.timedelta(days=days_check_out_after if days_check_out_after else 0)
        if op_code in ('CI', 'RI'):
            return [_ for _ in db_rows if _[3] - td_in_before <= dtt <= _[3] + td and _[5] == room_no]
        else:  # op_code in ('CO', 'RO')
            return [_ for _ in db_rows if _[4] - td <= dtt <= _[4] + td_out_after and _[5] == room_no]

    def _filter_rows_by_req_dates():
        return [_ for _ in db_rows if _[3] <= dtt <= _[4] + datetime.timedelta(hours=12) and _[5] == room_no]

    dtt = dt if type(date_from) is datetime.datetime else datetime.datetime(dt.year, dt.month, dt.day)  # trunc datetime
    diff = datetime.timedelta(days=max_days_diff)
    dts = dt.strftime(USER_DATE_FORMAT)
    dlv = debug_level >= DEBUG_LEVEL_VERBOSE

    if correct_system == 'Acu':
        rows = _filter_rows_by_req_borders(diff)
    else:
        ho_no = get_xml_element(sent_xml, 'HN')
        res_no = get_xml_element(sent_xml, 'RES-NR')
        sub_no = get_xml_element(sent_xml, 'SUB-NR')
        if op_code == 'RO':
            old_sub_no = get_xml_element(sent_xml, 'OSUB-NR')
            if old_sub_no:
                sub_no = old_sub_no
        rows = [_ for _ in db_rows if _[11] == ho_no and _[12] == res_no and _[13] == sub_no]
    if len(rows) > 1:
        if dlv:
            add_log_msg("{}:{: >4}@{}#{: <6}  More than one ({}) matching {} reservations found; db/xml: {}/{}"
                        .format(op_code, room_no, dts, ln, len(rows), correct_system, rows, sent_xml))
        sur_name = get_xml_element(sent_xml, 'SN')
        if sur_name:      # filter on surname (only given for op_code==CI/RM currently)
            rows = [_ for _ in rows if _[2].upper().endswith(sur_name.upper())]
            if dlv:
                add_log_msg("... {} after filtering by surname {}".format(len(rows), sur_name))
        while len(rows) != 1 and diff.days > 0:
            diff = datetime.timedelta(days=diff.days - 1)
            rows = _filter_rows_by_req_borders(diff)
            if dlv:
                add_log_msg("... {} after filtering by decremented maxDiffDays to {}".format(len(rows), diff.days))
    elif len(rows) == 0 and op_code not in ('CO', 'RO'):     # 1 ARO for several RUs - ignoring checkouts
        if dlv:
            add_log_msg("{}:{: >4}@{}#{: <6}  No reservation found; xml: {}"
                        .format(op_code, room_no, dts, ln, sent_xml))
        rows = _filter_rows_by_req_dates()
        if dlv:
            add_log_msg("... {} after checking long reservation for several chunks: {}".format(len(rows), rows))
    if len(rows) > 1:
        add_log_msg("{}:{: >4}@{}#{: <6}  {}more than one ({}) {} reservations found: {}"
                    .format(op_code, room_no, dts, ln, "... still " if dlv else "", len(rows), correct_system, rows),
                    is_error=True)
    elif len(rows) == 1:
        r = rows[0]
        od = OccData(op_code, dt, room_no, r[0], r[6], r[3], r[4], r[7], r[8],
                     (r[12] + "/" + str(r[13]) + '@' + str(r[11]) + ':' if len(r) > 11 and r[12] else '')
                     + str(r[1]) + "/" + str(r[2]) + "=" + str(r[9]) + "#" + str(r[10]),
                     r[11] if len(r) > 11 else '', r[12] if len(r) > 11 else '', r[13] if len(r) > 11 else '')
        room_status.append(od)
        add_log_msg("{}:{: >4}@{}#{: <6}  found {} reservations; Occupation/Db{} data: {}/{}{}"
                    .format(op_code, room_no, dts, ln, correct_system, "/Xml" if dlv else "", od, rows[0],
                            "/" + sent_xml if dlv else ""))
    elif dlv:
        add_log_msg("{}:{: >4}@{}#{: <6}  {}no {} reservation found"
                    .format(op_code, room_no, dts, ln, "... still " if op_code not in ('CO', 'RO') else "",
                            correct_system))


def fix_discrepancies(od):
    if correct_system == 'Acu':
        return fix_acu_discrepancies(od)
    else:
        return fix_ass_discrepancies(od)


def fix_acu_discrepancies(od):
    wrn = list()
    cols = None         # T_ARO columns to be updated
    msg = op_descriptions[od.op_code]
    if od.op_code in ('CI', 'RI'):
        if od.res_status not in (300, 330):
            if od.res_status in (320, 390):
                wrn.append("already checked-out - status={}".format(od.res_status))
            else:
                cols = dict(ARO_STATUS=300 if od.op_code == 'CI' else 330, ARO_TIMEIN=od.time_stamp, ARO_TIMEOUT=None)
    else:       # if od.op_code in ('CO', 'RO'):
        if od.res_status not in (320, 390):
            if od.res_status in (300, 330):
                cols = dict(ARO_STATUS=390, ARO_TIMEOUT=od.time_stamp)
            else:
                cols = dict(ARO_STATUS=390 if od.op_code == 'CO' else 320, ARO_TIMEIN=od.res_arrival,
                            ARO_TIMEOUT=od.time_stamp)
                wrn.append("TimeIn missing too - status={}".format(od.res_status))
    if cols and 'ARO_TIMEIN' in cols:
        cols['ARO_RECD_KEY'] = cols['ARO_TIMEIN']
    if cols and debug_level >= DEBUG_LEVEL_VERBOSE:
        msg += " FIX=" + str(cols)
    if cols or wrn:
        if "#None" in od.res_desc:
            wrn.append("No GdsNo")
        elif "," in od.res_desc[od.res_desc.find("#"):]:
            wrn.append("Multiple GdsNos")
        if wrn:
            msg += " (" + ", ".join(wrn) + ")"
        notification_add_line("Missing {}: {}".format(msg, od))
    if cols and correct_system:
        err = sys_db.update('T_ARO', cols, {"ARO_CODE": od.res_id})
        if err:
            notification_add_line("Error {} in correcting missing {}: {}".format(err, msg, od), is_error=True)
            sys_db.rollback()
        else:
            notification_add_line("Successfully fixed missing {}: {}".format(msg, od))
            sys_db.commit()
    return bool(cols)


def fix_ass_discrepancies(od):
    wrn = list()
    cols = None         # ass_cache.res_groups columns to be updated
    msg = op_descriptions[od.op_code]
    if od.op_code in ('CI', 'RI'):
        if od.res_time_in is None:
            if od.res_time_out is not None:
                wrn.append("already checked-out at {}".format(od.res_time_out))
            else:
                cols = dict(rgr_time_in=od.time_stamp, rgr_time_out=None)
    else:       # if od.op_code in ('CO', 'RO'):
        if od.res_time_out is None:
            if od.res_time_in is not None:
                cols = dict(rgr_time_out=od.time_stamp)
            else:
                cols = dict(rgr_time_in=od.res_arrival, rgr_time_out=od.time_stamp)
                wrn.append("TimeIn missing too - setting to arrival date ({})".format(od.res_arrival))
    if cols and debug_level >= DEBUG_LEVEL_VERBOSE:
        msg += " FIX=" + str(cols)
    if cols or wrn:
        if "#None" in od.res_desc:
            wrn.append("No GdsNo")
        elif "," in od.res_desc[od.res_desc.find("#"):]:
            wrn.append("Multiple GdsNos")
        if wrn:
            msg += " (" + ", ".join(wrn) + ")"
        notification_add_line("Missing {}: {}".format(msg, od))
    if cols and correct_system:
        cols['rgr_room_last_change'] = od.time_stamp
        cols['rgr_room_id'] = od.room_no
        err = sys_db.update('res_groups', cols, {"rgr_pk": od.res_id})
        if err:
            notification_add_line("Error {} in correcting missing {}: {}".format(err, msg, od), is_error=True)
            sys_db.rollback()
        else:
            notification_add_line("Successfully fixed missing {}: {}".format(msg, od))
            sys_db.commit()
    return bool(cols)


add_log_msg("Fetching reservation/occupation data from {} system".format(correct_system), importance=4)
try:
    if correct_system == 'Acu':
        sys_db = OraDB(dict(User=cae.get_opt('acuUser'), Password=cae.get_opt('acuPassword'),
                            DSN=cae.get_opt('acuDSN')),
                       app_name=cae.app_name, debug_level=cae.get_opt('debugLevel'))
        err_msg = sys_db.connect()
        if not err_msg:
            err_msg = sys_db.select('T_ARO',
                                    ['ARO_CODE', 'ARO_CDREF', 'F_OWNER_CONCAT(ARO_CDREF)',
                                     'ARO_EXP_ARRIVE', 'ARO_EXP_DEPART',
                                     "case when F_RESORT(ARO_APREF) = 'PBC' and length(ARO_APREF) = 3 then"
                                     " '0' end || ARO_APREF as ARO_APREF",
                                     'ARO_STATUS', 'ARO_TIMEIN', 'ARO_TIMEOUT', 'ARO_ROREF',
                                     "(select f_stragg(RU_CODE) from T_RU where RU_RHREF = ARO_RHREF"
                                     " and RU_STATUS <> 120"
                                     " and RU_FROM_DATE < least(ARO_EXP_DEPART, trunc(:till) + :days)"
                                     " and RU_FROM_DATE + RU_DAYS > greatest(ARO_EXP_ARRIVE, trunc(:beg) - :days))"
                                     " as GDS_NOS"],
                                    where_group_order="ARO_EXP_ARRIVE < trunc(:till) + :days"
                                    " and ARO_EXP_DEPART > trunc(:beg) - :days"
                                    " and ARO_STATUS <> 120 and F_RESORT(ARO_APREF)"
                                    " in (select LU_ID from T_LU where LU_CLASS = 'SIHOT_HOTELS' and LU_ACTIVE = 1)"
                                    " order by ARO_EXP_ARRIVE desc",  # order to have old room last for RM
                                    bind_vars=dict(beg=date_from, till=date_till, days=max_days_diff))
    else:
        sys_db = PostgresDB(dict(User=cae.get_opt('assUser'), Password=cae.get_opt('assPassword'),
                                 DSN=cae.get_opt('assDSN'), SslArgs=cae.get_var('assSslArgs')),
                            app_name=cae.app_name,
                            debug_level=cae.get_opt('debugLevel'))
        err_msg = sys_db.connect()
        if not err_msg:
            err_msg = sys_db.select('res_groups LEFT OUTER JOIN clients ON rgr_order_cl_fk = cl_pk',
                                    ['rgr_pk', 'cl_ac_id', 'cl_surname', 'cl_firstname',
                                     'rgr_arrival::timestamp', 'rgr_departure::timestamp', "rgr_room_id",
                                     'rgr_status', 'rgr_time_in', 'rgr_time_out', 'rgr_mkt_segment', "rgr_gds_no",
                                     'rgr_ho_fk', 'rgr_res_id', 'rgr_sub_id'],
                                    where_group_order="rgr_arrival < date(:till) + integer ':days'"
                                    " and rgr_departure > date(:beg) - integer ':days'"
                                    " and rgr_status <> 'S'"
                                    " order by rgr_arrival desc",  # order to have old room last for RM
                                    bind_vars=dict(beg=date_from, till=date_till, days=int(max_days_diff)))
    if err_msg:
        add_log_msg(err_msg, is_error=True, importance=3)
    else:
        db_rows = sys_db.fetch_all()
except Exception as ex:
    add_log_msg("{} database reservation fetch exception: {}\n{}".format(correct_system, ex, format_exc()),
                is_error=True, importance=3)

'''
add_log_msg("Fetching reservations from Sihot", importance=4)
try:
    res_search = ResSearch(cae)
    # the from/to date range filter of WEB ResSearch is filtering the arrival date only (not date range/departure)
    # adding flag ;WITH-PERSONS results in getting the whole reservation duplicated for each PAX in rooming list
    # adding scope NOORDERER prevents to include/use LANG/COUNTRY/NAME/EMAIL of orderer
    for chunk_beg, chunk_end in date_range_chunks():
        chunk_rows = res_search.search_res(from_date=chunk_beg, to_date=chunk_end, flags=search_flags, 
                                           scope=search_scope)
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
        oc = last_line = ''
        added_lines = 0
        last_ts = datetime.datetime.now()
        biggest_gap = datetime.timedelta(days=0)
        first_log_date = ts = None
        for line_no, line_str in enumerate(lines):
            line_str = line_str[:-1]    # remove trailing \n
            if oc:
                room = get_xml_element(line_str, 'RN')
                if not room or not get_xml_element(line_str, 'SUB-NR'):
                    # especially CI has mostly multiple lines (with RN/SUB-NR in the last line)
                    last_line += line_str
                    added_lines += 1
                    continue
                elif last_line:
                    line_str = last_line + line_str
                    line_no -= added_lines
                cae.dpo("\nParse Log Entry:", ts, oc, line_str)
                check_occ_change(ts, 'RI' if oc == 'RM' else oc, room, line_str[2:], line_no)
                room = get_xml_element(line_str, 'ORN')
                if room:
                    check_occ_change(ts, 'RO', room, line_str[2:], line_no)
                oc = last_line = ''
                added_lines = 0
                continue

            ts = get_log_time_stamp(line_str)
            if not ts:
                cae.dpo("Empty timestamp in log line, OC={}, line={}".format(oc, line_str))
                continue
            if not first_log_date:
                first_log_date = ts
            if ts - last_ts > biggest_gap:
                biggest_gap = ts - last_ts
            last_ts = ts
            tsc = convert_to_date_options_type(ts)
            if tsc < date_from:
                continue
            elif tsc > date_till:
                break
            elif ': onReceive: ' in line_str and line_str[-2:] in ('CI', 'CO', 'RM'):
                oc = line_str[-2:]
        if convert_to_date_options_type(first_log_date) > date_from:
            cae.dpo("Log file gap between specified begin date {} and {}".format(date_from, first_log_date))
        if convert_to_date_options_type(last_ts) < date_till:
            cae.dpo("Log file gap/cut from end of log file {} till specified end date {}".format(last_ts, date_till))
        cae.dpo("Biggest gap between log entries in specified log file:", biggest_gap)

    add_log_msg("Running " + str(len(room_status)) + " discrepancy checks"
                + (" and {} data fixes".format(correct_system) if correct_system else ""), importance=4)
    fixed_res_ids = list()
    for occ_data in reversed(room_status):  # process reversed to detect&skip multiple occupation changes on same res
        if occ_data.res_id in fixed_res_ids:
            add_log_msg("Occupation got already fixed; {} data: {}".format(correct_system, occ_data))
            continue
        if fix_discrepancies(occ_data):
            fixed_res_ids.append(occ_data.res_id)
            fixable += 1
        else:
            add_log_msg("Occupation not fixable; {} data: {}".format(correct_system, occ_data),
                        is_error=True, importance=3)

except Exception as ex:
    add_log_msg("Processing interrupted by exception: {}\n{}".format(ex, format_exc()), is_error=True, importance=3)

if sys_db:
    sys_db.close()
add_log_msg("Finished " + str(len(room_status)) + " discrepancy checks"
            + (" and {} data fixes".format(correct_system) if correct_system else "")
            + " - number of fixable records=" + str(fixable), importance=4)


send_err = send_err2 = None
if notification:
    subject = "Sihot Occupation Log Checker protocol"
    param_desc = ("FIXING {}".format(correct_system) if correct_system else "CHECKING") \
        + " OCC CHANGES BETWEEN " \
        + date_from.strftime(USER_DATE_FORMAT) + " AND " + date_till.strftime(USER_DATE_FORMAT)
    mail_body = str(len(log_items)) + " PROTOCOL ENTRIES WHILE " + param_desc + ":\n\n" + "\n\n".join(log_items)
    send_err = notification.send_notification(mail_body, subject=subject, body_style='plain')
    if send_err:
        add_log_msg(subject + " send error: {}. mail-body={}".format(send_err, mail_body), is_error=True, importance=4)
    if notification_warning_emails and (notification_lines or log_errors):
        subject = "Sihot Occupation Log Checker discrepancies/errors"
        mail_body = str(len(notification_lines)) + " DISCREPANCIES WHILE " + param_desc + ":\n\n" \
            + "\n\n".join(notification_lines) \
            + "\n\n" + str(len(log_errors)) + " ERRORS:\n\n" + "\n\n".join(log_errors)
        send_err2 = notification.send_notification(mail_body, subject=subject, mail_to=notification_warning_emails)
        if send_err2:
            add_log_msg(subject + " send error: {}. mail-body={}".format(send_err2, mail_body), is_error=True,
                        importance=4)

if log_errors or send_err or send_err2:
    cae.shutdown(42)

cae.shutdown()
