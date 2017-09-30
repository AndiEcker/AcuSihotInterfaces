"""
    0.1     first beta.
    0.2     also put correct sub-index onto external booking ref (GDSNO) for first and the other bookings if booking has
            several rooms for the same date range.
    0.3     changed sub-index into extra entries on the Sihot Rooming List.
    0.4     changed console and UPX pyinstaller flags from True to False.
    0.5     removed Booking.com imports and added RCI booking imports (using Acumen reservation inventory data).
    0.6     31-03-17: removed hyphen and sub-booking-id from GDSNO and dup-exec/-startup lock (lastRt).
    0.7     30-07-17: implementation of RCI booking imports (independent from Acumen reservation inventory data).
    0.8     15-07-17: refactoring moving contacts and res_inv_data to acu_sf_sh_sys_data.py.
    0.9     29-08-17: added salesforce credentials and JSON import (and commented out TC import).
"""
import json
import sys
import os
import shutil
import glob
import datetime
import csv
from traceback import format_exc

from ae_console_app import ConsoleApp, Progress, fix_encoding, uprint, DEBUG_LEVEL_VERBOSE, full_stack_trace
from ae_notification import Notification
from ae_db import DEF_USER, DEF_DSN
from acu_sf_sh_sys_data import AssSysData, EXT_REFS_SEP, RCI_MATCH_AND_BOOK_CODE_PREFIX
from sxmlif import ResToSihot, \
    SXML_DEF_ENCODING, ERR_MESSAGE_PREFIX_CONTINUE, \
    USE_KERNEL_FOR_CLIENTS_DEF, USE_KERNEL_FOR_RES_DEF, MAP_CLIENT_DEF, MAP_RES_DEF, \
    ACTION_DELETE, ACTION_INSERT, ACTION_UPDATE, ClientToSihot, ECM_DO_NOT_SEND_CLIENT

__version__ = '0.9'

cae = ConsoleApp(__version__, "Import reservations from external systems (Thomas Cook, RCI) into the SiHOT-PMS",
                 additional_cfg_files=['SihotMktSegExceptions.cfg'])
# cae.add_option('tciPath', "Import path and file mask for Thomas Cook R*.TXT files", 'C:/TC_Import/R*.txt', 'j')
# cae.add_option('bkcPath', "Import path and file mask for Booking.com CSV-tci_files", 'C:/BC_Import/?_*.csv', 'y')
cae.add_option('rciPath', "Import path and file mask for RCI CSV files", 'C:/RC_Import/*.csv', 'Y')
cae.add_option('jsonPath', "Import path and file mask for OTA JSON files", 'C:/JSON_Import/*.json', 'j')

cae.add_option('smtpServerUri', "SMTP error notification server URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP Sender/From address", '', 'f')
cae.add_option('smtpTo', "List/Expression of SMTP Receiver/To addresses", list(), 'r')
cae.add_option('warningsMailToAddr', "Warnings SMTP receiver/to addresses (if differs from smtpTo)", list(), 'v')

cae.add_option('acuUser', "User name of Acumen/Oracle system", DEF_USER, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", DEF_DSN, 'd')

cae.add_option('sfUser', "Salesforce account user name", '', 'y')
cae.add_option('sfPassword', "Salesforce account user password", '', 'a')
cae.add_option('sfToken', "Salesforce account token string", '', 'o')
cae.add_option('sfClientId', "Salesforce client/application name/id", cae.app_name(), 'C')
cae.add_option('sfIsSandbox', "Use Salesforce sandbox (instead of production)", True, 's')

cae.add_option('serverIP', "IP address of the SIHOT interface server", 'localhost', 'i')
cae.add_option('serverPort', "IP port of the WEB interface of this server", 14777, 'w')
cae.add_option('serverKernelPort', "IP port of the KERNEL interface of this server", 14772, 'k')

cae.add_option('timeout', "Timeout value for TCP/IP connections", 69.3)
cae.add_option('xmlEncoding', "Charset used for the xml data", SXML_DEF_ENCODING, 'e')

cae.add_option('useKernelForClient', "Used interface for clients (0=web, 1=kernel)", USE_KERNEL_FOR_CLIENTS_DEF, 'g')
cae.add_option('mapClient', "Guest/Client mapping of xml to db items", MAP_CLIENT_DEF, 'm')
cae.add_option('useKernelForRes', "Used interface for reservations (0=web, 1=kernel)", USE_KERNEL_FOR_RES_DEF, 'z')
cae.add_option('mapRes', "Reservation mapping of xml to db items", MAP_RES_DEF, 'n')

cae.add_option('breakOnError', "Abort importation if an error occurs (0=No, 1=Yes)", 0, 'b')

debug_level = cae.get_option('debugLevel')

uprint("Import path/file-mask for OTA-JSON/RCI:", cae.get_option('jsonPath'), cae.get_option('rciPath'))
notification = None
if cae.get_option('smtpServerUri') and cae.get_option('smtpFrom') and cae.get_option('smtpTo'):
    notification = Notification(smtp_server_uri=cae.get_option('smtpServerUri'),
                                mail_from=cae.get_option('smtpFrom'),
                                mail_to=cae.get_option('smtpTo'),
                                used_system=cae.get_option('acuDSN') + '/' + cae.get_option('serverIP'),
                                debug_level=debug_level)
    uprint('SMTP/From/To:', cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))
    if cae.get_option('warningsMailToAddr'):
        uprint("Warnings SMTP receiver address:", cae.get_option('warningsMailToAddr'))

uprint("Acumen DSN:", cae.get_option('acuDSN'))
uprint("Server IP/WEB-port/Kernel-port:", cae.get_option('serverIP'), cae.get_option('serverPort'),
       cae.get_option('serverKernelPort'))
uprint("TCP Timeout/XML Encoding:", cae.get_option('timeout'), cae.get_option('xmlEncoding'))
uprint("Use Kernel for clients:", "Yes" if cae.get_option('useKernelForClient') else "No (WEB)")
uprint("Use Kernel for reservations:", "Yes" if cae.get_option('useKernelForRes') else "No (WEB)")
uprint("Break on error:", "Yes" if cae.get_option('breakOnError') else "No")
if cae.get_config('warningFragments'):
    uprint('Warning Fragments:', cae.get_config('warningFragments'))

# max. length of label text shown in UI/screen log
MAX_SCREEN_LOG_LEN = cae.get_config('max_text_len', default_value=69999)

# file collection - lists of files to be imported
tci_files = list()
bkc_files = list()
rci_files = list()
jso_files = list()
imp_files = list()


def collect_files():
    global tci_files, bkc_files, rci_files, jso_files, imp_files
    # tci_files = glob.glob(cae.get_option('tciPath')) if cae.get_option('tciPath') else list()
    # tci_files.sort(key=lambda f: os.path.basename(f)[1], reverse=True)
    # tci_files.sort(key=lambda f: os.path.basename(f)[3:13])
    tci_files = list()
    # bkc_files = glob.glob(cae.get_option('bkcPath')) if cae.get_option('bkcPath') else list()
    # bkc_files.sort(key=lambda f: os.path.basename(f))
    bkc_files = list()
    rci_files = glob.glob(cae.get_option('rciPath')) if cae.get_option('rciPath') else list()
    jso_files = glob.glob(cae.get_option('jsonPath')) if cae.get_option('jsonPath') else list()
    jso_files.sort(key=lambda f: os.path.basename(f))
    imp_files = tci_files + bkc_files + rci_files + jso_files


'''# #########################################################
   # reservation import
   # #########################################################
'''


