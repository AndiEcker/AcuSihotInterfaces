import os
import datetime

import cx_Oracle
from ae_console_app import uprint, DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_VERBOSE

DEF_USER = 'SIHOT_INTERFACE'
DEF_DSN = 'SP.TEST'

MAX_STRING_LENGTH = 2000

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
        if dsn.count(':') == 1 and dsn.count('/@') == 1:   # old style format == host:port/@SID
            host, rest = dsn.split(':')
            port, service_id = rest.split('/@')
            self.dsn = cx_Oracle.makedsn(host=host, port=port, sid=service_id)
        elif dsn.count(':') == 1 and dsn.count('/') == 1:  # old style format == host:port/service_name
            host, rest = dsn.split(':')
            port, service_name = rest.split('/')
            self.dsn = cx_Oracle.makedsn(host=host, port=port, service_name=service_name)
        else:
            self.dsn = dsn                                  # TNS name like SP.DEV
        self.debug_level = debug_level
        self.conn = None
        self.curs = None

    def connect(self):
        err_msg = ''
        try:
            # old style: self.conn = cx_Oracle.connect(self.usr + '/"' + self.pwd + '"@' + self.dsn)
            self.conn = cx_Oracle.connect(user=self.usr, password=self.pwd, dsn=self.dsn)
            # self.conn.outputtypehandler = output_type_handler
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("OraDB: connected to Oracle database {} via client version {} with n-/encoding {}/{}"
                       .format(self.dsn, cx_Oracle.clientversion(), self.conn.nencoding, self.conn.encoding))
        except Exception as ex:
            err_msg = "oraDB-connect " + self.usr + "/" + self.pwd + "@" + self.dsn + " error: " + str(ex)
        else:
            try:
                self.curs = self.conn.cursor()
            except Exception as ex:
                err_msg = "oraDB-connect cursors " + self.usr + "/" + self.pwd + "@" + self.dsn + " error: " + str(ex)
        if self.debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint(err_msg or "OraDB: Oracle database cursor created.")
        return err_msg

    def select(self, from_join, cols=None, where_group_order='', bind_vars=None):
        if not cols:
            cols = list('*')
        if not where_group_order:
            where_group_order = '1=1'
        if not bind_vars:
            bind_vars = dict()
        else:
            new_dict = dict()
            for key, val in bind_vars.items():
                if isinstance(val, list):       # expand IN clause bind list variable to separate bind variables
                    var_list = [key + '_' + str(_) for _ in range(len(val))]
                    where_group_order = where_group_order.replace(':' + key, ':' + ',:'.join(var_list))
                    for var_val in zip(var_list, val):
                        new_dict[var_val[0]] = var_val[1]
                else:
                    new_dict[key] = val
            bind_vars = new_dict
        sq = "select {} from {} where {}".format(','.join(cols), from_join, where_group_order)
        if self.debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint('oraDB-' + sq)
        try:
            self.curs.execute(sq, **bind_vars)
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("oraDB.select() cursor.description:", self.curs.description)
        except Exception as ex:
            return "oraDB select-execute error: " + str(ex) + (" sql=" + sq if sq else "")
        return ''

    def cursor_description(self):
        return self.curs.description if self.curs else None

    def selected_column_names(self):
        curs_desc = self.cursor_description()
        col_names = list()
        if curs_desc:
            for col_desc in curs_desc:
                col_names.append(col_desc[0])
        return col_names

    def fetch_all(self):
        try:
            rows = self.curs.fetchall()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("oraDB fetch_all(), 1st of", len(rows), "rows:", rows[:1])
        except Exception as ex:
            uprint("oraDB fetch_all() exception: " + str(ex))
            rows = None
        return rows or list()

    def fetch_value(self, col_idx=0):
        try:
            val = self.curs.fetchone()[col_idx]
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("oraDB fetch_value() value: ", val)
        except Exception as ex:
            uprint("oraDB fetch_value() exception: " + str(ex))
            val = None
        return val

    def insert(self, table_name, col_values, commit=False):
        sq = "insert into " + table_name + " (" + ", ".join(col_values.keys()) \
             + ") values (:" + ", :".join(col_values.keys()) + ")"
        if self.debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint("oraDB.insert() query:", sq)
        try:
            self.curs.execute(sq, **col_values)
            if commit:
                self.conn.commit()
        except Exception as ex:
            return "oraDB insert-execute error: " + str(ex)
        return ''

    def update(self, table_name, col_values, where='', commit=False):
        if not where:
            where = "1=1"
        sq = "update " + table_name + " set " + ", ".join([c + " = :" + c for c in col_values.keys()]) \
             + " where " + where
        if self.debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint("oraDB.update() query:", sq)
        try:
            self.curs.execute(sq, **col_values)
            if commit:
                self.conn.commit()
        except Exception as ex:
            return "oraDB update-execute error: " + str(ex)
        return ''

    def commit(self):
        try:
            self.conn.commit()
        except Exception as ex:
            return "oraDB commit error: " + str(ex)
        return ''

    def rollback(self):
        try:
            self.conn.rollback()
        except Exception as ex:
            return "oraDB rollback error: " + str(ex)
        return ''

    def prepare_ref_param(self, value=None):
        if isinstance(value, datetime.datetime):
            ora_type = cx_Oracle.DATETIME
        elif isinstance(value, int) or isinstance(value, float):
            ora_type = cx_Oracle.NUMBER
        else:
            ora_type = cx_Oracle.STRING
            value = str(value)[:MAX_STRING_LENGTH - 1]
        ref_var = self.curs.var(ora_type)
        if value is not None:
            self.set_value(ref_var, value)
        return ref_var

    @staticmethod
    def get_value(var):
        return var.getvalue()

    @staticmethod
    def set_value(var, value):
        var.setvalue(0, value)

    def get_row_count(self):
        return self.curs.rowcount

    def call_proc(self, proc_name, proc_args, ret_dict=None):
        try:
            ret = self.curs.callproc(proc_name, proc_args)
            if ret_dict:
                ret_dict['return'] = ret
        except Exception as ex:
            return "oraDB call_proc error: " + str(ex)
        return ''

    def close(self, commit=True):
        if commit:
            err_msg = self.commit()
        else:
            err_msg = self.rollback()
        try:
            if self.curs:
                if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    uprint("oraDB closing cursor")
                self.curs.close()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("oraDB closing connection")
            self.conn.close()
        except Exception as ex:
            err_msg += "oraDB close error: " + str(ex)
        return err_msg
