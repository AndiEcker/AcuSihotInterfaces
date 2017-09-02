"""
    SfContactValidator is a tool for to validate email address, phone numbers and post address of Salesforce Contacts

    0.1     first beta.
"""
from ae_console_app import ConsoleApp, DEBUG_LEVEL_VERBOSE, uprint
from ae_contact_validation import EmailValidator, PhoneValidator, AddressValidator
from ae_notification import Notification
from sfif import prepare_connection, validate_flag_info, CONTACT_REC_TYPE_RENTALS, \
    EMAIL_DO_NOT_VALIDATE, EMAIL_NOT_VALIDATED, EMAIL_INVALIDATED, EMAIL_INVALID, EMAIL_VALID, EMAIL_ALL, \
    PHONE_DO_NOT_VALIDATE, PHONE_NOT_VALIDATED, PHONE_INVALIDATED, PHONE_INVALID, PHONE_VALID, PHONE_ALL, \
    ADDR_DO_NOT_VALIDATE, ADDR_NOT_VALIDATED, ADDR_INVALIDATED, ADDR_INVALID, ADDR_VALID, ADDR_ALL

__version__ = '0.2'

cae = ConsoleApp(__version__, "Salesforce Contact Data Validator", debug_level_def=DEBUG_LEVEL_VERBOSE)

cae.add_option('sfUser', "Salesforce account user name", '', 'y')
cae.add_option('sfPassword', "Salesforce account user password", '', 'a')
cae.add_option('sfToken', "Salesforce account token string", '', 'o')
cae.add_option('sfClientId', "Salesforce client/application name/id", cae.app_name(), 'C')
cae.add_option('sfIsSandbox', "Use Salesforce sandbox (instead of production)", True, 's')

cae.add_option('smtpServerUri', "SMTP notification server account URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP sender/from address", '', 'f')
cae.add_option('smtpTo', "List/Expression of SMTP receiver/to addresses", list(), 'r')

cae.add_option('warningsMailToAddr', "Warnings SMTP receiver/to addresses (if differs from smtpTo)", list(), 'v')

cae.add_option('recordTypesToValidate', "Contact record type(s) to be validated", "'" + CONTACT_REC_TYPE_RENTALS + "'",
               'R')
cae.add_option('additionalContactFilter', "Additional WHERE filter clause for Contact SOQL query", "", 'W')

cae.add_option('emailsToValidate', "Emails to be validated", EMAIL_NOT_VALIDATED, 'E',
               choices=(EMAIL_DO_NOT_VALIDATE, EMAIL_NOT_VALIDATED, EMAIL_INVALIDATED, EMAIL_INVALID, EMAIL_VALID,
                        EMAIL_ALL))
cae.add_option('phonesToValidate', "Phones to be validated", PHONE_NOT_VALIDATED, 'P',
               choices=(PHONE_DO_NOT_VALIDATE, PHONE_NOT_VALIDATED, PHONE_INVALIDATED, PHONE_INVALID, PHONE_VALID,
                        PHONE_ALL))
cae.add_option('addressesToValidate', "Post addresses to be validated", ADDR_DO_NOT_VALIDATE, 'A',
               choices=(ADDR_DO_NOT_VALIDATE, ADDR_NOT_VALIDATED, ADDR_INVALIDATED, ADDR_INVALID, ADDR_VALID, ADDR_ALL))


invalid_email_fragments = cae.get_config('InvalidEmailFragments', default_value=list())
uprint("Configured fragments for to detect invalid email address:", invalid_email_fragments)

sf_conn, sf_sandbox = prepare_connection(cae)
if not sf_conn:
    uprint("Salesforce account connection could not be established - please check your account data and credentials")
    cae.shutdown(20)

rec_types_to_validate = cae.get_option('recordTypesToValidate')
additional_contact_filter = cae.get_option('additionalContactFilter')
uprint("Contact filter:" + ((", RecordType(s)=" + rec_types_to_validate if rec_types_to_validate else "")
                            + (", Extra Filter=" + additional_contact_filter if additional_contact_filter else ""))[2:])

email_validator = phone_validator = addr_validator = None
email_validation = cae.get_option('emailsToValidate')
api_key = cae.get_config('emailValidatorApiKey')
if api_key:
    email_validator = EmailValidator(cae.get_config('emailValidatorBaseUrl'), api_key)
elif email_validation != EMAIL_DO_NOT_VALIDATE:
    uprint("SfContactValidator email validation configuration error: api key is missing")
    cae.shutdown(3)
