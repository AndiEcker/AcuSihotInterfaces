import sys
import os
import datetime
from builtins import chr  # works like unichr() also in Python 2
import re
import inspect
import pprint

from configparser import ConfigParser
from argparse import ArgumentParser

# supported debugging levels
DEBUG_LEVEL_DISABLED = 0
DEBUG_LEVEL_ENABLED = 1
DEBUG_LEVEL_VERBOSE = 2
DEBUG_LEVEL_TIMESTAMPED = 3
_debug_level = DEBUG_LEVEL_DISABLED
debug_levels = {0: 'disabled', 1: 'enabled', 2: 'verbose', 3: 'timestamped'}

# default name of main config section
MAIN_SECTION_DEF = 'Settings'

# default date/time formats in config files/variables
DATE_TIME_ISO = '%Y-%m-%d %H:%M:%S.%f'
DATE_ISO = '%Y-%m-%d'

# core encoding that will always work independent from destination (console, file system, XMLParser, ...)
DEF_ENCODING = 'ascii'

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


def fix_encoding(text, encoding=DEF_ENCODING, try_counter=2, pex=None, context='ae_console_app.fix_encoding()'):
    """ used for to encode invalid char encodings in text that cannot be fixed with encoding="cp1252/utf-8/.. """
    ori_text = text
    if try_counter == 0:
        try_method = "replacing &#128 with €, &#1; with ¿1¿ and &#7; with ¿7¿ for Sihot XML"
        text = text.replace('&#1;', '¿1¿').replace('&#7;', '¿7¿').replace('&#128;', '€')
    elif try_counter == 1:
        try_method = "replacing &#NNN; with chr(NNN) for Sihot XML"
        text = re.compile("&#([0-9]+);").sub(lambda m: chr(int(m.group(0)[2:-1])), text)
    elif try_counter == 2:
        if not encoding:
            encoding = DEF_ENCODING
        try_method = "recode to backslash-replaced " + encoding + " encoding"
        text = text.encode(encoding, errors='backslashreplace').decode(encoding)
    elif try_counter == 3:
        try_method = "replacing invalid unicode code points with ¿_¿"
        text = ILLEGAL_XML_SUB.sub('¿_¿', text)
    elif try_counter == 4:
        try_method = "replacing &#NNN; and &#xNNN; with ¿?¿"
        text = re.compile("&#([0-9]+);|&#x([0-9a-fA-F]+);").sub('¿?¿', text)
    else:
        try_method = ""
        text = None
    if try_method and _debug_level >= DEBUG_LEVEL_VERBOSE:
        try:        # first try to put ori_text in error message
            uprint(pprint.pformat(context + ": " + (str(pex) + '- ' if pex else '') + try_method +
                                  ", " + DEF_ENCODING + " text:\n'" +
                                  ori_text.encode(DEF_ENCODING, errors='backslashreplace').decode(DEF_ENCODING) + "'\n",
                                  indent=12, width=120))

        except UnicodeEncodeError:
            uprint(pprint.pformat(context + ": " + (str(pex) + '- ' if pex else '') + try_method, indent=12, width=120))
    return text


def full_stack_trace(ex):
    ret = "Exception {}. Traceback:\n".format(repr(ex))

    tb = sys.exc_info()[2]
    for item in reversed(inspect.getouterframes(tb.tb_frame)[1:]):
        ret += 'File "{1}", line {2}, in {3}\n'.format(*item)
        if item[4]:
            for line in item[4]:
                ret += ' '*4 + line.lstrip()
    for item in inspect.getinnerframes(tb):
        ret += 'file "{1}", line {2}, in {3}\n'.format(*item)
        if item[4]:
            for line in item[4]:
                ret += ' '*4 + line.lstrip()
    return ret


# save original stdout/stderr
ori_std_out = sys.stdout
ori_std_err = sys.stderr
app_std_out = ori_std_out
app_std_err = ori_std_err


