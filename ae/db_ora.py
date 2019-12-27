"""
oracle database layer
=====================

The main class :class:`OraDb` of this module is using the cx_Oracle package as the database driver
for to connect to an Oracle database.

The cx_Oracle package has to have version 5 or higher.

Basic Usage
-----------

For to create an instance of the class :class:`OraDb` you first have to create a
:class:`~ae.sys_core.SystemBase` instance. This can be done either programmatically
by providing an application instance (of the class :class:`~ae.ae_console.ConsoleApp`
or an inherited sub-class of it) plus any database parameters, like
required credentials and any database configuration features/options:

    app = ConsoleApp()
    system = SystemBase('system-id', app, dict(User='user name', Password='password`, ...), ...)

Alternatively provide all system-specific info within the :ref:`ae config files<config-files>`
and let :class:`~ae.sys_core.UsedSystems` load it:

    system = used_systems['system-id']

Finally pass the database parameters in `system` for to create an instance of :class:`OraDb`:

    ora_db = OraDb(system)

Then call the :meth:`~OraDb.connect` method of this instance for to connect to the Oracle database server:

    error_message = ora_db.connect()
    if error_message:
        print(error_message)

If the connection could not be established then  :meth:`~OraDb.connect` is returning an error
message string. If the return value is an empty string then you can use all the methods provided by
:class:`~ae.db_core.DbBase`, like e.g. :meth:`~ae.db_core.DbBase.update`:

    error_message = ora_db.update('my_table`, {'my_col': 'new value'})
    if error_message:
        print(error_message)
        error_message = ora_db.rollback()

An explicit call of :meth:`~ae.db_core.DbBase.rollback` is only needed if you use transactions.
In this case you should also use :meth:`~ae.db_core.DbBase.commit` at the end of each transaction for to store
any data updates:

    error_message = ora_db.commit()

Alternatively you can use the `commit` argument that is provided by the :class:`~ae.db_core.DbBase`
DML methods: by passing a `True` value to this argument, the method will automatically execute a
:meth:`~ae.db_core.DbBase.commit` call for you if no error occurred in the DML method:

    error_message = ora_db.update('table`, {'column': 369}, commit=True)

Finally after all database actions are done you can close the connection to the databases server
with the :meth:`~ae.db_core.DbBase.close` method:

    error_message = ora_db.close()

"""
import cx_Oracle
import datetime
import os
from typing import Any, Union

from ae.sys_core import SystemBase      # type: ignore  # for mypy
from ae.db_core import DbBase           # type: ignore  # for mypy


__version__ = '0.0.1'


class OraDb(DbBase):
    """ Oracle database class, based on :class:`~.db_core.DbBase` """
    def __init__(self, system: SystemBase):
        """ create instance of oracle database object.

        :param system:      instance of a :class:`~ae.sys_core.SystemBase` class.

        :class:`~ae.sys_core.SystemBase` (defined in the module :mod:`ae.sys_core`) is providing
        the credentials and features, which get retrieved from :ref:`config-files`, then converted
        by :meth:`~ae.db_core.DbBase.connect_params` into :ref:`connection parameters` for to connect
        to the Postgres database.

        If you experiencing the following unicode encoding error::

            'charmap' codec can't decode byte 0x90 in position 2: character maps to <undefined>

        Don't try to create a type handler like recommended in some places - I still got same error after adding
        the following method for to replace the self.conn.outputtypehandler of the database driver::

                def output_type_handler(cursor, name, default_type, size, precision, scale):
                    if default_type in (cx_Oracle.STRING, cx_Oracle.FIXED_CHAR):
                        return cursor.var(cx_Oracle.NCHAR, size, cursor.arraysize)

        Luckily, finally found workaround by setting the following OS environment variable to the
        character set of the used Oracle server (here UTF8)::

            os.environ["NLS_LANG"] = ".AL32UTF8"

        """
        super().__init__(system)
        os.environ["NLS_LANG"] = ".AL32UTF8"

    def connect(self):
        """ connect this instance to the database driver. """
        self.last_err_msg = ''

        conn_args = self.connect_params()
        user = conn_args.get('user')
        password = conn_args.get('password')
        dsn: str = conn_args.get('dsn')
        if dsn:
            if dsn.count(':') == 1 and dsn.count('/@') == 1:   # old style format == host:port/@SID
                host, rest = dsn.split(':', maxsplit=1)
                port, service_id = rest.split('/@', maxsplit=1)
                dsn = cx_Oracle.makedsn(host=host, port=port, sid=service_id)
            elif dsn and dsn.count(':') == 1 and dsn.count('/') == 1:  # old style format == host:port/service_name
                host, rest = dsn.split(':', maxsplit=1)
                port, service_name = rest.split('/', maxsplit=1)
                dsn = cx_Oracle.makedsn(host=host, port=port, service_name=service_name)
        else:
            dsn = cx_Oracle.makedsn(**conn_args)
        app_name = self.console_app.app_name

        try:
            # connect old style (using conn str): cx_Oracle.connect(self.usr + '/"' + self.pwd + '"@' + self.dsn)
            if cx_Oracle.__version__ >= '6':
                # sys context is using appcontext kwarg starting with cx_Oracle Version 6, which is
                # .. list of 3-tuples. So since V6 need to replace clientinfo kwarg with appcontext=app_ctx
                NAMESPACE = "CLIENTCONTEXT"  # fetch in Oracle with SELECT SYS_CONTEXT(NAMESPACE, "APP") FROM DUAL
                app_ctx = [(NAMESPACE, "APP", app_name),
                           (NAMESPACE, "LANG", "Python"),
                           (NAMESPACE, "MOD", "ae.db_ora")]
                self.conn = cx_Oracle.connect(user=user, password=password, dsn=dsn, appcontext=app_ctx)
            else:
                # sys context old style (until cx_Oracle Version 5 using clientinfo):
                self.conn = cx_Oracle.connect(user=user, password=password, dsn=dsn, clientinfo=app_name)
            # self.conn.outputtypehandler = output_type_handler       # see also comment in OraDb.__init__()
            self.console_app.dpo(f"OraDb.connect(): connected"
                                 f" via client version {cx_Oracle.clientversion()}/{cx_Oracle.apilevel}"
                                 f" with n-/encoding {self.conn.nencoding}/{self.conn.encoding} for {self}")
        except Exception as ex:
            self.last_err_msg = f"OraDb-connect() error '{ex}' for {self}"
        else:
            self.create_cursor()

        return self.last_err_msg

    def prepare_ref_param(self, value: Union[datetime.datetime, int, float, str]) -> Any:
        """ prepare special Oracle reference parameter.

        :param value:   the input value passed into the reference parameter of the called stored procedure.
        :return:        a handle to the reference variable.

        The following code snippet shows how to use this method together with :meth:`~.get_value` for
        to retrieve the returned value of a reference parameter::

            ora_db = OraDb(...)
            *ref_var* = ora_db.prepare_ref_param("input_value")
            err_msg = ora_db.call_proc('STORED_PROCEDURE', (*ref_var*, ...))
            if not err_msg:
                output_value = ora_db.get_value(*ref_var*)

        """
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
        """ get output value from a reference variable passed into a stored procedure.

        :param var:     handle to a reference variable.
        :return:        output value of the reference variable.
        """
        return var.getvalue()

    @staticmethod
    def set_value(var: Any, value: Union[datetime.datetime, int, float, str]):
        """ set the input value of a reference variable for to pass into a stored procedure.

        :param var:     handle to the reference variable to set.
        :param value:   value to set as input value of the reference variable.
        """
        var.setvalue(0, value)
