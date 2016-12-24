"""
    0.1     first beta.
"""
import os
import glob
import datetime

from console_app import ConsoleApp, Progress, uprint, DEBUG_LEVEL_VERBOSE
from notification import Notification
from db import DEF_USER, DEF_DSN
from acu_sihot_config import Data
from sxmlif import ResToSihot, \
    SXML_DEF_ENCODING, ERR_MESSAGE_PREFIX_CONTINUE, \
    USE_KERNEL_FOR_CLIENTS_DEF, USE_KERNEL_FOR_RES_DEF, MAP_CLIENT_DEF, MAP_RES_DEF, \
    ACTION_DELETE, ACTION_INSERT, ACTION_UPDATE

__version__ = '0.1'

cae = ConsoleApp(__version__, "Import reservations from external systems (Thomas Cook, RCI) into the SiHOT-PMS",
                 debug_level_def=DEBUG_LEVEL_VERBOSE)
cae.add_option('tciPath', "Import path and file mask for Thomas Cook R*.TXT-tci_files", 'C:/TourOp_Import/R*.txt', 'j')
cae.add_option('rciPath', "Import path and file mask for RCI CSV-tci_files", 'C:/RCI_Import/*.csv', 'y')

cae.add_option('smtpServerUri', "SMTP error notification server URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP Sender/From address", '', 'f')
cae.add_option('smtpTo', "SMTP Receiver/To addresses", '', 'r')
cae.add_option('warningsMailToAddr', "Warnings SMTP receiver/to addresses (if differs from smtpTo)", '[[]]', 'v')

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

cae.add_option('lastRt', "Timestamp of last command run", 'o')
cae.add_option('breakOnError', "Abort importation if an error occurs (0=No, 1=Yes)", 0, 'b')

lastRt = cae.get_option('lastRt')
if lastRt.startswith('@'):
    uprint("****  Reservation import process is still running from last batch, started at ", lastRt[1:])
    cae.shutdown(4)
error_msg = cae.set_option('lastRt', '@' + str(datetime.datetime.now()))
if error_msg:
    uprint(error_msg)

uprint('Import path/file-mask for Thomas Cook/RCI:', cae.get_option('tciPath'), cae.get_option('rciPath'))
notification = None
if cae.get_option('smtpServerUri') and cae.get_option('smtpFrom') and cae.get_option('smtpTo'):
    notification = Notification(smtp_server_uri=cae.get_option('smtpServerUri'),
                                mail_from=cae.get_option('smtpFrom'),
                                mail_to=cae.get_option('smtpTo').split(','),
                                used_system=cae.get_option('acuDSN') + '/' + cae.get_option('serverIp'),
                                debug_level=cae.get_option('debugLevel'))
    uprint('SMTP/From/To:', cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))
    if cae.get_option('warningsMailToAddr'):
        uprint('Warnings SMTP receiver address:', cae.get_option('warningsMailToAddr'))

uprint('Acumen Usr/DSN:', cae.get_option('acuUser'), cae.get_option('acuDSN'))
uprint('Server IP/port:', cae.get_option('serverIP'), cae.get_option('serverPort'))
uprint('TCP Timeout/XML Encoding:', cae.get_option('timeout'), cae.get_option('xmlEncoding'))
uprint('Use Kernel for clients:', 'Yes' if cae.get_option('useKernelForClient') else 'No (WEB)')
uprint('Use Kernel for reservations:', 'Yes' if cae.get_option('useKernelForRes') else 'No (WEB)')
uprint('Current run startup time:', cae.get_option('lastRt'))
uprint('Break on error:', 'Yes' if cae.get_option('breakOnError') else 'No')


conf_data = Data(acu_user=cae.get_option('acuUser'), acu_password=cae.get_option('acuPassword'),
                 acu_dsn=cae.get_option('acuDSN'))


