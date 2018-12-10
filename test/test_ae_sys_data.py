import pytest

from collections import OrderedDict
from ae_sys_data import aspect_key, aspect_key_system, aspect_key_direction, deeper, \
    field_name_idx_path, field_names_idx_paths, idx_path_field_name, \
    Value, Values, Record, Records, _Field, current_index, init_current_index, use_current_index, set_current_index, \
    FAT_VAL, FAD_FROM, FAD_ONTO, FAT_REC, FAT_RCX, ACTION_DELETE, FAT_IDX, FAT_CNV
from sys_data_ids import SDI_SH


@pytest.fixture()
def rec_2f_2s_incomplete():     # two fields and only partly complete two sub-levels
    r1 = Record(fields=dict(fnA='', fnB1sfnA='', fnB1sfnB='sfB2v'))
    print(r1)
    return r1


@pytest.fixture()
def rec_2f_2s_complete():       # two fields and only partly complete two sub-levels
    r1 = Record(fields=(('fnA', ''),
                        ('fnB0sfnA', 'sfA1v'), ('fnB0sfnB', 'sfB1v'),
                        ('fnB1sfnA', 'sfA2v'), ('fnB1sfnB', 'sfB2v')))
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
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test', )})
        assert deeper(999, Record()) == 998
        assert deeper(888, f) == 887
        assert deeper(3, Value()) == 2
        assert deeper(3, Records()) == 2
        assert deeper(3, None) == 2
        assert deeper(1, Value()) == 0
        assert deeper(1, None) == 0

        assert deeper(0, Record()) == 0
        assert deeper(0, f) == 0
        assert deeper(0, Value()) == 0
        assert deeper(0, Records()) == 0
        assert deeper(0, None) == 0

        assert deeper(-1, Record()) == -1
        assert deeper(-1, f) == -1
        assert deeper(-1, Value()) == -1
        assert deeper(-1, Records()) == -1
        assert deeper(-1, None) == -1

        assert deeper(-2, Record()) == -2
        assert deeper(-2, f) == -2
        assert deeper(-2, Value()) == 0
        assert deeper(-2, Records()) == -2
        assert deeper(-2, None) == -2

        assert deeper(-3, Record()) == -3
        assert deeper(-3, f) == 0
        assert deeper(-3, Value()) == -3
        assert deeper(-3, Records()) == -3
        assert deeper(-3, None) == -3

    def test_field_name_idx_path(self):
        assert not field_name_idx_path('test')
        assert field_name_idx_path('test') == tuple()
        assert not field_name_idx_path('TestTest')
        assert field_name_idx_path('TestTest') == tuple()
        assert not field_name_idx_path('test_Test')
        assert field_name_idx_path('test_Test') == tuple()
        assert field_name_idx_path('field_name1sub_field') == ('field_name', 1, 'sub_field')
        assert field_name_idx_path('FieldName1SubField') == ('FieldName', 1, 'SubField')
        assert field_name_idx_path('3FieldName1SubField') == (3, 'FieldName', 1, 'SubField')
        assert field_name_idx_path('FieldName101SubField') == ('FieldName', 101, 'SubField')
        assert field_name_idx_path('FieldName2SubField3SubSubField') == ('FieldName', 2, 'SubField', 3, 'SubSubField')

        assert not field_name_idx_path(3)

        assert not field_name_idx_path('3')
        assert field_name_idx_path('Test2') == ('Test', 2)
        assert field_name_idx_path('2Test2') == (2, 'Test', 2)
        assert field_name_idx_path('3Test') == (3, 'Test')

    def test_field_name_idx_path_sep(self):
        assert field_name_idx_path('Test.test') == ('Test', 'test')
        assert field_name_idx_path('.Test.test.') == ('Test', 'test')

        assert field_name_idx_path('Test3.test') == ('Test', 3, 'test')
        assert field_name_idx_path('Test33.test') == ('Test', 33, 'test')

        assert field_name_idx_path('Test.3.test') == ('Test', 3, 'test')
        assert field_name_idx_path('Test.33.test') == ('Test', 33, 'test')

    def test_field_name_idx_path_ret_root_fields(self):
        assert field_name_idx_path('test', return_root_fields=True) == ('test', )
        assert field_name_idx_path('TestTest', return_root_fields=True)
        assert field_name_idx_path('TestTest', return_root_fields=True) == ('TestTest', )
        assert field_name_idx_path('test_Test', return_root_fields=True) == ('test_Test', )
        assert field_name_idx_path('field_name1sub_field', return_root_fields=True) == ('field_name', 1, 'sub_field')
        assert field_name_idx_path('FieldName1SubField', return_root_fields=True) == ('FieldName', 1, 'SubField')
        assert field_name_idx_path('3FieldName1SubField', return_root_fields=True) == (3, 'FieldName', 1, 'SubField')
        assert field_name_idx_path('FieldName101SubField', return_root_fields=True) == ('FieldName', 101, 'SubField')
        assert field_name_idx_path('FieldName2SubField3SubSubField', return_root_fields=True) \
            == ('FieldName', 2, 'SubField', 3, 'SubSubField')

        assert field_name_idx_path(3, return_root_fields=True) == (3, )

        assert field_name_idx_path('3', return_root_fields=True) == ('3', )
        assert field_name_idx_path('Test2', return_root_fields=True) == ('Test', 2)
        assert field_name_idx_path('2Test2', return_root_fields=True) == (2, 'Test', 2)
        assert field_name_idx_path('3Test', return_root_fields=True) == (3, 'Test')

    def test_field_names_idx_paths(self):
        assert field_names_idx_paths(['3Test', ('fn', 0, 'sfn'), 9]) == [(3, 'Test'), ('fn', 0, 'sfn'), (9, )]

    def test_idx_path_field_name(self):
        assert idx_path_field_name(('test', 'TEST')) == 'test.TEST'
        assert idx_path_field_name((3, 'tst')) == '3tst'
        assert idx_path_field_name(('test3no-sub', )) == 'test3no-sub'
        assert idx_path_field_name(('test', 33)) == 'test33'

        assert idx_path_field_name(('test', 'TEST'), add_sep=True) == 'test.TEST'
        assert idx_path_field_name((3, 'tst'), add_sep=True) == '3.tst'
        assert idx_path_field_name(('test3no-sub',), add_sep=True) == 'test3no-sub'
        assert idx_path_field_name(('test', 33), add_sep=True) == 'test.33'

    def test_init_use_current_index(self):
        r = Record()
        init_current_index(r, ('fnA', ), None)
        assert current_index(r) == 'fnA'

        r.set_val(123, 'fnB', 1, 'fnBA')
        assert current_index(r) == 'fnA'   # set_val() never changes idx, only init on 1st call (if current_idx is None)
        set_current_index(r, idx='fnB')
        assert current_index(r) == 'fnB'
        assert current_index(r.value('fnB')) == 1
        assert r.value('fnB').idx_min == 1
        assert r.value('fnB').idx_max == 1
        assert current_index(r.value('fnB', 1)) == 'fnBA'

        r.set_val(456, 'fnB', 0, 'fnBA')
        assert current_index(r) == 'fnB'
        assert current_index(r.value('fnB')) == 1
        set_current_index(r.value('fnB'), idx=0)
        assert current_index(r.value('fnB')) == 0
        assert r.value('fnB').idx_min == 0
        assert r.value('fnB').idx_max == 1
        assert current_index(r.value('fnB', 1)) == 'fnBA'

        assert r.val('fnB', 1, 'fnBA') == 123
        assert r.val('fnB', 0, 'fnBA') == 456
        assert r.val('fnB', 1, 'fnBA', use_curr_idx=Value((1, ))) == 456
        assert r.val('fnB', 0, 'fnBA', use_curr_idx=Value((1, ))) == 456

        assert use_current_index(r, ('fnB', 0, 'fnBA'), Value((1, ))) == ('fnB', 0, 'fnBA')

    def test_set_current_index(self):
        r = Records()
        set_current_index(r, idx=2)
        assert current_index(r) == 2
        set_current_index(r, add=-1)
        assert current_index(r) == 1

        r = Record()
        set_current_index(r, idx='fnX')
        assert current_index(r) == 'fnX'


