from collections import OrderedDict
from ae_sys_data import DUMMY_FIELD_NAME, FAT_VAL, Field, Value, Record, Records


class TestField:
    def test_typing(self):
        assert isinstance(Field(), Field)

    def xxx_test_repr_eval(self):
        # assert eval(repr(Field())) == Field()
        f = Field()
        assert eval(repr(f)) == f

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


class TestRecord:
    def test_typing(self):
        assert isinstance(Record(), Record)
        assert isinstance(Record(), OrderedDict)
        assert isinstance(Record(), dict)

    def test_repr_eval(self):
        assert eval(repr(Record())) == Record()


class TestStructures:
    def test_field_lookup_standard(self):
        r = Record()
        r.add_field(Field(), 'test')
        print(r)
        assert r['test'].val() == ''

    def test_unpacking(self):
        r = Record()
        r.add_field(Field(), 'test1')
        r.add_field(Field(), 'test2')
        print(r)
        d = dict(**r)
        assert d == r


class TestIdxPath:
    def test_idx_key(self):
        fn1, fn2, sfn1, sfn2, v2, ri2 = 'test1', 'test2', 'sub1', 'sub2', 'test_val', 1
        r = Record()
        r.add_field(Field(), fn1)
        rs = Records()
        rs.append(Record())
        # rs.append(Record(fields=dict(sub1=Field(), sub2=Field().set_val(v2))))
        rs.append(Record(fields={sfn1: Field(), sfn2: Field().set_val(v2)}))
        f = Field().set_value(rs)
        r.add_field(f, fn2)
        print(repr(r))

        assert isinstance(r[fn2].value(ri2, sfn2), Value)
        assert isinstance(r[(fn2, ri2)], Record)
        assert isinstance(r[(fn2, ri2)][sfn2], Field)
        assert isinstance(r[(fn2, ri2, sfn2)], Value)

        assert r[(fn2, ri2)][sfn2].name == sfn2

        assert r.val(fn2, ri2, sfn2) == v2
        assert r[fn2].value(ri2, sfn2).val() == v2
        assert r[(fn2, ri2, sfn2)].val() == v2
        assert r[fn2, ri2, sfn2].val() == v2
        # assert r['test2#1.sub2'].val() == v2


class TestCopy:
    def test_copy_record(self):
        fn1, fn2, sfn1, sfn2, v2, vc2, ri2 = 'test1', 'test2', 'sub1', 'sub2', 'test_val', 'init_val', 1
        r1 = Record()
        r1.add_field(Field(), fn1)
        rs = Records()
        rs.append(Record())
        rs.append(Record(fields={sfn1: Field(), sfn2: Field().set_val(v2)}))
        f = Field().set_value(rs)
        r1.add_field(f, fn2)
        print(r1)
        r2 = Record(fields={(fn2, ri2, sfn2): Field().set_val(vc2)})
        assert r2[(fn2, ri2, sfn2)].val() == vc2
        r3 = r2.copy(to_rec=r1)
        print(r3)
        assert r1 == r3
        assert r1[(fn2, ri2, sfn2)].val() == v2
        assert r3[(fn2, ri2, sfn2)].val() == v2
