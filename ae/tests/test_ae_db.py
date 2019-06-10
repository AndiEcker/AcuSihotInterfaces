import datetime
from ae.console_app import ConsoleApp
from ae.db import OraDB, PostgresDB, bind_var_prefix

UPDATED_TEST_STRING = 'Updated Test String'
TEST_DATE = datetime.datetime(2018, 1, 21, 22, 33, 44)
TEST_TIME = datetime.time(hour=21, minute=39)
UPDATED_TIME = datetime.time(hour=18, minute=12)
test_db = None
test_table = None


class TestOraDB:
    def test_prepare_connect(self):
        global test_db
        cae = ConsoleApp('0.0', 'test ae db ora')
        test_db = OraDB(dict(User=cae.get_config('acuUser'), Password=cae.get_config('acuPassword'),
                             DSN=cae.get_config('acuDSN')),
                        app_name='test_ae_db-ora', debug_level=cae.get_option('debugLevel'))
        assert not test_db.last_err_msg

    def test_create_table(self):
        global test_table
        test_table = 'UT_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        test_db.execute_sql("CREATE TABLE " + test_table + " (col_int INTEGER, col_vc VARCHAR(69), col_dt DATE)",
                            commit=True)
        assert not test_db.last_err_msg

    def test_insert(self):
        assert not test_db.insert(test_table,
                                  dict(col_int=1, col_vc='test string', col_dt=TEST_DATE),
                                  commit=True)

    def test_update(self):
        assert not test_db.update(test_table, dict(col_vc=UPDATED_TEST_STRING), dict(col_int=1), commit=True)

    def test_upd_if_empty(self):
        assert not test_db.update(test_table, dict(col_vc='WillNotBeChanged'), dict(col_int=1), commit=True,
                                  locked_cols=['col_vc'])

    def test_select(self):
        assert not test_db.select(test_table, cols=['col_int', 'col_vc', 'col_dt'],
                                  where_group_order="col_int >= :" + bind_var_prefix + "xy", bind_vars=dict(xy=0))
        rows = test_db.fetch_all()
        assert rows
        assert rows[0][0] == 1
        assert rows[0][1] == UPDATED_TEST_STRING
        assert rows[0][2] == TEST_DATE

        assert not test_db.select(test_table, cols=['col_int', 'col_vc', 'col_dt'], chk_values=dict(col_int=1))
        rows = test_db.fetch_all()
        assert rows
        assert rows[0][0] == 1
        assert rows[0][1] == UPDATED_TEST_STRING
        assert rows[0][2] == TEST_DATE

    def test_in_clause(self):
        assert not test_db.select(test_table, cols=['col_int', 'col_vc', 'col_dt'],
                                  where_group_order="col_int IN (:" + bind_var_prefix + "yz)",
                                  bind_vars=dict(yz=[0, 1, 2, 3, 4]))
        rows = test_db.fetch_all()
        assert rows
        assert rows[0][0] == 1
        assert rows[0][1] == UPDATED_TEST_STRING
        assert rows[0][2] == TEST_DATE


class TestPostgresDB:
    def test_connect(self):    # test_connect
        global test_db
        cae = ConsoleApp('0.0', 'test ae db pg')
        test_db = PostgresDB(dict(User=cae.get_config('assRootUsr'), Password=cae.get_config('assRootPwd'), DSN='test',
                                  SslArgs=cae.get_config('assSslArgs')),
                             app_name='test_ae_db-pg', debug_level=cae.get_option('debugLevel'))
        assert not test_db.connect()
        assert not test_db.last_err_msg

    def test_create_table(self):
        global test_table
        test_table = 'UT_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        test_db.execute_sql("CREATE TABLE " + test_table + " (col_int INTEGER, col_vc VARCHAR(69), col_dt TIMESTAMP"
                                                           ", col_ti TIME)",
                            commit=True)
        assert not test_db.last_err_msg

    def test_insert(self):
        assert not test_db.insert(test_table,
                                  dict(col_int=1, col_vc='test string', col_dt=TEST_DATE, col_ti=TEST_TIME),
                                  commit=True)

    def test_update_char(self):
        assert not test_db.update(test_table, dict(col_vc=UPDATED_TEST_STRING), dict(col_int=1), commit=True)

    def test_update_time_as_char(self):
        assert not test_db.update(test_table, dict(col_ti='15:19'), dict(col_int=1), commit=True)
        assert not test_db.select(test_table, cols=['col_ti'], chk_values=dict(col_int=1))
        assert test_db.fetch_value() == datetime.time(hour=15, minute=19)

    def test_update_time(self):
        assert not test_db.update(test_table, dict(col_ti=UPDATED_TIME), dict(col_int=1), commit=True)

    def test_upd_if_empty(self):
        assert not test_db.update(test_table, dict(col_vc='WillNotBeChanged'), dict(col_int=1), commit=True,
                                  locked_cols=['col_vc'])

    def test_select(self):
        assert not test_db.select(test_table, cols=['col_int', 'col_vc', 'col_dt', 'col_ti'],
                                  chk_values=dict(col_int=1))
        rows = test_db.fetch_all()
        assert rows
        assert rows[0][0] == 1
        assert rows[0][1] == UPDATED_TEST_STRING
        assert rows[0][2] == TEST_DATE
        assert rows[0][3] == UPDATED_TIME

    def test_in_clause(self):
        assert not test_db.select(test_table, cols=['col_int', 'col_vc', 'col_dt', 'col_ti'],
                                  where_group_order="col_int IN (:" + bind_var_prefix + "yz)",
                                  bind_vars=dict(yz=[0, 1, 2, 3, 4]))
        rows = test_db.fetch_all()
        assert rows
        assert rows[0][0] == 1
        assert rows[0][1] == UPDATED_TEST_STRING
        assert rows[0][2] == TEST_DATE
        assert rows[0][3] == UPDATED_TIME