class TestValue:
    def test_typing(self):
        assert isinstance(Value(), list)

    def test_repr_eval(self):
        v = Value()
        r = repr(v)
        e = eval(r)
        assert e is not v
        assert e == v
        assert e[-1] == v.val()

    def test_val_init(self):
        v = Value()
        assert v.value() == []
        assert v.val() == ''
        with pytest.raises(AssertionError):
            v.set_val(Value().set_val('tvX'))
        v.set_val('tvA')
        assert v.value() == ['tvA']
        assert v.val() == 'tvA'
        v.clear_vals()
        assert v.value() == []
        assert v.val() == ''

    def test_val_get(self):
        v = Value()
        assert v.val() == ''
        assert v.val('test') is None
        assert v.val(12, 'sub_field') is None
        assert v.val('field', 12, 'sub_field') is None

        assert v.val(0) == ''
        assert v.val(-1) == ''
        v.append('test_val')
        assert v.val(0) == 'test_val'
        assert v.val(-1) == 'test_val'

    def test_node_child(self):
        v = Value()
        assert v.node_child(('test',)) is None
        assert v.node_child(('test', 3, 'subField')) is None
        assert v.node_child((2, 'test',)) is None


class TestField:
    def test_typing(self):
        assert isinstance(_Field(**{FAT_REC: Record(), FAT_RCX: ('test', )}), _Field)

    def test_field_val_init(self):
        r = Record()
        f = _Field(root_rec=r, root_idx=('test',))
        assert f.value() == []
        assert f.val() == ''
        f.set_value(Value(), root_rec=r, root_idx=('testB', ))
        assert f.value() == []
        assert f.val() == ''
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test',)}).set_value(Value((None,)))
        assert f.value() == [None]
        assert f.val() is None
        f = _Field(root_rec=Record(), root_idx=('test',)).set_val(None)
        assert f.value() == [None]
        assert f.val() is None

    def test_set_val(self):
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test',)}).set_val('f1v')
        assert f.val() == 'f1v'

    def test_val_get(self):
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test',)})
        assert f.val() == ''
        assert f.val('test') is None
        assert f.val(12, 'sub_field') is None
        assert f.val('sub_field', 12, '2nd_sub_field') is None

    def test_field_name_init(self):
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('init',)})
        assert f.name() == 'init'
        test_name = 'test'
        f.set_name(test_name)
        assert f.name() == test_name


