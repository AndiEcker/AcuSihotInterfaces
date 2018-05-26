import os
import datetime

from copy import deepcopy

import cx_Oracle
import psycopg2
# from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from ae_console_app import uprint, DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_VERBOSE


NAMED_BIND_VAR_PREFIX = ':'


def _locked_col_expr(col, locked_cols):
    return "COALESCE(" + col + ", " + NAMED_BIND_VAR_PREFIX + col + ")" if col in locked_cols \
        else NAMED_BIND_VAR_PREFIX + col


class GenericDB:
    def __init__(self, usr, pwd, dsn, debug_level=DEBUG_LEVEL_DISABLED):
        self.usr = usr
        self.pwd = pwd
        self.dsn = dsn
        self.debug_level = debug_level

        self.conn = None
        self.curs = None
        self.last_err_msg = ""

        self._param_style = 'named'

    def connect(self):
        raise NotImplementedError

    def _create_cursor(self):
        try:
            self.curs = self.conn.cursor()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("GenericDB: database cursor created.")
        except Exception as ex:
            self.last_err_msg = "GenericDB._create_cursor() error: " + str(ex)

    @staticmethod
    def _prepare_in_clause(sql, bind_vars, additional_col_values=None):
        new_bind_vars = deepcopy(additional_col_values or dict())
        if bind_vars:
            for key, val in bind_vars.items():
                if isinstance(val, list):       # expand IN clause bind list variable to separate bind variables
                    var_list = [key + '_' + str(_) for _ in range(len(val))]
                    in_vars = ','.join([NAMED_BIND_VAR_PREFIX + c for c in var_list])
                    sql = sql.replace(NAMED_BIND_VAR_PREFIX + key, in_vars)
                    for var_val in zip(var_list, val):
                        new_bind_vars[var_val[0]] = var_val[1]
                else:
                    new_bind_vars[key] = val
        return sql, new_bind_vars

    def _adapt_sql(self, sql, bind_vars):
        new_sql = sql
        if self._param_style == 'pyformat':
            for key in bind_vars.keys():
                new_sql = new_sql.replace(NAMED_BIND_VAR_PREFIX + key, '%(' + key + ')s')
        return new_sql

    def execute_sql(self, sql, commit=False, auto_commit=False, bind_vars=None):
        if self.conn or not self.connect():     # lazy connection
            if auto_commit:
                self.conn.autocommit = True     # or use: self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            action = sql.split()[0]
            if action == '--' or action == '/*':
                action = 'SCRIPT'
            elif action.upper() == 'CREATE':
                action += ' ' + sql.split()[1]

            self.last_err_msg = ""
            sql, bind_vars = self._prepare_in_clause(sql, bind_vars)
            sql = self._adapt_sql(sql, bind_vars)
            try:
                if bind_vars:
                    self.curs.execute(sql, bind_vars)
                else:
                    # if no bind vars then call without for to prevent error "'dict' object does not support indexing"
                    # .. in scripts with the % char (like e.g. dba_create_audit.sql)
                    self.curs.execute(sql)
                if commit:
                    self.conn.commit()
                if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    uprint("GenericDB.execute_sql({}, {}) {}".format(sql, bind_vars, action))
                    uprint(".. " + action + " cursor.rowcount/description:", self.curs.rowcount, self.curs.description)

            except Exception as ex:
                self.last_err_msg = "GenericDB.execute_sql({}, {}) {} error: {}".format(sql, bind_vars, action, ex)

        return self.last_err_msg

    def select(self, from_join, cols=None, where_group_order='', bind_vars=None, hints=''):
        if not cols:
            cols = list('*')
        if not where_group_order:
            where_group_order = '1=1'
        sql = "SELECT {} {} FROM {} WHERE {}".format(hints, ','.join(cols), from_join, where_group_order)
        return self.execute_sql(sql, bind_vars=bind_vars)

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
                uprint("GenericDB.fetch_all(), 1st of", len(rows), "rows:", rows[:1])
        except Exception as ex:
            self.last_err_msg = "GenericDB.fetch_all() exception: " + str(ex)
            uprint(self.last_err_msg)
            rows = None
        return rows or list()

    def fetch_value(self, col_idx=0):
        self.last_err_msg = ""
        try:
            val = self.curs.fetchone()[col_idx]
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("GenericDB.fetch_value()[{}] value: {}".format(col_idx, val))
        except Exception as ex:
            self.last_err_msg = "GenericDB.fetch_value()[{}] exception: {}".format(col_idx, ex)
            uprint(self.last_err_msg)
            val = None
        return val

    def insert(self, table_name, col_values, commit=False, returning_column=''):
        sql = "INSERT INTO " + table_name + " (" + ", ".join(col_values.keys()) \
              + ") VALUES (" + ", ".join([NAMED_BIND_VAR_PREFIX + c for c in col_values.keys()]) + ")"
        if returning_column:
            sql += " RETURNING " + returning_column
        return self.execute_sql(sql, commit=commit, bind_vars=col_values)

    def update(self, table_name, col_values, where='', commit=False, bind_vars=None, locked_cols=None):
        new_bind_vars = deepcopy(col_values)
        if bind_vars:
            new_bind_vars.update(bind_vars)
        if locked_cols is None:
            locked_cols = list()
        sql = "UPDATE " + table_name \
              + " SET " + ", ".join([c + " = " + _locked_col_expr(c, locked_cols) for c in col_values.keys()])
        if where:
            sql += " WHERE " + where
        return self.execute_sql(sql, commit=commit, bind_vars=new_bind_vars)

    def upsert(self, table_name, col_values, chk_values=None, returning_column='', commit=False, locked_cols=None):
        """
        INSERT or UPDATE in table_name the col_values, depending on if record already exists.
        :param table_name:          name of the database table.
        :param col_values:          dict of inserted/updated column values with the column name as key.
        :param chk_values:          dict of column names/values for to check if record already exists.
                                    If not passed then use first name/value of col_values (has then to be OrderedDict).
        :param returning_column:    name of column which value will be returned by next fetch_all/fetch_value() call.
        :param commit:              bool value to specify if commit should be done.
        :param locked_cols:         list of column names not be overwritten on update of column value is not empty
        :return:                    last error message or "" if no errors occurred.
        """
        if not chk_values:
            chk_values = dict([next(iter(col_values.items()))])     # use first dict item as pkey check value
        chk_expr = " AND ".join([k + " = " + NAMED_BIND_VAR_PREFIX + k for k in chk_values.keys()])

        self.select(table_name, ["count(*)"], chk_expr, chk_values)
        if not self.last_err_msg:
            count = self.fetch_value()
            if not self.last_err_msg:
                if count == 1:
                    bind_vars = deepcopy(chk_values).update(col_values)
                    self.update(table_name, col_values, chk_expr, commit=commit, bind_vars=bind_vars,
                                locked_cols=locked_cols)
                    if not self.last_err_msg and returning_column:
                        self.select(table_name, [returning_column], chk_expr, chk_values)
                elif count == 0:
                    self.insert(table_name, col_values, commit=commit, returning_column=returning_column)
                else:
                    self.last_err_msg = "GenericDB.upsert({}, {}, {}, {}) error: found {} duplicate primary key values"\
                        .format(table_name, col_values, chk_values, returning_column, count)
        return self.last_err_msg

    def commit(self, reset_last_err_msg=False):
        if reset_last_err_msg:
            self.last_err_msg = ""
        try:
            self.conn.commit()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("GenericDB.commit()")
        except Exception as ex:
            self.last_err_msg = "GenericDB commit error: " + str(ex)
        return self.last_err_msg

    def rollback(self, reset_last_err_msg=False):
        if reset_last_err_msg:
            self.last_err_msg = ""
        try:
            self.conn.rollback()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("GenericDB.rollback()")
        except Exception as ex:
            self.last_err_msg = "GenericDB rollback error: " + str(ex)
        return self.last_err_msg

    def get_row_count(self):
        return self.curs.rowcount

    def call_proc(self, proc_name, proc_args, ret_dict=None):
        self.last_err_msg = ""
        try:
            ret = self.curs.callproc(proc_name, proc_args)
            if ret_dict:
                ret_dict['return'] = ret
        except Exception as ex:
            self.last_err_msg = "GenericDB call_proc error: " + str(ex)
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
                        uprint("GenericDB cursor closed")
                self.conn.close()
                if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    uprint("GenericDB connection closed")
            except Exception as ex:
                self.last_err_msg += "GenericDB close error: " + str(ex)
        return self.last_err_msg


