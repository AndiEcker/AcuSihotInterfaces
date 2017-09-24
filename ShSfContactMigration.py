"""
    ShSfContactMigration is a tool for to migrate every Sihot rental guest with valid contact data as a Contact
    object into the Salesforce system.

    0.1     first beta.
"""
import datetime
import time
import re
from traceback import print_exc
import pprint

from copy import deepcopy

from ae_console_app import ConsoleApp, uprint, DEBUG_LEVEL_VERBOSE
from sxmlif import ResSearch, SXML_DEF_ENCODING, PARSE_ONLY_TAG_PREFIX
from sfif import prepare_connection, CONTACT_REC_TYPE_RENTALS, correct_email, correct_phone
from ae_notification import Notification

__version__ = '0.1'

LINE_SEPARATOR = '\n'
SIHOT_PROVIDES_CHECKOUT_TIME = False  # currently there is no real checkout time available in Sihot
SIHOT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S' if SIHOT_PROVIDES_CHECKOUT_TIME else '%Y-%m-%d'

startup_date = datetime.datetime.now() if SIHOT_PROVIDES_CHECKOUT_TIME else datetime.date.today()
mail_re = re.compile('[a-zA-Z0-9._%-]+@[a-zA-Z0-9._%-]+\.[a-zA-Z]{2,4}$')

PP_DEF_WIDTH = 120
pretty_print = pprint.PrettyPrinter(indent=6, width=PP_DEF_WIDTH, depth=9)

cae = ConsoleApp(__version__, "Migrate contactable guests from Sihot to Salesforce")
cae.add_option('serverIP', "IP address of the Sihot interface server", 'localhost', 'i')
cae.add_option('serverPort', "IP port of the Sihot WEB interface", 14777, 'w')
cae.add_option('timeout', "Timeout value for TCP/IP connections to Sihot", 1869.6, 't')
cae.add_option('xmlEncoding', "Charset used for the Sihot xml data", SXML_DEF_ENCODING, 'e')

cae.add_option('dateFrom', "Date" + ("/time" if SIHOT_PROVIDES_CHECKOUT_TIME else "") +
               " of first check-in to be migrated", startup_date - datetime.timedelta(days=1), 'F')
cae.add_option('dateTill', "Date" + ("/time" if SIHOT_PROVIDES_CHECKOUT_TIME else "") +
               " of last check-in to be migrated", startup_date - datetime.timedelta(days=1), 'T')

cae.add_option('sfUser', "Salesforce account user name", '', 'y')
cae.add_option('sfPassword', "Salesforce account user password", '', 'a')
cae.add_option('sfToken', "Salesforce account token string", '', 'o')
cae.add_option('sfClientId', "Salesforce client/application name/id", cae.app_name(), 'C')
cae.add_option('sfIsSandbox', "Use Salesforce sandbox (instead of production)", True, 's')

cae.add_option('smtpServerUri', "SMTP notification server account URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP sender/from address", '', 'f')
cae.add_option('smtpTo', "List/Expression of SMTP receiver/to addresses", list(), 'r')

cae.add_option('warningsMailToAddr', "Warnings SMTP receiver/to addresses (if differs from smtpTo)", list(), 'v')

debug_level = cae.get_option('debugLevel')

uprint("Server IP/Web-port:", cae.get_option('serverIP'), cae.get_option('serverPort'))
uprint("TCP Timeout/XML Encoding:", cae.get_option('timeout'), cae.get_option('xmlEncoding'))

date_from = cae.get_option('dateFrom')
date_till = cae.get_option('dateTill')
uprint("Date range including check-ins from", date_from.strftime(SIHOT_DATE_FORMAT),
       'and till/before', date_till.strftime(SIHOT_DATE_FORMAT))
if date_from > date_till:
    uprint("Specified date range is invalid - dateFrom({}) has to be before dateTill({}).".format(date_from, date_till))
    cae.shutdown(18)
elif date_till > startup_date:
    uprint("Future arrivals cannot be migrated - dateTill({}) has to be before {}.".format(date_till, startup_date))
    cae.shutdown(19)
# fetch given date range in chunks for to prevent timeouts and Sihot server blocking issues
sh_fetch_max_days = min(max(1, cae.get_config('shFetchMaxDays', default_value=7)), 31)
sh_fetch_pause_seconds = cae.get_config('shFetchPauseSeconds', default_value=1)
uprint("Sihot Data Fetch-maximum days (1..31, recommended 1..7)", sh_fetch_max_days,
       " and -pause in seconds between fetches", sh_fetch_pause_seconds)

