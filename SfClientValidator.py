"""
    SfClientValidator is a tool for to validate email address, phone numbers and post address of Salesforce clients

    0.1     first beta.
    0.2     refactored for to use validation also in ShSfClientMigration.py and renamed from SfContactValidator to
            SfClientValidator.
"""
import pprint

from ae_console_app import ConsoleApp, uprint
from ae_notification import add_notification_options, init_notification
from sfif import add_sf_options
from ass_sys_data import correct_email, correct_phone, AssSysData
from ae_client_validation import (add_validation_options, init_validation, clients_to_validate,
                                  EMAIL_NOT_VALIDATED, PHONE_NOT_VALIDATED)

__version__ = '0.2'

cae = ConsoleApp(__version__, "Salesforce Client Data Validator")

add_validation_options(cae, email_def=EMAIL_NOT_VALIDATED, phone_def=PHONE_NOT_VALIDATED)
add_sf_options(cae)
add_notification_options(cae)


email_validation, email_validator, \
    phone_validation, phone_validator, \
    addr_validation, addr_validator, \
    filter_sf_clients, filter_sf_rec_types, filter_email, \
    default_email_address, invalid_email_fragments, ignore_case_fields, changeable_fields = init_validation(cae)


conf_data = AssSysData(cae)
if conf_data.error_message:
    uprint("AssSysData initialization error: " + conf_data.error_message)
    cae.shutdown(20)

notification, warning_notification_emails = init_notification(cae, "SF " + ("sdbx" if conf_data.sf_sandbox else "prod"))


log_items = list()              # log entries with warnings and errors
log_errors = list()             # errors only (send to warningsMailToAddr)


def add_log_msg(msg, is_error=False, importance=2):
    global log_errors, log_items
    assert 0 < importance < 5
    if is_error:
        log_errors.append(msg)
    msg = " " * (4 - importance) + ("*" if is_error else "#") * importance + "  " + msg
    log_items.append(msg)
    uprint(msg)


# fetch rental clients migrated with ShSfClientMigration app for to validate email address and phone numbers
clients = clients_to_validate(conf_data.sf_conn,
                              filter_sf_clients=filter_sf_clients,
                              filter_sf_rec_types=filter_sf_rec_types,
                              email_validation=email_validation,
                              phone_validation=phone_validation,
                              addr_validation=addr_validation)
