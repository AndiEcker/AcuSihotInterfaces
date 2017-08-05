"""
    ShSfContactMigration is a tool for to migrate every Sihot rental guest with valid contact data as a contact
    object into the Salesforce system.

    0.1     first beta.
"""
import datetime
import time
import re
from traceback import print_exc

from ae_console_app import ConsoleApp, uprint
from sxmlif import ResSearch, SXML_DEF_ENCODING, PARSE_ONLY_TAG_PREFIX
from sfif import SfInterface

__version__ = '0.1'

LINE_SEPARATOR = '\n'
SIHOT_PROVIDES_CHECKOUT_TIME = False  # currently there is no real checkout time available in Sihot
SIHOT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S' if SIHOT_PROVIDES_CHECKOUT_TIME else '%Y-%m-%d'

startup_date = datetime.datetime.now() if SIHOT_PROVIDES_CHECKOUT_TIME else datetime.date.today()
mail_re = re.compile('[a-zA-Z0-9._%-]+@[a-zA-Z0-9._%-]+\.[a-zA-Z]{2,4}$')

cae = ConsoleApp(__version__, "Migrate contactable guests from Sihot to Salesforce")
cae.add_option('serverIP', "IP address of the Sihot interface server", 'localhost', 'i')
cae.add_option('serverPort', "IP port of the Sihot WEB interface", 14777, 'w')
cae.add_option('timeout', "Timeout value for TCP/IP connections to Sihot", 1869.6, 't')
cae.add_option('xmlEncoding', "Charset used for the Sihot xml data", SXML_DEF_ENCODING, 'e')

cae.add_option('dateFrom', "Date" + ("/time" if SIHOT_PROVIDES_CHECKOUT_TIME else "") +
               " of first check-in to be migrated", startup_date - datetime.timedelta(days=21), 'F')
cae.add_option('dateTill', "Date" + ("/time" if SIHOT_PROVIDES_CHECKOUT_TIME else "") +
               " of last check-in to be migrated", startup_date, 'T')

uprint("Server IP/Web-port:", cae.get_option('serverIP'), cae.get_option('serverPort'))
uprint("TCP Timeout/XML Encoding:", cae.get_option('timeout'), cae.get_option('xmlEncoding'))

date_from = cae.get_option('dateFrom')
date_till = cae.get_option('dateTill')
uprint("Date range including check-ins from", date_from.strftime(SIHOT_DATE_FORMAT),
       'and till/before', date_till.strftime(SIHOT_DATE_FORMAT))
if date_from >= date_till:
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

invalid_email_fragments = cae.get_config('InvalidEmailFragments', default_value=[])
uprint("Invalid email fragments:", invalid_email_fragments)

allowed_mkt_src = cae.get_config('MarketSources', default_value=[])
uprint("Allowed Market Sources:", allowed_mkt_src)

sf_user = cae.get_config('sfUser', default_value='')
sf_sandbox = cae.get_config('sfIsSandbox', default_value=False)
sf_client = cae.get_config('sfClientId', default_value='ShSfContactMigration')
uprint("Salesforce " + ("sandbox " if sf_sandbox else "") + "user/client-id:", sf_user, sf_client)

sf_conn = SfInterface(sf_user, cae.get_config('sfPassword'), cae.get_config('sfToken'), sf_sandbox, sf_client)

REC_TYPE_DEV_NAME = 'Rentals'
ELEM_MISSING = "(missing)"
ELEM_EMPTY = "(empty)"
ADD_INFO_PREFIX = '+'

mig_errors = []
mig_warnings = []       # warnings on Sihot data
ups_warnings = []       # warnings on Salesforce upserts


def mig_error(msg):
    msg = "  **  " + msg
    mig_errors.append(msg)
    uprint(msg)


def mig_warning(msg):
    msg = "  ##  " + msg
    mig_warnings.append(msg)
    uprint(msg)


def strip_add_info_keys(sfd):
    return [_ for _ in sfd.keys() if not _.startswith(ADD_INFO_PREFIX)]


def strip_add_info_from_sf_data(sfd, strip_populated_sf_fields=False, record_type_id=None):
    sfs = dict()
    sfc = sfd[ADD_INFO_PREFIX + 'sf_curr_data'] if strip_populated_sf_fields else None
    for data_key in strip_add_info_keys(sfd):
        is_rec_type_key = (data_key == 'RecordType.DeveloperName')
        if not sfc or is_rec_type_key or not sfc[data_key]:
            if record_type_id and is_rec_type_key:
                sfs['RecordTypeId'] = record_type_id
            else:
                sfs[data_key] = sfd[data_key]
        elif sfc[data_key] != sfd[data_key]:
            ups_warnings.append("Salesforce field {} has different value {} then Sihot {}"
                                .format(data_key, sfc[data_key], sfd[data_key]))
    return sfs