class TestRecord:
    def test_typing(self):
        assert isinstance(Record(), Record)
        assert isinstance(Record(), OrderedDict)
        assert isinstance(Record(), dict)

    def test_repr_eval(self):
        assert eval(repr(Record())) == Record()

    def test_field_lookup_standard(self):
        r = Record(fields=dict(test=''))
        print(r)
        assert r['test'].val() == ''

    def test_unpacking(self):
        r = Record(fields=dict(testA='', testB=''))
        print(r)
        d = dict(**r)
        assert d == r

    def test_set_val_flex_sys(self):
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

    def test_set_val_exact_sys(self):
        r = Record()
        r.set_val('fAv', 'fnA', 0, 'sfnA')
        assert r.val('fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 'fnA', 0, 'sfnA', flex_sys_dir=False, system='Xx')
        assert r.val('fnA', 0, 'sfnA', system='Xx') == 'fAvX'
        assert r.val('fnA', 0, 'sfnA') == 'fAv'

    def test_set_val_sys_converter(self):
        r = Record()
        r.set_val('fAv', 'fnA', 0, 'sfnA')
        assert r.val('fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 'fnA', 0, 'sfnA', system='Xx', converter=lambda f, v: v)
        assert r.val('fnA', 0, 'sfnA', system='Xx') == 'fAvX'
        assert r.val('fnA', 0, 'sfnA') == 'fAv'

    def test_val_use_curr_idx(self):
        r = Record()
        r.set_val('fAv1', 'fnA', 1, 'sfnA')
        f = r[('fnA', 1, 'sfnA')]
        assert r.val('fnA', 1, 'sfnA') == 'fAv1'
        assert r.val('fnA', 0, 'sfnA') is None
        assert r.val('fnA', 0, 'sfnA', use_curr_idx=Value((1, ))) == 'fAv1'
        assert r.val('fnA', 2, 'sfnA') is None
        assert r.val('fnA', 2, 'sfnA', use_curr_idx=Value((1, ))) == 'fAv1'
        assert f.val() == 'fAv1'

        recs = f.parent(value_types=(Records,))
        assert recs is not None
        set_current_index(recs, idx=2)
        assert r.val('fnA', 1, 'sfnA', use_curr_idx=Value((1, ))) is None
        set_current_index(recs, idx=1)
        assert r.val('fnA', 2, 'sfnA', use_curr_idx=Value((1, ))) == 'fAv1'

    def test_set_val_use_curr_idx(self):
        r = Record()
        r.set_val('fAv1', 'fnA', 1, 'sfnA')
        assert r.val('fnA', 1, 'sfnA') == 'fAv1'

        r.set_val('fAv0', 'fnA', 0, 'sfnA', use_curr_idx=Value((1, )))
        assert r.val('fnA', 0, 'sfnA') is None
        assert r.val('fnA', 1, 'sfnA') == 'fAv0'

        r.set_val('fAv2', 'fnA', 2, 'sfnA', use_curr_idx=Value((1, )))
        assert r.val('fnA', 2, 'sfnA') is None
        assert r.val('fnA', 1, 'sfnA') == 'fAv2'

    def test_set_val_root_rec_idx(self):
        r = Record()
        r.set_val('fAv0', 'fnA')
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA',)

        r = Record()
        r.set_node_child('fBv1', 'fnB', 0, 'sfnB')
        assert r['fnB'].root_rec() is r
        assert r['fnB'].root_idx() == ('fnB', )
        assert r[('fnB', 0, 'sfnB')].root_rec() is r
        assert r[('fnB', 0, 'sfnB')].root_idx() == ('fnB', 0, 'sfnB')

        r = Record()
        r.set_val('fAv1', 'fnA', 1, 'sfnA')
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA', )
        assert r[('fnA', 1, 'sfnA')].root_rec() is r
        assert r[('fnA', 1, 'sfnA')].root_idx() == ('fnA', 1, 'sfnA')

        r = Record()
        r.set_val('fAv3', 'fnA', root_rec=r)
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA', )

        r = Record()
        r.set_val('fAv2', 'fnA', 1, 'sfnA', root_rec=r)
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA', )
        assert r[('fnA', 1, 'sfnA')].root_rec() is r    # .. but the sub-field has it
        assert r[('fnA', 1, 'sfnA')].root_idx() == ('fnA', 1, 'sfnA')

        r = Record()
        r.set_node_child('fBv1', 'fnB', 0, 'sfnB')
        assert r['fnB'].root_rec() is r
        assert r['fnB'].root_idx() == ('fnB', )
        assert r[('fnB', 0, 'sfnB')].root_rec() is r
        assert r[('fnB', 0, 'sfnB')].root_idx() == ('fnB', 0, 'sfnB')

        r = Record()
        r.set_val('fAv3', 'fnA', 1, 'sfnA')
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA', )
        assert r[('fnA', 1, 'sfnA')].root_rec() is r
        assert r[('fnA', 1, 'sfnA')].root_idx() == ('fnA', 1, 'sfnA')

        r = Record()
        r.set_node_child('fBv3', 'fnB', 0, 'sfnB', root_rec=r)
        assert r['fnB'].root_rec() is r
        assert r['fnB'].root_idx() == ('fnB', )
        assert r[('fnB', 0, 'sfnB')].root_rec() is r
        assert r[('fnB', 0, 'sfnB')].root_idx() == ('fnB', 0, 'sfnB')

    def test_val_get(self, rec_2f_2s_incomplete):
        r = Record()
        assert r.val() == OrderedDict()
        assert r.val('test') is None
        assert r.val(12, 'sub_field') is None
        assert r.val('sub_field', 12, '2nd_sub_field') is None

        r = rec_2f_2s_incomplete
        assert type(r.val()) == OrderedDict
        assert r.val('fnA') == ''
        assert r.val('fnA', 12) is None
        assert r.val('unknown_field_name') is None
        assert type(r.val('fnB')) == list
        assert len(r.val('fnB')) == 2
        assert type(r.val('fnB', 0)) == OrderedDict
        assert type(r.val('fnB', 1)) == OrderedDict
        assert r.val('fnB', 0, 'sfnA') is None
        assert r.val('fnB', 0, 'sfnB') is None
        assert r.val('fnB', 1, 'sfnA') == ''
        assert r.val('fnB', 1, 'sfnB') == 'sfB2v'

    def test_add_fields(self):
        r = Record()
        r.add_fields(dict(fnA=33, fnB=66))
        assert r.val('fnA') == 33
        assert r['fnB'].val() == 66

        r1 = r
        r = Record()
        r.add_fields(r1)
        assert r.val('fnA') == 33
        assert r['fnB'].val() == 66

        r1 = r
        r = Record()
        r.add_fields(r1.val())
        assert r.val('fnA') == 33
        assert r['fnB'].val() == 66

        r = Record()
        r.add_fields([('fnA', 33), ('fnB', 66)])
        assert r.val('fnA') == 33
        assert r['fnB'].val() == 66

    def test_set_node_child(self):
        r = Record()
        r.set_node_child(12, 'fnA', protect=True)
        assert r.val('fnA') == 12
        r.set_node_child(33, 'fnA')
        assert r.val('fnA') == 33
        r.set_node_child('sfA2v', 'fnA', 2, 'sfnA', protect=False)
        assert r.val('fnA', 2, 'sfnA') == 'sfA2v'

        r[('fnA', 2, 'sfnA')] = 66
        assert r.val('fnA', 2, 'sfnA') == 66
        r['fnA2sfnA'] = 99
        assert r.val('fnA', 2, 'sfnA') == 99
        r.set_node_child('test_value', 'fnA2sfnA')
        assert r.val('fnA2sfnA') == 'test_value'
        assert r.val('fnA', 2, 'sfnA') == 'test_value'

        r.set_node_child(69, 'fnA', 2, 'sfnA')
        assert r.val('fnA', 2, 'sfnA') == 69

        r.set_node_child('flat_fld_val', 'fnB')
        r.set_node_child(11, 'fnB', 0, 'sfnB')
        assert r.val('fnB', 0, 'sfnB') == 11

        r.set_node_child('flat_fld_val', 'fnB')

        with pytest.raises(AssertionError):
            r.set_node_child(969, 'fnB', 0, 'sfnB', protect=True)
        assert r.val('fnB') == 'flat_fld_val'

        with pytest.raises(AssertionError):
            r.set_node_child(999, 'fnB', 0, 'sfnB', protect=True)
        assert r.val('fnB') == 'flat_fld_val'

        r = Record()
        r.set_node_child(dict(a=1, b=2), 'ab')
        assert isinstance(r.val('ab'), dict)
        assert not isinstance(r.val('ab'), Record)
        assert r.val('ab').get('a') == 1
        assert r.val('ab').get('b') == 2

        r.set_node_child(dict(x=3, y=4, z=dict(sez="leaf")), 'cd', 'e')
        assert isinstance(r.value('cd'), Record)
        assert isinstance(r.value('cd', 'e'), Value)
        assert isinstance(r.val('cd', 'e'), dict)
        assert not isinstance(r.val('cd', 'e'), Record)
        assert r.val('cd', 'e').get('z').get('sez') == "leaf"

    def test_set_node_child_to_rec(self):
        rp = Record(fields=dict(a=1, b=2))
        rc = Record(fields=dict(ba=21, bb=22))
        rp.set_node_child(rc, 'b')
        assert isinstance(rp.value('b'), Record)
        assert rp.val('b', 'ba') == 21
        assert rp.val('b', 'bb') == 22

        rp = Record(fields=dict(a=1, b=2))
        rc = Record(fields=dict(ba=321, bb=322))
        rp.set_node_child(rc, 'b', 3)
        assert isinstance(rp.value('b'), Records)
        assert rp.val('b', 3, 'ba') == 321
        assert rp.val('b', 3, 'bb') == 322

    def test_set_field_use_curr_idx(self):
        r = Record()
        r.set_node_child('fAv1', 'fnA', 1, 'sfnA')
        assert r.val('fnA', 1, 'sfnA') == 'fAv1'

        r.set_node_child('fAv0', 'fnA', 0, 'sfnA', use_curr_idx=Value((1,)))
        assert r.val('fnA', 0, 'sfnA') is None
        assert r.val('fnA', 1, 'sfnA') == 'fAv0'

        r.set_node_child('fAv2', 'fnA', 2, 'sfnA', use_curr_idx=Value((1,)))
        assert r.val('fnA', 2, 'sfnA') is None
        assert r.val('fnA', 1, 'sfnA') == 'fAv2'

        r.set_node_child(69, 'fnA', 0, 'sfnB', use_curr_idx=Value((1,)))
        assert r.val('fnA', 0, 'sfnB') is None
        assert r.val('fnA', 1, 'sfnB') == 69

        r.set_node_child('fAv3', 'fnA', 2, 'sfnB', use_curr_idx=Value((1,)))
        assert r.val('fnA', 2, 'sfnB') is None
        assert r.val('fnA', 1, 'sfnB') == 'fAv3'

    def test_fields_iter(self):
        r = Record()
        r.set_node_child(12, 'fnA')
        assert len(r) == 1
        for k in r:
            assert k == 'fnA'
        for i, k in enumerate(r):
            assert k == 'fnA'
            assert i == 0
        for k, v in r.items():
            assert k == 'fnA'
            assert v.name() == 'fnA'
            assert v.val() == 12
        for i, (k, v) in enumerate(r.items()):
            assert k == 'fnA'
            assert v.name() == 'fnA'
            assert v.val() == 12
            assert i == 0

    def test_missing_field(self):
        r = Record()
        with pytest.raises(KeyError):
            _ = r['fnA']
        r.set_node_child(12, 'fnA')
        assert r['fnA'].val() == 12
        with pytest.raises(KeyError):
            _ = r['fnMissing']

    def test_node_child(self, rec_2f_2s_incomplete):
        r = Record(system='Xx', direction='From')
        assert r.node_child(('test',)) is None

        r = rec_2f_2s_incomplete
        assert r.node_child(('fnA',)).val() == ''
        idx_path = ('fnB', 1, 'sfnB')
        assert r.node_child(idx_path).val() == 'sfB2v'

        r[('fnB', 1, 'sfnB')] = 11
        r[('fnB', 1, 'sfnB')].set_val(33, system='Xx', direction='From', flex_sys_dir=False)\
            .set_name('sfnB_From_Xx', system='Xx', direction='From')
        assert r[('fnB', 1, 'sfnB')].val() == 11
        assert r[('fnB', 1, 'sfnB')].val(system='Xx') == 33
        assert r[('fnB', 1, 'sfnB')].val(system='Xx', direction='From') == 33
        assert r.node_child(('fnB', 1, 'sfnB')).val(system='Xx') == 33
        assert r.node_child(('fnB', 1, 'sfnB')).val(system='Xx', direction=None) == 33
        assert r.node_child('fnB1sfnB').val(system='Xx') == 33
        assert r.node_child('fnB1sfnB_From_Xx').val(system='Xx') == 33
        assert r.node_child('fnB1sfnB_From_Xx').val(system='Xx') == 33

        # replace Records/Record children with Record child in fnB
        r.set_env(system='Xx')
        sr = Record(dict(sfnB_rec=66))
        # with pytest.raises(AssertionError):
        #     r['fnB'].set_value(sr, system='Xx')
        with pytest.raises(AssertionError):
            r['fnB'].set_value(sr, protect=True)
        r['fnB'].set_value(sr)
        assert r.node_child(('fnB', 'sfnB_rec')).val(system='Xx') == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system='Xx', direction=None) == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system='Xx', direction='') == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system='Xx', direction=FAD_FROM) == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system='Xx', direction=FAD_ONTO) == 66
        with pytest.raises(AssertionError):
            assert r.node_child(('fnB', 'sfnB_rec')).val(system='Xx', direction='test') == 66

        r.set_env(system='Xx', direction='From')
        assert r.node_child(('fnB', 'sfnB_rec')).val(system='Xx') == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system='Xx', direction=None) == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system='Xx', direction='') == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system='Xx', direction=FAD_FROM) == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system='Xx', direction=FAD_ONTO) == 66
        with pytest.raises(AssertionError):
            assert r.node_child(('fnB', 'sfnB_rec')).val(system='Xx', direction='test') == 66

    def test_copy(self):
        r = Record()
        assert r.copy() == r
        assert r.copy() is not r

        r.add_fields(dict(fnA=33, fnB=66, fnC0sfnC=99))
        assert len(r) == 3
        assert r.copy() == r
        assert r.copy() is not r

        r2 = r.copy(filter_func=lambda f: f.name() == 'fnB')
        assert len(r2) == 1
        assert r2.val('fnB') == 66

        r2 = r.copy(fields_patches=dict(fnB={aspect_key(FAT_VAL): Value((99, ))}))
        assert len(r2) == 3
        assert r2.val('fnB') == 99

    def test_pull(self):
        r = Record(fields=dict(fnA=-1))
        r['fnA'].set_name('fnA_systemXx', system='Xx', direction=FAD_FROM)
        r['fnA'].set_val('33', system='Xx', direction=FAD_FROM, converter=lambda fld, val: int(val))
        r.pull('Xx')
        assert r.val('fnA') == 33
        assert r['fnA'].val() == 33
        assert r['fnA'].val(system='Xx', direction=FAD_FROM) == '33'
        assert r['fnA'].val(system='Xx') == '33'

    def test_push(self):
        r = Record(fields=dict(fnA=33))
        r['fnA'].set_name('fnA_systemXx', system='Xx', direction=FAD_ONTO)
        r['fnA'].set_converter(lambda fld, val: str(val), system='Xx', direction=FAD_ONTO)
        r.push('Xx')
        assert r.val('fnA') == 33
        assert r['fnA'].val() == 33
        assert r['fnA'].val(system='Xx', direction=FAD_ONTO) == '33'
        assert r['fnA'].val(system='Xx') == '33'

    def test_set_env(self):
        r = Record().set_env(system='Xx', direction=FAD_ONTO, action='ACTION')
        assert r.system == 'Xx'
        assert r.direction == FAD_ONTO
        assert r.action == 'ACTION'
    
    def test_add_system_fields(self):
        SEP = '.'
        d = (
            ('F_CNT', 'Cnt'),
            ('F/', ),
            ('F' + SEP + 'NAME', ('fn', 0, 'Surname'), lambda f: "Adult " + str(f.crx())
                if f.crx() is None or f.crx() < f.rfv('Cnt') else "Child " + str(f.crx() - f.rfv('Cnt') + 1),
             lambda f: f.ina(ACTION_DELETE) or not f.val() or f.rfv('F', 0, 'Id')),
            ('F' + SEP + 'NAME2', ('fn', 0, 'Forename')),
            ('AUTO-GENERATED', None, '1',
             lambda f: f.ina(ACTION_DELETE) or (f.rfv('ResAdults') <= 2 and f.rfv('fn', f.crx(), 'Id'))),
            ('F' + SEP + 'MATCHCODE', ('fn', 0, 'Id')),
            ('ROOM-SEQ', None, '0',
             lambda f: f.ina(ACTION_DELETE)),
            ('PERS-SEQ', None, None,
             lambda f: f.ina(ACTION_DELETE),
             lambda f: (str(f.crx()))),
            ('F' + SEP + 'DOB', ('fn', 0, 'DOB'), None,
             lambda f: f.ina(ACTION_DELETE) or not f.val()),
            ('/F', None, None,
             lambda f: f.ina(ACTION_DELETE) or f.rfv('Cnt') <= 0),
        )
        sys_r = Record(system=SDI_SH, direction=FAD_ONTO)
        sys_r.add_system_fields(d)
        assert sys_r.val('Cnt') == ''

        data_r = Record(fields=dict(Cnt=2, fn0Forename='John'))
        sys_r.clear_vals()
        for k in data_r.leaf_indexes():
            if k[0] in sys_r:
                sys_r.set_val(data_r[k].val(), *k, root_rec=data_r)
        sys_r.push(SDI_SH)
        assert sys_r.val('Cnt') == 2
        assert data_r.val('fn', 0, 'Surname') is None
        assert sys_r.val('fn', 0, 'Surname') == 'Adult 0'
        assert sys_r.val('fn', 0, 'Surname', system=SDI_SH, direction=FAD_ONTO) == 'Adult 0'

        assert data_r.val('fn', 0, 'Forename') == 'John'
        assert sys_r.val('fn', 0, 'Forename') == 'John'
        assert sys_r.val('fn', 0, 'Forename', system=SDI_SH, direction=FAD_ONTO) == 'John'

        sys_r.set_val(0, 'Cnt')
        assert sys_r.val('fn', 0, 'Surname', system=SDI_SH, direction=FAD_ONTO) == 'Child 1'

        sys_r.set_val('Johnson', 'fn', 0, 'Surname')
        assert sys_r.val('fn', 0, 'Surname') == 'Child 1'   # != changed sys val because of flex_sys_dir=True
        sys_r.set_val('Johnson', 'fn', 0, 'Surname', flex_sys_dir=False)
        assert sys_r.val('fn', 0, 'Surname') == 'Johnson'   # .. now we are having a separate sys val
        sys_r['fn0Surname'].del_aspect(FAT_VAL, system=SDI_SH, direction=FAD_ONTO)
        assert sys_r.val('fn', 0, 'Surname') == 'Child 1'   # .. after delete of sys val: getting main val/calculator

        sys_r.set_val(123456, 'fn0Id')
        sys_r.push(SDI_SH)