def run_import(acu_user, acu_password, got_cancelled=None, amend_screen_log=None):
    global tci_files, bkc_files, rci_files

    if not got_cancelled:
        def got_cancelled():
            return False

    #  prepare logging env
    lf = cae.get_option('logFile')
    log_file_prefix = os.path.splitext(os.path.basename(lf))[0]
    log_file_path = os.path.dirname(lf)

    NO_FILE_PREFIX_CHAR = '@'
    error_log = list()
    import_log = list()

    def log_error(msg, ctx, line=-1, importance=2):
        error_log.append(dict(message=msg, context=ctx, line=line + 1))
        import_log.append(dict(message=msg, context=ctx, line=line + 1))
        msg = ' ' * (4 - importance) + '*' * importance + '  ' + msg
        uprint(msg)
        if amend_screen_log:
            amend_screen_log(msg, True)

    def log_import(msg, ctx, line=-1, importance=2):
        seps = '\n' * (importance - 2)
        import_log.append(dict(message=seps + msg, context=ctx, line=line + 1))
        msg = seps + ' ' * (4 - importance) + '#' * importance + '  ' + msg
        uprint(msg)
        if amend_screen_log:
            amend_screen_log(msg)

    log_import("Acumen Usr: " + acu_user, NO_FILE_PREFIX_CHAR + 'RunImport', importance=4)

    # logon to and prepare Acumen, Salesforce, Sihot and config data env
    conf_data = AssSysData(cae, acu_user=acu_user, acu_password=acu_password,
                           err_logger=log_error, warn_logger=log_import, ctx_no_file=NO_FILE_PREFIX_CHAR)
    if conf_data.error_message:
        log_error(conf_data.error_message, NO_FILE_PREFIX_CHAR + 'UserLogOn', importance=4)
        return

    log_import("successful user login", NO_FILE_PREFIX_CHAR + 'SuccessfulUserLogin')

    sub_res_id = 0      # sub-reservation-id for TCI/BKC group reservations

    ''' **************************************************************************************
        Thomas Cook Bookings Import              #############################################
        **************************************************************************************
    '''

    TCI_GDSNO_PREFIX = 'TC'
    # Thomas Cook import file format column indexes
    TCI_BOOK_TYPE = 0
    TCI_RESORT = 1  # PABE=PBC, BEVE=BHC
    TCI_ARR_DATE = 3
    TCI_STAY_DAYS = 4
    TCI_ROOM_SIZE1 = 7
    TCI_BOOK_IDX = 10
    TCI_PAX_IDX = 11
    TCI_ROOM_SIZE2 = 12
    TCI_FLIGHT_NO = 14
    TCI_BOOK_REF = 15
    TCI_BOOK_PREFIX = 16  # also specifying client country (SD=Denmark, TF=Finland, VN=Norway, VS=Sweden/LS=cruiser)
    TCI_SURNAME = 17
    TCI_FORENAME = 18
    TCI_PAX_TYPE = 19  # M=male adult, F=female adult, I=infant
    TCI_MEAL_PLAN = 20
    TCI_BOOK_DATE = 25
    TCI_COMMENT = 28
    TCI_BOOK_EXT = 31
    TCI_LINK_REF = 32  # linked/extended reservation (can have different LengthOfStay) - add to reservation comment
    TCI_CLIENT_CAT = 33
    TCI_NEW_LINE = 34

    def tci_cat_board_comments(curr_cols):
        room_size = curr_cols[TCI_ROOM_SIZE2].strip()  # A12 / A12SEA = Studio, A22 / A22SUP = 1 bed, A34 = 2 bed
        # ignore value in col 13 for certain codes because in this case the column 8 is correct
        if not room_size or room_size in ('H11-R2', 'H12-R2', 'H12BR2'):
            room_size = curr_cols[TCI_ROOM_SIZE1].strip()

        if room_size[-3:] == 'HAB':
            half_board = True
            # remove board info from unit size - these bookings had mostly also SPECIAL OFERTA
            # .. in board info(TCI_MEAL_PLAN)
            room_size = room_size[:-3]
        else:
            half_board = False
        # if room_size[:3] not in ('A12', 'A22', 'A34')
        # or room_size[3:] not in ('', 'ETG', 'HIF', 'SEA', 'VIE', 'SUP') or len(room_size) < 3:
        #    err_msg = 'Warning: Unknown Apartment Size'

        comments = list()
        ap_feats = list()
        if room_size[3:] == 'ETG':  # A22ETG / A34ETG == 1 bed / 2 bed with Duplex
            comments.append('#Duplex')  # 752 == AFT_CODE of "Duplex" apt.feature - HARD - CODED?!?!?
            ap_feats.append(752)  # paid supplement
        elif room_size[3:] == 'HIF' or room_size[3:] == 'VIE':  # A12HIF/A22HIF/A34HIF==studio/1 bed/2 bed high floor
            comments.append('#High Floor')  # 757 == HIF/"High Floor" in PBC == VIE/"View" in BHC
            ap_feats.append(757)  # paid supplement
        elif room_size[3:] == 'SEA':  # A12SEA / A22SEA == studio / 1 bed with sea / ocean view
            comments.append('#Seafront')  # 781 == AFT_CODE of "Seafront" apt.feature - HARD - CODED?!?!?
            ap_feats.append(781)
        elif room_size[3:] == 'SUP':  # 'A22SUP' == 1 Bed superior / recently - refurbished
            # A22SUP is a Sterling Suite so Reservations don't need a comment in the requnit
            comments.append('#Sterling')  # 748 == AFT_CODE of "Refurbished" apt.feature - HARD - CODED?!?!?
            ap_feats.append(748)

        room_cat = conf_data.get_size_cat('BHC' if curr_cols[TCI_RESORT] == 'BEVE' else 'PBC',  # BEVE=BHC, PABE=PBC
                                          'STUDIO' if room_size[1] == '1' else str(chr(ord(room_size[1]) - 1)) + ' BED',
                                          ap_feats)

        return room_cat, half_board, comments

    def tci_line_to_res_row(curr_line, last_line, file_name, line_num, rows):
        """ TC import file has per line one pax """
        nonlocal sub_res_id

        curr_cols = curr_line.split(';')

        # no header for to check but each last_line should start with either CNL, BOK or RBO
        if len(curr_cols) <= TCI_NEW_LINE:
            return "tci_line_to_res_row(): incomplete line, missing {} columns" \
                .format(TCI_NEW_LINE - len(curr_cols) + 1)
        elif curr_cols[TCI_BOOK_TYPE] not in ('CNL', 'BOK', 'RBO'):
            return "tci_line_to_res_row(): invalid line prefix {}".format(curr_line[:3])
        elif curr_cols[TCI_RESORT] not in ('BEVE', 'PABE'):
            return "tci_line_to_res_row(): invalid resort {}".format(curr_cols[TCI_RESORT])
        elif curr_cols[TCI_NEW_LINE] != '\n':
            return "tci_line_to_res_row(): incomplete line (missing end of line)"

        room_cat, half_board, comments = tci_cat_board_comments(curr_cols)
        is_adult = curr_cols[TCI_PAX_TYPE] in ('M', 'F')
        comments.append(curr_cols[TCI_COMMENT])  # start with apartment feature comments then client comment
        meal_plan = curr_cols[TCI_MEAL_PLAN]

        row = dict()
        if last_line:  # check if current line is an extension of the booking from last line (only not in first line)
            last_cols = last_line.split(';')
            if int(last_cols[TCI_BOOK_IDX]) + 1 == int(curr_cols[TCI_BOOK_IDX]) \
                    and int(last_cols[TCI_PAX_IDX]) + 1 == int(curr_cols[TCI_PAX_IDX]):
                # additional pax
                row = rows[-1]
            elif last_cols[TCI_BOOK_EXT] == 'H' and curr_cols[TCI_BOOK_EXT] == 'E' \
                    and last_cols[TCI_BOOK_REF] == curr_cols[TCI_LINK_REF] \
                    and last_cols[TCI_LINK_REF] == curr_cols[TCI_BOOK_REF]:
                # additional pax (maybe with different LengthOfStay)
                row = rows[-1]
                comments.append(curr_cols[TCI_LINK_REF] + '-' + curr_cols[TCI_BOOK_EXT])
                if datetime.timedelta(int(curr_cols[TCI_STAY_DAYS])) != row['DEP_DATE'] - row['ARR_DATE']:
                    comments.append('(LengthOfStay differs!)')
            elif last_cols[TCI_BOOK_REF] == curr_cols[TCI_BOOK_REF]:
                # separate room - mostly with same TC booking reference - increment sub_res_id (0==1st room)
                row = rows[-1]
                txt = curr_cols[TCI_BOOK_REF] + '-' + str(sub_res_id)
                if txt not in row['SIHOT_NOTE']:
                    row['SIHOT_NOTE'] += '+' + txt
                    row['SIHOT_TEC_NOTE'] += '|CR|+' + txt
                sub_res_id += 1
                comments.append(curr_cols[TCI_BOOK_REF] + '-' + str(sub_res_id))
            else:
                sub_res_id = 0

        if row:  # add next pax - extending previous row
            for txt in comments:
                if txt not in row['SIHOT_NOTE']:
                    row['SIHOT_NOTE'] += ';' + txt
                    row['SIHOT_TEC_NOTE'] += '|CR|' + txt
            row['RU_ADULTS' if is_adult else 'RU_CHILDREN'] += 1
        else:
            rows.append(row)
            row['SIHOT_GDSNO'] = TCI_GDSNO_PREFIX + curr_cols[TCI_BOOK_PREFIX] + curr_cols[TCI_BOOK_REF]
            row['SH_RES_TYPE'] = 'S' if curr_cols[TCI_BOOK_TYPE] == 'CNL' else '1'
            row['RUL_SIHOT_HOTEL'] = 1 if curr_cols[TCI_RESORT] == 'BEVE' else 4  # 1=BHC, 4=PBC
            row['SH_OBJID'] = row['OC_SIHOT_OBJID'] = conf_data.get_ro_agency_objid('TK')
            row['SH_MC'] = row['OC_CODE'] = conf_data.get_ro_agency_matchcode('TK')
            row['RH_EXT_BOOK_REF'] = curr_cols[TCI_BOOK_PREFIX] + curr_cols[TCI_BOOK_REF]
            row['RH_EXT_BOOK_DATE'] = curr_cols[TCI_BOOK_DATE]
            row['SIHOT_ALLOTMENT_NO'] = 11 if curr_cols[TCI_RESORT] == 'BEVE' else 12

            row['RUL_SIHOT_CAT'] = row['SH_PRICE_CAT'] = room_cat
            if curr_cols[TCI_CLIENT_CAT]:
                comments.append('ClientCat=' + curr_cols[TCI_CLIENT_CAT])
            if meal_plan == 'SPECIAL OFERTA':
                comments.append(meal_plan)
            row['SIHOT_NOTE'] = ';'.join(comments)
            row['SIHOT_TEC_NOTE'] = '|CR|'.join(comments)
            if half_board or 'HALF' in meal_plan.upper():
                row['RUL_SIHOT_PACK'] = 'HB'
            elif meal_plan and meal_plan != 'SPECIAL OFERTA':
                row['RUL_SIHOT_PACK'] = 'BB'
            else:
                row['RUL_SIHOT_PACK'] = 'RO'

            row['SIHOT_MKT_SEG'] = row['RUL_SIHOT_RATE'] = conf_data.get_ro_sihot_mkt_seg('TK')
            row['RO_RES_GROUP'] = conf_data.get_ro_res_group('TK')  # =='Rental SP'
            row['RU_SOURCE'] = 'T'
            row['ARR_DATE'] = datetime.datetime.strptime(curr_cols[TCI_ARR_DATE], '%Y-%m-%d')
            row['DEP_DATE'] = row['ARR_DATE'] + datetime.timedelta(int(curr_cols[TCI_STAY_DAYS]))
            row['SH_EXT_REF'] = curr_cols[TCI_FLIGHT_NO]
            row['RU_ADULTS' if is_adult else 'RU_CHILDREN'] = 1
            row['RU_CHILDREN' if is_adult else 'RU_ADULTS'] = 0

            row['RUL_ACTION'] = ACTION_DELETE if curr_cols[TCI_BOOK_TYPE] == 'CNL' \
                else (ACTION_UPDATE if curr_cols[TCI_BOOK_TYPE] == 'RBO' else ACTION_INSERT)

        # add pax name, person sequence number and room sequence number (sub_res_id)
        name_col = 'SH_' + ('ADULT' if is_adult else 'CHILD') \
                   + str(row['RU_ADULTS' if is_adult else 'RU_CHILDREN']) + '_NAME'
        row[name_col] = curr_cols[TCI_SURNAME]
        row[name_col + '2'] = curr_cols[TCI_FORENAME]
        pers_seq = row['RU_ADULTS'] if is_adult else 10 + row['RU_CHILDREN']
        row['SH_PERS_SEQ' + str(pers_seq)] = pers_seq - 1
        row['SH_ROOM_SEQ' + str(pers_seq)] = sub_res_id
        row['SH_ROOMS'] = sub_res_id + 1

        row['RUL_CHANGES'] = curr_line  # needed for error notification
        row['=FILE_NAME'] = file_name
        row['=LINE_NUM'] = line_num

        return ''

    ''' **************************************************************************************
        Booking.com Import               #####################################################
        **************************************************************************************
    '''
    BKC_HEADER_LINE = 'Reservation ID,Channel,Booked At,Modified At,Cancelled At,Room,Check-In,Check-Out' \
                      ',Guests,Adults,Children,Infants\n'
    BKC_GDSNO_PREFIX = 'BDC-'

    BKC_BOOK_REF = 0
    BKC_CHANNEL = 1
    BKC_BOOK_DATE = 2
    BKC_MODIFY_DATE = 3
    BKC_CANCEL_DATE = 4
    BKC_ROOM_INFO = 5
    BKC_ARR_DATE = 6
    BKC_DEP_DATE = 7
    BKC_GUEST_NAMES = 8
    BKC_ADULTS = 9
    BKC_CHILDREN = 10
    # BKC_BABIES = 11
    BKC_LINE_NUM = 12  # for to store original line number (because file content get re-ordered)

    BKC_COL_COUNT = 13

    def bkc_normalize_line(line):
        if line[-1] == ';':
            line = line[:-1]
        if line[0] == '"':
            # reformatting lines starting/ending with " (if room size value contains comma)
            line = line[1:-1]
            line.replace('""', '"')  # .. and replace duplicate high-commas with a single one

        return line

    def bkc_check_filename(file_name):
        resort = os.path.basename(file_name).split('_')[0]
        if resort in ('1', '4'):
            return int(resort)
        return 0

    def bkc_check_header(curr_cols, line):
        if len(curr_cols) != BKC_COL_COUNT:
            return "bkc_check_header(): invalid column count, {} differ".format(BKC_COL_COUNT - len(curr_cols))
        elif line != BKC_HEADER_LINE:
            return "bkc_check_header(): invalid header or file format {}".format(line)
        return ''

    def bkc_cat_pax_board_comments(curr_cols, resort):
        com = curr_cols[BKC_ROOM_INFO].strip(' -')
        room_info = com.replace('-', '').replace(' ', '').upper()
        comments = [com]
        if room_info[:5] == 'THREE':
            room_size = '3 BED'
        elif room_info[:3] == 'TWO' or room_info[:6] == 'DOUBLE' or room_info.find('DOUBLEBEDROOM') >= 0:
            room_size = '2 BED'
        elif room_info[:3] == 'ONE':
            room_size = '1 BED'
        else:
            if room_info[:3] != 'STU':
                comments.append("bkc_room_cat_pax_board() warning: room size missing (using Studio)")
            room_size = 'STUDIO'
        ap_feats = list()
        if room_info.find('SUPERIOR') >= 0:  # 748==AFT_CODE of "Refurbished" apt. feature
            ap_feats.append(748)
            comments.insert(0, '#Sterling')
        room_cat = conf_data.get_size_cat('BHC' if resort == 1 else 'PBC', room_size, ap_feats)

        children = ''
        pos = room_info.find('ADULTS')
        if pos > 0 and room_info[pos - 1].isdecimal():
            adults = int(room_info[pos - 1])
            pos = room_info.find('CHILD')
            if pos > 0 and room_info[pos - 1].isdecimal():
                children = int(room_info[pos - 1])
        else:
            adults = curr_cols[BKC_ADULTS]
            children = curr_cols[BKC_CHILDREN]

        adults = int(adults) if adults else 1
        children = int(children) if children else 0

        breakfast = room_info.find('BREAKFASTINCL')
        dinner = room_info.find('DINNERINCL')
        if breakfast >= 0 and dinner >= 0:
            board = 'HB'
        elif breakfast >= 0:
            board = 'BB'
        else:
            board = 'RO'

        return room_cat, adults, children, board, comments

    def bkc_line_to_res_row(curr_cols, resort, file_name, line_num, rows):
        """ Booking.com can have various lines per booking - identified with external booking ref/BKC_BOOK_REF """
        nonlocal sub_res_id

        # no header for to check but each last_line should start with either CNL, BOK or RBO
        if len(curr_cols) != BKC_COL_COUNT:
            return "bkc_line_to_res_row(): invalid column count, {} differ".format(BKC_COL_COUNT - len(curr_cols))
        elif len(curr_cols[BKC_BOOK_DATE].split('-')[0]) != 4:
            return "bkc_line_to_res_row(): invalid booking date format '{}' instead of YYYY-MM-DD" \
                .format(curr_cols[BKC_BOOK_DATE])
        elif curr_cols[BKC_CHANNEL] != 'Booking.com':
            return "bkc_line_to_res_row(): invalid channel {} instead of Booking.com".format(curr_cols[BKC_CHANNEL])

        room_cat, adults, children, board, comments = bkc_cat_pax_board_comments(curr_cols, resort)
        curr_arr = datetime.datetime.strptime(curr_cols[BKC_ARR_DATE], '%Y-%m-%d')
        curr_dep = datetime.datetime.strptime(curr_cols[BKC_DEP_DATE], '%Y-%m-%d')

        ext_key = curr_cols[BKC_BOOK_REF]
        row = dict()
        if rows:  # check if current line is an extension of the booking from last line (only not in first line)
            if BKC_GDSNO_PREFIX + ext_key in rows[-1]['SIHOT_GDSNO']:  # 'in' instead of '==' for to detect group res
                # check if date range extension or additional room - assuming additional room
                last_arr = rows[-1]['ARR_DATE']
                last_dep = rows[-1]['DEP_DATE']
                if last_dep == curr_arr:
                    # merge two contiguous date ranges (by extending last row)
                    row = rows[-1]
                    row['DEP_DATE'] = curr_dep
                    comments.append("date range extended")
                elif last_arr == curr_arr and last_dep != curr_dep:
                    comments.append("GroupRes:length of stay differs")
                elif last_arr != curr_arr and last_dep == curr_dep:
                    comments.append("GroupRes:different arrivals")
                else:
                    comments.append("GroupRes")
                if not row:
                    # separate room - with same booking reference
                    sub_res_id += 1
                    txt = ext_key + '-' + str(sub_res_id)
                    rows[-1]['SIHOT_GDSNO'] = BKC_GDSNO_PREFIX + txt
                    if txt not in rows[-1]['SIHOT_NOTE']:
                        rows[-1]['SIHOT_NOTE'] += txt
                        rows[-1]['SIHOT_TEC_NOTE'] += '|CR|' + txt
                        rows[-1]['SIHOT_LINK_GROUP'] = txt
                    ext_key += '-' + str(sub_res_id + 1)
                    comments.append(ext_key)

            elif sub_res_id:  # reset sub-res-no if last line was group or a merged booking
                sub_res_id = 0

        if row:  # add extra comments to extended previous row - removing duplicates
            for txt in comments:
                if txt not in row['SIHOT_NOTE']:
                    row['SIHOT_NOTE'] += ';' + txt
                    row['SIHOT_TEC_NOTE'] += '|CR|' + txt
        else:
            rows.append(row)
            row['SIHOT_GDSNO'] = BKC_GDSNO_PREFIX + ext_key
            row['SH_RES_TYPE'] = 'S' if curr_cols[BKC_CANCEL_DATE] else '1'
            row['RUL_SIHOT_HOTEL'] = resort  # 1=BHC, 4=PBC
            row['SH_OBJID'] = row['OC_SIHOT_OBJID'] = conf_data.get_ro_agency_objid('BK')
            row['SH_MC'] = row['OC_CODE'] = conf_data.get_ro_agency_matchcode('BK')
            row['RH_EXT_BOOK_REF'] = curr_cols[BKC_BOOK_REF]
            row['RH_EXT_BOOK_DATE'] = curr_cols[BKC_BOOK_DATE]
            row['SIHOT_LINK_GROUP'] = (ext_key + ' ' if sub_res_id else '') + acu_user[:2].lower()
            # no allotment for Booking.com: row['SIHOT_ALLOTMENT_NO'] = 11 if resort == 1 else 12

            row['RUL_SIHOT_CAT'] = row['SH_PRICE_CAT'] = room_cat
            row['SIHOT_NOTE'] = ';'.join(comments)
            row['SIHOT_TEC_NOTE'] = '|CR|'.join(comments)
            row['RUL_SIHOT_PACK'] = board

            row['SIHOT_MKT_SEG'] = row['RUL_SIHOT_RATE'] = conf_data.get_ro_sihot_mkt_seg('BK')
            row['RO_RES_GROUP'] = conf_data.get_ro_res_group('BK')  # 'Rental SP'
            row['RU_SOURCE'] = 'T'
            row['ARR_DATE'] = curr_arr
            row['DEP_DATE'] = curr_dep
            row['RU_ADULTS'] = adults
            row['RU_CHILDREN'] = children

            row['RUL_ACTION'] = ACTION_DELETE if curr_cols[BKC_CANCEL_DATE] \
                else (ACTION_UPDATE if curr_cols[BKC_MODIFY_DATE] else ACTION_INSERT)

            # add pax name(s) and person sequence number
            for i, full_name in enumerate(curr_cols[BKC_GUEST_NAMES].split(',')):
                name_col = 'SH_ADULT' + str(i + 1) + '_NAME'
                fore_name, last_name = full_name.strip().split(' ', maxsplit=1)
                if last_name:
                    row[name_col] = last_name
                if fore_name:
                    row[name_col + '2'] = fore_name
                row['SH_PERS_SEQ' + str(i + 1)] = i

        row['RUL_CHANGES'] = ','.join(curr_cols)  # needed for error notification
        row['=FILE_NAME'] = file_name
        row['=LINE_NUM'] = line_num

        return ''

    ''' **************************************************************************************
        ####  RCI Bookings Import            #################################################
        biggest differences to TCI and Booking.com import:
         o  client and matchcode explicitly created as guest record in Sihot
         o  room assigned to reservation (not for RL bookings)
         o  update of clients data (Sihot objid in local db and EXT_REFS in Sihot db)
        **************************************************************************************
    '''

    def rc_complete_client_row_with_ext_refs(c_row, ext_refs):
        """ complete client row for to send to Sihot as external references (EXT_REFS/EXT_REF_ID1/EXT_REF_TYPE1...) """
        s_ext_refs = list()
        for i, ext_ref in enumerate(ext_refs):
            if '=' in ext_ref:
                er_type, er_ref = ext_ref.split('=')
            else:
                er_type = 'RCI'
                er_ref = ext_ref
            er_type += str(i + 1)
            c_row['EXT_REF_TYPE' + str(i + 1)] = er_type
            c_row['EXT_REF_ID' + str(i + 1)] = er_ref
            s_ext_refs.append(er_type + '=' + er_ref)
        # EXT_REFS xml element is only needed for elemHideIf, data is in EXT_REF_ID<n>/EXT_REF_TYPE<n>
        c_row['EXT_REFS'] = EXT_REFS_SEP.join(s_ext_refs)

    def rc_country_to_iso2(rci_country):
        """ convert RCI country names into Sihot ISO2 country codes """
        iso_code = cae.get_config(rci_country.lower(), section='RcCountryToSihot')
        if not iso_code:
            iso_code = rci_country[:2]      # use first two letters if country is not defined in cfg file
        return iso_code

    def rc_ref_normalize(rci_ref):
        # first remove invalid characters
        ret = rci_ref.replace('/', '').replace('_', '').replace(' ', '')

        # check and correct RCI weeks and points member IDs to the format 9-999999 if possible
        length = len(ret)
        no_hyphen = '-' not in ret
        if length == 6 and no_hyphen and ret[0] in '123456789':  # 5-prefix for EU, 1-prefix for USA
            ret = ret[0] + '-' + ret[1:]
        elif length >= 7 and no_hyphen:  # 7+ digits (before 2015 we only converted 8+ digits)
            if ret[-3:-1] == '00' and ret[-1] in '123456789':
                ret = ret[-1] + '-' + ret[0:-3]
            else:
                ret = ret[:-5] + '-' + ret[-5:]
        elif length < 3 or length > 10 or no_hyphen:
            ret = None  # invalid rci ref

        return ret

    '''# #########################################################
       # RCI inbounds/weeks and RCI points import file processing
       # #########################################################
    '''

    #  AW4 file columns (new format changed in May 2017 - see the 3 new columns in 2nd row of RCI_FILE_HEADER)
    RCI_FILE_HEADER = 'RESORT NAME\tRESORT ID\tRESERVATION NUMBER' \
                      '\tLINE_OF_BUS_SUB_GRP_NM\tLINE_OF_BUS_NM\tTIER' \
                      '\tSTART DATE\tSTATUS\tRSVN TYPE\tGUEST CERT' \
                      '\tRCI ID\tMBR1 LAST\tMBR1 FIRST\tMBR EMAIL\tMBR TYPE\tGST LAST\tGST FIRST\tGST ADDR1' \
                      '\tGST ADDR2\tGST CITY\tGST STATE\tGST ZIP\tGST CNTRY\tGST PHONE\tGST EMAIL\tBOOK DT' \
                      '\tCXL DT\tUNIT\tBED\tOWNER ID\tOWNER FIRST\tOWNER LAST\tINT EXCH\tETL_ACTV_FLG' \
                      '\tETL_ACTV_FLG\tETL_ACTV_FLG\tETL_ACTV_FLG\tETL_ACTV_FLG\n'
    # RCI_RESORT_NAME = 0               # ResortId + ResortName (not used)
    RCI_RESORT_ID = 1  # BHC=1442, BHH=2398, HMC=2429, PBC=0803 (see also RS_RCI_CODE)
    RCI_BOOK_REF = 2
    # RCI_LINE_OF_BUS_SUB_GRP_NM = 3    # e.g. 141 (newly added and not used)
    # RCI_LINE_OF_BUS_NM = 4            # e.g. Member (newly added and not used)
    # RCI_TIER = 5                      # e.g. STANDARD (newly added and not used)
    RCI_ARR_DATE = 6
    RCI_BOOK_STATUS = 7  # STATUS, e.g. Reserved/Cancelled
    RCI_IS_GUEST = 9  # GUEST CERT, e.g. Y/N
    RCI_CLIENT_ID = 10
    RCI_CLIENT_SURNAME = 11
    RCI_CLIENT_FORENAME = 12
    RCI_CLIENT_EMAIL = 13
    RCI_GUEST_SURNAME = 15
    RCI_GUEST_FORENAME = 16
    RCI_GUEST_ADDR1 = 17
    RCI_GUEST_ADDR2 = 18
    RCI_GUEST_CITY = 19
    RCI_GUEST_STATE = 20
    RCI_GUEST_ZIP = 21
    RCI_GUEST_COUNTRY = 22
    RCI_GUEST_PHONE = 23
    RCI_GUEST_EMAIL = 24
    RCI_BOOK_DATE = 25
    RCI_CANCEL_DATE = 26
    RCI_APT_NO = 27
    RCI_ROOM_SIZE = 28
    RCI_OWNER_ID = 29
    RCI_OWNER_FORENAME = 30
    RCI_OWNER_SURNAME = 31
    RCI_COL_COUNT = 38

    def rci_imp_line_check(curr_line, file_name, line_num):
        err_msg = ''
        curr_cols = curr_line.split('\t')
        if curr_line[-1] != '\n':
            err_msg = "rci_line_to_res_row(): incomplete line (missing end of line)"
        elif len(curr_cols) < RCI_COL_COUNT:
            err_msg = "rci_line_to_res_row(): incomplete line (missing {} columns)" \
                .format(RCI_COL_COUNT - len(curr_cols))
        elif len(curr_cols) > RCI_COL_COUNT:
            err_msg = "rci_line_to_res_row(): wrong line format, having {} extra columns" \
                .format(len(curr_cols) - RCI_COL_COUNT)
        elif curr_cols[RCI_BOOK_STATUS] not in ('Reserved', 'Cancelled'):
            curr_cols = None
            err_msg = "Skip/hide request and incomplete bookings (without any apartment value)"
        elif 'RCI POINTS' in curr_cols[RCI_CLIENT_SURNAME] + curr_cols[RCI_CLIENT_FORENAME] \
                + curr_cols[RCI_GUEST_SURNAME] + curr_cols[RCI_GUEST_FORENAME]:
            curr_cols = None
            err_msg = "Skip/ignore RCI Points bookings"
        else:
            for _ in range(RCI_COL_COUNT, RC_COL_COUNT):
                curr_cols.append('Unused')
            curr_cols[RC_FILE_NAME] = file_name
            curr_cols[RC_LINE_NUM] = line_num
            curr_cols[RC_POINTS] = False
            cid = rc_ref_normalize(curr_cols[RCI_CLIENT_ID])
            curr_cols[RC_OCC_CLIENTS_IDX] = conf_data.get_contact_index(cid, file_name, line_num)
            cid = rc_ref_normalize(curr_cols[RCI_OWNER_ID])
            # sometimes resort is the "owner", e.g. 2429-55555/2429-99928 for HMC - in Sihot we are not hiding resort
            # if cid in client_refs_add_exclude:
            #     curr_cols[RC_OWN_CLIENTS_IDX] = -1
            # else:
            curr_cols[RC_OWN_CLIENTS_IDX] = conf_data.get_contact_index(cid, file_name, line_num)

        return curr_cols, err_msg

    def rci_line_to_occ_client_row(curr_cols):
        row = dict()
        row['CD_CODE'] = conf_data.contact_acu_id(curr_cols[RC_OCC_CLIENTS_IDX])
        row['CD_SNAM1'] = curr_cols[RCI_CLIENT_SURNAME]
        row['CD_FNAM1'] = curr_cols[RCI_CLIENT_FORENAME]
        row['CD_ADD11'] = curr_cols[RCI_GUEST_ADDR1]
        row['CD_ADD12'] = curr_cols[RCI_GUEST_ADDR2]
        row['SIHOT_COUNTRY'] = rc_country_to_iso2(curr_cols[RCI_GUEST_COUNTRY])
        row['SIHOT_STATE'] = curr_cols[RCI_GUEST_STATE]
        row['CD_POSTAL'] = curr_cols[RCI_GUEST_ZIP]
        row['CD_CITY'] = curr_cols[RCI_GUEST_CITY]
        row['CD_EMAIL'] = curr_cols[RCI_GUEST_EMAIL]
        row['CD_HTEL1'] = curr_cols[RCI_GUEST_PHONE]
        ext_refs = conf_data.contact_ext_refs([curr_cols[RC_OCC_CLIENTS_IDX]])
        if ext_refs:
            row['CD_RCI_REF'] = ext_refs[0]  # first ref coming from Acu.CD_RCI_REF and put into Sihot MATCH-ADM element

        # constant values - needed for to be accepted by the Sihot Kernel interface
        row['CD_SIHOT_OBJID'] = None
        row['SIHOT_GUESTTYPE1'] = '1'

        return row, ''

    def rci_line_to_own_client_row(curr_cols):
        row = dict()
        row['CD_CODE'] = conf_data.contact_acu_id(curr_cols[RC_OWN_CLIENTS_IDX])
        row['CD_SNAM1'] = curr_cols[RCI_CLIENT_SURNAME]
        row['CD_FNAM1'] = curr_cols[RCI_CLIENT_FORENAME]
        row['CD_ADD11'] = curr_cols[RCI_GUEST_ADDR1]
        row['CD_ADD12'] = curr_cols[RCI_GUEST_ADDR2]
        row['SIHOT_COUNTRY'] = rc_country_to_iso2(curr_cols[RCI_GUEST_COUNTRY])
        row['SIHOT_STATE'] = curr_cols[RCI_GUEST_STATE]
        row['CD_POSTAL'] = curr_cols[RCI_GUEST_ZIP]
        row['CD_CITY'] = curr_cols[RCI_GUEST_CITY]
        row['CD_EMAIL'] = curr_cols[RCI_GUEST_EMAIL]
        row['CD_HTEL1'] = curr_cols[RCI_GUEST_PHONE]
        ext_refs = conf_data.contact_ext_refs(curr_cols[RC_OWN_CLIENTS_IDX])
        if ext_refs:
            row['CD_RCI_REF'] = ext_refs[0]  # first ref coming from Acu.CD_RCI_REF and put into Sihot MATCH-ADM element
        # constant values - needed for to be accepted by the Sihot Kernel interface
        row['CD_SIHOT_OBJID'] = None
        row['SIHOT_GUESTTYPE1'] = '1'

        return row, ''

    def rci_line_to_res_row(curr_cols):
        """ used for to import RCI inbounds for week owners (RI/RO), leads (RL) and CPA owners (RI/RO) """
        row = dict()
        comments = list()

        row['RUL_SIHOT_HOTEL'] = conf_data.rci_to_sihot_hotel_id(curr_cols[RCI_RESORT_ID])
        if not row['RUL_SIHOT_HOTEL'] or row['RUL_SIHOT_HOTEL'] <= 0:
            return None, "rci_line_to_res_row(): invalid resort id {}".format(curr_cols[RCI_RESORT_ID])

        if curr_cols[RCI_BOOK_STATUS] == 'Cancelled':
            comments.append('Cancelled=' + curr_cols[RCI_CANCEL_DATE])
            row['SH_RES_TYPE'] = 'S'
            row['RUL_ACTION'] = ACTION_DELETE
        else:
            row['SH_RES_TYPE'] = '1'
            row['RUL_ACTION'] = ACTION_INSERT
        row['SIHOT_GDSNO'] = RCI_MATCH_AND_BOOK_CODE_PREFIX + curr_cols[RCI_BOOK_REF]
        row['RH_EXT_BOOK_REF'] = curr_cols[RCI_BOOK_REF]
        row['RH_EXT_BOOK_DATE'] = datetime.datetime.strptime(curr_cols[RCI_BOOK_DATE][:10], '%Y-%m-%d')

        row['ARR_DATE'] = datetime.datetime.strptime(curr_cols[RCI_ARR_DATE][:10], '%Y-%m-%d')
        row['DEP_DATE'] = row['ARR_DATE'] + datetime.timedelta(7)

        rno = ('0' if row['RUL_SIHOT_HOTEL'] == 4 and len(curr_cols[RCI_APT_NO]) == 3 else '') + curr_cols[RCI_APT_NO]
        rsi = 'STUDIO' if curr_cols[RCI_ROOM_SIZE][0] == 'S' else curr_cols[RCI_ROOM_SIZE][0] + ' BED'
        row['RUL_SIHOT_CAT'] = row['SH_PRICE_CAT'] = conf_data.rci_to_sihot_room_cat(row['RUL_SIHOT_HOTEL'], rsi)
        comments.append(rsi + ' (' + rno + ')')
        row['RUL_SIHOT_ROOM'] = conf_data.allocated_room(rno, row['ARR_DATE'])

        cl_occ_idx = curr_cols[RC_OCC_CLIENTS_IDX]
        cl_own_idx = curr_cols[RC_OWN_CLIENTS_IDX] if curr_cols[RC_OWN_CLIENTS_IDX] > -1 else cl_occ_idx
        own_rci_ref = rc_ref_normalize(curr_cols[RCI_OWNER_ID])
        row['SH_OBJID'] = row['OC_SIHOT_OBJID'] = conf_data.contact_sh_id(cl_own_idx)
        row['SH_MC'] = row['OC_CODE'] = conf_data.contact_acu_id(cl_own_idx)

        is_guest = curr_cols[RCI_IS_GUEST] == 'Y'
        if is_guest:                                # guest bookings doesn't provide RCI client Id
            if curr_cols[RCI_CLIENT_SURNAME] or curr_cols[RCI_CLIENT_FORENAME]:
                own_name = curr_cols[RCI_CLIENT_SURNAME] + ', ' + curr_cols[RCI_CLIENT_FORENAME]
            else:
                own_name = '(unknown)'
            comments.append('GuestOf=' + own_rci_ref + '=' + row['OC_CODE'] + ':' + own_name)

            comments.append('ExcMail=' + curr_cols[RCI_CLIENT_EMAIL])
            row['CD_SIHOT_OBJID'] = None
            row['CD_CODE'] = ''
            row['SH_ADULT1_NAME'] = curr_cols[RCI_GUEST_SURNAME]
            row['SH_ADULT1_NAME2'] = curr_cols[RCI_GUEST_FORENAME]
        else:
            row['CD_SIHOT_OBJID'] = conf_data.contact_sh_id(cl_occ_idx)
            row['CD_CODE'] = conf_data.contact_acu_id(cl_occ_idx)
            # has to be populated after send to Sihot: row['CD_SIHOT_OBJID'] = client_row['CD_SIHOT_OBJID']
            row['SH_ADULT1_NAME'] = curr_cols[RCI_CLIENT_SURNAME]
            row['SH_ADULT1_NAME2'] = curr_cols[RCI_CLIENT_FORENAME]
        row['SH_PRES_SEQ1'] = 0
        row['SH_ROOM_SEQ1'] = 0
        row['RU_ADULTS'] = 1
        row['RU_CHILDREN'] = 0

        mkt_seg, mkt_grp = conf_data.mkt_seg_grp(curr_cols[RC_OCC_CLIENTS_IDX], is_guest,
                                                 curr_cols[RC_FILE_NAME], curr_cols[RC_LINE_NUM])
        row['SIHOT_MKT_SEG'] = row['RUL_SIHOT_RATE'] = mkt_seg
        row['RO_RES_GROUP'] = mkt_grp  # RCI External, RCI Internal, RCI External Guest, RCI Owner Guest
        row['RU_SOURCE'] = 'R'

        row['RUL_SIHOT_PACK'] = 'RO'

        comments.append("Owner/Club=" + own_rci_ref + ' '
                        + curr_cols[RCI_OWNER_SURNAME] + ', ' + curr_cols[RCI_OWNER_FORENAME])

        row['SIHOT_NOTE'] = ";".join(comments)
        row['SIHOT_TEC_NOTE'] = "|CR|".join(comments)

        row['=FILE_NAME'] = curr_cols[RC_FILE_NAME]
        row['=LINE_NUM'] = curr_cols[RC_LINE_NUM]

        return row, ''

    #  AP7 file columns (new format changed in May 2017 - see new TIER column in 2nd row of RCIP_FILE_HEADER)
    RCIP_FILE_HEADER = 'RESORT ID\tRESORT NAME\tRSVN LINK\tRESERVATION NUMBER\tSYSTEM' \
                       '\tTIER' \
                       '\tCHK IN DT\tCHK OUT DT\tNIGHTS\tRSVN STATUS\tRSVN TYPE\tGUEST CERT' \
                       '\tUNIT TYPE 1\tUNIT NBR 1\tUNIT TYPE 2\tUNIT NBR 2\tUNIT TYPE 3\tUNIT NBR 3' \
                       '\tMBR ID\tMBR1 LAST	MBR1 FIRST\tMBR TIER\tLOCKOFF\tLOCKOFF UNIT TYPE' \
                       '\tGUARANTEED_CD\tGUARANTEED_FLG\tMSTR UNIT TYPE\tMSTR UNIT NBR' \
                       '\tGST LAST\tGST FIRST\tGST ADDR1\tGST ADDR2\tGST CITY\tGST STATE\tGST ZIP\tGST CNTRY' \
                       '\tGST PHONE\tGST EMAIL\tINT EXCH\tBOOK DT\tCXL DT\tMASTER ARRIVAL DATE\n'
    RCIP_RESORT_ID = 0  # BHC=1442, BHH=2398, HMC=2429, PBC=0803 (see also RS_RCI_CODE)
    RCIP_BOOK_REF = 3
    RCIP_ARR_DATE = 6
    RCIP_DEP_DATE = 7
    RCIP_BOOK_STATUS = 9  # e.g. R=Reserved/C=Cancelled
    RCIP_IS_GUEST = 11
    RCIP_ROOM_SIZE = 12
    RCIP_APT_NO = 13
    RCIP_CLIENT_ID = 18
    RCIP_CLIENT_SURNAME = 19
    RCIP_CLIENT_FORENAME = 20
    RCIP_GUEST_SURNAME = 28
    RCIP_GUEST_FORENAME = 29
    RCIP_GUEST_ADDR1 = 30
    RCIP_GUEST_ADDR2 = 31
    RCIP_GUEST_CITY = 32
    RCIP_GUEST_STATE = 33
    RCIP_GUEST_ZIP = 34
    RCIP_GUEST_COUNTRY = 35
    RCIP_GUEST_PHONE = 36
    RCIP_GUEST_EMAIL = 37
    RCIP_BOOK_DATE = 39
    RCIP_CANCEL_DATE = 40
    RCIP_COL_COUNT = 42

    # extra columns for to store import filename and line (because we re-order for to check dup-clients/cont-res.)
    RC_FILE_NAME = max(RCI_COL_COUNT, RCIP_COL_COUNT)
    RC_LINE_NUM = RC_FILE_NAME + 1
    RC_POINTS = RC_FILE_NAME + 2
    RC_OCC_CLIENTS_IDX = RC_FILE_NAME + 3
    RC_OWN_CLIENTS_IDX = RC_FILE_NAME + 4   # not used for points import (only one RCI ID given in import file)
    RC_COL_COUNT = RC_FILE_NAME + 5

    def rcip_imp_line_check(curr_line, file_name, line_num):
        curr_cols = curr_line.split('\t')
        if curr_line[-1] != '\n':
            err_msg = "rcip_line_to_res_row(): incomplete line (missing end of line)"
        elif len(curr_cols) < RCIP_COL_COUNT:
            err_msg = "rcip_line_to_res_row(): incomplete line, missing {} columns" \
                .format(RCIP_COL_COUNT - len(curr_cols))
        elif len(curr_cols) > RCIP_COL_COUNT:
            err_msg = "rcip_line_to_res_row(): wrong line format, having {} extra columns" \
                .format(len(curr_cols) - RCIP_COL_COUNT)
        else:
            err_msg = ''
            for _ in range(RCIP_COL_COUNT, RC_COL_COUNT):
                curr_cols.append('Unused')
            curr_cols[RC_FILE_NAME] = file_name
            curr_cols[RC_LINE_NUM] = line_num
            curr_cols[RC_POINTS] = True
            cid = rc_ref_normalize(curr_cols[RCIP_CLIENT_ID])
            curr_cols[RC_OCC_CLIENTS_IDX] = conf_data.get_contact_index(cid, file_name, line_num)
            curr_cols[RC_OWN_CLIENTS_IDX] = -1  # does not exists for points but needed for generic client send check
        return curr_cols, err_msg

    def rcip_line_to_occ_client_row(curr_cols):
        row = dict()
        rci_ref = rc_ref_normalize(curr_cols[RCIP_CLIENT_ID])
        row['CD_RCI_REF'] = rci_ref  # Sihot MATCH-ADM element
        if curr_cols[RCIP_IS_GUEST] == 'Y':
            row['CD_CODE'] = ''     # dict key needed/used in elemHideIf expressions
            row['CD_SNAM1'] = curr_cols[RCIP_GUEST_SURNAME]
            row['CD_FNAM1'] = curr_cols[RCIP_GUEST_FORENAME]
        else:
            row['CD_CODE'] = RCI_MATCH_AND_BOOK_CODE_PREFIX + rci_ref
            row['CD_SNAM1'] = curr_cols[RCIP_CLIENT_SURNAME]
            row['CD_FNAM1'] = curr_cols[RCIP_CLIENT_FORENAME]
        row['CD_ADD11'] = curr_cols[RCIP_GUEST_ADDR1]
        row['CD_ADD12'] = curr_cols[RCIP_GUEST_ADDR2]
        row['SIHOT_COUNTRY'] = rc_country_to_iso2(curr_cols[RCIP_GUEST_COUNTRY])
        row['SIHOT_STATE'] = curr_cols[RCIP_GUEST_STATE]
        row['CD_POSTAL'] = curr_cols[RCIP_GUEST_ZIP]
        row['CD_CITY'] = curr_cols[RCIP_GUEST_CITY]
        row['CD_EMAIL'] = curr_cols[RCIP_GUEST_EMAIL]
        row['CD_HTEL1'] = curr_cols[RCIP_GUEST_PHONE]
        # constant values - needed for to be accepted by the Sihot Kernel interface
        row['CD_SIHOT_OBJID'] = None
        row['SIHOT_GUESTTYPE1'] = '1'

        return row, ''

    def rcip_line_to_own_client_row(_):
        return dict(), "This method gets never executed because RCI(AP7) doesn't provide owner data for points bookings"

    def rcip_line_to_res_row(curr_cols):
        row = dict()
        comments = list()

        row['RUL_SIHOT_HOTEL'] = conf_data.rci_to_sihot_hotel_id(curr_cols[RCIP_RESORT_ID])
        if not row['RUL_SIHOT_HOTEL'] or row['RUL_SIHOT_HOTEL'] <= 0:
            return None, "rci_line_to_res_row(): invalid resort id {}".format(curr_cols[RCIP_RESORT_ID])

        if curr_cols[RCIP_BOOK_STATUS] == 'C':
            comments.append('Cancelled=' + curr_cols[RCIP_CANCEL_DATE])
        row['SH_RES_TYPE'] = 'S' if curr_cols[RCIP_BOOK_STATUS] == 'C' else '1'
        row['RUL_ACTION'] = ACTION_DELETE if curr_cols[RCIP_BOOK_STATUS] == 'C' else ACTION_INSERT

        row['SIHOT_GDSNO'] = RCI_MATCH_AND_BOOK_CODE_PREFIX + curr_cols[RCIP_BOOK_REF]
        row['RH_EXT_BOOK_REF'] = curr_cols[RCIP_BOOK_REF]
        row['RH_EXT_BOOK_DATE'] = datetime.datetime.strptime(curr_cols[RCIP_BOOK_DATE][:10], '%Y-%m-%d')

        row['ARR_DATE'] = datetime.datetime.strptime(curr_cols[RCIP_ARR_DATE][:10], '%Y-%m-%d')
        row['DEP_DATE'] = datetime.datetime.strptime(curr_cols[RCIP_DEP_DATE][:10], '%Y-%m-%d')

        rno = ('0' if row['RUL_SIHOT_HOTEL'] == 4 and len(curr_cols[RCIP_APT_NO]) == 3 else '') + curr_cols[RCIP_APT_NO]
        rsi = 'STUDIO' if curr_cols[RCIP_ROOM_SIZE][0] == 'S' else curr_cols[RCIP_ROOM_SIZE][0] + ' BED'
        row['RUL_SIHOT_CAT'] = row['SH_PRICE_CAT'] = conf_data.rci_to_sihot_room_cat(row['RUL_SIHOT_HOTEL'], rsi)
        comments.append(rsi + ' (' + rno + ')')
        row['RUL_SIHOT_ROOM'] = conf_data.allocated_room(rno, row['ARR_DATE'])

        cl_occ_idx = curr_cols[RC_OCC_CLIENTS_IDX]
        row['SH_OBJID'] = row['OC_SIHOT_OBJID'] = row['CD_SIHOT_OBJID'] = conf_data.contact_sh_id(cl_occ_idx)
        row['SH_MC'] = row['OC_CODE'] = row['CD_CODE'] = conf_data.contact_acu_id(cl_occ_idx)

        is_guest = curr_cols[RCIP_IS_GUEST] == 'Y'
        if is_guest:
            if curr_cols[RCIP_CLIENT_SURNAME] or curr_cols[RCIP_CLIENT_FORENAME]:
                own_name = curr_cols[RCIP_CLIENT_SURNAME] + ", " + curr_cols[RCIP_CLIENT_FORENAME]
            else:
                own_name = '(unknown)'
            comments.append('GuestOf=' + own_name)
            row['SH_ADULT1_NAME'] = curr_cols[RCIP_GUEST_SURNAME]
            row['SH_ADULT1_NAME2'] = curr_cols[RCIP_GUEST_FORENAME]
        else:
            row['SH_ADULT1_NAME'] = curr_cols[RCIP_CLIENT_SURNAME]
            row['SH_ADULT1_NAME2'] = curr_cols[RCIP_CLIENT_FORENAME]
        row['RU_ADULTS'] = 1
        row['RU_CHILDREN'] = 0

        mkt_seg, mkt_grp = conf_data.mkt_seg_grp(curr_cols[RC_OCC_CLIENTS_IDX], is_guest,
                                                 curr_cols[RC_FILE_NAME], curr_cols[RC_LINE_NUM])
        row['SIHOT_MKT_SEG'] = row['RUL_SIHOT_RATE'] = mkt_seg
        row['RO_RES_GROUP'] = mkt_grp  # RCI External, RCI Internal, RCI External Guest, RCI Owner Guest
        row['RU_SOURCE'] = 'R'

        row['RUL_SIHOT_PACK'] = 'RO'

        row['SIHOT_NOTE'] = ';'.join(comments)
        row['SIHOT_TEC_NOTE'] = '|CR|'.join(comments)

        row['=FILE_NAME'] = curr_cols[RC_FILE_NAME]
        row['=LINE_NUM'] = curr_cols[RC_LINE_NUM]

        return row, ''

    '''# #########################################################
       # OTA/JSON import file processing
       # #########################################################
    '''

    def json_imp_to_res_row(row, file_name, res_index):
        row['ARR_DATE'] = datetime.datetime.strptime(row['ARR_DATE'], '%Y-%m-%d')
        row['DEP_DATE'] = datetime.datetime.strptime(row['DEP_DATE'], '%Y-%m-%d')
        row['RH_EXT_BOOK_DATE'] = datetime.datetime.strptime(row['RH_EXT_BOOK_DATE'], '%Y-%m-%d')

        row['=FILE_NAME'] = file_name
        row['=LINE_NUM'] = res_index

        return row, ''

    #
    # #########################################################
    # LOAD import files
    # #########################################################
    #
    collect_files()

    res_rows = list()
    error_msg = ''

    if False and cae.get_option('tciPath') and tci_files and not got_cancelled():
        log_import("Starting Thomas Cook import", NO_FILE_PREFIX_CHAR + 'TciImportStart', importance=4)
        ''' sort TCI files 1.ASCENDING by actualization date and 2.DESCENDING by file type (R5 first, then R3, then R1)
            .. for to process cancellation/re-bookings in the correct order.
            .. (date and type taken from file name R?_yyyy-mm-dd hh.mm.ss.txt - ?=1-booking 3-cancellation 5-re-booking)
            .. hour/minute/... info cannot be used because it happened (see 17-Jan-14 6:40=R1 and 6:42=R5)
            .. that the R3/5 TCI files had a higher minute value than the associated R1 file with correction booking.
        '''
        if debug_level >= DEBUG_LEVEL_VERBOSE:
            log_import("TCI files: " + str(tci_files), NO_FILE_PREFIX_CHAR + 'TciFileCollect', importance=1)
        for fn in tci_files:
            if got_cancelled():
                log_error("User cancelled processing of TCI import file", fn, importance=4)
                break
            log_import("Processing import file " + fn, fn, importance=4)
            with open(fn, 'r') as fp:
                lines = fp.readlines()

            last_ln = ''
            for idx, ln in enumerate(lines):
                if got_cancelled():
                    log_error("User cancelled processing of TCI import lines", fn, idx, importance=4)
                    break
                if debug_level >= DEBUG_LEVEL_VERBOSE:
                    log_import('Import line loaded: ' + ln, fn, idx)
                try:
                    error_msg = tci_line_to_res_row(ln, last_ln, fn, idx, res_rows)
                except Exception as ex:
                    error_msg = "TCI Line parse exception: {}".format(ex)
                log_import("Parsed import line: " + str(res_rows[-1]), fn, idx)
                if error_msg:
                    log_error(error_msg, fn, idx)
                    if cae.get_option('breakOnError'):
                        break
                last_ln = ln
            if error_log and cae.get_option('breakOnError'):
                break

    if False and cae.get_option('bkcPath') and bkc_files and (not error_log or not cae.get_option('breakOnError')) \
            and not got_cancelled():
        log_import("Starting Booking.com import", NO_FILE_PREFIX_CHAR + 'BkcImportStart', importance=4)
        if debug_level >= DEBUG_LEVEL_VERBOSE:
            log_import("BKC files: " + str(bkc_files), NO_FILE_PREFIX_CHAR + 'BkcFileCollect', importance=1)
        for fn in bkc_files:
            if got_cancelled():
                log_error("User cancelled processing of BKC import file", fn, importance=4)
                break
            log_import("Processing import file " + fn, fn, importance=4)
            hotel_id = bkc_check_filename(fn)
            if not hotel_id:
                log_error("Hotel ID prefix followed by underscore character is missing - skipping.", fn, importance=4)
                continue

            with open(fn, 'r', encoding='utf-8-sig') as fp:  # encoding is removing the utf8 BOM
                lines = fp.readlines()
            # check/remove header and parse all other lines normalized into column list
            header = ''
            imp_rows = list()
            for idx, ln in enumerate(lines):
                if got_cancelled():
                    log_error("User cancelled processing of BKC import lines", fn, idx, importance=4)
                    break
                if debug_level >= DEBUG_LEVEL_VERBOSE:
                    log_import("Import line loaded: " + ln, fn, idx)
                try:
                    ln = bkc_normalize_line(ln)
                    cs = [c for c in csv.reader([ln])][0]
                    cs.append(str(idx))  # store original line number in BKC_LINE_NUM (because lines get re-ordered)
                    if not header:
                        header = ln
                        error_msg = bkc_check_header(cs, ln)
                    else:
                        imp_rows.append(cs)
                except Exception as ex:
                    error_msg = "Booking.com line normalize exception: {}".format(ex)
                log_import("Normalized import line: " + str(imp_rows[-1]), fn, idx)
                if error_msg:
                    log_error(error_msg, fn, idx)
                    if cae.get_option('breakOnError'):
                        break

            if got_cancelled() or (error_log and cae.get_option('breakOnError')):
                break

            # sort by ext book ref, room info, adults and arrival date for to allow to join date ranges
            imp_rows.sort(key=lambda f: f[BKC_BOOK_REF] + f[BKC_ROOM_INFO] + f[BKC_ADULTS] + f[BKC_ARR_DATE])

            for idx, ln in enumerate(imp_rows):
                if got_cancelled():
                    log_error("User cancelled loading and parsing of BKC import line", fn, idx, importance=4)
                    break
                if debug_level >= DEBUG_LEVEL_VERBOSE:
                    log_import("Parsing import line: " + ln, fn, int(ln[BKC_LINE_NUM]))
                try:
                    error_msg = bkc_line_to_res_row(ln, hotel_id, fn, int(ln[BKC_LINE_NUM]), res_rows)
                except Exception as ex:
                    error_msg = "Booking.com line parse exception: {}".format(ex)
                log_import("Parsed import line: " + str(res_rows[-1]), fn, int(ln[BKC_LINE_NUM]))
                if error_msg:
                    log_error(error_msg, fn, int(ln[BKC_LINE_NUM]))
                    if cae.get_option('breakOnError'):
                        break

            if error_log and cae.get_option('breakOnError'):
                break

    if cae.get_option('rciPath') and rci_files and (not error_log or not cae.get_option('breakOnError')) \
            and not got_cancelled():
        log_import("Starting RCI import", NO_FILE_PREFIX_CHAR + 'RciImportStart', importance=4)
        if debug_level >= DEBUG_LEVEL_VERBOSE:
            log_import("RCI files: " + str(rci_files), NO_FILE_PREFIX_CHAR + 'RciFileCollect', importance=1)

        # re-create resort match codes config value from Acumen data if empty
        if not cae.get_config('ClientRefsResortCodes'):
            m1 = conf_data.load_view(None, 'T_CD', ["CD_CODE"], "CD_RCI_REF in (:rci_refs)",
                                     {'rci_refs': conf_data.client_refs_add_exclude})
            m2 = conf_data.load_view(None, 'T_CR', ["CR_CDREF"], "CR_TYPE like 'RCI%' and CR_REF in (:rci_refs)",
                                     {'rci_refs': conf_data.client_refs_add_exclude})
            if m1 is None or m2 is None:
                error_msg = "Resort match code fetch error"
                log_error(error_msg, NO_FILE_PREFIX_CHAR + 'RciResortCodesDataFetch', importance=3)
                return
            match_codes = sorted(list(set([_[0] for _ in m1 + m2])))
            cae.set_config('ClientRefsResortCodes', EXT_REFS_SEP.join(match_codes))

        error_msg = conf_data.fetch_contacts()      # load clients data
        if error_msg:
            log_error(error_msg, NO_FILE_PREFIX_CHAR + 'RciClientDataFetch', importance=3)
            return

        error_msg = conf_data.fetch_res_inv_data()  # load reservation inventory data
        if error_msg:
            log_error(error_msg, NO_FILE_PREFIX_CHAR + 'RciResInvDataFetch', importance=3)
            return

        imp_rows = list()
        points_import = False
        for fn in rci_files:
            if got_cancelled():
                log_error("User cancelled loading of import files", fn, importance=4)
                break
            log_import("Loading import file " + fn, fn, importance=4)
            with open(fn, 'r', encoding='utf-16') as fp:
                lines = fp.readlines()

            progress = Progress(debug_level, start_counter=len(lines),
                                start_msg="Loading and parsing import file " + fn,
                                nothing_to_do_msg="No records found in import file " + fn)

            for idx, ln in enumerate(lines):
                if got_cancelled():
                    log_error("User cancelled loading and parsing of import files", fn, idx, importance=4)
                    break
                progress.next(processed_id='import file line ' + str(idx + 1), error_msg=error_msg)
                if debug_level >= DEBUG_LEVEL_VERBOSE:
                    log_import("Import line loaded: " + ln, fn, idx)
                if idx == 0:  # first line is header
                    if ln == RCI_FILE_HEADER:
                        points_import = False
                    elif ln == RCIP_FILE_HEADER:
                        points_import = True
                    else:
                        log_error("Skipped import file {} with invalid file header {}".format(fn, ln), fn, idx)
                        break
                else:
                    func = rcip_imp_line_check if points_import else rci_imp_line_check
                    imp_cols, error_msg = func(ln, fn, idx)
                    if not imp_cols:
                        if debug_level >= DEBUG_LEVEL_VERBOSE:
                            log_import(error_msg or "Import line skipped", fn, idx)
                        error_msg = ""
                        continue  # ignoring imported line
                    if not error_msg:
                        imp_rows.append(imp_cols)
                if error_msg:
                    log_error("RCI{} import line error: {}".format('P' if points_import else '', error_msg), fn, idx)
                    if cae.get_option('breakOnError'):
                        break
            progress.finished(error_msg=error_msg)
            error_msg = ""
            if error_log and cae.get_option('breakOnError'):
                break

        if not got_cancelled() and (not error_log or not cae.get_option('breakOnError')):
            log_import("Processing clients", NO_FILE_PREFIX_CHAR + 'RciProcessClients', importance=4)
            progress = Progress(debug_level, start_counter=len(imp_rows),
                                start_msg="Sending {run_counter} clients to Sihot",
                                nothing_to_do_msg="No client records to be send to Sihot")
            client_send = ClientToSihot(cae, use_kernel_interface=cae.get_option('useKernelForClient'),
                                        map_client=cae.get_option('mapClient'), connect_to_acu=False)

            # sent_contacts is for to detect clients sent already by SihotResSync and duplicate clients in import file
            sent_clients = conf_data.sent_contacts()
            for lni, imp_cols in enumerate(imp_rows):
                fn, idx = imp_cols[RC_FILE_NAME], imp_cols[RC_LINE_NUM]
                if got_cancelled():
                    log_error("User cancelled client parsing and send", fn, idx, importance=4)
                    break
                progress.next(processed_id="Parsing and sending client " + str(lni), error_msg=error_msg)
                which_clients = ['occupant', 'owner']
                clients_indexes = [imp_cols[RC_OCC_CLIENTS_IDX], imp_cols[RC_OWN_CLIENTS_IDX]]
                if imp_cols[RC_POINTS]:
                    funcs = [rcip_line_to_occ_client_row, rcip_line_to_own_client_row]
                else:
                    funcs = [rci_line_to_occ_client_row, rci_line_to_own_client_row]
                for which_client, clients_idx, func in zip(which_clients, clients_indexes, funcs):
                    if clients_idx == -1:
                        continue
                    try:
                        client_row, error_msg = func(imp_cols)
                    except Exception as ex:
                        error_msg = which_client + "/client line parse exception: {}".format(ex)
                    if not error_msg:
                        if debug_level >= DEBUG_LEVEL_VERBOSE:
                            log_import("Parsed " + which_client + "/client data: " + str(client_row), fn, idx)
                        if clients_idx in sent_clients:
                            if debug_level >= DEBUG_LEVEL_VERBOSE:
                                log_import(which_client + "/client {} skip"
                                           .format(conf_data.contacts[clients_idx]), fn, idx)
                            continue
                        rc_complete_client_row_with_ext_refs(client_row, conf_data.contact_ext_refs(clients_idx))
                        try:
                            error_msg = client_send.send_client_to_sihot(client_row)
                            if not error_msg:
                                if debug_level >= DEBUG_LEVEL_VERBOSE:
                                    log_import("Sent " + which_client + "/client: " + str(client_row), fn, idx)
                                client_row['CD_SIHOT_OBJID'] = client_send.response.objid
                                conf_data.complete_contacts_with_sh_id(clients_idx, client_row['CD_SIHOT_OBJID'])
                                sent_clients.append(clients_idx)
                        except Exception as ex:
                            error_msg = which_client + "/client send exception: {}".format(full_stack_trace(ex))
                        if error_msg:
                            break

                if error_msg:
                    log_error(error_msg, fn, idx)
                    if cae.get_option('breakOnError'):
                        break

            progress.finished(error_msg=error_msg)
            error_msg = ""

        # overwrite clients data if at least one client got changed/extended
        if conf_data.contacts_changed:
            conf_data.save_contacts()

        # now parse RCI reservations
        if not got_cancelled() and (not error_log or not cae.get_option('breakOnError')):
            log_import("Parsing reservations", NO_FILE_PREFIX_CHAR + 'RciParseRes', importance=4)
            progress = Progress(debug_level, start_counter=len(imp_rows),
                                start_msg="Parsing {run_counter} reservations",
                                nothing_to_do_msg="No reservation records to be parsed")
            for lni, imp_cols in enumerate(imp_rows):
                fn, idx = imp_cols[RC_FILE_NAME], imp_cols[RC_LINE_NUM]
                if got_cancelled():
                    log_error("User cancelled reservation parsing", fn, idx, importance=4)
                    break
                progress.next(processed_id="Parsing reservation " + str(lni), error_msg=error_msg)
                func = rcip_line_to_res_row if imp_cols[RC_POINTS] else rci_line_to_res_row
                try:
                    if debug_level >= DEBUG_LEVEL_VERBOSE:
                        log_import("Parsing import line: " + str(imp_cols), fn, idx)
                    res_row, error_msg = func(imp_cols)
                    if debug_level >= DEBUG_LEVEL_VERBOSE:
                        log_import("Parsed import columns: " + str(res_row), fn, idx)
                    res_rows.append(res_row)
                except Exception as ex:
                    error_msg = "res line parse exception: {}".format(ex)
                if error_msg:
                    log_error("Parse reservation error: {}".format(error_msg), fn, idx)
                    if cae.get_option('breakOnError'):
                        break

            progress.finished(error_msg=error_msg)
            error_msg = ""

    if cae.get_option('jsonPath') and jso_files and (not error_log or not cae.get_option('breakOnError')) \
            and not got_cancelled():
        log_import("Starting OTA JSON import", NO_FILE_PREFIX_CHAR + 'JsonImportStart', importance=4)
        if debug_level >= DEBUG_LEVEL_VERBOSE:
            log_import("JSON files: " + str(jso_files), NO_FILE_PREFIX_CHAR + 'JsonFileCollect', importance=1)

        progress = Progress(debug_level, start_counter=len(jso_files),
                            start_msg="Loading and parsing JSON import files",
                            nothing_to_do_msg="No JSON files found in import folder " + cae.get_option('jsonPath'))
        for fn in jso_files:
            if got_cancelled():
                log_error("User cancelled loading of JSON import files", fn, importance=4)
                break
            log_import("Loading JSON import file " + fn, fn, importance=4)
            with open(fn, 'r', encoding='utf-8') as fp:
                json_data = json.load(fp)

            if debug_level >= DEBUG_LEVEL_VERBOSE:
                log_import("JSON import file {} loaded; content={}".format(fn, json_data), fn)

            for idx, json_res in enumerate(json_data):
                res_row, error_msg = json_imp_to_res_row(json_res, fn, idx)
                if not res_row:
                    if debug_level >= DEBUG_LEVEL_VERBOSE:
                        log_import(error_msg or "JSON import file/reservation skipped", fn, idx)
                    error_msg = ""
                    continue  # ignoring imported reservation
                if not error_msg:
                    res_rows.append(res_row)
                progress.next(processed_id="import file {} reservation {}".format(fn, idx + 1), error_msg=error_msg)
                if error_msg:
                    log_error("OTA/JSON reservation import error: {}".format(error_msg), fn, idx)
                    if cae.get_option('breakOnError'):
                        break
            if error_msg:
                log_error("OTA/JSON file import error: {}".format(error_msg), fn)
                if cae.get_option('breakOnError'):
                    break

        progress.finished(error_msg=error_msg)
        error_msg = ""

    # #######################################################################################
    #  SEND imported reservation bookings of all supported booking channels (RCI, JSON)
    # #######################################################################################

    if not got_cancelled() and (not error_log or not cae.get_option('breakOnError')):
        log_import("Sending reservations to Sihot", NO_FILE_PREFIX_CHAR + 'SendResStart', importance=4)
        progress = Progress(debug_level, start_counter=len(res_rows),
                            start_msg="Prepare sending of {run_counter} reservation request changes to Sihot",
                            nothing_to_do_msg="No reservations found for to be sent")
        res_send = ResToSihot(cae, use_kernel_interface=cae.get_option('useKernelForRes'),
                              map_res=cae.get_option('mapRes'),
                              use_kernel_for_new_clients=cae.get_option('useKernelForClient'),
                              map_client=cae.get_option('mapClient'),
                              connect_to_acu=False)

        for res_row_idx, crow in enumerate(res_rows):
            fn, idx = crow['=FILE_NAME'], crow['=LINE_NUM']
            if got_cancelled():
                log_error("User cancelled reservation send", fn, idx, importance=4)
                break
            progress.next(processed_id=str(crow['RH_EXT_BOOK_REF']), error_msg=error_msg)
            try:
                error_msg = res_send.send_row_to_sihot(crow, ensure_client_mode=ECM_DO_NOT_SEND_CLIENT)
            except Exception as ex:
                error_msg = "reservation send exception: {}".format(full_stack_trace(ex))
            if error_msg:
                if error_msg.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                    log_import("Ignoring error sending res: " + str(crow), fn, idx)
                    error_msg = ''
                    continue
                if 'setDataRoom not available!' in error_msg:  # was: 'A_Persons::setDataRoom not available!'
                    error_msg = "Apartment {} occupied between {} and {} - created GDS-No {} for manual allocation." \
                        .format(crow['RUL_SIHOT_ROOM'], crow['ARR_DATE'].strftime('%d-%m-%Y'),
                                crow['DEP_DATE'].strftime('%d-%m-%Y'), crow['SIHOT_GDSNO']) \
                        + (" Original error: " + error_msg if debug_level >= DEBUG_LEVEL_VERBOSE else "")
                log_error(error_msg, fn, idx)
                if cae.get_option('breakOnError'):
                    break
            elif debug_level >= DEBUG_LEVEL_VERBOSE:
                log_import("Sent res: " + str(crow), fn, idx)

        warnings = res_send.get_warnings()
        progress.finished(error_msg=error_msg)
    else:
        warnings = ""

    # #########################################################
    # logging and clean up
    # #########################################################

    if got_cancelled():
        log_import("Import cancelled by user", NO_FILE_PREFIX_CHAR + 'UserCancellation', importance=4)

    log_import("Log and send warnings", NO_FILE_PREFIX_CHAR + 'LogSendWarnings', importance=4)
    if warnings:
        if debug_level >= DEBUG_LEVEL_VERBOSE:
            log_import("Sending warnings: " + warnings, NO_FILE_PREFIX_CHAR + 'SendResWarnings')
        if notification:
            notification.send_notification(warnings, subject="SihotResImport warnings notification",
                                           mail_to=cae.get_option('warningsMailToAddr'))

    log_import("Pass Import Files to user/server logs", NO_FILE_PREFIX_CHAR + 'MoveImportFiles', importance=4)
    for sfn in tci_files + bkc_files + rci_files + jso_files:
        imp_file_path = os.path.dirname(sfn)
        imp_dir_name = os.path.basename(os.path.normpath(imp_file_path))
        imp_file_name = os.path.basename(sfn)

        # first copy imported file to tci/bkc/rci logging sub-folder (on the server)
        dfn = os.path.join(log_file_path, imp_dir_name, log_file_prefix + '_' + imp_file_name)
        shutil.copy2(sfn, dfn)
        if debug_level >= DEBUG_LEVEL_VERBOSE:
            log_import(sfn + " copied to " + dfn, sfn)

        ddn = os.path.join(imp_file_path, 'processed')
        if not os.path.isdir(ddn):
            os.mkdir(ddn)

        # if no error happened in the imported file - then move it to the processed sub-folder (on the users machine)
        if not [_ for _ in error_log if sfn in _['context']]:   # sfn == _['context'] should work too
            dfn = os.path.join(ddn, log_file_prefix + '_' + imp_file_name)
            os.rename(sfn, dfn)
            log_import(sfn + ' moved to ' + dfn, sfn)

        # create import log file for each import file (on the user machine)
        log_msg = '\n\n'.join(_['context'] + '@' + str(_['line']) + ':' + _['message'] for _ in import_log
                              if _['context'][0] == NO_FILE_PREFIX_CHAR or sfn in _['context'])
        with open(os.path.join(ddn, log_file_prefix + '_' + imp_file_name + '_import.log'), 'a') as fh:
            fh.write(fix_encoding(log_msg, encoding=fh.encoding, context="SihotResImport File Log Fix Encoding"))

    if error_log:
        error_text = '\n'.join(_['context'] + '@' + str(_['line']) + ':' + _['message'] for _ in error_log)
        if notification:
            notification_err = notification.send_notification(error_text, subject="SihotResImport error notification")
            if notification_err:
                error_text += "Notification send error: " + notification_err
                log_import("Notification send error: " + notification_err, NO_FILE_PREFIX_CHAR + 'SendNotification')
        uprint('****  Error Log:\n', error_text)
        with open(os.path.join(log_file_path, log_file_prefix + '_errors.log'), 'a') as fh:
            fh.write(fix_encoding(error_text, encoding=fh.encoding, context="SihotResImport Error Log Fix Encoding"))

    log_msg = '\n'.join(_['context'] + '@' + str(_['line']) + ':' + _['message'] for _ in import_log)
    with open(os.path.join(log_file_path, log_file_prefix + '_import.log'), 'a') as fh:
        fh.write(fix_encoding(log_msg, encoding=fh.encoding, context="SihotResImport Import Log Fix Encoding"))

    if not amend_screen_log:        # import running in console mode (no UI)
        quit_app(error_log)