search_flags = cae.get_config('ResSearchFlags', default_value='ALL-HOTELS')
uprint("Search flags:", search_flags)
search_scope = cae.get_config('ResSearchScope', default_value='NOORDERER;NORATES;NOPERSTYPES')
uprint("Search scope:", search_scope)

allowed_mkt_src = cae.get_config('MarketSources', default_value=list())
uprint("Allowed Market Sources:", allowed_mkt_src)

invalid_email_fragments = cae.get_config('InvalidEmailFragments', default_value=list())
uprint("Invalid email fragments:", invalid_email_fragments)
restrict_to_valid_emails = cae.get_config('restrictToValidEmails', default_value=True)
if restrict_to_valid_emails:
    uprint("      Only sending valid email addresses")
default_email_address = cae.get_config('defaultEmailAddress', default_value='ClientHasNoEmail@signallia.com')
# html font is not working in Outlook: <font face="Courier New, Courier, monospace"> ... </font>
msf_beg = cae.get_config('monoSpacedFontBegin', default_value='<pre>')
msf_end = cae.get_config('monoSpacedFontEnd', default_value='</pre>')

ignore_case_fields = cae.get_config('ignoreCaseFields', default_value=['Email'])
changeable_contact_fields = cae.get_config('changeableContactFields', default_value=['Email'])

sf_conn, sf_sandbox = prepare_connection(cae)
if not sf_conn:
    uprint("Salesforce account connection could not be established - please check your account data and credentials")
    cae.shutdown(20)

notification = warning_notification_emails = None
if cae.get_option('smtpServerUri') and cae.get_option('smtpFrom') and cae.get_option('smtpTo'):
    notification = Notification(smtp_server_uri=cae.get_option('smtpServerUri'),
                                mail_from=cae.get_option('smtpFrom'),
                                mail_to=cae.get_option('smtpTo'),
                                used_system=cae.get_option('serverIP') + '/Salesforce ' + ("sandbox" if sf_sandbox
                                                                                           else "production"),
                                debug_level=cae.get_option('debugLevel'))
    uprint("SMTP Uri/From/To:", cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))
    warning_notification_emails = cae.get_option('warningsMailToAddr')
    if warning_notification_emails:
        uprint("Warnings SMTP receiver address(es):", warning_notification_emails)

ELEM_MISSING = "(missing)"
ELEM_EMPTY = "(empty)"

ADD_INFO_PREFIX = '+'
AI_SH_RES_ID = ADD_INFO_PREFIX + 'res_id'
AI_SH_RL_ID = ADD_INFO_PREFIX + 'sh_rl_id'
AI_WARNINGS = ADD_INFO_PREFIX + 'warnings'
AI_SCORE = ADD_INFO_PREFIX + 'score'
AI_SF_ID = ADD_INFO_PREFIX + 'sf_id'
AI_SF_CURR_DATA = ADD_INFO_PREFIX + 'sf_curr_data'

log_errors = list()
log_items = list()              # warnings on Sihot data
ups_warnings = list()           # warnings on Salesforce upserts
notification_lines = list()     # user notifications


def add_log_msg(msg, is_error=False):
    global log_errors, log_items
    if is_error:
        log_errors.append(msg)
    msg = ("  **  " if is_error else "  ##  ") + msg
    log_items.append(msg)
    uprint(msg)


def notification_add_line(msg, is_error=False):
    global notification_lines
    add_log_msg(msg, is_error=is_error)
    notification_lines.append(msg)


def strip_add_info_keys(sfd):
    return [_ for _ in sfd.keys() if not _.startswith(ADD_INFO_PREFIX)]


