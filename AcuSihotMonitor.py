import datetime
from functools import partial

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.actionbar import ActionButton
from kivy.lang.builder import Factory
from kivy.properties import DictProperty
from kivy.clock import Clock

from console_app import ConsoleApp, uprint, DEBUG_LEVEL_VERBOSE
from db import OraDB, DEF_USER, DEF_DSN
from acu_sihot_config import Data
from sxmlif import PostMessage, ConfigDict, CatRooms, SXML_DEF_ENCODING

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


def run_check(check_name):
    try:
        if check_name == 'Number of categorized apartments':
            result = ora_get_num_apt()
        elif check_name == 'Number of unsynced guests':
            result = ora_get_num_cd_unsynced()
        elif check_name == 'Number of unsynced reservations':
            result = ora_get_num_res_unsynced()
        elif check_name == 'Agency Match Codes':
            result = cfg_agency_match_codes()
        elif check_name == 'Agency Object Ids':
            result = cfg_agency_obj_ids()
        else:
            result = "Invalid Check Run '{}'".format(check_name)
    except Exception as ex:
        result = "run_check() exception: " + str(ex)
    return result


def ora_get_num_apt():
    ora_db = connect_db()
    ora_db.select('T_AP', ['count(*)'], "exists (select LU_NUMBER from T_LU where LU_CLASS = 'SIHOT_HOTELS'"
                                        " and LU_ID = (select AT_RSREF from T_AT where AT_CODE = AP_ATREF)"
                                        " and LU_ACTIVE = 1)")
    ret = str(ora_db.fetch_all()[0][0])
    ora_db.select('T_AP', ['count(*)'], "AP_SIHOT_CAT is not NULL")
    ret += " (" + str(ora_db.fetch_all()[0][0]) + ")"
    ora_db.close()
    return ret


def ora_get_num_cd_unsynced():
    ora_db = connect_db()
    ora_db.select('V_ACU_CD_UNSYNCED', ['count(*)'])
    rows = ora_db.fetch_all()
    ora_db.close()
    return str(rows[0][0])


def ora_get_num_res_unsynced():
    ora_db = connect_db()
    ora_db.select('V_ACU_RES_UNSYNCED', ['count(*)'])
    rows = ora_db.fetch_all()
    ora_db.close()
    return str(rows[0][0])


def cfg_agency_match_codes():
    config_data = Data(cae.get_option('acuUser'), cae.get_option('acuPassword'), cae.get_option('acuDSN'))
    ora_db = connect_db()
    agencies = config_data.load_view(ora_db, 'T_RO', ['RO_CODE'], "RO_SIHOT_AGENCY_MC is not NULL")
    ora_db.close()
    ret = ""
    for agency in agencies:
        ret += ", " + agency[0] + "=" + config_data.get_ro_agency_matchcode(agency[0])
    return ret[2:]


def cfg_agency_obj_ids():
    config_data = Data(cae.get_option('acuUser'), cae.get_option('acuPassword'), cae.get_option('acuDSN'))
    ora_db = connect_db()
    agencies = config_data.load_view(ora_db, 'T_RO', ['RO_CODE'], "RO_SIHOT_AGENCY_OBJID is not NULL")
    ora_db.close()
    ret = ""
    for agency in agencies:
        ret += ", " + agency[0] + "=" + str(config_data.get_ro_agency_objid(agency[0]))
    return ret[2:]


""" HELPERS """