def ext_sf_dict(sfd, msg, skip_it=True):
    mig_warning(("Skipping " if skip_it else "") + "res-id " + sfd[ADD_INFO_PREFIX + 'sh_rl_id']
                + " with " + msg + '; Sihot data=' + str(strip_add_info_from_sf_data(sfd)))
    sfd[ADD_INFO_PREFIX + 'warnings'].append(msg)
    if skip_it:
        sfd[ADD_INFO_PREFIX + 'score'] -= 1.0


def get_col_val(shd, col_nam, arri=-1, verbose=False):
    """ get the column value from the row_dict variable, using arr_index in case of multiple values """
    if col_nam not in shd:
        col_val = ELEM_MISSING if verbose else ""
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
        if not col_val and verbose:
            col_val = ELEM_EMPTY

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


def email_is_valid(email):
    email = email.lower()
    if email and mail_re.match(email):
        for frag in invalid_email_fragments:
            if frag in email:
                break       # email is invalid/filtered-out
        else:
            return True
    return False


def valid_email_indexes(shd):
    indexes = []
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
    mail_names = mail_name.replace('.', ' ').replace('-', ' ').replace('_', ' ').split()
    pers_name = sfd['FirstName'].lower() + " " + sfd['LastName'].lower()
    pers_names = pers_name.replace('.', ' ').replace('-', ' ').split()
    sfd[ADD_INFO_PREFIX + 'score'] += len(set(mail_names).intersection(pers_names)) * 3.0 \
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

uprint("####  Fetching from Sihot")
all_rows = []
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
    uprint(" ***  Sihot interface exception:", str(ex))
    print_exc()
    cae.shutdown(27)


def prepare_mig_data(shd, arri, sh_res_id, email, snam, src, hot_id):
    """ mig MARKETCODE, LANG, NAME, NAME2, EMAIL, PHONE, COUNTRY, CITY, STREET, GDSNO, RES-HOTEL, RN, ARR, DEP """
    sfd = dict()
    sfd['RecordType.DeveloperName'] = REC_TYPE_DEV_NAME
    # FirstName or LastName or Name (combined field - not works with UPDATE/CREATE) or Full_Name__c (Formula)
    sfd['FirstName'] = get_col_val(shd, 'NAME2', arri)
    sfd['LastName'] = snam
    # Language (Picklist) or Spoken_Languages__c (Picklist, multi-select) ?!?!?
    lc_iso2 = get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'LANG', arri)
    sfd['Language__c'] = cae.get_config(lc_iso2, 'LanguageCodes', default_value=lc_iso2)
    # Description (Long Text Area, 32000) or Client_Comments__c (Long Text Area, 4000) or LeadSource (Picklist)
    # .. or Source__c (Picklist) or HERE_HOW__c (Picklist) ?!?!?
    sfd['Description'] = "Market Source=" + src
    sfd['Email'] = email
    # Phone or OtherPhone or HomePhone ?!?!?
    sfd['Phone'] = get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'PHONE', arri)
    # Address_1__c or MailingStreet
    sfd['MailingStreet'] = get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'STREET', arri)
    # MailingCity or City (Text, 50) or Address_2__c (Text, 80)
    sfd['MailingCity'] = get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'CITY', arri)
    # Country__c/code (Picklist) or Address_3__c (Text, 100) or MailingCountry
    # .. and remap, e.g. Great Britain need to be UK not GB (ISO2)
    cc_iso2 = get_col_val(shd, PARSE_ONLY_TAG_PREFIX + 'COUNTRY', arri)[:2]     # ES has sometimes suffix w/ two numbers
    sfd['Country__c'] = cae.get_config(cc_iso2, 'CountryCodes', default_value=cc_iso2)
    # Booking__c (Long Text Area, 32768) or use field Previous_Arrival_Info__c (Text, 100) ?!?!?
    sfd['Previous_Arrival_Info__c'] = "Hotel=" + hot_id \
        + " Room=" + get_col_val(shd, 'RN', arri) \
        + " Arr=" + get_col_val(shd, 'ARR', arri) \
        + " Dep=" + get_col_val(shd, 'DEP', arri) \
        + " Sihot GdsNo=" + get_col_val(shd, 'GDSNO', arri)

    sfd[ADD_INFO_PREFIX + 'sh_res_id'] = sh_res_id
    sfd[ADD_INFO_PREFIX + 'sh_rl_id'] = sh_res_id + '=' + str(arr_index + 1)   # rooming list id
    sfd[ADD_INFO_PREFIX + 'warnings'] = list()
    sfd[ADD_INFO_PREFIX + 'score'] = 0.0
    sfd[ADD_INFO_PREFIX + 'sf_id'] = None           # populate later with data from Salesforce
    sfd[ADD_INFO_PREFIX + 'sf_curr_data'] = None

    return sfd