def strip_add_info_from_sf_data(sfd, strip_populated_sf_fields=False, record_type_id=None):
    sfs = dict()
    sfc = sfd[AI_SF_CURR_DATA] if strip_populated_sf_fields else None
    sf_has_valid_email = (sfc and sfc['Email'] and email_is_valid(sfc['Email']))
    sid = sfd[AI_SF_ID] or sfd[AI_SH_RL_ID]

    for key in strip_add_info_keys(sfd):
        # tweak sending key and value
        if key == 'RecordType.DeveloperName':
            send_key = 'RecordTypeId'
            send_val = record_type_id
        else:
            send_key = key
            send_val = sfd.get(key, "")
        # check if sihot field data (sfd) has to be included into sfs (send to Salesforce or displayed in log)
        if sfc and key in sfc and sfc[key] and (key not in changeable_contact_fields
                                                or (sf_has_valid_email and key == 'Email')):
            sh_val = sfd.get(key, "")
            sf_val = sfc[key]
            if sh_val != sf_val:
                cae.dprint("Contact {}: prevented change of field {} to '{}' (from '{}')"
                           .format(sid, key, sh_val, sf_val))
            if key in ignore_case_fields:
                sh_val = sh_val.lower()
                sf_val = sf_val.lower()
            if sh_val != sf_val:
                ups_warnings.append("Contact {}: field {} has different value in Sihot '{}' then in Salesforce '{}'"
                                    .format(sid, key, sh_val, sf_val))
            continue

        sfs[send_key] = send_val    # pass field value to returned dictionary

    if sfs and sfd[AI_SF_ID]:
        sfs['Id'] = sfd[AI_SF_ID]

    return sfs


def ext_sf_dict(sfd, msg, skip_it=True):
    add_log_msg(("Skipping " if skip_it else "") + "res-id " + sfd[AI_SH_RL_ID]
                + " with " + msg + '; Sihot data=' + pretty_print.pformat(strip_add_info_from_sf_data(sfd)))
    sfd[AI_WARNINGS].append(msg)
    if skip_it:
        sfd[AI_SCORE] -= 1.0


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


def email_is_valid(email):
    if email:
        email = email.lower()
        if mail_re.match(email):
            for frag in invalid_email_fragments:
                if frag in email:
                    break  # email is invalid/filtered-out
            else:
                return True
    return False


def valid_email_indexes(shd):
    indexes = list()
    if PARSE_ONLY_TAG_PREFIX + 'EMAIL' in shd:
        col_def = shd[PARSE_ONLY_TAG_PREFIX + 'EMAIL']
        if 'elemListVal' in col_def:
            for idx, email in enumerate(col_def['elemListVal']):
                if email and email_is_valid(email):
                    indexes.append(idx)
        if not indexes and 'elemVal' in col_def and col_def['elemVal'] and email_is_valid(col_def['elemVal']):
            col_def['elemListVal'] = [col_def['elemVal']]
            indexes.append(0)
    return indexes


def score_match_name_to_email(sfd):
    mail_name = sfd['Email'].lower()
    if mail_name and '@' in mail_name:
        mail_name = mail_name.split('@')[0]
        mail_names = mail_name.replace('.', ' ').replace('-', ' ').replace('_', ' ').split()
        pers_name = sfd['FirstName'].lower() + " " + sfd['LastName'].lower()
        pers_names = pers_name.replace('.', ' ').replace('-', ' ').split()
        sfd[AI_SCORE] += len(set(mail_names).intersection(pers_names)) * 3.0 \
            + len([_ for _ in pers_names if _ in mail_name]) * 1.5 \
            + len([_ for _ in mail_name if _ in pers_name]) / len(mail_name)


def date_range_chunks():
    one_day = datetime.timedelta(days=1)
    add_days = datetime.timedelta(days=sh_fetch_max_days) - one_day
    chunk_till = date_from - one_day
    while chunk_till < date_till:
        chunk_from = chunk_till + one_day
        chunk_till = min(chunk_from + add_days, date_till)
        yield chunk_from, chunk_till