class TestRecords:
    def test_typing(self):
        assert isinstance(Records(), Records)
        assert isinstance(Records(), list)

    def test_repr_eval(self):
        _ = Values      # added for to remove Pycharm warning
        rec_str = repr(Records())
        assert eval(rec_str) == Records()

    def test_set_val_flex_sys(self):
        r = Records()
        r.set_val('fAv', 0, 'fnA', 0, 'sfnA')
        assert r.val(0, 'fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 0, 'fnA', 0, 'sfnA', system='Xx')
        assert r.val(0, 'fnA', 0, 'sfnA', system='Xx') == 'fAvX'
        assert r.val(0, 'fnA', 0, 'sfnA') == 'fAvX'

    def test_set_val_exact_sys(self):
        r = Records()
        r.set_val('fAv', 0, 'fnA', 0, 'sfnA')
        assert r.val(0, 'fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 0, 'fnA', 0, 'sfnA', flex_sys_dir=False, system='Xx')
        assert r.val(0, 'fnA', 0, 'sfnA', system='Xx') == 'fAvX'
        assert r.val(0, 'fnA', 0, 'sfnA') == 'fAv'

    def test_set_val_sys_converter(self):
        r = Records()
        r.set_val('fAv', 0, 'fnA', 0, 'sfnA')
        assert r.val(0, 'fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 0, 'fnA', 0, 'sfnA', system='Xx', converter=lambda f, v: v)
        assert r.val(0, 'fnA', 0, 'sfnA', system='Xx') == 'fAvX'
        assert r.val(0, 'fnA', 0, 'sfnA') == 'fAv'

    def test_val_get(self):
        r = Records()
        assert r.val() == list()
        assert r.val(0) is None
        assert r.val('test') is None
        assert r.val(12, 'sub_field') is None
        assert r.val('sub_field', 12, '2nd_sub_field') is None

        r.append(Record())
        assert r.val(0) == OrderedDict()

    def test_set_field(self):
        r = Records()
        r.set_node_child(12, 4, 'fnA', protect=True)
        assert r.val(4, 'fnA') == 12
        r.set_node_child(33, 4, 'fnA')
        assert r.val(4, 'fnA') == 33

        r[2].set_val(99, 'sfnA')
        assert r.val(2, 'sfnA') == 99

    def test_get_value(self):
        r = Records()
        assert not r.value()
        assert isinstance(r.value(), list)
        assert isinstance(r.value(), Records)
        r.append(Record())
        assert r.value()
        assert r.value() == Records((Record(), ))
        assert len(r.value()) == 1
        r.set_node_child(33, 3, 'fnA')
        assert len(r.value()) == 4
        assert r.value(3, 'fnA') == Value((33, ))

    def test_set_value(self):
        r = Records()
        r.set_node_child(33, 3, 'fnA')
        assert r.value(3, 'fnA').val() == 33
        r.set_value(Value().set_val(66), 3, 'fnA')
        assert r.value(3, 'fnA').val() == 66

    def test_clear_vals(self):
        r = Records()
        r.set_node_child(33, 3, 'fnA')
        assert len(r) == 4
        r.clear_vals()
        assert r.value(3, 'fnA').val() == ''
        assert len(r) == 4

    def test_append_sub_record(self):
        r1 = Record(fields=dict(fnA=1, fnB0sfnA=2, fnB0sfnB=3))

        r1.value('fnB').append_record(root_rec=r1, root_idx=('fnB', ))
        assert r1.val('fnB', 1, 'sfnA') == 2
        assert r1.val('fnB', 1, 'sfnB') == 3

        r1.node_child('fnB').append_record(root_rec=r1, root_idx=('fnB', ))
        assert r1.val('fnB', 2, 'sfnA') == 2
        assert r1.val('fnB', 2, 'sfnB') == 3

    def test_append_sub_record_to_foreign_records(self):
        r1 = Record(fields=dict(fnA=1, fnB0sfnA=2, fnB0sfnB=3))
        r2 = Record(fields=dict(fnA=7, fnB1sfnA=8, fnB1sfnB=9))

        r2.value('fnB').append_record(from_rec=r1.value('fnB', 0), root_rec=r2, root_idx=('fnB', ))
        assert r2.val('fnB', 2, 'sfnA') == 2
        assert r2.val('fnB', 2, 'sfnB') == 3
        assert r2['fnB'].root_rec() is r2
        assert r2[('fnB', 2, 'sfnB')].root_rec() is r2
        assert r2['fnB'].root_idx() == ('fnB', )
        assert r2[('fnB', 2, 'sfnB')].root_idx() == ('fnB', 2, 'sfnB')

        r1.value('fnB').append_record(from_rec=r2.value('fnB', 1), root_rec=r1, root_idx=('fnB', ))
        assert r1.val('fnB', 1, 'sfnA') == 8
        assert r1.val('fnB', 1, 'sfnB') == 9
        assert r1['fnB'].root_rec() is r1
        assert r1[('fnB', 1, 'sfnB')].root_rec() is r1
        assert r1['fnB'].root_idx() == ('fnB', )
        assert r1[('fnB', 1, 'sfnB')].root_idx() == ('fnB', 1, 'sfnB')


class TestStructures:
    def test_idx_key(self, rec_2f_2s_incomplete):
        assert isinstance(rec_2f_2s_incomplete['fnB'].value(), Records)
        assert isinstance(rec_2f_2s_incomplete[('fnB',)].value(), Records)

        assert isinstance(rec_2f_2s_incomplete[('fnB', 1)], Record)
        assert isinstance(rec_2f_2s_incomplete[('fnB',)].value(1), Record)

        assert isinstance(rec_2f_2s_incomplete[('fnB', 1, 'sfnB')].value(), Value)

        assert isinstance(rec_2f_2s_incomplete['fnB'][1]['sfnB'].value(), Value)
        assert isinstance(rec_2f_2s_incomplete['fnB'][1].value('sfnB'), Value)
        assert isinstance(rec_2f_2s_incomplete['fnB'].value(1, 'sfnB'), Value)
        assert isinstance(rec_2f_2s_incomplete[('fnB',)].value(1, 'sfnB'), Value)

        assert rec_2f_2s_incomplete.val('fnB', 1, 'sfnB') == 'sfB2v'
        assert rec_2f_2s_incomplete['fnB'].value(1, 'sfnB').val() == 'sfB2v'
        assert rec_2f_2s_incomplete[('fnB',)].value(1, 'sfnB').val() == 'sfB2v'
        assert rec_2f_2s_incomplete[('fnB', 1)]['sfnB'].val() == 'sfB2v'
        assert rec_2f_2s_incomplete[('fnB', 1, 'sfnB')].val() == 'sfB2v'
        assert rec_2f_2s_incomplete['fnB', 1, 'sfnB'].val() == 'sfB2v'
        
        assert rec_2f_2s_incomplete['fnB1sfnB'].val() == 'sfB2v'

    def test_leafs(self, rec_2f_2s_incomplete, rec_2f_2s_complete):
        leafs = list(rec_2f_2s_incomplete.leafs())
        assert len(leafs) == 3

        leafs = list(rec_2f_2s_complete.leafs())
        assert len(leafs) == 5

    def test_leaf_indexes(self, rec_2f_2s_incomplete, rec_2f_2s_complete):
        leaf_indexes = list(rec_2f_2s_incomplete.leaf_indexes())
        assert len(leaf_indexes) == 3
        for li in [('fnA',), ('fnB', 1, 'sfnB'), ('fnB', 1, 'sfnA')]:
            assert li in leaf_indexes

        leaf_indexes = list(rec_2f_2s_complete.leaf_indexes())
        assert len(leaf_indexes) == 5
        for li in [('fnA',), ('fnB', 0, 'sfnB'), ('fnB', 0, 'sfnA'), ('fnB', 1, 'sfnB'), ('fnB', 1, 'sfnA')]:
            assert li in leaf_indexes


class TestCopy:
    def test_shallow_copy_record(self, rec_2f_2s_incomplete):
        r1c = rec_2f_2s_incomplete.copy()
        assert rec_2f_2s_incomplete == r1c
        assert rec_2f_2s_incomplete is not r1c
        assert rec_2f_2s_incomplete[('fnB', 1, 'sfnB')].val() == 'sfB2v'
        assert r1c[('fnB', 1, 'sfnB')].val() == 'sfB2v'

        rec_2f_2s_incomplete[('fnB', 1, 'sfnB')].set_val('sfB2v_new')
        assert rec_2f_2s_incomplete[('fnB', 1, 'sfnB')].val() == 'sfB2v_new'
        assert r1c[('fnB', 1, 'sfnB')].val() == 'sfB2v_new'

    def test_deep_copy_record(self, rec_2f_2s_incomplete):
        r1c = rec_2f_2s_incomplete.copy(deepness=-1)
        # STRANGE crashing in: assert rec_2f_2s_incomplete == r1c
        assert id(rec_2f_2s_incomplete) != id(r1c)
        assert rec_2f_2s_incomplete is not r1c

        assert id(rec_2f_2s_incomplete['fnA']) != id(r1c['fnA'])
        assert rec_2f_2s_incomplete['fnA'] is not r1c['fnA']

        assert rec_2f_2s_incomplete['fnA'].value() == r1c['fnA'].value()
        assert id(rec_2f_2s_incomplete['fnA'].value()) != id(r1c['fnA'].value())
        assert rec_2f_2s_incomplete['fnA'].value() is not r1c['fnA'].value()

        # STRANGE failing until implementation of _Field.__eq__: assert rec_2f_2s_incomplete['fnB'] == r1c['fnB']
        assert id(rec_2f_2s_incomplete['fnB']) != id(r1c['fnB'])
        assert rec_2f_2s_incomplete['fnB'] is not r1c['fnB']

        # STRANGE crashing in: assert rec_2f_2s_incomplete['fnB'][1] == r1c['fnB'][1]
        assert id(rec_2f_2s_incomplete['fnB'][1]) != id(r1c['fnB'][1])
        assert rec_2f_2s_incomplete['fnB'][1] is not r1c['fnB'][1]

        assert id(rec_2f_2s_incomplete['fnB'][1]['sfnB']) != id(r1c['fnB'][1]['sfnB'])
        assert rec_2f_2s_incomplete['fnB'][1]['sfnB'] is not r1c['fnB'][1]['sfnB']

        assert rec_2f_2s_incomplete['fnB'][1]['sfnB'].value() == r1c['fnB'][1]['sfnB'].value()

        assert rec_2f_2s_incomplete[('fnB', 1, 'sfnB')].val() == 'sfB2v'
        assert r1c[('fnB', 1, 'sfnB')].val() == 'sfB2v'

        rec_2f_2s_incomplete[('fnB', 1, 'sfnB')].set_val('sfB2v_new')
        assert rec_2f_2s_incomplete[('fnB', 1, 'sfnB')].val() == 'sfB2v_new'
        assert r1c[('fnB', 1, 'sfnB')].val() == 'sfB2v'

    def test_flat_copy_record(self, rec_2f_2s_incomplete):
        # test flattening copy into existing record (r2)
        r2 = Record(fields={('fnB', 1, 'sfnB'): 'sfB2v_old'})
        assert r2[('fnB', 1, 'sfnB')].val() == 'sfB2v_old'
        r3 = r2.copy(onto_rec=rec_2f_2s_incomplete)
        print(r3)
        assert rec_2f_2s_incomplete != r2
        assert rec_2f_2s_incomplete is not r2
        assert rec_2f_2s_incomplete == r3
        assert rec_2f_2s_incomplete is r3
        assert rec_2f_2s_incomplete[('fnB', 1, 'sfnB')].val() == 'sfB2v'
        assert r2[('fnB', 1, 'sfnB')].val() == 'sfB2v_old'
        assert r3[('fnB', 1, 'sfnB')].val() == 'sfB2v'


class TestSystemDirections:
    def test_multi_sys_name_rec(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete
        rX = r.copy().set_env(system='Xx', direction=FAD_FROM)
        rX.add_system_fields((('fnAXx', 'fnA'), ('sfnAXx', 'fnB0sfnA'), ('sfnBXx', 'fnB0sfnB')))
        rY = r.copy().set_env(system='Yy', direction=FAD_ONTO)
        rY.add_system_fields((('fnAYy', 'fnA'), ('sfnAYy', 'fnB0sfnA'), ('sfnBYy', 'fnB0sfnB')))
        for idx in r.leaf_indexes():
            if len(idx) > 1 and idx[1] > 0:
                break
            assert r[idx].name(system='Xx') == r[idx].name() + 'Xx'
            assert r[idx].name(system='Yy') == r[idx].name() + 'Yy'

    def test_multi_sys_val_rec(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete
        rX = r.copy().set_env(system='Xx', direction=FAD_FROM)
        rX.add_system_fields((('fnAXx', 'fnA', 0),
                              ('sfnAXx', 'fnB0sfnA', 1), ('sfnBXx', 'fnB0sfnB', 2),
                              ('sfnAXx', 'fnB1sfnA', 3), ('sfnBXx', 'fnB1sfnB', 4)))
        for i, idx in enumerate(r.leaf_indexes()):
            assert r[idx].val() == i
            assert r[idx].val(system='Xx') == i

        rY = r.copy().set_env(system='Yy', direction=FAD_ONTO)
        rY.add_system_fields((('fnAXx', 'fnA', 5),
                              ('sfnAXx', 'fnB0sfnA', 6), ('sfnBXx', 'fnB0sfnB', 7),
                              ('sfnAXx', 'fnB1sfnA', 8), ('sfnBXx', 'fnB1sfnB', 9)))
        for i, idx in enumerate(r.leaf_indexes()):
            assert r[idx].val() == i + 5
            assert r[idx].val(system='Xx') == i + 5
            assert r[idx].val(system='Yy') == i + 5

    def test_multi_sys_converter_rec(self, rec_2f_2s_complete):
        # PyCharm doesn't like assignments of lambda to vars: cnv = lambda f, v: v + 10
        def cnv(_, v):
            return v + 10

        r = rec_2f_2s_complete
        rX = r.copy().set_env(system='Xx', direction=FAD_FROM)
        rX.add_system_fields((('fnAXx', 'fnA', 0, cnv),
                              ('sfnAXx', 'fnB0sfnA', 1, cnv), ('sfnBXx', 'fnB0sfnB', 2, cnv),
                              ('sfnAXx', 'fnB1sfnA', 3, cnv), ('sfnBXx', 'fnB1sfnB', 4, cnv)),
                             sys_fld_indexes={FAT_IDX + FAD_FROM: 0, FAT_IDX: 1, FAT_VAL: 2, FAT_CNV + FAD_FROM: 3})
        for i, idx in enumerate(r.leaf_indexes()):
            assert isinstance(r[idx].val(), str)
            assert r[idx].val() in ('', 'sfA1v', 'sfA2v', 'sfB1v', 'sfB2v')
            assert r[idx].val(system='Xx') == i
            r[idx].pull('Xx', r, idx)
            assert r[idx].val() == i + 10
            assert r[idx].val(system='Xx') == i

    def test_shorter_sys_idx_path(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete
        str_val = "KEY1=val1,KEY2=val2,RCI=val3"
        rX = r.copy().set_env(system='Xx', direction=FAD_FROM)
        rX.add_system_fields((('fnAXx', 'fnA'),
                              ('fnBXx', 'fnB', str_val, lambda f, v: f.string_to_records(v, ['sfnA', 'sfnB']))),
                             sys_fld_indexes={FAT_IDX + FAD_FROM: 0, FAT_IDX: 1, FAT_VAL: 2, FAT_CNV + FAD_FROM: 3})
        r.pull('Xx')
        assert r.val('fnB', 0, 'sfnA') == 'KEY1'
        assert r.val('fnB', 0, 'sfnB') == 'val1'
        assert r.val('fnB', 1, 'sfnA') == 'KEY2'
        assert r.val('fnB', 1, 'sfnB') == 'val2'
        assert r.val('fnB', 2, 'sfnA') == 'RCI'
        assert r.val('fnB', 2, 'sfnB') == 'val3'

        rY = r.copy().set_env(system='Yy', direction=FAD_ONTO)
        rY.add_system_fields((('fnAXx', 'fnA'),
                              ('fnBXx', 'fnB',
                               lambda _, val: ",".join(k + "=" + v for rec in val for k, v in rec.items()))),
                             sys_fld_indexes={FAT_IDX + FAD_ONTO: 0, FAT_IDX: 1, FAT_CNV + FAD_ONTO: 3})
        r.pull('Xx')
        assert r.val('fnB', 0, 'sfnA') == 'KEY1'
        assert r.val('fnB', 0, 'sfnB') == 'val1'
        assert r.val('fnB', 1, 'sfnA') == 'KEY2'
        assert r.val('fnB', 1, 'sfnB') == 'val2'
        assert r.val('fnB', 2, 'sfnA') == 'RCI'
        assert r.val('fnB', 2, 'sfnB') == 'val3'


class TestSetVal:
    def test_set_field_val(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete

        r['fnA'] = 1
        assert r.val('fnA') == 1
        r[('fnA', 0, 'sfnA')] = 2
        assert r.val('fnA', 0, 'sfnA') == 2
        r[('fnA', 0, 'sfnB')] = 3
        assert r.val('fnA', 0, 'sfnB') == 3
        r[('fnA', 1, 'sfnA')] = 4
        assert r.val('fnA', 1, 'sfnA') == 4
        r[('fnA', 1, 'sfnB')] = 5
        assert r.val('fnA', 1, 'sfnB') == 5

    def test_set_field_sys_val(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete
        rX = r.copy().set_env(system='Xx', direction=FAD_FROM)
        rX.add_system_fields((('fnAXx', 'fnA'),
                              ('sfnAXx', 'fnB0sfnA'), ('sfnBXx', 'fnB0sfnB'),
                              ('sfnAXx', 'fnB1sfnA'), ('sfnBXx', 'fnB1sfnB')))

        rX.set_val(1, 'fnA', system='Xx', direction=FAD_FROM, flex_sys_dir=False)
        assert r['fnAXx'].val() == ''       # sys_name idx 'fnAXx' does NOT use sys val
        assert r.val('fnAXx') == ''
        assert r.val('fnAXx', system='Xx') == 1
        assert r.val('fnA', system='Xx') == 1

        assert rX['fnA'].val() == ''         # .. also using sys rec does not help if accessed via field

        assert rX.val('fnA') == 1            # .. but sys rec val (rX.val()) does - even if using main field name
        assert rX.val('fnAXx') == 1

        # check for deep field
        rX.set_val(1, 'fnB', 1, 'sfnB', system='Xx', direction=FAD_FROM, flex_sys_dir=False)
        # sys_name idx 'fnAXx' does NOT use sys val
        assert r['fnAXx'].val() == ''
        assert r.val('fnB', 1, 'sfnBXx') == 'sfB2v'
        assert r.val('fnB', 1, 'sfnBXx', system='Xx') == 1
        assert r.val('fnB', 1, 'sfnB', system='Xx') == 1

        # .. but sys rec (rX) does if not accessed via field - even if using main field name
        assert rX['fnB', 1, 'sfnB'].val() == 'sfB2v'
        assert rX['fnB', 1, 'sfnBXx'].val() == 'sfB2v'
        assert rX.val('fnB', 1, 'sfnB') == 1
        assert rX.val('fnB', 1, 'sfnBXx') == 1

    def test_values_set_val(self):
        vus = Values()
        assert vus.set_val(9, 3).val(3) == 9
        assert vus.set_val('6', 2).val(2) == '6'
        vus.set_val([3], 1)
        assert vus.val(1) == [3]
