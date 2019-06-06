"""
    0.1     first beta.
    0.2     refactored to use V_ACU_RES_UNSYNCED (including resort filter) and T_SRSL.
    0.3     added error counter to Progress
"""

from ae.console_app import ConsoleApp, Progress, uprint, full_stack_trace
from acif import add_ac_options, AcuClientToSihot, AcuResToSihot
from sxmlif import ERR_MESSAGE_PREFIX_CONTINUE
from shif import add_sh_options, print_sh_options


__version__ = '0.3'

cae = ConsoleApp(__version__, "Migrate all guest/reservation data from Acumen/Oracle system to the SiHOT-PMS")
add_sh_options(cae, add_kernel_port=True)

add_ac_options(cae)

cae.add_option('clientsFirst', "Migrate first the clients then the reservations (0=No, 1=Yes)",
               0, 'q', choices=(0, 1, 2))
cae.add_option('breakOnError', "Abort migration if error occurs (0=No, 1=Yes)", 1, 'b', choices=(0, 1))

sync_date_ranges = dict(H='historical', M='present and 1 month in future', P='present and all future', F='future only',
                        Y='present, 1 month in future and all for hotels 1, 4 and 999',
                        Y90='like Y plus the 90 oldest records in the sync queue',
                        Y180='like Y plus the 180 oldest records in the sync queue',
                        Y360='like Y plus the 360 oldest records in the sync queue',
                        Y720='like Y plus the 720 oldest records in the sync queue')
cae.add_option('syncDateRange', "Restrict sync. of res. to: "
               + ", ".join([k + '=' + v for k, v in sync_date_ranges.items()]), '', 'R',
               choices=sync_date_ranges.keys())
cae.add_option('includeCxlRes', "Include also cancelled reservations (0=No, 1=Yes)", 1, 'I', choices=(0, 1))

print_sh_options(cae)
uprint("Acumen Usr/DSN:", cae.get_option('acuUser'), cae.get_option('acuDSN'))
uprint("Migrate Clients First/Separate:",
       ['No', 'Yes', 'Yes with client reservations'][int(cae.get_option('clientsFirst'))])
break_on_error = cae.get_option('breakOnError')
uprint("Break on error:", 'Yes' if break_on_error else 'No')
sync_date_range = cae.get_option('syncDateRange')
future_only = sync_date_range == 'F'
uprint("Migrate Reservation History:", 'No' if future_only else 'Yes')
if sync_date_range and not future_only:
    uprint("!!!!  Synchronizing only reservations in date range: " + sync_date_ranges[sync_date_range])
include_cxl_res = cae.get_option('includeCxlRes')
if include_cxl_res:
    uprint("Include also cancelled reservations: Yes")


error_msg = ""
uprint("####  Migration of .......  ####")

if cae.get_option('clientsFirst'):
    uprint('####  ... Clients' + ('+Res' if cae.get_option('clientsFirst') == 2 else '....')
           + ('.....' if future_only else 'Hist.') + '  ####')
    acumen_cd = AcuClientToSihot(cae)
    acu_res_hist = AcuResToSihot(cae)

    error_msg = acumen_cd.fetch_all_valid_from_acu()
    progress = Progress(cae, start_counter=len(acumen_cd.recs),
                        start_msg=' ###  Prepare sending of {run_counter} client(s) to Sihot',
                        nothing_to_do_msg='SihotMigration: acumen_cd fetch returning no recs')
    if not error_msg:
        for rec in acumen_cd.recs:
            error_msg = acumen_cd.send_client_to_sihot(rec)
            progress.next(processed_id=rec['AcuId'] + '/' + str(rec['AcuLogId']), error_msg=error_msg)
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
                error_msg = acu_res_hist.fetch_from_acu_by_aru(where_group_order="CD_CODE = '" + rec['AcuId'] + "'",
                                                               date_range=sync_date_range)
                if error_msg:
                    error_msg = 'SihotMigration guest ' + rec['AcuId'] + ' reservation history fetch error: ' + \
                                error_msg + '! Data=' + str(rec)
                else:
                    error_msg = acu_res_hist.send_res_recs_to_sihot()
                    if error_msg:
                        error_msg = 'SihotMigration guest ' + rec['AcuId'] + \
                                    ' reservation history send error: ' + error_msg + '! Data=' + str(rec)
                        acu_res_hist.ora_db.rollback()
                    else:
                        acu_res_hist.ora_db.commit()
            if error_msg:
                uprint('****  Error sending new guest ' + rec['AcuId'] + ' to Sihot: ' + error_msg)
                if error_msg.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                    continue  # currently not used/returned-by-send_client_to_sihot()
                elif break_on_error:
                    break

    progress.finished(error_msg=error_msg)
    if error_msg:
        cae.shutdown(11)


uprint("####  ... " + ("future Res......" if future_only else "Reservations....") + "  ####")

try:
    acumen_res = AcuResToSihot(cae)
    error_msg = acumen_res.fetch_from_acu_by_aru(date_range=sync_date_range)
    if not error_msg:
        progress = Progress(cae, start_counter=len(acumen_res.recs),
                            start_msg=' ###  Prepare the migration of {total_count} reservations to Sihot',
                            nothing_to_do_msg='SihotMigration: acumen_res.fetch_all_valid_from_acu() returning no recs')
        if include_cxl_res:
            all_recs = acumen_res.recs
        else:
            all_recs = list()
            del_gds_nos = list()
            for rec in reversed(acumen_res.recs):
                gds_no = rec['ResGdsNo']
                if gds_no in del_gds_nos:
                    continue
                elif rec['ResStatus'] == 'S' and gds_no:
                    del_gds_nos.append(gds_no)
                else:
                    all_recs.append(rec)
            all_recs = reversed(all_recs)
        for rec in all_recs:
            error_msg = acumen_res.send_res_to_sihot(rec)
            res_id = acumen_res.res_id_values(rec)
            progress.next(processed_id=res_id, error_msg=error_msg)
            if error_msg:
                acumen_res.ora_db.rollback()
            else:
                error_msg = acumen_res.ora_db.commit()
            if error_msg:
                if error_msg.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                    continue
                elif cae.get_option('breakOnError'):
                    break

        progress.finished(error_msg=error_msg)

except Exception as ex:
    uprint("\n\nMigration Req/ARU Changes exception: " + full_stack_trace(ex))

cae.shutdown(12 if error_msg else 0)