def prepare_mig_data(shd, arri, sh_res_id, email, snam, fnam, src, hot_id):
    """ mig MARKETCODE, LANG, NAME, NAME2, EMAIL, PHONE, COUNTRY, CITY, STREET, GDSNO, RES-HOTEL, RN, ARR, DEP """
    sh_rl_id = sh_res_id + '=' + str(arri + 1)  # rooming list id
    sfd = dict()
    sfd[AI_SH_RES_ID] = sh_res_id
    sfd[AI_SH_RL_ID] = sh_rl_id
    sfd[AI_WARNINGS] = list()
    sfd[AI_SCORE] = 0.0
    sfd[AI_SF_ID] = None  # populate later with data from Salesforce
    sfd[AI_SF_CURR_DATA] = None

    sfd['RecordType.DeveloperName'] = CONTACT_REC_TYPE_RENTALS
    # FirstName or LastName or Name (combined field - not works with UPDATE/CREATE) or Full_Name__c (Formula)
    sfd['FirstName'] = fnam     # get_col_val(shd, 'NAME2', arri)
    sfd['LastName'] = snam
    sfd['Birthdate'] = get_col_val(shd, 'DOB', arri)
    # Language (Picklist) or Spoken_Languages__c (Picklist, multi-select) ?!?!?
    lc_iso2 = get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'LANG', arri)
    sfd['Language__c'] = cae.get_config(lc_iso2, 'LanguageCodes', default_value=lc_iso2)
    # Description (Long Text Area, 32000) or Client_Comments__c (Long Text Area, 4000) or LeadSource (Picklist)
    # .. or Source__c (Picklist) or HERE_HOW__c (Picklist) ?!?!?
    sfd['Description'] = "Market Source=" + src
    sfd['Email'] = email if email_is_valid(email) else default_email_address
    # HomePhone or MobilePhone or Work_Phone__c (or Phone or OtherPhone or Phone2__c or AssistantPhone) ?!?!?
    phone_changes = list()
    sfd['HomePhone'], phone_changed = correct_phone(get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'PHONE', arri),
                                                    changed=False, removed=phone_changes)
    if phone_changed:
        ext_sf_dict(sfd, "HomePhone corrected, removed 'index:char'=" + str(phone_changes))
    # Mobile phone number is not provided by Sihot WEB RES-SEARCH
    # sfd['MobilePhone'] = get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'MOBIL', arri)
    # Address_1__c or MailingStreet
    sfd['MailingStreet'] = get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'STREET', arri)
    # MailingCity or City (Text, 50) or Address_2__c (Text, 80)
    sfd['MailingCity'] = get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'CITY', arri)
    # Country__c/code (Picklist) or Address_3__c (Text, 100) or MailingCountry
    # .. and remap, e.g. Great Britain need to be UK not GB (ISO2).
    # .. Also remove extra characters, because ES has sometimes suffix w/ two numbers
    cc_iso2 = get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'COUNTRY', arri, default_value="")[:2]
    sfd['Country__c'] = cae.get_config(cc_iso2, 'CountryCodes', default_value=cc_iso2)
    # Booking__c (Long Text Area, 32768) or use field Previous_Arrival_Info__c (Text, 100) ?!?!?
    sfd['Previous_Arrival_Info__c'] = (""
                                       + " Arr=" + get_col_val(shd, 'ARR', arri, default_value='')
                                       + " Dep=" + get_col_val(shd, 'DEP', arri, default_value='')
                                       + " Hotel=" + str(hot_id)
                                       + " Room=" + get_col_val(shd, 'RN', arri, default_value='')
                                       + " GdsNo=" + get_col_val(shd, 'GDSNO', arri, default_value='')
                                       + " ResId=" + sh_rl_id
                                       ).strip()

    return sfd


def layout_message(sfd, cols):
    form_str = "{:21}: {:33}"
    rtd = 'RecordType.DeveloperName'
    txt = "\n"
    for col in cols:
        shv = sfd[col]
        sf_curr_data = sfd[AI_SF_CURR_DATA]
        if not sf_curr_data:
            sfv = None
        elif col == rtd:
            sfv = sf_curr_data['RecordType']['DeveloperName'] \
                  + ", Contact Id=" + sf_curr_data['attributes']['url'].split('/')[-1]
        else:
            sfv = sf_curr_data[col]
        if shv or sfv:
            col_label = (col[:-3] if col[-3:] == '__c' else ("Record Type" if col == rtd else col)).replace("_", " ")
            txt += form_str.format(col_label, str(shv))
            if sfv:
                txt += " (SF={})".format(sfv)
            txt += "\n"
    txt += form_str.format("Sihot res-rooming-id", sfd[AI_SH_RL_ID]) + "\n"
    txt += form_str.format("Name-Mail Match Score", str(sfd[AI_SCORE])) + "\n"
    if sfd[AI_WARNINGS]:
        txt += "Discrepancies:\n" + "\n".join(["   " + _ for _ in sfd[AI_WARNINGS]]) + "\n"

    return txt + "-" * 108