def quit_app(err_log=None):
    cae.shutdown(12 if err_log else 0)


if cae.get_option('acuPassword'):
    # running without ui in console

    # (added next line for to remove inspection warning on "too broad exception clause")
    # noinspection PyBroadException
    try:
        run_import(cae.get_option('acuUser'), cae.get_option('acuPassword'))
    except KeyboardInterrupt:
        uprint("\n****  SihotResImport run cancelled by user\n")
    except Exception as ri_ex:
        uprint("\n****  SihotResImport exception:\n", format_exc())

else:
    # no password given, then we need the kivy UI for to logon the user
    import threading

    sys.argv = [sys.argv[0]]  # remove command line options for to prevent errors in kivy args_parse
    from kivy.config import Config  # window size have to be specified before any other kivy imports
    Config.set('graphics', 'width', '1800')
    Config.set('graphics', 'height', '999')
    from kivy.app import App
    from kivy.core.window import Window
    from kivy.lang.builder import Factory
    from kivy.properties import NumericProperty, StringProperty
    from kivy.uix.textinput import TextInput
    from kivy.utils import escape_markup
    from kivy.clock import mainthread


    class CapitalInput(TextInput):
        def insert_text(self, substring, from_undo=False):
            return super(CapitalInput, self).insert_text(substring.upper(), from_undo=from_undo)


    class SihotResImportApp(App):
        file_count = NumericProperty(0)
        file_names = StringProperty()
        user_name = StringProperty(cae.get_option('acuUser'))
        user_password = StringProperty(cae.get_option('acuPassword'))

        cancel_import = threading.Event()
        _thread = None

        def build(self):
            cae.dprint("App.build()", minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            self.display_files()
            self.title = "Sihot Reservation Import  V " + __version__
            self.root = Factory.MainWindow()
            return self.root

        def display_files(self):
            cae.dprint("App.display_files()", minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            collect_files()  # collect files for showing them in the user interface
            self.file_count = len(imp_files)
            self.file_names = ''
            for fn in imp_files:
                fn = os.path.splitext(os.path.basename(fn))[0]
                self.file_names += '\n' + fn

        def key_down_callback(self, keyboard, key_code, scan_code, text, modifiers, *args, **kwargs):
            if True:   # change to True for debugging - leave dprint for hiding Pycharm inspection "Parameter not used"
                cae.dprint("App.kbd {!r} key {} pressed, scan code={!r}, text={!r}, modifiers={!r}, args={}, kwargs={}"
                           .format(keyboard, key_code, scan_code, text, modifiers, args, kwargs),
                           minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            if self._thread and self._thread.is_alive():                        # block kbd while import is running
                return True
            elif key_code == 27:                                                # escape key
                self.exit_app()
                return True
            elif key_code == 13 and not self.root.ids.import_button.disabled:   # enter key
                self.start_import()
                return True
            return False

        def on_start(self):
            cae.dprint("App.on_start()", minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            Window.bind(on_key_down=self.key_down_callback)

        def on_stop(self):
            cae.dprint("App.on_stop()", minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            self.cancel_import.set()
            self.exit_app()

        @mainthread
        def amend_screen_log(self, text, is_error=False):
            beg_color, end_color = '[color=ff99aa]', '[/color]'
            # text = text.replace('[', '&bl;').replace(']', '&br;').replace('&', '&amp;') # convert special markup chars
            text = '\n' + escape_markup(text)
            if is_error:
                text = beg_color + text + end_color
            ti = self.root.ids.error_log
            text = (ti.text + text)[-MAX_SCREEN_LOG_LEN:]
            beg_pos, end_pos = text.find(beg_color), text.find(end_color)
            if beg_pos > end_pos or beg_pos == -1 and end_pos >= 0:
                # prevent Label color markup warning message "pop style stack without push"
                text = beg_color + text
            ti.text = text
            self.root.ids.scroll_view.scroll_y = 0

        def start_import(self):
            cae.dprint("App.start_import()", minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            usr = self.root.ids.user_name.text
            cae.set_config('acuUser', usr.upper())
            self.prepare_ui_for_import()

            self._thread = threading.Thread(target=self.exec_import,
                                            args=(usr, self.root.ids.user_password.text,
                                                  self.cancel_import.is_set, self.amend_screen_log))
            self._thread.start()

        def prepare_ui_for_import(self):
            cae.dprint("App.prepare_ui_for_import()", minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            ids = self.root.ids
            ids.user_name.disabled = True
            ids.user_password.disabled = True
            ids.import_button.disabled = True
            ids.exit_or_cancel_button.text = "Cancel Import"

        def exec_import(self, usr, pw, event_is_set_func, amend_screen_log_func):
            cae.dprint("App.exec_import()", minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            # (added next line for to remove inspection warning on "too broad exception clause")
            # noinspection PyBroadException
            try:
                run_import(usr, pw, event_is_set_func, amend_screen_log_func)
            except Exception:
                exc_and_tb = format_exc()
                cae.dprint(exc_and_tb)
                self.amend_screen_log(exc_and_tb, is_error=True)
            self.finalize_import()

        def finalize_import(self):
            cae.dprint("App.finalize_import()", minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            ids = self.root.ids
            self.user_password = ""         # reset pw - user need to enter again for new import run
            ids.user_password.text = ""     # .. should be set by app.user_password kv expression but isn't
            self.display_files()            # self.file_count (triggering reset of import_button.text/.disabled)
            # ids.import_button.disabled = not self.file_count or not ids.user_name.text or not ids.user_password.text
            ids.exit_or_cancel_button.text = "Exit"
            ids.user_name.disabled = False
            ids.user_password.disabled = False
            self._thread = None

        def exit_app_or_cancel_import(self):
            cae.dprint("App.exit_app_or_cancel_import(), thread-alive={}, is_set={}"
                       .format(self._thread.is_alive() if self._thread else 'finished', self.cancel_import.is_set()),
                       minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            if self._thread and self._thread.is_alive():
                self.cancel_import.set()
                self._thread.join()
                self.cancel_import.clear()
            # elif self.cancel_import.is_set():   # if import got just cancelled - leave UI running
            #     self.cancel_import.clear()
            else:
                self.exit_app()

        def exit_app(self):
            cae.dprint("App.exit_app()", minimum_debug_level=DEBUG_LEVEL_VERBOSE)
            if self._thread and self._thread.is_alive():
                self.cancel_import.set()
                cae.dprint("  ....  waiting for to join/finish worker thread")
                self._thread.join()
                cae.dprint("  ....  worker thread successfully joined/finished")
            quit_app()

    SihotResImportApp().run()
