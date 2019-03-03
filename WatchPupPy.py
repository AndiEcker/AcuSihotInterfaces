"""
    0.4     changed command call from check_call() to check_output() for to determine and pass StdOut/StdErr  AND
            added outer try exception fallback into main loop (for to catch strange/unsuspected errors).
    0.5     added new option sendOutput for to allow caller to use either check_call() or check_output().
    0.6     added outage check of T_SRSL/ARO (Sihot-To-Acumen interface), changed run lock reset to be optional.
    0.7     added process ids to notification emails and stdout.
    0.8     refactored using add_ass_options() and init_ass_data().
    0.9     enhanced system checking (merge errors and added checks for AssCache and Salesforce), fixed bug (missing
            config file write) in reset_last_run_time().
    1.0     add check of last T_SRSL for RU (SRSL_TABLE) and fix file path bug and on INI lock reset.

TODO:
    - investigate and fix bug with freeze if sendOutput option is specified with the value 1/enabled and unsuccessful
      reset problem (see notification emails from 04-09-17).

SERVER RUN SYSTEM CONFIGURATION:

When you are using WatchPupPy for always running servers (specifying 0 value for the cmdInterval option)
then ensure that you disable Windows Error Reporting to prevent the freeze by the message box showing
"<APP.EXE> has stopped working" and offering "Check online for a solution and close program":
- https://www.raymond.cc/blog/disable-program-has-stopped-working-error-dialog-in-windows-server-2008/
- https://monitormyweb.com/guides/how-to-disable-stopped-working-message-in-windows

"""
import os
import time
import datetime
import subprocess
from configparser import ConfigParser
import pprint

from sys_data_ids import SDI_ASS, SDI_ACU, SDI_SF, SDI_SH, SDF_SH_KERNEL_PORT, SDF_SH_WEB_PORT
from ae_console_app import ConsoleApp, Progress, uprint, full_stack_trace,\
    MAIN_SECTION_DEF, DATE_TIME_ISO, DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_VERBOSE
from sxmlif import PostMessage
from shif import ClientSearch
from ass_sys_data import add_ass_options, init_ass_data


__version__ = '1.0'

BREAK_PREFIX = 'User pressed Ctrl+C key'
MAX_SRSL_OUTAGE_HOURS = 18.0                # maximum time after last sync entry was logged (multiple on TEST system)
DEF_TC_SC_ID = '27'
DEF_TC_SC_MC = 'TCRENT'
DEF_TC_AG_ID = '20'
DEF_TC_AG_MC = 'TCAG'


cae = ConsoleApp(__version__, "Periodically execute and supervise command")

cae.add_option('cmdLine', "command [line] to execute", '', 'x')
cae.add_option('cmdInterval', "command interval in seconds (pass 0 for always running servers)", 3600, 'l')  # ==1 hour
cae.add_option('envChecks', "Number of environment checks per command interval", 3, 'n')
cae.add_option('sendOutput',
               "Include command output in the notification email (0=No, 1=Yes if notification is enabled)", 0, 'O')

ass_options = add_ass_options(cae, add_kernel_port=True, break_on_error=True)

cmd_line = cae.get_option('cmdLine')
if not cmd_line:
    uprint('Empty command line - Nothing to do.')
    cae.shutdown()
uprint('Command line:', cmd_line)
command_line_args = cmd_line.split(' ')
exe_name = command_line_args[0]

