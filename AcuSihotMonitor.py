"""
    0.1     first beta
"""
import datetime
from functools import partial
from traceback import print_exc

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
# from kivy.uix.actionbar import ActionButton
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.actionbar import ActionButton
from kivy.uix.popup import Popup
from kivy.lang.builder import Factory
from kivy.properties import BooleanProperty, NumericProperty, StringProperty, DictProperty, ObjectProperty
from kivy.clock import Clock

from ae_console_app import ConsoleApp, uprint, DEBUG_LEVEL_VERBOSE
from ae_calendar import DateChangeScreen
from ae_db import OraDB, DEF_USER, DEF_DSN
from acu_sihot_config import Data
from sxmlif import AcuServer, PostMessage, ConfigDict, CatRooms, ResToSihot, ResSearch, SXML_DEF_ENCODING

__version__ = '0.1'

ROOT_BOARD_NAME = 'All'
BACK_BOARD_NAME = 'BACK'

LIST_ITEM_HEIGHT = 39
MAX_LIST_ITEMS = 369

DATE_DISPLAY_FORMAT = '%d/%m/%Y'

FILTER_CRITERIA_SUFFIX = '_criteria'
FILTER_CRITERIA_SEP = '::'


cae = ConsoleApp(__version__, "Monitor the Acumen and Sihot interfaces and servers")
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

""" TESTS """


def run_check(check_name, data_dict):
    try:
        if 'from_join' in data_dict:
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

        elif check_name == 'Reservation Discrepancies':
            results = sih_reservation_discrepancies(data_dict)
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
    beg_day = data_dict['first_arrival_criteria']   # datetime.datetime.today()
    end_day = beg_day + datetime.timedelta(days=int(data_dict['days_criteria']))   # days=1)  # 9)
    req = ResToSihot(cae)
    result = req.fetch_all_valid_from_acu("ARR_DATE < DATE'" + end_day.strftime('%Y-%m-%d') + "'"
                                          " and DEP_DATE > DATE'" + beg_day.strftime('%Y-%m-%d') + "'")
    if not result:  # no error message then process fetched rows
        result = []
        for crow in req.rows:
            if crow['SIHOT_GDSNO']:
                rs = ResSearch(cae)
                rd = rs.search(gdsno=crow['SIHOT_GDSNO'])
                row_err = ''
                if rd and isinstance(rd, list):
                    # compare reservation for errors/discrepancies
                    if len(rd) != 1:
                        row_err += '/Res. count!=1 ' + str(len(rd))
                    if rd[0]['GDSNO']['elemVal'] != crow['SIHOT_GDSNO']:
                        row_err += '/GDS no mismatch ' + rd[0]['GDSNO']['elemVal']
                    if rd[0]['ARR']['elemVal'] != crow['ARR_DATE'].strftime('%Y-%m-%d'):
                        row_err += '/Arrival date mismatch ' + rd[0]['ARR']['elemVal'] + \
                                   ' a=' + crow['ARR_DATE'].strftime('%Y-%m-%d')
                    if rd[0]['DEP']['elemVal'] != crow['DEP_DATE'].strftime('%Y-%m-%d'):
                        row_err += '/Depart. date mismatch ' + rd[0]['DEP']['elemVal'] + \
                                   ' a=' + crow['DEP_DATE'].strftime('%Y-%m-%d')
                    if (rd[0]['RN'].get('elemVal')
                        or crow['RUL_SIHOT_ROOM']) \
                            and rd[0]['RN'].get('elemVal') != crow['RUL_SIHOT_ROOM']:  # prevent None != '' false posit.
                        row_err += '/Room no mismatch ' + str(rd[0]['RN'].get('elemVal')) \
                                   + ' a=' + str(crow['RUL_SIHOT_ROOM'])
                elif rd:
                    row_err += '/Unexpected search result=' + str(rd)
                else:
                    row_err += '/Sihot search error ' + rs.response.error_text
                if row_err:
                    result.append((crow['SIHOT_GDSNO'], row_err[1:]))
            else:
                result.append(('RU' + str(crow['RUL_PRIMARY']), '(not check-able because RU deleted)'))
        result = (result, ('GDS_NO__18', 'Discrepancy__72L'))

    return result if result else ('No discrepancies found for date range {}..{}.'.format(beg_day, end_day),)


