"""
    0.1     first beta.
    0.2     refactored to use V_ACU_RES_UNSYNCED (including resort filter) and T_SRSL.
    0.3     added error counter to Progress, refactored lastId into LastRt and removed processed_A*.
"""
from datetime import datetime

from console_app import ConsoleApp, Progress, uprint
from notification import Notification
from db import DEF_USER, DEF_DSN
from sxmlif import ClientToSihot, ResToSihot, \
    SXML_DEF_ENCODING, ERR_MESSAGE_PREFIX_CONTINUE, \
    USE_KERNEL_FOR_CLIENTS_DEF, USE_KERNEL_FOR_RES_DEF, MAP_CLIENT_DEF, MAP_RES_DEF

__version__ = '0.3'

cae = ConsoleApp(__version__, "Synchronize reservation changes from Acumen/Oracle system to the SiHOT-PMS")
cae.add_option('acuUser', "User name of Acumen/Oracle system", DEF_USER, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", DEF_DSN, 'd')

cae.add_option('serverIP', "IP address of the SIHOT interface server", 'localhost', 'i')
cae.add_option('serverPort', "IP port of the WEB interface of this server", 14777, 'w')
cae.add_option('serverKernelPort', "IP port of the KERNEL interface of this server", 14772, 'k')

cae.add_option('timeout', "Timeout value for TCP/IP connections", 39.6)
cae.add_option('xmlEncoding', "Charset used for the xml data", SXML_DEF_ENCODING, 'e')

cae.add_option('useKernelForClient', "Used interface for clients (0=web, 1=kernel)", USE_KERNEL_FOR_CLIENTS_DEF, 'g')
cae.add_option('mapClient', "Guest/Client mapping of xml to db items", MAP_CLIENT_DEF, 'm')
cae.add_option('useKernelForRes', "Used interface for reservations (0=web, 1=kernel)", USE_KERNEL_FOR_RES_DEF, 'z')
cae.add_option('mapRes', "Reservation mapping of xml to db items", MAP_RES_DEF, 'n')

cae.add_option('clientsFirst', "Migrate first the clients then the reservations (0=No, 1=Yes)",
               0, 'q', choices=(0, 1, 2))
cae.add_option('breakOnError', "Abort synchronization if an error occurs (0=No, 1=Yes)", 0, 'b')

cae.add_option('smtpServerUri', "SMTP notification server account URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP sender/from address", '', 'f')
cae.add_option('smtpTo', "SMTP receiver/to addresses (and fallback if smtpToEval returns None/empty-list)", [], 'r')
cae.add_option('smtpToEval', "error and data specific eval expression resulting in list of notification receivers", '',
               'a')

cae.add_option('warningsMailToAddr', "Warnings SMTP receiver/to addresses (if differs from smtpTo)", [], 'v')


debug_level = cae.get_option('debugLevel')
uprint('Acumen Usr/DSN:', cae.get_option('acuUser'), cae.get_option('acuDSN'))
uprint('Server IP/Web-/Kernel-port:', cae.get_option('serverIP'), cae.get_option('serverPort'),
       cae.get_option('serverKernelPort'))
uprint('TCP Timeout/XML Encoding:', cae.get_option('timeout'), cae.get_option('xmlEncoding'))
uprint('Use Kernel for clients:', 'Yes' if cae.get_option('useKernelForClient') else 'No (WEB)')
uprint('Use Kernel for reservations:', 'Yes' if cae.get_option('useKernelForRes') else 'No (WEB)')
last_rt_prefix = cae.get_option('acuDSN')[-4:]
uprint('Last unfinished run (-1=all finished):  ', cae.get_config(last_rt_prefix + 'lastRt'))
uprint('Migrate Clients First/Separate:',
       ['No', 'Yes', 'Yes with client reservations'][int(cae.get_option('clientsFirst'))])
uprint('Break on error:', 'Yes' if cae.get_option('breakOnError') else 'No')
notification = mail_to_expr = None
if cae.get_option('smtpServerUri') and cae.get_option('smtpFrom') and cae.get_option('smtpTo'):
    notification = Notification(smtp_server_uri=cae.get_option('smtpServerUri'),
                                mail_from=cae.get_option('smtpFrom'),
                                mail_to=cae.get_option('smtpTo'),
                                used_system=cae.get_option('acuDSN') + '/' + cae.get_option('serverIP'),
                                debug_level=debug_level)
    uprint('SMTP Uri/From/To:', cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))
    if cae.get_option('smtpToEval'):
        mail_to_expr = cae.get_option('smtpToEval')
        uprint('SMTP To Evaluation Expression:', mail_to_expr)
    if cae.get_option('warningsMailToAddr'):
        uprint('Warnings SMTP receiver address:', cae.get_option('warningsMailToAddr'))