class OraDB(GenericDB):

    def __init__(self, usr=ACU_DEF_USR, pwd='', dsn=ACU_DEF_DSN, debug_level=DEBUG_LEVEL_DISABLED):
        super(OraDB, self).__init__(usr=usr, pwd=pwd, dsn=dsn, debug_level=debug_level)

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

        # used for to fix the following unicode encoding error:
        # .. 'charmap' codec can't decode byte 0x90 in position 2: character maps to <undefined>
        # ... BUT it was not working (still got same error)
        '''
        def output_type_handler(cursor, name, default_type, size, precision, scale):
            if default_type in (cx_Oracle.STRING, cx_Oracle.FIXED_CHAR):
                return cursor.var(cx_Oracle.NCHAR, size, cursor.arraysize)
        '''
        # workaround with the next statement for OraDB
        os.environ["NLS_LANG"] = ".AL32UTF8"

    def connect(self):
        self.last_err_msg = ''
        try:
            # old style: self.conn = cx_Oracle.connect(self.usr + '/"' + self.pwd + '"@' + self.dsn)
            self.conn = cx_Oracle.connect(user=self.usr, password=self.pwd, dsn=self.dsn)
            # self.conn.outputtypehandler = output_type_handler - see also comment in __init__()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("OraDB: connected to Oracle database {} via client version {}/{} with n-/encoding {}/{}"
                       .format(self.dsn, cx_Oracle.clientversion(), cx_Oracle.apilevel,
                               self.conn.nencoding, self.conn.encoding))
        except Exception as ex:
            self.last_err_msg = "OraDB-connect " + self.usr + "@" + self.dsn + " error: " + str(ex)
        else:
            self._create_cursor()
        return self.last_err_msg

    def prepare_ref_param(self, value=None):
        if isinstance(value, datetime.datetime):    # also True if value is datetime.date because inherits from datetime
            ora_type = cx_Oracle.DATETIME
        elif isinstance(value, int) or isinstance(value, float):
            ora_type = cx_Oracle.NUMBER
        else:
            ora_type = cx_Oracle.STRING
            value = str(value)
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


