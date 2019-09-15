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
    1.0     30-05-18 bug fix in sxmlif.py: now use RUL_PRIMARY instead of RU_CODE in F_SIHOT_CAT/CAT element for
            to allow sync of deleted RU records.
    1.1     28-02-19 migrated to use system data fields.
    1.2     08-03-19 extended logging and notification messages.
    1.3     11-05-19 beautified and hardened error notification and logging.
"""
import datetime

from sys_data_ids import (SDF_SH_WEB_PORT, SDF_SH_KERNEL_PORT, SDF_SH_TIMEOUT, SDF_SH_XML_ENCODING,
                          SDF_SH_USE_KERNEL_FOR_CLIENT, SDF_SH_USE_KERNEL_FOR_RES, SDI_ACU)
from ae.console_app import ConsoleApp
from ae.core import DATE_TIME_ISO, full_stack_trace
from ae.progress import Progress
from ae_notification.notification import add_notification_options, init_notification
from ae.sys_data import ACTION_INSERT, ACTION_UPDATE, ACTION_DELETE

from sxmlif import ERR_MESSAGE_PREFIX_CONTINUE
from acif import add_ac_options, AcuClientToSihot, AcuResToSihot
from shif import add_sh_options, ECM_TRY_AND_IGNORE_ERRORS
from ass_sys_data import AssSysData

__version__ = '1.3'

ADMIN_MAIL_TO_LIST = ['ITDevmen@signallia.com']

cae = ConsoleApp("Synchronize reservation changes from Acumen/Oracle system to the SiHOT-PMS",
                 additional_cfg_files=['SihotMktSegExceptions.cfg'])
add_ac_options(cae)
add_sh_options(cae, add_kernel_port=True, add_maps_and_kernel_usage=True)
add_notification_options(cae, add_warnings=True)
cae.add_opt('clientsFirst', "Migrate first the clients then the reservations (0=No, 1=Yes)",
            0, 'q', choices=(0, 1, 2))
cae.add_opt('breakOnError', "Abort synchronization if an error occurs (0=No, 1=Yes)", 0, 'b', choices=(0, 1))
cae.add_opt('migrationMode', "Skip room swap and hotel movement requests (0=No, 1=Yes)", 0, 'M', choices=(0, 1))
sync_date_ranges = dict(H='historical', M='present and 1 month in future', P='present and all future', F='future only',
                        Y='present, 1 month in future and all for hotels 1, 4 and 999',
                        Y90='like Y plus the 90 oldest records in the sync queue',
                        Y180='like Y plus the 180 oldest records in the sync queue',
                        Y360='like Y plus the 360 oldest records in the sync queue',
                        Y720='like Y plus the 720 oldest records in the sync queue')
cae.add_opt('syncDateRange', "Restrict sync. of res. to: "
            + ", ".join([k + '=' + v for k, v in sync_date_ranges.items()]), '', 'R',
            choices=sync_date_ranges.keys())


debug_level = cae.get_opt('debugLevel')
cae.po('Acumen Usr/DSN:', cae.get_opt('acuUser'), cae.get_opt('acuDSN'))
cae.po('Server IP/Web-/Kernel-port:', cae.get_opt('shServerIP'), cae.get_opt(SDF_SH_WEB_PORT),
       cae.get_opt(SDF_SH_KERNEL_PORT))
cae.po('TCP Timeout/XML Encoding:', cae.get_opt(SDF_SH_TIMEOUT), cae.get_opt(SDF_SH_XML_ENCODING))
cae.po('Use Kernel for clients:', 'Yes' if cae.get_opt(SDF_SH_USE_KERNEL_FOR_CLIENT) else 'No (WEB)')
cae.po('Use Kernel for reservations:', 'Yes' if cae.get_opt(SDF_SH_USE_KERNEL_FOR_RES) else 'No (WEB)')
last_rt_prefix = cae.get_opt('acuDSN')[-4:]
cae.po('Last unfinished run (-1=all finished):  ', cae.get_var(last_rt_prefix + 'lastRt'))
cae.po('Migrate Clients First/Separate:',
       ['No', 'Yes', 'Yes with client reservations'][int(cae.get_opt('clientsFirst'))])
cae.po('Break on error:', 'Yes' if cae.get_opt('breakOnError') else 'No')
notification, warning_notification_emails = init_notification(cae, cae.get_opt('acuDSN')
                                                              + '/' + cae.get_opt('shServerIP'))
if cae.get_var('warningFragments'):
    cae.po('Warning Fragments:', cae.get_var('warningFragments'))
migration_mode = cae.get_opt('migrationMode')
if migration_mode:
    cae.po("!!!!  Migration mode (room swaps and hotel movements are disabled)")
sync_date_range = cae.get_opt('syncDateRange')
if sync_date_range:
    cae.po("!!!!  Synchronizing only reservations in date range: " + sync_date_ranges[sync_date_range])


lastUnfinishedRunTime = cae.get_var(last_rt_prefix + 'lastRt')
if lastUnfinishedRunTime.startswith('@'):
    cae.po("****  Synchronization process is still running from last batch, started at ", lastUnfinishedRunTime[1:])
    cae.shutdown(4)
app_env_err = cae.set_var(last_rt_prefix + 'lastRt', '@' + datetime.datetime.now().strftime(DATE_TIME_ISO))


def send_notification(what, sid, mail_body, data_dict=None):
    global notification
    if not notification:
        return
    if not data_dict:
        data_dict = dict()

    subject = 'SihotResSync notification ' + what + ' ' + sid
    send_err = notification.send_notification(mail_body, subject=subject, data_dict=data_dict, body_style='plain')
    if send_err:
        cae.po(" **** " + subject
               + " send error: {}. data='{}' mail-body='{}'.".format(send_err, data_dict, mail_body))


error_msg = ""
if cae.get_opt('clientsFirst'):
    try:
        cae.po("####  Sync CD Changes.....  ####")

        acumen_cd = AcuClientToSihot(cae)
        error_msg = acumen_cd.fetch_from_acu_by_acu()
        progress = Progress(cae, start_counter=len(acumen_cd.recs),
                            start_msg=' ###  Prepare sending of {run_counter} client detail changes to Sihot',
                            nothing_to_do_msg='SihotResSync: acumen client fetch returning no recs')
        if not error_msg:
            for rec in acumen_cd.recs:
                error_msg = acumen_cd.send_client_to_sihot(rec)
                cid = rec['AcuId'] + '/' + str(rec['AcuLogId'])
                progress.next(processed_id=cid, error_msg=error_msg)
                if error_msg:
                    send_notification('Acumen Client', cid, error_msg, rec)
                error_msg += acumen_cd.ora_db.commit()
                if error_msg:
                    if error_msg.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                        continue            # currently not used/returned-by-send_client_to_sihot()
                    elif cae.get_opt('breakOnError'):
                        break
        progress.finished(error_msg=error_msg)
        send_notification('Synced Clients', str(datetime.datetime.now()), progress.get_end_message(error_msg=error_msg))
    except Exception as ex:
        app_env_err += '\n\nSync CD Changes exception: ' + str(ex)


sync_errors = []
if not error_msg:
    try:
        cae.po("####  Sync Req/ARU Changes  ####")

        asd = AssSysData(cae)
        hotel_ids = asd.ho_id_list()     # determine active/valid Sihot-hotels

        acumen_req = AcuResToSihot(cae, ora_db=asd.connection(SDI_ACU))
        error_msg = acumen_req.fetch_from_acu_by_aru(date_range=sync_date_range)
        if error_msg:
            notification.send_notification(error_msg, subject='SihotResSync fetch error notification',
                                           mail_to=ADMIN_MAIL_TO_LIST, body_style='plain')
        else:
            # 1st pre-run without room allocation - for to allow room swaps in the same batch
            room_recs = [r.copy(deepness=-1) for r in acumen_req.recs if r['ResHotelId']
                         and r['ResHotelId'] == r['ResLastHotelId']
                         and r['ResAction'] != ACTION_DELETE]
            if not migration_mode and room_recs:
                cae.dpo("  ##  room swap pre-run has {} recs".format(len(room_recs)))
                progress = Progress(cae, start_counter=len(room_recs),
                                    start_msg=" ###  Prepare sending of {total_count} room swaps to Sihot",
                                    nothing_to_do_msg=" ***  SihotResSync: room swap fetch returning no recs")
                for rec in room_recs:
                    rec['ResRoomNo'] = ''
                    error_msg = acumen_req.send_res_to_sihot(rec, ensure_client_mode=ECM_TRY_AND_IGNORE_ERRORS)
                    progress.next(processed_id='RoomSwap:' + acumen_req.res_id_values(rec), error_msg=error_msg)
                    if error_msg and notification:
                        error_msg = acumen_req.res_id_values(rec) + '\n\nERRORS=' + error_msg \
                                    + '\n\nWARNINGS=' + acumen_req.get_warnings()
                        notification.send_notification(error_msg, subject='SihotResSync admin room-swap notification',
                                                       mail_to=ADMIN_MAIL_TO_LIST, body_style='plain')
                    acumen_req.ora_db.rollback()  # send but roll back changes in ResObjId and T_SRSL
                progress.finished(error_msg=error_msg)

            # 2nd pre-run for hotel movements (HOTMOVE) - for to delete/cancel booking in last/old hotel
            room_recs = [r.copy(deepness=-1) for r in acumen_req.recs if r['ResHotelId'] != r['ResLastHotelId']
                         and r['ResLastHotelId'] in hotel_ids
                         and r['ResAction'] == ACTION_UPDATE]
            hotel_move_gds_nos = list()
            if not migration_mode and room_recs:
                cae.dpo("  ##  hotel movement pre-run has {} recs".format(len(room_recs)))
                progress = Progress(cae, start_counter=len(room_recs),
                                    start_msg=" ###  Prepare sending of {total_count} hotel movements to Sihot",
                                    nothing_to_do_msg=" ***  SihotResSync: hotel movement fetch returning no recs")
                for rec in room_recs:
                    new_hotel = str(rec['ResHotelId'])
                    rec['ResHotelId'] = rec['ResLastHotelId']
                    rec['ResRoomCat'] = rec['ResLastRoomCat']
                    rec['ResAction'] = ACTION_DELETE
                    rec['ResStatus'] = 'S'

                    error_msg = acumen_req.send_res_to_sihot(rec, ensure_client_mode=ECM_TRY_AND_IGNORE_ERRORS)

                    progress.next(processed_id='HotMove:' + acumen_req.res_id_values(rec), error_msg=error_msg)
                    if error_msg and notification:
                        error_msg = acumen_req.res_id_values(rec) + '\n\nERRORS=' + error_msg \
                                    + '\n\nWARNINGS=' + acumen_req.get_warnings()
                        notification.send_notification(error_msg, subject='SihotResSync admin HOTMOVE notification',
                                                       mail_to=ADMIN_MAIL_TO_LIST, body_style='plain')
                    if new_hotel not in hotel_ids:
                        acumen_req.ora_db.commit()    # because this res get skipped in the run loop underneath
                    else:
                        acumen_req.ora_db.rollback()  # send but roll back changes in ResObjId and T_SRSL
                    if rec.val('ResGdsNo'):
                        hotel_move_gds_nos.append(rec['ResGdsNo'])
                progress.finished(error_msg=error_msg)

            if not migration_mode:
                acumen_req.wipe_warnings()          # .. also wipe the warnings for to not be shown multiple/max=3 times
                acumen_req.wipe_gds_errors()        # .. as well as the errors for erroneous bookings (w/ same GDS)

            # now do the full run with room allocations (only skipping/excluding HOTMOVE to non-Sihot-hotel)
            synced_ids = list()
            progress = Progress(cae, start_counter=len(acumen_req.recs),
                                start_msg=" ###  Prepare sending of {total_count} reservations to Sihot",
                                nothing_to_do_msg=" ***  SihotResSync: acumen reservation fetch returning no recs")
            if acumen_req.recs:
                cae.dpo("  ##  full/main run has {} recs"
                        .format(len([_ for _ in acumen_req.recs if _['ResHotelId'] in hotel_ids])))
                for rec in acumen_req.recs:
                    rid = acumen_req.res_id_values(rec)
                    if rec['ResHotelId'] not in hotel_ids:
                        synced_ids.append(rid + "(H)")
                        continue        # skip HOTMOVE if new hotel is a non-Sihot-hotel
                    elif rec['ResLastHotelId'] not in hotel_ids:
                        rec['ResAction'] = ACTION_INSERT
                    if rec.val('ResGdsNo') in hotel_move_gds_nos:
                        cae.dpo("  ##  HotMove ResObjId {} reset; GdsNo={}".format(rec['ResObjId'], rec['ResGdsNo']))
                        rec['ResObjId'] = ''

                    error_msg = acumen_req.send_res_to_sihot(rec)

                    rid = acumen_req.res_id_values(rec)     # refresh rid with new ResId/ResSubId from Sihot
                    progress.next(processed_id=rid, error_msg=error_msg)
                    if error_msg:
                        send_notification("Acumen Reservation", rid, acumen_req.res_id_desc(rec, error_msg), rec)
                    error_msg += acumen_req.ora_db.commit()
                    if error_msg:
                        if error_msg.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                            synced_ids.append(rid + "(C)")
                            continue
                        sync_errors.append(rid + ": " + error_msg)
                        if cae.get_opt('breakOnError'):
                            break
                    else:
                        synced_ids.append(rid)
            progress.finished(error_msg=error_msg)
            cae.po("####  Synced IDs: " + str(synced_ids))
            send_notification("Synced Reservations", str(datetime.datetime.now()),
                              progress.get_end_message()
                              + "\n\n\nSYNCHRONIZED (" + acumen_req.res_id_label() + "):\n" + str(synced_ids)
                              + "\n\n\nERRORS (" + acumen_req.res_id_label() + ": ERR):\n\n" + "\n\n".join(sync_errors))
            warnings = acumen_req.get_warnings()
            if notification and warnings:
                notification.send_notification(warnings, subject="SihotResSync warnings notification",
                                               mail_to=cae.get_opt('warningsMailToAddr'), body_style='plain')

    except Exception as ex:
        app_env_err += "\n\nSync Req/ARU Changes exception: " + full_stack_trace(ex)


# release dup exec lock
try:
    set_opt_err = cae.set_var(last_rt_prefix + 'lastRt', str(-1))
except Exception as ex:
    set_opt_err = 'Duplicate execution lock release exception: ' + str(ex)
    cae.po("\nDUP EXEC LOCK ERROR=", set_opt_err)
    app_env_err += '\n\n' + set_opt_err

if app_env_err:
    cae.po("\nAPP ENV ERRORS:\n", app_env_err)
    notification.send_notification(app_env_err, subject='SihotResSync environment error', mail_to=ADMIN_MAIL_TO_LIST)

cae.shutdown(13 if set_opt_err else (12 if sync_errors else 0))
