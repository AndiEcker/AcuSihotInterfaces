import psycopg2
# from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from ae.core import DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_VERBOSE, po
from ae.db_core import DbBase

__version__ = '0.0.1'


class PostgresDB(DbBase):
    def __init__(self, credentials, features=None, app_name='ae.db-pg', debug_level=DEBUG_LEVEL_DISABLED):
        """
        create instance of postgres database object
        :param credentials: dict with account credentials ('CredItems' cfg), including User=user name, Password=user
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
            if self.app_name:
                connection_params['application_name'] = self.app_name
            if self._ssl_args:
                connection_params.update(self._ssl_args)

            self.conn = psycopg2.connect(**connection_params)
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                po(f"PostgresDB: connected to postgres database {self.dsn}"
                   f" via api/server {psycopg2.apilevel}/{self.conn.server_version}"
                   f" with encoding {self.conn.encoding}")
        except Exception as ex:
            self.last_err_msg = f"PostgresDB-connect {self.usr} on {self.dsn} error: {ex}"
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
                    po("PostgresDB.execute_sql(): automatic rollback after error; for connection recycling")
                self.conn.rollback()
        return self.last_err_msg
