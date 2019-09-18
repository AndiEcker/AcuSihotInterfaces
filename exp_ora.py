from ae.core import DEF_ENCODE_ERRORS
from acif import ACU_DEF_USR, ACU_DEF_DSN
from ae.console_app import ConsoleApp
from ae_db.db import OraDB

__version__ = '0.1'

COL_SEP = "\t"
LINE_SEP = "\n"

EXCLUDED = (
    'SALES.EVENTLOG', 'LOBBY.REQUESTED_UNIT_LOG',
    )


cae = ConsoleApp("Export data from Acumen/Oracle servers")
cae.add_opt('acuUser', "Acumen/Oracle user account name", ACU_DEF_USR, 'u')
cae.add_opt('acuPassword', "Acumen/Oracle user account password", '', 'p')
cae.add_opt('acuDSN', "Acumen/Oracle data source name", ACU_DEF_DSN, 'd')

cae.po('Acumen Usr/DSN:', cae.get_opt('acuUser'), cae.get_opt('acuDSN'))

ora_db = OraDB(dict(User=cae.get_opt('acuUser'),
                    Password=cae.get_opt('acuPassword'),
                    DSN=cae.get_opt('acuDSN')),
               app_name=cae.app_name, debug_level=cae.get_opt('debugLevel'))
err_msg = ora_db.connect()
if err_msg:
    cae.po(err_msg)
    cae.shutdown(1)

err_msg = ora_db.select('dba_tables', ["owner", "table_name"],
                        where_group_order="owner in ('LOBBY', 'MFEE', 'SALES') order by 1")
if err_msg:
    cae.po(err_msg)
    cae.shutdown(2)

owner_tables = ora_db.fetch_all()
cae.po(len(owner_tables), "TABLES:", owner_tables)

cnt = 0
for owner, table in owner_tables:
    table_name = owner + "." + table
    if table_name in EXCLUDED:
        cae.po("SKIPPING TABLE", table_name)

    err_msg = ora_db.select(table_name, ['*'])
    if err_msg:
        cae.po(err_msg)
        cae.shutdown(3)

    col_names = ora_db.selected_column_names()
    cae.po("===  TABLE", table_name, len(col_names), "COLS: ", col_names)
    with open("c:/ora_bkup/py/" + table_name + ".csv", "w", encoding='utf-8', errors=DEF_ENCODE_ERRORS) as fo:
        fo.write(COL_SEP.join(col_names) + LINE_SEP)

        rows = ora_db.fetch_all()
        cae.po(len(rows), "ROWS")

        for row in rows:
            fo.write(COL_SEP.join([repr(col) for col in row]) + LINE_SEP)
            cnt += 1

cae.po("Number of rows*tables", cnt)

ora_db.close()

cae.shutdown()
