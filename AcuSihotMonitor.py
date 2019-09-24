"""
    0.1     first beta.
    0.2     first release: added "please wait" messages using Clock.schedule_once().
    0.3     ported to Python 3.5 with the option to use the angle backend (via KIVY_GL_BACKEND=angle_sdl2 env var).
    0.4     small refactoring and bug fixes (e.g. show app version in window title, added ErrorItem to kv, ...).

    TODO:
    - fix problem with "F_KEY_VAL(replace(replace(RUL_CHANGES" in AcuSihotMonitor_Support.ini queries.
    - add more checks (e.g. Expected Occupancy with previous/next room no.).
    - implement filter selection list with check boxes.
    - fix problems with dynamic ActionItems in upstream kivy repo.
    - Check if current master branch of Pyinstaller is including all needed kivy dependencies (including angle) and if
      not then fix problems upstream (failing kivy hook and the including of the kv file with pyinstaller for the two
      kivy apps AcuSihotMonitor and SihotResImport).

"""
import sys
import datetime
from functools import partial
from traceback import print_exc

from sys_data_ids import SDF_SH_CLIENT_PORT, SDI_ACU
from ae.core import DATE_ISO, DEBUG_LEVEL_VERBOSE
from ae.console_app import ConsoleApp
from sxmlif import PostMessage, ConfigDict, CatRooms
from acif import AcumenRes, AcuServer
from shif import ResSearch
from ass_sys_data import add_ass_options, init_ass_data, AssSysData

__version__ = '0.4'

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

cae = ConsoleApp("Monitor the Acumen and Sihot interfaces and servers",
                 cfg_opt_eval_vars=dict(date_format=DATE_DISPLAY_FORMAT))

ass_options = add_ass_options(cae, add_kernel_port=True, break_on_error=True)

# logon to and prepare AssCache and config data env, optional also connect to Acumen, Salesforce, Sihot
ass_data = init_ass_data(cae, ass_options)
asd = ass_data['assSysData']  # public instance for config/data fetches, could be redefined by logon

""" KIVY IMPORTS - done here for (1) prevent PyCharm import inspection warning and (2) remove command line options """
if True:  # added for to hide PyCharm inspection warning "module level import not at top of file"
    sys.argv = [sys.argv[0]]  # remove command line options for to prevent errors in kivy args_parse
    from kivy.config import Config  # window size have to be specified before any other kivy imports

    Config.set('graphics', 'width', '1800')
    Config.set('graphics', 'height', '999')
    from kivy.app import App
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.textinput import TextInput
    from kivy.uix.actionbar import ActionButton, ActionGroup, ActionView
    from kivy.uix.popup import Popup
    # noinspection PyProtectedMember
    from kivy.lang.builder import Factory
    from kivy.properties import BooleanProperty, NumericProperty, StringProperty, DictProperty, ObjectProperty
    from kivy.clock import Clock
    from kivy.core.window import Window

    from ae_calendar.calendar import DateChangeScreen

""" TESTS """


def run_check(check_name, data_dict, app_inst):
    try:
        if 'from_join' in data_dict:  # direct query/fetch against/from Acumen
            results = db_fetch(data_dict)
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
        elif check_name == 'Room Category Discrepancies':
            results = cfg_room_cat_discrepancies(data_dict, app_inst)
        else:
            results = ("Unknown Check Name '{}'".format(check_name),)
    except Exception as ex:
        print_exc()
        results = ("run_check() exception: " + str(ex),)

    return results


def _ass_test_method(method):
    global cae
    old_val = cae.get_opt(SDF_SH_CLIENT_PORT)
    cae.set_opt(SDF_SH_CLIENT_PORT, 11000, save_to_config=False)
    ret = method()
    cae.set_opt(SDF_SH_CLIENT_PORT, old_val, save_to_config=False)
    return ret


def ass_test_time_sync():
    return _ass_test_method(AcuServer(cae).time_sync)


