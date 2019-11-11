""" ae.db_core unit tests """
import pytest

from ae.core import DEBUG_LEVEL_ENABLED
from ae.console import ConsoleApp
from ae.lockname import NamedLocks

from ae.db_core import DbBase, NAMED_BIND_VAR_PREFIX, CHK_BIND_VAR_PREFIX


PROC_NAME = 'PROC_NAME'
PROC_ARGS = ('PROC_ARG1', 'PROC_ARG2')
FETCH_ALL_VALUES = [(1, 'COL2_VAL', 'COL3_VAL')]    # the 1 value is used for test_upsert*()


class XxConn:
    def connect(self, *args, **kwargs):
        return self, args, kwargs

    def cursor(self):
        return XxCurs(self)

    def commit(self):
        return

    def rollback(self):
        return

    def close(self):
        return


class XxCurs:
    description = (('COL1', ), ('COL2', ), )
    statusmessage = "XxCursStatusMessage"
    rowcount = 0

    def __init__(self, conn):
        self.conn_obj = conn
        self.exec_sql = ""
        self.exec_bind_vars = dict()

    def callproc(self, proc_name, proc_args):
        return self, proc_name, proc_args

    def close(self):
        return

    def execute(self, sql, bind_vars=None):
        self.exec_sql = sql
        self.exec_bind_vars = bind_vars

    def fetchall(self):
        self.rowcount = 1
        return FETCH_ALL_VALUES or self

    def fetchone(self):
        self.rowcount = 1
        return FETCH_ALL_VALUES[0] or self


class XxDb(DbBase):
    def connect(self):
        self.conn = XxConn()
        self._create_cursor()
        return self.last_err_msg


DB_USER = 'db_user'
DB_PASSWORD = 'db_password'
DB_DSN = 'db_dsn'


@pytest.fixture
def db(cons_app):
    return DbBase(cons_app, dict(User=DB_USER, Password=DB_PASSWORD, DSN=DB_DSN))


@pytest.fixture
def xx(cons_app):
    ret = XxDb(cons_app, dict(User=DB_USER, Password=DB_PASSWORD, DSN=DB_DSN))
    ret.connect()
    return ret


