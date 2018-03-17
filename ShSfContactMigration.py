"""
    ShSfContactMigration is a tool for to migrate every Sihot rental guest with valid contact data as a SF Contact,
    Lead or Account (PersonAccount) object into the Salesforce system.

    0.1     first beta.
    0.2     refactored for to upload to SF as Account/Lead (before: Contact) all yesterday arrivals (before: only
            Rentals), implemented email/phone validation options and adapted for new SF instance.
"""
import re
from traceback import print_exc
import pprint

from copy import deepcopy

from ae_console_app import ConsoleApp, uprint, DEBUG_LEVEL_VERBOSE
from ae_contact_validation import add_validation_options, init_validation, CONTACT_REC_TYPE_RENTALS
from ae_notification import add_notification_options, init_notification
from shif import ResBulkFetcher, date_range, elem_value, hotel_and_res_id
from sfif import add_sf_options, prepare_connection, correct_email, correct_phone

__version__ = '0.2'

mail_re = re.compile('[a-zA-Z0-9._%-]+@[a-zA-Z0-9._%-]+\.[a-zA-Z]{2,4}$')

PP_DEF_WIDTH = 120
pretty_print = pprint.PrettyPrinter(indent=6, width=PP_DEF_WIDTH, depth=9)


cae = ConsoleApp(__version__, "Migrate contactable guests from Sihot to Salesforce")

rbf = ResBulkFetcher(cae, allow_future_arrivals=False)
rbf.add_options()

add_validation_options(cae)
add_sf_options(cae)
add_notification_options(cae)


debug_level = cae.get_option('debugLevel')

rbf.load_config()
rbf.print_config()

email_validation, email_validator, \
    phone_validation, phone_validator, \
    addr_validation, addr_validator, \
    filter_sf_clients, filter_sf_rec_types, filter_email, \
    default_email_address, invalid_email_fragments, ignore_case_fields, changeable_fields = init_validation(cae)

sf_conn, sf_sandbox = prepare_connection(cae)
if not sf_conn:
    uprint("Salesforce account connection could not be established - please check your account data and credentials")
    cae.shutdown(20)

notification, warning_notification_emails = init_notification(cae, cae.get_option('serverIP') + '/Salesforce '
                                                              + ("sandbox" if sf_sandbox else "production"))