add_log_msg("Validating {} clients".format(len(clients)), importance=4)
emails_validated = phones_validated = addresses_validated = clients_updated = 0
skipped_email_ids = dict()
for rec in clients:
    cae.dprint("Checking Client for needed validation", rec)
    update_in_sf = False
    if email_validator and 'Email' in rec and rec['Email'] \
            and eval("rec['CD_email_valid__c'] in (" + email_validation.replace('NULL', 'None') + ",)"):
        for frag in invalid_email_fragments:
            if frag in rec['Email']:
                if frag not in skipped_email_ids:
                    skipped_email_ids[frag] = list()
                skipped_email_ids[frag].append(rec['Id'])
                break
        else:
            email_changes = list()
            rec['Email'], email_changed = correct_email(rec['Email'], changed=False, removed=email_changes)
            if email_changed:
                add_log_msg("{Id} email {Email} corrected; removed 'index:char'={chg}".format(chg=email_changes, **rec))
                update_in_sf = True
            err_msg = email_validator.validate(rec['Email'])
            validation_flag = rec['CD_email_valid__c']
            if not err_msg:
                validation_flag = '1'
                add_log_msg("{Id} email {Email} is valid.".format(**rec))
            elif "'status': 114" in err_msg or "'status': 118" in err_msg:
                validation_flag = None
                add_log_msg("{Id} email {Email} validation timed out. Error={err_msg}".format(err_msg=err_msg, **rec))
            else:
                validation_flag = '0'
                add_log_msg("{Id} email {Email} is invalid. Reason={err_msg}"
                            .format(err_msg=err_msg, **rec), is_error=True)
            update_in_sf = update_in_sf or validation_flag != rec['CD_email_valid__c']
            rec['CD_email_valid__c'] = validation_flag
        emails_validated += 1
    if phone_validator and 'Phone' in rec and rec['Phone'] \
            and eval("rec['CD_Htel_valid__c'] in (" + phone_validation.replace('NULL', 'None') + ",)"):
        phone_changes = list()
        rec['Phone'], phone_changed = correct_phone(rec['Phone'], changed=False, removed=phone_changes)
        if phone_changed:
            add_log_msg("{Id} phone {Phone} corrected; removed 'index:char'={chg}"
                        .format(chg=phone_changes, **rec))
            update_in_sf = True
        corr = dict()
        err_msg = phone_validator.validate(rec['Phone'], country_code=rec['Country'], ret_val_dict=corr)
        validation_flag = rec['CD_Htel_valid__c']
        if err_msg:
            validation_flag = '0'
            add_log_msg("{Id} phone {Phone} is invalid. Reason={err_msg}"
                        .format(err_msg=err_msg, **rec), is_error=True)
        else:
            validation_flag = '1'
            add_log_msg("{Id} phone {Phone} is valid.".format(**rec))
            if 'formatinternational' in corr and corr['formatinternational']:
                if rec['Phone'] != corr['formatinternational']:
                    add_log_msg("{Id} phone {Phone} correcting to {formatinternational}".format(**rec, **corr))
                    rec['Phone'] = corr['formatinternational']
                    update_in_sf = True
            elif 'formatnational' in corr and corr['formatnational']:
                if rec['Phone'] != corr['formatnational']:
                    add_log_msg("{Id} phone {Phone} correcting to {formatnational}".format(**rec, **corr))
                    rec['Phone'] = corr['formatnational']
                    update_in_sf = True
            if 'countrycode' in corr and corr['countrycode']:
                if rec['Country'] != corr['countrycode']:
                    add_log_msg("{Id} country code {Country} correcting to {countrycode}".format(**rec, **corr))
                    rec['Country'] = corr['countrycode']
                    update_in_sf = True
        update_in_sf = update_in_sf or validation_flag != rec['CD_Htel_valid__c']
        rec['CD_Htel_valid__c'] = validation_flag
        phones_validated += 1
    if phone_validator and 'MobilePhone' in rec and rec['MobilePhone'] \
            and eval("rec['CD_mtel_valid__c'] in (" + phone_validation.replace('NULL', 'None') + ",)"):
        phone_changes = list()
        rec['MobilePhone'], phone_changed = correct_phone(rec['MobilePhone'], changed=False, removed=phone_changes)
        if phone_changed:
            add_log_msg("{Id} mobile phone {MobilePhone} corrected; removed 'index:char'={chg}"
                        .format(chg=phone_changes, **rec))
            update_in_sf = True
        corr = dict()
        err_msg = phone_validator.validate(rec['MobilePhone'], country_code=rec['Country'], ret_val_dict=corr)
        validation_flag = rec['CD_mtel_valid__c']
        if err_msg:
            validation_flag = '0'
            add_log_msg("{Id} mobile phone {MobilePhone} is invalid. Reason={err_msg}"
                        .format(err_msg=err_msg, **rec), is_error=True)
        else:
            validation_flag = '1'
            add_log_msg("{Id} mobile phone {MobilePhone} is valid.".format(**rec))
            if 'formatinternational' in corr and corr['formatinternational']:
                if rec['MobilePhone'] != corr['formatinternational']:
                    add_log_msg("{Id} mobile phone {MobilePhone} correcting to {formatinternational}"
                                .format(**rec, **corr))
                    rec['MobilePhone'] = corr['formatinternational']
                    update_in_sf = True
            elif 'formatnational' in corr and corr['formatnational']:
                if rec['MobilePhone'] != corr['formatnational']:
                    add_log_msg("{Id} mobile phone {MobilePhone} correcting to {formatnational}".format(**rec, **corr))
                    rec['MobilePhone'] = corr['formatnational']
                    update_in_sf = True
            if 'countrycode' in corr and corr['countrycode']:
                if rec['Country'] != corr['countrycode']:
                    add_log_msg("{Id} country code {Country} correcting to {countrycode}".format(**rec, **corr))
                    rec['Country'] = corr['countrycode']
                    update_in_sf = True
        update_in_sf = update_in_sf or validation_flag != rec['CD_mtel_valid__c']
        rec['CD_mtel_valid__c'] = validation_flag
        phones_validated += 1
    if phone_validator and 'Work_Phone__c' in rec and rec['Work_Phone__c'] \
            and eval("rec['CD_wtel_valid__c'] in (" + phone_validation.replace('NULL', 'None') + ",)"):
        phone_changes = list()
        rec['Work_Phone__c'], phone_changed = correct_phone(rec['Work_Phone__c'], changed=False, removed=phone_changes)
        if phone_changed:
            add_log_msg("{Id} work phone {Work_Phone__c} corrected; removed 'index:char'={chg}"
                        .format(chg=phone_changes, **rec))
            update_in_sf = True
        corr = dict()
        err_msg = phone_validator.validate(rec['Work_Phone__c'], country_code=rec['Country'], ret_val_dict=corr,
                                           try_alternative_country=False)
        validation_flag = rec['CD_wtel_valid__c']
        if err_msg:
            validation_flag = '0'
            add_log_msg("{Id} work phone {Work_Phone__c} is invalid. Reason={err_msg}"
                        .format(err_msg=err_msg, **rec), is_error=True)
        else:
            validation_flag = '1'
            add_log_msg("{Id} work phone {Work_Phone__c} is valid.".format(**rec))
            if 'formatinternational' in corr and corr['formatinternational']:
                if rec['Work_Phone__c'] != corr['formatinternational']:
                    add_log_msg("{Id} work phone {Work_Phone__c} correcting to {formatinternational}"
                                .format(**rec, **corr))
                    rec['Work_Phone__c'] = corr['formatinternational']
                    update_in_sf = True
            elif 'formatnational' in corr and corr['formatnational']:
                if rec['Work_Phone__c'] != corr['formatnational']:
                    add_log_msg("{Id} work phone {Work_Phone__c} correcting to {formatnational}".format(**rec, **corr))
                    rec['Work_Phone__c'] = corr['formatnational']
                    update_in_sf = True
            if 'countrycode' in corr and corr['countrycode']:
                if rec['Country'] != corr['countrycode']:
                    add_log_msg("{Id} country code {Country} correcting to {countrycode}".format(**rec, **corr))
                    rec['Country'] = corr['countrycode']
                    update_in_sf = True
        update_in_sf = update_in_sf or validation_flag != rec['CD_wtel_valid__c']
        rec['CD_wtel_valid__c'] = validation_flag
        phones_validated += 1

    if update_in_sf:
        _, err_msg, log_msg = conf_data.sf_client_upsert(rec)
        if err_msg:
            add_log_msg(err_msg, is_error=True)
        else:
            clients_updated += 1
        if log_msg:
            add_log_msg(log_msg)


