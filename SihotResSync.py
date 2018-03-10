"""
    0.1     first beta.
    0.2     refactored to use V_ACU_RES_UNSYNCED (including resort filter) and T_SRSL.
    0.3     added error counter to Progress, refactored lastId into LastRt and removed processed_A*.
    0.4     removed more fields on DELETE action and implemented DELETE for room allocations moved to non-Sihot-hotels.
    0.5     changed SihotResSync.ini and SyncLIVE.cmd for to specify log and debug level in ini + small refactorings.
    0.6     added sync_summary and synced_ids and (in sxmlif.py) skipping of follow-up changes after/of erroneous res.
    0.7     23-09-17 added migrationMode and syncDateRange command line option.
    0.8     01-03-18 extended to allow allotments (RCI) configured by SihotMktSegExceptions.cfg.
    0.9     08-03-18 bug fix in sxmlif.py: now set SRSL_DATE to start-of-sync-query-fetch instead of end-of-sync).
"""
import datetime

from ae_console_app import ConsoleApp, Progress, uprint, DATE_TIME_ISO, DEBUG_LEVEL_VERBOSE, full_stack_trace
from ae_notification import Notification
from ae_db import ACU_DEF_USR, ACU_DEF_DSN

from sxmlif import ClientToSihot, ResToSihot, \
    SXML_DEF_ENCODING, ERR_MESSAGE_PREFIX_CONTINUE, \
    USE_KERNEL_FOR_CLIENTS_DEF, USE_KERNEL_FOR_RES_DEF, MAP_CLIENT_DEF, MAP_RES_DEF, \
    ACTION_UPDATE, ACTION_DELETE, ECM_TRY_AND_IGNORE_ERRORS, ECM_ENSURE_WITH_ERRORS
from ass_sys_data import AssSysData

__version__ = '0.9'

ADMIN_MAIL_TO_LIST = ['ITDevmen@acumen.es']

cae = ConsoleApp(__version__, "Synchronize reservation changes from Acumen/Oracle system to the SiHOT-PMS",
                 additional_cfg_files=['SihotMktSegExceptions.cfg'])
cae.add_option('acuUser', "User name of Acumen/Oracle system", ACU_DEF_USR, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", ACU_DEF_DSN, 'd')

cae.add_option('serverIP', "IP address of the SIHOT interface server", 'localhost', 'i')
cae.add_option('serverPort', "IP port of the WEB interface of this server", 14777, 'w')
cae.add_option('serverKernelPort', "IP port of the KERNEL interface of this server", 14772, 'k')

cae.add_option('timeout', "Timeout value for TCP/IP connections", 69.3)
cae.add_option('xmlEncoding', "Charset used for the xml data", SXML_DEF_ENCODING, 'e')

cae.add_option('useKernelForClient', "Used interface for clients (0=web, 1=kernel)", USE_KERNEL_FOR_CLIENTS_DEF, 'g',
               choices=(0, 1))
cae.add_option('mapClient', "Guest/Client mapping of xml to db items", MAP_CLIENT_DEF, 'm')
cae.add_option('useKernelForRes', "Used interface for reservations (0=web, 1=kernel)", USE_KERNEL_FOR_RES_DEF, 'z',
               choices=(0, 1))
cae.add_option('mapRes', "Reservation mapping of xml to db items", MAP_RES_DEF, 'n')

cae.add_option('clientsFirst', "Migrate first the clients then the reservations (0=No, 1=Yes)",
               0, 'q', choices=(0, 1, 2))
cae.add_option('breakOnError', "Abort synchronization if an error occurs (0=No, 1=Yes)", 0, 'b', choices=(0, 1))

cae.add_option('smtpServerUri', "SMTP notification server account URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP sender/from address", '', 'f')
cae.add_option('smtpTo', "List/Expression of SMTP receiver/to addresses", list(), 'r')

cae.add_option('warningsMailToAddr', "Warnings SMTP receiver/to addresses (if differs from smtpTo)", list(), 'v')

cae.add_option('migrationMode', "Skip room swap and hotel movement requests (0=No, 1=Yes)", 0, 'M', choices=(0, 1))
sync_date_ranges = dict(H='historical', M='present and 1 month in future', P='present and all future', F='future only',
                        Y='present, 1 month in future and all for hotels 1, 4 and 999',
                        Y90='like Y plus the 90 oldest records in the sync queue',
                        Y180='like Y plus the 180 oldest records in the sync queue',
                        Y360='like Y plus the 360 oldest records in the sync queue',
                        Y720='like Y plus the 720 oldest records in the sync queue')
cae.add_option('syncDateRange', "Restrict sync. of res. to: "
               + ", ".join([k + '=' + v for k, v in sync_date_ranges.items()]), '', 'R',
               choices=sync_date_ranges.keys())


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
notification = None
if cae.get_option('smtpServerUri') and cae.get_option('smtpFrom') and cae.get_option('smtpTo'):
    notification = Notification(smtp_server_uri=cae.get_option('smtpServerUri'),
                                mail_from=cae.get_option('smtpFrom'),
                                mail_to=cae.get_option('smtpTo'),
                                used_system=cae.get_option('acuDSN') + '/' + cae.get_option('serverIP'),
                                debug_level=debug_level)
    uprint('SMTP Uri/From/To:', cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))
    if cae.get_option('warningsMailToAddr'):
        uprint('Warnings SMTP receiver address:', cae.get_option('warningsMailToAddr'))