def ass_test_link_alive():
    return _ass_test_method(AcuServer(cae).link_alive)


def sih_reservation_discrepancies(data_dict):
    beg_day = data_dict['first_occupancy_criteria']  # datetime.datetime.today()
    end_day = beg_day + datetime.timedelta(days=int(data_dict['days_criteria']))
    req = AcumenRes(cae)
    results = req.fetch_all_valid_from_acu("ARR_DATE < DATE'" + end_day.strftime(DATE_ISO) + "'"
                                           " and DEP_DATE > DATE'" + beg_day.strftime(DATE_ISO) + "'"
                                           " order by ARR_DATE, CD_CODE")
    if results:
        # error message
        results = (results,)
    else:  # no error message then process fetched recs
        err_sep = '//'
        results = list()
        for rec in req.recs:
            if rec['ResGdsNo']:
                rs = ResSearch(cae)
                rd = rs.search_res(gds_no=rec['ResGdsNo'])
                row_err = ''
                if rd and isinstance(rd, list):
                    # compare reservation for errors/discrepancies
                    if len(rd) != 1:
                        row_err += err_sep + 'Res. count AC=1 SH=' + str(len(rd)) + \
                                   ('(' + ','.join([(rd[n]['_RES-HOTEL'].val() or '') + '='
                                                    + str(rd[n]['ARR'].val()) + '...'
                                                    + str(rd[n]['DEP'].val()) for n in range(len(rd))]) + ')'
                                    if cae.get_opt('debugLevel') >= DEBUG_LEVEL_VERBOSE else '')
                    row_err = _sih_check_all_res(rec, rd, row_err, err_sep)
                elif rd:
                    row_err += err_sep + 'Unexpected search result=' + str(rd)
                else:
                    row_err += err_sep + 'Sihot interface search error text=' + rs.response.error_text + \
                               ' msg=' + str(rs.response.msg)
                if row_err:
                    results.append((rec['ResArrival'].strftime('%d-%m-%Y'), rec['AcuId'], rec['ResRateSegment'],
                                    rec['ResGdsNo'], row_err[len(err_sep):]))
            else:
                results.append(('RU' + str(rec['RUL_PRIMARY']), '(not check-able because RU deleted)'))
        results = (results, ('Arrival__18', 'Guest Ref__18', 'RO__06', 'GDS_NO__18', 'Discrepancy__72L'))

    return results or ('No discrepancies found for date range {}..{}.'.format(beg_day, end_day),)


