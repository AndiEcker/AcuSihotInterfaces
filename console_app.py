import sys
import os

from configparser import ConfigParser
from argparse import ArgumentParser

DEBUG_LEVEL_DISABLED = 0
DEBUG_LEVEL_ENABLED = 1
DEBUG_LEVEL_VERBOSE = 2

MAIN_SECTION_DEF = 'Settings'

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


class _DuplicateSysOut:
    def __init__(self, log_file, sys_out=ori_std_out):
        self.log_file = log_file
        self.sys_out = sys_out

    def write(self, message):
        self.sys_out.write(message)
        self.log_file.write(message)

    def __getattr__(self, attr):
        return getattr(self.sys_out, attr)


class ConsoleApp:
    def __init__(self, ver, desc, main_section=MAIN_SECTION_DEF, debug_level_def=DEBUG_LEVEL_DISABLED, log_file_def=''):
        main_fnam = sys.argv[0]
        uprint(os.path.basename(main_fnam), " V", ver)
        uprint("####  Initialization......  ####")

        self._app_name = os.path.splitext(main_fnam)[0]
        self._cfg_fnam = self._app_name + '.ini'

        self._options = dict()
        """ self._options contains predefined and user-defined options.
            The _args_parsed instance variable ensure that the command line arguments get re-parsed if add_option()
            get called after a first call to either get_option() or dprint(), which are initiating
            the re-fetch of the args and INI/cfg vars.
        """
        self._args_parsed = False
        self._log_file = None

        self._main_section = main_section
        self._cfg_parser_env = ConfigParser()
        self._cfg_parser_env.read('.console_app_env.cfg')
        self._cfg_parser_app = ConfigParser()
        self._cfg_parser_app.read(self._cfg_fnam)
        self._arg_parser = ArgumentParser(description=desc)

        self.add_option('debugLevel', 'Display additional debugging info on console output', debug_level_def, 'D',
                        choices=(DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE))
        self.add_option('logFile', 'Copy stdout and stderr into log file', log_file_def, 'L')

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
        self._arg_parser.add_argument('-' + short_opt, '--' + name, help=desc, default=cfg_val, type=type(cfg_val),
                                      choices=choices, metavar=name)
        self._options[name] = dict(desc=desc, val=value, evaluate=evaluate or eval_opt)

    def _get_cfg(self, name, section=None, default_value=None, use_env=False):
        c = self._cfg_parser_env if use_env else self._cfg_parser_app
        f = (c.getboolean if isinstance(default_value, bool)
             else (c.getfloat if isinstance(default_value, float)
                   else (c.getint if isinstance(default_value, int)
                         else c.get)))
        return f(section if section else self._main_section, name, fallback=default_value)

    def get_config(self, name, section=None, default_value=None, check_eval_only=False):
        ret = self._get_cfg(name,                                                          # app cfg
                            section=section,
                            default_value=self._get_cfg(name,                              # env app sec
                                                        section=self._app_name,
                                                        default_value=self._get_cfg(name,  # env main sec
                                                                                    section=section,
                                                                                    default_value=default_value,
                                                                                    use_env=True),
                                                        use_env=True))
        evaluate = False
        if isinstance(ret, str):
            if ret.startswith("'''") and ret.endswith("'''") or ret.startswith('"""') and ret.endswith('"""'):
                evaluate = True
                ret = ret[3:-3]
            elif ret.startswith("[[") and ret.endswith("]]") or ret.startswith("{{") and ret.endswith("}}"):
                evaluate = True
                ret = ret[1:-1]
        elif isinstance(ret, dict) or isinstance(ret, list):
            evaluate = True

        if check_eval_only:
            ret = (ret, evaluate)
        elif evaluate and isinstance(ret, str):
            try:
                ret = eval(ret)
            except Exception as ex:
                uprint("ConsoleApp.get_config() exception '{}' on evaluating the option {}"
                       + " with value '{}'".format(ex, name, ret))
        return ret

    def _parse_args(self):
        # this method should only get called once and only after all the options have been added with self.add_option().
        # self.add_option() sets the determined config file value as the default value and then following call of
        # .. _arg_parser.parse_args() overwrites it with command line argument value if given
        args = self._arg_parser.parse_args()

        for k in self._options.keys():
            val = getattr(args, k)
            if self._options[k]['evaluate']:
                try:
                    val = eval(val)
                except Exception as ex:
                    uprint("ConsoleApp._parse_args() exception '{}' on evaluating the option {}"
                           + " with value: '{}'".format(ex, k, val))
            self._options[k]['val'] = (bool(val) if isinstance(self._options[k]['val'], bool)
                                       else (float(val) if isinstance(self._options[k]['val'], float)
                                             else (int(val) if isinstance(self._options[k]['val'], int)
                                                   else val)))

        log_file = self._options['logFile']['val']
        if log_file:            # enable logging
            global app_std_out, app_std_err
            try:
                if self._log_file:
                    self._log_file.close()
                self._log_file = open(log_file, "a")
                app_std_out = sys.stdout = _DuplicateSysOut(self._log_file)
                app_std_err = sys.stderr = _DuplicateSysOut(self._log_file, sys_out=ori_std_err)
            except Exception as ex:
                uprint("****  ConsoleApp._parse_args(): enable logging exception=", ex)

        if self._options['debugLevel']['val']:
            uprint('Debug Level (' + str(DEBUG_LEVEL_VERBOSE) + '=verbose):', self._options['debugLevel']['val'])
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

    def set_option(self, name, val, cfg_fnam=None):
        err_msg = ''
        if not cfg_fnam:
            cfg_fnam = self._cfg_fnam
        self._options[name]['val'] = str(val)
        if os.path.isfile(cfg_fnam):
            try:
                cfg_parser = ConfigParser()
                cfg_parser.read(cfg_fnam)
                cfg_parser.set(self._main_section, name, str(val))
                with open(cfg_fnam, 'w') as configfile:
                    cfg_parser.write(configfile)
            except Exception as ex:
                err_msg = "****  ConsoleApp.set_option(" + str(name) + ", " + str(val) + ") exception: " + str(ex)
        else:
            err_msg = "****  INI file " + str(cfg_fnam) + " not found. Please set the INI/cfg variable " + \
                      self._main_section + "/" + str(name) + " manually to the value " + str(val)
        return err_msg

    def dprint(self, *objects, sep=' ', end='\n', file=None, minimum_debug_level=DEBUG_LEVEL_ENABLED):
        if self.get_option('debugLevel') >= minimum_debug_level:
            uprint(*objects, sep=sep, end=end, file=file)

    def shutdown(self, exit_code=0):
        if exit_code:
            uprint("****  Non-zero exit code:", exit_code)
        uprint('####  Shutdown............  ####')
        if self._log_file:
            self._log_file.close()
        sys.exit(exit_code)