def sih_test_notification():
    return ''


def cfg_agency_match_codes():
    config_data = Data(cae.get_option('acuUser'), cae.get_option('acuPassword'), cae.get_option('acuDSN'))
    acu_db = connect_db()
    agencies = config_data.load_view(acu_db, 'T_RO', ['RO_CODE'], "RO_SIHOT_AGENCY_MC is not NULL")
    acu_db.close()
    ret = ""
    for agency in agencies:
        ret += ", " + agency[0] + "=" + config_data.get_ro_agency_matchcode(agency[0])
    return ret[2:]


def cfg_agency_obj_ids():
    config_data = Data(cae.get_option('acuUser'), cae.get_option('acuPassword'), cae.get_option('acuDSN'))
    acu_db = connect_db()
    agencies = config_data.load_view(acu_db, 'T_RO', ['RO_CODE'], "RO_SIHOT_AGENCY_OBJID is not NULL")
    acu_db.close()
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


class FilterActionButton(ActionButton):
    criteria_name = StringProperty()
    criteria_type = ObjectProperty()

    def on_press(self, **kwargs):
        value = self.text
        if FILTER_CRITERIA_SEP in value:
            value = value.split(FILTER_CRITERIA_SEP)[1]

        app = App.get_running_app()
        if self.criteria_type is datetime.date:
            app.change_date_filter(self.criteria_name, value)
        else:
            app.change_char_filter(self.criteria_name, value)