if cae.get_config('warningFragments'):
    uprint('Warning Fragments:', cae.get_config('warningFragments'))
migration_mode = cae.get_option('migrationMode')
if migration_mode:
    uprint("!!!!  Migration mode (room swaps and hotel movements are disabled)")
sync_date_range = cae.get_option('syncDateRange')
if sync_date_range:
    uprint("!!!!  Synchronizing only reservations in date range: " + sync_date_ranges[sync_date_range])


lastUnfinishedRunTime = cae.get_config(last_rt_prefix + 'lastRt')
if lastUnfinishedRunTime.startswith('@'):
    uprint("****  Synchronization process is still running from last batch, started at ", lastUnfinishedRunTime[1:])
    cae.shutdown(4)
app_env_err = cae.set_config(last_rt_prefix + 'lastRt', '@' + datetime.datetime.now().strftime(DATE_TIME_ISO))


def send_notification(what, sid, mail_body, data_dict=None):
    global notification
    if not notification:
        return
    if not data_dict:
        data_dict = dict()

    subject = 'SihotResSync notification ' + what + ' ' + sid
    send_err = notification.send_notification(mail_body, subject=subject, data_dict=data_dict)
    if send_err:
        uprint(" **** " + subject
               + " send error: {}. data='{}' mail-body='{}'.".format(send_err, data_dict, mail_body))


error_msg = ""
if cae.get_option('clientsFirst'):
    try:
        uprint("####  Sync CD Changes.....  ####")

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
                    send_notification('Acumen Client', cid, error_msg, crow)
                error_msg += acumen_cd.ora_db.commit()
                if error_msg:
                    if error_msg.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                        continue            # currently not used/returned-by-send_client_to_sihot()
                    elif cae.get_option('breakOnError'):
                        break
        progress.finished(error_msg=error_msg)
        send_notification('Synced Clients', str(datetime.datetime.now()), progress.get_end_message(error_msg=error_msg))
    except Exception as ex:
        app_env_err += '\n\nSync CD Changes exception: ' + str(ex)