class PostgresDB(GenericDB):
    def __init__(self, usr, pwd, dsn, debug_level=DEBUG_LEVEL_DISABLED):
        """
        create instance of postgres database object
        :param usr:         user name
        :param pwd:         user password
        :param dsn:         database name and optionally host address (separated with a @ character)
        :param debug_level: debug level
        """
        super(PostgresDB, self).__init__(usr=usr, pwd=pwd, dsn=dsn, debug_level=debug_level)
        # for "named" PEP-0249 sql will be adapted to fit postgres driver "pyformat" sql bind-var/parameter syntax
        self._param_style = 'pyformat'

    def connect(self):
        self.last_err_msg = ''
        try:
            connection_params = dict(user=self.usr, password=self.pwd)
            if '@' in self.dsn:
                connection_params['dbname'], connection_params['host'] = self.dsn.split('@')
            else:
                connection_params['dbname'] = self.dsn
            self.conn = psycopg2.connect(**connection_params)
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("PostgresDB: connected to postgres database {} via api/server {}/{} with encoding {}"
                       .format(self.dsn, psycopg2.apilevel, self.conn.server_version, self.conn.encoding))
        except Exception as ex:
            self.last_err_msg = "PostgresDB-connect " + self.usr + "@" + self.dsn + " error: " + str(ex)
        else:
            self._create_cursor()
        return self.last_err_msg
