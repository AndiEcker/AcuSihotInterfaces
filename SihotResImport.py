"""
    0.1     first beta.
"""
import sys
import os
import shutil
import glob
import datetime
import csv

from console_app import ConsoleApp, Progress, uprint, DEBUG_LEVEL_VERBOSE
from notification import Notification
from db import DEF_USER, DEF_DSN
from acu_sihot_config import Data
from sxmlif import ResToSihot, \
    SXML_DEF_ENCODING, ERR_MESSAGE_PREFIX_CONTINUE, \
    USE_KERNEL_FOR_CLIENTS_DEF, USE_KERNEL_FOR_RES_DEF, MAP_CLIENT_DEF, MAP_RES_DEF, \
    ACTION_DELETE, ACTION_INSERT, ACTION_UPDATE

__version__ = '0.1'

RUN_MODE_CONSOLE = 'c'
RUN_MODE_UI = 'u'

cae = ConsoleApp(__version__, "Import reservations from external systems (Thomas Cook, RCI) into the SiHOT-PMS",
                 debug_level_def=DEBUG_LEVEL_VERBOSE)
cae.add_option('tciPath', "Import path and file mask for Thomas Cook R*.TXT-tci_files", 'C:/TC_Import/R*.txt', 'j')
cae.add_option('bkcPath', "Import path and file mask for Booking.com CSV-tci_files", 'C:/BC_Import/?_*.csv', 'y')
# cae.add_option('rciPath', "Import path and file mask for RCI CSV-tci_files", 'C:/RC_Import/*.csv', 'y')

cae.add_option('smtpServerUri', "SMTP error notification server URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP Sender/From address", '', 'f')
cae.add_option('smtpTo', "List/Expression of SMTP Receiver/To addresses", [], 'r')
cae.add_option('warningsMailToAddr', "Warnings SMTP receiver/to addresses (if differs from smtpTo)", [], 'v')

cae.add_option('acuUser', "User name of Acumen/Oracle system", DEF_USER, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", DEF_DSN, 'd')

cae.add_option('serverIP', "IP address of the SIHOT interface server", 'localhost', 'i')
cae.add_option('serverPort', "IP port of the WEB interface of this server", 14777, 'w')
cae.add_option('serverKernelPort', "IP port of the KERNEL interface of this server", 14772, 'k')

cae.add_option('timeout', "Timeout value for TCP/IP connections", 39.6)
cae.add_option('xmlEncoding', "Charset used for the xml data", SXML_DEF_ENCODING, 'e')

cae.add_option('useKernelForClient', "Used interface for clients (0=web, 1=kernel)", USE_KERNEL_FOR_CLIENTS_DEF, 'g')
cae.add_option('mapClient', "Guest/Client mapping of xml to db items", MAP_CLIENT_DEF, 'm')
cae.add_option('useKernelForRes', "Used interface for reservations (0=web, 1=kernel)", USE_KERNEL_FOR_RES_DEF, 'z')
cae.add_option('mapRes', "Reservation mapping of xml to db items", MAP_RES_DEF, 'n')

cae.add_option('breakOnError', "Abort importation if an error occurs (0=No, 1=Yes)", 0, 'b')

last_rt_prefix = cae.get_option('acuDSN')[-4:]
lastRt = cae.get_config(last_rt_prefix + 'lastRt')
if lastRt.startswith('@'):
    uprint("****  Reservation import process is still running from last batch, started at ", lastRt[1:])
    cae.shutdown(4)
err_msg = cae.set_config(last_rt_prefix + 'lastRt', '@' + str(datetime.datetime.now()))
if err_msg:
    uprint(err_msg)

uprint('Import path/file-mask for Thomas Cook/Booking.com:', cae.get_option('tciPath'), cae.get_option('bkcPath'))
notification = None
if cae.get_option('smtpServerUri') and cae.get_option('smtpFrom') and cae.get_option('smtpTo'):
    notification = Notification(smtp_server_uri=cae.get_option('smtpServerUri'),
                                mail_from=cae.get_option('smtpFrom'),
                                mail_to=cae.get_option('smtpTo'),
                                used_system=cae.get_option('acuDSN') + '/' + cae.get_option('serverIP'),
                                debug_level=cae.get_option('debugLevel'))
    uprint('SMTP/From/To:', cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))
    if cae.get_option('warningsMailToAddr'):
        uprint('Warnings SMTP receiver address:', cae.get_option('warningsMailToAddr'))