class TestDbBaseUnconnected:
    def test_init(self, db):
        assert isinstance(db.console_app, ConsoleApp)
        assert db.usr == DB_USER
        assert db.pwd == DB_PASSWORD
        assert db.dsn == DB_DSN
        assert db.conn is None
        assert db.curs is None
        assert db.last_err_msg == ""
        assert db._param_style == 'named'

    def test_adapt_sql(self, db):
        sql = "SELECT a FROM b WHERE c > :d"
        assert db._adapt_sql(sql, dict(d=1)) == sql
        db._param_style = 'pyformat'
        assert db._adapt_sql(sql, dict(d=1)) == "SELECT a FROM b WHERE c > %(d)s"
        assert db.last_err_msg == ""

    def test_create_cursor_ex_cov(self, db):
        assert db.last_err_msg == ""
        db._create_cursor()     # produces error because db.conn is not initialized
        assert db.last_err_msg

    def test_prepare_in_clause(self, db):
        sql = "SELECT a FROM b WHERE c IN (:d)"
        sqo, bind = db._prepare_in_clause(sql, dict(d=1))
        assert sqo == sql
        assert bind == dict(d=1)

        sqo, bind = db._prepare_in_clause(sql, dict(d=[1, 2]))
        assert sqo == "SELECT a FROM b WHERE c IN (:d_0,:d_1)"
        assert bind == dict(d_0=1, d_1=2)

    def test_rebind_ensure_nonempty_chk(self, db):
        chk = dict()
        wgo = " GROUP BY x ORDER BY y"
        bdv = dict(d=2)
        ebd = dict(e=3)
        new_chk, new_wgo, new_bdv = db._rebind(chk, wgo, bdv, ebd)
        assert new_chk == ebd
        assert f"{NAMED_BIND_VAR_PREFIX}{CHK_BIND_VAR_PREFIX}e" in new_wgo
        assert new_bdv == {CHK_BIND_VAR_PREFIX + 'd': 2, CHK_BIND_VAR_PREFIX + 'e': 3, 'e': 3}

    def test_rebind_ensure_nonempty_wgo(self, db):
        chk = dict(d=1)
        wgo = ""
        bdv = dict()
        new_chk, new_wgo, new_bdv = db._rebind(chk, wgo, bdv)
        assert new_chk is chk
        assert f"{NAMED_BIND_VAR_PREFIX}{CHK_BIND_VAR_PREFIX}d" in new_wgo
        assert new_bdv == {CHK_BIND_VAR_PREFIX + 'd': 1}

    def test_rebind_ensure_nonempty_wgo_without_chk(self, db):
        chk = dict()
        wgo = ""
        bdv = dict()
        new_chk, new_wgo, new_bdv = db._rebind(chk, wgo, bdv)
        assert new_chk is chk
        assert new_wgo != ""    # 1=1
        assert new_bdv == chk

    def test_rebind_chk_into_order_wgo(self, db):
        chk = dict(d=1)
        wgo = "order by x"
        bdv = dict()
        new_chk, new_wgo, new_bdv = db._rebind(chk, wgo, bdv)
        bdn = f"{NAMED_BIND_VAR_PREFIX}{CHK_BIND_VAR_PREFIX}d"
        assert new_chk is chk
        assert bdn in new_wgo
        assert new_wgo.find(bdn) < new_wgo.find('order by')
        assert new_bdv == {CHK_BIND_VAR_PREFIX + 'd': 1}

    def test_rebind_chk_into_group_wgo(self, db):
        chk = dict(d=1)
        wgo = "group by x"
        bdv = dict()
        new_chk, new_wgo, new_bdv = db._rebind(chk, wgo, bdv)
        bdn = f"{NAMED_BIND_VAR_PREFIX}{CHK_BIND_VAR_PREFIX}d"
        assert new_chk is chk
        assert bdn in new_wgo
        assert new_wgo.find(bdn) < new_wgo.find('group by')
        assert new_bdv == {CHK_BIND_VAR_PREFIX + 'd': 1}

    def test_rebind_merge_bind_vars(self, db):
        chk = dict(d=1)
        wgo = "c = 'city' GROUP BY x ORDER BY y"
        bdv = dict(v=2)
        ebd = dict(e=3)
        new_chk, new_wgo, new_bdv = db._rebind(chk, wgo, bdv, ebd)
        assert new_chk is chk
        assert f"{NAMED_BIND_VAR_PREFIX}{CHK_BIND_VAR_PREFIX}d" in new_wgo
        assert new_bdv == {'CV_d': 1, 'CV_v': 2, 'e': 3}

    def test_rebind_overwrite_bind_vars(self, db):
        chk = dict(d=1)
        wgo = "c = 'city' GROUP BY x ORDER BY y"
        bdv = dict(d=2)
        ebd = dict(e=3)
        new_chk, new_wgo, new_bdv = db._rebind(chk, wgo, bdv, ebd)
        assert chk is new_chk
        assert f"{NAMED_BIND_VAR_PREFIX}{CHK_BIND_VAR_PREFIX}d" in new_wgo
        assert new_bdv == {'CV_d': 2, 'e': 3}

    def test_call_proc_ex_cov(self, db):
        db.call_proc('', ())
        assert db.last_err_msg

    def test_close_ex_cov(self, db):
        db.conn = "invalidConnObj"
        db.close()
        assert db.last_err_msg

    def test_connect_ex_cov(self, db):
        with pytest.raises(NotImplementedError):
            db.connect()

    def test_cursor_description_no_curs_cov(self, db):
        assert db.cursor_description() is None

    def test_fetch_all_ex_cov(self, db):
        rows = db.fetch_all()
        assert isinstance(rows, list)
        assert db.last_err_msg

    def test_execute_sql_ex_cov(self, db):
        db.conn = XxConn()
        db.execute_sql('InvalidSQLOnUnconnectedConn')
        assert db.last_err_msg


