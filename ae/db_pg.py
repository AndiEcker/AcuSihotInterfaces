"""
postgres database layer
=======================

This module provides the class :class:`PostgresDb` for to connect and interact
with a Postgres database server.

The communication with the database driver is done with great help of the
:ref:`psycopg2 pypi package <https://pypi.org/project/psycopg2>`.

Basic Usage
-----------

For to create an instance of the class :class:`PostgresDb` you first have to create a
:class:`~ae.sys_core.SystemBase` instance. This can be done either programmatically
by providing an application instance (of the class :class:`~ae.ae_console.ConsoleApp`
or an inherited sub-class of it) plus any database parameters, like
required credentials and any database configuration features/options:

    app = ConsoleApp()
    system = SystemBase('system-id', app, dict(User='user name', Password='password`, Dsn='dbname@host', ...), ...)

Alternatively provide all system-specific info within the :ref:`ae config files<config-files>`
and let :class:`~ae.sys_core.UsedSystems` load it:

    system = used_systems['system-id']

Finally pass the database parameters in `system` for to create an instance of :class:`PostgresDb`:

    pg_db = PostgresDb(system)

Then call the :meth:`~PostgresDb.connect` method of this instance for to connect to the Postgres database server:

    error_message = pg_db.connect()
    if error_message:
        print(error_message)

If the connection could not be established then  :meth:`~PostgresDb.connect` is returning an error
message string. If the return value is an empty string then you can use all the methods provided by
:class:`~ae.db_core.DbBase`, like e.g. :meth:`~ae.db_core.DbBase.update`:

    error_message = pg_db.update('my_table`, {'my_col': 'new value'})
    if error_message:
        print(error_message)
        error_message = pg_db.rollback()

An explicit call of :meth:`~ae.db_core.DbBase.rollback` is only needed if you use transactions (autocommit is False).
In this case you should also use :meth:`~ae.db_core.DbBase.commit` at the end of each transaction for to store
any data updates:

    error_message = pg_db.commit()

Alternatively you can use the `commit` argument that is provided by the :class:`~ae.db_core.DbBase`
DML methods: by passing a `True` value to this argument, the method will automatically execute a
:meth:`~ae.db_core.DbBase.commit` call for you if no error occurred in the DML method:

    error_message = pg_db.update('table`, {'column': 369}, commit=True)

Finally after all database actions are done you can close the connection to the databases server
with the :meth:`~ae.db_core.DbBase.close` method:

    error_message = pg_db.close()

"""
import psycopg2
# from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from typing import Any, Dict, Optional

from ae.sys_core import SystemBase
from ae.db_core import DbBase

__version__ = '0.0.1'


class PostgresDb(DbBase):
    """ an instance of this class represents a Postgres database. """
    def __init__(self, system: SystemBase):
        """ create instance of Postgres database object

        :param system:      instance of a :class:`ae.sys_core.SystemBase` class.

        The :class:`ae.sys_core.SystemBase` which is implemented in the module :mod:`ae.sys_core` is providing
        the credentials and features for the Postgres database, which get retrieved
        from config files ('availableSystems' and other config variables). Some useful attributes
        of this class are e.g.:

        **console_app** : ConsoleApp instance of the application using this database.

        **credentials** : dict with credentials for to connect to a Postgres database. The following
        credentials are supported by the database driver (only user and password
        and the database name are mandatory):

        * **user** : user name
        * **password** : user password
        * **dbname** : database name (alternatively use the **database** key)
        * **database** : database name (alternative to **dbname**)
        * **dsn** : database name with optional host address (separated with a @ character)
        * **host** : database server host name or IP address
        * **port** : database server port number

        For connections via SSL to the Postgres server you have to add either the dict keys
        **sslmode**, **sslcert** and **sslkey** or **sslrootcert** and **sslcrl** (depending
        on the configuration of your server).

        **features** :    optional list of features.
        """
        super().__init__(system)
        # for "named" PEP-0249 sql will be adapted to fit postgres driver "(pyformat)" sql bind-var/parameter syntax
        self.param_style = 'pyformat'

    def connect(self) -> str:
        """ connect this instance to the Postgres database server, using the credentials provided at instantiation.

        :return:    error message in case of error or empty string if not.
        """
        self.last_err_msg = ''
        try:
            connection_params = dict()
            if '@' in self.dsn:
                connection_params['dbname'], connection_params['host'] = self.dsn.split('@')
            else:
                connection_params['dbname'] = self.dsn
            if self.console_app.app_name:
                connection_params['application_name'] = self.console_app.app_name
            connection_params.update(self.connect_params())
            if 'database' in connection_params:
                connection_params.pop('dbname')

            self.conn = psycopg2.connect(**connection_params)
            self.console_app.dpo(f"PostgresDb.connect(): connected"
                                 f" via api/server {psycopg2.apilevel}/{self.conn.server_version}"
                                 f" with encoding {self.conn.encoding} for {self}")
        except Exception as ex:
            self.last_err_msg = f"PostgresDb-connect() error: {ex} for {self}"
        else:
            self.create_cursor()
        return self.last_err_msg

    def execute_sql(self, sql: str, commit: bool = False, bind_vars: Optional[Dict[str, Any]] = None,
                    auto_commit: bool = False) -> str:
        """ execute sql query or sql command.

        :param sql:             sql query or command to execute.
        :param commit:          pass True to commit (after INSERT or UPDATE queries).
        :param bind_vars:       dict of bind variables (key=variable name, value=value).
        :param auto_commit:     pass True activate auto-commit-mode for this postgres session.
        :return:                last error message or empty string if no errors occurred.

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