def layout_message(sfd, cols):
    form_str = "{:21}: {:33}"
    rtd = 'RecordType.DeveloperName'
    txt = "\n"
    for col in cols:
        shv = sfd[col]
        sf_curr_data = sfd[ADD_INFO_PREFIX + 'sf_curr_data']
        if not sf_curr_data:
            sfv = None
        elif col == rtd:
            sfv = sf_curr_data['RecordType']['DeveloperName'] \
                  + ", Contact Id=" + sf_curr_data['attributes']['url'].split('/')[-1]
        else:
            sfv = sf_curr_data[col]
        if shv or sfv:
            col_label = (col[:-3] if col[-3:] == '__c' else ("Record Type" if col == rtd else col)).replace("_", " ")
            txt += form_str.format(col_label, shv)
            if sfv:
                txt += " (SF={})".format(sfv)
            txt += "\n"
    txt += form_str.format("Sihot res-rooming-id", sfd[ADD_INFO_PREFIX + 'sh_rl_id']) + "\n"
    txt += form_str.format("Name-Mail Match Score", str(sfd[ADD_INFO_PREFIX + 'score'])) + "\n"
    if sfd[ADD_INFO_PREFIX + 'warnings']:
        txt += "Discrepancies:\n" + "\n".join(["   " + _ for _ in sfd[ADD_INFO_PREFIX + 'warnings']]) + "\n"

    return txt + "-" * 108


