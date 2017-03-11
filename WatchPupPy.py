"""
    0.4     changed command call from check_call() to check_output() for to determine and pass StdOut/StdErr  AND
            added outer try exception fallback into main loop (for to catch strange/unsuspected errors)
"""
import os
import time
import datetime
import subprocess
from configparser import ConfigParser

from console_app import ConsoleApp, Progress, uprint, MAIN_SECTION_DEF, DATE_ISO_FULL, DEBUG_LEVEL_VERBOSE
from db import OraDB, DEF_USER, DEF_DSN
from notification import Notification
from sxmlif import PostMessage, GuestInfo, SXML_DEF_ENCODING

__version__ = '0.4'

BREAK_PREFIX = 'User pressed Ctrl+C key'

cae = ConsoleApp(__version__, "Periodically execute and supervise command")
cae.add_option('cmdLine', "command [line] to execute", '', 'x')
cae.add_option('cmdInterval', "command interval in seconds (pass 0 for always running servers)", 3600, 's')  # ==1 hour
cae.add_option('envChecks', "Number of environment checks per command interval", 4, 'n')

cae.add_option('acuUser', "User name of Acumen/Oracle system", DEF_USER, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", DEF_DSN, 'd')

cae.add_option('serverIP', "IP address of the SIHOT interface server", 'localhost', 'i')
cae.add_option('serverPort', "IP port of the WEB interface of this server", 14777, 'w')
cae.add_option('serverKernelPort', "IP port of the KERNEL interface of this server", 14772, 'k')
cae.add_option('timeout', "Timeout value for TCP/IP connections", 39.6)
cae.add_option('xmlEncoding', "Charset used for the xml data", SXML_DEF_ENCODING, 'e')

cae.add_option('breakOnError', "Abort synchronization if an error occurs (0=No, 1=Yes)", 0, 'b')

cae.add_option('smtpServerUri', "SMTP notification server account URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP Sender/From address", '', 'f')
cae.add_option('smtpTo', "List/Expression of SMTP Receiver/To addresses", [], 'r')

if not cae.get_option('cmdLine'):
    uprint('Empty command line - Nothing to do.')
    cae.shutdown()
command_line_args = cae.get_option('cmdLine').split(' ')
uprint('Command line:', cae.get_option('cmdLine'))
uprint("Command interval/checks:", cae.get_option('cmdInterval'), cae.get_option('envChecks'))
check_acumen = cae.get_option('acuUser') and cae.get_option('acuDSN')
if check_acumen:
    uprint('Checked Acumen Usr/DSN:', cae.get_option('acuUser'), cae.get_option('acuDSN'))
last_rt_prefix = cae.get_option('acuDSN')[-4:]
check_sihot_web = cae.get_option('serverIP') and cae.get_option('serverPort')
check_sihot_kernel = cae.get_option('serverIP') and cae.get_option('serverKernelPort')
if check_sihot_web or check_sihot_kernel:
    uprint('Server IP/Web-/Kernel-port:', cae.get_option('serverIP'), cae.get_option('serverPort'),
           cae.get_option('serverKernelPort'))
    uprint('TCP Timeout/XML Encoding:', cae.get_option('timeout'), cae.get_option('xmlEncoding'))
break_on_error = cae.get_option('breakOnError')
uprint('Break on error:', 'Yes' if break_on_error else 'No')
notification = None
if cae.get_option('smtpServerUri') and cae.get_option('smtpFrom') and cae.get_option('smtpTo'):
    mail_body = 'Executing: ' + cae.get_option('cmdLine')
    notification = Notification(smtp_server_uri=cae.get_option('smtpServerUri'),
                                mail_from=cae.get_option('smtpFrom'),
                                mail_to=cae.get_option('smtpTo'),
                                used_system=cae.get_option('acuDSN') + '/' + cae.get_option('serverIP'),
                                mail_body_footer=mail_body,
                                debug_level=cae.get_option('debugLevel'))
    uprint('SMTP Uri/From/To:', cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))


command_interval = cae.get_option('cmdInterval')  # in seconds
env_checks_per_interval = cae.get_option('envChecks')