uprint('Acumen DSN:', cae.get_option('acuDSN'))
uprint('Server IP/port:', cae.get_option('serverIP'), cae.get_option('serverPort'))
uprint('TCP Timeout/XML Encoding:', cae.get_option('timeout'), cae.get_option('xmlEncoding'))
uprint('Use Kernel for clients:', 'Yes' if cae.get_option('useKernelForClient') else 'No (WEB)')
uprint('Use Kernel for reservations:', 'Yes' if cae.get_option('useKernelForRes') else 'No (WEB)')
uprint('Current run startup time:', cae.get_config(last_rt_prefix + 'lastRt'))
uprint('Break on error:', 'Yes' if cae.get_option('breakOnError') else 'No')

# check if Acumen domain/user/pw is fully specified and show kivy UI for to enter them if not
run_mode = RUN_MODE_CONSOLE if cae.get_config('acuPassword') else RUN_MODE_UI
sub_res_id = 0      # for Booking.com group reservations

'''# #########################################################
   # file collection, logging and progress helpers
   # #########################################################
'''
error_log = ''


def log_error(err):
    global error_log
    uprint(err)
    error_log += '\n' + err

lf = cae.get_option('logFile')
log_file_prefix = os.path.splitext(os.path.basename(lf))[0]
log_file_path = os.path.dirname(lf)

tci_files = []
bkc_files = []
rci_files = []
imp_files = []


def collect_files():
    global tci_files, bkc_files, rci_files, imp_files
    tci_files = glob.glob(cae.get_option('tciPath')) if cae.get_option('tciPath') else []
    bkc_files = glob.glob(cae.get_option('bkcPath')) if cae.get_option('bkcPath') else []
    rci_files = glob.glob(cae.get_option('rciPath')) if cae.get_option('rciPath') else []
    imp_files = tci_files + bkc_files + rci_files


'''# #########################################################
   # reservation import
   # #########################################################
'''


