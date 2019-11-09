"""
postgres database layer
=======================

The main class :class:`PostgresDb` of this module is based on psycopg2 package.

Basic Usage
-----------

First create an instance of :class:`PostgresDb` providing the application instance (of the class
:class:`ConsoleApp` or an inherited sub-class of it) plus all needed credentials and features/options:

    app = ConsoleApp()
    pg_db = PostgresDb(app, dict(User='user name', Password='password`, Dsn='LIVE@TNS-NAME', ...), ...)

With the database properties provided at instantiation, call first the :meth:`~.connect` for to connect
to the Postgres database:

    error_message = pg_db.connect()
    if error_message:
        print(error_message)
        pg_db.rollback()

After that you can use any data selection and manipulation method of the base class
:class:`~.db_core.DbBase`.
"""
import psycopg2
# from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from typing import Any, Dict, Optional, Sequence

from ae.console import ConsoleApp
from ae.db_core import DbBase

__version__ = '0.0.1'


class PostgresDb(DbBase):
    """ an instance of this class represents a Postgres database. """
    def __init__(self, console_app: ConsoleApp, credentials: Dict[str, str], features: Sequence[str] = ()):
        """ create instance of postgres database object

        :param console_app: ConsoleApp instance of the application using this database.
        :param credentials: dict with database credentials ('CredItems' cfg), including User=user name, Password=user
                            password, DSN=database name and optionally host address (separated with a @ character) and
                            SslArgs=dict of SSL arguments (sslmode, sslrootcert, sslcert, sslkey).
        :param features:    optional list of features (currently not used for databases).
        """
        super().__init__(console_app, credentials, features=features)
        self._ssl_args = credentials.get('SslArgs')
        # for "named" PEP-0249 sql will be adapted to fit postgres driver "(pyformat)" sql bind-var/parameter syntax
        self._param_style = 'pyformat'

    def connect(self) -> str:
        """ connect this instance to the Postgres database server, using the credentials provided at instantiation.

        :return:    error message in case of error or empty string if not.
        """
        self.last_err_msg = ''
        try:
            connection_params = dict(user=self.usr, password=self.pwd)
            if '@' in self.dsn:
                connection_params['dbname'], connection_params['host'] = self.dsn.split('@')
            else:
                connection_params['dbname'] = self.dsn
            if self.console_app.app_name:
                connection_params['application_name'] = self.console_app.app_name
            if self._ssl_args:
                connection_params.update(self._ssl_args)

            self.conn = psycopg2.connect(**connection_params)
            self.console_app.dpo(f"PostgresDb: connected to postgres database {self.dsn}"
                                 f" via api/server {psycopg2.apilevel}/{self.conn.server_version}"
                                 f" with encoding {self.conn.encoding}")
        except Exception as ex:
            self.last_err_msg = f"PostgresDb-connect {self.usr} on {self.dsn} error: {ex}"
        else:
            self._create_cursor()
        return self.last_err_msg

    def execute_sql(self, sql: str, commit: bool = False, bind_vars: Optional[Dict[str, Any]] = None,
                    auto_commit: bool = False) -> str:
        """ execute sql query.

        :param sql:             sql query to execute.
        :param commit:          pass True to commit (after UPDATE queries).
        :param bind_vars:
        :param auto_commit:     pass True
        :return:

        .. hint::
            Overwriting generic execute_sql for Postgres because if auto_commit is False then a db error
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

        """
        if self.conn or not self.connect():
            if auto_commit:
                self.conn.autocommit = True     # or use: self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            super().execute_sql(sql, commit=commit, bind_vars=bind_vars)

            if self.last_err_msg and not auto_commit:
                self.console_app.dpo("PostgresDb.execute_sql(): automatic rollback after error (connection recycling)")
                self.conn.rollback()

        return self.last_err_msg