''' Thomas Cook Bookings Import  #############################################
'''
# Thomas Cook import file format column indexes
TCI_BOOK_TYPE = 0
TCI_RESORT = 1          # PABE=PBC, BEVE=BHC
TCI_ARR_DATE = 3
TCI_STAY_DAYS = 4
TCI_ROOM_SIZE1 = 7
TCI_BOOK_IDX = 10
TCI_PAX_IDX = 11
TCI_ROOM_SIZE2 = 12
TCI_FLIGHT_NO = 14
TCI_BOOK_REF = 15
TCI_BOOK_PREFIX = 16    # also specifying client country (SD=Denmark, TF=Finland, VN=Norway, VS=Sweden/LS=cruiser)
TCI_SURNAME = 17
TCI_FORENAME = 18
TCI_PAX_TYPE = 19       # M=male adult, F=female adult, I=infant
TCI_MEAL_PLAN = 20
TCI_BOOK_DATE = 25
TCI_COMMENT = 28
TCI_BOOK_EXT = 31
TCI_LINK_REF = 32       # linked/extended reservation (can have different LengthOfStay) - added to reservation comment
TCI_CLIENT_CAT = 33
TCI_NEW_LINE = 34


def tci_determine_room_cat_and_extra_comment(curr_cols):
    room_size = curr_cols[TCI_ROOM_SIZE2].strip()   # A12 / A12SEA = Studio, A22 / A22SUP = 1 bed, A34 = 2 bed
    # ignore value in col 13 for certain codes because in this case the column 8 is correct
    if not room_size or room_size in ('H11-R2', 'H12-R2', 'H12BR2'):
        room_size = curr_cols[TCI_ROOM_SIZE1].strip()

    if room_size[-3:] == 'HAB':
        half_board = True
        # remove board info from unit size - these bookings had mostly also SPECIAL OFERTA in board info(TCI_MEAL_PLAN)
        room_size = room_size[:-3]
    else:
        half_board = False
    # if room_size[:3] not in ('A12', 'A22', 'A34') or room_size[3:] not in ('', 'ETG', 'HIF', 'SEA', 'VIE', 'SUP') or \
    #                len(room_size) < 3:
    #    err_msg = 'Warning: Unknown Apartment Size'

    extra_comment = ''
    ap_feats = []
    if room_size[3:] == 'ETG':          # A22ETG / A34ETG == 1 bed / 2 bed with Duplex
        extra_comment = '#Duplex'       # 752 == AFT_CODE of "Duplex" apt.feature - HARD - CODED?!?!?
        ap_feats.append(752)            # paid supplement
    elif room_size[3:] == 'HIF' or room_size[3:] == 'VIE':  # A12HIF/A22HIF/A34HIF==studio/1 bed/2 bed with high floor
        extra_comment = '#High Floor'   # 757 == HIF/"High Floor" in PBC == VIE/"View" in BHC
        ap_feats.append(757)            # paid supplement
    elif room_size[3:] == 'SEA':        # A12SEA / A22SEA == studio / 1 bed with sea / ocean view
        extra_comment = '#Seafront'     # 781 == AFT_CODE of "Seafront" apt.feature - HARD - CODED?!?!?
        ap_feats.append(781)
    elif room_size[3:] == 'SUP':        # 'A22SUP' == 1 Bed superior / recently - refurbished
        # A22SUP is a Sterling Suite so Reservations don't need a comment in the requnit
        extra_comment = '#Sterling'     # 748 == AFT_CODE of "Refurbished" apt.feature - HARD - CODED?!?!?
        ap_feats.append(748)

    room_cat = conf_data.get_size_cat('BHC' if curr_cols[TCI_RESORT] == 'BEVE' else 'PBC',  # BEVE=BHC, PABE=PBC
                                      'STUDIO' if room_size[1] == '1' else str(chr(ord(room_size[1]) - 1)) + ' BED',
                                      ap_feats)

    return room_cat, extra_comment, half_board


