from ae_console_app import ConsoleApp, DEBUG_LEVEL_VERBOSE, uprint
from ae_contact_validation import EmailValidator, PhoneValidator, AddressValidator
from ae_notification import Notification
from sfif import prepare_connection

__version__ = '0.1'

cae = ConsoleApp(__version__, "Salesforce Contact Validator", debug_level_def=DEBUG_LEVEL_VERBOSE)

cae.add_option('smtpServerUri', "SMTP notification server account URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP sender/from address", '', 'f')
cae.add_option('smtpTo', "List/Expression of SMTP receiver/to addresses", [], 'r')

cae.add_option('warningsMailToAddr', "Warnings SMTP receiver/to addresses (if differs from smtpTo)", [], 'v')


sf_conn, sf_sandbox = prepare_connection(cae, client_id='SfContactValidator',
                                         use_production=cae.get_option('useSfProduction'), print_on_console=True)

email_validator = EmailValidator(cae.get_config('emailValidatorBaseUrl'), cae.get_config('emailValidatorApiKey'))
phone_validator = PhoneValidator(cae.get_config('phoneValidatorBaseUrl'), cae.get_config('phoneValidatorApiKey'))
addr_validator = AddressValidator(cae.get_config('addressValidatorBaseUrl'), cae.get_config('addressValidatorApiKey'),
                                  auto_complete_search_url=cae.get_config('addressValidatorSearchUrl'),
                                  auto_complete_fetch_url=cae.get_config('addressValidatorFetchUrl'))


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


log_items = []              # log entries with warnings and errors
log_errors = []             # errors only (send to warningsMailToAddr)


def add_log_msg(msg, is_error=False):
    global log_errors, log_items
    if is_error:
        log_errors.append(msg)
    msg = ("  **  " if is_error else "  ##  ") + msg
    log_items.append(msg)
    uprint(msg)


# fetch rental Contacts migrated with ShSfContactMigration app for to validate email address and phone numbers
contacts = sf_conn.contacts_not_validated(rec_type_dev_name='Rentals', validate_phone=True)
add_log_msg("Found {} not fully validated contacts".format(len(contacts)))
for rec in contacts:
    cae.dprint("Validating Contact", rec)
    if 'Email' in rec and rec['Email'] and rec['CD_email_valid__c'] is None:
        err_msg = email_validator.validate(rec['Email'])
        if err_msg:
            rec['CD_email_valid__c'] = '0'
            add_log_msg("{Id} email {Email} is invalid. Reason={err_msg}".format(err_msg=err_msg, **rec), is_error=True)
        else:
            rec['CD_email_valid__c'] = '1'
    if 'HomePhone' in rec and rec['HomePhone'] and rec['CD_Htel_valid__c'] is None:
        corr = dict()
        err_msg = phone_validator.validate(rec['HomePhone'], country_code=rec['Country__c'], ret_val_dict=corr)
        if err_msg:
            rec['CD_Htel_valid__c'] = '0'
            add_log_msg("{Id} home phone {HomePhone} is invalid. Reason={err_msg}".format(err_msg=err_msg, **rec),
                        is_error=True)
        else:
            rec['CD_Htel_valid__c'] = '1'
            if rec['HomePhone'] != corr['formatinternational']:
                add_log_msg("{Id} home phone {HomePhone} correcting to {formatinternational}".format(**rec, **corr))
                rec['HomePhone'] = corr['formatinternational']
            if rec['Country__c'] != corr['countrycode']:
                add_log_msg("{Id} country code {Country__c} correcting to {countrycode}".format(**rec, **corr))
                rec['Country__c'] = corr['countrycode']
    if 'MobilePhone' in rec and rec['MobilePhone'] and rec['CD_mtel_valid__c'] is None:
        err_msg = phone_validator.validate(rec['MobilePhone'], country_code=rec['Country__c'])
        if err_msg:
            rec['CD_mtel_valid__c'] = '0'
            add_log_msg("{Id} home phone {MobilePhone} is invalid. Reason={err_msg}".format(err_msg=err_msg, **rec),
                        is_error=True)
        else:
            rec['CD_mtel_valid__c'] = '1'
            if rec['MobilePhone'] != corr['formatinternational']:
                add_log_msg("{Id} mobile phone {MobilePhone} correcting to {formatinternational}".format(**rec, **corr))
                rec['MobilePhone'] = corr['formatinternational']
            if rec['Country__c'] != corr['countrycode']:
                add_log_msg("{Id} country code {Country__c} correcting to {countrycode}".format(**rec, **corr))
                rec['Country__c'] = corr['countrycode']
    if 'Work_Phone__c' in rec and rec['Work_Phone__c'] and rec['CD_wtel_valid__c'] is None:
        err_msg = phone_validator.validate(rec['Work_Phone__c'], country_code=rec['Country__c'])
        if err_msg:
            rec['CD_wtel_valid__c'] = '0'
            add_log_msg("{Id} home phone {Work_Phone__c} is invalid. Reason={err_msg}".format(err_msg=err_msg, **rec),
                        is_error=True)
        else:
            rec['CD_wtel_valid__c'] = '1'
            if rec['Work_Phone__c'] != corr['formatinternational']:
                add_log_msg("{Id} work phone {Work_Phone__c} correcting to {formatinternational}".format(**rec, **corr))
                rec['Work_Phone__c'] = corr['formatinternational']
            if rec['Country__c'] != corr['countrycode']:
                add_log_msg("{Id} country code {Country__c} correcting to {countrycode}".format(**rec, **corr))
                rec['Country__c'] = corr['countrycode']

    err_msg, log_msg = sf_conn.contact_upsert(rec)
    if err_msg:
        add_log_msg(err_msg, is_error=True)
    if log_msg:
        cae.dprint(log_msg)


if notification:
    subject = "Sihot Salesforce Contact Migration protocol" + (" (sandbox/test system)" if sf_sandbox else "")
    mail_body = "\n".join(log_items)
    send_err = notification.send_notification(mail_body, subject=subject)
    if send_err:
        uprint("****  " + subject + " send error: {}. mail-body='{}'.".format(send_err, mail_body))
        cae.shutdown(36)
    if warning_notification_emails and log_errors:
        mail_body = "\n".join(log_errors)
        subject = "Sihot Salesforce Contact Migration errors/discrepancies" + (" (sandbox)" if sf_sandbox else "")
        send_err = notification.send_notification(mail_body, subject=subject, mail_to=warning_notification_emails)
        if send_err:
            uprint("****  " + subject + " send error: {}. mail-body='{}'.".format(send_err, mail_body))
            cae.shutdown(39)

if log_errors:
    cae.shutdown(42)

cae.shutdown()