def _sih_check_all_res(rec, rd, row_err, err_sep):
    max_offset = datetime.timedelta(days=asd.room_change_max_days_diff)
    acu_sep = ' AC='
    sih_sep = ' SH='
    for n in range(len(rd)):
        if len(rd) > 1:
            sih_sep = ' SH' + str(n + 1) + '='
        if rd[n]['GDSNO'].val() != rec['ResGdsNo']:
            row_err += err_sep + 'GDS no mismatch' + \
                       acu_sep + str(rec['ResGdsNo']) + \
                       sih_sep + str(rd[n]['GDSNO'].val())
        if abs(datetime.datetime.strptime(rd[n]['ARR'].val(), DATE_ISO) - rec['ResArrival']) > max_offset:
            row_err += err_sep + 'Arrival date offset more than ' + str(max_offset.days) + ' days' + \
                       acu_sep + rec['ResArrival'].strftime(DATE_ISO) + \
                       sih_sep + str(rd[n]['ARR'].val())
        if abs(datetime.datetime.strptime(rd[n]['DEP'].val(), DATE_ISO) - rec['ResDeparture']) > max_offset:
            row_err += err_sep + 'Departure date offset more than ' + str(max_offset.days) + ' days' + \
                       acu_sep + rec['ResDeparture'].strftime(DATE_ISO) + \
                       sih_sep + str(rd[n]['DEP'].val())
        if rd[n]['RT'].val() != rec['ResStatus']:
            row_err += err_sep + 'Res. status mismatch' + \
                       acu_sep + str(rec['ResStatus']) + \
                       sih_sep + str(rd[n]['RT'].val())
        # MARKETCODE-NO is mostly empty in Sihot RES-SEARCH response!!!
        if rd[n]['MARKETCODE'].val() and rd[n]['MARKETCODE'].val() != rec['ResRateSegment']:
            row_err += err_sep + 'Market segment mismatch' + \
                       acu_sep + str(rec['ResRateSegment']) + \
                       sih_sep + str(rd[n]['MARKETCODE'].val())
        # RN can be empty/None - prevent None != '' false posit.
        if (rd[n]['RN'].val() or '') != rec['ResRoomNo']:
            row_err += err_sep + 'Room no mismatch' + \
                       acu_sep + str(rec['ResRoomNo']) + \
                       sih_sep + str(rd[n]['RN'].val())
        elif rd[n]['_RES-HOTEL'].val() and rd[n]['_RES-HOTEL'].val() != rec['ResHotelId']:
            row_err += err_sep + 'Hotel-ID mismatch' + \
                       acu_sep + rec['ResHotelId'] + \
                       sih_sep + str(rd[n]['_RES-HOTEL'].val())
        elif rd[n]['ID'].val() and str(rd[n]['ID'].val()) != rec['ResHotelId']:
            # actually the hotel ID is not provided within the Sihot interface response xml?!?!?
            row_err += err_sep + 'Hotel ID mismatch' + \
                       acu_sep + rec['ResHotelId'] + \
                       sih_sep + str(rd[n]['ID'].val())

    return row_err


def sih_reservation_search(data_dict):
    list_marker_prefix = '*'
    result_columns = ['RES-HOTEL__03', 'GDSNO__09',
                      'RES-NR__06',
                      'SUB-NR__03',
                      list_marker_prefix + 'MATCHCODE__15', list_marker_prefix + 'NAME__21',
                      'ARR__09', 'DEP__09', 'RN__06', 'OBJID__06']
    rs = ResSearch(cae)
    # available filters: hotel_id, from_date, to_date, matchcode, name, gds_no, flags, scope
    filters = {k[:-len(FILTER_CRITERIA_SUFFIX)]: v for k, v in data_dict.items() if k.endswith(FILTER_CRITERIA_SUFFIX)}
    rd = rs.search_res(**filters)
    results = list()
    if rd and isinstance(rd, list):
        for row in rd:
            col_values = list()
            for c in result_columns:
                is_list = c.startswith(list_marker_prefix)
                if is_list:
                    c = c[len(list_marker_prefix):]
                if COLUMN_ATTRIBUTE_SEP in c:
                    c = c.split(COLUMN_ATTRIBUTE_SEP)[0]
                if c not in row:
                    elem_val = '(undef.)'
                elif is_list and isinstance(row[c].val(), list):
                    elem_val = str(row[c].val())
                elif row[c].val() is not None:
                    elem_val = row[c].val()
                else:
                    elem_val = '(missing)'
                col_values.append(elem_val)
            results.append(col_values)
        column_names = list()
        for c in result_columns:
            if c.startswith(list_marker_prefix):
                c = c[len(list_marker_prefix):]
            column_names.append(c)
        results = (results, tuple(column_names))

    return results


def sih_test_notification():
    return 'NOT IMPLEMENTED'


def cfg_agency_match_codes():
    agencies = asd.ro_agencies
    ret = ""
    for agency in agencies:
        ret += ", " + agency[0] + "=" + asd.get_ro_agency_matchcode(agency[0])
    return ret[2:]


def cfg_agency_obj_ids():
    agencies = asd.ro_agencies
    ret = ""
    for agency in agencies:
        ret += ", " + agency[0] + "=" + str(asd.get_ro_agency_objid(agency[0]))
    return ret[2:]