command_interval = cae.get_option('cmdInterval')  # in seconds
env_checks_per_interval = cae.get_option('envChecks')
uprint("Command interval/checks:", command_interval, env_checks_per_interval)
if command_interval:
    # init timeout to command_interval-5% (if 1 hour than to 57 minutes, ensure minimum 1 minute for error recovering)
    timeout = max(command_interval - max(command_interval // 20, 60), 60)
else:
    timeout = None  # run sub-process without interrupting (only re-start if crashes)
check_interval = command_interval // env_checks_per_interval
last_timer = last_run = last_check = None

last_sync = datetime.datetime.now()
last_rt_prefix = cae.get_option('acuDSN')[-4:]


ass_data = init_ass_data(cae, ass_options, used_systems_msg_prefix="Active Sys Env Checks")
asd = ass_data['assSysData']
if asd.error_message:
    uprint("WatchPupPy startup error: ", asd.error_message)
    asd.close_dbs()
    cae.shutdown(exit_code=9)


break_on_error = ass_data['breakOnError']
notification = ass_data['notification']
send_output = 1 if notification and cae.get_option('sendOutput') else 0
uprint("Send Output (subprocess call method: 1=check_output, 0=check_call)", send_output)

is_test = asd.is_test_system()
max_sync_outage_delta = exe_name.startswith(('AcuServer', 'SihotResSync')) \
                        and datetime.timedelta(hours=MAX_SRSL_OUTAGE_HOURS * (9 if is_test else 1))


def user_notification(subject, body):
    parent_pid = os.getppid()
    pid = os.getpid()
    subject += " " + exe_name + " pid=" + str(parent_pid) + ("/" + str(pid) if pid != parent_pid else "")
    body = pprint.pformat(body, indent=3, width=120)

    if notification:
        err_message = notification.send_notification(body, subject=subject, body_style='plain')
        if err_message:
            uprint("****  WatchPupPy notification error: {}. Unsent notification body:\n{}.".format(err_message, body))
    else:
        uprint("****  " + subject + "\n" + body)


def get_timer_corrected():
    """ get timer ticker value (seconds) and reset all timer vars on overflow (which should actually never happen
        with monotonic, but some OS may only support 32 bits - rolling-over after 49.7 days) """
    global last_timer, last_run, last_check
    curr_timer = time.monotonic()
    if last_timer is None or curr_timer < last_timer:   # if app-startup or timer-roll-over
        last_run = curr_timer - command_interval        # .. then reset to directly do next env-check and cmd-run
        last_check = curr_timer - check_interval
    last_timer = curr_timer
    return curr_timer

        
def reset_last_run_time(force=False):
    msg = ""
    try:
        cmd_cfg_file_name = os.path.splitext(exe_name)[0] + '.ini'
        if os.path.isfile(cmd_cfg_file_name):
            cmd_cfg_parser = ConfigParser()
            cmd_cfg_parser.optionxform = str  # or use 'lambda option: option' to have case-sensitive INI/CFG var names
            cmd_cfg_parser.read(cmd_cfg_file_name)
            last_start = cmd_cfg_parser.get(MAIN_SECTION_DEF, last_rt_prefix + 'lastRt')
            if last_start[0] == '@':
                last_start_dt = datetime.datetime.strptime(last_start[1:], DATE_TIME_ISO)
                interval_delta = datetime.timedelta(seconds=command_interval) * 3
                now_dt = datetime.datetime.now()
                if force or now_dt > last_start_dt + interval_delta:
                    cmd_cfg_parser.set(MAIN_SECTION_DEF,
                                       last_rt_prefix + 'Rt_kill_' + datetime.datetime.now().strftime('%y%m%d_%H%M%S'),
                                       last_start)
                    cmd_cfg_parser.set(MAIN_SECTION_DEF,
                                       last_rt_prefix + 'lastRt', '-999')
                    with open(cmd_cfg_file_name, 'w') as ini_fp:
                        cmd_cfg_parser.write(ini_fp)
                    msg = cmd_cfg_file_name + " lock reset. Old value=" + str(last_start)
                else:
                    msg = cmd_cfg_file_name + " still locked for " + str(last_start_dt + interval_delta - now_dt)
            else:
                msg = "Found INI file {} but lock entry {} is missing the leading @ character (value={})"\
                    .format(cmd_cfg_file_name, last_rt_prefix + 'lastRt', last_start)
        else:
            msg = cmd_cfg_file_name + " not found"
    except Exception as x:
        msg += " exception: " + str(x)
    if msg:
        uprint("WatchPupPy.reset_last_run_time()", msg)
        user_notification('WatchPupPy reset last run time warning', msg)


startup = get_timer_corrected()     # initialize timer and last check/run values
cae.dprint(" ###  Startup {} timer value={}, last check={}, check interval={}, last run={}, run interval={}"
           .format("" if is_test else "production", startup, last_check, check_interval, last_run, command_interval),
           minimum_debug_level=DEBUG_LEVEL_DISABLED if is_test else DEBUG_LEVEL_VERBOSE)
progress = Progress(cae.get_option('debugLevel'), total_count=1,
                    start_msg='Preparing environment checks and first run of {}'.format(exe_name))

errors = list()
run_starts = run_ends = err_count = 0
tc_sc_id = tc_sc_mc = tc_ag_id = tc_ag_mc = ''
while True:
    try:        # outer exception fallback - only for strange/unsuspected errors
        # check for errors/warnings to be send to support
        run_msg = "Preparing {}. run (after {} runs with {} errors)".format(run_starts, run_ends, err_count)
        err_msg = "\n      ".join(errors)
        progress.next(processed_id=run_msg, error_msg=err_msg)
        if err_msg:
            err_count += 1
            user_notification("WatchPupPy notification", err_msg)
            if break_on_error or BREAK_PREFIX in err_msg:
                break
            errors = list()
            time.sleep(command_interval / 30)  # wait 120 seconds after each error, for command_interval of 1 hour

        # wait for next check_interval, only directly after startup checks on first run
        if get_timer_corrected() < last_check + check_interval:
            cae.dprint(" ###  Waiting for next check in {} seconds (timer={}, last={}, interval={})".format(
                last_check + check_interval - get_timer_corrected(), get_timer_corrected(), last_check, check_interval),
                minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        try:
            while get_timer_corrected() < last_check + check_interval:
                time.sleep(1)  # allow to process/raise KeyboardInterrupt within 1 second
        except KeyboardInterrupt:
            errors.append(BREAK_PREFIX + " while waiting for next check in {} seconds"
                          .format(last_check + check_interval - get_timer_corrected()))
            continue  # first notify, then break in next loop because auf BREAK_PREFIX
        cae.dprint(" ###  Running checks (timer={}, last={}, interval={})".format(
            get_timer_corrected(), last_check, check_interval),
            minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        # check environment and connections: AssCache, Acu/Oracle, Salesforce, Sihot servers and interfaces
        if SDI_ASS in asd.used_systems:
            if not asd.connection(SDI_ASS) or asd.connection(SDI_ASS).select('pg_tables'):
                asd.reconnect(SDI_ASS)
            if not asd.connection(SDI_ASS):
                errors.append("AssCache environment check connection error: " + asd.error_message)
            else:
                ass_db = asd.connection(SDI_ASS)
                err_msg = ass_db.select('hotels', ['ho_pk', 'ho_ac_id'])
                if err_msg:
                    errors.append("AssCache table hotels selection error: " + err_msg)

        if SDI_ACU in asd.used_systems:
            if not asd.connection(SDI_ACU) or asd.connection(SDI_ACU).select('dual', ['sysdate']):
                asd.reconnect(SDI_ACU)
            if not asd.connection(SDI_ACU):
                errors.append("Acumen environment check connection error: " + asd.error_message)
            else:
                ora_db = asd.connection(SDI_ACU)
                err_msg = ora_db.select('T_RO', ['RO_SIHOT_AGENCY_OBJID', 'RO_SIHOT_AGENCY_MC'],
                                        where_group_order="RO_CODE = 'TK'")
                if err_msg:
                    errors.append("Acumen environment T_RO/TK selection error: " + err_msg)
                else:
                    rows = ora_db.fetch_all()
                    if ora_db.last_err_msg:
                        errors.append("Acumen environment fetch T_RO/TK error: " + ora_db.last_err_msg)
                    else:
                        tc_sc_id = str(rows[0][0])  # == DEF_TC_SC_ID
                        tc_sc_mc = rows[0][1]       # == DEF_TC_SC_MC

                err_msg = ora_db.select('T_RO', ['RO_SIHOT_AGENCY_OBJID', 'RO_SIHOT_AGENCY_MC'],
                                        where_group_order="RO_CODE = 'tk'")
                if err_msg:
                    errors.append("Acumen environment T_RO/tk selection error: " + err_msg)
                else:
                    rows = ora_db.fetch_all()
                    if ora_db.last_err_msg:
                        errors.append("Acumen environment fetch T_RO/tk error: " + ora_db.last_err_msg)
                    else:
                        tc_ag_id = str(rows[0][0])  # == DEF_TC_AG_ID
                        tc_ag_mc = rows[0][1]       # == DEF_TC_AG_MC

                if not errors and (tc_sc_id != DEF_TC_SC_ID or tc_sc_mc != DEF_TC_SC_MC or
                                   tc_ag_id != DEF_TC_AG_ID or tc_ag_mc != DEF_TC_AG_MC):
                    errors.append("Acumen environment check found Thomas Cook configuration errors/discrepancies:"
                                  " expected {}/{}/{}/{} but got {}/{}/{}/{}."
                                  .format(DEF_TC_SC_ID, DEF_TC_SC_MC, DEF_TC_AG_ID, DEF_TC_AG_MC,
                                          tc_sc_id, tc_sc_mc, tc_ag_id, tc_ag_mc))

                # special Acumen check for AcuServer and for the Acumen-To-Sihot interface
                if max_sync_outage_delta:
                    tbl = 'ARO' if exe_name.startswith('AcuServer') else 'RU'
                    err_msg = ora_db.select('T_SRSL', ['MAX(SRSL_DATE)'],
                                            where_group_order="SRSL_TABLE = '{}' "
                                                              "and substr(SRSL_STATUS, 1, 6) = 'SYNCED'".format(tbl))
                    if err_msg:
                        errors.append("Acumen environment T_SRSL/{} selection error: {}".format(tbl, err_msg))
                    else:
                        rows = ora_db.fetch_all()
                        if ora_db.last_err_msg:
                            errors.append("Acumen fetch T_SRSL/{} error: {}".format(tbl, ora_db.last_err_msg))
                        else:
                            newest_sync = rows[0][0]
                            # directly after WatchPupPy startup use newest_sync instead of startup-time
                            if newest_sync < last_sync:
                                last_sync, newest_sync = newest_sync, last_sync
                            if newest_sync - last_sync > max_sync_outage_delta:
                                warn_msg = "No {} since {} (longer than {})" \
                                    .format("room occupancy state changes" if tbl == 'ARO' else "reservation syncs",
                                            last_sync, max_sync_outage_delta)
                                user_notification("WatchPupPy warning notification", warn_msg)
                            last_sync = newest_sync
        if errors:  # if Acumen has failures: ensure correct values for Sihot Kernel interface check
            tc_sc_id = DEF_TC_SC_ID
            tc_sc_mc = DEF_TC_SC_MC
            tc_ag_id = DEF_TC_AG_ID
            tc_ag_mc = DEF_TC_AG_MC

        if SDI_SF in asd.used_systems:
            if not asd.connection(SDI_SF).record_type_id('Contact'):
                errors.append("Salesforce environment record type fetch error: " + asd.connection(SDI_SF).error_msg)

        if SDI_SH in asd.used_systems and SDF_SH_KERNEL_PORT in asd.used_systems[SDI_SH].features:
            gi = ClientSearch(cae)
            tc_sc_obj_id2 = gi.client_id_by_matchcode(tc_sc_mc)
            if tc_sc_id != tc_sc_obj_id2:
                errors.append("Sihot kernel check found Thomas Cook Northern matchcode discrepancy: expected={} got={}."
                              .format(tc_sc_id, tc_sc_obj_id2))
            tc_ag_obj_id2 = gi.client_id_by_matchcode(tc_ag_mc)
            if tc_ag_id != tc_ag_obj_id2:
                errors.append("Sihot kernel check found Thomas Cook AG/U.K. matchcode discrepancy: expected={} got={}."
                              .format(tc_ag_id, tc_ag_obj_id2))

        if SDI_SH in asd.used_systems and SDF_SH_WEB_PORT in asd.used_systems[SDI_SH].features:
            pm = PostMessage(cae)
            err_msg = pm.post_message("WatchPupPy Sihot WEB check for command {}".format(exe_name))
            if err_msg:
                errors.append(err_msg)

        if errors:
            continue

        # check interval / next execution
        last_check = get_timer_corrected()

        if last_check + check_interval < last_run + command_interval:
            cae.dprint(" ###  Timer={}, next check in {}s (last={} interval={}), next run in {}s (last={} interval={})"
                       .format(get_timer_corrected(),
                               last_check + check_interval - get_timer_corrected(), last_check, check_interval,
                               last_run + command_interval - get_timer_corrected(), last_run, command_interval),
                       minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            continue  # wait for next check

        # wait for next command_interval, only directly after startup checks on first run
        if get_timer_corrected() < last_run + command_interval:
            cae.dprint(" ###  Waiting for next run in {} seconds (timer={}, last={}, interval={})".format(
                last_run + command_interval - get_timer_corrected(), get_timer_corrected(), last_run, command_interval),
                minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        try:
            while get_timer_corrected() < last_run + command_interval:
                time.sleep(1)  # allow to process/raise KeyboardInterrupt within 1 second
        except KeyboardInterrupt:
            errors.append(BREAK_PREFIX + " while waiting for next command schedule in {} seconds"
                          .format(last_run + command_interval - get_timer_corrected()))
            continue  # first notify, then break in next loop because auf BREAK_PREFIX
        cae.dprint(" ###  Run command (timer={}, last={}, interval={})"
                   .format(get_timer_corrected(), last_run, command_interval), minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        # then run the command
        run_starts += 1
        try:
            if send_output:
                subprocess.check_output(command_line_args, timeout=timeout, stderr=subprocess.STDOUT,
                                        universal_newlines=True)  # shell=True
            else:
                subprocess.check_call(command_line_args, timeout=timeout)
        except subprocess.CalledProcessError as cpe:
            err_msg = "{}. run returned non-zero exit code {}".format(run_starts, cpe.returncode)
            if cpe.returncode == 4:
                reset_last_run_time()
            if getattr(cpe, 'output'):      # only available when running command with check_output()/send_output
                err_msg += "\n         output=" + str(cpe.output)
            errors.append(err_msg)
            continue        # command not really started, so try directly again - don't reset last_run variable
        except subprocess.TimeoutExpired as toe:    # sub process killed
            err_msg = "{}. run timed out at {} last sync={}; interval={}, current timer({})-last_run({})={}"\
                .format(run_starts, datetime.datetime.now(), last_sync,
                        timeout, get_timer_corrected(), last_run, get_timer_corrected() - last_run)
            if getattr(toe, 'output'):      # only available when running command with check_output()/send_output
                err_msg += "\n         output=" + str(getattr(toe, 'output'))  # PyCharm says not defined: toe.output
            errors.append(err_msg)
            reset_last_run_time(force=True)   # force reset of lock in INI file because subproc killed
            continue        # try directly again - don't reset last_run variable
        except KeyboardInterrupt:
            errors.append(BREAK_PREFIX + " while running {}. command {}".format(run_starts, exe_name))
            continue        # jump to begin of loop for to notify user, BREAK this loop and quit this app
        except Exception as ex:
            errors.append("{}. run raised unspecified exception: {}\n      {}"
                          .format(run_starts, ex, full_stack_trace(ex)))
            continue        # try directly again - don't reset last_run variable

        last_run = last_check
        last_sync = datetime.datetime.now()
        run_ends += 1
    except KeyboardInterrupt:
        errors.append(BREAK_PREFIX + " before/after running {}. command {}".format(run_starts, exe_name))
    except Exception as ex:
        errors.append("WatchPupPy loop exception: " + full_stack_trace(ex))

progress.finished(error_msg=err_msg)
if asd:
    asd.close_dbs()
uprint("####  WatchPupPy exit - successfully run {} of {} times the command {}".format(run_ends, run_starts, exe_name))
if err_count:
    uprint("****  {} runs failed".format(err_count))