uprint("####  Fetching from Sihot")
all_rows = list()
try:
    res_search = ResSearch(cae)
    # the from/to date range filter of WEB ResSearch is filtering the arrival date only (not date range/departure)
    # adding flag ;WITH-PERSONS results in getting the whole reservation duplicated for each PAX in rooming list
    # adding scope NOORDERER prevents to include/use LANG/COUNTRY/NAME/EMAIL of orderer
    for chunk_beg, chunk_end in date_range_chunks():
        chunk_rows = res_search.search(from_date=chunk_beg, to_date=chunk_end, flags=search_flags, scope=search_scope)
        if chunk_rows and isinstance(chunk_rows, str):
            uprint(" ***  Sihot.PMS reservation search error:", chunk_rows)
            cae.shutdown(21)
        elif not chunk_rows or not isinstance(chunk_rows, list):
            uprint(" ***  Unspecified Sihot.PMS reservation search error")
            cae.shutdown(24)
        uprint("  ##  Fetched {} reservations from Sihot with arrivals between {} and {} - flags={}, scope={}"
               .format(len(chunk_rows), chunk_beg, chunk_end, search_flags, search_scope))
        all_rows.extend(chunk_rows)
        time.sleep(sh_fetch_pause_seconds)
except Exception as ex:
    uprint(" ***  Sihot interface reservation fetch exception:", str(ex))
    print_exc()
    cae.shutdown(27)


