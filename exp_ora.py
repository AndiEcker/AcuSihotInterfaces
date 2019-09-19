from ae.core import DEF_ENCODE_ERRORS
from acif import ACU_DEF_USR, ACU_DEF_DSN
from ae.console_app import ConsoleApp
from ae_db.db import OraDB

__version__ = '0.1'

CHK_RUN = False

COL_SEP = "\t"
LINE_SEP = "\n"

EXCLUDED = (
    'LOBBY.APT_OCCUPIED', 'LOBBY.APTSOWNER_LOG_BACKUP', 'LOBBY.REQUESTED_UNIT_LOG',
    'SALES.EVENTLOG', 'SALES.EVENTLOG_BACKUP',
    'SALES.PROSPECT_ASSIGN_LOG_BACKUP', 'SALES.PRE_CLIENT_LOG_BACKUP', 'SALES.APTS_HK_LOG_BACKUP',
    )

CHK_TABLES = (  # EXCLUDED
    # 'SALES.EVENTLOG',
    # tables with year 0 is out of range
    'SALES.OWNER_PROFILE', 'SALES.DEAL_WEEKS', 'SALES.RCI_RESORTS',
)
BIG_TABLE_MIN = 369000


cae = ConsoleApp("Export data from Acumen/Oracle servers")
cae.add_opt('outPath', "path to store the exported table data", "c:/ora_bkup/py/")
cae.add_opt('acuUser', "Acumen/Oracle user account name", ACU_DEF_USR, 'u')
cae.add_opt('acuPassword', "Acumen/Oracle user account password", '', 'p')
cae.add_opt('acuDSN', "Acumen/Oracle data source name", ACU_DEF_DSN, 'd')

cae.po('Export path:', cae.get_opt('outPath'))
cae.po('Acumen Usr/DSN:', cae.get_opt('acuUser'), cae.get_opt('acuDSN'))

ora_db = OraDB(dict(User=cae.get_opt('acuUser'),
                    Password=cae.get_opt('acuPassword'),
                    DSN=cae.get_opt('acuDSN')),
               app_name=cae.app_name, debug_level=cae.get_opt('debugLevel'))
err_msg = ora_db.connect()
if err_msg:
    cae.po(err_msg)
    cae.shutdown(1)

if CHK_RUN:
    cae.po("***  CHECK RUN ******************")
    owner_tables = CHK_TABLES
else:
    err_msg = ora_db.select('dba_tables', ["owner || '.' || table_name"],
                            where_group_order="owner in ('LOBBY', 'MFEE', 'SALES') order by 1")
    if err_msg:
        cae.po(err_msg)
        cae.shutdown(2)
    owner_tables = ora_db.fetch_all()
cae.po(len(owner_tables), "TABLES:", owner_tables)

tot_rows = 0
max_rows = 0
big_tables = list()
out_path = cae.get_argument('outPath')

for table_row in owner_tables:
    table_name = table_row[0]
    if table_name in EXCLUDED:
        cae.po("SKIPPING TABLE", table_name)
        continue

    err_msg = ora_db.select(table_name, ['*'])
    if err_msg:
        cae.po(err_msg)
        if not CHK_RUN:
            cae.shutdown(3)

    col_names = ora_db.selected_column_names()
    rows = ora_db.fetch_all()

    num_rows = len(rows)
    cae.po("===  TABLE", table_name, num_rows, "ROWS", len(col_names), "COLS: ", col_names)
    tot_rows += num_rows
    if num_rows > max_rows:
        max_rows = num_rows
    if num_rows > BIG_TABLE_MIN:
        big_tables.append(table_name + "=" + str(num_rows))

    if CHK_RUN:
        continue

    with open(out_path + table_name + ".csv", "w", encoding='utf-8', errors=DEF_ENCODE_ERRORS) as fo:
        fo.write(COL_SEP.join(col_names) + LINE_SEP)

        cae.po(len(rows), "ROWS")

        for row in rows:
            fo.write(COL_SEP.join([repr(col) for col in row]) + LINE_SEP)
            tot_rows += 1

cae.po("Number of rows*tables", tot_rows)
cae.po("Max rows", max_rows, " in ", big_tables)

ora_db.close()

cae.shutdown()
