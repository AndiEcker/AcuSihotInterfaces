import os
import cx_Oracle
from console_app import uprint, DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_VERBOSE

DEF_USER = 'SIHOT_INTERFACE'
DEF_DSN = 'SP.TEST'


# used for to fix the following unicode encoding error:
# .. 'charmap' codec can't decode byte 0x90 in position 2: character maps to <undefined>
# ... BUT it was not working (still got same error)
'''
def output_type_handler(cursor, name, default_type, size, precision, scale):
    if default_type in (cx_Oracle.STRING, cx_Oracle.FIXED_CHAR):
        return cursor.var(cx_Oracle.NCHAR, size, cursor.arraysize)
'''
# workaround with the next statement
os.environ["NLS_LANG"] = ".AL32UTF8"


class OraDB:

    def __init__(self, usr=DEF_USER, pwd='', dsn=DEF_DSN, debug_level=DEBUG_LEVEL_DISABLED):
        self.usr = usr
        self.pwd = pwd
        self.dsn = dsn
        self.debug_level = debug_level
        self.conn = None
        self.curs = None

    def connect(self):
        try:
            self.conn = cx_Oracle.connect(self.usr + '/"' + self.pwd + '"@' + self.dsn)
            # self.conn.outputtypehandler = output_type_handler
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint('OraDB: connected to Oracle database {} via client version {} with n-/encoding {}/{}'
                       .format(self.dsn, cx_Oracle.clientversion(), self.conn.nencoding, self.conn.encoding))
        except Exception as ex:
            return 'oraDB-connect ' + self.usr + '/' + self.pwd + '@' + self.dsn + ' error: ' + str(ex)
        else:
            self.curs = self.conn.cursor()
        if self.debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint('OraDB: Oracle database cursor created')
        return ''

    def select(self, table_names, cols=None, where_group_order='', bind_vars=None):
        if not cols:
            cols = list('*')
        if not where_group_order:
            where_group_order = '1=1'
        if not bind_vars:
            bind_vars = dict()
        sq = "select {} from {} where {}".format(','.join(cols), table_names, where_group_order)
        if self.debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint('oraDB-' + sq)
        try:
            self.curs.execute(sq, **bind_vars)
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint('oraDB.select() cursor.description:', self.curs.description)
        except Exception as ex:
            return 'oraDB select-execute error: ' + str(ex) + (' sql=' + sq if sq else '')
        return ''

    def fetch_all(self):
        try:
            rows = self.curs.fetchall()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint('oraDB fetch_all(), 1st of', len(rows), ' rows: ', rows[:1])
        except Exception as ex:
            uprint('oraDB fetch_all() exception: ' + str(ex))
            rows = None
        return rows if rows else []

    def fetch_value(self, col_idx=0):
        try:
            val = self.curs.fetchone()[col_idx]
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint('oraDB fetch_value() value: ', val)
        except Exception as ex:
            uprint('oraDB fetch_value() exception: ' + str(ex))
            val = None
        return val

    def insert(self, table_name, col_values, commit=False):
        sq = 'insert into ' + table_name + ' (' + ', '.join(col_values.keys()) \
             + ') values (:' + ', :'.join(col_values.keys()) + ')'
        if self.debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint('oraDB.insert() query: ', sq)
        try:
            self.curs.execute(sq, **col_values)
            if commit:
                self.conn.commit()
        except Exception as ex:
            return 'oraDB insert-execute error: ' + str(ex)
        return ''

    def update(self, table_name, col_values, where='', commit=False):
        if not where:
            where = '1=1'
        sq = 'update ' + table_name + ' set ' + ', '.join([c + ' = :' + c for c in col_values.keys()]) \
             + ' where ' + where
        if self.debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint('oraDB.update() query: ', sq)
        try:
            self.curs.execute(sq, **col_values)
            if commit:
                self.conn.commit()
        except Exception as ex:
            return 'oraDB update-execute error: ' + str(ex)
        return ''

    def commit(self):
        try:
            self.conn.commit()
        except Exception as ex:
            return 'oraDB commit error: ' + str(ex)
        return ''

    def rollback(self):
        try:
            self.conn.rollback()
        except Exception as ex:
            return 'oraDB rollback error: ' + str(ex)
        return ''

    def close(self, commit=True):
        if commit:
            err_msg = self.commit()
        else:
            err_msg = self.rollback()
        try:
            if self.curs:
                if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    uprint('oraDB closing cursor')
                self.curs.close()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint('oraDB closing connection')
            self.conn.close()
        except Exception as ex:
            err_msg += 'oraDB close error: ' + str(ex)
        return err_msg