# collect all the emails found in this export run (for to skip duplicates)
uprint("####  Evaluate reservations fetched from Sihot")
found_emails = list()
valid_contacts = list()
try:
    for row_dict in all_rows:
        hotel_id, res_id = get_hotel_and_res_id(row_dict)

        arr_indexes = valid_email_indexes(row_dict) if restrict_to_valid_emails else valid_name_indexes(row_dict)
        if not arr_indexes:
            add_log_msg("Skipping res-id {} with invalid/empty {}: {}"
                        .format(res_id, "email address" if restrict_to_valid_emails else "surname",
                                get_col_val(row_dict,
                                            PARSE_ONLY_TAG_PREFIX + 'EMAIL' if restrict_to_valid_emails else 'NAME',
                                            verbose=True)))
            continue
        for arr_index in arr_indexes:
            mail_changes = list()
            email_addr, mail_changed = correct_email(get_col_val(row_dict, PARSE_ONLY_TAG_PREFIX + 'EMAIL', arr_index),
                                                     changed=False, removed=mail_changes)
            surname = get_col_val(row_dict, 'NAME', arr_index)
            forename = get_col_val(row_dict, 'NAME2', arr_index)
            mkt_src = get_col_val(row_dict, PARSE_ONLY_TAG_PREFIX + 'MARKETCODE', arr_index)
            sh_dict = prepare_mig_data(row_dict, arr_index, res_id, email_addr, surname, forename, mkt_src, hotel_id)

            if mail_changed:
                ext_sf_dict(sh_dict, "email corrected, removed 'index:char'=" + str(mail_changes))
            if not hotel_id or hotel_id == '999':
                ext_sf_dict(sh_dict, "invalid hotel-id {}".format(hotel_id))
            if not res_id:
                ext_sf_dict(sh_dict, "missing res-id")
            check_in, check_out = get_date_range(row_dict)
            if not check_in or not check_out:
                ext_sf_dict(sh_dict, "incomplete check-in={} check-out={}".format(check_in, check_out))
            if not (date_from <= check_in <= date_till):
                ext_sf_dict(sh_dict, "arrival {} not between {} and {}".format(check_in, date_from, date_till))
            if mkt_src not in allowed_mkt_src:
                ext_sf_dict(sh_dict, "disallowed market source {}".format(mkt_src))
            res_type = get_col_val(row_dict, 'RT', arr_index)
            if res_type in ('S', 'N', '', None):
                ext_sf_dict(sh_dict, "invalid/cancel/no-show reservation type {}".format(res_type))
            if not email_addr:
                ext_sf_dict(sh_dict, "missing email address", skip_it=restrict_to_valid_emails)
            if not name_is_valid(surname):
                ext_sf_dict(sh_dict, "missing/invalid surname {}".format(surname))
            if not name_is_valid(forename):
                ext_sf_dict(sh_dict, "missing/invalid forename {}".format(forename))
            if not mkt_src:
                ext_sf_dict(sh_dict, "missing market source")
            res_group = get_col_val(row_dict, 'CHANNEL', verbose=True)
            if res_group != 'RS':
                ext_sf_dict(sh_dict, "empty/invalid res. group/channel {} (market-source={})"
                            .format(res_group, get_col_val(row_dict, PARSE_ONLY_TAG_PREFIX + 'MARKETCODE')),
                            skip_it=False)  # only warn on missing channel, so no: skip_it = True

            if sh_dict[AI_SCORE] >= 0.0:
                score_match_name_to_email(sh_dict)
                valid_contacts.append(sh_dict)

    uprint("####  Ordering filtered contacts")
    valid_contacts.sort(key=lambda d: d[AI_SH_RES_ID] + '{:06.3}'.format(d[AI_SCORE]),
                        reverse=True)
    uprint("####  Detecting reservation-id/email duplicates and fetch current Salesforce contact data (if available)")
    notification_lines.append("####  Validate and compare Sihot and Salesforce contact data")
    dup_res = 0
    dup_emails = 0
    rooming_list_ids = list()
    existing_contact_ids = list()
    contacts_to_mig = list()
    for sh_dict in valid_contacts:
        rl_id = sh_dict[AI_SH_RL_ID]
        if rl_id in rooming_list_ids:
            add_log_msg("Res-id {:12} is duplicated; data={}".format(rl_id, pretty_print.pformat(sh_dict)))
            dup_res += 1
            continue
        rooming_list_ids.append(rl_id)
        email_addr = sh_dict['Email']
        if email_is_valid(email_addr):
            if email_addr in found_emails:
                add_log_msg("Res-id {:12} with duplicate email address {}; data={}"
                            .format(rl_id, email_addr, pretty_print.pformat(sh_dict)))
                dup_emails += 1
                continue
            found_emails.append(email_addr)

            contacts_to_mig.append(sh_dict)

            sf_id = sf_conn.contact_by_email(email_addr)
            if sf_id:
                sf_cd = sf_conn.contact_data_by_id(sf_id, strip_add_info_keys(sh_dict))
                if sf_conn.error_msg:
                    notification_add_line("SF-FETCH-DATA-ERROR: '{}' of contact ID {}".format(sf_conn.error_msg, sf_id),
                                          is_error=True)
                    continue
                sh_dict[AI_SF_ID] = sf_id
                sh_dict[AI_SF_CURR_DATA] = sf_cd
                existing_contact_ids.append(sh_dict)
        elif not restrict_to_valid_emails:
            # ensure that also clients with clienthasnoemail@s... will be uploaded to Salesforce if email not restricted
            contacts_to_mig.append(sh_dict)

    uprint("####  Migrating contacts to Salesforce")
    notification_lines.append("####  Migrating Sihot guest data to Salesforce")
    rec_type_id = sf_conn.record_type_id(CONTACT_REC_TYPE_RENTALS)
    contacts_migrated = list()
    send_errors = 0
    for sh_dict in contacts_to_mig:
        res_id = sh_dict[AI_SH_RL_ID]
        sh_pp_data = pretty_print.pformat(sh_dict)
        sf_send = strip_add_info_from_sf_data(sh_dict, strip_populated_sf_fields=True, record_type_id=rec_type_id)
        if not sf_send:
            notification_add_line("Skipped Sihot Res-Id {:12} to be sent because of empty/unchanged Sihot guest data={}"
                                  .format(res_id, sh_pp_data))
            continue
        sfi = sh_dict[AI_SF_ID]
        err_msg, log_msg = sf_conn.contact_upsert(sf_send)
        if err_msg:
            send_errors += 1
            notification_add_line(("Error {} in {} of Sihot Res-Id {:12} with match score {:6.3}"
                                   " to Salesforce; sent data={}"
                                   + (" full data={full_data}" if debug_level >= DEBUG_LEVEL_VERBOSE else ""))
                                  .format(err_msg, "updating Contact " + sfi if sfi else "migrating",
                                          res_id, sh_dict[AI_SCORE], pretty_print.pformat(sf_send),
                                          full_data=sh_pp_data),
                                  is_error=True)
        else:
            contacts_migrated.append(sh_dict)
        if log_msg:
            notification_add_line("Migrated Sihot Res-Id {:12} {} with match score {:6.3} to Salesforce; data={}, {}"
                                  .format(res_id, "updated Contact " + sfi if sfi else "migrated",
                                          sh_dict[AI_SCORE], sh_pp_data, log_msg))

    uprint(" ###  Sihot-Salesforce data mismatches (not updated in Salesforce) - UPSERT warnings:")
    for upsert_msg in ups_warnings:
        uprint("   #  ", upsert_msg)

    uprint()
    uprint("####  Migration Summary")
    uprint()
    valid_contact_count = len(valid_contacts)
    mig_contact_count = valid_contact_count - dup_res - dup_emails - send_errors
    assert len(contacts_migrated) == mig_contact_count
    notification_add_line("Duplicate {}/{} res-ids/emails and {} upload errors out of valid {} Sihot guests/clients"
                          .format(dup_res, dup_emails, send_errors, valid_contact_count))
    uprint("Found {} unique emails: {}".format(len(found_emails), found_emails))
    uprint("Skipped {} duplicates of loaded reservation-rooming-ids: {}".format(dup_res, rooming_list_ids))
    uprint()
    uprint(" ###  Comparision of {} existing Sf contacts".format(len(existing_contact_ids)))
    for sh_dict in existing_contact_ids:
        ec = deepcopy(sh_dict)
        uprint("  ##  Sf-Id", ec[AI_SF_ID])
        uprint("      SF:", pprint.pformat(ec[AI_SF_CURR_DATA], indent=9, width=PP_DEF_WIDTH))
        ec.pop(AI_SF_CURR_DATA)
        uprint("      SH:", pprint.pformat(ec, indent=9, width=PP_DEF_WIDTH))

    uprint()
    uprint("####  ", mig_contact_count, "Contacts migrated:")
    contacts_notifications = list()
    range_str = ("BETWEEN" + date_from.strftime(SIHOT_DATE_FORMAT) + " AND " + date_till.strftime(SIHOT_DATE_FORMAT)) \
        if date_till != date_from else "ON " + date_from.strftime(SIHOT_DATE_FORMAT)
    contacts_notifications.append("####  {} MIGRATED CONTACTS ARRIVED {}:\n\n"
                                  .format(mig_contact_count, range_str))
    layout_fields = ['RecordType.DeveloperName', 'FirstName', 'LastName', 'Birthdate', 'Email', 'HomePhone',
                     'MailingStreet', 'MailingCity', 'Country__c',
                     'Language__c', 'Description', 'Previous_Arrival_Info__c']
    for sh_dict in contacts_migrated:
        contact_layout = layout_message(sh_dict, layout_fields)
        uprint(contact_layout)
        # add as one monospaced font block with including \n to prevent double \n\n
        contacts_notifications.append(msf_beg + contact_layout + msf_end)
    notification_lines = contacts_notifications + ["\n\n####  FULL PROTOCOL:\n"] + notification_lines