def cfg_room_cat_discrepancies(data_dict, app_inst):
    result, column_names = db_fetch(data_dict, from_join_name='_from_join')
    if isinstance(result, str):
        return result, None

    column_names.append("Discrepancies__69")
    discrepancies = list()
    sihot_cat_apts = dict()
    for hotel_id in asd.ho_id_list(data_dict['resort_criteria']):
        hotel_cat_apts = app_inst.cat_rooms.get_cat_rooms(hotel_id=hotel_id)
        for cat, apts in hotel_cat_apts.items():
            prev_apts = sihot_cat_apts.get(cat, list())
            sihot_cat_apts[cat] = prev_apts + apts
    # UNCOMMENT THIS AND THE LINE DOWN FOR TO CREATE SQL UPDATE COMMANDS FOR TO CONFIG/SET AP_SIHOT_CAT: sql = ""
    for cols in result:
        dis = ""
        if cols[2] and cols[2] != cols[3]:
            dis += "\nDifferent Acumen apartment and lookup category"
        if cols[3] not in sihot_cat_apts:
            dis += "\nSihot is missing Acumen category " + cols[3]
        elif cols[1] not in sihot_cat_apts[cols[3]]:
            for cat, apts in sihot_cat_apts.items():
                if cols[1] in apts:
                    dis += "\nDifferent Sihot room category " + cat
                    # sql += "\r\n update T_AP set AP_SIHOT_CAT = '" + cat + "' where AP_CODE = '" + cols[1] + "';"
                    break
            else:
                dis += "\nApartment missing in Sihot"
        if dis:
            discrepancies.append(cols + (dis[1:],))

    return discrepancies, column_names


""" HELPERS """


def db_fetch(data_dict, from_join_name='from_join'):
    bind_vars = {_[:-len(FILTER_CRITERIA_SUFFIX)]: data_dict[_] for _ in data_dict
                 if _.endswith(FILTER_CRITERIA_SUFFIX)}
    acu_db = asd.connection(SDI_ACU)
    err_msg = acu_db.select(from_join=data_dict[from_join_name], cols=data_dict['cols'],
                            where_group_order=data_dict.get('where_group_order'), bind_vars=bind_vars)
    if err_msg:
        cae.dpo('AcuSihotMonitor.db_fetch() select error:', err_msg)
        results = (err_msg,)
    else:
        results = (acu_db.fetch_all(), acu_db.selected_column_names())
    acu_db.close()

    return results


""" UI """


class MainWindow(FloatLayout):
    pass


class CheckItem(BoxLayout):
    data_dict = DictProperty()


