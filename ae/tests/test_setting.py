import pytest
import datetime

from ae.core import DATE_TIME_ISO, DATE_ISO
from ae.literal import Literal


class TestLiteral:
    def test_init(self):
        s = Literal()
        assert s.value is None

        s = Literal(literal='test_val')
        assert isinstance(s.value, str)
        assert s.value == 'test_val'

    def test_bool_values(self):
        bs = 'True'
        s = Literal(literal=bs, value_type=bool)
        assert isinstance(s.value, bool)
        assert s.value is True

        bn = 1
        s = Literal(literal=bn, value_type=bool)
        assert isinstance(s.value, bool)
        assert s.value is True

    def test_byte_values(self):
        bs = b'TEST'
        s = Literal(literal=bs)
        assert isinstance(s.value, bytes)
        assert s.value == bs

        s = Literal(literal=bs, value_type=str)
        assert isinstance(s.value, str)
        assert s.value == 'TEST'

    def test_date_values(self):
        ds = '2020-12-24'
        s = Literal(literal=ds, value_type=datetime.date)
        assert isinstance(s.value, datetime.date)
        assert s.value == datetime.datetime.strptime(ds, DATE_ISO).date()

        dts = datetime.datetime.now().strftime(DATE_TIME_ISO)
        s = Literal(literal=dts, value_type=datetime.datetime)
        assert isinstance(s.value, datetime.datetime)
        assert s.value == datetime.datetime.strptime(dts, DATE_TIME_ISO)

    def test_value_exception(self):
        ds = '2020-66-99'
        s = Literal(literal=ds, value_type=datetime.date)
        with pytest.raises(ValueError):
            _ = s.value
