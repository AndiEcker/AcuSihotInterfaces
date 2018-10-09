from ae_sys_data import DUMMY_FIELD_NAME, FAT_VAL, Field, Value


class TestField:
    def test_field_val_init(self):
        f = Field()
        assert f.value() == ['']
        assert f.val() == ''
        f.set_value(Value())
        assert f.value() == ['']
        assert f.val() == ''
        f = Field().set_value(Value((None, )))
        assert f.value() == [None]
        assert f.val() is None
        f = Field(**{FAT_VAL: Value((None, ))})
        assert f.value() == [None]
        assert f.val() is None

    def test_field_name_init(self):
        f = Field()
        assert f.name == DUMMY_FIELD_NAME
        test_name = 'test'
        f.set_name(test_name)
        assert f.name == test_name