def connect_db():
    """ open Oracle database connection """
    ora_db = OraDB(cae.get_option('acuUser'), cae.get_option('acuPassword'),
                   cae.get_option('acuDSN'), debug_level=cae.get_option('debugLevel'))
    ora_db.connect()
    return ora_db


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
        cae.dprint("AcuSihotMonitorApp() check_list", self.check_list, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        # self.boards = {k:v for ci in self.checks}
        self.board_history = []

    def build(self):
        print('App.build()')
        self.root = MainWindow()
        self.go_to_board(ROOT_BOARD_NAME)
        return self.root

    def on_start(self):
        print('App.on_start()')

    def board_items(self, board_name):
        return [ci for ci in self.check_list
                if (board_name == ROOT_BOARD_NAME and 'parent_board' not in ci)
                or ('parent_board' in ci and ci['parent_board'] == board_name)
                ]

    def board_check_indexes(self, board_name):
        return [i for i in range(len(self.check_list))
                if (board_name == ROOT_BOARD_NAME and 'parent_board' not in self.check_list[i])
                or ('parent_board' in self.check_list[i] and self.check_list[i]['parent_board'] == board_name)
                ]

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

        print('Go To Board', board_name, 'Stack=', self.board_history)

        mw = self.root

        bg = mw.ids.board_group
        bg.clear_widgets()
        bg.list_action_item = []        # missing in ActionGroup.clear_widgets() ?!?!?
        bg._list_overflow_items = []

        cg = mw.ids.check_group
        cg.clear_widgets()
        cg.list_action_item = []        # missing in ActionGroup.clear_widgets() ?!?!?
        cg._list_overflow_items = []

        cis = mw.ids.check_items
        cis.clear_widgets()

        for check_index in self.board_check_indexes(board_name):
            check_item = self.check_list[check_index]
            if [cid for cid in self.check_list if 'parent_board' in cid and cid['parent_board'] == check_item['name']]:
                bm = Factory.BoardMenu(text=check_item['name'])
                bg.add_widget(bm)

            cm = Factory.CheckMenu(text=check_item['name'])
            cg.add_widget(cm)

            if 'background_color' not in check_item:
                check_item['background_color'] = self.get_background_color(board_name)
            ci = Factory.CheckItem(data_dict=check_item)
            self.check_list[check_index] = ci.data_dict  # put shallow copy of dict from DictProperty back to check_list
            cis.add_widget(ci)

        if board_name != ROOT_BOARD_NAME:
            bg.add_widget(Factory.BoardMenu(text=BACK_BOARD_NAME))
        cg.add_widget(Factory.CheckMenu(text=ROOT_BOARD_NAME))

        mw.ids.action_previous.title = board_name
        bg.show_group()
        cg.show_group()

    def do_checks(self, check_name):
        title_obj = self.root.ids.action_previous
        curr_board = title_obj.title
        title_obj.title += " (running check " + check_name + " - please wait)"
        cb = partial(self.run_checks, check_name, curr_board)
        Clock.schedule_once(cb)

    def run_checks(self, check_name, curr_board, *args, run_at=None):
        print('Run Check', check_name)
        if not run_at:
            run_at = datetime.datetime.now().strftime('%d-%m-%y %H:%M:%S')
        result = ''

        check_items = self.board_items(check_name)
        if check_items:
            # recursively run all tests/checks of this board and all the sub-boards
            for check_item in check_items:
                result += ' / ' + self.run_checks(check_item['name'], curr_board)
            result = result[3:]
            self.root.ids.action_previous = curr_board
        else:
            Clock.tick()
            result = run_check(check_name)
            Clock.tick()

        self.update_check_result(check_name, result, run_at)

        return result

    def run_check_cb(self, *args):
        self.curr_result = run_check(self.curr_check_name)
        self.root.ids.action_previous.title = self.curr_board_name
        self.update_check_result(self.curr_check_name, self.curr_result, self.curr_run_at)

    def update_check_result(self, check_name, result, run_at):
        check_index = [i for i in range(len(self.check_list)) if self.check_list[i]['name'] == check_name][0]
        cae.dprint("update_check_result() dict={}".format(self.check_list[check_index]),
                   minimum_debug_level=DEBUG_LEVEL_VERBOSE)
        self.check_list[check_index]['check_result'] = result
        self.check_list[check_index]['last_check'] = run_at

        # save updated CHECKS to config/INI file
        self.ca.set_config('checks', self.check_list)


if __name__ == '__main__':
    AcuSihotMonitorApp().run()
