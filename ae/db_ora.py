import cx_Oracle
import datetime
import os

from ae.core import DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_VERBOSE, po
from ae.db_core import DbBase

__version__ = '0.0.1'


class OraDB(DbBase):
    def __init__(self, credentials, features=None, app_name='ae.db-ora', debug_level=DEBUG_LEVEL_DISABLED):
        """
        create instance of oracle database object
        :param credentials: dict with account credentials ('CredItems' cfg), including User=user name, Password=user
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
                app_ctx = [(NAMESPACE, "APP", self.app_name), (NAMESPACE, "LANG", "Python"),
                           (NAMESPACE, "MOD", "ae.db")]
                self.conn = cx_Oracle.connect(user=self.usr, password=self.pwd, dsn=self.dsn, appcontext=app_ctx)
            else:
                # sys context old style (until V5 using clientinfo):
                self.conn = cx_Oracle.connect(user=self.usr, password=self.pwd, dsn=self.dsn, clientinfo=self.app_name)
            # self.conn.outputtypehandler = output_type_handler       # see also comment in OraDB.__init__()
            if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                po(f"OraDB: connected to Oracle database {self.dsn}"
                   f" via client version {cx_Oracle.clientversion()}/{cx_Oracle.apilevel}"
                   f" with n-/encoding {self.conn.nencoding}/{self.conn.encoding}")
        except Exception as ex:
            self.last_err_msg = f"OraDB-connect {getattr(self, 'usr')}@{getattr(self, 'dsn')} ex='{ex}'"
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