def tci_line_to_res_row(curr_line, last_line, rows):
    """ TC import file has per line one pax """
    curr_cols = curr_line.split(';')

    # no header for to check but each last_line should start with either CNL, BOK or RBO
    if len(curr_cols) <= TCI_NEW_LINE:
        return 'tci_line_to_res_row(): incomplete line (missing {} columns)'.format(TCI_NEW_LINE - len(curr_cols) + 1)
    elif curr_cols[TCI_BOOK_TYPE] not in ('CNL', 'BOK', 'RBO'):
        return 'tci_line_to_res_row(): invalid line prefix {}'.format(curr_line[:3])
    elif curr_cols[TCI_RESORT] not in ('BEVE', 'PABE'):
        return 'tci_line_to_res_row(): invalid resort {}'.format(curr_cols[TCI_RESORT])
    elif curr_cols[TCI_NEW_LINE] != '\n':
        return 'tci_line_to_res_row(): incomplete line (missing end of line)'

    room_cat, comment, half_board = tci_determine_room_cat_and_extra_comment(curr_cols)
    is_adult = curr_cols[TCI_PAX_TYPE] in ('M', 'F')
    comment += curr_cols[TCI_COMMENT]       # start with apartment feature comments then client comment
    meal_plan = curr_cols[TCI_MEAL_PLAN]

    row = {}
    if last_line:   # check if current line is an extension of the booking from the last line (only not in first line)
        last_cols = last_line.split(';')
        if last_cols[TCI_BOOK_IDX] == curr_cols[TCI_BOOK_IDX] \
                and int(last_cols[TCI_PAX_IDX]) + 1 == int(curr_cols[TCI_PAX_IDX]):
            # additional pax
            row = rows[-1]
        elif last_cols[TCI_BOOK_EXT] == 'H' and curr_cols[TCI_BOOK_EXT] == 'E' and \
                last_cols[TCI_BOOK_REF] == curr_cols[TCI_LINK_REF] and \
                last_cols[TCI_LINK_REF] == curr_cols[TCI_BOOK_REF]:
            # additional pax (maybe with different LengthOfStay)
            row = rows[-1]
            comment += ' ' + curr_cols[TCI_LINK_REF] + '-' + curr_cols[TCI_BOOK_EXT]
            if datetime.timedelta(int(curr_cols[TCI_STAY_DAYS])) != row['DEP_DATE'] - row['ARR_DATE']:
                comment += '(LengthOfStay differs!)'
        elif last_cols[TCI_BOOK_IDX] > '1' or last_cols[TCI_BOOK_REF] == curr_cols[TCI_BOOK_REF]:
            # separate room - mostly with same TC booking reference
            rows[-1]['SIHOT_NOTE'] += '+' + curr_cols[TCI_BOOK_REF] + '-' + curr_cols[TCI_BOOK_IDX]
            rows[-1]['SIHOT_TEC_NOTE'] += '|CR|+' + curr_cols[TCI_BOOK_REF] + '-' + curr_cols[TCI_BOOK_IDX]
            comment += ' ' + curr_cols[TCI_BOOK_REF] + '-' + curr_cols[TCI_BOOK_IDX]

    if row:     # add next pax - extending previous row
        row['SIHOT_NOTE'] += comment
        row['SIHOT_TEC_NOTE'] += comment
        row['RU_ADULTS' if is_adult else 'RU_CHILDREN'] += 1
    else:
        rows.append(row)
        row['SIHOT_GDSNO'] = 'TC' + curr_cols[TCI_BOOK_PREFIX] + curr_cols[TCI_BOOK_REF]    # GDSNO
        row['SH_RES_TYPE'] = 'S' if curr_cols[TCI_BOOK_TYPE] == 'CNL' else '1'
        row['SIHOT_HOTEL_C'] = '1' if curr_cols[TCI_RESORT] == 'BEVE' else '4'  # 1=BHC, 4=PBC
        row['SH_OBJID'] = row['OC_SIHOT_OBJID'] = conf_data.get_ro_agency_objid('TK')
        row['SH_MC'] = row['OC_CODE'] = conf_data.get_ro_agency_matchcode('TK')
        row['RH_EXT_BOOK_REF'] = curr_cols[TCI_BOOK_PREFIX] + curr_cols[TCI_BOOK_REF]
        row['RH_EXT_BOOK_DATE'] = curr_cols[TCI_BOOK_DATE]

        row['RUL_SIHOT_CAT'] = row['SH_PRICE_CAT'] = room_cat
        if curr_cols[TCI_CLIENT_CAT]:
            comment += ' ClientCat=' + curr_cols[TCI_CLIENT_CAT]
        if meal_plan == 'SPECIAL OFERTA':
            comment += ' ' + meal_plan
        row['SIHOT_NOTE'] = comment.strip()
        row['SIHOT_TEC_NOTE'] = comment.strip()
        if half_board or 'HALF' in meal_plan.upper():
            row['RUL_SIHOT_PACK'] = 'HB'
        elif meal_plan and meal_plan != 'SPECIAL OFERTA':
            row['RUL_SIHOT_PACK'] = 'BB'
        else:
            row['RUL_SIHOT_PACK'] = 'RO'

        row['SIHOT_MKT_SEG'] = 'TC'
        row['RO_RES_GROUP'] = 'Rental SP'
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

    return ''