phone_validation = cae.get_option('phonesToValidate')
api_key = cae.get_config('phoneValidatorApiKey')
if api_key:
    phone_validator = PhoneValidator(cae.get_config('phoneValidatorBaseUrl'), api_key)
elif phone_validation != PHONE_DO_NOT_VALIDATE:
    uprint("SfContactValidator phone validation configuration error: api key is missing")
    cae.shutdown(6)
addr_validation = cae.get_option('addressesToValidate')
api_key = cae.get_config('addressValidatorApiKey')
if api_key:
    addr_validator = AddressValidator(cae.get_config('addressValidatorBaseUrl'), api_key,
                                      auto_complete_search_url=cae.get_config('addressValidatorSearchUrl'),
                                      auto_complete_fetch_url=cae.get_config('addressValidatorFetchUrl'))
elif addr_validation != ADDR_DO_NOT_VALIDATE:
    uprint("SfContactValidator address validation configuration error: api key is missing")
    cae.shutdown(9)


notification = warning_notification_emails = None
if cae.get_option('smtpServerUri') and cae.get_option('smtpFrom') and cae.get_option('smtpTo'):
    notification = Notification(smtp_server_uri=cae.get_option('smtpServerUri'),
                                mail_from=cae.get_option('smtpFrom'),
                                mail_to=cae.get_option('smtpTo'),
                                used_system="Salesforce " + ("sandbox" if sf_sandbox else "production"),
                                debug_level=cae.get_option('debugLevel'))
    uprint("SMTP Uri/From/To:", cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))
    warning_notification_emails = cae.get_option('warningsMailToAddr')
    if warning_notification_emails:
        uprint("Warnings SMTP receiver address(es):", warning_notification_emails)


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


# fetch rental Contacts migrated with ShSfContactMigration app for to validate email address and phone numbers
contacts = sf_conn.contacts_to_validate(rec_type_dev_names=rec_types_to_validate,
                                        additional_filter=additional_contact_filter,
                                        email_validation=email_validation,
                                        phone_validation=phone_validation,
                                        addr_validation=addr_validation)
add_log_msg("Validating {} contacts, checking email={}, phone={}, address={}"
            .format(len(contacts), validate_flag_info(email_validation), validate_flag_info(phone_validation),
                    validate_flag_info(addr_validation)),
            importance=4)