class Progress:
    def __init__(self, debug_level,                         # default next message built only if >= DEBUG_LEVEL_VERBOSE
                 start_counter=0, total_count=0,            # pass either start_counter or total_counter (never both)
                 start_msg='', next_msg='', end_msg='',     # message templates/masks for start, processing and end
                 err_msg='', nothing_to_do_msg=''):
        if not next_msg and debug_level >= DEBUG_LEVEL_VERBOSE:
            next_msg = ' ###  Processing ID {processed_id}: ' + \
                       ('left' if start_counter > 0 and total_count == 0 else 'item') + \
                       ' {run_counter} of {total_count}. {err_counter} errors={err_msg}'
        self._next_msg = next_msg
        if not end_msg and not err_msg and debug_level >= DEBUG_LEVEL_ENABLED:
            end_msg = ' ###  Finished processing of {total_count} having {err_counter} failures:{err_msg}'
        self._end_msg = end_msg
        if not err_msg and debug_level >= DEBUG_LEVEL_VERBOSE:
            err_msg = ' ###  {err_counter} failures on processing item {run_counter} of {total_count}:{err_msg}'
        self._err_msg = err_msg

        self._err_counter = 0
        self._run_counter = start_counter + 1                       # def=decrementing run_counter
        self._total_count = start_counter
        self._delta = -1
        if total_count > 0:                                         # incrementing run_counter
            self._run_counter = 0
            self._total_count = total_count
            self._delta = 1
        elif start_counter <= 0:
            if nothing_to_do_msg:
                uprint(nothing_to_do_msg)
            return                                                  # RETURN -- empty set - nothing to process

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
        uprint(self._end_msg.format(run_counter=self._run_counter, total_count=self._total_count,
                                    err_counter=self._err_counter, err_msg=error_msg))
