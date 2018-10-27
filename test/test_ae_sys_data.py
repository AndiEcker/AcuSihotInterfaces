import pytest

from collections import OrderedDict
from ae_sys_data import aspect_key, aspect_key_system, aspect_key_direction, deeper, field_name_idx_path, \
    DUMMY_FIELD_NAME, FAT_VAL, FAD_FROM, FAD_ONTO, \
    Field, Value, Record, Records
from sys_data_ids import SDI_SH


@pytest.fixture()
def rec_2f_2s():    # two fields and two sub-levels
    r1 = Record()
    r1.add_field(Field(), 'fnA')
    rs = Records()
    rs.append(Record())
    rs.append(Record(fields={'sfnA': Field(), 'sfnB': Field().set_val('sfBv')}))
    f = Field().set_value(rs)
    r1.add_field(f, 'fnB')
    print(r1)
    return r1


class TestHelperMethods:
    def test_aspect_key(self):
        assert aspect_key(FAT_VAL, SDI_SH, FAD_FROM) == FAT_VAL + FAD_FROM + SDI_SH

    def test_aspect_key_system(self):
        assert aspect_key_system(FAT_VAL + FAD_FROM + SDI_SH) == SDI_SH
        assert aspect_key_system(FAT_VAL + FAD_ONTO + SDI_SH) == SDI_SH
        assert aspect_key_system(FAT_VAL + SDI_SH) == SDI_SH

    def test_aspect_key_direction(self):
        assert aspect_key_direction(FAT_VAL + FAD_FROM + SDI_SH) == FAD_FROM
        assert aspect_key_direction(FAT_VAL + FAD_ONTO + SDI_SH) == FAD_ONTO
        assert aspect_key_direction(FAT_VAL + SDI_SH) == ''

    def test_deeper(self):
        assert deeper(999, Record()) == 998
        assert deeper(888, Field()) == 887
        assert deeper(3, Value()) == 2
        assert deeper(3, Records()) == 2
        assert deeper(3, None) == 2
        assert deeper(1, Value()) == 0
        assert deeper(1, None) == 0

        assert deeper(0, Record()) == 0
        assert deeper(0, Field()) == 0
        assert deeper(0, Value()) == 0
        assert deeper(0, Records()) == 0
        assert deeper(0, None) == 0

        assert deeper(-1, Record()) == -1
        assert deeper(-1, Field()) == -1
        assert deeper(-1, Value()) == -1
        assert deeper(-1, Records()) == -1
        assert deeper(-1, None) == -1

        assert deeper(-2, Record()) == -2
        assert deeper(-2, Field()) == -2
        assert deeper(-2, Value()) == 0
        assert deeper(-2, Records()) == -2
        assert deeper(-2, None) == -2

        assert deeper(-3, Record()) == -3
        assert deeper(-3, Field()) == 0
        assert deeper(-3, Value()) == -3
        assert deeper(-3, Records()) == -3
        assert deeper(-3, None) == -3

    def test_field_name_idx_path(self):
        assert field_name_idx_path('field_name1sub_field') == ('field_name', 1, 'sub_field')
        assert field_name_idx_path('FieldName1SubField') == ('FieldName', 1, 'SubField')
        assert field_name_idx_path('3FieldName1SubField') == (3, 'FieldName', 1, 'SubField')
        assert field_name_idx_path('FieldName101SubField') == ('FieldName', 101, 'SubField')
        assert field_name_idx_path('FieldName2SubField3SubSubField') == ('FieldName', 2, 'SubField', 3, 'SubSubField')