except Exception as ex:
    notification_add_line("Migration interrupted by exception: {}".format(ex), is_error=True)
    print_exc()

if notification:
    subject = "Sihot Salesforce Contact Migration protocol" + (" (sandbox/test system)" if sf_sandbox else "")
    mail_body = "\n\n".join(notification_lines)
    send_err = notification.send_notification(mail_body, subject=subject)
    if send_err:
        uprint("****  " + subject + " send error: {}. mail-body='{}'.".format(send_err, mail_body))
        cae.shutdown(36)
    if warning_notification_emails and (ups_warnings or log_errors):
        mail_body = "MIGRATION WARNINGS:\n\n" + ("\n\n".join(ups_warnings) if ups_warnings else "NONE") \
                    + "\n\nERRORS:\n\n" + ("\n\n".join(log_errors) if log_errors else "NONE")
        subject = "Sihot Salesforce Contact Migration errors/discrepancies" + (" (sandbox)" if sf_sandbox else "")
        send_err = notification.send_notification(mail_body, subject=subject, mail_to=warning_notification_emails)
        if send_err:
            uprint("****  " + subject + " send error: {}. mail-body='{}'.".format(send_err, mail_body))
            cae.shutdown(39)

if log_errors:
    cae.shutdown(42)

# CURRENTLY DISABLED because this is running daily and the command line args defaults
# if date_till == startup_date - datetime.timedelta(days=1):
#    cae.set_config('dateFrom', date_till)
#    uprint("  ##  Changed next runs From Date to", date_till)

cae.shutdown()