def run_import(acu_user, acu_password):
    global sub_res_id, error_log, tci_files, bkc_files, rci_files

    uprint('Acumen Usr:', acu_user)

    # #########################################################
    # Login - user authentication
    # #########################################################
    conf_data = Data(acu_user=acu_user, acu_password=acu_password, acu_dsn=cae.get_option('acuDSN'))
    if conf_data.error_message:
        log_error(conf_data.error_message)
        return

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

        comments = []
        ap_feats = []
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

    def tci_line_to_res_row(curr_line, last_line, rows):
        """ TC import file has per line one pax """
        curr_cols = curr_line.split(';')

        # no header for to check but each last_line should start with either CNL, BOK or RBO
        if len(curr_cols) <= TCI_NEW_LINE:
            return 'tci_line_to_res_row(): incomplete line, missing {} columns' \
                .format(TCI_NEW_LINE - len(curr_cols) + 1)
        elif curr_cols[TCI_BOOK_TYPE] not in ('CNL', 'BOK', 'RBO'):
            return 'tci_line_to_res_row(): invalid line prefix {}'.format(curr_line[:3])
        elif curr_cols[TCI_RESORT] not in ('BEVE', 'PABE'):
            return 'tci_line_to_res_row(): invalid resort {}'.format(curr_cols[TCI_RESORT])
        elif curr_cols[TCI_NEW_LINE] != '\n':
            return 'tci_line_to_res_row(): incomplete line (missing end of line)'

        room_cat, half_board, comments = tci_cat_board_comments(curr_cols)
        is_adult = curr_cols[TCI_PAX_TYPE] in ('M', 'F')
        comments.append(curr_cols[TCI_COMMENT])  # start with apartment feature comments then client comment
        meal_plan = curr_cols[TCI_MEAL_PLAN]

        row = {}
        if last_line:  # check if current line is an extension of the booking from last line (only not in first line)
            last_cols = last_line.split(';')
            if last_cols[TCI_BOOK_IDX] == curr_cols[TCI_BOOK_IDX] \
                    and int(last_cols[TCI_PAX_IDX]) + 1 == int(curr_cols[TCI_PAX_IDX]):
                # additional pax
                row = rows[-1]
            elif last_cols[TCI_BOOK_EXT] == 'H' and curr_cols[TCI_BOOK_EXT] == 'E'\
                    and last_cols[TCI_BOOK_REF] == curr_cols[TCI_LINK_REF] \
                    and last_cols[TCI_LINK_REF] == curr_cols[TCI_BOOK_REF]:
                # additional pax (maybe with different LengthOfStay)
                row = rows[-1]
                comments.append(curr_cols[TCI_LINK_REF] + '-' + curr_cols[TCI_BOOK_EXT])
                if datetime.timedelta(int(curr_cols[TCI_STAY_DAYS])) != row['DEP_DATE'] - row['ARR_DATE']:
                    comments.append('(LengthOfStay differs!)')
            elif last_cols[TCI_BOOK_IDX] > '1' or last_cols[TCI_BOOK_REF] == curr_cols[TCI_BOOK_REF]:
                # separate room - mostly with same TC booking reference
                rows[-1]['SIHOT_NOTE'] += '+' + curr_cols[TCI_BOOK_REF] + '-' + curr_cols[TCI_BOOK_IDX]
                rows[-1]['SIHOT_TEC_NOTE'] += '|CR|+' + curr_cols[TCI_BOOK_REF] + '-' + curr_cols[TCI_BOOK_IDX]
                comments.append(curr_cols[TCI_BOOK_REF] + '-' + curr_cols[TCI_BOOK_IDX])

        if row:  # add next pax - extending previous row
            for txt in comments:
                if txt not in row['SIHOT_NOTE']:
                    row['SIHOT_NOTE'] += ';' + txt
                    row['SIHOT_TEC_NOTE'] += '|CR|' + txt
            row['RU_ADULTS' if is_adult else 'RU_CHILDREN'] += 1
        else:
            rows.append(row)
            row['SIHOT_GDSNO'] = TCI_GDSNO_PREFIX + curr_cols[TCI_BOOK_PREFIX] + curr_cols[TCI_BOOK_REF]  # GDSNO
            row['SH_RES_TYPE'] = 'S' if curr_cols[TCI_BOOK_TYPE] == 'CNL' else '1'
            row['SIHOT_HOTEL_C'] = '1' if curr_cols[TCI_RESORT] == 'BEVE' else '4'  # 1=BHC, 4=PBC
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

        # add pax name and person sequence number
        name_col = 'SH_' + ('ADULT' if is_adult else 'CHILD') \
                   + str(row['RU_ADULTS' if is_adult else 'RU_CHILDREN']) + '_NAME'
        row[name_col] = curr_cols[TCI_SURNAME]
        row[name_col + '2'] = curr_cols[TCI_FORENAME]
        pers_seq = row['RU_ADULTS'] if is_adult else 10 + row['RU_CHILDREN']
        row['SH_PERS_SEQ' + str(pers_seq)] = pers_seq - 1

        row['RUL_CHANGES'] = curr_line      # needed for error notification

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

    BKC_COL_COUNT = 12

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

    def bkc_check_header(cols, line):
        if len(cols) != BKC_COL_COUNT:
            return 'bkc_check_header(): invalid column count, {} differ'.format(BKC_COL_COUNT - len(cols))
        elif line != BKC_HEADER_LINE:
            return 'bkc_check_header(): invalid header or file format {}'.format(line)
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
                comments.append('bkc_room_cat_pax_board() warning: room size missing (using Studio)')
            room_size = 'STUDIO'
        ap_feats = []
        if room_info.find('SUPERIOR') >= 0:     # 748==AFT_CODE of "Refurbished" apt. feature
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

    def bkc_line_to_res_row(curr_cols, resort, rows):
        """ Booking.com can have various lines per booking - identified with external booking ref/BKC_BOOK_REF """
        global sub_res_id

        # no header for to check but each last_line should start with either CNL, BOK or RBO
        if len(curr_cols) != BKC_COL_COUNT:
            return 'bkc_line_to_res_row(): invalid column count, {} differ'.format(BKC_COL_COUNT - len(curr_cols))
        elif len(curr_cols[BKC_BOOK_DATE].split('-')[0]) != 4:
            return "bkc_line_to_res_row(): invalid booking date format '{}' instead of YYYY-MM-DD"\
                .format(curr_cols[BKC_BOOK_DATE])
        elif curr_cols[BKC_CHANNEL] != 'Booking.com':
            return 'bkc_line_to_res_row(): invalid channel {} instead of Booking.com'.format(curr_cols[BKC_CHANNEL])

        room_cat, adults, children, board, comments = bkc_cat_pax_board_comments(curr_cols, resort)
        curr_arr = datetime.datetime.strptime(curr_cols[BKC_ARR_DATE], '%Y-%m-%d')
        curr_dep = datetime.datetime.strptime(curr_cols[BKC_DEP_DATE], '%Y-%m-%d')

        ext_key = curr_cols[BKC_BOOK_REF]
        row = {}
        if rows:  # check if current line is an extension of the booking from last line (only not in first line)
            if BKC_GDSNO_PREFIX + ext_key in rows[-1]['SIHOT_GDSNO']:   # 'in' instead of '==' for to detect group res
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

            elif sub_res_id:    # reset sub-res-no if last line was group or a merged booking
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
            row['SIHOT_HOTEL_C'] = str(resort)  # 1=BHC, 4=PBC
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

        row['RUL_CHANGES'] = ','.join(curr_cols)      # needed for error notification

        return ''

    ''' **************************************************************************************
        RCI Bookings Import              #####################################################
        biggest differences to TCI and Booking.com import:
         o  client and matchcode explicitly created as guest record in Sihot
         o  room assigned to reservation
         o  possibly update of reservation inventory type (AOWN_ROREF) in Acumen needed
        **************************************************************************************
    '''
    RCI_RESORT = 1  # BHC=1442, BHH=2398, HMC=2429, PBC=0803 (see also RS_RCI_CODE)
    RCI_BOOK_REF = 2
    RCI_ARR_DATE = 3
    RCI_BOOK_TYPE = 4
    # RCI_IS_GUEST = 6
    RCI_SURNAME = 8
    RCI_FORENAME = 9
    RCI_GUEST_SURNAME = 12
    RCI_GUEST_FORENAME = 13
    RCI_APT_NO = 24
    # RCI_ROOM_SIZE = 25
    RCI_COL_COUNT = 35

    def rci_line_to_res_row(curr_line, rows):
        curr_cols = curr_line.split('\t')
        if curr_line[-1] != '\n':
            return 'rci_line_to_res_row(): incomplete line (missing end of line)'
        elif len(curr_cols) != RCI_COL_COUNT:
            return 'rci_line_to_res_row(): incomplete line (missing {} columns)'.format(RCI_COL_COUNT - len(curr_cols))
        elif curr_cols[RCI_RESORT] not in ('1442', '2398', '2429', '0803'):
            return 'rci_line_to_res_row(): invalid resort id {}'.format(curr_cols[RCI_RESORT])
        elif curr_cols[RCI_BOOK_TYPE] != 'Reserved':
            return ''  # skip/hide request and incomplete bookings (without any apartment value)
        elif 'RCI POINTS' in curr_cols[RCI_SURNAME] + curr_cols[RCI_FORENAME] \
                + curr_cols[RCI_GUEST_SURNAME] + curr_cols[RCI_GUEST_FORENAME]:
            return ''  # skip/ignore RCI Points bookings

        row = dict()
        row['RH_EXT_BOOK_REF'] = curr_cols[RCI_BOOK_REF]
        row['ARR_DATE'] = datetime.datetime.strptime(curr_cols[RCI_ARR_DATE][:10], '%Y-%m-%d')
        row['DEP_DATE'] = row['ARR_DATE'] + datetime.timedelta(7)
        row['RUL_SIHOT_ROOM'] = curr_cols[RCI_APT_NO]
        # room_size = 'STUDIO' if curr_cols[RCI_ROOM_SIZE][0] == 'S' else curr_cols[RCI_ROOM_SIZE][0] + ' BED'
        # comment = room_size + ' (' + row['RUL_SIHOT_ROOM'] + ')'
        rows.append(row)
        return ''

    RCIP_RESORT = 0
    RCIP_COL_COUNT = 99

    def rcip_line_to_res_row(curr_line, rows):
        curr_cols = curr_line.split('\t')

        if curr_line[-1] != '\n':
            return 'rcip_line_to_res_row(): incomplete line (missing end of line)'
        elif len(curr_cols) != RCIP_COL_COUNT:
            return 'rcip_line_to_res_row(): incomplete line, missing {} columns'.format(RCIP_COL_COUNT - len(curr_cols))
        elif curr_cols[RCIP_RESORT] not in ('1442', '2398', '2429', '0803'):
            return 'rcip_line_to_res_row(): invalid resort id {}'.format(curr_cols[RCIP_RESORT])

        rows.append({})

        return ''

    # #########################################################
    # LOAD import files
    # #########################################################
    collect_files()
    res_rows = []
    error_msg = ''

    if cae.get_option('tciPath'):
        uprint('####  Load Thomas Cook...  ####')
        ''' sort tci_files 1.ASCENDING by actualization date and 2.DESCENDING by file type (R5 first, then R3, then R1)
            .. for to process cancellation/re-bookings in the correct order.
            .. (date and type taken from file name R?_yyyy-mm-dd hh.mm.ss.txt - ?=1-booking 3-cancellation 5-re-booking)
            .. hour/minute/... info cannot be used because it happened (see 17-Jan-14 6:40=R1 and 6:42=R5)
            .. that the R3/5 tci_files had a higher minute value than the associated R1 file with correction booking.
        '''
        tci_files.sort(key=lambda f: os.path.basename(f)[1], reverse=True)
        tci_files.sort(key=lambda f: os.path.basename(f)[3:13])
        cae.dprint(tci_files)
        for fn in tci_files:
            with open(fn, 'r') as fp:
                lines = fp.readlines()

            last_ln = ''
            for idx, ln in enumerate(lines):
                cae.dprint(ln)
                try:
                    error_msg = tci_line_to_res_row(ln, last_ln, res_rows)
                except Exception as ex:
                    error_msg = 'TCI Line parse exception: {}'.format(ex)
                if error_msg:
                    log_error('Error in line {} of TCI file {}: {}'.format(idx + 1, fn, error_msg))
                    if cae.get_option('breakOnError'):
                        break
                last_ln = ln
            if error_log and cae.get_option('breakOnError'):
                break

    if cae.get_option('bkcPath') and (not error_log or not cae.get_option('breakOnError')):
        uprint('####  Load Booking.com...  ####')
        bkc_files.sort(key=lambda f: os.path.basename(f))
        cae.dprint(bkc_files)
        for fn in bkc_files:
            hotel_id = bkc_check_filename(fn)
            if not hotel_id:
                log_error('Hotel ID prefix followed by underscore character is missing in file name {} - skipping.'
                          .format(fn))
                continue

            with open(fn, 'r', encoding='utf-8-sig') as fp:     # encoding is removing the utf8 BOM 'ï»¿'
                lines = fp.readlines()
            # check/remove header and parse all other lines normalized into column list
            header = ''
            imp_rows = []
            for idx, ln in enumerate(lines):
                try:
                    ln = bkc_normalize_line(ln)
                    cs = [c for c in csv.reader([ln])][0]
                    if not header:
                        header = ln
                        error_msg = bkc_check_header(cs, ln)
                    else:
                        imp_rows.append(cs)
                except Exception as ex:
                    error_msg = 'Booking.com line parse exception: {}'.format(ex)
                if error_msg:
                    log_error("Error in line {} of Booking.com file {}: {}".format(idx + 1, fn, error_msg))
                    if cae.get_option('breakOnError'):
                        break

            if error_log and cae.get_option('breakOnError'):
                break

            # sort by ext book ref, room info, adults and arrival date for to allow to join date ranges
            imp_rows.sort(key=lambda f: f[BKC_BOOK_REF] + f[BKC_ROOM_INFO] + f[BKC_ADULTS] + f[BKC_ARR_DATE])

            for idx, ln in enumerate(imp_rows):
                cae.dprint(ln)
                try:
                    error_msg = bkc_line_to_res_row(ln, hotel_id, res_rows)
                except Exception as ex:
                    error_msg = 'Booking.com line parse exception: {}'.format(ex)
                if error_msg:
                    log_error("Error in line {} of Booking.com file {}: {}".format(idx + 1, fn, error_msg))
                    if cae.get_option('breakOnError'):
                        break

            if error_log and cae.get_option('breakOnError'):
                break

    if cae.get_option('rciPath') and (not error_log or not cae.get_option('breakOnError')):
        uprint('####  Load RCI...........  ####')
        cae.dprint(rci_files)
        for fn in rci_files:
            with open(fn, 'r') as fp:
                lines = fp.readlines()

            points_import = False
            for idx, ln in enumerate(lines):
                if idx == 0:  # first line is header
                    if ln == 'RESORT NAME\tRESORT ID\tRESERVATION NUMBER\tSTART DATE\tSTATUS\tRSVN TYPE\tGUEST CERT' \
                             '\tRCI ID\tMBR1 LAST\tMBR1 FIRST\tMBR EMAIL\tMBR TYPE\tGST LAST\tGST FIRST\tGST ADDR1' \
                             '\tGST ADDR2\tGST ITY\tGST STATE\tGST ZIP\tGST CNTRY\tGST PHONE\tGST EMAIL\tBOOK DT' \
                             '\tCXL DT\tUNIT\tBED\tOWNER ID\tOWNER FIRST\tOWNER LAST\tINT EXCH\tETL_ACTV_FLG' \
                             '\tETL_ACTV_FLG\tETL_ACTV_FLG\tETL_ACTV_FLG\tETL_ACTV_FLG\n':
                        points_import = False
                    elif ln == '':
                        points_import = True
                    else:
                        error_msg = 'Invalid file header'
                else:
                    cae.dprint(ln)
                    try:
                        if points_import:
                            error_msg = rcip_line_to_res_row(ln, res_rows)
                        else:
                            error_msg = rci_line_to_res_row(ln, res_rows)
                    except Exception as ex:
                        error_msg = 'line parse exception: {}'.format(ex)
                if error_msg:
                    log_error('Error in line {} of RCI{} file {}: {}'.format(idx + 1, 'P' if points_import else '',
                                                                             fn, error_msg))
                    if cae.get_option('breakOnError'):
                        break

            if error_msg and cae.get_option('breakOnError'):
                break

    # #########################################################
    # SEND imported bookings
    # #########################################################

    if not error_log or not cae.get_option('breakOnError'):
        uprint('####  Send reservations..  ####')

        acumen_req = ResToSihot(cae, use_kernel_interface=cae.get_option('useKernelForRes'),
                                map_res=cae.get_option('mapRes'),
                                use_kernel_for_new_clients=cae.get_option('useKernelForClient'),
                                map_client=cae.get_option('mapClient'),
                                connect_to_acu=False)
        progress = Progress(cae.get_option('debugLevel'), start_counter=len(res_rows),
                            start_msg='Prepare sending of {run_counter} reservation request changes to Sihot',
                            nothing_to_do_msg='SihotResImport: no files found in import folder(s)')
        for crow in res_rows:
            error_msg = acumen_req.send_row_to_sihot(crow)
            progress.next(processed_id=str(crow['RH_EXT_BOOK_REF']), error_msg=error_msg)
            if error_msg:
                if error_msg.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                    error_msg = ''
                    continue
                log_error('Error in sending reservation {} to Sihot {}'.format(crow, error_msg))
                if cae.get_option('breakOnError'):
                    break

        warnings = acumen_req.get_warnings()
        if notification and warnings:
            mail_to = cae.get_option('warningsMailToAddr')
            notification.send_notification(warnings, subject='SihotResImport warnings notification', mail_to=mail_to)

        progress.finished(error_msg=error_msg)

    # #########################################################
    # logging and clean up
    # #########################################################

    if error_log:
        with open(os.path.join(log_file_path, log_file_prefix, '_errors.log'), 'a') as fh:
            fh.write(error_log)
    else:
        uprint('####  Move Import Files..  ####')
        for sfn in tci_files + bkc_files + rci_files:
            dn = os.path.dirname(sfn)
            folder = os.path.basename(os.path.normpath(dn))
            filename = os.path.basename(sfn)
            # first copy imported file to tci/bkc/rci logging sub-folder (on the server)
            shutil.copy2(sfn, os.path.join(log_file_path, folder, log_file_prefix + '_' + filename))
            # .. then move the imported file to the processed sub-folder (on the users machine)
            ddn = os.path.join(dn, 'processed')
            if not os.path.isdir(ddn):
                os.mkdir(ddn)
            dfn = os.path.join(ddn, log_file_prefix + '_' + filename)
            os.rename(sfn, dfn)
            cae.dprint("   #  ", sfn, 'to', dfn, minimum_debug_level=DEBUG_LEVEL_VERBOSE)

    if error_log:
        if notification:
            notification.send_notification(error_log, subject="SihotResImport error notification")
        uprint('Error Log:', error_log)
        if run_mode == RUN_MODE_UI:
            return  # don't quit app for to show errors on screen to user

    quit_app(error_log)