''' RCI Bookings Import  #####################################################
    biggest differences to TCI import:
     o  client and matchcode explicitly created as guest record in Sihot
     o  room assigned to reservation
     o  possibly update of reservation inventory type (AOWN_ROREF) in Acumen needed
'''
RCI_RESORT = 1      # BHC=1442, BHH=2398, HMC=2429, PBC=0803 (see also RS_RCI_CODE)
RCI_BOOK_REF = 2
RCI_ARR_DATE = 3
RCI_BOOK_TYPE = 4
RCI_IS_GUEST = 6
RCI_SURNAME = 8
RCI_FORENAME = 9
RCI_GUEST_SURNAME = 12
RCI_GUEST_FORENAME = 13
RCI_APT_NO = 24
RCI_ROOM_SIZE = 25
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
        return ''   # skip/hide request and incomplete bookings (without any apartment value)
    elif 'RCI POINTS' in curr_cols[RCI_SURNAME] + curr_cols[RCI_FORENAME] \
            + curr_cols[RCI_GUEST_SURNAME] + curr_cols[RCI_GUEST_FORENAME]:
        return ''   # skip/ignore RCI Points bookings

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
        return 'rcip_line_to_res_row(): incomplete line (missing {} columns)'.format(RCIP_COL_COUNT - len(curr_cols))
    elif curr_cols[RCIP_RESORT] not in ('1442', '2398', '2429', '0803'):
        return 'rcip_line_to_res_row(): invalid resort id {}'.format(curr_cols[RCIP_RESORT])

    return ''


tci_files = []
rci_files = []
res_rows = []
error_log = ''

if cae.get_option('tciPath'):
    uprint('####  Load Thomas Cook...  ####')
    tci_files = glob.glob(cae.get_option('tciPath'))
    ''' sort tci_files 1.ASCENDING by actualization date and 2.DESCENDING by file type (R5 first, then R3 and finally R1)
        .. for to process cancellation/re-bookings in the correct order.
        .. (date and type taken from file name R?_yyyy-mm-dd hh.mm.ss.txt - ?=1-booking 3-cancellation 5-re-booking)
        .. hour/minute/... info cannot be used because it happened (see 17-Jan-14 6:40=R1 and 6:42=R5)
        .. that the R3/5 tci_files had a higher minute value than the associated R1 file with the correction booking.
    '''
    tci_files.sort(key=lambda f: os.path.basename(f)[1], reverse=True)
    tci_files.sort(key=lambda f: os.path.basename(f)[3:13])
    print(tci_files)
    for fn in tci_files:
        with open(fn, 'r') as fp:
            lines = fp.readlines()

        last_ln = ''
        for idx, ln in enumerate(lines):
            if cae.get_option('debugLevel'):
                print(repr(ln))
            try:
                error_msg = tci_line_to_res_row(ln, last_ln, res_rows)
            except Exception as ex:
                error_msg = 'TCI Line parse exception: {}'.format(ex)
            if error_msg:
                error_log += 'Error in line {} of TCI file {}: {}\n'.format(idx + 1, fn, error_msg)
                if cae.get_option('breakOnError'):
                    break
            last_ln = ln
        if error_msg and cae.get_option('breakOnError'):
            break


