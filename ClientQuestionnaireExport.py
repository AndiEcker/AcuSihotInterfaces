"""
    ClientQuestionnaireExport is a tool to export all check-outs within a given date range into a CSV file to
    be sent to a service company to do the client questionnaires. This tool is replacing the currently
    used Acumen/Oracle procedure SALES.TRIPADVISOR (runs every Tuesday around 11 by an Oracle job, creating the file
    INTUITION.csv within the folder <oracle-server>/home/oracle/ext_tables).
    
    FYI: There is a similar export available within the Sihot.PMS EXE application via the menu entry
    "Export / Export stays for Marketing" (with the checkbox "Email filter" checked) which is exporting a
    CSV file into the folder U:/transfer/staysformarketing/.
    
    0.1     first beta.
    0.2     roughly refactored to use ae.sys_data - NOT TESTED.
"""
import os
import datetime
import re
from traceback import print_exc

from ae.console import ConsoleApp
from ae.inspector import try_eval
from ae.sys_data_sh import ResSearch, SH_DATE_FORMAT
from ae.sys_data_sh import add_sh_options, print_sh_options


__version__ = '0.2'

LIST_MARKER_PREFIX = '*'
LINE_SEPARATOR = '\n'

startup_date = datetime.date.today()
mail_re = re.compile('[a-zA-Z0-9._%-]+@[a-zA-Z0-9._%-]+\.[a-zA-Z]{2,4}$')

cae = ConsoleApp("Export check-outs from Sihot to CSV file")
cae.add_opt('dateFrom', "Date of first check-out to be exported", startup_date - datetime.timedelta(days=7), 'F')
cae.add_opt('dateTill', "Date of last check-out to be exported", startup_date, 'T')

# old Acumen script used the following file path: //<oracle-server>/home/oracle/ext_tables/INTUITION.csv
cae.add_opt('exportFile', "Full path and name of the CSV file (appending new checkouts if already exits)", '', 'x')

add_sh_options(cae)


export_fnam = cae.get_opt('exportFile')
cae.po("Export file:", export_fnam)
date_from = cae.get_opt('dateFrom')
date_till = cae.get_opt('dateTill')
cae.po("Date range including checkouts from", date_from.strftime(SH_DATE_FORMAT),
       "and till/before", date_till.strftime(SH_DATE_FORMAT))
print_sh_options(cae)

column_separator = cae.get_var('columnSeparator', default_value=',')
cae.po("Column separator character:", column_separator)
max_len_of_stay = cae.get_var('maxLengthOfStay', default_value=42)
cae.po("Maximum length of stay:", max_len_of_stay,
       " - includes arrivals back to", date_from - datetime.timedelta(days=max_len_of_stay))
search_flags = cae.get_var('ResSearchFlags', default_value='ALL-HOTELS')
cae.po("Search flags:", search_flags)
search_scope = cae.get_var('ResSearchScope', default_value='NOORDERER;NORATES;NOPERSTYPES')
cae.po("Search scope:", search_scope)
file_caption = cae.get_var('fileCaption',
                           default_value='UNIQUEID' + column_separator
                                         + 'CHECKIN' + column_separator + 'CHECKOUT' + column_separator
                                         + 'FIRSTNAME' + column_separator + 'LASTNAME' + column_separator
                                         + 'EMAIL' + column_separator + 'CITY' + column_separator
                                         + 'COUNTRY' + column_separator + 'RESORT' + column_separator
                                         + 'LOCATIONID' + column_separator
                                         + 'STAYMONTH' + column_separator + 'STAYYEAR' + column_separator
                                         + 'LANGUAGE')
cae.po("File caption:", file_caption)
file_columns = cae.get_var('fileColumns',
                           default_value=['<unique_id>', 'ARR', 'DEP',
                                          LIST_MARKER_PREFIX + 'NAME2', LIST_MARKER_PREFIX + 'NAME',
                                          LIST_MARKER_PREFIX + 'EMAIL',
                                          LIST_MARKER_PREFIX + 'CITY',
                                          LIST_MARKER_PREFIX + 'COUNTRY',
                                          '<hotel_id_to_name(hotel_id)>',
                                          '<hotel_id_to_location_id(hotel_id)>',  # '<"xx-0000-xx">',
                                          '<check_out.month>', '<check_out.year>',
                                          LIST_MARKER_PREFIX + 'LANG',
                                          ])
cae.po("File columns:", file_columns)

if not export_fnam:
    cae.po("Invalid or empty export file name - please specify with the --exportFile option.")
    cae.shutdown(15)
elif date_from >= date_till:
    cae.po("Specified date range is invalid - dateFrom({}) has to be before dateTill({})."
           .format(date_from, date_till))
    cae.shutdown(18)


