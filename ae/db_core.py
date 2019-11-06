"""
    provide database connections - currently supported database are Postgres and Oracle.
"""
from copy import deepcopy

from ae.core import DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE, po
from ae.lockname import NamedLocks

__version__ = '0.0.1'


NAMED_BIND_VAR_PREFIX = ':'
bind_var_prefix = "CV_"   # for to allow new value in SET clause and old value in WHERE clause for same column/-name
# .. we add this prefix to all bind_vars and chk_values (self._adapt_sql() would not work with suffix)


def _normalize_col_values(col_values):
    for key, val in col_values.items():
        if isinstance(val, str) and not val:
            col_values[key] = None
    return col_values


class DbBase:
    def __init__(self, credentials, features=None, app_name='ae.db-gen', debug_level=DEBUG_LEVEL_DISABLED):
        """
        create instance of generic database object (base class for real database like e.g. postgres or oracle).
        :param credentials: dict with account credentials ('CredItems' cfg), including User=user name, Password=user
                            password and DSN=database name and optionally host address (separated with a @ character).
        :param features:    optional list of features (currently not used for databases).
        :param app_name:    application name (shown in the server DB session).
        :param debug_level: debug level.
        """
        user = credentials.get('User')
        password = credentials.get('Password')
        dsn = credentials.get('DSN')
        assert user and password, f"db.py/DbBase has empty user name ({user}) and/or password"
        self.usr = user
        self.pwd = password
        assert dsn and isinstance(dsn, str), f"db.py/DbBase() has invalid dsn argument {dsn}"
        self.dsn = dsn
        self._features = features
        self.app_name = app_name
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
                po(f"{self.dsn}: database cursor created.")
        except Exception as ex:
            self.last_err_msg = f"{self.dsn}._create_cursor() error: {ex}"

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
            extra_where = " AND ".join([f"{k} = {NAMED_BIND_VAR_PREFIX}{bind_var_prefix}{k}"
                                        for k in chk_values.keys()])
            if not where_group_order:
                where_group_order = extra_where
            elif where_group_order.upper().startswith(('GROUP BY', 'ORDER BY')):
                where_group_order = f"{extra_where} {where_group_order}"
            else:
                where_group_order = f"({extra_where}) AND {where_group_order}"

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
            self.last_err_msg = f"{self.dsn} call_proc error: {ex}"
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
                        po(f"{self.dsn} cursor closed")
                self.conn.close()
                self.conn = None
                if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    po(f"{self.dsn} connection closed")
            except Exception as ex:
                self.last_err_msg += f"{self.dsn} close error: {ex}"
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
                po(f"{self.dsn}.fetch_all(), 1st of {len(rows)} recs: {rows[:1]}")
        except Exception as ex:
            self.last_err_msg = f"{self.dsn}.fetch_all() exception: {ex}"
            po(self.last_err_msg)
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
                po(f"{self.dsn}.fetch_value() retrieved values: {values}[{col_idx}]")
        except Exception as ex:
            self.last_err_msg = \
                f"{self.dsn}.fetch_value()[{col_idx}] exception: {ex}; status message={self.curs.statusmessage}"
            po(self.last_err_msg)
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
                    po(f"{self.dsn}.execute_sql({sql}, {bind_vars}) {action}")
                    po(f".. {action} cursor.rowcount/description: {self.curs.rowcount} {self.curs.description}")

            except Exception as ex:
                self.last_err_msg += f"{self.dsn}.execute_sql() {action} error={ex}; {sql}, {bind_vars}"

        if self.debug_level >= DEBUG_LEVEL_ENABLED and self.last_err_msg:
            po(self.last_err_msg)

        return self.last_err_msg

    def delete(self, table_name, chk_values=None, where_group_order='', bind_vars=None, commit=False):
        chk_values, where_group_order, bind_vars = self._rebind(chk_values, where_group_order, bind_vars)
        sql = f"DELETE FROM {table_name} WHERE {where_group_order}"

        with self.thread_lock_init(table_name, chk_values):
            self.execute_sql(sql, commit=commit, bind_vars=bind_vars)

        return self.last_err_msg

    def insert(self, table_name, col_values, returning_column='', commit=False):
        _normalize_col_values(col_values)
        sql = f"INSERT INTO {table_name} (" + ", ".join(col_values.keys()) \
              + ") VALUES (" + ", ".join([NAMED_BIND_VAR_PREFIX + c for c in col_values.keys()]) + ")"
        if returning_column:
            sql += " RETURNING " + returning_column
        return self.execute_sql(sql, commit=commit, bind_vars=col_values)

    def select(self, from_join, cols=None, chk_values=None, where_group_order='', bind_vars=None, hints=''):
        if not cols:
            cols = list('*')
        chk_values, where_group_order, bind_vars = self._rebind(chk_values, where_group_order, bind_vars)
        sql = f"SELECT {hints} {','.join(cols)} FROM {from_join} WHERE {where_group_order}"
        return self.execute_sql(sql, bind_vars=bind_vars)

    def update(self, table_name, col_values, chk_values=None, where_group_order='', bind_vars=None,
               commit=False, locked_cols=None):
        _normalize_col_values(col_values)
        chk_values, where_group_order, bind_vars = self._rebind(chk_values, where_group_order, bind_vars,
                                                                extra_bind=col_values)
        if locked_cols is None:
            locked_cols = list()
        sql = "UPDATE " + table_name \
              + " SET " + ", ".join([
                f"{col} = " + (f"COALESCE({col}, {NAMED_BIND_VAR_PREFIX}{col})" if col in locked_cols else
                               f"{NAMED_BIND_VAR_PREFIX}{col}")
                for col in col_values.keys()])
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
                            else f"skipping update because found {count} duplicate check/search values"
                        self.last_err_msg = f"{self.dsn}.upsert() error={msg}; args={table_name}," \
                                            f" {col_values}, {chk_values}, {where_group_order}, {bind_vars}"
        return self.last_err_msg

    def commit(self, reset_last_err_msg=False):
        if reset_last_err_msg:
            self.last_err_msg = ""
        try:
            self.conn.commit()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                po(f"{self.dsn}.commit()")
        except Exception as ex:
            self.last_err_msg = f"{self.dsn} commit error: {ex}"
        return self.last_err_msg

    def rollback(self, reset_last_err_msg=False):
        if reset_last_err_msg:
            self.last_err_msg = ""

        try:
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                po(f"{self.dsn}.rollback()")
            self.conn.rollback()
        except Exception as ex:
            self.last_err_msg = f"{self.dsn} rollback error: {ex}"

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