def uprint(*objects, sep=' ', end='\n', file=None, flush=False, encode_errors_def='backslashreplace'):
    if not file:
        file = app_std_out  # cannot be specified as argument default because ConsoleApp._check_logging() may change it
    enc = file.encoding

    # even with enc == 'UTF-8' and because of _DuplicateSysOut is also writing to file it raises the exception:
    # ..UnicodeEncodeError: 'charmap' codec can't encode character '\x9f' in position 191: character maps to <undefined>
    # if enc == 'UTF-8':
    #     print(*objects, sep=sep, end=end, file=file, flush=flush)
    # else:
    #     print(*map(lambda _: str(_).encode(enc, errors=encode_errors_def).decode(enc), objects),
    #           sep=sep, end=end, file=file, flush=flush)
    if _debug_level >= DEBUG_LEVEL_TIMESTAMPED:
        print_objects = (datetime.datetime.now().strftime(DATE_TIME_ISO),) + objects
    else:
        print_objects = objects
    try_counter = 2     # skip try_counter 0 and 1 because it is very specific to the Sihot XML interface and XMLParser
    while True:
        try:
            print(*map(lambda _: str(_).encode(enc, errors=encode_errors_def).decode(enc), print_objects),
                  sep=sep, end=end, file=file, flush=flush)
            break
        except UnicodeEncodeError:
            fixed_objects = list()
            for obj in print_objects:
                if isinstance(obj, str) or isinstance(obj, bytes):
                    obj = fix_encoding(obj, enc, try_counter)
                    if not obj:
                        raise
                fixed_objects.append(obj)
            print_objects = fixed_objects
        try_counter += 1


class _DuplicateSysOut:
    def __init__(self, log_file, sys_out=ori_std_out):
        self.log_file = log_file
        self.sys_out = sys_out

    def write(self, message):
        if self.log_file:
            try:
                self.log_file.write(message)
            except UnicodeEncodeError:
                # log file has different encoding than console, so simply replace with backslash
                enc = self.log_file.encoding
                self.log_file.write(fix_encoding(message, encoding=enc))
        self.sys_out.write(message)

    def __getattr__(self, attr):
        return getattr(self.sys_out, attr)


class Setting:
    def __init__(self, name='Unnamed', value=None, value_type=None):
        """ create new Setting instance

        :param name: optional name of the setting (only used for debugging/error-message).
        :param value: optional initial value or evaluable string expression.
        :param value_type: optional value type. cannot be changed later. will be determined latest in value getter.
        """
        super(Setting, self).__init__()
        self._name = name
        self._value = None
        self._type = value_type
        if value is not None:
            self.value = value

    @property
    def value(self):
        value = self._value
        try:
            if self._type != type(value):
                if isinstance(value, bytes):    # convert bytes to string?
                    value = str(value, encoding='utf-8')  # value.decode('utf-8', 'replace') -> shows warning in PyCharm
                if isinstance(value, str):
                    eval_expr = self._eval_str(value)
                    self._value = eval(eval_expr) if eval_expr else \
                        (bool(eval(value)) if self._type == bool else
                         (datetime.datetime.strptime(value, DATE_TIME_ISO)
                          if self._type == datetime.datetime and len(value) > 10 else
                          (datetime.datetime.strptime(value, DATE_ISO).date()
                           if self._type in (datetime.date, datetime.datetime) else
                           (self._type(value) if self._type else value))))
                elif self._type:
                    self._value = self._type(value)
            if not self._type and self._value is not None:      # the value type gets only once initialized
                self._type = type(self._value)
        except Exception as ex:
            uprint("Setting.value exception '{}' on evaluating the setting {} with value: '{}'"
                   .format(ex, self._name, value))
        return self._value

    @value.setter
    def value(self, value):
        if not self._type and not isinstance(value, str) and value is not None:
            self._type = type(value)
        self._value = value

    def convert_value(self, value):
        self.value = value
        return self.value

    @staticmethod
    def _eval_str(str_val):
        """ check str_val if needs to be evaluated and return non-empty-and-stripped-eval-string if yes else '' """
        if (str_val.startswith("'''") and str_val.endswith("'''")) \
                or (str_val.startswith('"""') and str_val.endswith('"""')):
            ret = str_val[3:-3]
        elif (str_val.startswith("[") and str_val.endswith("]")) \
                or (str_val.startswith("{") and str_val.endswith("}")) \
                or (str_val.startswith("(") and str_val.endswith(")")) \
                or (str_val.startswith("'") and str_val.endswith("'")) \
                or (str_val.startswith('"') and str_val.endswith('"')):
            ret = str_val
        else:
            ret = ''
        return ret