# html font is not working in Outlook: <font face="Courier New, Courier, monospace"> ... </font>
msf_beg = cae.get_config('monoSpacedFontBegin', default_value='<pre>')
msf_end = cae.get_config('monoSpacedFontEnd', default_value='</pre>')


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
        if sfc and key in sfc and sfc[key] and (key not in changeable_fields
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


def name_is_valid(name):
    if name:
        name = name.lower()
    return name not in ("adult 1", "adult 2", "adult 3", "adult 4", "adult 5", "adult 6",
                        "child 1", "child 1", "child 2", "child 4", "no name", "not specified", "", None)


def valid_name_indexes(shd):
    indexes = list()
    if 'NAME' in shd and 'NAME2' in shd:
        elem_def1 = shd['NAME']
        elem_def2 = shd['NAME2']
        if 'elemListVal' in elem_def1 and 'elemListVal' in elem_def2:
            for idx, name in enumerate(elem_def1['elemListVal']):
                if len(elem_def2['elemListVal']) > idx:
                    name2 = elem_def2['elemListVal'][idx]
                    if name and name_is_valid(name) and name2 and name_is_valid(name2):
                        indexes.append(idx)
        if not indexes and 'elemVal' in elem_def1 and elem_def1['elemVal'] and name_is_valid(elem_def1['elemVal']) \
                and 'elemVal' in elem_def2 and elem_def2['elemVal'] and name_is_valid(elem_def2['elemVal']):
            elem_def1['elemListVal'] = [elem_def1['elemVal']]
            elem_def2['elemListVal'] = [elem_def2['elemVal']]
            indexes.append(0)
    return indexes


def email_is_valid(email_addr):
    if email_addr:
        email_addr = email_addr.lower()
        if mail_re.match(email_addr):
            for frag in invalid_email_fragments:
                if frag in email_addr:
                    break  # email is invalid/filtered-out
            else:
                return True
    return False


def valid_email_indexes(shd):
    indexes = list()
    if 'EMAIL' in shd:
        elem_def = shd['EMAIL']
        if 'elemListVal' in elem_def:
            for idx, email_addr in enumerate(elem_def['elemListVal']):
                if email_addr and email_is_valid(email_addr):
                    indexes.append(idx)
        if not indexes and 'elemVal' in elem_def and elem_def['elemVal'] and email_is_valid(elem_def['elemVal']):
            elem_def['elemListVal'] = [elem_def['elemVal']]
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


def prepare_mig_data(shd, arri, sh_res_id, email_addr, phone_no, snam, fnam, src, hot_id):
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
    sfd['FirstName'] = fnam     # elem_value(shd, 'NAME2', arri)
    sfd['LastName'] = snam
    sfd['Birthdate'] = elem_value(shd, 'DOB', arri)
    # Language__c (Picklist) or Spoken_Languages__c (Picklist, multi-select) ?!?!?
    lc_iso2 = elem_value(shd, 'LANG', arri)
    sfd['Language'] = cae.get_config(lc_iso2, 'LanguageCodes', default_value=lc_iso2)
    # Description (Long Text Area, 32000) or Client_Comments__c (Long Text Area, 4000) or LeadSource (Picklist)
    # .. or Source__c (Picklist) or HERE_HOW__c (Picklist) ?!?!?
    sfd['Description'] = "Market Source=" + str(src)
    sfd['Email'] = email_addr if email_is_valid(email_addr) else default_email_address
    # Phone or HomePhone or MobilePhone or Work_Phone__c (or Phone or OtherPhone or Phone2__c or AssistantPhone) ?!?!?
    sfd['Phone'] = phone_no
    # Mobile phone number is not provided by Sihot WEB RES-SEARCH
    # sfd['MobilePhone'] = elem_value(shd, 'MOBIL', arri)
    # Address_1__c or Address.Street or MailingStreet
    sfd['Street'] = elem_value(shd, 'STREET', arri)
    # MailingCity or City (Text, 50) or Address.City or Address_2__c (Text, 80)
    sfd['City'] = elem_value(shd, 'CITY', arri)
    # Country__c/code (Picklist) or Address.Country or Address_3__c (Text, 100) or MailingCountry
    # .. and remap, e.g. Great Britain need to be UK not GB (ISO2).
    # .. Also remove extra characters, because ES has sometimes suffix w/ two numbers
    cc_iso2 = elem_value(shd, 'COUNTRY', arri, default_value="")[:2]
    sfd['Country'] = cae.get_config(cc_iso2, 'CountryCodes', default_value=cc_iso2)
    # Booking__c (Long Text Area, 32768) or use field Previous_Arrival_Info__c (Text, 100) ?!?!?
    sfd['ArrivalInfo'] = (""
                          + " Arr=" + elem_value(shd, 'ARR', arri, default_value='')
                          + " Dep=" + elem_value(shd, 'DEP', arri, default_value='')
                          + " Hotel=" + str(hot_id)
                          + " Room=" + elem_value(shd, 'RN', arri, default_value='')
                          + " GdsNo=" + elem_value(shd, 'GDSNO', arri, default_value='')
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
            field_label = (col[:-3] if col[-3:] == '__c' else ("Record Type" if col == rtd else col)).replace("_", " ")
            txt += form_str.format(field_label, str(shv))
            if sfv:
                txt += " (SF={})".format(sfv)
            txt += "\n"
    txt += form_str.format("Sihot res-rooming-id", sfd[AI_SH_RL_ID]) + "\n"
    txt += form_str.format("Name-Mail Match Score", str(sfd[AI_SCORE])) + "\n"
    if sfd[AI_WARNINGS]:
        txt += "Discrepancies:\n" + "\n".join(["   " + _ for _ in sfd[AI_WARNINGS]]) + "\n"

    return txt + "-" * 108


uprint("####  Fetching from Sihot")
all_rows = rbf.fetch_all()

# collect all the emails found in this export run (for to skip duplicates)
uprint("####  Evaluate reservations fetched from Sihot")
found_emails = list()
found_phones = list()
valid_clients = list()
try:
    for row_dict in all_rows:
        hotel_id, res_id = hotel_and_res_id(row_dict)

        arr_indexes = valid_email_indexes(row_dict) if filter_email[:5] == 'valid' else valid_name_indexes(row_dict)
        if not arr_indexes:
            add_log_msg("Skipping res-id {} with invalid/empty {}: {}"
                        .format(res_id, "email address" if filter_email[:5] == 'valid' else "surname",
                                elem_value(row_dict, 'EMAIL' if filter_email[:5] == 'valid' else 'NAME', verbose=True)))
            continue
        for arr_index in arr_indexes:
            mail_changes = list()
            email, mail_changed = correct_email(elem_value(row_dict, 'EMAIL', arr_index),
                                                changed=False, removed=mail_changes)
            phone_changes = list()
            phone, phone_changed = correct_phone(elem_value(row_dict, 'PHONE', arr_index),
                                                 changed=False, removed=phone_changes)
            surname = elem_value(row_dict, 'NAME', arr_index)
            forename = elem_value(row_dict, 'NAME2', arr_index)
            mkt_src = elem_value(row_dict, 'MARKETCODE', arr_index)
            sf_dict = prepare_mig_data(row_dict, arr_index, res_id, email, phone, surname, forename, mkt_src, hotel_id)

            if mail_changed:
                ext_sf_dict(sf_dict, "email corrected, removed 'index:char'=" + str(mail_changes), skip_it=False)
            if email_validator and email:
                err_msg = email_validator.validate(email)
                if err_msg:
                    ext_sf_dict(sf_dict, "email {} invalid, err={}".format(email, err_msg))
            if phone_changed:
                ext_sf_dict(sf_dict, "phone corrected, removed 'index:char'=" + str(phone_changes), skip_it=False)
            if phone_validator and phone:
                err_msg = phone_validator.validate(phone, country_code=elem_value(row_dict, 'COUNTRY', arr_index))
                if err_msg:
                    ext_sf_dict(sf_dict, "phone {} invalid, err={}".format(phone, err_msg), skip_it=False)
            if not hotel_id or hotel_id == '999':
                ext_sf_dict(sf_dict, "invalid hotel-id {}".format(hotel_id))
            if not res_id:
                ext_sf_dict(sf_dict, "missing res-id")
            check_in, check_out = date_range(row_dict)
            if not check_in or not check_out:
                ext_sf_dict(sf_dict, "incomplete check-in={} check-out={}".format(check_in, check_out))
            if not (rbf.date_from <= check_in <= rbf.date_till):
                ext_sf_dict(sf_dict, "arrival {} not between {} and {}".format(check_in, rbf.date_from, rbf.date_till))
            if mkt_src not in rbf.allowed_mkt_src:
                ext_sf_dict(sf_dict, "disallowed market source {}".format(mkt_src))
            res_type = elem_value(row_dict, 'RT', arr_index)
            if res_type in ('S', 'N', '', None):
                ext_sf_dict(sf_dict, "invalid/cancel/no-show reservation type {}".format(res_type))
            if not email:
                ext_sf_dict(sf_dict, "missing email address", skip_it=filter_email[:5] == 'valid')
            if not name_is_valid(surname):
                ext_sf_dict(sf_dict, "missing/invalid surname {}".format(surname))
            if not name_is_valid(forename):
                ext_sf_dict(sf_dict, "missing/invalid forename {}".format(forename))
            if not mkt_src:
                ext_sf_dict(sf_dict, "missing market source")
            res_group = elem_value(row_dict, 'CHANNEL', verbose=True)
            if res_group != 'RS':
                ext_sf_dict(sf_dict, "empty/invalid res. group/channel {} (market-source={})"
                            .format(res_group, elem_value(row_dict, 'MARKETCODE')),
                            skip_it=False)  # only warn on missing channel, so no: skip_it = True

            if sf_dict[AI_SCORE] >= 0.0:
                score_match_name_to_email(sf_dict)
                valid_clients.append(sf_dict)

    uprint("####  Ordering filtered contacts")
    valid_clients.sort(key=lambda d: d[AI_SH_RES_ID] + '{:06.3}'.format(d[AI_SCORE]),
                       reverse=True)
    uprint("####  Detecting reservation-id/email duplicates and fetch current Salesforce contact data (if available)")
    notification_lines.append("####  Validate and compare Sihot and Salesforce contact data")
    dup_res = dup_emails = dup_phones = 0
    rooming_list_ids = list()
    existing_client_ids = list()
    clients_to_mig = list()
    for sf_dict in valid_clients:
        rl_id = sf_dict[AI_SH_RL_ID]
        if rl_id in rooming_list_ids:
            add_log_msg("Res-id {:12} is duplicated; data={}".format(rl_id, pretty_print.pformat(sf_dict)))
            dup_res += 1
            continue
        rooming_list_ids.append(rl_id)

        email = sf_dict['Email']
        if email_is_valid(email):
            if email in found_emails:
                add_log_msg("Res-id {:12} with duplicate email address {}; data={}"
                            .format(rl_id, email, pretty_print.pformat(sf_dict)))
                dup_emails += 1
                continue
            found_emails.append(email)
        elif filter_email[:5] == 'valid':
            # ensure that also clients with clienthasnoemail@... will be uploaded to Salesforce if email not restricted
            continue

        phone = sf_dict['Phone']
        if phone in found_phones:
            add_log_msg("Res-id {:12} with duplicate phone number {}; data={}"
                        .format(rl_id, phone, pretty_print.pformat(sf_dict)))
            dup_phones += 1
            continue
        found_phones.append(phone)

        clients_to_mig.append(sf_dict)

    uprint("####  Migrating contacts to Salesforce")
    notification_lines.append("####  Migrating Sihot guest data to Salesforce")
    rec_type_id = sf_conn.record_type_id(CONTACT_REC_TYPE_RENTALS)
    clients_migrated = list()
    send_errors = 0
    for sf_dict in clients_to_mig:
        res_id = sf_dict[AI_SH_RL_ID]
        sh_pp_data = pretty_print.pformat(sf_dict)

        sf_id, sf_obj = sf_conn.find_client(sf_dict['Email'], sf_dict['Phone'], sf_dict['FirstName'],
                                            sf_dict['LastName'])
        if not sf_id:
            sf_id = sf_conn.client_id_by_email(sf_dict['Email'])
            if sf_id:
                sf_obj = 'Contact'
        if sf_id:
            sf_dict[AI_SF_ID] = sf_id
            existing_client_ids.append(sf_dict)
            sf_dict[AI_SF_CURR_DATA] = sf_conn.client_data_by_id(sf_id, strip_add_info_keys(sf_dict), sf_obj)
            if sf_conn.error_msg:
                notification_add_line("SF-FETCH-DATA-ERROR: '{}' of contact ID {}".format(sf_conn.error_msg, sf_id),
                                      is_error=True)

        sf_send = strip_add_info_from_sf_data(sf_dict, strip_populated_sf_fields=True, record_type_id=rec_type_id)
        if not sf_send:
            notification_add_line("Skipped Sihot Res-Id {:12} to be sent because of empty/unchanged Sihot guest data={}"
                                  .format(res_id, sh_pp_data))
            continue

        _, err_msg, log_msg = sf_conn.client_upsert(sf_send, sf_obj)
        if err_msg:
            send_errors += 1
            notification_add_line(("Error {} in {} of Sihot Res-Id {:12} with match score {:6.3}"
                                   " to Salesforce; sent data={}"
                                   + (" full data={full_data}" if debug_level >= DEBUG_LEVEL_VERBOSE else ""))
                                  .format(err_msg, "updating Contact " + sf_id if sf_id else "migrating",
                                          res_id, sf_dict[AI_SCORE], pretty_print.pformat(sf_send),
                                          full_data=sh_pp_data),
                                  is_error=True)
        else:
            clients_migrated.append(sf_dict)
        if log_msg:
            notification_add_line("Migrated Sihot Res-Id {:12} {} with match score {:6.3} to Salesforce; data={}, {}"
                                  .format(res_id, "updated Contact " + sf_id if sf_id else "migrated",
                                          sf_dict[AI_SCORE], sh_pp_data, log_msg))

    uprint(" ###  Sihot-Salesforce data mismatches (not updated in Salesforce) - UPSERT warnings:")
    for upsert_msg in ups_warnings:
        uprint("   #  ", upsert_msg)

    uprint()
    uprint("####  Migration Summary")
    uprint()
    valid_contact_count = len(valid_clients)
    mig_contact_count = valid_contact_count - dup_res - dup_emails - dup_phones - send_errors
    assert len(clients_migrated) == mig_contact_count
    notification_add_line("Duplicate {}/{}/{} res-ids/emails/phones and {} upload errors out of {} Sihot guests/clients"
                          .format(dup_res, dup_emails, dup_phones, send_errors, valid_contact_count))
    uprint("Found {} unique emails: {}".format(len(found_emails), found_emails))
    uprint("Found {} unique phone numbers: {}".format(len(found_phones), found_phones))
    uprint("Skipped {} duplicates of loaded reservation-rooming-ids: {}".format(dup_res, rooming_list_ids))
    uprint()
    uprint(" ###  Comparision of {} existing Sf contacts".format(len(existing_client_ids)))
    for sf_dict in existing_client_ids:
        ec = deepcopy(sf_dict)
        uprint("  ##  Sf-Id", ec[AI_SF_ID])
        uprint("      SF:", pprint.pformat(ec[AI_SF_CURR_DATA], indent=9, width=PP_DEF_WIDTH))
        ec.pop(AI_SF_CURR_DATA)
        uprint("      SH:", pprint.pformat(ec, indent=9, width=PP_DEF_WIDTH))

    uprint()
    uprint("####  ", mig_contact_count, "Contacts migrated:")
    contacts_notifications = list()
    contacts_notifications.append("####  {} MIGRATED CONTACTS ARRIVED {}:\n\n"
                                  .format(mig_contact_count, rbf.date_range_str()))
    layout_fields = ['RecordType.DeveloperName', 'FirstName', 'LastName', 'Birthdate', 'Email', 'Phone',
                     'Street', 'City', 'Country', 'Language', 'Description', 'ArrivalInfo']
    for sf_dict in clients_migrated:
        contact_layout = layout_message(sf_dict, layout_fields)
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