def quit_app(err_log=None):
    # release dup exec lock
    set_opt_err = cae.set_config(last_rt_prefix + 'lastRt', str(-1))
    if set_opt_err:
        uprint('SihotResImport.quit_app() error:', set_opt_err)

    cae.shutdown(13 if set_opt_err else (12 if err_log else 0))


if run_mode == RUN_MODE_UI:
    sys.argv = [sys.argv[0]]    # remove command line options for to prevent errors in kivy args_parse
    from kivy.app import App
    from kivy.lang.builder import Factory
    from kivy.properties import NumericProperty, StringProperty
    from kivy.uix.textinput import TextInput

    class CapitalInput(TextInput):
        def insert_text(self, substring, from_undo=False):
            return super(CapitalInput, self).insert_text(substring.upper(), from_undo=from_undo)

    class SihotResImportApp(App):
        file_count = NumericProperty(0)
        file_names = StringProperty()
        user_name = StringProperty(cae.get_option('acuUser'))
        user_password = StringProperty(cae.get_option('acuPassword'))

        def build(self):
            cae.dprint('App.build()')
            self.display_files()
            self.root = Factory.MainWindow()
            return self.root

        def display_files(self):
            collect_files()  # collect files for showing them in the user interface
            self.file_count = len(imp_files)
            for fn in imp_files:
                fn = os.path.splitext(os.path.basename(fn))[0]
                self.file_names += '\n' + fn

        def on_start(self):
            cae.dprint('App.on_start()')

        def on_stop(self):
            cae.dprint('App.on_stop()')
            self.exit_app()

        @staticmethod
        def exit_app():
            cae.dprint('App.quit_app()')
            quit_app()

        def run_import(self):
            cae.dprint('App.run_import()')
            usr = self.root.ids.user_name.text
            cae.set_config('acuUser', usr.upper())
            self.root.ids.import_button.disabled = True
            run_import(usr, self.root.ids.user_password.text)
            self.root.ids.error_log.text = error_log
            self.user_password = ''     # wipe pw, normally run_import() exits the app, only executed on login error
            self.display_files()
            self.root.ids.import_button.disabled = False


    SihotResImportApp().run()

else:
    # running without ui in console
    run_import(cae.get_option('acuUser'), cae.get_option('acuPassword'))
