import pytest

from collections import OrderedDict
from ae_sys_data import aspect_key, aspect_key_system, aspect_key_direction, deeper, field_name_idx_path, \
    Value, Record, Records, _Field, current_index, init_current_index, use_current_index, set_current_index, \
    FAT_VAL, FAD_FROM, FAD_ONTO, FAT_REC, FAT_RCX, ACTION_DELETE
from sys_data_ids import SDI_SH


@pytest.fixture()
def rec_2f_2s_incomplete():     # two fields and only partly complete two sub-levels
    r1 = Record(fields=dict(fnA='', fnB1sfnA='', fnB1sfnB='sfB2v'))
    print(r1)
    return r1


@pytest.fixture()
def rec_2f_2s_complete():       # two fields and only partly complete two sub-levels
    r1 = Record(fields=dict(fnA='', fnB0sfnA='sfA1v', fnB0sfnB='sfB1v', fnB1sfnA='sfA2v', fnB1sfnB='sfB2v'))
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

        assert not field_name_idx_path('3')
        assert field_name_idx_path('Test2') == ('Test', 2)
        assert field_name_idx_path('2Test2') == (2, 'Test', 2)
        assert field_name_idx_path('3Test') == (3, 'Test')

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
        assert f.name == 'init'
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
        r.set_val('fAv1', 'fnA', 1, 'sfnA')
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA', )
        assert r[('fnA', 1, 'sfnA')].root_rec() is r
        assert r[('fnA', 1, 'sfnA')].root_idx() == ('fnA', 1, 'sfnA')

        r = Record()
        r.set_node_child('fBv1', 'fnB', 0, 'sfnB')
        assert r['fnB'].root_rec() is r
        assert r['fnB'].root_idx() == ('fnB', )
        assert r[('fnB', 0, 'sfnB')].root_rec() is r
        assert r[('fnB', 0, 'sfnB')].root_idx() == ('fnB', 0, 'sfnB')

        r = Record()
        r.set_val('fAv3', 'fnA', root_rec=r, root_idx=('fnA', ))
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA', )

        r = Record()
        r.set_val('fAv2', 'fnA', 1, 'sfnA', root_rec=r)
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA', )
        assert r[('fnA', 1, 'sfnA')].root_rec() is r    # .. but the sub-field has it
        assert r[('fnA', 1, 'sfnA')].root_idx() == ('fnA', 1, 'sfnA')

        r = Record()
        r.set_node_child('fBv1', 'fnB', 0, 'sfnB', root_rec=r)
        assert r['fnB'].root_rec() is r
        assert r['fnB'].root_idx() == ('fnB', )
        assert r[('fnB', 0, 'sfnB')].root_rec() is r
        assert r[('fnB', 0, 'sfnB')].root_idx() == ('fnB', 0, 'sfnB')

        r = Record()
        r.set_val('fAv3', 'fnA', 1, 'sfnA', root_rec=r, root_idx=('fnA', 1, 'sfnA'))
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA', )
        assert r[('fnA', 1, 'sfnA')].root_rec() is r
        assert r[('fnA', 1, 'sfnA')].root_idx() == ('fnA', 1, 'sfnA')

        r = Record()
        r.set_node_child('fBv3', 'fnB', 0, 'sfnB', root_rec=r, root_idx=('fnB', 0, 'sfnB'))
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
            assert v.name == 'fnA'
            assert v.val() == 12
        for i, (k, v) in enumerate(r.items()):
            assert k == 'fnA'
            assert v.name == 'fnA'
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
        assert r.node_child(('fnB', 1, 'sfnB'), system=None, direction=None).val(system='Xx', direction=None) == 33
        assert r.node_child('fnB1sfnB', system=None, direction=None).val(system='Xx') == 33
        assert r.node_child('fnB1sfnB_From_Xx', system=None, direction=None).val(system='Xx') == 33
        assert r.node_child('fnB1sfnB_From_Xx').val(system='Xx') == 33

        # create different value path for system Xx
        r.set_env(system='Xx')
        sr = Record(dict(sfnB_rec=66))
        r['fnB'].set_value(sr, system='Xx')
        assert r.node_child(('fnB', 'sfnB_rec'), system=None, direction=None).val(system='Xx') == 66
        assert r.node_child(('fnB', 'sfnB_rec'), system=None, direction=None).val(system='Xx', direction=None) == 66
        assert r.node_child(('fnB', 'sfnB_rec'), system=None, direction=None).val(system='Xx') == 66
        assert r.node_child(('fnB', 'sfnB_rec'), system=None, direction=None).val(system='Xx') == 66
        assert r.node_child(('fnB', 'sfnB_rec'), system=None).val(system='Xx') == 66

        r.set_env(system='Xx', direction='From')
        assert r.node_child(('fnB', 'sfnB_rec'), system=None, direction=None).val(system='Xx') == 66
        assert r.node_child(('fnB', 'sfnB_rec'), system=None, direction=None).val(system='Xx', direction=None) == 66
        assert r.node_child(('fnB', 'sfnB_rec'), system=None, direction=None).val(system='Xx') == 66
        assert r.node_child(('fnB', 'sfnB_rec'), system=None, direction=None).val(system='Xx') == 66
        assert r.node_child(('fnB', 'sfnB_rec'), system=None).val(system='Xx') == 66

    def test_copy(self):
        r = Record()
        assert r.copy() == r
        assert r.copy() is not r

        r.add_fields(dict(fnA=33, fnB=66, fnC0sfnC=99))
        assert len(r) == 3
        assert r.copy() == r
        assert r.copy() is not r

        r2 = r.copy(filter_func=lambda f: f.name == 'fnB')
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
            ('F/', None),
            ('F' + SEP + 'NAME', ('fn', 0, 'Surname'),
             lambda f: f.ina(ACTION_DELETE) or not f.val() or f.rfv('F', 0, 'Id'),
             lambda f: ("Adult " + str(f.crx()) if f.crx() is None or f.crx() < f.rfv('Cnt')
                        else "Child " + str(f.crx() - f.rfv('Cnt') + 1))),
            ('F' + SEP + 'NAME2', ('fn', 0, 'Forename')),
            ('AUTO-GENERATED', None,
             lambda f: f.ina(ACTION_DELETE) or (f.rfv('ResAdults') <= 2 and f.rfv('Id')),
             '1'),
            ('F' + SEP + 'MATCHCODE', ('fn', 0, 'Id'),
             lambda f: f.ina(ACTION_DELETE) or not f.val() or f.rfv('ShId')),
            ('ROOM-SEQ', None,
             lambda f: f.ina(ACTION_DELETE),
             '0'),
            ('PERS-SEQ', None,
             lambda f: f.ina(ACTION_DELETE),
             lambda f: (str(f.crx()))),
            ('F' + SEP + 'DOB', ('fn', 0, 'DOB'),
             lambda f: f.ina(ACTION_DELETE) or not f.val()),
            ('/F', None,
             lambda f: f.ina(ACTION_DELETE) or f.rfv('Cnt') <= 0),
        )
        sys_r = Record(system=SDI_SH, direction=FAD_FROM)
        sys_r.add_system_fields(d)
        assert sys_r.val('Cnt') == ''

        data_r = Record(fields=dict(Cnt=2, fn0Forename='John'))
        sys_r.clear_vals()
        for k in data_r.leaf_indexes():
            if k[0] in sys_r:
                sys_r.set_val(data_r[k].val(), *k)
        sys_r.push(SDI_SH)
        assert sys_r.val('Cnt') == 2
        #assert sys_r.val('fn', 0, 'Surname') == 'Adult0'

        sys_r.set_val('Johnson', 'fn', 0, 'Surname')
        assert sys_r.val('fn', 0, 'Surname') == 'Johnson'

        sys_r.set_val(123456, 'fn0Id')
        sys_r.push(SDI_SH)


class TestRecords:
    def test_typing(self):
        assert isinstance(Records(), Records)
        assert isinstance(Records(), list)

    def test_repr_eval(self):
        assert eval(repr(Records())) == Records()

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
        r3 = r2.copy(to_rec=rec_2f_2s_incomplete)
        print(r3)
        assert rec_2f_2s_incomplete != r2
        assert rec_2f_2s_incomplete is not r2
        assert rec_2f_2s_incomplete == r3
        assert rec_2f_2s_incomplete is r3
        assert rec_2f_2s_incomplete[('fnB', 1, 'sfnB')].val() == 'sfB2v'
        assert r2[('fnB', 1, 'sfnB')].val() == 'sfB2v_old'
        assert r3[('fnB', 1, 'sfnB')].val() == 'sfB2v'