sync_errors = []
if not error_msg:
    try:
        uprint("####  Sync Req/ARU Changes  ####")

        config_data = AssSysData(cae)
        hotel_ids = config_data.ho_id_list()     # determine active/valid Sihot-hotels
        acumen_req = ResToSihot(cae, use_kernel_interface=cae.get_option('useKernelForRes'),
                                map_res=cae.get_option('mapRes'),
                                use_kernel_for_new_clients=cae.get_option('useKernelForClient'),
                                map_client=cae.get_option('mapClient'))
        error_msg = acumen_req.fetch_from_acu_by_aru(date_range=sync_date_range)
        if error_msg:
            notification.send_notification(error_msg, subject='SihotResSync fetch error notification',
                                           mail_to=ADMIN_MAIL_TO_LIST)
        else:
            # 1st pre-run without room allocation - for to allow room swaps in the same batch
            room_rows = [dict(r) for r in acumen_req.rows if r['RUL_SIHOT_ROOM']
                         and r['RUL_SIHOT_HOTEL'] == r['RUL_SIHOT_LAST_HOTEL']
                         and r['RUL_ACTION'] != ACTION_DELETE]
            if not migration_mode and room_rows:
                cae.dprint(" ###  room swap pre-run has {} rows".format(len(room_rows)),
                           minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                progress = Progress(debug_level, start_counter=len(room_rows),
                                    start_msg=" ###  Prepare sending of {total_count} room swaps to Sihot",
                                    nothing_to_do_msg=" ***  SihotResSync: room swap fetch returning no rows")
                for crow in room_rows:
                    crow['RUL_SIHOT_ROOM'] = ''
                    error_msg = acumen_req.send_row_to_sihot(crow, ensure_client_mode=ECM_TRY_AND_IGNORE_ERRORS)
                    progress.next(processed_id='RoomSwap:' + acumen_req.res_id_values(crow), error_msg=error_msg)
                    if error_msg and notification:
                        error_msg = acumen_req.res_id_values(crow) + '\n\nERRORS=' + error_msg \
                                    + '\n\nWARNINGS=' + acumen_req.get_warnings()
                        notification.send_notification(error_msg, subject='SihotResSync admin room-swap notification',
                                                       mail_to=ADMIN_MAIL_TO_LIST)
                    acumen_req.ora_db.rollback()  # send but directly roll back changes in RU_SIHOT_OBJID and T_SRSL
                progress.finished(error_msg=error_msg)

            # 2nd pre-run for hotel movements (HOTMOVE) - for to delete/cancel booking in last/old hotel
            room_rows = [dict(r) for r in acumen_req.rows if r['RUL_SIHOT_HOTEL'] != r['RUL_SIHOT_LAST_HOTEL']
                         and str(r['RUL_SIHOT_LAST_HOTEL']) in hotel_ids
                         and r['RUL_ACTION'] == ACTION_UPDATE]
            if not migration_mode and room_rows:
                cae.dprint(" ###  hotel movement pre-run has {} rows".format(len(room_rows)),
                           minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                progress = Progress(debug_level, start_counter=len(room_rows),
                                    start_msg=" ###  Prepare sending of {total_count} hotel movements to Sihot",
                                    nothing_to_do_msg=" ***  SihotResSync: hotel movement fetch returning no rows")
                for crow in room_rows:
                    new_hotel = str(crow['RUL_SIHOT_HOTEL'])
                    crow['RUL_SIHOT_HOTEL'] = crow['RUL_SIHOT_LAST_HOTEL']
                    crow['RUL_SIHOT_CAT'] = crow['RUL_SIHOT_LAST_CAT']
                    crow['RUL_ACTION'] = 'DELETE'
                    crow['SH_RES_TYPE'] = 'S'
                    error_msg = acumen_req.send_row_to_sihot(crow, ensure_client_mode=ECM_TRY_AND_IGNORE_ERRORS)
                    progress.next(processed_id='HotMove:' + acumen_req.res_id_values(crow), error_msg=error_msg)
                    if error_msg and notification:
                        error_msg = acumen_req.res_id_values(crow) + '\n\nERRORS=' + error_msg \
                                    + '\n\nWARNINGS=' + acumen_req.get_warnings()
                        notification.send_notification(error_msg, subject='SihotResSync admin HOTMOVE notification',
                                                       mail_to=ADMIN_MAIL_TO_LIST)
                    if new_hotel not in hotel_ids:
                        acumen_req.ora_db.commit()    # because this res get skipped in the full run loop underneath
                    else:
                        acumen_req.ora_db.rollback()  # send but directly roll back changes in RU_SIHOT_OBJID and T_SRSL
                progress.finished(error_msg=error_msg)

            if not migration_mode:
                acumen_req.wipe_warnings()          # .. also wipe the warnings for to not be shown multiple/max=3 times
                acumen_req.wipe_gds_errors()        # .. as well as the errors for erroneous bookings (w/ same GDS)

            # now do the full run with room allocations (only skipping/excluding HOTMOVE to non-Sihot-hotel)
            synced_ids = list()
            progress = Progress(debug_level, start_counter=acumen_req.row_count,
                                start_msg=" ###  Prepare sending of {total_count} reservations to Sihot",
                                nothing_to_do_msg=" ***  SihotResSync: acumen reservation fetch returning no rows")
            if acumen_req.rows:
                cae.dprint(" ###  full/main run has {} rows"
                           .format(len([_ for _ in acumen_req.rows if str(_['RUL_SIHOT_HOTEL']) in hotel_ids])),
                           minimum_debug_level=DEBUG_LEVEL_VERBOSE)
                for crow in acumen_req.rows:
                    rid = acumen_req.res_id_values(crow)
                    if str(crow['RUL_SIHOT_HOTEL']) not in hotel_ids:
                        synced_ids.append(rid + "(H)")
                        continue        # skip HOTMOVE if new hotel is a non-Sihot-hotel
                    elif str(crow['RUL_SIHOT_LAST_HOTEL']) not in hotel_ids:
                        crow['RUL_ACTION'] = 'INSERT'
                    error_msg = acumen_req.send_row_to_sihot(crow, ensure_client_mode=ECM_ENSURE_WITH_ERRORS)
                    progress.next(processed_id=rid, error_msg=error_msg)
                    if error_msg:
                        send_notification("Acumen Reservation", rid, acumen_req.res_id_desc(crow, error_msg), crow)
                    error_msg += acumen_req.ora_db.commit()
                    if error_msg:
                        if error_msg.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                            synced_ids.append(rid + "(C)")
                            continue
                        sync_errors.append(rid + ": " + error_msg)
                        if cae.get_option('breakOnError'):
                            break
                    else:
                        synced_ids.append(rid)
            progress.finished(error_msg=error_msg)
            uprint("####  Synced IDs: " + str(synced_ids))
            send_notification("Synced Reservations", str(datetime.datetime.now()),
                              progress.get_end_message()
                              + "\n\n\nSYNCHRONIZED (" + acumen_req.res_id_label() + "):\n" + str(synced_ids)
                              + "\n\n\nERRORS (" + acumen_req.res_id_label() + ": ERR):\n\n" + "\n\n".join(sync_errors))
            warnings = acumen_req.get_warnings()
            if notification and warnings:
                notification.send_notification(warnings, subject="SihotResSync warnings notification",
                                               mail_to=cae.get_option('warningsMailToAddr'))

    except Exception as ex:
        app_env_err += "\n\nSync Req/ARU Changes exception: " + full_stack_trace(ex)


# release dup exec lock
try:
    set_opt_err = cae.set_config(last_rt_prefix + 'lastRt', str(-1))
except Exception as ex:
    set_opt_err = 'Duplicate execution lock release exception: ' + str(ex)
    uprint("\nDUP EXEC LOCK ERROR=", set_opt_err)
    app_env_err += '\n\n' + set_opt_err

if app_env_err:
    uprint("\nAPP ENV ERRORS:\n", app_env_err)
    notification.send_notification(app_env_err, subject='SihotResSync environment error', mail_to=ADMIN_MAIL_TO_LIST)

cae.shutdown(13 if set_opt_err else (12 if sync_errors else 0))