_config_options = None     # initialized in ConsoleApp.__init__()


class ConsoleApp:
    def __init__(self, app_version, app_desc, debug_level_def=DEBUG_LEVEL_DISABLED,
                 log_file_def='', config_eval_vars=None, additional_cfg_files=None):
        """ encapsulating ConfigParser and ArgumentParser for python console applications
            :param app_version          application version.
            :param app_desc             application description.
            :param debug_level_def      default debug level (DEBUG_LEVEL_DISABLED).
            :param log_file_def         default log file name.
            :param config_eval_vars     dict of additional application specific data values that are used in eval
                                        expressions (e.g. AcuSihotMonitor.ini).
            :param additional_cfg_files list of additional CFG/INI file names (opt. incl. abs/rel. path).
        """
        global _config_options
        self.config_eval_vars = config_eval_vars or dict()

        cwd_path = os.getcwd()
        app_path_fnam_ext = sys.argv[0]
        app_fnam = os.path.basename(app_path_fnam_ext)
        app_path = os.path.dirname(app_path_fnam_ext)

        self._app_name = os.path.splitext(app_fnam)[0]
        self._app_version = app_version

        uprint(self._app_name, " V", app_version, "  Startup", datetime.datetime.now(), app_desc)
        uprint("####  Initialization......  ####")

        """
            :var  _config_options              contains predefined and user-defined options (dict of Setting instances).
            :ivar _parsed_args          flag to ensure that the command line arguments get re-parsed if add_option()
                                        get called after a first call to methods which are initiating the re-fetch of
                                        the args and INI/cfg vars (like e.g. get_option() or dprint()).
            :ivar _log_file             file handle of currently opened log file (opened in self._parse_args()).
        """
        _config_options = dict()
        self._parsed_args = None
        self._log_file = None

        # compile list of cfg/ini files - the last file overwrites previously loaded variable values
        INI_EXT = '.ini'
        cwd_path_fnam = os.path.join(cwd_path, self._app_name)
        app_path_fnam = os.path.splitext(app_path_fnam_ext)[0]
        config_files = [os.path.join(app_path, '.console_app_env.cfg'), os.path.join(cwd_path, '.console_app_env.cfg'),
                        app_path_fnam + '.cfg', app_path_fnam + INI_EXT,
                        cwd_path_fnam + '.cfg', cwd_path_fnam + INI_EXT,
                        ]
        if additional_cfg_files:
            for cfg_fnam in additional_cfg_files:
                add_cfg_path_fnam = os.path.join(cwd_path, cfg_fnam)
                if os.path.isfile(add_cfg_path_fnam):
                    config_files.append(add_cfg_path_fnam)
                else:
                    add_cfg_path_fnam = os.path.join(app_path, cfg_fnam)
                    if os.path.isfile(add_cfg_path_fnam):
                        config_files.append(add_cfg_path_fnam)
                    elif os.path.isfile(cfg_fnam):
                        config_files.append(cfg_fnam)
                    else:
                        uprint("****  Additional config file {} not found!".format(cfg_fnam))

        # last existing INI/CFG file is default config file to write to
        for cfg_fnam in reversed(config_files):
            if cfg_fnam.endswith(INI_EXT) and os.path.isfile(cfg_fnam):
                self._cfg_fnam = cfg_fnam
                break
        else:   # .. and if there is no INI file at all then create a <APP_NAME>.INI file in the cwd
            self._cfg_fnam = cwd_path_fnam + INI_EXT

        self._cfg_parser = ConfigParser()
        self._cfg_parser.optionxform = str      # or use 'lambda option: option' to have case sensitive var names
        self._cfg_parser.read(config_files)

        self._arg_parser = ArgumentParser(description=app_desc)
        self.add_option('debugLevel', "Display additional debugging info on console output", debug_level_def, 'D',
                        choices=debug_levels.keys())
        self.add_option('logFile', "Copy stdout and stderr into log file", log_file_def, 'L')

    def add_option(self, name, desc, value, short_opt=None, choices=None):
        """ defining and adding an new option for this app as INI/CFG var and as command line argument.

            The name and desc arguments are strings that are specifying the name and short description of the option
            of the console app. The name value will also be available as long command line argument option (case-sens.).

            The value argument is specifying the default value and the type of the option. It will be used only
            if the config values are not specified in any config file. The command line argument option value
            will always overwrite this value (and any value in any config file).

            If the short option character get not passed into short_opt then the first character of the name
            is used. The short options 'D' and 'L' are used internally (recommending using only lower-case options).

            For string expressions that need to evaluated for to determine their value you either can pass
            True for the evaluate parameter or you enclose the string expression with triple high commas.
        """
        global _config_options
        self._parsed_args = None        # request (re-)parsing of command line args
        if not short_opt:
            short_opt = name[0]

        # determine config value for to use as default for command line arg
        setting = Setting(name=name, value=value)
        cfg_val = self._get_config_val(name, default_value=value)
        setting.value = cfg_val
        self._arg_parser.add_argument('-' + short_opt, '--' + name, help=desc, default=cfg_val,
                                      type=setting.convert_value, choices=choices, metavar=name)
        _config_options[name] = setting

    def add_parameter(self, *args, **kwargs):
        self._arg_parser.add_argument(*args, **kwargs)

    def _parse_args(self):
        """ this should only get called once and only after all the options have been added with self.add_option().
            self.add_option() sets the determined config file value as the default value and then following call of
            .. _arg_parser.parse_args() overwrites it with command line argument value if given
        """
        global _debug_level, _config_options
        self._parsed_args = self._arg_parser.parse_args()

        for name in _config_options.keys():
            _config_options[name].value = getattr(self._parsed_args, name)

        log_file = _config_options['logFile'].value
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
        _debug_level = _config_options['debugLevel'].value
        if _debug_level:
            uprint("Debug Level(" + ", ".join([str(k) + "=" + v for k, v in debug_levels.items()]) + "):", _debug_level)
            # print sys env - s.a. pyinstaller docs (http://pythonhosted.org/PyInstaller/runtime-information.html)
            uprint("System Environment:")
            uprint(" "*18, "argv      =", str(sys.argv))
            uprint(" "*18, "executable=", sys.executable)
            uprint(" "*18, "cwd       =", os.getcwd())
            uprint(" "*18, "__file__  =", __file__)
            uprint(" "*18, "frozen    =", getattr(sys, 'frozen', False))
            if getattr(sys, 'frozen', False):
                uprint(" "*18, "bundle-dir=", getattr(sys, '_MEIPASS', '*#ERR#*'))
            uprint(" "*18, "main-cfg  =", self._cfg_fnam)
        if log_file:
            uprint('Log file:', log_file)

    def get_option(self, name, default_value=None):
        """ get the value of the option specified by it's name.

            The returned value has the same type as the value specified in the add_option() call and is the value from
            either (ordered by precedence - first specified/found value will be returned):
            - command line arguments option
            - default section of INI file in the current working directory (cwd)
            - default section of CFG file in the current working directory (cwd)
            - default section of INI file in the application directory (where the main py or exe file is placed)
            - default section of CFG file in the application directory (where the main py or exe file is placed)
            - default section of .console_app_env.cfg in the cwd
            - default section of .console_app_env.cfg in the application directory
            - value argument passed into the add_option() method call (defining the option)
            - default_value argument passed into this method (should actually not happen-add_option() didn't get called)
        """
        if not self._parsed_args:
            self._parse_args()
        return _config_options[name].value if name in _config_options else default_value

    def set_option(self, name, val, cfg_fnam=None, save_to_config=True):
        global _debug_level, _config_options
        _config_options[name].value = val
        if name == 'debugLevel' and not save_to_config:
            _debug_level = _config_options[name].value
        return self.set_config(name, val, cfg_fnam) if save_to_config else ''

    def get_parameter(self, name):
        if not self._parsed_args:
            self._parse_args()
        return getattr(self._parsed_args, name)

    def _get_config_val(self, name, section=None, default_value=None, cfg_parser=None):
        cfg_parser = cfg_parser or self._cfg_parser
        val = cfg_parser.get(section or MAIN_SECTION_DEF, name, fallback=default_value)
        return val

    def get_config(self, name, section=None, default_value=None, cfg_parser=None, value_type=None):
        if name in _config_options and section in (MAIN_SECTION_DEF, '', None):
            val = _config_options[name].value
        else:
            s = Setting(name=name, value=default_value, value_type=value_type)  # Setting used only for conversion/eval
            s.value = self._get_config_val(name, section=section, default_value=s.value, cfg_parser=cfg_parser)
            val = s.value
        return val

    def set_config(self, name, val, cfg_fnam=None, section=None):
        global _debug_level
        if not cfg_fnam:
            cfg_fnam = self._cfg_fnam
        if not section:
            section = MAIN_SECTION_DEF

        if name in _config_options and section in (MAIN_SECTION_DEF, '', None):
            _config_options[name].value = val
            if name == 'debugLevel':
                _debug_level = _config_options[name].value

        err_msg = ''
        if os.path.isfile(cfg_fnam):
            try:
                cfg_parser = ConfigParser()     # not using self._cfg_parser for to put INI vars from other files
                cfg_parser.optionxform = str    # or use 'lambda option: option' to have case sensitive var names
                cfg_parser.read(cfg_fnam)
                if isinstance(val, dict) or isinstance(val, list) or isinstance(val, tuple):
                    str_val = "'''" + repr(val).replace('%', '%%') + "'''"
                elif type(val) is datetime.datetime:
                    str_val = val.strftime(DATE_TIME_ISO)
                elif type(val) is datetime.date:
                    str_val = val.strftime(DATE_ISO)
                else:
                    str_val = str(val)       # using str() here because repr() will put high-commas around string values
                cfg_parser.set(section, name, str_val)
                with open(cfg_fnam, 'w') as configfile:
                    cfg_parser.write(configfile)
            except Exception as ex:
                err_msg = "****  ConsoleApp.set_option(" + str(name) + ", " + str(val) + ") exception: " + str(ex)
        else:
            err_msg = "****  INI/CFG file " + str(cfg_fnam) + " not found. Please set the ini/cfg variable " + \
                      section + "/" + str(name) + " manually to the value " + str(val)
        return err_msg

    def dprint(self, *objects, sep=' ', end='\n', file=None, minimum_debug_level=DEBUG_LEVEL_ENABLED):
        if self.get_option('debugLevel') >= minimum_debug_level:
            uprint(*objects, sep=sep, end=end, file=file)

    def app_name(self):
        return self._app_name

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
                 end_msg="Finished processing of {total_count} having {err_counter} failures:{err_msg}",
                 err_msg="{err_counter} failures on processing of {total_count} items, current={run_counter}:{err_msg}",
                 nothing_to_do_msg=''):
        if not next_msg and debug_level >= DEBUG_LEVEL_VERBOSE:
            next_msg = "Processing '{processed_id}': " + \
                       ("left" if start_counter > 0 and total_count == 0 else "item") + \
                       " {run_counter} of {total_count}. {err_counter} errors={err_msg}"

        def _complete_msg_prefix(msg, pch='#'):
            return (pch in msg and msg) or msg and " " + pch * 3 + "  " + msg or ""

        self._next_msg = _complete_msg_prefix(next_msg)
        self._end_msg = _complete_msg_prefix(end_msg)
        self._err_msg = _complete_msg_prefix(err_msg, '*')

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
                uprint(_complete_msg_prefix(nothing_to_do_msg))
            return  # RETURN -- empty set - nothing to process

        if start_msg:
            uprint(_complete_msg_prefix(start_msg).format(run_counter=self._run_counter + self._delta,
                                                          total_count=self._total_count))

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