# collect all the emails found in this export run (for to skip duplicates)
uprint("####  Evaluate reservations fetched from Sihot")
found_emails = []
valid_contacts = []
try:
    dup_res = 0
    dup_emails = 0
    rooming_list_ids = []
    existing_contact_ids = []
    for row_dict in all_rows:
        hotel_id, res_id = get_hotel_and_res_id(row_dict)
        arr_indexes = valid_email_indexes(row_dict)
        if not arr_indexes:
            mig_warning("Skipping res-id {} with invalid/empty email address(es) {}"
                        .format(res_id, get_col_val(row_dict, PARSE_ONLY_TAG_PREFIX + 'EMAIL', verbose=True)))
            continue
        for arr_index in arr_indexes:
            email_addr = get_col_val(row_dict, PARSE_ONLY_TAG_PREFIX + 'EMAIL', arr_index)
            surname = get_col_val(row_dict, 'NAME', arr_index)
            mkt_src = get_col_val(row_dict, PARSE_ONLY_TAG_PREFIX + 'MARKETCODE', arr_index)
            sf_dict = prepare_mig_data(row_dict, arr_index, res_id, email_addr, surname, mkt_src, hotel_id)

            if not hotel_id or hotel_id == '999':
                ext_sf_dict(sf_dict, "invalid hotel-id {}".format(hotel_id))
            if not res_id:
                ext_sf_dict(sf_dict, "missing res-id")
            check_in, check_out = get_date_range(row_dict)
            if not check_in or not check_out:
                ext_sf_dict(sf_dict, "incomplete check-in={} check-out={}".format(check_in, check_out))
            if not (date_from <= check_in <= date_till):
                ext_sf_dict(sf_dict, "arrival {} not between {} and {}".format(check_in, date_from, date_till))
            if mkt_src not in allowed_mkt_src:
                ext_sf_dict(sf_dict, "disallowed market source {}".format(mkt_src))
            res_type = get_col_val(row_dict, 'RT', arr_index)
            if res_type in ('S', 'N', '', None):
                ext_sf_dict(sf_dict, "invalid/cancel/no-show reservation type {}".format(res_type))
            if not email_addr:
                ext_sf_dict(sf_dict, "missing email address")
            if surname in ("Adult 1", "Adult 2", "Adult 3", "Adult 4", "Adult 5", "Adult 6",
                           "Child 1", "Child 1", "Child 2", "Child 4", "NO NAME", "not specified", "", None):
                ext_sf_dict(sf_dict, "missing/invalid surname {}".format(surname))
            if not mkt_src:
                ext_sf_dict(sf_dict, "missing market source")
            res_group = get_col_val(row_dict, 'CHANNEL', verbose=True)
            if res_group != 'RS':
                ext_sf_dict(sf_dict, "empty/invalid res. group/channel {} (market-source={})"
                            .format(res_group, get_col_val(row_dict, PARSE_ONLY_TAG_PREFIX + 'MARKETCODE')),
                            skip_it=False)  # only warn on missing channel, so no: skip_it = True

            if sf_dict[ADD_INFO_PREFIX + 'score'] >= 0.0:
                score_match_name_to_email(sf_dict)
                valid_contacts.append(sf_dict)

    uprint("####  Ordering filtered contacts")
    valid_contacts.sort(key=lambda d: d[ADD_INFO_PREFIX + 'sh_res_id'] + '{:06.3}'.format(d[ADD_INFO_PREFIX + 'score']),
                        reverse=True)
    uprint("####  Detecting reservation-id/email duplicates and fetch current Salesforce contact data (if available)")
    mig_contacts = list()
    for sf_dict in valid_contacts:
        rl_id = sf_dict[ADD_INFO_PREFIX + 'sh_rl_id']
        if rl_id in rooming_list_ids:
            mig_warning("Res-id {:12} is duplicated; data={}".format(rl_id, sf_dict))
            dup_res += 1
            continue
        rooming_list_ids.append(rl_id)
        email_addr = sf_dict['Email']
        if email_addr in found_emails:
            mig_warning("Res-id {:12} with duplicate email address {}; data={}".format(rl_id, email_addr, sf_dict))
            dup_emails += 1
            continue
        found_emails.append(email_addr)

        mig_contacts.append(sf_dict)

        sf_id = sf_conn.contact_by_email(email_addr)
        if sf_id:
            sf_cd = sf_conn.contact_data_by_id(sf_id, strip_add_info_keys(sf_dict))
            if sf_conn.error_msg:
                mig_error("SF-ERROR: " + sf_conn.error_msg)
                continue
            sf_dict[ADD_INFO_PREFIX + 'sf_id'] = sf_id
            sf_dict[ADD_INFO_PREFIX + 'sf_curr_data'] = sf_cd
            existing_contact_ids.append(sf_dict)

    uprint("####  Migrating contacts to Salesforce")
    rec_type_id = sf_conn.record_type_id(REC_TYPE_DEV_NAME)
    for sf_dict in mig_contacts:
        sf_send = strip_add_info_from_sf_data(sf_dict, strip_populated_sf_fields=True, record_type_id=rec_type_id)
        sfi = sf_dict[ADD_INFO_PREFIX + 'sf_id']
        if sfi:
            sf_conn.sf_types().Contact.update(sfi, sf_send)
        else:
            sf_conn.sf_types().Contact.create(sf_send)
        if sf_conn.error_msg:
            mig_warning("UPSERT of Salesforce Contact Id {} with error: {}".format(sfi, sf_conn.error_msg))
        else:
            mig_warning("Res-Id {:12} {} with match score {:6.3} to Salesforce; data={}"
                        .format(sf_dict[ADD_INFO_PREFIX + 'sh_rl_id'], "updated Contact " + sfi if sfi else "migrated",
                                sf_dict[ADD_INFO_PREFIX + 'score'], sf_dict))

    uprint(" ###  Sihot-Salesforce data mismatches (not updated in Salesforce) - UPSERT warnings:")
    for upsert_msg in ups_warnings:
        uprint("   #  ", upsert_msg)

    uprint()
    uprint("####  Migration Summary")
    uprint()
    valid_contact_count = len(valid_contacts)
    mig_contact_count = valid_contact_count - dup_res - dup_emails
    assert len(mig_contacts) == mig_contact_count
    uprint("Filtered duplicate {} res-ids and {} emails out of valid/fetched {}/{} Sihot guests/clients"
           .format(dup_res, dup_emails, valid_contact_count, len(all_rows)))
    uprint("Found {} unique emails out of valid {} emails".format(dup_emails, len(found_emails), found_emails))
    uprint("Skipped {} duplicates out of {} valid Sihot reservation-rooming-ids".format(dup_res, rooming_list_ids))
    uprint()
    uprint(" ###  Comparision of {} existing Sf contacts".format(len(existing_contact_ids)))
    for sf_dict in existing_contact_ids:
        uprint("  ##  Sf-Id", sf_dict[ADD_INFO_PREFIX + 'sf_id'])
        uprint("      SH:", sf_dict)
        uprint("      SF:", sf_dict[ADD_INFO_PREFIX + 'sf_curr_data'])

    uprint()
    uprint("####  ", mig_contact_count, "Contacts migrated:")
    layout_fields = ['RecordType.DeveloperName', 'FirstName', 'LastName', 'Email', 'Phone',
                     'MailingStreet', 'MailingCity', 'Country__c',
                     'Language__c', 'Description', 'Previous_Arrival_Info__c']
    for sf_dict in mig_contacts:
        uprint(layout_message(sf_dict, layout_fields))


except Exception as ex:
    mig_error("Migration interrupted by exception: {}".format(ex))
    print_exc()


if mig_errors:
    cae.shutdown(39)

if date_till == startup_date:
    cae.set_config('dateFrom', date_till)

cae.shutdown()
