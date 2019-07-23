import datetime

from ae import DATE_ISO, DATE_TIME_ISO
from ae.setting import Setting


class TestSetting:
    def test_init(self):
        s = Setting()
        assert s.value is None

        s = Setting(value='test_val')
        assert isinstance(s.value, str)
        assert s.value == 'test_val'

    def test_bool_values(self):
        bs = 'True'
        s = Setting(value=bs, value_type=bool)
        assert isinstance(s.value, bool)
        assert s.value is True

        bn = 1
        s = Setting(value=bn, value_type=bool)
        assert isinstance(s.value, bool)
        assert s.value is True

    def test_byte_values(self):
        bs = b'TEST'
        s = Setting(value=bs)
        assert isinstance(s.value, bytes)
        assert s.value == bs

        s = Setting(value=bs, value_type=str)
        assert isinstance(s.value, str)
        assert s.value == 'TEST'

    def test_date_values(self):
        ds = '2020-12-24'
        s = Setting(value=ds, value_type=datetime.date)
        assert isinstance(s.value, datetime.date)
        assert s.value == datetime.datetime.strptime(ds, DATE_ISO).date()

        dts = datetime.datetime.now().strftime(DATE_TIME_ISO)
        s = Setting(value=dts, value_type=datetime.datetime)
        assert isinstance(s.value, datetime.datetime)
        assert s.value == datetime.datetime.strptime(dts, DATE_TIME_ISO)