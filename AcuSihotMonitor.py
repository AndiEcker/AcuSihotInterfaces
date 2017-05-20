"""
    0.1     first beta.
    0.2     first release: added "please wait" messages using Clock.schedule_once().
    0.3     ported to Python 3.5 with the option to use the angle backend (via KIVY_GL_BACKEND=angle_sdl2 env var).
"""
import datetime
from functools import partial
from traceback import print_exc

from kivy.config import Config      # window size have to be specified before any other kivy imports
Config.set('graphics', 'width', '1800')
Config.set('graphics', 'height', '999')
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.actionbar import ActionButton, ActionGroup, ActionView, ActionToggleButton  # ActionCheck
from kivy.uix.popup import Popup
from kivy.lang.builder import Factory
from kivy.properties import BooleanProperty, NumericProperty, StringProperty, DictProperty, ObjectProperty
from kivy.clock import Clock

from ae_console_app import ConsoleApp, uprint, DEBUG_LEVEL_VERBOSE
from ae_calendar import DateChangeScreen
from ae_db import OraDB, DEF_USER, DEF_DSN
from acu_sihot_config import Data
from sxmlif import AcuServer, PostMessage, ConfigDict, CatRooms, ResToSihot, ResSearch, \
    SXML_DEF_ENCODING, PARSE_ONLY_TAG_PREFIX


__version__ = '0.3'


ROOT_BOARD_NAME = 'All'
BACK_BOARD_NAME = 'BACK'
REFRESH_BOARD_PREFIX = 'REFRESH '

LIST_ITEM_HEIGHT = 39
MAX_LIST_ITEMS = 369

DATE_DISPLAY_FORMAT = '%d/%m/%Y'

FILTER_CRITERIA_SUFFIX = '_criteria'
FILTER_SELECTION_SUFFIX = '_selection'
FILTER_CRITERIA_SEP = '::'

COLUMN_ATTRIBUTE_SEP = '__'

cae = ConsoleApp(__version__, "Monitor the Acumen and Sihot interfaces and servers",
                 config_eval_vars=dict(date_format=DATE_DISPLAY_FORMAT))
