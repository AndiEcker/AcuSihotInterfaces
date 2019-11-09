"""
oracle database layer
=====================

The main class :class:`OraDb` of this module is based on cx_Oracle package.

The cx_Oracle package has to have version 5 or higher.

Basic Usage
-----------

First create an instance of :class:`OraDb` providing the application instance (of the class
:class:`ConsoleApp` or an inherited sub-class of it) plus all needed credentials and features/options:

    app = ConsoleApp()
    ora_db = OraDb(app, dict(User='user name', Password='password`, Dsn='LIVE@TNS-NAME', ...), ...)

With the database properties provided at instantiation, call first the :meth:`~.connect` for to connect
to the Oracle database:

    error_message = ora_db.connect()
    if error_message:
        print(error_message)
        ora_db.rollback()

After that you can use any data selection and manipulation method of the base class
:class:`~.db_core.DbBase`.
"""
import cx_Oracle
import datetime
import os
from typing import Any, Dict, Sequence, Union

from ae.console import ConsoleApp
from ae.db_core import DbBase

__version__ = '0.0.1'


class OraDb(DbBase):
    """ Oracle database class, based on :class:`~.db_core.DbBase` """
    def __init__(self, console_app: ConsoleApp, credentials: Dict[str, str], features: Sequence[str] = ()):
        """ create instance of oracle database object.

        :param console_app: ConsoleApp instance of the application using this database.
        :param credentials: dict with account credentials ('CredItems' cfg), including User=user name, Password=user
                            password and DSN=database name and optionally host address (separated with a @ character).
        :param features:    optional list of features (currently not used for databases).

        If you experiencing the following unicode encoding error::

            'charmap' codec can't decode byte 0x90 in position 2: character maps to <undefined>

        Don't try to create a type handler like recommended in some places - I still got same error after adding
        the following method for to replace the self.conn.outputtypehandler of the database driver::

                def output_type_handler(cursor, name, default_type, size, precision, scale):
                    if default_type in (cx_Oracle.STRING, cx_Oracle.FIXED_CHAR):
                        return cursor.var(cx_Oracle.NCHAR, size, cursor.arraysize)

        Luckily, finally found workaround with the following statement executed at the end of this method::

            os.environ["NLS_LANG"] = ".AL32UTF8"

        """
        super().__init__(console_app, credentials, features=features)

        if self.dsn.count(':') == 1 and self.dsn.count('/@') == 1:   # old style format == host:port/@SID
            host, rest = self.dsn.split(':')
            port, service_id = rest.split('/@')
            self.dsn = cx_Oracle.makedsn(host=host, port=port, sid=service_id)
        elif self.dsn.count(':') == 1 and self.dsn.count('/') == 1:  # old style format == host:port/service_name
            host, rest = self.dsn.split(':')
            port, service_name = rest.split('/')
            self.dsn = cx_Oracle.makedsn(host=host, port=port, service_name=service_name)

        os.environ["NLS_LANG"] = ".AL32UTF8"

    def connect(self):
        """ connect this instance to the database driver. """
        self.last_err_msg = ''
        try:
            # connect old style (using conn str): cx_Oracle.connect(self.usr + '/"' + self.pwd + '"@' + self.dsn)
            if cx_Oracle.__version__ > '6':
                # sys context was using clientinfo kwarg in/up-to cx_Oracle V5 - with V6 kwarg renamed to appcontext and
                # .. now it is using a list of 3-tuples. So since V6 need to replace clientinfo with appcontext=app_ctx
                NAMESPACE = "CLIENTCONTEXT"  # fetch in Oracle with SELECT SYS_CONTEXT(NAMESPACE, "APP") FROM DUAL
                app_ctx = [(NAMESPACE, "APP", self.console_app.app_name), (NAMESPACE, "LANG", "Python"),
                           (NAMESPACE, "MOD", "ae.db")]
                self.conn = cx_Oracle.connect(user=self.usr, password=self.pwd, dsn=self.dsn, appcontext=app_ctx)
            else:
                # sys context old style (until V5 using clientinfo):
                self.conn = cx_Oracle.connect(user=self.usr, password=self.pwd, dsn=self.dsn,
                                              clientinfo=self.console_app.app_name)
            # self.conn.outputtypehandler = output_type_handler       # see also comment in OraDb.__init__()
            self.console_app.dpo(f"OraDb: connected to Oracle database {self.dsn}"
                                 f" via client version {cx_Oracle.clientversion()}/{cx_Oracle.apilevel}"
                                 f" with n-/encoding {self.conn.nencoding}/{self.conn.encoding}")
        except Exception as ex:
            self.last_err_msg = f"OraDb-connect {getattr(self, 'usr')}@{getattr(self, 'dsn')} ex='{ex}'"
        else:
            self._create_cursor()
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
