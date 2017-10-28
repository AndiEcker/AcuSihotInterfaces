import os
import datetime

import cx_Oracle
from copy import deepcopy

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
        self.last_err_msg = ""

    def connect(self):
        self.last_err_msg = ''
        try:
            # old style: self.conn = cx_Oracle.connect(self.usr + '/"' + self.pwd + '"@' + self.dsn)
            self.conn = cx_Oracle.connect(user=self.usr, password=self.pwd, dsn=self.dsn)
            # self.conn.outputtypehandler = output_type_handler
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("OraDB: connected to Oracle database {} via client version {} with n-/encoding {}/{}"
                       .format(self.dsn, cx_Oracle.clientversion(), self.conn.nencoding, self.conn.encoding))
        except Exception as ex:
            self.last_err_msg = "oraDB-connect " + self.usr + "/" + self.pwd + "@" + self.dsn + " error: " + str(ex)
        else:
            try:
                self.curs = self.conn.cursor()
                if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    uprint("OraDB: Oracle database cursor created.")
            except Exception as ex:
                self.last_err_msg = "oraDB-connect cursors " + self.usr + "@" + self.dsn + " error: " + str(ex)
        return self.last_err_msg

    @staticmethod
    def _prepare_in_clause(where_group_order, bind_vars, additional_col_values=None):
        if not bind_vars:
            bv = deepcopy(additional_col_values or dict())
        else:
            new_dict = deepcopy(additional_col_values or dict())
            for key, val in bind_vars.items():
                if isinstance(val, list):       # expand IN clause bind list variable to separate bind variables
                    var_list = [key + '_' + str(_) for _ in range(len(val))]
                    where_group_order = where_group_order.replace(':' + key, ':' + ',:'.join(var_list))
                    for var_val in zip(var_list, val):
                        new_dict[var_val[0]] = var_val[1]
                else:
                    new_dict[key] = val
            bv = new_dict
        return where_group_order, bv

    def select(self, from_join, cols=None, where_group_order='', bind_vars=None, hints=''):
        self.last_err_msg = ""
        if not cols:
            cols = list('*')
        if not where_group_order:
            where_group_order = '1=1'
        where_group_order, bind_vars = self._prepare_in_clause(where_group_order, bind_vars)
        sq = "select {} {} from {} where {}".format(hints, ','.join(cols), from_join, where_group_order)
        try:
            self.curs.execute(sq, **bind_vars)
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("oraDB-{}. BindVars={}".format(sq, bind_vars))
                uprint("oraDB.select() cursor.description:", self.curs.description)
        except Exception as ex:
            self.last_err_msg = "oraDB select-execute error: " + str(ex) + (" sql=" + sq if sq else "")
        return self.last_err_msg

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
        self.last_err_msg = ""
        try:
            rows = self.curs.fetchall()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("oraDB fetch_all(), 1st of", len(rows), "rows:", rows[:1])
        except Exception as ex:
            self.last_err_msg = "oraDB fetch_all() exception: " + str(ex)
            uprint(self.last_err_msg)
            rows = None
        return rows or list()

    def fetch_value(self, col_idx=0):
        self.last_err_msg = ""
        try:
            val = self.curs.fetchone()[col_idx]
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("oraDB fetch_value() value: ", val)
        except Exception as ex:
            self.last_err_msg = "oraDB fetch_value() exception: " + str(ex)
            uprint(self.last_err_msg)
            val = None
        return val

    def insert(self, table_name, col_values, commit=False):
        self.last_err_msg = ""
        sq = "insert into " + table_name + " (" + ", ".join(col_values.keys()) \
             + ") values (:" + ", :".join(col_values.keys()) + ")"
        try:
            self.curs.execute(sq, **col_values)
            if commit:
                self.conn.commit()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("oraDB.insert() query:", sq)
        except Exception as ex:
            self.last_err_msg = "oraDB insert({})-execute error: {}".format(sq, ex)
        return self.last_err_msg

    def update(self, table_name, col_values, where='', commit=False, bind_vars=None):
        self.last_err_msg = ""
        if not where:
            where = "1=1"
        where, bind_vars = self._prepare_in_clause(where, bind_vars, additional_col_values=col_values)
        sq = "update " + table_name + " set " + ", ".join([c + " = :" + c for c in col_values.keys()]) \
             + " where " + where
        try:
            self.curs.execute(sq, **bind_vars)
            if commit:
                self.conn.commit()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("oraDB.update() query:", sq)
        except Exception as ex:
            self.last_err_msg = "oraDB update({})-execute error: {}".format(sq, ex)
        return self.last_err_msg

    def commit(self):
        self.last_err_msg = ""
        try:
            self.conn.commit()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("oraDB.commit()")
        except Exception as ex:
            self.last_err_msg = "oraDB commit error: " + str(ex)
        return self.last_err_msg

    def rollback(self):
        self.last_err_msg = ""
        try:
            self.conn.rollback()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("oraDB.rollback()")
        except Exception as ex:
            self.last_err_msg = "oraDB rollback error: " + str(ex)
        return self.last_err_msg

    def prepare_ref_param(self, value=None):
        if isinstance(value, datetime.datetime):    # also True if value is datetime.date because inherits from datetime
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
        self.last_err_msg = ""
        try:
            ret = self.curs.callproc(proc_name, proc_args)
            if ret_dict:
                ret_dict['return'] = ret
        except Exception as ex:
            self.last_err_msg = "oraDB call_proc error: " + str(ex)
        return self.last_err_msg

    def close(self, commit=True):
        self.last_err_msg = ""
        if self.conn:
            if commit:
                self.last_err_msg = self.commit()
            else:
                self.last_err_msg = self.rollback()
            try:
                if self.curs:
                    self.curs.close()
                    if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                        uprint("oraDB cursor closed")
                self.conn.close()
                if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    uprint("oraDB connection closed")
            except Exception as ex:
                self.last_err_msg += "oraDB close error: " + str(ex)
        return self.last_err_msg