class AcuSihotMonitorApp(App):
    landscape = BooleanProperty()
    list_header_height = NumericProperty()

    def __init__(self, **kwargs):
        super(AcuSihotMonitorApp, self).__init__(**kwargs)
        self.ca = cae

        self.config_dict = ConfigDict(cae)
        self.post_message = PostMessage(cae)
        self.cat_rooms = CatRooms(cae)

        self.check_list = cae.get_config('checks')
        cae.dprint("AcuSihotMonitorApp.__init__() check_list", self.check_list, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        # self.boards = {k:v for ci in self.checks}
        self.board_history = []

        self.filter_widgets = []
        self.date_change_popup = None
        self.char_change_popup = None
        self.changing_criteria = ''

    def build(self):
        cae.dprint('AcuSihotMonitorApp.build()', minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        self.root = MainWindow()
        self.go_to_board(ROOT_BOARD_NAME)
        return self.root

    def screen_size_changed(self):
        self.landscape = self.root.width >= self.root.height

    def on_start(self):
        cae.dprint('AcuSihotMonitorApp.on_start()', minimum_debug_level=DEBUG_LEVEL_VERBOSE)

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
        self.display_board(board_name)

    def display_board(self, board_name):
        cae.dprint('AcuSihotMonitorApp.display_board()', board_name, 'Stack=', self.board_history,
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)

        mw = self.root

        bg = mw.ids.board_group
        bg.clear_widgets()
        bg.list_action_item = []  # missing in ActionGroup.clear_widgets() ?!?!?
        bg._list_overflow_items = []

        cg = mw.ids.check_group
        cg.clear_widgets()
        cg.list_action_item = []  # missing in ActionGroup.clear_widgets() ?!?!?
        cg._list_overflow_items = []

        lg = mw.ids.list_group
        lg.clear_widgets()
        lg.list_action_item = []  # missing in ActionGroup.clear_widgets() ?!?!?
        lg._list_overflow_items = []

        lig = mw.ids.list_grid
        lig.clear_widgets()

        if self.filter_widgets:
            for w in self.filter_widgets:
                mw.ids.action_view.remove_widget(w)
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

            elif isinstance(result, str):
                lii = BoxLayout(size_hint_y=None, height=69)
                cil = Label(text=result)
                lii.add_widget(cil)
                lig.add_widget(lii)

            # add filters to ActionView
            for k in board_dict:
                if k.endswith(FILTER_CRITERIA_SUFFIX):
                    filter_name = k[:-len(FILTER_CRITERIA_SUFFIX)]
                    filter_value = board_dict[k]
                    filter_type = type(filter_value)
                    if filter_type is datetime.date:
                        filter_value = filter_value.strftime(DATE_DISPLAY_FORMAT)
                    if self.landscape:
                        filter_value = filter_name + FILTER_CRITERIA_SEP + filter_value
                    fw = FilterActionButton(text=filter_value, criteria_name=filter_name, criteria_type=filter_type)
                    self.filter_widgets.append(fw)
                    mw.ids.action_view.add_widget(fw)

        if board_name != ROOT_BOARD_NAME:
            bg.add_widget(Factory.BoardMenu(text=BACK_BOARD_NAME))

        mw.ids.action_previous.title = board_name
        # action view has no show_group(): mw.ids.action_view.show_group()
        bg.show_group()
        cg.show_group()
        lg.show_group()

    def _filter_changed(self, new_value):
        # will be done by display_board() anyway: self.filter_widgets.text = new_date.strftime(DATE_DISPLAY_FORMAT)
        curr_check = self.root.ids.action_previous.title
        check_dict = self.check_list[self.check_index(curr_check)]
        check_dict[self.changing_criteria + FILTER_CRITERIA_SUFFIX] = new_value
        results = run_check(curr_check, check_dict)
        self.update_check_result(curr_check, results, datetime.datetime.now().strftime('%d-%m-%y %H:%M:%S'))
        self.display_board(curr_check)

    def change_date_filter(self, changing_criteria, curr_date, *_):
        cae.dprint('AcuSihotMonitorApp.change_date_filter():', curr_date, changing_criteria, _,
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        pu = Popup(title='Change Date',
                   content=DateChangeScreen(selected_date=datetime.datetime.strptime(curr_date, DATE_DISPLAY_FORMAT)),
                   size_hint=(.9, .9))
        pu.open()
        self.date_change_popup = pu
        self.changing_criteria = changing_criteria

    def date_changed(self, new_date, *_):
        cae.dprint('AcuSihotMonitorApp.date_changed():', new_date, _, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        if self.date_change_popup:
            self.date_change_popup.dismiss()
            self.date_change_popup = None
        self._filter_changed(new_date)

    def change_char_filter(self, changing_criteria, curr_char, *_):
        cae.dprint('AcuSihotMonitorApp.change_char_filter():', changing_criteria, curr_char, _,
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        ti = TextInput(text=curr_char)
        pu = Popup(title='Change Filter', content=ti, size_hint=(.6, .3), on_dismiss=self.char_changed)
        pu.open()
        self.char_change_popup = pu
        self.changing_criteria = changing_criteria

    def char_changed(self, *_):
        cae.dprint('AcuSihotMonitorApp.char_changed():', self.char_change_popup.content.text, _,
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        self._filter_changed(self.char_change_popup.content.text)

    def do_checks(self, check_name):
        cae.dprint('AcuSihotMonitorApp.do_checks():', check_name, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        title_obj = self.root.ids.action_previous
        curr_board = title_obj.title
        title_obj.title += " (running check " + check_name + " - please wait)"
        cb = partial(self.run_checks, check_name, curr_board)
        Clock.schedule_once(cb)

    def run_checks(self, check_name, curr_board, *args, run_at=None):
        cae.dprint('AcuSihotMonitorApp.run_checks():', check_name, curr_board, args, run_at,
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        root_check = False
        if not run_at:
            run_at = datetime.datetime.now().strftime('%d-%m-%y %H:%M:%S')
            root_check = True

        check_items = self.board_items(check_name)
        if check_items:
            # recursively run all tests/checks of this board and all the sub-boards
            ret = ''
            for check_item in check_items:
                ret += ' / ' + self.run_checks(check_item['name'], curr_board, run_at=run_at)
            results = (ret[3:],)
        else:
            Clock.tick()
            results = run_check(check_name, self.check_list[self.check_index(check_name)])
            Clock.tick()

        self.update_check_result(check_name, results, run_at)

        if root_check:
            self.root.ids.action_previous.title = curr_board

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
        self.ca.set_config('checks', self.check_list)

    @staticmethod
    def column_attributes(column_names):
        column_attributes = list()
        for cn in column_names:
            attributes = dict()
            l = cn.split('__')
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
                    txt = dd.strftime(DATE_DISPLAY_FORMAT) + '=' + txt
                else:
                    txt = dd + '=' + txt
        return txt


if __name__ == '__main__':
    AcuSihotMonitorApp().run()
