"""
    provide database connections - currently supported database are Postgres and Oracle.
"""
import os
import datetime

from copy import deepcopy

import cx_Oracle
import psycopg2
# from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from sys_data_ids import DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE
from ae.console_app import NamedLocks, uprint


NAMED_BIND_VAR_PREFIX = ':'
bind_var_prefix = "CV_"   # for to allow new value in SET clause and old value in WHERE clause for same column/-name
# .. we add this prefix to all bind_vars and chk_values (self._adapt_sql() would not work with suffix)


def _locked_col_expr(col, locked_cols):
    return "COALESCE(" + col + ", " + NAMED_BIND_VAR_PREFIX + col + ")" if col in locked_cols \
        else NAMED_BIND_VAR_PREFIX + col


def _normalize_col_values(col_values):
    for key, val in col_values.items():
        if isinstance(val, str) and not val:
            col_values[key] = None
    return col_values


class GenericDB:
    def __init__(self, credentials, features=None, app_name='ae.db-gen', debug_level=DEBUG_LEVEL_DISABLED):
        """
        create instance of generic database object (base class for real database like e.g. postgres or oracle).
        :param credentials: dict with account credentials (SYS_CRED_ITEMS), including User=user name, Password=user
                            password and DSN=database name and optionally host address (separated with a @ character).
        :param features:    optional list of features (currently not used for databases).
        :param app_name:    application name (shown in the server DB session).
        :param debug_level: debug level.
        """
        user = credentials.get('User')
        password = credentials.get('Password')
        dsn = credentials.get('DSN')
        assert user and password, "db.py/GenericDB has empty user name ({}) and/or password".format(user)
        self.usr = user
        self.pwd = password
        assert dsn and isinstance(dsn, str), "db.py/GenericDB() has invalid dsn argument {}".format(dsn)
        self.dsn = dsn
        self._features = features
        self._app_name = app_name
        self.debug_level = debug_level

        self.conn = None
        self.curs = None
        self.last_err_msg = ""

        self._param_style = 'named'

    def _adapt_sql(self, sql, bind_vars):
        new_sql = sql
        if self._param_style == 'pyformat':
            for key in bind_vars.keys():
                new_sql = new_sql.replace(NAMED_BIND_VAR_PREFIX + key, '%(' + key + ')s')
        return new_sql

    def _create_cursor(self):
        try:
            self.curs = self.conn.cursor()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint(self.dsn + ": database cursor created.")
        except Exception as ex:
            self.last_err_msg = self.dsn + "._create_cursor() error: " + str(ex)

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

    @staticmethod
    def _rebind(chk_values, where_group_order, bind_vars, extra_bind=None):
        rebound_vars = dict()   # use new instance to not change callers bind_vars dict

        if extra_bind:
            rebound_vars.update(extra_bind)
            if not chk_values:
                chk_values = dict([next(iter(extra_bind.items()))])  # use first dict item as pkey check value

        if chk_values:
            rebound_vars.update({bind_var_prefix + k: v for k, v in chk_values.items()})
            extra_where = " AND ".join([k + " = " + NAMED_BIND_VAR_PREFIX + bind_var_prefix + k
                                        for k in chk_values.keys()])
            if not where_group_order:
                where_group_order = extra_where
            elif where_group_order.upper().startswith(('GROUP BY', 'ORDER BY')):
                where_group_order = extra_where + " " + where_group_order
            else:
                where_group_order = "(" + extra_where + ") AND " + where_group_order

        if not where_group_order:
            where_group_order = '1=1'

        if bind_vars:
            rebound_vars.update({bind_var_prefix + k: v for k, v in bind_vars.items()})

        return chk_values, where_group_order, rebound_vars

    def call_proc(self, proc_name, proc_args, ret_dict=None):
        self.last_err_msg = ""
        try:
            ret = self.curs.callproc(proc_name, proc_args)
            if ret_dict:
                ret_dict['return'] = ret
        except Exception as ex:
            self.last_err_msg = self.dsn + " call_proc error: " + str(ex)
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
                    self.curs = None
                    if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                        uprint(self.dsn + " cursor closed")
                self.conn.close()
                self.conn = None
                if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    uprint(self.dsn + " connection closed")
            except Exception as ex:
                self.last_err_msg += self.dsn + " close error: " + str(ex)
        return self.last_err_msg

    def connect(self):
        raise NotImplementedError

    def cursor_description(self):
        return self.curs.description if self.curs else None

    def fetch_all(self):
        self.last_err_msg = ""
        try:
            rows = self.curs.fetchall()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint(self.dsn + ".fetch_all(), 1st of", len(rows), "recs:", rows[:1])
        except Exception as ex:
            self.last_err_msg = self.dsn + ".fetch_all() exception: " + str(ex)
            uprint(self.last_err_msg)
            rows = None
        return rows or list()

    def fetch_value(self, col_idx=0):
        self.last_err_msg = ""
        val = None
        try:
            values = self.curs.fetchone()
            if values:
                val = values[col_idx]
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint(self.dsn + ".fetch_value() retrieved values: {}[{}]".format(values, col_idx))
        except Exception as ex:
            self.last_err_msg = self.dsn + ".fetch_value()[{}] exception: {}; status message={}"\
                .format(col_idx, ex, self.curs.statusmessage)
            uprint(self.last_err_msg)
        return val

    def execute_sql(self, sql, commit=False, auto_commit=False, bind_vars=None):
        action = sql.split()[0]
        if action == '--' or action == '/*':
            action = 'SCRIPT'
        elif action.upper() == 'CREATE':
            action += ' ' + sql.split()[1]

        if self.conn or not self.connect():     # lazy connection
            if auto_commit:
                self.conn.autocommit = True     # or use: self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

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
                    uprint(self.dsn + ".execute_sql({}, {}) {}".format(sql, bind_vars, action))
                    uprint(".. " + action + " cursor.rowcount/description:", self.curs.rowcount, self.curs.description)

            except Exception as ex:
                self.last_err_msg += self.dsn + ".execute_sql() {} error={}; {}, {}".format(action, ex, sql, bind_vars)

        if self.debug_level >= DEBUG_LEVEL_ENABLED and self.last_err_msg:
            uprint(self.last_err_msg)

        return self.last_err_msg

    def delete(self, table_name, chk_values=None, where_group_order='', bind_vars=None, commit=False):
        chk_values, where_group_order, bind_vars = self._rebind(chk_values, where_group_order, bind_vars)
        sql = "DELETE FROM {} WHERE {}".format(table_name, where_group_order)

        with self.thread_lock_init(table_name, chk_values):
            self.execute_sql(sql, commit=commit, bind_vars=bind_vars)

        return self.last_err_msg

    def insert(self, table_name, col_values, returning_column='', commit=False):
        _normalize_col_values(col_values)
        sql = "INSERT INTO " + table_name + " (" + ", ".join(col_values.keys()) \
              + ") VALUES (" + ", ".join([NAMED_BIND_VAR_PREFIX + c for c in col_values.keys()]) + ")"
        if returning_column:
            sql += " RETURNING " + returning_column
        return self.execute_sql(sql, commit=commit, bind_vars=col_values)

    def select(self, from_join, cols=None, chk_values=None, where_group_order='', bind_vars=None, hints=''):
        if not cols:
            cols = list('*')
        chk_values, where_group_order, bind_vars = self._rebind(chk_values, where_group_order, bind_vars)
        sql = "SELECT {} {} FROM {} WHERE {}".format(hints, ','.join(cols), from_join, where_group_order)
        return self.execute_sql(sql, bind_vars=bind_vars)

    def update(self, table_name, col_values, chk_values=None, where_group_order='', bind_vars=None,
               commit=False, locked_cols=None):
        _normalize_col_values(col_values)
        chk_values, where_group_order, bind_vars = self._rebind(chk_values, where_group_order, bind_vars,
                                                                extra_bind=col_values)
        if locked_cols is None:
            locked_cols = list()
        sql = "UPDATE " + table_name \
              + " SET " + ", ".join([c + " = " + _locked_col_expr(c, locked_cols) for c in col_values.keys()])
        if where_group_order:
            sql += " WHERE " + where_group_order

        with self.thread_lock_init(table_name, chk_values):
            self.execute_sql(sql, commit=commit, bind_vars=bind_vars)

        return self.last_err_msg

    def upsert(self, table_name, col_values, chk_values=None, where_group_order='', bind_vars=None,
               returning_column='', commit=False, locked_cols=None, multiple_row_update=True):
        """
        INSERT or UPDATE in table_name the col_values, depending on if record already exists.
        :param table_name:          name of the database table.
        :param col_values:          dict of inserted/updated column values with the column name as key.
        :param chk_values:          dict of column names/values for to identify affected record(s), also used for to
                                    check if record already exists.
                                    If not passed then use first name/value of col_values (has then to be OrderedDict).
        :param where_group_order:   string added after the SQL WHERE clause (including WHERE, ORDER BY
                                    and GROUP BY expressions. bind variables - specified in the bind_vars arg - have to
                                    be prefixed with the 'CV_' var_prefix in this string - s.a. _rebind()).
        :param bind_vars:           dict of extra bind variables (key=name, value=value), e.g..
        :param returning_column:    name of column which value will be returned by next fetch_all/fetch_value() call.
        :param commit:              bool value to specify if commit should be done.
        :param locked_cols:         list of column names not be overwritten on update of column value is not empty
        :param multiple_row_update  allow update of multiple records with the same chk_values.
        :return:                    last error message or "" if no errors occurred.
        """
        _normalize_col_values(col_values)

        with self.thread_lock_init(table_name, chk_values):
            if not self.select(table_name, ["count(*)"],
                               chk_values=chk_values, where_group_order=where_group_order, bind_vars=bind_vars):
                count = self.fetch_value()
                if not self.last_err_msg:
                    if count == 1 or (multiple_row_update and count > 1):
                        if not self.update(table_name, col_values, chk_values=chk_values,
                                           where_group_order=where_group_order, bind_vars=bind_vars,
                                           commit=commit, locked_cols=locked_cols) \
                                and returning_column:
                            self.select(table_name, [returning_column],
                                        chk_values=chk_values, where_group_order=where_group_order, bind_vars=bind_vars)
                    elif count == 0:
                        col_values.update(chk_values)
                        self.insert(table_name, col_values, returning_column=returning_column, commit=commit)
                    else:               # count not in (0, 1) or count is None:
                        msg = "SELECT COUNT(*) returned None" if count is None \
                            else "skipping update because found {} duplicate check/search values".format(count)
                        self.last_err_msg = self.dsn + ".upsert() error={}; args={}, {}, {}, {}, {}"\
                            .format(msg, table_name, col_values, chk_values, where_group_order, bind_vars)
        return self.last_err_msg

    def commit(self, reset_last_err_msg=False):
        if reset_last_err_msg:
            self.last_err_msg = ""
        try:
            self.conn.commit()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint(self.dsn + ".commit()")
        except Exception as ex:
            self.last_err_msg = self.dsn + " commit error: " + str(ex)
        return self.last_err_msg

    def rollback(self, reset_last_err_msg=False):
        if reset_last_err_msg:
            self.last_err_msg = ""

        try:
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint(self.dsn + ".rollback()")
            self.conn.rollback()
        except Exception as ex:
            self.last_err_msg = self.dsn + " rollback error: " + str(ex)

        return self.last_err_msg

    def get_row_count(self):
        return self.curs.rowcount

    def selected_column_names(self):
        curs_desc = self.cursor_description()
        col_names = list()
        if curs_desc:
            for col_desc in curs_desc:
                col_names.append(col_desc[0])
        return col_names

    @staticmethod
    def thread_lock_init(table_name, chk_values):
        return NamedLocks(table_name + str(sorted(chk_values.items())))


