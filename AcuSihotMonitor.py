import datetime
from functools import partial
from traceback import print_exc

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
# from kivy.uix.actionbar import ActionButton
from kivy.lang.builder import Factory
from kivy.properties import DictProperty
from kivy.clock import Clock

from console_app import ConsoleApp, uprint, DEBUG_LEVEL_VERBOSE
from db import OraDB, DEF_USER, DEF_DSN
from acu_sihot_config import Data
from sxmlif import AcuServer, PostMessage, ConfigDict, CatRooms, ResToSihot, ResSearch, SXML_DEF_ENCODING

__version__ = '0.1'

ROOT_BOARD_NAME = 'All'
BACK_BOARD_NAME = 'BACK'

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
            acu_db = connect_db()
            result = acu_db.select(from_join=data_dict['from_join'], cols=data_dict['cols'],
                                   where_group_order=data_dict.get('where_group_order'))
            if not result:
                result = acu_db.fetch_all()
            acu_db.close()

        elif check_name == 'Time Sync':
            result = ass_test_time_sync()
        elif check_name == 'Link Alive':
            result = ass_test_link_alive()

        elif check_name == 'Reservation Discrepancies':
            result = sih_missing_reservations()
        elif check_name == 'Notification':
            result = sih_test_notification()

        elif check_name == 'Agency Match Codes':
            result = cfg_agency_match_codes()
        elif check_name == 'Agency Object Ids':
            result = cfg_agency_obj_ids()

        else:
            result = "Unknown Check Name '{}'".format(check_name)
    except Exception as ex:
        print_exc()
        result = "run_check() exception: " + str(ex)

    return result


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


def sih_missing_reservations():
    today = datetime.datetime.today()
    future_day = today + datetime.timedelta(days=1)  # 9)
    req = ResToSihot(cae)
    result = req.fetch_all_valid_from_acu("ARR_DATE < DATE'" + future_day.strftime('%Y-%m-%d') + "'"
                                          " and DEP_DATE > DATE'" + today.strftime('%Y-%m-%d') + "'")
    if not result:      # no error message then process fetched rows
        result = []
        for crow in req.rows:
            if crow['SIHOT_GDSNO']:
                rs = ResSearch(cae)
                rd = rs.search(gdsno=crow['SIHOT_GDSNO'])
                row_err = ''
                if isinstance(rd, list):
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
                    if (rd[0]['RN']['elemVal'] or crow['SIHOT_ROOM_NO']) \
                            and rd[0]['RN']['elemVal'] != crow['SIHOT_ROOM_NO']:  # prevent None != '' false positive
                        row_err += '/Room no mismatch ' + rd[0]['RN']['elemVal'] + ' a=' + str(crow['SIHOT_ROOM_NO'])
                else:
                    row_err += '/Sihot search error ' + str(rd)
                if row_err:
                    result.append((crow['SIHOT_GDSNO'], row_err[1:]))
            else:
                result.append(('RU' + str(crow['RUL_PRIMARY']), '(not check-able because RU deleted)'))

    return result if result else 'No discrepancies found for date range {}..{}.'.format(today, future_day)


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


class AcuSihotMonitorApp(App):
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

    def build(self):
        cae.dprint('AcuSihotMonitorApp.build()', minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        self.root = MainWindow()
        self.go_to_board(ROOT_BOARD_NAME)
        return self.root

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
            check_item = [ci for ci in self.check_list if ci['name'] == board_name][0]
            if 'background_color' in check_item:
                break
            board_name = check_item['parent_board']
        return check_item['background_color']

    def go_to_board(self, board_name):
        if board_name != BACK_BOARD_NAME:
            self.board_history.append(board_name)
        elif len(self.board_history) >= 2:
            self.board_history.pop()
            board_name = self.board_history[-1]

        cae.dprint('AcuSihotMonitorApp.go_to_board()', board_name, 'Stack=', self.board_history,
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

        ig = mw.ids.item_grid
        ig.clear_widgets()

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
                ig.add_widget(ci)

                cm = Factory.CheckMenu(text=check_item['name'])
                cg.add_widget(cm)

        else:
            result = self.check_list[self.check_index(board_name)].get('check_result')
            if isinstance(result, list):
                for rd in result:
                    li = Factory.BoxLayout(size_hint_y=None, height=39)
                    for cd in rd:
                        cl = Factory.Label(text=str(cd))
                        li.add_widget(cl)
                    ig.add_widget(li)
            elif isinstance(result, str):
                li = Factory.BoxLayout(size_hint_y=None, height=69)
                cl = Factory.Label(text=result)
                li.add_widget(cl)
                ig.add_widget(li)

        if board_name != ROOT_BOARD_NAME:
            bg.add_widget(Factory.BoardMenu(text=BACK_BOARD_NAME))

        mw.ids.action_previous.title = board_name
        bg.show_group()
        cg.show_group()
        lg.show_group()

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
        result = ''

        check_items = self.board_items(check_name)
        if check_items:
            # recursively run all tests/checks of this board and all the sub-boards
            for check_item in check_items:
                result += ' / ' + self.run_checks(check_item['name'], curr_board, run_at=run_at)
            result = result[3:]
        else:
            Clock.tick()
            result = run_check(check_name, self.check_list[self.check_index(check_name)])
            Clock.tick()

        self.update_check_result(check_name, result, run_at)

        if root_check:
            self.root.ids.action_previous.title = curr_board

        return str(result)

    def update_check_result(self, check_name, result, run_at):
        check_index = self.check_index(check_name)
        cae.dprint("AcuSihotMonitorApp.update_check_result(): dict={} result={}"
                   .format(self.check_list[check_index], result),
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        self.check_list[check_index]['check_result'] = result
        self.check_list[check_index]['last_check'] = run_at

        # save updated CHECKS to config/INI file
        self.ca.set_config('checks', self.check_list)


if __name__ == '__main__':
    AcuSihotMonitorApp().run()
