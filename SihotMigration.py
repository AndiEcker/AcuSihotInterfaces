"""
    0.1     first beta.
    0.2     refactored to use V_ACU_RES_UNSYNCED (including resort filter) and T_SRSL.
    0.3     added error counter to Progress
"""

from ae_console_app import ConsoleApp, Progress, uprint
from ae_db import DEF_USER, DEF_DSN
from sxmlif import ClientToSihot, ResToSihot, SXML_DEF_ENCODING, ERR_MESSAGE_PREFIX_CONTINUE

__version__ = '0.3'

cae = ConsoleApp(__version__, "Migrate all guest/reservation data from Acumen/Oracle system to the SiHOT-PMS")
cae.add_option('serverIP', "IP address of the SIHOT interface server", 'localhost', 'i')
cae.add_option('serverPort', "IP port of the WEB interface of this server", 14777, 'w')
cae.add_option('serverKernelPort', "IP port of the KERNEL interface of this server", 14772, 'k')

cae.add_option('timeout', "Timeout value for TCP/IP connections", 69.3)
cae.add_option('xmlEncoding', "Charset used for the xml data", SXML_DEF_ENCODING, 'e')

cae.add_option('acuUser', "User name of Acumen/Oracle system", DEF_USER, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", DEF_DSN, 'd')

cae.add_option('resHistory', "Migrate also the clients reservation history (0=No, 1=Yes)", 1, 'R', choices=(0, 1))
cae.add_option('clientsFirst', "Migrate first the clients then the reservations (0=No, 1=Yes)",
               0, 'q', choices=(0, 1, 2))
cae.add_option('breakOnError', "Abort migration if error occurs (0=No, 1=Yes)", 1, 'b', choices=(0, 1))

future_only = not cae.get_option('resHistory')
break_on_error = cae.get_option('breakOnError')

uprint('Server IP/Web-/Kernel-port:', cae.get_option('serverIP'), cae.get_option('serverPort'),
       cae.get_option('serverKernelPort'))
uprint('TCP Timeout/XML Encoding:', cae.get_option('timeout'), cae.get_option('xmlEncoding'))
uprint('Acumen Usr/DSN:', cae.get_option('acuUser'), cae.get_option('acuDSN'))
uprint('Migrate Reservation History:', 'No' if future_only else 'Yes')
uprint('Migrate Clients First/Separate:',
       ['No', 'Yes', 'Yes with client reservations'][int(cae.get_option('clientsFirst'))])
uprint('Break on error:', 'Yes' if break_on_error else 'No')


uprint('####  Migration of .......  ####')

if cae.get_option('clientsFirst'):
    uprint('####  ... Clients' + ('+Res' if cae.get_option('clientsFirst') == 2 else '....')
           + ('.....' if future_only else 'Hist.') + '  ####')
    acumen_cd = ClientToSihot(cae)
    acu_res_hist = ResToSihot(cae)

    error_msg = acumen_cd.fetch_all_valid_from_acu()
    progress = Progress(cae.get_option('debugLevel'), start_counter=acumen_cd.row_count,
                        start_msg='Prepare sending of {run_counter} client(s) to Sihot',
                        nothing_to_do_msg='SihotMigration: acumen_cd fetch returning no rows')
    if not error_msg:
        for crow in acumen_cd.rows:
            error_msg = acumen_cd.send_client_to_sihot(crow)
            progress.next(processed_id=crow['CD_CODE'] + '/' + str(crow['CDL_CODE']), error_msg=error_msg)
            if error_msg:
                acumen_cd.ora_db.rollback()
            else:
                error_msg = acumen_cd.ora_db.commit()

            if not error_msg and cae.get_option('clientsFirst') == 2:
                # NOT FULLY FUNCTIONAL / TESTED
                # DB SELECT very slow - better fetch/import all unsynced reservations with one select - see down
                # using fetch_from_acu_by_cd() would also pass reservations for currently not existing hotels
                #  error_msg = acu_res_hist.fetch_from_acu_by_cd(cols['CD_CODE'], future_only=future_only)
                # .. on the other hand: with aru fetch we are only migrating the synchronized resOcc types
                error_msg = acu_res_hist.fetch_from_acu_by_aru(where_group_order="CD_CODE = '" + crow['CD_CODE'] + "'",
                                                               date_range='F' if future_only else '')
                if error_msg:
                    error_msg = 'SihotMigration guest ' + crow['CD_CODE'] + ' reservation history fetch error: ' + \
                                error_msg + '! Data=' + str(crow)
                if not error_msg:
                    error_msg = acu_res_hist.send_rows_to_sihot(commit_per_row=True)
                    if error_msg:
                        error_msg = 'SihotMigration guest ' + crow['CD_CODE'] + \
                                    ' reservation history send error: ' + error_msg + '! Data=' + str(crow)
            if error_msg:
                uprint('****  Error sending new guest ' + crow['CD_CODE'] + ' to Sihot: ' + error_msg)
                if error_msg.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                    continue  # currently not used/returned-by-send_client_to_sihot()
                elif break_on_error:
                    break

    progress.finished(error_msg=error_msg)
    if error_msg:
        cae.shutdown(11)


uprint('####  ... ' + ('future Res......' if future_only else 'Reservations....') + '  ####')

acumen_req = ResToSihot(cae)
error_msg = acumen_req.fetch_all_valid_from_acu(date_range='F' if future_only else '')
progress = Progress(cae.get_option('debugLevel'), start_counter=acumen_req.row_count,
                    start_msg='Prepare the migration of {total_count} reservations to Sihot',
                    nothing_to_do_msg='SihotMigration: acumen_req.fetch_all_valid_from_acu() returning no rows')
if not error_msg:
    for crow in acumen_req.rows:
        error_msg = acumen_req.send_row_to_sihot(crow)
        progress.next(processed_id=str(crow['RUL_PRIMARY']) + '/' + str(crow['RUL_CODE']), error_msg=error_msg)
        if error_msg:
            acumen_req.ora_db.rollback()
        else:
            error_msg = acumen_req.ora_db.commit()
        if error_msg:
            if error_msg.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                continue
            elif cae.get_option('breakOnError'):
                break

progress.finished(error_msg=error_msg)

cae.shutdown(12 if error_msg else 0)