lastUnfinishedRunTime = cae.get_config(last_rt_prefix + 'lastRt')
if lastUnfinishedRunTime.startswith('@'):
    uprint("****  Synchronization process is still running from last batch, started at ", lastUnfinishedRunTime[1:])
    cae.shutdown(4)
error_msg = cae.set_config(last_rt_prefix + 'lastRt', '@' + str(datetime.now()))
if error_msg:
    uprint(error_msg)


def send_notification(what, sid, mail_body):
    global notification, mail_to_expr
    if not notification:
        return

    mail_to_addr_list = None
    if mail_to_expr:
        try:
            mail_to_addr_list = eval(mail_to_expr)      # crow[] for to check data and error_msg for to check error
        except Exception as ex:
            uprint(" **** SihotResSync.send_notification() exception '" + str(ex) +
                   "' on evaluating of '" + str(mail_to_expr) + "' with error_msg='" + error_msg + "' and crow='" +
                   str(crow) + "'.")
    send_err = notification.send_notification(mail_body, subject='SihotResSync notification ' + what + ' ' + sid,
                                              mail_to=mail_to_addr_list)
    if send_err:
        uprint(" **** SihotResSync " + what
               + " send notification error: {}. Unsent ID='{}' error message: {}.".format(send_err, sid, error_msg))


if cae.get_option('clientsFirst'):
    uprint("####  Sync CD Changes....  ####")

    acumen_cd = ClientToSihot(cae, use_kernel_interface=cae.get_option('useKernelForClient'),
                              map_client=cae.get_option('mapClient'))
    error_msg = acumen_cd.fetch_from_acu_by_acu()
    progress = Progress(debug_level, start_counter=acumen_cd.row_count,
                        start_msg='Prepare sending of {run_counter} client detail changes to Sihot',
                        nothing_to_do_msg='SihotResSync: acumen client fetch returning no rows')
    if not error_msg:
        for crow in acumen_cd.rows:
            error_msg = acumen_cd.send_client_to_sihot(crow)
            cid = crow['CD_CODE'] + '/' + str(crow['CDL_CODE'])
            progress.next(processed_id=cid, error_msg=error_msg)
            if error_msg:
                acumen_cd.ora_db.rollback()
                send_notification('Acumen Client', cid, error_msg)
            else:
                error_msg = acumen_cd.ora_db.commit()
            if error_msg:
                if error_msg.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                    continue            # currently not used/returned-by-send_client_to_sihot()
                elif cae.get_option('breakOnError'):
                    break

    progress.finished(error_msg=error_msg)


if not error_msg:
    uprint("####  Sync Req/ARU Changes ####")

    acumen_req = ResToSihot(cae, use_kernel_interface=cae.get_option('useKernelForRes'),
                            map_res=cae.get_option('mapRes'),
                            use_kernel_for_new_clients=cae.get_option('useKernelForClient'),
                            map_client=cae.get_option('mapClient'))
    error_msg = acumen_req.fetch_from_acu_by_aru()
    progress = Progress(debug_level, start_counter=acumen_req.row_count,
                        start_msg=" ###  Prepare sending of {total_count} reservations to Sihot",
                        nothing_to_do_msg=" ***  SihotResSync: acumen reservation fetch returning no rows")
    if not error_msg:
        for crow in acumen_req.rows:
            error_msg = acumen_req.send_row_to_sihot(crow)
            rid = acumen_req.res_id_values(crow)
            progress.next(processed_id=rid, error_msg=error_msg)
            if error_msg:
                acumen_req.ora_db.rollback()
                send_notification('Acumen Reservation', rid, acumen_req.res_id_desc(crow, error_msg))
            else:
                error_msg = acumen_req.ora_db.commit()
            if error_msg:
                if error_msg.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                    continue
                elif cae.get_option('breakOnError'):
                    break

        warnings = acumen_req.get_warnings()
        if notification and warnings:
            mail_to = cae.get_option('warningsMailToAddr')
            notification.send_notification(warnings, subject='SihotResSync warnings notification', mail_to=mail_to)

    progress.finished(error_msg=error_msg)

# release dup exec lock
set_opt_err = cae.set_config(last_rt_prefix + 'lastRt', str(-1))

cae.shutdown(13 if set_opt_err else (12 if error_msg else 0))
