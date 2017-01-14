import datetime

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.actionbar import ActionButton
from kivy.lang.builder import Factory

from console_app import ConsoleApp, uprint
from db import OraDB, DEF_USER, DEF_DSN
from acu_sihot_config import Data
from sxmlif import PostMessage, ConfigDict, CatRooms, SXML_DEF_ENCODING


__version__ = '0.3'


BOARDS = \
    {
        'Main': ({'name': 'Oracle',
                  'last_check': '28-12-2016 14:32', 'check_result': 'Ok', 'background_color': (.75, .6, 0, 1)},
                 {'name': 'Sihot',
                  'last_check': '28-12-2016 14:32', 'check_result': 'Ok', 'background_color': (.69, 0, 0, 1)},
                 {'name': 'AcuSvr',
                  'last_check': '28-12-2016 14:32', 'check_result': 'Ok', 'background_color': (.75, .36, 0, 1)},
                 {'name': 'System Config',
                  'last_check': '28-12-2016 14:32', 'check_result': 'Ok', 'background_color': (0, 0, .6, 1)},
                ),
        'Oracle': (),
        'Sihot': (),
        'AcuSvr': (),
    }


cae = ConsoleApp(__version__, "Periodically execute and supervise command")
cae.add_option('acuUser', "User name of Acumen/Oracle system", DEF_USER, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", DEF_DSN, 'd')

cae.add_option('serverIP', "IP address of the SIHOT interface server", 'localhost', 'i')
cae.add_option('serverPort', "IP port of the WEB interface of this server", 14777, 'w')
cae.add_option('serverKernelPort', "IP port of the KERNEL interface of this server", 14772, 'k')
cae.add_option('timeout', "Timeout value for TCP/IP connections", 39.6)
cae.add_option('xmlEncoding', "Charset used for the xml data", SXML_DEF_ENCODING, 'e')

uprint('Acumen Usr/DSN:', cae.get_option('acuUser'), cae.get_option('acuDSN'))
uprint('Server IP/Web-/Kernel-port:', cae.get_option('serverIP'), cae.get_option('serverPort'),
       cae.get_option('serverKernelPort'))
uprint('TCP Timeout/XML Encoding:', cae.get_option('timeout'), cae.get_option('xmlEncoding'))


class MainWindow(FloatLayout):
    pass


class AcuSihotMonitorApp(App):
    def __init__(self, **kwargs):
        super(AcuSihotMonitorApp, self).__init__(**kwargs)
        self.ca = cae

        self.ora_db = OraDB(cae.get_option('acuUser'), cae.get_option('acuPassword'),
                            cae.get_option('acuDSN'), debug_level=cae.get_option('debugLevel'))
        self.ora_db.connect()

        self.config_data = Data(cae.get_option('acuUser'), cae.get_option('acuPassword'), cae.get_option('acuDSN'))
        self.config_dict = ConfigDict(cae)
        self.post_message = PostMessage(cae)
        self.cat_rooms = CatRooms(cae)

    def build(self):
        self.root = MainWindow()
        self.go_to_board('Main')
        return self.root

    def go_to_board(self, board_name):
        print('Go To Board', board_name)
        mw = self.root

        bg = mw.ids.board_group
        bg.clear_widgets()
        cg = mw.ids.check_group
        cg.clear_widgets()
        cis = mw.ids.check_items
        cis.clear_widgets()
        checks = BOARDS[board_name]
        for check_item in checks:
            if check_item['name'] in BOARDS:
                bm = Factory.BoardMenu(text=check_item['name'])
                bg.add_widget(bm)
            cm = Factory.CheckMenu(text=check_item['name'])
            cg.add_widget(cm)
            ci = Factory.CheckItem()
            for k, v in check_item.items():
                setattr(ci, k, v)
            cis.add_widget(ci)
        if board_name != 'Main':
            bg.add_widget(Factory.BoardMenu(text=board_name))
        cg.add_widget(Factory.CheckMenu(text='All'))

    def run_check(self, check_name):
        print('Run Check', check_name)
        if check_name in ('Main', 'All'):
            pass    # run all tests/checks

        result = 'Ok'
        BOARDS[check_name]['check_result'] = result
        BOARDS[check_name]['last_check'] = datetime.datetime.now().strftime('%d-%m-%y %H:M%:%S')


if __name__ == '__main__':
    AcuSihotMonitorApp().run()