if command_interval:
    # initialize timeout to command_interval min 5% (if 1 hour than to 57 minutes) for (3 min.) error pause & recovering
    timeout = command_interval - max(command_interval // 20, 1)
else:
    timeout = None  # run server without interrupting (only re-start if crashes)
check_interval = command_interval // env_checks_per_interval
last_timer = last_run = last_check = None


def get_timer_corrected():
    """ get timer ticker value (seconds) and reset all timer vars on overflow (which should actually never happen
        with monotonic, but some OS may only support 32 bits - rolling-over after 49.7 days) """
    global last_timer, last_run, last_check
    curr_timer = time.monotonic()
    if last_timer is None or curr_timer < last_timer:
        last_run = curr_timer - command_interval
        last_check = curr_timer - check_interval
    last_timer = curr_timer
    return curr_timer

        
def reset_last_run_time(interval, force=False):
    try:
        cmd_cfg_file_name = os.path.splitext(command_line_args[0])[0] + '.ini'
        if os.path.isfile(cmd_cfg_file_name):
            cmd_cfg_parser = ConfigParser()
            cmd_cfg_parser.read(cmd_cfg_file_name)
            last_start = cmd_cfg_parser.get(MAIN_SECTION_DEF, last_rt_prefix + 'lastRt')
            if last_start[0] == '@':
                last_start_dt = datetime.datetime.strptime(last_start[1:], DATE_ISO_FULL)
                interval_delta = datetime.timedelta(seconds=interval)
                now_dt = datetime.datetime.now()
                if not force and last_start_dt + interval_delta >= now_dt:
                    msg = "still locked for " + str(last_start_dt + interval_delta - now_dt)
                else:
                    cmd_cfg_parser.set(MAIN_SECTION_DEF,
                                       last_rt_prefix + 'Rt_kill_' + datetime.datetime.now().strftime('%y%m%d_%H%M%S'),
                                       last_start)
                    cmd_cfg_parser.set(MAIN_SECTION_DEF,
                                       last_rt_prefix + 'lastRt', '-9')
                    msg = "successful reset. Old value=" + str(last_start)
            else:
                msg = ""
        else:
            msg = cmd_cfg_file_name + " not found"
    except Exception as x:
        msg = "exception: " + str(x)
    if msg:
        uprint("WatchPupPy.reset_last_run_time():", msg)
        if notification:
            err_message = notification.send_notification(msg, subject='WatchPupPy reset last run time warning')
            if err_message:
                uprint(' #### WatchPupPy send notification warning: {}. Unsent error message: {}.'
                       .format(msg, err_message))


startup = get_timer_corrected()     # initialize timer and last check/run values
cae.dprint("  ###  Startup timer value={}, last check={}, check interval={}, last run={}, run interval={}".format(
            startup, last_check, check_interval, last_run, command_interval),
           minimum_debug_level=DEBUG_LEVEL_VERBOSE)
progress = Progress(cae.get_option('debugLevel'), total_count=1,
                    start_msg='Preparing environment checks and first run of {}'.format(command_line_args))

err_msg = ''
run_starts = run_ends = err_count = 0
while True:
    try:        # outer exception fallback - only for strange/unsuspected errors
        # check for errors/warnings to be send to support
        run_msg = "Preparing {}. run (after {} runs with {} errors)".format(run_starts, run_ends, err_count)
        progress.next(processed_id=run_msg, error_msg=err_msg)
        if err_msg:
            err_count += 1
            if notification:
                send_err = notification.send_notification(err_msg, subject='WatchPupPy notification')
                if send_err:
                    uprint(' #### WatchPupPy send notification error: {}. Unsent error message: {}.'
                           .format(send_err, err_msg))
            else:
                uprint(' **** ' + err_msg)
            if break_on_error or err_msg.startswith(BREAK_PREFIX):
                break
            err_msg = ''
            time.sleep(command_interval / 30)  # wait 120 seconds after each error, for command_interval of 1 hour

        # wait for next check_interval, only directly after startup checks on first run
        if get_timer_corrected() < last_check + check_interval:
            cae.dprint("  ###  Waiting for next check in {} seconds (timer={}, last={}, interval={})".format(
                last_check + check_interval - get_timer_corrected(), get_timer_corrected(), last_check, check_interval),
                minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        try:
            while get_timer_corrected() < last_check + check_interval:
                time.sleep(1)  # allow to process/raise KeyboardInterrupt within 1 second
        except KeyboardInterrupt:
            err_msg = BREAK_PREFIX + " while waiting for next check in " \
                      + str(last_check + check_interval - get_timer_corrected()) + " seconds"
            continue  # first notify, then break in next loop because auf BREAK_PREFIX
        cae.dprint("  ###  Running checks (timer={}, last={}, interval={})".format(
            get_timer_corrected(), last_check, check_interval),
            minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        # check environment and connections: Acu/Oracle, Sihot servers and interfaces
        if check_acumen:
            ora_db = OraDB(cae.get_option('acuUser'), cae.get_option('acuPassword'), cae.get_option('acuDSN'),
                           debug_level=cae.get_option('debugLevel'))
            err_msg = ora_db.connect()
            if err_msg:
                err_msg = "Acumen environment check connection error: " + err_msg
                continue
            err_msg = ora_db.select('dual', ['sysdate'])
            if err_msg:
                ora_db.close()
                err_msg = "Acumen environment check selection error: " + err_msg
                continue
            err_msg = ora_db.select('T_RO', ['RO_SIHOT_AGENCY_OBJID', 'RO_SIHOT_AGENCY_MC'], "RO_CODE = 'TK'")
            rows = ora_db.fetch_all()
            tc_sc_obj_id = str(rows[0][0])  # == '27'
            tc_sc_mc = rows[0][1]  # == 'TCRENT'
            err_msg = ora_db.select('T_RO', ['RO_SIHOT_AGENCY_OBJID', 'RO_SIHOT_AGENCY_MC'], "RO_CODE = 'tk'")
            rows = ora_db.fetch_all()
            tc_ag_obj_id = str(rows[0][0])  # == '20'
            tc_ag_mc = rows[0][1]  # == 'TCAG'
            ora_db.close()
            if tc_sc_obj_id != '27' or tc_sc_mc != 'TCRENT' or tc_ag_obj_id != '20' or tc_ag_mc != 'TCAG':
                err_msg = ("Acumen environment check found Thomas Cook configuration errors/discrepancies:"
                           " expected {}/{}/{}/{} but got {}/{}/{}/{}.") \
                    .format('27', 'TCRENT', '20', 'TCAG', tc_sc_obj_id, tc_sc_mc, tc_ag_obj_id, tc_ag_mc)
                continue
        else:
            tc_sc_obj_id = '27'
            tc_sc_mc = 'TCRENT'
            tc_ag_obj_id = '20'
            tc_ag_mc = 'TCAG'

        if check_sihot_kernel:
            gi = GuestInfo(cae)
            tc_sc_obj_id2 = gi.get_objid_by_matchcode(tc_sc_mc)
            if tc_sc_obj_id != tc_sc_obj_id2:
                err_msg = 'Sihot kernel check found Thomas Cook Northern matchcode discrepancy: expected={} got={}.' \
                    .format(tc_sc_obj_id, tc_sc_obj_id2)
                continue
            tc_ag_obj_id2 = gi.get_objid_by_matchcode(tc_ag_mc)
            if tc_ag_obj_id != tc_ag_obj_id2:
                err_msg = 'Sihot kernel check found Thomas Cook AG/U.K. matchcode discrepancy: expected={} got={}.' \
                    .format(tc_ag_obj_id, tc_ag_obj_id2)
                continue

        if check_sihot_web:
            pm = PostMessage(cae)
            err_msg = pm.post_message("WatchPupPy Sihot WEB check for command {}".format(command_line_args[0]))
            if err_msg:
                continue

        last_check = get_timer_corrected()

        if last_check + check_interval < last_run + command_interval:
            cae.dprint("  ###  Timer={}, next check in {}s (last={} interval={}), next run in {}s (last={} interval={})"
                       .format(get_timer_corrected(),
                               last_check + check_interval - get_timer_corrected(), last_check, check_interval,
                               last_run + command_interval - get_timer_corrected(), last_run, command_interval),
                       minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            continue  # wait for next check

        # wait for next command_interval, only directly after startup checks on first run
        if get_timer_corrected() < last_run + command_interval:
            cae.dprint("  ###  Waiting for next run in {} seconds (timer={}, last={}, interval={})".format(
                last_run + command_interval - get_timer_corrected(), get_timer_corrected(), last_run, command_interval),
                minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        try:
            while get_timer_corrected() < last_run + command_interval:
                time.sleep(1)  # allow to process/raise KeyboardInterrupt within 1 second
        except KeyboardInterrupt:
            err_msg = BREAK_PREFIX + ' while waiting for next command schedule in ' \
                      + str(last_run + command_interval - get_timer_corrected()) + ' seconds'
            continue  # first notify, then break in next loop because auf BREAK_PREFIX
        cae.dprint("  ###  Run command (timer={}, last={}, interval={})".format(
            get_timer_corrected(), last_run, command_interval),
            minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        # then run the command
        run_starts += 1
        try:
            # for to get output changed from: process = subprocess.check_call(command_line_args, timeout=timeout)
            # .. to:
            output = subprocess.check_output(command_line_args, stderr=subprocess.STDOUT, timeout=timeout)  # shell=True
        except subprocess.CalledProcessError as cpe:
            err_msg = str(run_starts) + '. run returned non-zero exit code:' + str(cpe.returncode)
            if cpe.returncode == 4:
                reset_last_run_time(command_interval)
                continue  # command not really started, so try directly again - don't reset last_run variable
            err_msg += '\n' + str(cpe.output)
        except subprocess.TimeoutExpired as toe:
            err_msg = str(run_starts) + '. run timed out - current timer=' + str(get_timer_corrected()) \
                      + ', last_run=' + str(last_run) \
                      + ', output=' + str(toe.output)
            reset_last_run_time(command_interval, force=True)
            continue  # try directly again - don't reset last_run variable
        except KeyboardInterrupt:
            err_msg = BREAK_PREFIX + ' while running ' + str(run_starts) + '. command ' + str(command_line_args)
        except Exception as ex:
            err_msg = str(run_starts) + '. run raised unspecified exception: ' + str(ex)

        last_run = get_timer_corrected()
        run_ends += 1
    except Exception as ex:
        err_msg += '\n\n' + 'WatchPupPy loop exception: ' + str(ex)

progress.finished(error_msg=err_msg)
uprint(' #### WatchPupPy exit - successfully run', run_ends, 'of', run_starts, 'times the command', command_line_args)
if err_count:
    uprint(' **** ' + str(err_count) + ' runs failed.')