class TestField:
    def test_typing(self):
        assert isinstance(Field(), Field)

    def test_repr_eval(self):
        # assert eval(repr(Field())) == Field()
        f = Field()
        r = repr(f)
        e = eval(r)
        print()
        print(e, repr(e))
        print(f, repr(f))
        assert e is not f
        # assert e == f     # this will not be True until the implementation of Field.__eq__()
        assert e.val() == f.val()
        assert e.value() == f.value()

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

    def test_set_val(self):
        f = Field().set_val('f1v')
        assert f.val() == 'f1v'

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

    def test_set_val_fuzzy(self):
        r = Record()
        r.set_val('fAv1', 'fnA', 1, 'sfnA')
        assert r.val('fnA', 1, 'sfnA') == 'fAv1'
        r.set_val('fAvX1', 'fnA', 1, 'sfnA', system='Xx')
        assert r.val('fnA', 1, 'sfnA', system='Xx') == 'fAvX1'
        assert r.val('fnA', 1, 'sfnA') == 'fAvX1'

        r.set_val('fAv', 'fnA', 0, 'sfnA')
        assert r.val('fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 'fnA', 0, 'sfnA', system='Xx')
        assert r.val('fnA', 0, 'sfnA', system='Xx') == 'fAvX'
        assert r.val('fnA', 0, 'sfnA') == 'fAvX'

    def test_set_val_sys_exact(self):
        r = Record()
        r.set_val('fAv', 'fnA', 0, 'sfnA')
        assert r.val('fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 'fnA', 0, 'sfnA', fuzzy_aspect=False, system='Xx')
        assert r.val('fnA', 0, 'sfnA', system='Xx') == 'fAvX'
        assert r.val('fnA', 0, 'sfnA') == 'fAv'

    def test_set_val_sys_converter(self):
        r = Record()
        r.set_val('fAv', 'fnA', 0, 'sfnA')
        assert r.val('fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 'fnA', 0, 'sfnA', system='Xx', converter=lambda f, v: v)
        assert r.val('fnA', 0, 'sfnA', system='Xx') == 'fAvX'
        assert r.val('fnA', 0, 'sfnA') == 'fAv'


class TestRecords:
    def test_typing(self):
        assert isinstance(Records(), Records)
        assert isinstance(Records(), list)

    def test_repr_eval(self):
        assert eval(repr(Records())) == Records()

    def test_set_val_fuzzy(self):
        r = Records()
        r.set_val('fAv', 0, 'fnA', 0, 'sfnA')
        assert r.val(0, 'fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 0, 'fnA', 0, 'sfnA', system='Xx')
        assert r.val(0, 'fnA', 0, 'sfnA', system='Xx') == 'fAvX'
        assert r.val(0, 'fnA', 0, 'sfnA') == 'fAvX'

    def test_set_val_sys_exact(self):
        r = Records()
        r.set_val('fAv', 0, 'fnA', 0, 'sfnA')
        assert r.val(0, 'fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 0, 'fnA', 0, 'sfnA', fuzzy_aspect=False, system='Xx')
        assert r.val(0, 'fnA', 0, 'sfnA', system='Xx') == 'fAvX'
        assert r.val(0, 'fnA', 0, 'sfnA') == 'fAv'

    def test_set_val_sys_converter(self):
        r = Records()
        r.set_val('fAv', 0, 'fnA', 0, 'sfnA')
        assert r.val(0, 'fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 0, 'fnA', 0, 'sfnA', system='Xx', converter=lambda f, v: v)
        assert r.val(0, 'fnA', 0, 'sfnA', system='Xx') == 'fAvX'
        assert r.val(0, 'fnA', 0, 'sfnA') == 'fAv'


class TestStructures:
    def test_field_lookup_standard(self):
        r = Record()
        r.add_field(Field(), 'test')
        print(r)
        assert r['test'].val() == ''

    def test_unpacking(self):
        r = Record()
        r.add_field(Field(), 'testA')
        r.add_field(Field(), 'testB')
        print(r)
        d = dict(**r)
        assert d == r


class TestIdxPath:
    def test_idx_key(self, rec_2f_2s):
        assert isinstance(rec_2f_2s['fnB'], Field)
        assert isinstance(rec_2f_2s['fnB'].value(), Records)
        assert isinstance(rec_2f_2s[('fnB', )].value(), Records)

        assert isinstance(rec_2f_2s[('fnB', 1)], Record)
        assert isinstance(rec_2f_2s[('fnB', )].value(1), Record)

        assert isinstance(rec_2f_2s[('fnB', 1)]['sfnB'], Field)
        assert isinstance(rec_2f_2s[('fnB', 1, 'sfnB')], Field)
        assert isinstance(rec_2f_2s[('fnB', 1, 'sfnB')].value(), Value)

        assert isinstance(rec_2f_2s['fnB'][1]['sfnB'], Field)
        assert isinstance(rec_2f_2s['fnB'][1]['sfnB'].value(), Value)
        assert isinstance(rec_2f_2s['fnB'][1].value('sfnB'), Value)
        assert isinstance(rec_2f_2s['fnB'].value(1, 'sfnB'), Value)
        assert isinstance(rec_2f_2s[('fnB', )].value(1, 'sfnB'), Value)

        assert rec_2f_2s.val('fnB', 1, 'sfnB') == 'sfBv'
        assert rec_2f_2s['fnB'].value(1, 'sfnB').val() == 'sfBv'
        assert rec_2f_2s[('fnB', )].value(1, 'sfnB').val() == 'sfBv'
        assert rec_2f_2s[('fnB', 1)]['sfnB'].val() == 'sfBv'
        assert rec_2f_2s[('fnB', 1, 'sfnB')].val() == 'sfBv'
        assert rec_2f_2s['fnB', 1, 'sfnB'].val() == 'sfBv'
        
        assert rec_2f_2s['fnB1sfnB'].val() == 'sfBv'


class TestCopy:
    def test_shallow_copy_record(self, rec_2f_2s):
        r1c = rec_2f_2s.copy()
        assert rec_2f_2s == r1c
        assert rec_2f_2s is not r1c
        assert rec_2f_2s[('fnB', 1, 'sfnB')].val() == 'sfBv'
        assert r1c[('fnB', 1, 'sfnB')].val() == 'sfBv'

        rec_2f_2s[('fnB', 1, 'sfnB')].set_val('sfBv_new')
        assert rec_2f_2s[('fnB', 1, 'sfnB')].val() == 'sfBv_new'
        assert r1c[('fnB', 1, 'sfnB')].val() == 'sfBv_new'

    def test_deep_copy_record(self, rec_2f_2s):
        r1c = rec_2f_2s.copy(deepness=-1)
        # STRANGE crashing in: assert rec_2f_2s == r1c
        assert id(rec_2f_2s) != id(r1c)
        assert rec_2f_2s is not r1c

        assert id(rec_2f_2s['fnA']) != id(r1c['fnA'])
        assert rec_2f_2s['fnA'] is not r1c['fnA']

        assert rec_2f_2s['fnA'].value() == r1c['fnA'].value()
        assert id(rec_2f_2s['fnA'].value()) != id(r1c['fnA'].value())
        assert rec_2f_2s['fnA'].value() is not r1c['fnA'].value()

        # STRANGE failing until implementation of Field.__eq__: assert rec_2f_2s['fnB'] == r1c['fnB']
        assert id(rec_2f_2s['fnB']) != id(r1c['fnB'])
        assert rec_2f_2s['fnB'] is not r1c['fnB']

        # STRANGE crashing in: assert rec_2f_2s['fnB'][1] == r1c['fnB'][1]
        assert id(rec_2f_2s['fnB'][1]) != id(r1c['fnB'][1])
        assert rec_2f_2s['fnB'][1] is not r1c['fnB'][1]

        assert id(rec_2f_2s['fnB'][1]['sfnB']) != id(r1c['fnB'][1]['sfnB'])
        assert rec_2f_2s['fnB'][1]['sfnB'] is not r1c['fnB'][1]['sfnB']

        assert rec_2f_2s['fnB'][1]['sfnB'].value() == r1c['fnB'][1]['sfnB'].value()

        assert rec_2f_2s[('fnB', 1, 'sfnB')].val() == 'sfBv'
        assert r1c[('fnB', 1, 'sfnB')].val() == 'sfBv'

        rec_2f_2s[('fnB', 1, 'sfnB')].set_val('sfBv_new')
        assert rec_2f_2s[('fnB', 1, 'sfnB')].val() == 'sfBv_new'
        assert r1c[('fnB', 1, 'sfnB')].val() == 'sfBv'

    def test_flat_copy_record(self, rec_2f_2s):
        # test flattening copy into existing record (r2)
        r2 = Record(fields={('fnB', 1, 'sfnB'): Field().set_val('sfBv_old')})
        assert r2[('fnB', 1, 'sfnB')].val() == 'sfBv_old'
        r3 = r2.copy(to_rec=rec_2f_2s)
        print(r3)
        assert rec_2f_2s != r2
        assert rec_2f_2s is not r2
        assert rec_2f_2s == r3
        assert rec_2f_2s is r3
        assert rec_2f_2s[('fnB', 1, 'sfnB')].val() == 'sfBv'
        assert r2[('fnB', 1, 'sfnB')].val() == 'sfBv_old'
        assert r3[('fnB', 1, 'sfnB')].val() == 'sfBv'