emails_validated = phones_validated = addresses_validated = contacts_updated = 0
for rec in contacts:
    cae.dprint("Checking Contact for needed validation", rec)
    update_in_sf = False
    if email_validator and 'Email' in rec and rec['Email'] and email_validation != EMAIL_DO_NOT_VALIDATE \
            and eval("rec['CD_email_valid__c'] in (" + email_validation.replace('NULL', 'None') + ",)"):
        for frag in invalid_email_fragments:
            if frag in rec['Email']:
                add_log_msg("{Id} email {Email} skipped because contains fragment {frag}.".format(frag=frag, **rec))
                break
        else:
            if ' ' in rec['Email']:
                rec['Email'] = rec['Email'].replace(' ', '')
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
    if phone_validator and 'HomePhone' in rec and rec['HomePhone'] and phone_validation != PHONE_DO_NOT_VALIDATE \
            and eval("rec['CD_Htel_valid__c'] in (" + phone_validation.replace('NULL', 'None') + ",)"):
        corr = dict()
        if ' ' in rec['HomePhone']:
            rec['HomePhone'] = rec['HomePhone'].replace(' ', '')
            update_in_sf = True
        err_msg = phone_validator.validate(rec['HomePhone'], country_code=rec['Country__c'], ret_val_dict=corr)
        validation_flag = rec['CD_Htel_valid__c']
        if err_msg:
            validation_flag = '0'
            add_log_msg("{Id} home phone {HomePhone} is invalid (in {Country__c}). Reason={err_msg}"
                        .format(err_msg=err_msg, **rec), is_error=True)
        else:
            validation_flag = '1'
            add_log_msg("{Id} homephone {HomePhone} is valid.".format(**rec))
            if 'formatinternational' in corr and corr['formatinternational']:
                if rec['HomePhone'] != corr['formatinternational']:
                    add_log_msg("{Id} home phone {HomePhone} correcting to {formatinternational}".format(**rec, **corr))
                    rec['HomePhone'] = corr['formatinternational']
                    update_in_sf = True
            elif 'formatnational' in corr and corr['formatnational']:
                if rec['HomePhone'] != corr['formatnational']:
                    add_log_msg("{Id} home phone {HomePhone} correcting to {formatnational}".format(**rec, **corr))
                    rec['HomePhone'] = corr['formatnational']
                    update_in_sf = True
            if 'countrycode' in corr and corr['countrycode']:
                if rec['Country__c'] != corr['countrycode']:
                    add_log_msg("{Id} country code {Country__c} correcting to {countrycode}".format(**rec, **corr))
                    rec['Country__c'] = corr['countrycode']
                    update_in_sf = True
        update_in_sf = update_in_sf or validation_flag != rec['CD_Htel_valid__c']
        rec['CD_Htel_valid__c'] = validation_flag
        phones_validated += 1
    if phone_validator and 'MobilePhone' in rec and rec['MobilePhone'] and phone_validation != PHONE_DO_NOT_VALIDATE \
            and eval("rec['CD_mtel_valid__c'] in (" + phone_validation.replace('NULL', 'None') + ",)"):
        corr = dict()
        if ' ' in rec['MobilePhone']:
            rec['MobilePhone'] = rec['MobilePhone'].replace(' ', '')
            update_in_sf = True
        err_msg = phone_validator.validate(rec['MobilePhone'], country_code=rec['Country__c'], ret_val_dict=corr)
        validation_flag = rec['CD_mtel_valid__c']
        if err_msg:
            validation_flag = '0'
            add_log_msg("{Id} mobile phone {MobilePhone} is invalid (in {Country__c}). Reason={err_msg}"
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
                if rec['Country__c'] != corr['countrycode']:
                    add_log_msg("{Id} country code {Country__c} correcting to {countrycode}".format(**rec, **corr))
                    rec['Country__c'] = corr['countrycode']
                    update_in_sf = True
        update_in_sf = update_in_sf or validation_flag != rec['CD_mtel_valid__c']
        rec['CD_mtel_valid__c'] = validation_flag
        phones_validated += 1
    if phone_validator and 'Work_Phone__c' in rec and rec['Work_Phone__c'] \
            and phone_validation != PHONE_DO_NOT_VALIDATE \
            and eval("rec['CD_wtel_valid__c'] in (" + phone_validation.replace('NULL', 'None') + ",)"):
        corr = dict()
        if ' ' in rec['Work_Phone__c']:
            rec['Work_Phone__c'] = rec['Work_Phone__c'].replace(' ', '')
            update_in_sf = True
        err_msg = phone_validator.validate(rec['Work_Phone__c'], country_code=rec['Country__c'], ret_val_dict=corr)
        validation_flag = rec['CD_wtel_valid__c']
        if err_msg:
            validation_flag = '0'
            add_log_msg("{Id} work phone {Work_Phone__c} is invalid (in {Country__c}). Reason={err_msg}"
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
                if rec['Country__c'] != corr['countrycode']:
                    add_log_msg("{Id} country code {Country__c} correcting to {countrycode}".format(**rec, **corr))
                    rec['Country__c'] = corr['countrycode']
                    update_in_sf = True
        update_in_sf = update_in_sf or validation_flag != rec['CD_wtel_valid__c']
        rec['CD_wtel_valid__c'] = validation_flag
        phones_validated += 1

    if update_in_sf:
        err_msg, log_msg = sf_conn.contact_upsert(rec)
        if err_msg:
            add_log_msg(err_msg, is_error=True)
        else:
            contacts_updated += 1
        if log_msg:
            add_log_msg(log_msg)


add_log_msg("Updated {} of {} contacts having {} errors while validating emails={}, phones={}, addresses={}"
            .format(contacts_updated, len(contacts), len(log_errors), emails_validated, phones_validated,
                    addresses_validated),
            importance=4)

if notification:
    subject = "Salesforce Contact Validation protocol" + (" (sandbox/test system)" if sf_sandbox else "")
    mail_body = "\n\n".join(log_items)
    send_err = notification.send_notification(mail_body, subject=subject)
    if send_err:
        uprint("****  " + subject + " send error: {}. mail-body='{}'.".format(send_err, mail_body))
        cae.shutdown(36)
    if warning_notification_emails and log_errors:
        mail_body = "\n\n".join(log_errors)
        subject = "Salesforce Contact Validation errors/discrepancies" + (" (sandbox)" if sf_sandbox else "")
        send_err = notification.send_notification(mail_body, subject=subject, mail_to=warning_notification_emails)
        if send_err:
            uprint("****  " + subject + " send error: {}. mail-body='{}'.".format(send_err, mail_body))
            cae.shutdown(39)

cae.shutdown(42 if log_errors else 0)
