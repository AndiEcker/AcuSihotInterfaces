import sys
import os
import datetime

from builtins import chr  # works like unichr() also in Python 2
import re

from configparser import ConfigParser
from argparse import ArgumentParser, ArgumentTypeError

DEBUG_LEVEL_DISABLED = 0
DEBUG_LEVEL_ENABLED = 1
DEBUG_LEVEL_VERBOSE = 2

MAIN_SECTION_DEF = 'Settings'

DATE_TIME_ISO = '%Y-%m-%d %H:%M:%S.%f'
DATE_ISO = '%Y-%m-%d'

# illegal characters in XML
# .. taken from https://stackoverflow.com/questions/1707890/fast-way-to-filter-illegal-xml-unicode-chars-in-python
ILLEGAL_XML_CHARS = [(0x00, 0x08), (0x0B, 0x0C), (0x0E, 0x1F),
                     (0x7F, 0x84), (0x86, 0x9F),
                     (0xFDD0, 0xFDDF), (0xFFFE, 0xFFFF)]
if sys.maxunicode >= 0x10000:  # not narrow build of Python
    ILLEGAL_XML_CHARS.extend([(0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF),
                              (0x3FFFE, 0x3FFFF), (0x4FFFE, 0x4FFFF),
                              (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
                              (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF),
                              (0x9FFFE, 0x9FFFF), (0xAFFFE, 0xAFFFF),
                              (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
                              (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF),
                              (0xFFFFE, 0xFFFFF), (0x10FFFE, 0x10FFFF)])
ILLEGAL_XML_SUB = re.compile(u'[%s]' % u''.join(["%s-%s" % (chr(low), chr(high)) for (low, high) in ILLEGAL_XML_CHARS]))

# save original stdout/stderr
ori_std_out = sys.stdout
ori_std_err = sys.stderr
app_std_out = ori_std_out
app_std_err = ori_std_err


def uprint(*objects, sep=' ', end='\n', file=None, flush=False, encode_errors_def='backslashreplace'):
    if not file:
        file = app_std_out  # cannot be specified as argument default because ConsoleApp._check_logging() may change it
    enc = file.encoding
    if enc == 'UTF-8':
        print(*objects, sep=sep, end=end, file=file, flush=flush)
    else:
        print(*map(lambda obj: str(obj).encode(enc, errors=encode_errors_def).decode(enc), objects),
              sep=sep, end=end, file=file, flush=flush)


def prepare_eval_str(val):
    """ check val if needs to be evaluated and return non-empty-and-stripped-eval-string if yes else '' """

    if isinstance(val, bytes):
        val = val.decode('utf-8', 'replace')  # convert bytes to string

    ret = ''
    if isinstance(val, str):
        if (val.startswith("'''") and val.endswith("'''")) \
                or (val.startswith('"""') and val.endswith('"""')):
            ret = val[3:-3]
        elif (val.startswith("[") and val.endswith("]")) \
                or (val.startswith("{") and val.endswith("}")) \
                or (val.startswith("(") and val.endswith(")")):
            ret = val

    return ret


class _DuplicateSysOut:
    def __init__(self, log_file, sys_out=ori_std_out):
        self.log_file = log_file
        self.sys_out = sys_out

    def write(self, message):
        if self.log_file:
            self.log_file.write(message)
        self.sys_out.write(message)

    def __getattr__(self, attr):
        return getattr(self.sys_out, attr)


class ConsoleApp:
    def __init__(self, ver, desc, main_section=MAIN_SECTION_DEF, debug_level_def=DEBUG_LEVEL_DISABLED, log_file_def='',
                 config_eval_vars=None):
        app_path = sys.argv[0]
        app_fnam = os.path.basename(app_path)
        self._app_name = os.path.splitext(app_fnam)[0]
        self._app_version = ver
        uprint(self._app_name, " V", ver, "  Startup", datetime.datetime.now())
        uprint("####  Initialization......  ####")

        self.config_eval_vars = config_eval_vars if config_eval_vars else dict()
        self._options = dict()
        """ self._options contains predefined and user-defined options.
            The _args_parsed instance variable ensure that the command line arguments get re-parsed if add_option()
            get called after a first call to either get_option() or dprint(), which are initiating
            the re-fetch of the args and INI/cfg vars.
        """
        self._args_parsed = False
        self._log_file = None

        # determine main config file (also for to store configs): 1st in cwd, then in app path
        cfg_fnam_cwd = os.path.join(os.getcwd(), self._app_name)
        cfg_fnam_app = os.path.splitext(app_path)[0]
        if os.path.isfile(cfg_fnam_cwd + '.cfg'):
            cfg_fnam_cwd += '.cfg'
            self._cfg_fnam = cfg_fnam_cwd
        elif os.path.isfile(cfg_fnam_cwd + '.ini'):
            cfg_fnam_cwd += '.ini'
            self._cfg_fnam = cfg_fnam_cwd
        elif os.path.isfile(cfg_fnam_app + '.cfg'):
            cfg_fnam_app += '.cfg'
            self._cfg_fnam = cfg_fnam_app
        else:
            cfg_fnam_app += '.ini'
            self._cfg_fnam = cfg_fnam_app

        self._main_section = main_section
        self._cfg_parser_cwd = ConfigParser()
        self._cfg_parser_cwd.read(cfg_fnam_cwd)
        self._cfg_parser_app = ConfigParser()
        self._cfg_parser_app.read(cfg_fnam_app)
        self._cfg_parser_env = ConfigParser()
        self._cfg_parser_env.read('.console_app_env.cfg')
        self._arg_parser = ArgumentParser(description=desc)

        self.add_option('debugLevel', "Display additional debugging info on console output", debug_level_def, 'D',
                        choices=(DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE))
        self.add_option('logFile', "Copy stdout and stderr into log file", log_file_def, 'L')

    @staticmethod
    def _parse_date_time(dat):
        try:
            return datetime.datetime.strptime(dat, DATE_TIME_ISO)
        except ValueError:
            msg = "Not a valid date/time: '{}' - expected format: {}.".format(dat, DATE_TIME_ISO)
            raise ArgumentTypeError(msg)

    @staticmethod
    def _parse_date(dat):
        try:
            return datetime.datetime.strptime(dat, DATE_ISO).date()
        except ValueError:
            msg = "Not a valid date: '{}' - expected format: {}.".format(dat, DATE_ISO)
            raise ArgumentTypeError(msg)

    def add_option(self, name, desc, value, short_opt=None, eval_opt=False, choices=None):
        """ defining and adding an new option for this console app as INI/cfg var and as command line argument.

            The name and desc arguments are strings that are specifying the name and short description of the option
            of the console app. The name value will also be available as long command line argument option (case-sens.).

            The value argument is specifying the default value and the type of the option.
            If the config values are not specified in the app config file then the option default/fallback values will
            be searched within the base config file: first in the app name section then in the default main section.
            Only if they also not there then the value argument/parameter of this method is used as the default
            value for this option. The command line argument option value will always overwrite this value.

            If the short option character get not passed into short_opt then the first character of the name
            is used. The short options 'D' and 'L' are used internally (recommending using only lower-case options).

            For string expressions that need to evaluated for to determine their value you either can pass
            True for the evaluate parameter or you enclose the string expression with triple high commas.
        """
        self._args_parsed = False
        # determine config value for to use as default for command line arg
        cfg_val, evaluate = self.get_config(name, default_value=value, check_eval_only=True)
        if not short_opt:
            short_opt = name[0]
        arg_type = type(cfg_val)
        if arg_type is datetime.datetime:
            arg_type = self._parse_date_time
        elif arg_type is datetime.date:
            arg_type = self._parse_date
        self._arg_parser.add_argument('-' + short_opt, '--' + name, help=desc, default=cfg_val, type=arg_type,
                                      choices=choices, metavar=name)
        self._options[name] = dict(desc=desc, val=value, evaluate=evaluate or eval_opt)

    def _parse_args(self):
        # this method should only get called once and only after all the options have been added with self.add_option().
        # self.add_option() sets the determined config file value as the default value and then following call of
        # .. _arg_parser.parse_args() overwrites it with command line argument value if given
        args = self._arg_parser.parse_args()

        for k in self._options.keys():
            val = getattr(args, k)
            if self._options[k]['evaluate']:
                eval_str = prepare_eval_str(val)
                if eval_str:
                    try:
                        val = eval(eval_str)
                    except Exception as ex:
                        uprint("ConsoleApp._parse_args() exception '{}' on evaluating the option {} with value: '{}'"
                               .format(ex, k, eval_str))
            def_val = self._options[k]['val']
            self._options[k]['val'] = (bool(val) if isinstance(def_val, bool)
                                       else (float(val) if isinstance(def_val, float)
                                             else (int(val) if isinstance(def_val, int)
                                                   else val)))

        log_file = self._options['logFile']['val']
        if log_file:  # enable logging
            global app_std_out, app_std_err
            try:
                if self._log_file:
                    self._log_file.close()
                self._log_file = open(log_file, "a")
                app_std_out = sys.stdout = _DuplicateSysOut(self._log_file)
                app_std_err = sys.stderr = _DuplicateSysOut(self._log_file, sys_out=ori_std_err)
            except Exception as ex:
                uprint("****  ConsoleApp._parse_args(): enable logging exception=", ex)

        uprint(self._app_name, " V", self._app_version, "  Args  parsed", datetime.datetime.now())
        uprint("####  Startup finished....  ####")

        # finished argument parsing - now print chosen option values to the console
        if self._options['debugLevel']['val']:
            uprint("Debug Level (" + str(DEBUG_LEVEL_VERBOSE) + "=verbose):", self._options['debugLevel']['val'])
            # print sys env - s.a. pyinstaller docs (http://pythonhosted.org/PyInstaller/runtime-information.html)
            uprint("System Environment: argv[0]=", sys.argv[0],
                   "executable=", sys.executable,
                   "cwd=", os.getcwd(),
                   "__file__=", __file__,
                   "frozen=", getattr(sys, 'frozen', False),
                   "bundle-dir=", getattr(sys, '_MEIPASS', '*#ERR#*') if getattr(sys, 'frozen', False)
                   else os.path.dirname(os.path.abspath(__file__)),
                   "main-cfg=", self._cfg_fnam)
        if log_file:
            uprint('Log file: ' + log_file)

        self._args_parsed = True

    def get_option(self, name, value=None):
        """ get the value of the option specified by it's name.

            The returned value has the same type as the value specified in the add_option() call and is the value from
            either (ordered by precedence - first specified value will be returned):
            - the command line args option
            - the app config/INI main section (def section name=MAIN_SECTION_DEF)
            - the env config/INI app section
            - the env config/INI main section
            - the value argument passed into the add_option() method call (defining the option)
            - the value argument passed into this method (should actually not happen - add_option() didn't get called)
        """
        if not self._args_parsed:
            self._parse_args()
        return self._options[name]['val'] if name in self._options else value

    def set_option(self, name, val, cfg_fnam=None, save_to_config=True):
        self._options[name]['val'] = val
        return self.set_config(name, val, cfg_fnam) if save_to_config else ''

    def _get_cfg(self, name, section=None, default_value=None, cfg_parser=None):
        c = cfg_parser if cfg_parser else self._cfg_parser_app
        f = (c.getboolean if isinstance(default_value, bool)
             else (c.getfloat if isinstance(default_value, float)
                   else (c.getint if isinstance(default_value, int)
                         else c.get)))
        cfg_val = f(section if section else self._main_section, name, fallback=default_value)
        if isinstance(default_value, datetime.datetime) and isinstance(cfg_val, str):
            cfg_val = datetime.datetime.strptime(cfg_val, DATE_TIME_ISO)
        elif isinstance(default_value, datetime.date) and isinstance(cfg_val, str):
            day = datetime.datetime.strptime(cfg_val, DATE_ISO)
            cfg_val = datetime.date(day.year, day.month, day.day)
        return cfg_val

    def get_config(self, name, section=None, default_value=None, check_eval_only=False):
        f = self._get_cfg
        ret = f(name,  # cwd cfg
                section=section,
                default_value=f(name,  # app cfg
                                section=section,
                                default_value=f(name,  # env app sec
                                                section=self._app_name,
                                                default_value=f(name,  # env main sec
                                                                section=section,
                                                                default_value=default_value,
                                                                cfg_parser=self._cfg_parser_env),
                                                cfg_parser=self._cfg_parser_env)),
                cfg_parser=self._cfg_parser_cwd)
        eval_str = prepare_eval_str(ret)
        if check_eval_only:  # check if caller requested to return tuple of value and eval
            ret = (ret, bool(eval_str) or isinstance(ret, list) or isinstance(ret, dict) or isinstance(ret, tuple))

        elif eval_str:
            try:
                ret = eval(eval_str)
            except Exception as ex:
                uprint("ConsoleApp.get_config() exception '{}' on evaluating the option {} with value '{}'"
                       .format(ex, name, eval_str))
        return ret

    def set_config(self, name, val, cfg_fnam=None, section=None):
        if not cfg_fnam:
            cfg_fnam = self._cfg_fnam
        if not section:
            section = self._main_section

        err_msg = ''
        if os.path.isfile(cfg_fnam):
            try:
                cfg_parser = ConfigParser()
                cfg_parser.read(cfg_fnam)
                if isinstance(val, dict) or isinstance(val, list) or isinstance(val, tuple):
                    str_val = "'''" + repr(val).replace('%', '%%') + "'''"
                elif isinstance(val, datetime.datetime):
                    str_val = val.strftime(DATE_TIME_ISO)
                elif isinstance(val, datetime.date):
                    str_val = val.strftime(DATE_ISO)
                else:
                    str_val = str(val)
                cfg_parser.set(section, name, str_val)
                with open(cfg_fnam, 'w') as configfile:
                    cfg_parser.write(configfile)
            except Exception as ex:
                err_msg = "****  ConsoleApp.set_option(" + str(name) + ", " + str(val) + ") exception: " + str(ex)
        else:
            err_msg = "****  INI file " + str(cfg_fnam) + " not found. Please set the INI/cfg variable " + \
                      section + "/" + str(name) + " manually to the value " + str(val)
        return err_msg

    def dprint(self, *objects, sep=' ', end='\n', file=None, minimum_debug_level=DEBUG_LEVEL_ENABLED):
        if self.get_option('debugLevel') >= minimum_debug_level:
            uprint(*objects, sep=sep, end=end, file=file)

    def shutdown(self, exit_code=0):
        if exit_code:
            uprint("****  Non-zero exit code:", exit_code)
        uprint('####  Shutdown............  ####')
        if self._log_file:
            app_std_err.log_file = None  # prevent calls of _DuplicateSysOut.log_file.write() to prevent exception
            app_std_out.log_file = None
            sys.stdout = ori_std_out  # set back for to prevent stack overflow/recursion error with kivy logger:
            sys.stderr = ori_std_err  # .. "Fatal Python error: Cannot recover from stack overflow"
            self._log_file.close()
        sys.exit(exit_code)


class Progress:
    def __init__(self, debug_level,  # default next message built only if >= DEBUG_LEVEL_VERBOSE
                 start_counter=0, total_count=0,  # pass either start_counter or total_counter (never both)
                 start_msg="", next_msg="",  # message templates/masks for start, processing and end
                 end_msg=" ###  Finished processing of {total_count} having {err_counter} failures:{err_msg}",
                 err_msg=" ###  {err_counter} failures on processing item {run_counter} of {total_count}:{err_msg}",
                 nothing_to_do_msg=''):
        if not next_msg and debug_level >= DEBUG_LEVEL_VERBOSE:
            next_msg = " ###  Processing '{processed_id}': " + \
                       ("left" if start_counter > 0 and total_count == 0 else "item") + \
                       " {run_counter} of {total_count}. {err_counter} errors={err_msg}"
        self._next_msg = next_msg
        self._end_msg = end_msg
        self._err_msg = err_msg

        self._err_counter = 0
        self._run_counter = start_counter + 1  # def=decrementing run_counter
        self._total_count = start_counter
        self._delta = -1
        if total_count > 0:  # incrementing run_counter
            self._run_counter = 0
            self._total_count = total_count
            self._delta = 1
        elif start_counter <= 0:
            if nothing_to_do_msg:
                uprint(nothing_to_do_msg)
            return  # RETURN -- empty set - nothing to process

        if start_msg:
            uprint(start_msg.format(run_counter=self._run_counter + self._delta, total_count=self._total_count))

    def next(self, processed_id='', error_msg='', next_msg=''):
        self._run_counter += self._delta
        if error_msg:
            self._err_counter += 1

        if error_msg and self._err_msg:
            uprint(self._err_msg.format(run_counter=self._run_counter, total_count=self._total_count,
                                        err_counter=self._err_counter, err_msg=error_msg, processed_id=processed_id))

        if not next_msg:
            next_msg = self._next_msg
        if next_msg:
            # using uprint with end parameter instead of leading \r will NOT GET DISPLAYED within PyCharm,
            # .. also not with flush - see http://stackoverflow.com/questions/34751441/
            # when-writing-carriage-return-to-a-pycharm-console-the-whole-line-is-deleted
            # .. uprint('   ', pend, end='\r', flush=True)
            next_msg = '\r' + next_msg
            uprint(next_msg.format(run_counter=self._run_counter, total_count=self._total_count,
                                   err_counter=self._err_counter, err_msg=error_msg, processed_id=processed_id))

    def finished(self, error_msg=''):
        if error_msg and self._err_msg:
            uprint(self._err_msg.format(run_counter=self._run_counter, total_count=self._total_count,
                                        err_counter=self._err_counter, err_msg=error_msg))
        uprint(self.get_end_message(error_msg=error_msg))

    def get_end_message(self, error_msg=''):
        return self._end_msg.format(run_counter=self._run_counter, total_count=self._total_count,
                                    err_counter=self._err_counter, err_msg=error_msg)