class OraDB(GenericDB):
    def __init__(self, credentials, features=None, app_name='ae.db-ora', debug_level=DEBUG_LEVEL_DISABLED):
        """
        create instance of oracle database object
        :param credentials: dict with account credentials (SYS_CRED_ITEMS), including User=user name, Password=user
                            password and DSN=database name and optionally host address (separated with a @ character).
        :param features:    optional list of features (currently not used for databases).
        :param app_name:    application name (shown in the server DB session).
        :param debug_level: debug level.
        """
        super(OraDB, self).__init__(credentials, features=features, app_name=app_name, debug_level=debug_level)

        if self.dsn.count(':') == 1 and self.dsn.count('/@') == 1:   # old style format == host:port/@SID
            host, rest = self.dsn.split(':')
            port, service_id = rest.split('/@')
            self.dsn = cx_Oracle.makedsn(host=host, port=port, sid=service_id)
        elif self.dsn.count(':') == 1 and self.dsn.count('/') == 1:  # old style format == host:port/service_name
            host, rest = self.dsn.split(':')
            port, service_name = rest.split('/')
            self.dsn = cx_Oracle.makedsn(host=host, port=port, service_name=service_name)

        # used for to fix the following unicode encoding error:
        # .. 'charmap' codec can't decode byte 0x90 in position 2: character maps to <undefined>
        # ... BUT it was not working (still got same error)
        '''
        def output_type_handler(cursor, name, default_type, size, precision, scale):
            if default_type in (cx_Oracle.STRING, cx_Oracle.FIXED_CHAR):
                return cursor.var(cx_Oracle.NCHAR, size, cursor.arraysize)
        '''
        # .. luckily, finally found workaround with the next statement for OraDB
        os.environ["NLS_LANG"] = ".AL32UTF8"

    def connect(self):
        self.last_err_msg = ''
        try:
            # connect old style (using conn str): cx_Oracle.connect(self.usr + '/"' + self.pwd + '"@' + self.dsn)
            if cx_Oracle.__version__ > '6':
                # sys context was using clientinfo kwarg in/up-to cx_Oracle V5 - with V6 kwarg renamed to appcontext and
                # .. now it is using a list of 3-tuples. So since V6 need to replace clientinfo with appcontext=app_ctx
                NAMESPACE = "CLIENTCONTEXT"  # fetch in Oracle with SELECT SYS_CONTEXT(NAMESPACE, "APP") FROM DUAL
                app_ctx = [(NAMESPACE, "APP", self._app_name), (NAMESPACE, "LANG", "Python"),
                           (NAMESPACE, "MOD", "ae.db")]
                self.conn = cx_Oracle.connect(user=self.usr, password=self.pwd, dsn=self.dsn, appcontext=app_ctx)
            else:
                # sys context old style (until V5 using clientinfo):
                self.conn = cx_Oracle.connect(user=self.usr, password=self.pwd, dsn=self.dsn, clientinfo=self._app_name)
            # self.conn.outputtypehandler = output_type_handler       # see also comment in OraDB.__init__()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("OraDB: connected to Oracle database {} via client version {}/{} with n-/encoding {}/{}"
                       .format(self.dsn, cx_Oracle.clientversion(), cx_Oracle.apilevel,
                               self.conn.nencoding, self.conn.encoding))
        except Exception as ex:
            self.last_err_msg = "OraDB-connect {}@{} ex='{}'".format(getattr(self, 'usr'), getattr(self, 'dsn'), ex)
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
    def __init__(self, credentials, features=None, app_name='ae.db-pg', debug_level=DEBUG_LEVEL_DISABLED):
        """
        create instance of postgres database object
        :param credentials: dict with account credentials (SYS_CRED_ITEMS), including User=user name, Password=user
                            password, DSN=database name and optionally host address (separated with a @ character) and
                            SslArgs=dict of SSL arguments (sslmode, sslrootcert, sslcert, sslkey).
        :param features:    optional list of features (currently not used for databases).
        :param app_name:    application name (shown in the server DB session).
        :param debug_level: debug level.
        """
        super(PostgresDB, self).__init__(credentials, features=features, app_name=app_name, debug_level=debug_level)
        self._ssl_args = credentials.get('SslArgs')
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
            if self._app_name:
                connection_params['application_name'] = self._app_name
            if self._ssl_args:
                connection_params.update(self._ssl_args)

            self.conn = psycopg2.connect(**connection_params)
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                uprint("PostgresDB: connected to postgres database {} via api/server {}/{} with encoding {}"
                       .format(self.dsn, psycopg2.apilevel, self.conn.server_version, self.conn.encoding))
        except Exception as ex:
            self.last_err_msg = "PostgresDB-connect " + self.usr + " on " + self.dsn + " error: " + str(ex)
        else:
            self._create_cursor()
        return self.last_err_msg

    def execute_sql(self, sql, commit=False, auto_commit=False, bind_vars=None):
        if self.conn or not self.connect():
            ''' Overwriting generic execute_sql for Postgres because if auto_commit is False then a db error
                is invalidating the connection until it gets rolled back (optionally to a save-point).
                Unfortunately psycopg2 does not provide/implement save-points. Could be done alternatively with
                execute("SAVEPOINT NonAutoCommErrRollback") but RELEASE/ROLLBACK makes it complicated (see also
                https://stackoverflow.com/questions/2370328/continuing-a-transaction-after-primary-key-violation-error):
                
                    save_point = None if auto_commit else self.conn.setSavepoint('NonAutoCommErrRollback')
                    super().execute_sql(sql, commit=commit, auto_commit=auto_commit, bind_vars=bind_vars)
                    if save_point:
                        if self.last_err_msg:
                            self.conn.rollback(save_point)
                        else:
                            self.conn.releaseSavepoint(save_point)
                    return self.last_err_msg
                
                Therefore KISS - a simple rollback will do it also.
            '''
            super().execute_sql(sql, commit=commit, auto_commit=auto_commit, bind_vars=bind_vars)
            if self.last_err_msg and not auto_commit:
                if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    uprint("PostgresDB.execute_sql(): automatic rollback after error; for connection recycling")
                self.conn.rollback()
        return self.last_err_msg