if cae.get_option('rciPath') and (not error_log or not cae.get_option('breakOnError')):
    uprint('####  Load RCI...........  ####')
    rci_files = glob.glob(cae.get_option('rciPath'))
    print(rci_files)
    for fn in rci_files:
        with open(fn, 'r') as fp:
            lines = fp.readlines()

        points_import = False
        for idx, ln in enumerate(lines):
            if idx == 0:    # first line is header
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
                if cae.get_option('debugLevel'):
                    print(repr(ln))
                try:
                    if points_import:
                        error_msg = rcip_line_to_res_row(ln, res_rows)
                    else:
                        error_msg = rci_line_to_res_row(ln, res_rows)
                except Exception as ex:
                    error_msg = 'line parse exception: {}'.format(ex)
            if error_msg:
                error_log += 'Error in line {} of RCI{} file {}: {}\n'.format(idx + 1, 'P' if points_import else '',
                                                                              fn, error_msg)
                if cae.get_option('breakOnError'):
                    break
        if error_msg and cae.get_option('breakOnError'):
            break


if not error_log or not cae.get_option('breakOnError'):
    uprint('####  Send reservations..  ####')

    acumen_req = ResToSihot(cae, use_kernel_interface=cae.get_option('useKernelForRes'),
                            map_res=cae.get_option('mapRes'),
                            use_kernel_for_new_clients=cae.get_option('useKernelForClient'),
                            map_client=cae.get_option('mapClient'),
                            connect_to_acu=False)
    progress = Progress(cae.get_option('debugLevel'), start_counter=len(res_rows),
                        start_msg='Prepare sending of {run_counter} reservation request changes to Sihot',
                        nothing_to_do_msg='SihotResImport: no rows loaded from import folder(s)')
    for cols in res_rows:
        error_msg = acumen_req.send_row_to_sihot(cols)
        progress.next(processed_id=str(cols['RH_EXT_BOOK_REF']), error_msg=error_msg)
        if error_msg:
            if error_msg.startswith(ERR_MESSAGE_PREFIX_CONTINUE):
                error_msg = ''
                continue
            error_log += 'Error in sending reservation {} to Sihot {}\n'.format(cols, error_msg)
            if cae.get_option('breakOnError'):
                break

    warnings = acumen_req.get_warnings()
    if notification and warnings:
        mail_to = cae.get_option('warningsMailToAddr')
        notification.send_notification(warnings, subject='SihotResImport warnings notification', mail_to=mail_to)

    progress.finished(error_msg=error_msg)


if not error_log:
    uprint('####  Move Import Files..  ####')
    dt = datetime.datetime.strftime('%y%m%d_%H%M%S_')
    for sfn in tci_files + rci_files:
        # without the str() around dirname PyCharm is showing the strange warning:
        # .. Expected type 'list' (matched generic type 'List[TypeVar('T')]'), got 'str' instead
        dfn = os.path.join(os.path.dirname(sfn), 'processed', dt + os.path.basename(sfn))
        os.rename(sfn, dfn)


if error_log:
    if notification:
        notification.send_notification(error_log, subject="SihotResImport error notification")
    print('Error Log:', error_log)

# release dup exec lock
set_opt_err = cae.set_option('lastRt', str(-1))

cae.shutdown(13 if set_opt_err else (12 if error_msg else 0))