class TestBaseDbStubConnected:
    def test_connect_create_cursor(self, xx):
        assert xx.connect() == ""
        assert isinstance(xx.conn, XxConn)
        assert isinstance(xx.curs, XxCurs)
        assert xx.last_err_msg == ""

    def test_call_proc(self, xx):
        ret = dict()
        xx.call_proc(PROC_NAME, PROC_ARGS, ret_dict=ret)
        assert xx.last_err_msg == ""
        cur, prn, pra = ret['return']
        assert isinstance(cur, XxCurs)
        assert prn == PROC_NAME
        assert pra == PROC_ARGS

    def test_close(self, xx):
        xx.close()
        assert xx.last_err_msg == ""
        assert xx.conn is None
        assert xx.curs is None

    def test_close_rollback(self, xx):
        xx.close(commit=False)
        assert xx.last_err_msg == ""
        assert xx.conn is None
        assert xx.curs is None

    def test_cursor_description(self, xx):
        assert xx.cursor_description() == XxCurs.description
        assert xx.last_err_msg == ""

    def test_fetch_all(self, xx):
        rows = xx.fetch_all()
        assert xx.last_err_msg == ""
        assert isinstance(rows, list)
        assert rows is FETCH_ALL_VALUES

    def test_fetch_value(self, xx):
        col_val = xx.fetch_value(1)
        assert xx.last_err_msg == ""
        assert col_val == FETCH_ALL_VALUES[0][1]

    def test_fetch_value_ex_cov(self, xx):
        xx.curs.fetchone = "InvalidCursorMeth"
        xx.fetch_value()
        assert xx.last_err_msg

    def test_execute_sql(self, xx):
        xx.execute_sql('CREATE TABLE a')
        assert xx.last_err_msg == ""
        assert xx.curs.exec_sql == 'CREATE TABLE a'

    def test_execute_sql_script_action(self, xx):
        xx.execute_sql('-- SCRIPT')
        assert xx.last_err_msg == ""
        assert xx.curs.exec_sql == '-- SCRIPT'

    def test_execute_sql_bind_vars(self, xx):
        bind_vars = dict(d=1)
        xx.execute_sql('SELECT 1', bind_vars=bind_vars)
        assert xx.last_err_msg == ""
        assert xx.curs.exec_sql == 'SELECT 1'
        assert xx.curs.exec_bind_vars == bind_vars

    def test_execute_sql_commit(self, xx):
        xx.execute_sql('CREATE TABLE a', commit=True)
        assert xx.last_err_msg == ""
        assert xx.curs.exec_sql == 'CREATE TABLE a'

    def test_execute_sql_ex_debug_cov(self, xx):
        xx.curs.execute = "InvalidCursMeth"
        xx.console_app.debug_level = DEBUG_LEVEL_ENABLED
        xx.execute_sql('CREATE TABLE a')
        assert xx.last_err_msg

    def test_delete(self, xx):
        xx.delete('TABLE_NAME', dict(chk=33), "GROUP BY z", dict(bind=99), commit=True)
        assert xx.last_err_msg == ""
        assert 'DELETE ' in xx.curs.exec_sql
        assert 'TABLE_NAME' in xx.curs.exec_sql
        assert 'chk' in xx.curs.exec_sql
        assert "GROUP BY z" in xx.curs.exec_sql

    def test_insert(self, xx):
        xx.insert('TABLE_NAME', dict(chk=33), "RET_COL", commit=True)
        assert xx.last_err_msg == ""
        assert 'INSERT ' in xx.curs.exec_sql
        assert 'TABLE_NAME' in xx.curs.exec_sql
        assert 'chk' in xx.curs.exec_sql
        assert "RET_COL" in xx.curs.exec_sql

    def test_select(self, xx):
        xx.select('TABLE_NAME', (), dict(chk=3), "GROUP BY z", dict(bind=99), hints="HINTS")
        assert xx.last_err_msg == ""
        assert 'SELECT ' in xx.curs.exec_sql
        assert 'TABLE_NAME' in xx.curs.exec_sql
        assert 'chk' in xx.curs.exec_sql
        assert "GROUP BY z" in xx.curs.exec_sql
        assert "HINTS" in xx.curs.exec_sql

    def test_update(self, xx):
        xx.update('TABLE_NAME', dict(col=1), dict(chk=3), "EXTRA_WHERE", dict(bind=99))
        assert xx.last_err_msg == ""
        assert 'UPDATE ' in xx.curs.exec_sql
        assert 'TABLE_NAME' in xx.curs.exec_sql
        assert 'col' in xx.curs.exec_sql
        assert 'chk' in xx.curs.exec_sql
        assert "EXTRA_WHERE" in xx.curs.exec_sql

    def test_upsert(self, xx):
        xx.upsert('TABLE_NAME', dict(col=1), dict(chk=3), "EXTRA_WHERE", dict(bind=99))
        assert xx.last_err_msg == ""
        assert 'UPDATE ' in xx.curs.exec_sql
        assert 'TABLE_NAME' in xx.curs.exec_sql
        assert 'col' in xx.curs.exec_sql
        assert 'chk' in xx.curs.exec_sql
        assert "EXTRA_WHERE" in xx.curs.exec_sql

    def test_upsert_returning(self, xx):
        xx.upsert('TABLE_NAME', dict(col=1), dict(chk=3), "EXTRA_WHERE", dict(bind=99), returning_column='RET_COL')
        assert xx.last_err_msg == ""
        assert 'SELECT ' in xx.curs.exec_sql
        assert 'TABLE_NAME' in xx.curs.exec_sql
        assert 'col' not in xx.curs.exec_sql
        assert 'chk' in xx.curs.exec_sql
        assert "EXTRA_WHERE" in xx.curs.exec_sql
        assert "RET_COL" in xx.curs.exec_sql

    def test_upsert_insert(self, xx):
        xx.curs.fetchone = lambda : (0, )      # force SELECT COUNT() to return zero/0
        xx.upsert('TABLE_NAME', dict(col=1), dict(chk=3), "EXTRA_WHERE", dict(bind=99))
        assert xx.last_err_msg == ""
        assert 'INSERT ' in xx.curs.exec_sql
        assert 'TABLE_NAME' in xx.curs.exec_sql
        assert 'col' in xx.curs.exec_sql
        assert 'chk' in xx.curs.exec_sql
        assert "EXTRA_WHERE" not in xx.curs.exec_sql

    def test_upsert_err_multiple(self, xx):
        xx.curs.fetchone = lambda : (2, )      # force SELECT COUNT() to return 2 records
        xx.upsert('TABLE_NAME', dict(col=1), dict(chk=3), "EXTRA_WHERE", dict(bind=99), multiple_row_update=False)
        assert "returned 2" in xx.last_err_msg

    def test_upsert_err_negative(self, xx):
        xx.curs.fetchone = lambda : (-3, )      # force SELECT COUNT() to return -3
        xx.upsert('TABLE_NAME', dict(col=1), dict(chk=3), "EXTRA_WHERE", dict(bind=99))
        assert "returned -3" in xx.last_err_msg

    def test_commit(self, xx):
        xx.last_err_msg = "ERROR"
        xx.commit(reset_last_err_msg=True)
        assert xx.last_err_msg == ""

    def test_rollback(self, xx):
        xx.last_err_msg = "ERROR"
        xx.rollback(reset_last_err_msg=True)
        assert xx.last_err_msg == ""

    def test_get_row_count(self, xx):
        assert xx.get_row_count() == 0

    def test_get_row_count_after_fetch(self, xx):
        xx.fetch_value()
        assert xx.get_row_count() == 1

    def test_selected_column_names(self, xx):
        assert xx.selected_column_names() == [col_desc_tuple[0] for col_desc_tuple in XxCurs.description]

    def test_thread_lock_init(self, xx):
        lock = xx.thread_lock_init('TABLE_NAME', dict(chk=99))
        assert isinstance(lock, NamedLocks)