add_log_msg("Updated {} of {} clients having {} errors while validating emails={}, phones={}, addresses={}"
            .format(clients_updated, len(clients), len(log_errors), emails_validated, phones_validated,
                    addresses_validated),
            importance=4)

if skipped_email_ids:
    for frag, id_list in skipped_email_ids.items():
        add_log_msg("{} Emails skipped because contains fragment {} in Salesforce Ids: {}"
                    .format(len(id_list), frag, pprint.pformat(id_list, indent=9, compact=True)))

if notification:
    subject = "Salesforce Client Validation protocol" + (" (sandbox/test system)" if conf_data.sf_sandbox else "")
    mail_body = "\n\n".join(log_items)
    send_err = notification.send_notification(mail_body, subject=subject)
    if send_err:
        uprint("****  " + subject + " send error: {}. mail-body='{}'.".format(send_err, mail_body))
        cae.shutdown(36)
    if warning_notification_emails and log_errors:
        mail_body = "\n\n".join(log_errors)
        subject = "Salesforce Client Validation errors/discrepancies" + (" (sandbox)" if conf_data.sf_sandbox else "")
        send_err = notification.send_notification(mail_body, subject=subject, mail_to=warning_notification_emails)
        if send_err:
            uprint("****  " + subject + " send error: {}. mail-body='{}'.".format(send_err, mail_body))
            cae.shutdown(39)

cae.shutdown(42 if log_errors else 0)
