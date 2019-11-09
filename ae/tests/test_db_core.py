""" ae.db_core unit tests """
from ae.db_core import DbBase


class XxDriver:
    def connect(self, *args, **kwargs):
        return self, args, kwargs


class XxDb(DbBase):
    def connect(self):
        self.conn = XxDriver()


class TestDbBase:
    def test(self):
        pass