def get_hotel_and_res_id(res_rec):  # see also sys_data_sh.py/hotel_and_res_id()
    h_id = res_rec['RES-HOTEL'].val()
    r_num = res_rec['RES-NR'].val()
    s_num = res_rec['SUB-NR'].val()
    if not h_id or not hotel_id_to_name(h_id) or not hotel_id_to_location_id(h_id) or not r_num:
        cae.dpo("  ##  Skipping reservation with invalid hotel-id/RES-NR/SUB-NR", h_id, r_num, s_num)
        return None, None
    return h_id, r_num + ('/' + s_num if s_num else '') + '@' + h_id


def hotel_id_to_name(h_id):
    return cae.get_var(h_id, 'HotelNames')


def hotel_id_to_location_id(h_id):
    return cae.get_var(h_id, 'HotelLocationIds')


# collect all the emails found in this export run (to skip duplicates)
found_emails = list()


def email_is_valid(email):
    if email and email.lower()[-6:] != 'spv.es' and email.lower()[-6:] != 'svp.es' \
            and email.lower()[-15:] != 'silverpoint.com' and email.lower()[:16] != 'clienthasnoemail' \
            and email.lower()[-7:] != '@xx.com' and email.lower() != 'no@email.com' \
            and mail_re.match(email):
        if email not in found_emails:
            found_emails.append(email)
            return True
    return False


try:
    res_search = ResSearch(cae)
    # the from/to date range filter of WEB ResSearch is filtering the arrival date only (not date range/departure)
    first_checkin = date_from - datetime.timedelta(days=max_len_of_stay)
    last_checkout = date_till - datetime.timedelta(days=1)
    # adding flag ;WITH-PERSONS results in getting the whole reservation duplicated for each PAX in rooming list
    # adding scope NOORDERER prevents to include/use LANG/COUNTRY/NAME/EMAIL of orderer
    recs = res_search.search_res(from_date=first_checkin, to_date=last_checkout, flags=search_flags, scope=search_scope)
    if recs and isinstance(recs, str):
        cae.po(" ***  Sihot.PMS reservation search error:", recs)
        cae.shutdown(21)
    elif recs and isinstance(recs, list):
        exp_file_exists = os.path.exists(export_fnam)
        with open(export_fnam, 'a' if exp_file_exists else 'w') as f:
            if not exp_file_exists:
                f.write(file_caption)
            unique_ids = list()
            for rec in recs:
                hotel_id, res_id = get_hotel_and_res_id(rec)
                if not hotel_id or not res_id:
                    # skip error already logged within hotel_and_res_id()
                    continue
                check_in = rec['ResArrival'].val()
                check_out = rec['ResDeparture'].val()
                if not check_in or not check_out:
                    cae.dpo(" ###  Skipping incomplete check-in/-out/res-id=", check_in, check_out, res_id)
                    continue
                if not (date_from <= check_out < date_till):
                    cae.dpo("  ##  Skipping check-out", check_out,
                            "not in date range from ", date_from, 'till', date_till, 'res-id=', res_id)
                    continue
                res_type = rec['ResStatus']
                if res_type in ('S', 'N'):
                    cae.dpo("  ##  Skipping because of reservation type", res_type, 'res-id=', res_id)
                    continue
                for arr_index in range(len(rec['ResPersons'])):
                    unique_id = res_id + ('#' + str(arr_index) if arr_index >= 0 else '')
                    if unique_id in unique_ids:
                        cae.po("  **  Detected duplicate guest/client with unique-id=", unique_id)
                    unique_ids.append(unique_id)
                    f.write(LINE_SEPARATOR)
                    first_col = True
                    for c_nam in file_columns:
                        if c_nam.startswith('<') and c_nam.endswith('>'):
                            c_nam = c_nam[1:-1]
                            try:
                                c_val = try_eval(c_nam, glo_vars=globals(), loc_vars=locals())
                            except Exception as ex:
                                c_val = ex
                                cae.dpo(" ###  Invalid column expression", c_nam, "; exception:", str(ex))
                        else:
                            c_val = rec.val('ResPersons', arr_index, c_nam)
                        if first_col:
                            first_col = False
                        else:
                            f.write(column_separator)
                        c_val = str(c_val)
                        if column_separator in c_val:
                            c_val = '"' + c_val + '"'
                        f.write(c_val)
            f.write(LINE_SEPARATOR)
    else:
        cae.po(" ***  Unspecified Sihot.PMS reservation search error")
        cae.shutdown(24)
except Exception as ex:
    cae.po(" ***  Exception:", str(ex))
    print_exc()
    cae.shutdown(27)

if date_till == startup_date:
    cae.set_var('dateFrom', date_till)
cae.shutdown()