class FixedActionGroup(ActionGroup):
    def fixed_clear_widgets(self):  # cannot override ActionGroup.clear_widgets() because show_group() is using it
        super(FixedActionGroup, self).clear_widgets()
        self.list_action_item = list()  # missing in ActionGroup.clear_widgets() ?!?!?
        self._list_overflow_items = list()

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
    user_name = StringProperty(cae.get_opt('acuUser'))
    user_password = StringProperty(cae.get_opt('acuPassword'))

    def __init__(self, **kwargs):
        super(AcuSihotMonitorApp, self).__init__(**kwargs)

        self.title = "Acumen Sihot Monitor V " + __version__
        self.config_dict = ConfigDict(cae)
        self.post_message = PostMessage(cae)
        self.cat_rooms = CatRooms(cae)

        self.check_list = cae.get_var('checks', default_value=cae.get_var('checks_template'))
        cae.dpo("AcuSihotMonitorApp.__init__() check_list", self.check_list)
        # self.boards = {k:v for ci in self.checks}
        self.board_history = list()

        self.filter_widgets = list()
        self.filter_change_popup = None
        self.filter_change_criteria = ''

        self.app_started = False
        self.main_win = None
        self.logon_win = None

    def build(self):
        cae.dpo('AcuSihotMonitorApp.build()')
        self.root = FloatLayout()
        self.main_win = MainWindow()
        self.logon_win = Factory.LogonWindow()
        usr = cae.get_opt('acuUser')
        pwd = cae.get_opt('acuPassword')
        if usr and pwd and self.init_config_data(usr, pwd):
            self.root.add_widget(self.main_win)
            self.go_to_board(ROOT_BOARD_NAME)
        else:
            self.root.add_widget(self.logon_win)
        return self.root

    @staticmethod
    def init_config_data(user_name, user_pass):
        global asd
        asd = AssSysData(cae, acu_user=user_name, acu_password=user_pass)
        if asd.error_message:
            pu = Popup(title='Logon Error', content=Label(text=asd.error_message), size_hint=(.9, .3))
            pu.open()
            return False
        return True

    def logon(self):
        user_name = self.logon_win.ids.user_name.text
        user_pass = self.logon_win.ids.user_password.text
        if self.init_config_data(user_name, user_pass):
            cae.set_opt('acuUser', user_name)
            cae.set_opt('acuPassword', user_pass, save_to_config=False)
            self.root.clear_widgets()
            self.root.add_widget(self.main_win)
            self.go_to_board(ROOT_BOARD_NAME)

    def on_start(self):
        cae.dpo("App.on_start()")
        Window.bind(on_key_down=self.key_down_callback)
        self.app_started = True

    def key_down_callback(self, keyboard, key_code, scan_code, text, modifiers, *args, **kwargs):
        if True:  # change to True for debugging - leave dpo for hiding Pycharm inspection "Parameter not used"
            cae.dpo("App.kbd {!r} key {} pressed, scan code={!r}, text={!r}, modifiers={!r}, args={}, kwargs={}"
                    .format(keyboard, key_code, scan_code, text, modifiers, args, kwargs))
        if key_code == 27:  # escape key
            self.exit_app()
            return True
        elif key_code == 13 and not self.logon_win.ids.import_button.disabled:  # enter key
            self.logon()
            return True
        return False

    @staticmethod
    def exit_app():
        cae.shutdown()

    def screen_size_changed(self):
        self.landscape = self.root.width >= self.root.height

    def board_items(self, board_name):
        return [ci for ci in self.check_list
                if (board_name == ROOT_BOARD_NAME and 'parent_board' not in ci) or ci.get('parent_board') == board_name
                ]

    def board_item_indexes(self, board_name):
        return [i for i in range(len(self.check_list))
                if (board_name == ROOT_BOARD_NAME and 'parent_board' not in self.check_list[i])
                or self.check_list[i].get('parent_board') == board_name
                ]

    def check_index(self, check_name):
        return [i for i in range(len(self.check_list)) if self.check_list[i]['name'] == check_name][0]

    def is_parent_item(self, check_name):
        return [cid for cid in self.check_list if cid.get('parent_board') == check_name]

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
        cae.dpo('AcuSihotMonitorApp.go_to_board()', board_name, 'Stack=', self.board_history)
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
        cae.dpo('AcuSihotMonitorApp.display_board()', board_name, _, 'Stack=', self.board_history)
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
            self.filter_widgets = list()

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
                lii = BoxLayout(size_hint_y=None, height=690)
                # cil = Label(text=result)
                cil = Factory.ErrorItem(text=result)
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
                    filter_value = str(filter_value)  # convert to string if multi_select
                filter_value += FILTER_CRITERIA_SEP
                if self.landscape:
                    filter_value += filter_name
                if filter_name + FILTER_SELECTION_SUFFIX in board_dict:
                    filter_selection = board_dict[filter_name + FILTER_SELECTION_SUFFIX]
                    if isinstance(filter_selection, dict) and 'from_join' in filter_selection:
                        acu_db = asd.connection(SDI_ACU)
                        err_msg = acu_db.select(from_join=filter_selection['from_join'],
                                                cols=filter_selection['fields'],
                                                where_group_order=filter_selection.get('where_group_order'),
                                                bind_vars=filter_selection.get('bind_vars', dict()))
                        if err_msg:
                            cae.dpo('AcuSihotMonitor._add_filters_to_actionview() select error:', err_msg)
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
        cae.dpo('AcuSihotMonitorApp.change_filter():', old_value, criteria_name, criteria_type, _)
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
        cae.dpo('AcuSihotMonitorApp.date_changed():', new_date, _)
        if self.filter_change_popup:
            self.filter_change_popup.dismiss()
            self.filter_change_popup = None
        self.filter_changed(new_date)

    def char_changed(self, *_):
        cae.dpo('AcuSihotMonitorApp.char_changed():', self.filter_change_popup.content.text, _)
        self.filter_changed(self.filter_change_popup.content.text)

    def filter_selected(self, new_value, criteria_name, criteria_type, *_):
        cae.dpo('AcuSihotMonitorApp.filter_selected():', new_value, criteria_name, criteria_type, _)
        self.filter_change_criteria = criteria_name
        if criteria_type is datetime.date:
            new_value = new_value.strftime(DATE_DISPLAY_FORMAT)
        self.filter_changed(new_value)

    def filter_changed(self, new_value):
        cae.dpo('AcuSihotMonitorApp.filter_changed():', new_value)
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
        cae.dpo('AcuSihotMonitorApp.do_checks():', check_name)
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
        results = run_check(curr_check, check_dict, self)
        self.update_check_result(curr_check, results, datetime.datetime.now().strftime('%d-%m-%y %H:%M:%S'))
        self.display_board(curr_check)

    def run_checks(self, check_name, curr_board, *args, run_at=None):
        cae.dpo('AcuSihotMonitorApp.run_checks():', check_name, curr_board, args, run_at)
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
            results = run_check(check_name, self.check_list[self.check_index(check_name)], self)
            # Clock.tick()

        self.update_check_result(check_name, results, run_at)
        self.display_board(check_name)

        # if root_check:
        #    self.main_win.ids.action_previous.title = curr_board

        return str(results[0])

    def update_check_result(self, check_name, results, run_at):
        check_index = self.check_index(check_name)
        cae.dpo("AcuSihotMonitorApp.update_check_result(): dict={} results={}"
                .format(self.check_list[check_index], results))
        self.check_list[check_index]['check_result'] = results[0]
        if len(results) > 1:
            self.check_list[check_index]['column_attributes'] = self.column_attributes(results[1])
        self.check_list[check_index]['last_check'] = run_at

        # save updated CHECKS to config/INI file
        err_msg = cae.set_var('checks', self.check_list)
        if err_msg:
            cae.po("AcuSihotMonitorApp.update_check_result() error={} checks_list={}"
                   .format(err_msg, self.check_list))

    @staticmethod
    def column_attributes(column_names):
        column_attributes = list()
        for cn in column_names:
            attributes = dict()
            x = cn.split(COLUMN_ATTRIBUTE_SEP)
            attributes['column_name'] = x[0]
            if len(x) > 1:
                attributes['size_hint_x'] = int(x[1][:2]) / 100
                if len(x[1]) > 2:
                    attributes['halign'] = 'left' if x[1][2] == 'L' else ('right' if x[1][2] == 'R' else 'justify')
                else:
                    attributes['halign'] = 'center'
            column_attributes.append(attributes)
        return column_attributes

    @staticmethod
    def label_attributes(column_attributes, text):
        kca = dict(column_attributes)
        kca['text'] = text
        kca.pop('column_name')
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
                if isinstance(dd, datetime.datetime):  # also True if dd is datetime.date
                    txt = dd.strftime(DATE_DISPLAY_FORMAT) + FILTER_CRITERIA_SEP + txt
                elif dd:
                    txt = str(dd) + FILTER_CRITERIA_SEP + txt
        return txt


if __name__ == '__main__':
    AcuSihotMonitorApp().run()