cae.add_option('acuUser', "User name of Acumen/Oracle system", DEF_USER, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", DEF_DSN, 'd')

cae.add_option('serverIP', "IP address of the Sihot interface server", 'localhost', 'i')
cae.add_option('serverPort', "IP port of the Sihot WEB interface", 14777, 'w')
cae.add_option('serverKernelPort', "IP port of the Sihot KERNEL interface", 14772, 'k')
cae.add_option('timeout', "Timeout value for TCP/IP connections to Sihot", 39.6)
cae.add_option('xmlEncoding', "Charset used for the Sihot xml data", SXML_DEF_ENCODING, 'e')

uprint('Acumen Usr/DSN:', cae.get_option('acuUser'), cae.get_option('acuDSN'))
uprint('Server IP/Web-/Kernel-port:', cae.get_option('serverIP'), cae.get_option('serverPort'),
       cae.get_option('serverKernelPort'))
uprint('TCP Timeout/XML Encoding:', cae.get_option('timeout'), cae.get_option('xmlEncoding'))


config_data = None      # public Data() instance for Acumen config/data fetches


""" TESTS """


def run_check(check_name, data_dict):
    try:
        if 'from_join' in data_dict:  # direct query/fetch against/from Acumen
            bind_vars = {_[:-len(FILTER_CRITERIA_SUFFIX)]: data_dict[_] for _ in data_dict
                         if _.endswith(FILTER_CRITERIA_SUFFIX)}
            acu_db = connect_db()
            err_msg = acu_db.select(from_join=data_dict['from_join'], cols=data_dict['cols'],
                                    where_group_order=data_dict.get('where_group_order'), bind_vars=bind_vars)
            if err_msg:
                cae.dprint('AcuSihotMonitor.run_check() select error:', err_msg)
                results = (err_msg,)
            else:
                results = (acu_db.fetch_all(), acu_db.selected_column_names())
            acu_db.close()

        elif check_name == 'Time Sync':
            results = (ass_test_time_sync(),)
        elif check_name == 'Link Alive':
            results = (ass_test_link_alive(),)

        elif check_name == 'Sihot Reservation Discrepancies':
            results = sih_reservation_discrepancies(data_dict)
        elif check_name == 'Sihot Reservation Search':
            results = sih_reservation_search(data_dict)
        elif check_name == 'Notification':
            results = (sih_test_notification(),)

        elif check_name == 'Agency Match Codes':
            results = (cfg_agency_match_codes(),)
        elif check_name == 'Agency Object Ids':
            results = (cfg_agency_obj_ids(),)

        else:
            results = ("Unknown Check Name '{}'".format(check_name),)
    except Exception as ex:
        print_exc()
        results = ("run_check() exception: " + str(ex),)

    return results


def _ass_test_method(method):
    global cae
    old_val = cae.get_option('serverPort')
    cae.set_option('serverPort', 11000, save_to_config=False)
    ret = method()
    cae.set_option('serverPort', old_val, save_to_config=False)
    return ret


def ass_test_time_sync():
    return _ass_test_method(AcuServer(cae).time_sync)


def ass_test_link_alive():
    return _ass_test_method(AcuServer(cae).link_alive)


def sih_reservation_discrepancies(data_dict):
    beg_day = data_dict['first_arrival_criteria']  # datetime.datetime.today()
    end_day = beg_day + datetime.timedelta(days=int(data_dict['days_criteria']))
    req = ResToSihot(cae)
    results = req.fetch_all_valid_from_acu("ARR_DATE < DATE'" + end_day.strftime('%Y-%m-%d') + "'"
                                           " and DEP_DATE > DATE'" + beg_day.strftime('%Y-%m-%d') + "'")
    if results:
        # error message
        results = (results,)
    else:   # no error message then process fetched rows
        err_sep = '//'
        results = []
        for crow in req.rows:
            if crow['SIHOT_GDSNO']:
                rs = ResSearch(cae)
                rd = rs.search(gdsno=crow['SIHOT_GDSNO'])
                row_err = ''
                if rd and isinstance(rd, list):
                    # compare reservation for errors/discrepancies
                    if len(rd) != 1:
                        row_err += err_sep + 'Res. count AC=1 SH=' + str(len(rd)) + \
                                   ('(' + ','.join([rd[n]['_RES-HOTEL'].get('elemVal', '') + '='
                                                   + str(rd[n]['ARR'].get('elemVal')) + '...'
                                                   + str(rd[n]['DEP'].get('elemVal')) for n in range(len(rd))]) + ')'
                                    if cae.get_option('debugLevel') >= DEBUG_LEVEL_VERBOSE else '')
                    row_err = _sih_check_all_res(crow, rd, row_err, err_sep)
                elif rd:
                    row_err += err_sep + 'Unexpected search result=' + str(rd)
                else:
                    row_err += err_sep + 'Sihot interface search error text=' + rs.response.error_text + \
                               ' msg=' + str(rs.response.msg)
                if row_err:
                    results.append((crow['SIHOT_GDSNO'], crow['CD_CODE'], crow['RUL_SIHOT_RATE'],
                                    crow['ARR_DATE'].strftime('%d-%m-%Y'), row_err[len(err_sep):]))
            else:
                results.append(('RU' + str(crow['RUL_PRIMARY']), '(not check-able because RU deleted)'))
        results = (results, ('GDS_NO__18', 'Guest Ref__18', 'RO__06', 'Arrival__18', 'Discrepancy__72L'))

    return results if results else ('No discrepancies found for date range {}..{}.'.format(beg_day, end_day),)


def _sih_check_all_res(crow, rd, row_err, err_sep):
    max_offset = datetime.timedelta(days=config_data.room_change_max_days_diff)
    acu_sep = ' AC='
    sih_sep = ' SH='
    for n in range(len(rd)):
        if len(rd) > 1:
            sih_sep = ' SH' + str(n + 1) + '='
        if rd[n]['GDSNO'].get('elemVal') != crow['SIHOT_GDSNO']:
            row_err += err_sep + 'GDS no mismatch' + \
                       acu_sep + str(crow['SIHOT_GDSNO']) + \
                       sih_sep + str(rd[n]['GDSNO'].get('elemVal'))
        if abs(datetime.datetime.strptime(rd[n]['ARR'].get('elemVal'), '%Y-%m-%d') - crow['ARR_DATE']) > max_offset:
            row_err += err_sep + 'Arrival date offset more than ' + str(max_offset.days) + ' days' + \
                       acu_sep + crow['ARR_DATE'].strftime('%Y-%m-%d') + \
                       sih_sep + str(rd[n]['ARR'].get('elemVal'))
        if abs(datetime.datetime.strptime(rd[n]['DEP'].get('elemVal'), '%Y-%m-%d') - crow['DEP_DATE']) > max_offset:
            row_err += err_sep + 'Departure date offset more than ' + str(max_offset.days) + ' days' + \
                       acu_sep + crow['DEP_DATE'].strftime('%Y-%m-%d') + \
                       sih_sep + str(rd[n]['DEP'].get('elemVal'))
        if rd[n]['RT'].get('elemVal') != crow['SH_RES_TYPE']:
            row_err += err_sep + 'Res. status mismatch' + \
                       acu_sep + str(crow['SH_RES_TYPE']) + \
                       sih_sep + str(rd[n]['RT'].get('elemVal'))
        # Marketcode-no is mostly empty in Sihot RES-SEARCH response!!!
        if rd[n]['MARKETCODE-NO'].get('elemVal') and rd[n]['MARKETCODE-NO'].get('elemVal') != crow['RUL_SIHOT_RATE']:
            row_err += err_sep + 'Market segment mismatch' + \
                       acu_sep + str(crow['RUL_SIHOT_RATE']) + \
                       sih_sep + str(rd[n]['MARKETCODE-NO'].get('elemVal'))
        # RN can be empty/None - prevent None != '' false posit.
        if rd[n]['RN'].get('elemVal', crow['RUL_SIHOT_ROOM']) and rd[n]['RN'].get('elemVal') != crow['RUL_SIHOT_ROOM']:
            row_err += err_sep + 'Room no mismatch' + \
                       acu_sep + str(crow['RUL_SIHOT_ROOM']) + \
                       sih_sep + str(rd[n]['RN'].get('elemVal'))
        elif rd[n]['_RES-HOTEL'].get('elemVal') and rd[n]['_RES-HOTEL'].get('elemVal') != str(crow['RUL_SIHOT_HOTEL']):
            row_err += err_sep + 'Hotel-ID mismatch' + \
                       acu_sep + str(crow['RUL_SIHOT_HOTEL']) + \
                       sih_sep + str(rd[n]['_RES-HOTEL'].get('elemVal'))
        elif rd[n]['ID'].get('elemVal') and str(rd[n]['ID'].get('elemVal')) != str(crow['RUL_SIHOT_HOTEL']):
            # actually the hotel ID is not provided within the Sihot interface response xml?!?!?
            row_err += err_sep + 'Hotel ID mismatch' + \
                       acu_sep + str(crow['RUL_SIHOT_HOTEL']) + \
                       sih_sep + str(rd[n]['ID'].get('elemVal'))

    return row_err


def sih_reservation_search(data_dict):
    list_marker_prefix = '*'
    result_columns = [PARSE_ONLY_TAG_PREFIX + 'RES-HOTEL__03', 'GDSNO__09',
                      PARSE_ONLY_TAG_PREFIX + 'RES-NR__06',
                      PARSE_ONLY_TAG_PREFIX + 'SUB-NR__03',
                      list_marker_prefix + 'MATCHCODE__15', list_marker_prefix + 'NAME__21',
                      'ARR__09', 'DEP__09', 'RN__06', PARSE_ONLY_TAG_PREFIX + 'OBJID__06']
    rs = ResSearch(cae)
    # available filters: hotel_id, from_date, to_date, matchcode, name, gdsno, flags, scope
    filters = {k[:-len(FILTER_CRITERIA_SUFFIX)]: v for k, v in data_dict.items() if k.endswith(FILTER_CRITERIA_SUFFIX)}
    rd = rs.search(**filters)
    results = list()
    if rd and isinstance(rd, list):
        for row in rd:
            # col_values = [(str(row[col[len(list_marker_prefix):]]['elemListVal'])
            #                if col[:len(list_marker_prefix)] == list_marker_prefix
            #                   and 'elemListVal' in row[col[len(list_marker_prefix):]]
            #                else row[col]['elemVal'])
            #               if col in row or col[len(list_marker_prefix):] in row else '(undef.)'
            #               for col in result_columns]
            col_values = []
            for c in result_columns:
                is_list = c.startswith(list_marker_prefix)
                if is_list:
                    c = c[len(list_marker_prefix):]
                if COLUMN_ATTRIBUTE_SEP in c:
                    c = c.split(COLUMN_ATTRIBUTE_SEP)[0]
                if c not in row:
                    col_val = '(undef.)'
                elif is_list and 'elemListVal' in row[c]:
                    col_val = str(row[c]['elemListVal'])
                elif 'elemVal' in row[c]:
                    col_val = row[c]['elemVal']
                else:
                    col_val = '(missing)'
                col_values.append(col_val)
            results.append(col_values)
        column_names = []
        for c in result_columns:
            if c.startswith(list_marker_prefix):
                c = c[len(list_marker_prefix):]
            if c.startswith(PARSE_ONLY_TAG_PREFIX):
                c = c[len(PARSE_ONLY_TAG_PREFIX):]
            column_names.append(c)
        results = (results, tuple(column_names))

    return results


def sih_test_notification():
    return 'NOT IMPLEMENTED'


def cfg_agency_match_codes():
    agencies = config_data.load_view(None, 'T_RO', ['RO_CODE'], "RO_SIHOT_AGENCY_MC is not NULL")
    ret = ""
    for agency in agencies:
        ret += ", " + agency[0] + "=" + config_data.get_ro_agency_matchcode(agency[0])
    return ret[2:]


def cfg_agency_obj_ids():
    agencies = config_data.load_view(None, 'T_RO', ['RO_CODE'], "RO_SIHOT_AGENCY_OBJID is not NULL")
    ret = ""
    for agency in agencies:
        ret += ", " + agency[0] + "=" + str(config_data.get_ro_agency_objid(agency[0]))
    return ret[2:]


""" HELPERS """


def connect_db():
    """ open Oracle database connection """
    acu_db = OraDB(cae.get_option('acuUser'), cae.get_option('acuPassword'),
                   cae.get_option('acuDSN'), debug_level=cae.get_option('debugLevel'))
    acu_db.connect()
    return acu_db


""" UI """


class MainWindow(FloatLayout):
    pass


class CheckItem(BoxLayout):
    data_dict = DictProperty()


class FixedActionGroup(ActionGroup):
    def fixed_clear_widgets(self):  # cannot override ActionGroup.clear_widgets() because show_group() is using it
        super(FixedActionGroup, self).clear_widgets()
        self.list_action_item = []  # missing in ActionGroup.clear_widgets() ?!?!?
        self._list_overflow_items = []

    def fixed_remove_widget(self, widget):
        super(FixedActionGroup, self).remove_widget(widget)
        if widget in self.list_action_item:
            self.list_action_item.remove(widget)
        if widget in self._list_overflow_items:
            self._list_overflow_items.remove(widget)


class FixedActionView(ActionView):
    def fixed_remove_widget(self, widget):
        """ ONLY NEEDED FOR OVERRIDE remove_widget(): 
        try:
            super(FixedActionView, self).remove_widget(widget)
        except ValueError:
            # ignoring exception within ActionView.remove_widget() trying to remove children of
            # .. ActionOverflow from ActionView._list_action_items
            pass
        """
        super(FixedActionView, self).remove_widget(widget)

        if widget in self._list_action_group:
            self._list_action_group.remove(widget)


class FilterActionButton(ActionButton):
    criteria_name = StringProperty()
    criteria_type = ObjectProperty()


class FilterSelectionGroup(FixedActionGroup):
    pass


class FilterSelectionItem(ActionButton):
    criteria_name = StringProperty()
    criteria_type = ObjectProperty()


class FilterSelectionButton(FilterSelectionItem):
    """ ActionButton for to select a single filter value from a selection list """


class FilterSelectionToggleButton(FilterSelectionItem):
    """ ActionToggleButton for to toggle item within multi_select filter check list """


class CapitalInput(TextInput):
    def insert_text(self, substring, from_undo=False):
        return super(CapitalInput, self).insert_text(substring.upper(), from_undo=from_undo)


class AcuSihotMonitorApp(App):
    landscape = BooleanProperty()
    list_header_height = NumericProperty()
    user_name = StringProperty(cae.get_option('acuUser'))
    user_password = StringProperty(cae.get_option('acuPassword'))

    def __init__(self, **kwargs):
        super(AcuSihotMonitorApp, self).__init__(**kwargs)
        self.ca = cae

        self.config_dict = ConfigDict(cae)
        self.post_message = PostMessage(cae)
        self.cat_rooms = CatRooms(cae)

        self.check_list = cae.get_config('checks', default_value=cae.get_config('checks_template'))
        cae.dprint("AcuSihotMonitorApp.__init__() check_list", self.check_list, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        # self.boards = {k:v for ci in self.checks}
        self.board_history = []

        self.filter_widgets = []
        self.filter_change_popup = None
        self.filter_change_criteria = ''

        self.app_started = False
        self.main_win = None
        self.logon_win = None

    def build(self):
        cae.dprint('AcuSihotMonitorApp.build()', minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        self.root = FloatLayout()
        self.main_win = MainWindow()
        self.logon_win = Factory.LogonWindow()
        usr = cae.get_option('acuUser')
        pwd = cae.get_option('acuPassword')
        if usr and pwd and self.init_config_data(usr, pwd, cae.get_option('acuDSN')):
            self.root.add_widget(self.main_win)
            self.go_to_board(ROOT_BOARD_NAME)
        else:
            self.root.add_widget(self.logon_win)
        return self.root

    @staticmethod
    def init_config_data(user_name, user_pass, db_dsn):
        global config_data
        config_data = Data(user_name, user_pass, db_dsn)
        if config_data.error_message:
            pu = Popup(title='Logon Error', content=Label(text=config_data.error_message), size_hint=(.9, .3))
            pu.open()
            return False
        return True

    def logon(self):
        user_name = self.logon_win.ids.user_name.text
        user_pass = self.logon_win.ids.user_password.text
        if self.init_config_data(user_name, user_pass, cae.get_option('acuDSN')):
            cae.set_option('acuUser', user_name)
            cae.set_option('acuPassword', user_pass, save_to_config=False)
            self.root.clear_widgets()
            self.root.add_widget(self.main_win)
            self.go_to_board(ROOT_BOARD_NAME)

    @staticmethod
    def exit_app():
        cae.shutdown()

    def screen_size_changed(self):
        self.landscape = self.root.width >= self.root.height

    def on_start(self):
        cae.dprint('AcuSihotMonitorApp.on_start()', minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        self.app_started = True

    def board_items(self, board_name):
        return [ci for ci in self.check_list
                if (board_name == ROOT_BOARD_NAME and 'parent_board' not in ci)
                or ('parent_board' in ci and ci['parent_board'] == board_name)
                ]

    def board_item_indexes(self, board_name):
        return [i for i in range(len(self.check_list))
                if (board_name == ROOT_BOARD_NAME and 'parent_board' not in self.check_list[i])
                or ('parent_board' in self.check_list[i] and self.check_list[i]['parent_board'] == board_name)
                ]

    def check_index(self, check_name):
        return [i for i in range(len(self.check_list)) if self.check_list[i]['name'] == check_name][0]

    def is_parent_item(self, check_name):
        return [cid for cid in self.check_list if 'parent_board' in cid and cid['parent_board'] == check_name]

    def get_background_color(self, board_name):
        """ determines the background_color from the current board or a parent board """
        while True:
            check_items = [ci for ci in self.check_list if ci['name'] == board_name]
            if not check_items:
                return 0, .36, .36, 1
            check_item = check_items[0]
            if 'background_color' in check_item:
                break
            board_name = check_item['parent_board']
        return check_item['background_color']

    def go_to_board(self, board_name):
        cae.dprint('AcuSihotMonitorApp.go_to_board()', board_name, 'Stack=', self.board_history,
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        if board_name != BACK_BOARD_NAME:
            self.board_history.append(board_name)
        elif len(self.board_history) >= 2:
            self.board_history.pop()
            board_name = self.board_history[-1]
        else:
            board_name = ROOT_BOARD_NAME
        self.main_win.ids.action_previous.title += " (displaying board " + board_name + " - please wait)"
        cb = partial(self.display_board, board_name)
        Clock.schedule_once(cb)

    def display_board(self, board_name, *_):
        cae.dprint('AcuSihotMonitorApp.display_board()', board_name, _, 'Stack=', self.board_history,
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        mw = self.main_win
        av = mw.ids.action_view

        bg = mw.ids.board_group
        bg.fixed_clear_widgets()

        cg = mw.ids.check_group
        cg.fixed_clear_widgets()

        lg = mw.ids.list_group
        lg.fixed_clear_widgets()

        lig = mw.ids.list_grid
        lig.clear_widgets()

        if self.filter_widgets:
            for w in self.filter_widgets:
                av.fixed_remove_widget(w)
            self.filter_widgets = []

        lih = mw.ids.list_header
        lih.clear_widgets()
        self.list_header_height = 0

        child_indexes = self.board_item_indexes(board_name)
        if child_indexes:
            for check_index in child_indexes:
                check_item = self.check_list[check_index]
                if 'background_color' not in check_item:
                    check_item['background_color'] = self.get_background_color(board_name)

                if self.is_parent_item(check_item['name']):
                    bm = Factory.BoardMenu(text=check_item['name'])
                    bg.add_widget(bm)
                else:
                    lm = Factory.ListMenu(text=check_item['name'])
                    lg.add_widget(lm)

                ci = Factory.CheckItem(data_dict=check_item)
                # because kivy is still missing a ReferenceDictProperty we have to put the shallow copy of the
                # .. check_item data dict (passed to the CheckItem constructor) from DictProperty back to check_list
                self.check_list[check_index] = ci.data_dict
                lig.add_widget(ci)

                cm = Factory.CheckMenu(text=check_item['name'])
                cg.add_widget(cm)

        else:
            board_index = self.check_index(board_name)
            board_dict = self.check_list[board_index]
            result = board_dict.get('check_result')
            if isinstance(result, list):
                self.list_header_height = LIST_ITEM_HEIGHT
                cas = board_dict.get('column_attributes')
                for ca in cas:
                    chl = Factory.ListItem(**self.label_attributes(ca, ca['column_name']))
                    lih.add_widget(chl)
                for idx, rd in enumerate(result):
                    lii = BoxLayout(size_hint_y=None, height=LIST_ITEM_HEIGHT)
                    for cd, ca in zip(rd, cas):
                        cil = Factory.ListItem(**self.label_attributes(ca, str(cd)))
                        lii.add_widget(cil)
                    lig.add_widget(lii)
                    if idx >= MAX_LIST_ITEMS:
                        lii = BoxLayout(size_hint_y=None, height=LIST_ITEM_HEIGHT)
                        cil = Label(text="MAXIMUM LIST ITEMS REACHED - {} items hidden".format(len(result) - idx))
                        lii.add_widget(cil)
                        lig.add_widget(lii)
                        break

            else:
                if not isinstance(result, str):
                    result = self.result_text(board_dict)
                lii = BoxLayout(size_hint_y=None, height=69)
                cil = Label(text=result)
                lii.add_widget(cil)
                lig.add_widget(lii)

            cm = Factory.CheckMenu(text=REFRESH_BOARD_PREFIX + board_name)
            cg.add_widget(cm)

            self._add_filters_to_actionview(av, board_dict)

        if board_name != ROOT_BOARD_NAME:
            bg.add_widget(Factory.BoardMenu(text=BACK_BOARD_NAME))

        mw.ids.action_previous.title = board_name

        if self.app_started:  # prevent crash on app startup
            # first two leads to a crash and do_layout() is not showing the filter groups
            # av.width += 1
            # av.on_width(av.width)
            # this is working without crash, but is not showing the filter groups:
            # av.do_layout()
            # this one is not showing the filter groups
            # Clock.schedule_once(av.do_layout, 1.0)
            # the next line is mostly working if the timeout value is given and greater/equal 0.8
            # .. (but did crash sometimes with 0.9 and even with 1.6):
            # now after adding app_startup and not doing a refresh on app startup the following call is working even
            # .. with 0.3 seconds, but I want to go back and try do_layout directly:
            # Clock.schedule_once(partial(av.on_width, av.width), 0.3) #3.6)
            # calling directly av.do_layout() - with or without Clock-schedule_once() is still not showing the entries
            # .. within the drop downs - so going back to
            # Clock.schedule_once(av.do_layout, 0.3)
            Clock.schedule_once(partial(av.on_width, av.width), 0.3)

    def _add_filters_to_actionview(self, action_view, board_dict):
        for k in board_dict:
            if k.endswith(FILTER_CRITERIA_SUFFIX):
                filter_name = k[:-len(FILTER_CRITERIA_SUFFIX)]
                filter_value = board_dict[k]
                filter_type = type(filter_value)
                if filter_type is datetime.date:
                    filter_value = filter_value.strftime(DATE_DISPLAY_FORMAT)
                else:
                    filter_value = str(filter_value)    # convert to string if multi_select
                filter_value += FILTER_CRITERIA_SEP
                if self.landscape:
                    filter_value += filter_name
                if filter_name + FILTER_SELECTION_SUFFIX in board_dict:
                    filter_selection = board_dict[filter_name + FILTER_SELECTION_SUFFIX]
                    if isinstance(filter_selection, dict) and 'from_join' in filter_selection:
                        acu_db = connect_db()
                        err_msg = acu_db.select(from_join=filter_selection['from_join'],
                                                cols=filter_selection['cols'],
                                                where_group_order=filter_selection.get('where_group_order'),
                                                bind_vars=filter_selection.get('bind_vars', {}))
                        if err_msg:
                            cae.dprint('AcuSihotMonitor._add_filters_to_actionview() select error:', err_msg)
                            continue
                        results = [r[0] for r in acu_db.fetch_all()]
                        acu_db.close()
                    else:
                        results = filter_selection  # hard coded list of selection values
                    fw = FilterSelectionGroup(text=filter_value, mode='spinner')
                    if isinstance(board_dict[filter_name + FILTER_CRITERIA_SUFFIX], list):
                        for r in results:
                            ab = FilterSelectionToggleButton(text=r, state='down' if r in board_dict[k] else 'normal',
                                                             criteria_name=filter_name, criteria_type=filter_type)
                            fw.add_widget(ab)
                    else:
                        for r in results:
                            ab = FilterSelectionButton(text=r, criteria_name=filter_name, criteria_type=filter_type)
                            fw.add_widget(ab)
                else:
                    fw = FilterActionButton(text=filter_value, criteria_name=filter_name, criteria_type=filter_type)
                action_view.add_widget(fw)
                self.filter_widgets.append(fw)
                if filter_name + FILTER_SELECTION_SUFFIX in board_dict:
                    fw.show_group()

    def change_filter(self, old_value, criteria_name, criteria_type, *_):
        cae.dprint('AcuSihotMonitorApp.change_filter():', old_value, criteria_name, criteria_type, _,
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        old_value = old_value.split(FILTER_CRITERIA_SEP)[0]
        if criteria_type is datetime.date:
            dc = DateChangeScreen(selected_date=datetime.datetime.strptime(old_value, DATE_DISPLAY_FORMAT).date())
            pu = Popup(title='Change Date', content=dc, size_hint=(.9, .9))
        else:
            ti = TextInput(text=old_value)
            pu = Popup(title='Change Filter', content=ti, size_hint=(.6, .3), on_dismiss=self.char_changed)
        pu.open()
        self.filter_change_popup = pu
        self.filter_change_criteria = criteria_name

    def date_changed(self, new_date, *_):
        cae.dprint('AcuSihotMonitorApp.date_changed():', new_date, _, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        if self.filter_change_popup:
            self.filter_change_popup.dismiss()
            self.filter_change_popup = None
        self.filter_changed(new_date)

    def char_changed(self, *_):
        cae.dprint('AcuSihotMonitorApp.char_changed():', self.filter_change_popup.content.text, _,
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        self.filter_changed(self.filter_change_popup.content.text)

    def filter_selected(self, new_value, criteria_name, criteria_type, *_):
        cae.dprint('AcuSihotMonitorApp.filter_selected():', new_value, criteria_name, criteria_type, _,
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        self.filter_change_criteria = criteria_name
        if criteria_type is datetime.date:
            new_value = new_value.strftime(DATE_DISPLAY_FORMAT)
        self.filter_changed(new_value)

    def filter_changed(self, new_value):
        cae.dprint('AcuSihotMonitorApp.filter_changed():', new_value, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        # will be done by display_board() anyway: self.filter_widgets.text = new_date.strftime(DATE_DISPLAY_FORMAT)
        title_obj = self.main_win.ids.action_previous
        curr_check = title_obj.title
        check_dict = self.check_list[self.check_index(curr_check)]
        if isinstance(check_dict[self.filter_change_criteria + FILTER_CRITERIA_SUFFIX], list):  # multi_select
            if new_value in check_dict[self.filter_change_criteria + FILTER_CRITERIA_SUFFIX]:
                check_dict[self.filter_change_criteria + FILTER_CRITERIA_SUFFIX].remove(new_value)
            else:
                check_dict[self.filter_change_criteria + FILTER_CRITERIA_SUFFIX].append(new_value)
        else:
            check_dict[self.filter_change_criteria + FILTER_CRITERIA_SUFFIX] = new_value
        title_obj.title = "(running check " + curr_check + " - please wait)"
        cb = partial(self.run_curr_check, curr_check, check_dict)
        Clock.schedule_once(cb)

    def do_checks(self, check_name):
        cae.dprint('AcuSihotMonitorApp.do_checks():', check_name, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        title_obj = self.main_win.ids.action_previous
        curr_board = title_obj.title
        if check_name.startswith(REFRESH_BOARD_PREFIX):
            check_name = check_name[len(REFRESH_BOARD_PREFIX):]
        title_obj.title += " (running check " + check_name + " - please wait)"
        cb = partial(self.run_checks, check_name, curr_board)
        Clock.schedule_once(cb)
        if check_name == curr_board:
            cb = partial(self.display_board, check_name)
            Clock.schedule_once(cb)

    def run_curr_check(self, curr_check, check_dict, *_):
        results = run_check(curr_check, check_dict)
        self.update_check_result(curr_check, results, datetime.datetime.now().strftime('%d-%m-%y %H:%M:%S'))
        self.display_board(curr_check)

    def run_checks(self, check_name, curr_board, *args, run_at=None):
        cae.dprint('AcuSihotMonitorApp.run_checks():', check_name, curr_board, args, run_at,
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        # root_check = False
        if not run_at:
            run_at = datetime.datetime.now().strftime('%d-%m-%y %H:%M:%S')
            # root_check = True

        check_items = self.board_items(check_name)
        if check_items:
            # recursively run all tests/checks of this board and all the sub-boards
            ret = ''
            for check_item in check_items:
                ret += ' / ' + self.run_checks(check_item['name'], curr_board, run_at=run_at)
            results = (ret[3:],)
        else:
            # Clock.tick()
            results = run_check(check_name, self.check_list[self.check_index(check_name)])
            # Clock.tick()

        self.update_check_result(check_name, results, run_at)
        self.display_board(check_name)

        # if root_check:
        #    self.main_win.ids.action_previous.title = curr_board

        return str(results[0])

    def update_check_result(self, check_name, results, run_at):
        check_index = self.check_index(check_name)
        cae.dprint("AcuSihotMonitorApp.update_check_result(): dict={} results={}"
                   .format(self.check_list[check_index], results),
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        self.check_list[check_index]['check_result'] = results[0]
        if len(results) > 1:
            self.check_list[check_index]['column_attributes'] = self.column_attributes(results[1])
        self.check_list[check_index]['last_check'] = run_at

        # save updated CHECKS to config/INI file
        err_msg = self.ca.set_config('checks', self.check_list)
        if err_msg:
            uprint("AcuSihotMonitorApp.update_check_result() error={} checks_list={}".format(err_msg, self.check_list))

    @staticmethod
    def column_attributes(column_names):
        column_attributes = list()
        for cn in column_names:
            attributes = dict()
            l = cn.split(COLUMN_ATTRIBUTE_SEP)
            attributes['column_name'] = l[0]
            if len(l) > 1:
                attributes['size_hint_x'] = int(l[1][:2]) / 100
                if len(l[1]) > 2:
                    attributes['halign'] = 'left' if l[1][2] == 'L' else ('right' if l[1][2] == 'R' else 'justify')
                else:
                    attributes['halign'] = 'center'
            column_attributes.append(attributes)
        return column_attributes

    @staticmethod
    def label_attributes(column_attributes, text):
        kca = dict(column_attributes)
        kca['text'] = text
        del kca['column_name']
        return kca

    @staticmethod
    def result_text(data_dict):
        """ used for check button text within kv and self.display_board() for to show check result """
        if 'check_result' in data_dict:
            if isinstance(data_dict['check_result'], str):
                txt = data_dict['check_result']
            else:
                txt = str(len(data_dict['check_result']))
        else:
            txt = '(no check run)'
        for k in data_dict:
            if k.endswith(FILTER_CRITERIA_SUFFIX):
                dd = data_dict[k]
                if isinstance(dd, datetime.date):
                    txt = dd.strftime(DATE_DISPLAY_FORMAT) + FILTER_CRITERIA_SEP + txt
                elif dd:
                    txt = str(dd) + FILTER_CRITERIA_SEP + txt
        return txt


if __name__ == '__main__':
    AcuSihotMonitorApp().run()
