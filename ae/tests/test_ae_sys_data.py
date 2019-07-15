import pytest
import datetime
from collections import OrderedDict

from ae.sys_data import (
    aspect_key, aspect_key_system, aspect_key_direction, deeper,
    field_name_idx_path, field_names_idx_paths, idx_path_field_name,
    Value, Values, Record, Records, _Field,
    compose_current_index, current_index, init_current_index, use_current_index, set_current_index,
    FAD_FROM, FAD_ONTO, FAT_VAL, FAT_REC, FAT_RCX, FAT_SQE, FAT_CAL, FAT_IDX, FAT_CNV,
    ACTION_DELETE, IDX_PATH_SEP, ALL_FIELDS, CALLABLE_SUFFIX, System)


SS = 'Ss'       # test system ids
SX = 'Xx'
SY = 'Yy'


@pytest.fixture()
def rec_2f_2s_complete():       # two fields and only partly complete two sub-levels
    r1 = Record(fields=(('fnA', ''),
                        ('fnB0sfnA', 'sfA1v'), ('fnB0sfnB', 'sfB1v'),
                        ('fnB1sfnA', 'sfA2v'), ('fnB1sfnB', 'sfB2v'))
                )
    print(r1)
    return r1


@pytest.fixture()
def rec_2f_2s_incomplete():     # two fields and only partly complete two sub-levels
    r1 = Record(fields=dict(fnA='', fnB1sfnA='', fnB1sfnB='sfB2v'))
    print(r1)
    return r1


class TestHelperMethods:
    def test_aspect_key(self):
        assert aspect_key(FAT_VAL, SS, FAD_FROM) == FAT_VAL + FAD_FROM + SS

    def test_aspect_key_system(self):
        assert aspect_key_system(FAT_VAL + FAD_FROM + SS) == SS
        assert aspect_key_system(FAT_VAL + FAD_ONTO + SS) == SS
        assert aspect_key_system(FAT_VAL + SS) == SS

    def test_aspect_key_direction(self):
        assert aspect_key_direction(FAT_VAL + FAD_FROM + SS) == FAD_FROM
        assert aspect_key_direction(FAT_VAL + FAD_ONTO + SS) == FAD_ONTO
        assert aspect_key_direction(FAT_VAL + SS) == ''

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

    def test_idx_path_sep_valid_char(self):
        # ensure that IDX_PATH_SEP is not a dot character (would break xml element name paths lookups in shif.py)
        assert IDX_PATH_SEP != '.'

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

        assert field_name_idx_path('3') == ()
        assert field_name_idx_path('Test2') == ()           # index sys name field split exception
        assert field_name_idx_path('2Test2') == (2, 'Test2')
        assert field_name_idx_path('2Test34') == (2, 'Test34')
        assert field_name_idx_path('2Test345') == (2, 'Test', 3, '45')
        assert field_name_idx_path('2Test3456') == (2, 'Test', 34, '56')
        assert field_name_idx_path('23Test4567') == (23, 'Test', 45, '67')
        assert field_name_idx_path('234Test5678') == (234, 'Test', 56, '78')
        assert field_name_idx_path('3Test') == (3, 'Test')

    def test_field_name_idx_path_sep(self):
        assert field_name_idx_path('Test' + IDX_PATH_SEP + 'test') == ('Test', 'test')
        assert field_name_idx_path(IDX_PATH_SEP + 'Test' + IDX_PATH_SEP + 'test' + IDX_PATH_SEP) == ('Test', 'test')

        assert field_name_idx_path('Test3' + IDX_PATH_SEP + 'test') == ('Test', 3, 'test')
        assert field_name_idx_path('Test33' + IDX_PATH_SEP + 'test') == ('Test', 33, 'test')

        assert field_name_idx_path('Test' + IDX_PATH_SEP + '3' + IDX_PATH_SEP + 'test') == ('Test', 3, 'test')
        assert field_name_idx_path('Test' + IDX_PATH_SEP + '33' + IDX_PATH_SEP + 'test') == ('Test', 33, 'test')

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
        assert field_name_idx_path('Test2', return_root_fields=True) == ('Test2', )
        assert field_name_idx_path('2Test2', return_root_fields=True) == (2, 'Test2', )
        assert field_name_idx_path('3Test', return_root_fields=True) == (3, 'Test')

    def test_field_names_idx_paths(self):
        assert field_names_idx_paths(['3Test', ('fn', 0, 'sfn'), 9]) == [(3, 'Test'), ('fn', 0, 'sfn'), (9, )]

    def test_idx_path_field_name(self):
        assert idx_path_field_name(('test', 'TEST')) == 'test' + IDX_PATH_SEP + 'TEST'
        assert idx_path_field_name((3, 'tst')) == '3tst'
        assert idx_path_field_name(('test3no-sub', )) == 'test3no-sub'
        assert idx_path_field_name(('test', 33)) == 'test33'

        assert idx_path_field_name(('test', 'TEST'), add_sep=True) == 'test' + IDX_PATH_SEP + 'TEST'
        assert idx_path_field_name((3, 'tst'), add_sep=True) == '3' + IDX_PATH_SEP + 'tst'
        assert idx_path_field_name(('test3no-sub',), add_sep=True) == 'test3no-sub'
        assert idx_path_field_name(('test', 33), add_sep=True) == 'test' + IDX_PATH_SEP + '33'

    def test_compose_current_index(self):
        idx_path = ('fn', 1, 'sfn')
        assert compose_current_index(Record(), idx_path, Value((1, ))) == idx_path
        idx_path = ('fn', 1)
        assert compose_current_index(Record(), idx_path, Value((1, ))) == idx_path
        idx_path = ('fn', )
        assert compose_current_index(Record(), idx_path, Value((1, ))) == idx_path

        rec = Record(fields=dict(fnA='', fnB1sfnA='', fnB1sfnB='sfB2v'))
        idx_path = ('fnB', 1, 'sfnB')
        assert compose_current_index(rec, idx_path, Value((1, ))) == idx_path

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

        with pytest.raises(AssertionError):
            use_current_index(None, ('fnB', 0, 'fnBA'), Value((1,)))

    def test_set_current_index(self):
        rs = Records()
        set_current_index(rs, idx=2)
        assert current_index(rs) == 2
        set_current_index(rs, add=-1)
        assert current_index(rs) == 1

        r = Record()
        set_current_index(r, idx='fnX')
        assert current_index(r) == 'fnX'

    def test_set_current_system_index(self, rec_2f_2s_complete):
        SEP = '+'
        r = Record()
        assert r.current_idx is None
        assert r.set_current_system_index('TEST', SEP) is None

        r = rec_2f_2s_complete.set_env(system=SX, direction=FAD_ONTO)
        assert r.current_idx == 'fnA'
        assert r.value('fnB', flex_sys_dir=True).current_idx == 0
        r.add_system_fields((('A' + SEP + 'X', 'fnA'), ('B' + SEP + 'Y', 'fnB0sfnA'), ('B' + SEP + 'Z', 'fnB0sfnB')))
        assert r.current_idx == 'fnA'
        assert r.value('fnB', flex_sys_dir=True).current_idx == 0
        assert r.node_child(('fnB', 0)).current_idx == 'sfnA'

        assert r.set_current_system_index('A', SEP) is None
        assert r.current_idx == 'fnA'
        assert r.value('fnB', flex_sys_dir=True).current_idx == 0
        assert r.node_child(('fnB', 0)).current_idx == 'sfnA'

        assert r.set_current_system_index('B', SEP) is r
        assert r.current_idx == 'fnA'
        assert r.value('fnB', flex_sys_dir=True).current_idx == 1
        assert r.node_child(('fnB', 0)).current_idx == 'sfnA'

        assert r.set_current_system_index('B', SEP) is r
        assert r.current_idx == 'fnA'
        assert r.value('fnB', flex_sys_dir=True).current_idx == 2
        assert r.node_child(('fnB', 0)).current_idx == 'sfnA'

        assert r.set_current_system_index('B', SEP, idx_val=0, idx_add=None) is r
        assert r.current_idx == 'fnA'
        assert r.value('fnB', flex_sys_dir=True).current_idx == 0
        assert r.node_child(('fnB', 0)).current_idx == 'sfnA'

        assert r.set_current_system_index('B', SEP, idx_add=2) is r
        assert r.current_idx == 'fnA'
        assert r.value('fnB', flex_sys_dir=True).current_idx == 2
        assert r.node_child(('fnB', 0)).current_idx == 'sfnA'


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
        assert not v.initialized
        assert v.value() == []
        assert not v.initialized
        assert v.val() == ''
        assert not v.initialized
        with pytest.raises(AssertionError):
            v.set_val(Value().set_val('tvX'))
        assert not v.initialized
        v.set_val('tvA')
        assert v.initialized
        assert v.value() == ['tvA']
        assert v.val() == 'tvA'
        v.clear_leafs()
        assert v.value() == []
        assert v.val() == ''

    def test_val_set(self):
        v = Value()
        v.set_val('tvA')
        assert v.val() == 'tvA'
        v[0] = 'tvB'
        assert v.val() == 'tvB'
        v[-1] = 'tvC'
        assert v.val() == 'tvC'
        with pytest.raises(IndexError):
            v['test'] = 'tvD'
        assert v.val() == 'tvC'

    def test_val_get(self):
        v = Value()
        assert v.val() == ''
        # ae: 26-Feb-19 changed Value.val() to return empty string instead of None
        # assert v.val('test') is None
        # assert v.val(12, 'sub_field') is None
        # assert v.val('field', 12, 'sub_field') is None
        assert v.val('test') == ''
        assert v.val(12, 'sub_field') == ''
        assert v.val('field', 12, 'sub_field') == ''

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
        assert v.node_child(()) == v


class TestValues:
    def test_node_child(self):
        u = Values()
        assert u.node_child(('test',)) is None
        with pytest.raises(AssertionError):
            u.node_child(('test',), moan=True)
        assert u.node_child((0,)) is None
        with pytest.raises(AssertionError):
            u.node_child((0,), moan=True)
        assert u.node_child(()) is None
        with pytest.raises(AssertionError):
            u.node_child((), moan=True)
        assert u.node_child(('test',)) is None
        with pytest.raises(AssertionError):
            u.node_child(('test',), moan=True)
        assert u.node_child('test') is None
        with pytest.raises(AssertionError):
            u.node_child('test', moan=True)
        assert u.node_child(0) is None
        with pytest.raises(AssertionError):
            u.node_child(0, moan=True)
        assert u.node_child(None) is None
        with pytest.raises(AssertionError):
            u.node_child(None, moan=True)

    def test_set_value(self):
        u = Values()
        assert u.set_val('test_val', 0) is u
        root_idx = ('test', )
        assert u.set_value(Value().set_val('other_test_val'), 0, root_idx=root_idx) is u
        assert u.val(0) == 'other_test_val'


class TestField:
    def test_typing(self):
        assert isinstance(_Field(**{FAT_REC: Record(), FAT_RCX: ('test', )}), _Field)

    def test_repr(self):
        r = Record(fields=dict(test='xxx'), system=SX, direction=FAD_ONTO)
        f = r.node_child(('test',))

        rep = repr(f)
        assert 'test' in rep
        assert 'xxx' in rep

        r.add_system_fields((('tsf', 'test'), ))
        rep = repr(f)
        assert 'test' in rep
        assert 'xxx' in rep

        r.set_val('sys_val', 'tsf', system=SX, direction=FAD_ONTO, flex_sys_dir=False)
        print(r)
        rep = repr(f)
        assert 'tsf' in rep
        assert 'test' in rep
        assert 'xxx' in rep
        assert 'sys_val' in rep

    def test_node_child(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete
        f = r.node_child(('fnA', ))
        assert f.node_child(tuple()) is None
        assert f.node_child((('invalid_idx_path[0]',),)) is None
        assert f.node_child(datetime) is None
        assert f.node_child('') is None
        assert f.node_child(None) is None

        f = _Field(root_rec=r, root_idx=('test',))
        assert f.node_child(('test', )) is None
        f.set_aspect('', FAT_VAL, allow_values=True)
        assert f.node_child(('test', )) is None

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

    def test_set_value(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete
        v = Value()
        r.set_value(v, 'fnB', 0, 'sfnA')
        assert r.value('fnB', 0, 'sfnA') == v
        assert r.value('fnB', 0, 'sfnA') is v

    def test_set_val(self):
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test',)})
        f.set_val('f1v')
        assert f.val() == 'f1v'

    def test_val_get(self):
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test',)})
        assert f.val() == ''
        # ae: 26-Feb-19 changed Value.val() to return empty string instead of None
        # assert f.val('test') is None
        # assert f.val(12, 'sub_field') is None
        # assert f.val('sub_field', 12, '2nd_sub_field') is None
        assert f.val('test') == ''
        assert f.val(12, 'sub_field') == ''
        assert f.val('sub_field', 12, '2nd_sub_field') == ''

    def test_field_name_init(self):
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('init',)})
        assert f.name() == 'init'
        test_name = 'test'
        f.set_name(test_name)
        assert f.name() == test_name

    def test_set_and_del_user_aspect(self):
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test',)})
        fat = 'Uak'
        uav = 'user_aspect_val'
        assert not f.aspect_exists(fat)
        assert f.set_aspect(uav, fat) is f
        assert f.aspect_exists(fat)
        assert f.aspect_value(fat) == uav
        assert f.set_aspect(None, fat)      # delete/remove aspect
        assert not f.aspect_exists(fat)

    def test_find_aspect_key(self):
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test',)})
        assert f.find_aspect_key(FAT_REC) == FAT_REC
        assert f.find_aspect_key('Uak') is None

    def test_set_aspects(self):
        def call_val(_field):
            return 'new_val'
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test',)})

        assert f.set_aspects(**{FAT_SQE + CALLABLE_SUFFIX: call_val}) is f
        assert f.aspect_value(FAT_SQE) == 'new_val'

        assert f.set_aspects(allow_values=True, **{FAT_VAL + CALLABLE_SUFFIX: call_val}) is f
        assert f.aspect_value(FAT_VAL) == 'new_val'

    def test_del_name(self):
        r = Record(fields=dict(test='xxx'), system=SX, direction=FAD_ONTO)
        r.add_system_fields((('tsf', 'test'), ))
        f = r.node_child(('test',))

        assert f.name(system=SX, direction=FAD_ONTO) == 'tsf'
        assert f.del_name(system=SX, direction=FAD_ONTO) is f
        assert f.name(system=SX, direction=FAD_ONTO) == 'test'
        assert f.name(system=SX, direction=FAD_ONTO, flex_sys_dir=False) is None

    def test_calculator(self):
        def call_val(_field):
            return cal_val

        cal_val = 'init_val'
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test',)})
        assert f.set_calculator(call_val)
        assert f.calculator() is call_val
        assert f.val() == 'init_val'
        cal_val = 'new_val'
        assert f.val() == 'new_val'

        cal_val = 'init_val'
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test',), FAT_CAL: call_val})
        assert f.calculator() is call_val
        assert f.val() == 'init_val'
        cal_val = 'new_val'
        assert f.val() == 'new_val'

    def test_filter(self):
        def filter_callable(_field):
            return filtered

        filtered = True
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test',)})
        assert f.set_filter(filter_callable) is f
        assert f.filter() is filter_callable
        assert f.filter()(f)
        filtered = False
        assert not f.filter()(f)

    def test_sql_expression(self):
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test',)})
        sqe = 'SELECT * from test'
        assert f.set_sql_expression(sqe) is f
        assert f.sql_expression() == sqe

    def test_validator(self):
        def validator_callable(_field, _val):
            return is_valid

        is_valid = True
        f = _Field(**{FAT_REC: Record(), FAT_RCX: ('test',)})
        assert f.set_validator(validator_callable) is f
        assert f.validator() is validator_callable
        assert f.validate(None)
        is_valid = False
        assert not f.validate(None)

    def test_clear_leafs(self):
        r = Record(fields=dict(test='xxx'), system=SX, direction=FAD_ONTO)
        f = r.node_child(('test',))

        r.add_system_fields((('tsf', 'test', 'clear_val'),))
        assert f.val() == 'clear_val'

        assert f.clear_leafs(system=None, direction=None) is f
        assert f.val() == 'clear_val'

        f.set_val('new_val')
        assert f.clear_leafs(system=None, direction=None) is f
        assert f.val() == 'clear_val'

        f.set_val('new_val', system=SX, direction=FAD_ONTO, flex_sys_dir=False)
        assert f.clear_leafs(system=None, direction=None) is f
        assert f.val(system=SX, direction=FAD_ONTO) == 'clear_val'

    def test_pull(self):
        r = Record(fields=dict(test='xxx'), system=SX, direction=FAD_FROM)
        f = r.node_child(('test',))
        r.add_system_fields((('tsf', 'test', 'init_val'),))

        f.set_val('sys_val', system=SX, direction=FAD_FROM, flex_sys_dir=False)
        assert f.pull(SX, r, ('test', )) is f
        assert f.val() == 'sys_val'

        f.set_val(None, system=SX, direction=FAD_FROM, flex_sys_dir=False)
        assert f.pull(SX, r, ('test', )) is f
        assert f.val() == ''

    def test_push(self):
        r = Record(fields=dict(test='xxx'), system=SX, direction=FAD_ONTO)
        f = r.node_child(('test',))
        r.add_system_fields((('tsf', 'test', 'init_val'),))
        f.set_val('sys_val', system=SX, direction=FAD_ONTO, flex_sys_dir=False)

        f.set_val('new_val')
        assert f.push(SX, r, ('test', )) is f
        assert f.val(system=SX, direction=FAD_ONTO, flex_sys_dir=False) == 'new_val'

        f.set_val(None)
        assert f.push(SX, r, ('test', )) is f
        assert f.val(system=SX, direction=FAD_ONTO, flex_sys_dir=False) == ''

    def test_system_record_val(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete.set_env(system=SX, direction=FAD_FROM)
        f = r.node_child(('fnA',))
        r.add_system_fields((('fnAXx', 'fnA', 'Av'), ('fnBXx', 'fnB'), ('sfnAXx', 'fnB0sfnA'), ('sfnBXx', 'fnB0sfnB')))

        assert f.system_record_val == f.srv
        assert f.srv() == 'Av'
        assert f.srv('fnA') == 'Av'
        assert f.srv('fnB') == r.val('fnB')
        assert f.srv('fnB', 0, 'sfnA') == 'sfA1v'
        assert f.srv('fnB', 1, 'sfnA') == 'sfA2v'

    def test_in_actions(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete.set_env(system=SX, direction=FAD_FROM)
        f = r.node_child(('fnA',))

        assert f.in_actions == f.ina

        assert not f.ina(ACTION_DELETE)

        r.set_env(action=ACTION_DELETE)
        assert f.ina(ACTION_DELETE)

    def test_parent(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete
        f = r.node_child(('fnB', 1, 'sfnB'))

        assert f.parent() is r.node_child(('fnB', 1))
        assert f.parent(value_types=(Record, )) is r.node_child(('fnB', 1))
        assert f.parent(value_types=(Records, )) is r.node_child(('fnB', )).value()
        assert r.node_child(('fnB', )).parent() is r
        assert r.node_child(('fnA', )).parent() is r


class TestRecord:
    def test_typing(self):
        assert isinstance(Record(), Record)
        assert isinstance(Record(), OrderedDict)
        assert isinstance(Record(), dict)

    def test_repr_eval(self):
        assert eval(repr(Record())) == Record()

    def test_field_lookup_standard(self):
        r = Record(fields=dict(test='xxx'))
        print(r)

        assert r['test'] == 'xxx'
        assert r.val('test') == 'xxx'
        assert r.get('test').val() == 'xxx'     # get() always gets field (independent of field_items)

        r.field_items = True
        assert r['test'].val() == 'xxx'
        assert r.val('test') == 'xxx'
        assert r.get('test').val() == 'xxx'

    def test_field_lookup_sys_name(self):
        r = Record(fields=dict(test='xxx'), system=SX, direction=FAD_ONTO)
        r.add_system_fields((('tsf', 'test'), ))

        field = r.node_child(('test', ))
        assert field
        assert field.root_idx() == ('test', )
        assert field.root_idx(system=SX, direction=FAD_ONTO) == ('tsf', )

        assert r['tsf'] == 'xxx'
        assert r.val('tsf') == 'xxx'
        assert r.get('tsf') is None             # get() doesn't find sys names

        r.field_items = True
        assert r['tsf'].val() == 'xxx'
        assert r.val('tsf') == 'xxx'
        assert r.get('tsf') is None

    def test_unpacking(self):
        r = Record(fields=dict(testA='', testB=''))
        print(r)
        d = dict(**r)
        assert d == r

    def test_set_val_basics(self):
        r = Record()
        r.set_val(dict(fnA=33, fnB=66))
        assert r.val('fnA') == 33

    def test_set_val_flex_sys(self):
        r = Record()
        r.set_val('fAv1', 'fnA', 1, 'sfnA')
        assert r.val('fnA', 1, 'sfnA') == 'fAv1'
        r.set_val('fAvX1', 'fnA', 1, 'sfnA', system=SX)
        assert r.val('fnA', 1, 'sfnA', system=SX) == 'fAvX1'
        assert r.val('fnA', 1, 'sfnA') == 'fAvX1'

        r.set_val('fAv', 'fnA', 0, 'sfnA')
        assert r.val('fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 'fnA', 0, 'sfnA', system=SX)
        assert r.val('fnA', 0, 'sfnA', system=SX) == 'fAvX'
        assert r.val('fnA', 0, 'sfnA') == 'fAvX'

    def test_set_val_exact_sys(self):
        r = Record()
        r.set_val('fAv', 'fnA', 0, 'sfnA')
        assert r.val('fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 'fnA', 0, 'sfnA', flex_sys_dir=False, system=SX)
        assert r.val('fnA', 0, 'sfnA', system=SX) == 'fAvX'
        assert r.val('fnA', 0, 'sfnA') == 'fAv'

    def test_set_val_sys_converter(self):
        r = Record()
        r.set_val('fAv', 'fnA', 0, 'sfnA')
        assert r.val('fnA', 0, 'sfnA') == 'fAv'
        r.set_val('fAvX', 'fnA', 0, 'sfnA', system=SX, converter=lambda f, v: v)
        assert r.val('fnA', 0, 'sfnA', system=SX) == 'fAvX'
        assert r.val('fnA', 0, 'sfnA') == 'fAv'

    def test_val_use_curr_idx(self):
        r = Record()
        r.set_val('fAv1', 'fnA', 1, 'sfnA')
        assert r.val('fnA', 1, 'sfnA') == 'fAv1'
        assert r.val('fnA', 0, 'sfnA') is None
        assert r.val('fnA', 0, 'sfnA', use_curr_idx=Value((1, ))) == 'fAv1'
        assert r.val('fnA', 2, 'sfnA') is None
        assert r.val('fnA', 2, 'sfnA', use_curr_idx=Value((1, ))) == 'fAv1'

        r.field_items = True
        f = r[('fnA', 1, 'sfnA')]
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
        r = Record(field_items=True)
        r.set_val('fAv0', 'fnA')
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA',)

        r = Record(field_items=True)
        r.set_node_child('fBv1', 'fnB', 0, 'sfnB')
        assert r['fnB'].root_rec() is r
        assert r['fnB'].root_idx() == ('fnB', )
        assert r[('fnB', 0, 'sfnB')].root_rec() is r
        assert r[('fnB', 0, 'sfnB')].root_idx() == ('fnB', 0, 'sfnB')

        r = Record(field_items=True)
        r.set_val('fAv1', 'fnA', 1, 'sfnA')
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA', )
        assert r[('fnA', 1, 'sfnA')].root_rec() is r
        assert r[('fnA', 1, 'sfnA')].root_idx() == ('fnA', 1, 'sfnA')

        r = Record(field_items=True)
        r.set_val('fAv3', 'fnA', root_rec=r)
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA', )

        r = Record(field_items=True)
        r.set_val('fAv2', 'fnA', 1, 'sfnA', root_rec=r)
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA', )
        assert r[('fnA', 1, 'sfnA')].root_rec() is r    # .. but the sub-field has it
        assert r[('fnA', 1, 'sfnA')].root_idx() == ('fnA', 1, 'sfnA')

        r = Record(field_items=True)
        r.set_node_child('fBv1', 'fnB', 0, 'sfnB')
        assert r['fnB'].root_rec() is r
        assert r['fnB'].root_idx() == ('fnB', )
        assert r[('fnB', 0, 'sfnB')].root_rec() is r
        assert r[('fnB', 0, 'sfnB')].root_idx() == ('fnB', 0, 'sfnB')

        r = Record(field_items=True)
        r.set_val('fAv3', 'fnA', 1, 'sfnA')
        assert r['fnA'].root_rec() is r
        assert r['fnA'].root_idx() == ('fnA', )
        assert r[('fnA', 1, 'sfnA')].root_rec() is r
        assert r[('fnA', 1, 'sfnA')].root_idx() == ('fnA', 1, 'sfnA')

        r = Record(field_items=True)
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
        r.field_items = True
        assert r['fnB'].val() == 66

        r1 = r
        r = Record()
        r.add_fields(r1)
        assert r.val('fnA') == 33
        r.field_items = True
        assert r['fnB'].val() == 66

        r1 = r
        r = Record()
        r.add_fields(r1.val())
        assert r.val('fnA') == 33
        assert r.val('fnB') == 66

        r = Record()
        r.add_fields([('fnA', 33), ('fnB', 66)])
        assert r.val('fnA') == 33
        assert r.val('fnB') == 66

    def test_set_node_child(self):
        r = Record()
        r.set_node_child(12, 'fnA', protect=True)
        assert r.val('fnA') == 12
        r.set_node_child(33, 'fnA')
        assert r.val('fnA') == 33
        r.set_node_child('sfA2v', 'fnA', 2, 'sfnA')     # protect==False
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
        with pytest.raises(AssertionError):
            _ = r['fnA']
        r.set_node_child(12, 'fnA')
        assert r.val('fnA') == 12
        r.field_items = True
        assert r['fnA'].val() == 12
        with pytest.raises(AssertionError):
            _ = r['fnMissing']

    def test_node_child(self, rec_2f_2s_incomplete):
        r = Record(system=SX, direction='From')
        assert r.node_child(()) is None
        with pytest.raises(AssertionError):
            r.node_child((), moan=True)
        assert r.node_child((0,)) is None
        with pytest.raises(AssertionError):
            r.node_child((0,), moan=True)
        assert r.node_child(('test',)) is None

        r = rec_2f_2s_incomplete
        assert r.node_child(('fnA',)).val() == ''
        idx_path = ('fnB', 1, 'sfnB')
        assert r.node_child(idx_path).val() == 'sfB2v'

        r[('fnB', 1, 'sfnB')] = 11
        assert r.val('fnB', 1, 'sfnB') == 11
        r.field_items = True
        r[('fnB', 1, 'sfnB')].set_val(33, system=SX, direction='From', flex_sys_dir=False)
        r[('fnB', 1, 'sfnB')].set_name('sfnB_From_Xx', system=SX, direction='From')
        assert r[('fnB', 1, 'sfnB')].val() == 11
        assert r[('fnB', 1, 'sfnB')].val(system=SX) == 33
        assert r[('fnB', 1, 'sfnB')].val(system=SX, direction='From') == 33
        assert r.node_child(('fnB', 1, 'sfnB')).val(system=SX) == 33
        assert r.node_child(('fnB', 1, 'sfnB')).val(system=SX, direction=None) == 33
        assert r.node_child('fnB1sfnB').val(system=SX) == 33
        assert r.node_child('fnB1sfnB_From_Xx').val(system=SX) == 33
        assert r.node_child('fnB1sfnB_From_Xx').val(system=SX) == 33

        # replace Records/Record children with Record child in fnB
        r.set_env(system=SX)
        sr = Record(fields=dict(sfnB_rec=66), field_items=True)
        # with pytest.raises(AssertionError):
        #     r['fnB'].set_value(sr, system=SX)
        with pytest.raises(AssertionError):
            r['fnB'].set_value(sr, protect=True)
        r['fnB'].set_value(sr)
        assert r.node_child(('fnB', 'sfnB_rec')).val(system=SX) == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system=SX, direction=None) == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system=SX, direction='') == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system=SX, direction=FAD_FROM) == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system=SX, direction=FAD_ONTO) == 66
        with pytest.raises(AssertionError):
            assert r.node_child(('fnB', 'sfnB_rec')).val(system=SX, direction='test') == 66

        r.set_env(system=SX, direction='From')
        assert r.node_child(('fnB', 'sfnB_rec')).val(system=SX) == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system=SX, direction=None) == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system=SX, direction='') == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system=SX, direction=FAD_FROM) == 66
        assert r.node_child(('fnB', 'sfnB_rec')).val(system=SX, direction=FAD_ONTO) == 66
        with pytest.raises(AssertionError):
            assert r.node_child(('fnB', 'sfnB_rec')).val(system=SX, direction='test') == 66

    def test_copy(self):
        r = Record()
        assert r.copy() == r
        assert r.copy() is not r

        r.add_fields(dict(fnA=33, fnB=66, fnC0sfnC=99))
        assert len(r) == 3
        assert r.copy() == r
        assert r.copy() is not r

        r2 = r.copy(filter_fields=lambda f: f.name() != 'fnB')
        assert len(r2) == 1
        assert r2.val('fnB') == 66

        r2 = r.copy(fields_patches=dict(fnB={aspect_key(FAT_VAL): Value((99, ))}))
        assert len(r2) == 3
        assert r2.val('fnB') == 99

        r2 = r.copy(fields_patches={ALL_FIELDS: {aspect_key(FAT_VAL): Value((99,))}})
        assert len(r2) == 3
        assert r2.val('fnB') == 99

    def test_pop(self):
        r = Record(fields=dict(a=1, b=2))
        assert len(r) == 2

        f = r.pop('b')
        assert isinstance(f, _Field)
        assert f.val() == 2
        assert len(r) == 1

    def test_pull(self):
        r = Record(fields=dict(fnA=-1), field_items=True)
        r['fnA'].set_name('fnA_systemXx', system=SX, direction=FAD_FROM)
        r['fnA'].set_val('33', system=SX, direction=FAD_FROM, converter=lambda fld, val: int(val))
        r.pull(SX)
        assert r.val('fnA') == 33
        assert r['fnA'].val() == 33
        assert r['fnA'].val(system=SX, direction=FAD_FROM) == '33'
        assert r['fnA'].val(system=SX) == '33'

        r.set_val('sfnBv', 'fnB', 0, 'sfnB', system=SX, direction=FAD_FROM)
        r.pull(SX)
        assert r.val('fnB0sfnB') == 'sfnBv'
        assert r['fnB0sfnB'].val() == 'sfnBv'
        assert r['fnB0sfnB'].val(system=SX, direction=FAD_FROM) == 'sfnBv'
        assert r['fnB0sfnB'].val(system=SX) == 'sfnBv'

    def test_push(self):
        r = Record(fields=dict(fnA=33), field_items=True)
        r['fnA'].set_name('fnA_systemXx', system=SX, direction=FAD_ONTO)
        r['fnA'].set_converter(lambda fld, val: str(val), system=SX, direction=FAD_ONTO)
        r.push(SX)
        assert r.val('fnA') == 33
        assert r['fnA'].val() == 33
        assert r['fnA'].val(system=SX, direction=FAD_ONTO) == '33'
        assert r['fnA'].val(system=SX) == '33'

    def test_set_env(self):
        r = Record().set_env(system=SX, direction=FAD_ONTO, action='ACTION')
        assert r.system == SX
        assert r.direction == FAD_ONTO
        assert r.action == 'ACTION'
    
    def test_add_system_fields_basic(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete.set_env(system=SX, direction=FAD_FROM)
        assert len(r) == 2
        assert len(list(r.leafs())) == 5

        r.add_system_fields((('fnAXx', 'fnA'), ('sfnX1Xx', 'fnX0sfnX1')))
        assert len(r) == 3
        assert len(list(r.leafs())) == 6
        assert r.node_child('fnA').name(system=SX, direction=FAD_FROM) == 'fnAXx'
        assert r.node_child('fnB0sfnA').name(system=SX, direction=FAD_FROM) == 'sfnA'
        assert r.node_child('fnB0sfnB').name(system=SX, direction=FAD_FROM) == 'sfnB'
        assert r.node_child('fnX0sfnX1').name(system=SX, direction=FAD_FROM) == 'sfnX1Xx'

        r.add_system_fields((('sfnAXx', 'fnB0sfnA'), ('sfnX2Xx', 'fnX0sfnX2')), extend=False)
        assert len(r) == 3
        assert len(list(r.leafs())) == 6
        assert r.node_child('fnB0sfnA').name(system=SX, direction=FAD_FROM) == 'sfnAXx'
        assert r.node_child('fnB0sfnB').name(system=SX, direction=FAD_FROM) == 'sfnB'
        assert r.node_child('fnX0sfnX2') is None

    def test_add_system_fields_complex(self):
        SEP = '.'
        d = (
            ('F_CNT', 'Cnt'),
            ('F/', ),
            ('F' + SEP + 'NAME', ('fn', 0, 'PersSurname'), lambda f: "Adult " + str(f.crx())
                if f.crx() is None or f.crx() < f.rfv('Cnt') else "Child " + str(f.crx() - f.rfv('Cnt') + 1),
             lambda f: f.ina(ACTION_DELETE) or not f.val() or f.rfv('F', 0, 'Id')),
            ('F' + SEP + 'NAME2', ('fn', 0, 'PersForename')),
            ('AUTO-GENERATED', None, '1',
             lambda f: f.ina(ACTION_DELETE) or (f.rfv('ResAdults') <= 2 and f.rfv('fn', f.crx(), 'Id'))),
            ('F' + SEP + 'MATCHCODE', ('fn', 0, 'Id')),
            ('ROOM-SEQ', None, '0',
             lambda f: f.ina(ACTION_DELETE)),
            ('PERS-SEQ', None, None,
             lambda f: f.ina(ACTION_DELETE),
             lambda f: (str(f.crx()))),
            ('F' + SEP + 'DOB', ('fn', 0, 'PersDOB'), None,
             lambda f: f.ina(ACTION_DELETE) or not f.val()),
            ('/F', None, None,
             lambda f: f.ina(ACTION_DELETE) or f.rfv('Cnt') <= 0),
        )
        sys_r = Record(system=SS, direction=FAD_ONTO)
        sys_r.add_system_fields(d)
        assert sys_r.val('Cnt') == ''

        data_r = Record(fields=dict(Cnt=2, fn0PersForename='John'))
        sys_r.clear_leafs()
        for k in data_r.leaf_indexes():
            if k[0] in sys_r:
                sys_r.set_val(data_r.val(k), *k, root_rec=data_r)
        sys_r.push(SS)
        assert sys_r.val('Cnt') == 2
        assert data_r.val('fn', 0, 'PersSurname') is None
        assert sys_r.val('fn', 0, 'PersSurname') == 'Adult 0'
        assert sys_r.val('fn', 0, 'PersSurname', system=SS, direction=FAD_ONTO) == 'Adult 0'

        assert data_r.val('fn', 0, 'PersForename') == 'John'
        assert sys_r.val('fn', 0, 'PersForename') == 'John'
        assert sys_r.val('fn', 0, 'PersForename', system=SS, direction=FAD_ONTO) == 'John'

        sys_r.set_val(0, 'Cnt')
        assert sys_r.val('fn', 0, 'PersSurname', system=SS, direction=FAD_ONTO) == 'Child 1'

        sys_r.set_val('Johnson', 'fn', 0, 'PersSurname')
        assert sys_r.val('fn', 0, 'PersSurname') == 'Child 1'   # != changed sys val because of flex_sys_dir=True
        sys_r.set_val('Johnson', 'fn', 0, 'PersSurname', flex_sys_dir=False)
        assert sys_r.val('fn', 0, 'PersSurname') == 'Johnson'   # .. now we are having a separate sys val
        sys_r.field_items = True
        sys_r['fn0PersSurname'].del_aspect(FAT_VAL, system=SS, direction=FAD_ONTO)
        assert sys_r.val('fn', 0, 'PersSurname') == 'Child 1'   # .. after delete of sys val: get main val/calculator

        sys_r.set_val(123456, 'fn0Id')
        sys_r.push(SS)

    def test_collect_system_fields(self):
        SEP = '.'
        r = Record(system=SX, direction=FAD_ONTO)
        r.add_system_fields((('Sys_Fld', 'Fld'),))
        csf = r.collect_system_fields(('Invalid_Fld',), SEP)
        assert not csf
        csf = r.collect_system_fields(('Sys_Fld',), SEP)
        assert len(csf) == 1
        assert isinstance(csf[0], _Field)
        assert csf[0].name() == 'Fld'
        assert csf[0].name(system=SX, direction=FAD_ONTO) == 'Sys_Fld'

    def test_compare_leafs(self):
        r = Record(fields=dict(fnA=33))
        assert not r.compare_leafs(Record(fields=dict(fnA=33)))
        assert not r.compare_leafs(Record(fields=dict(fnA=33, fnB=66)), field_names=('fnA',))
        assert not r.compare_leafs(Record(fields=dict(fnA=33, fnB=66)), exclude_fields=('fnB',))

        r = Record(fields=dict(fnA=33, fnB=66))
        assert not r.compare_leafs(Record(fields=dict(fnA=33, fnB=66)))
        assert not r.compare_leafs(Record(fields=dict(fnA=33, fnB=66)), field_names=('fnA',))
        assert not r.compare_leafs(Record(fields=dict(fnA=33, fnB=66)), exclude_fields=('fnB',))

        r = Record(fields=dict(fnA=33))
        assert len(r.compare_leafs(Record(fields=dict(fnA=99)))) == 1
        assert len(r.compare_leafs(Record(fields=dict(fnC=99)))) == 2

    def test_compare_val(self):
        d = datetime.date.today()
        r = Record(fields=dict(fnA=33, fnB='66', fnC=d))
        assert r.compare_val('fnA') == 33
        assert r.compare_val('fnB') == '66'
        assert r.compare_val('fnC') == d.toordinal()

        mail = 'test.mail@test_domain.net'
        pho = '00341234567890'
        r = Record(fields=dict(SfId='x' * 30, Name='jesus', Email=mail, Phone=pho, Long='x' * 80, Empty=''))
        assert r.compare_val('SfId') == 'x' * 15                    # SF-ID's get cut to 15 characters
        assert r.compare_val('Name') == 'Jesus'                     # Names get Capitalized
        assert r.compare_val('Email') == mail.replace('_', '')      # removing underscore in domain only!
        assert r.compare_val('Phone') == pho
        assert r.compare_val('Long') == 'x' * 39                    # Long strings speedup - only compare 1st 30 chars
        assert r.compare_val('Empty') is None

    def test_leaf_names(self, rec_2f_2s_complete, rec_2f_2s_incomplete):
        r = Record(fields=dict(fnA=33, fnB='66', fnC=datetime.date.today()))
        assert len(r.leaf_names()) == 3
        assert 'fnA' in r.leaf_names()      # field creation order is not guaranteed
        assert 'fnB' in r.leaf_names()
        assert 'fnC' in r.leaf_names()

        r = rec_2f_2s_complete
        assert len(r.leaf_names()) == 3
        assert r.leaf_names(field_names=('fnA',)) == ('fnA',)
        assert r.leaf_names(col_names=('fnA',)) == ('fnA',)
        assert r.leaf_names() == ('fnA', 'sfnA', 'sfnB')
        assert r.leaf_names(field_names=('Invalid_fn',)) == ()
        assert r.leaf_names(col_names=('Invalid_fn',)) == ()
        assert r.leaf_names(exclude_fields=('sfnA', 'sfnB')) == ('fnA', )
        assert r.leaf_names(exclude_fields=('fnA', 'sfnB')) == ('sfnA', )
        assert r.leaf_names(exclude_fields=('fnA', 'sfnA')) == ('sfnB', )

        assert r.leaf_names(exclude_fields=('fnA', 'sfnA'), name_type='s') == ('sfnB', )
        assert r.leaf_names(exclude_fields=('fnA', 'sfnA'), name_type='f') == ('sfnB', )
        assert r.leaf_names(exclude_fields=('fnA', 'sfnA'), name_type='r') == ('fnB0sfnB', )
        assert r.leaf_names(exclude_fields=('fnA', 'sfnA'), name_type='S') == (('fnB', 0, 'sfnB'),)
        assert r.leaf_names(exclude_fields=('fnA', 'sfnA'), name_type='F') == (('fnB', 0, 'sfnB'),)

        # repeat some tests - now with system field names added
        r.set_env(system=SX, direction=FAD_FROM)
        r.add_system_fields((('fnAXx', 'fnA'), ('sfnAXx', 'fnB0sfnA'), ('sfnBXx', 'fnB0sfnB')))
        assert len(r.leaf_names()) == 3
        assert r.leaf_names(field_names=('fnA',)) == ('fnA',)
        assert r.leaf_names(col_names=('fnAXx',)) == ('fnA',)
        assert r.leaf_names() == ('fnA', 'sfnA', 'sfnB')
        assert r.leaf_names(field_names=('Invalid_fn',)) == ()
        assert r.leaf_names(col_names=('Invalid_fn',)) == ()
        assert r.leaf_names(exclude_fields=('sfnA', 'sfnB')) == ('fnA', )
        assert r.leaf_names(exclude_fields=('fnA', 'sfnB')) == ('sfnA', )
        assert r.leaf_names(exclude_fields=('fnA', 'sfnA')) == ('sfnB', )

        assert r.leaf_names(exclude_fields=('fnA', 'sfnA'), name_type='s') == ('sfnBXx', )
        assert r.leaf_names(exclude_fields=('fnA', 'sfnA'), name_type='f') == ('sfnB', )
        assert r.leaf_names(exclude_fields=('fnA', 'sfnA'), name_type='r') == ('fnB0sfnB', )
        assert r.leaf_names(exclude_fields=('fnA', 'sfnA'), name_type='S') == (('fnB', 0, 'sfnBXx'),)
        assert r.leaf_names(exclude_fields=('fnA', 'sfnA'), name_type='F') == (('fnB', 0, 'sfnB'),)

        r = rec_2f_2s_incomplete
        assert len(r.leaf_names()) == 1
        assert r.leaf_names() == ('fnA',)
        assert r.leaf_names(field_names=('fnA',)) == ('fnA',)
        assert r.leaf_names(col_names=('fnA',)) == ('fnA',)
        assert r.leaf_names(field_names=('Invalid_fn',)) == ()
        assert r.leaf_names(col_names=('Invalid_fn',)) == ()
        assert r.leaf_names(exclude_fields=('fnA',)) == ()

    def test_merge_leafs(self, rec_2f_2s_complete, rec_2f_2s_incomplete):
        r = Record()
        assert len(r) == 0
        assert len(list(r.leafs())) == 0
        r.merge_leafs(rec_2f_2s_incomplete)
        assert len(r) == 2
        assert len(list(r.leafs())) == 3
        r.merge_leafs(rec_2f_2s_complete)
        assert len(r) == 2
        assert len(list(r.leafs())) == 5

    def test_match_key(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete
        assert r.match_key(()) == ()
        assert r.match_key(('fnA',)) == ('', )
        assert r.match_key(('fnA', 'fnB0sfnA', 'fnB0sfnB')) == ('', 'sfA1v', 'sfB1v')
        assert r.match_key(('fnA', 'fnB0sfnA', 'fnB1sfnB')) == ('', 'sfA1v', 'sfB2v')
        assert r.match_key(('fnB1sfnA', 'fnB1sfnB')) == ('sfA2v', 'sfB2v')

    def test_merge_vals(self, rec_2f_2s_complete, rec_2f_2s_incomplete):
        r = Record()
        assert len(r) == 0
        r.merge_vals(rec_2f_2s_complete, extend=False)
        assert len(r) == 0
        assert len(list(r.leafs())) == 0

        r.merge_vals(rec_2f_2s_incomplete)
        assert len(r) == 2
        assert len(list(r.leafs())) == 3
        assert not r.val('Invalid_fn')
        assert r.val('fnA') == ''
        assert r.val('fnB0sfnA') is None
        assert r.val('fnB0sfnB') is None
        assert r.val('fnB1sfnA') == ''
        assert r.val('fnB1sfnB') == 'sfB2v'

        r.merge_vals(rec_2f_2s_complete, extend=False)
        assert len(r) == 2
        assert len(list(r.leafs())) == 5
        assert not r.val('Invalid_fn')
        assert r.val('fnA') == ''
        assert r.val('fnB0sfnA') == 'sfA1v'
        assert r.val('fnB0sfnB') == 'sfB1v'
        assert r.val('fnB1sfnA') == 'sfA2v'
        assert r.val('fnB1sfnB') == 'sfB2v'

        r.merge_vals(rec_2f_2s_complete)
        assert len(r) == 2
        assert len(list(r.leafs())) == 5
        assert not r.val('Invalid_fn')
        assert r.val('fnA') == ''
        assert r.val('fnB0sfnA') == 'sfA1v'
        assert r.val('fnB0sfnB') == 'sfB1v'
        assert r.val('fnB1sfnA') == 'sfA2v'
        assert r.val('fnB1sfnB') == 'sfB2v'

    def test_missing_fields(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete
        assert r.missing_fields(('fnX', ('fnY', 'fnZ'))) == [('fnX',), ('fnY', 'fnZ')]
        assert r.missing_fields(('fnA', ('fnY', 'fnZ'))) == [('fnA',), ('fnY', 'fnZ')]  # fnA has empty value ('')
        assert r.missing_fields(('fnB', ('fnY', 'fnZ'))) == [('fnY', 'fnZ')]
        assert r.missing_fields(('fnB0sfnA', ('fnY', 'fnZ'))) == [('fnY', 'fnZ')]
        assert r.missing_fields(('fnB0sfnB', ('fnY', 'fnZ'))) == [('fnY', 'fnZ')]
        assert r.missing_fields(('fnB0sfnA', ('fnB0sfnB', 'fnY', 'fnZ'))) == []
        assert r.missing_fields(('fnX', 'fnB0sfnA', ('fnB0sfnB', 'fnY', 'fnZ'))) == [('fnX', )]

    def test_sql_columns(self, rec_2f_2s_complete):
        r = Record()
        assert r.sql_columns(SS) == list()

        r = rec_2f_2s_complete
        assert r.sql_columns(SS) == list()

        r = rec_2f_2s_complete.copy()
        r.set_env(system=SS, direction=FAD_ONTO).add_system_fields((('DbCol1', 'fnA'), ('DbCol2', 'fnX')))
        assert r.sql_columns(SS) == list()

        r = rec_2f_2s_complete.copy()
        r.set_env(system=SS, direction=FAD_FROM).add_system_fields((('DbCol1', 'fnA'), ('DbCol2', 'fnX')))
        assert r.sql_columns(SS) == ['DbCol1', 'DbCol2']

        r = rec_2f_2s_complete.copy()
        r.set_env(system=SS, direction=FAD_FROM).add_system_fields((('DbCol1', 'fnA'), ('DbCol2', 'fnX')))
        assert r.sql_columns(SS, col_names=('DbCol2',)) == ['DbCol2']

    def test_sql_select(self, rec_2f_2s_complete):
        r = Record()
        assert r.sql_select(SS) == list()

        r = rec_2f_2s_complete
        assert r.sql_select(SS) == list()

        r = rec_2f_2s_complete.copy()
        r.set_env(system=SS, direction=FAD_ONTO).add_system_fields((('DbCol1', 'fnA'), ('DbCol2', 'fnX')))
        assert r.sql_select(SS) == list()

        r = rec_2f_2s_complete.copy()
        r.set_env(system=SS, direction=FAD_FROM).add_system_fields((('DbCol1', 'fnA'), ('DbCol2', 'fnX')))
        assert r.sql_select(SS) == ['DbCol1', 'DbCol2']

        r = rec_2f_2s_complete.copy()
        r.set_env(system=SS, direction=FAD_FROM).add_system_fields((('DbCol1', 'fnA'), ('DbCol2', 'fnX')))
        assert r.sql_select(SS, col_names=('DbCol2',)) == ['DbCol2']

        r = rec_2f_2s_complete.copy()
        r.set_env(system=SS, direction=FAD_FROM).add_system_fields((('DbCol1', 'fnA'), ('DbCol2', 'fnX')))
        r.node_child('fnX').set_sql_expression('db_expr')
        assert r.sql_select(SS, col_names=('DbCol2',)) == ['DbCol2']

        r = rec_2f_2s_complete.copy()
        r.set_env(system=SS, direction=FAD_FROM).add_system_fields((('DbCol1', 'fnA'), ('DbCol2', 'fnX')))
        r.node_child('fnX').set_sql_expression('db_expr', system=SS, direction=FAD_FROM)
        assert r.sql_select(SS, col_names=('DbCol2',)) == ['db_expr AS DbCol2']

    def test_to_dict(self, rec_2f_2s_complete):
        r = Record()
        assert r.to_dict() == dict()

        r = rec_2f_2s_complete.copy()
        assert r.to_dict() == dict(fnB0sfnA='sfA1v', fnB0sfnB='sfB1v', fnB1sfnA='sfA2v', fnB1sfnB='sfB2v')
        assert r.to_dict(filter_fields=lambda f: f.name() == 'sfnB') == dict(fnB0sfnA='sfA1v', fnB1sfnA='sfA2v')
        assert r.to_dict(put_empty_val=True) == dict(fnA='',
                                                     fnB0sfnA='sfA1v', fnB0sfnB='sfB1v',
                                                     fnB1sfnA='sfA2v', fnB1sfnB='sfB2v')
        assert r.to_dict(put_system_val=False) == dict(fnB0sfnA='sfA1v', fnB0sfnB='sfB1v',
                                                       fnB1sfnA='sfA2v', fnB1sfnB='sfB2v')
        assert r.to_dict(key_type=None) == dict(sfnA='sfA2v', sfnB='sfB2v')
        assert r.to_dict(key_type=tuple) == {('fnB', 0, 'sfnA'): 'sfA1v', ('fnB', 0, 'sfnB'): 'sfB1v',
                                             ('fnB', 1, 'sfnA'): 'sfA2v', ('fnB', 1, 'sfnB'): 'sfB2v'}
        assert r.to_dict(put_system_val=False, key_type=None) == dict(sfnA='sfA2v', sfnB='sfB2v')
        assert r.to_dict(put_empty_val=True, key_type=None) == dict(fnA='', sfnA='sfA2v', sfnB='sfB2v')

        r = rec_2f_2s_complete.copy().set_env(system=SX, direction=FAD_ONTO)
        r.add_system_fields((('fnAX', 'fnA'), ('sfnAX', 'fnB0sfnA'), ('sfnBX', 'fnB0sfnB')))
        assert r.to_dict() == dict(fnB0sfnAX='sfA1v', fnB0sfnBX='sfB1v', fnB1sfnAX='sfA2v', fnB1sfnBX='sfB2v')
        assert r.to_dict(use_system_key=False) == dict(fnB0sfnA='sfA1v', fnB0sfnB='sfB1v',
                                                       fnB1sfnA='sfA2v', fnB1sfnB='sfB2v')
        assert r.to_dict(filter_fields=lambda f: f.name() == 'sfnB') == dict(fnB0sfnAX='sfA1v', fnB1sfnAX='sfA2v')
        assert r.to_dict(filter_fields=lambda f: f.name() == 'sfnB', use_system_key=False) == dict(fnB0sfnA='sfA1v',
                                                                                                   fnB1sfnA='sfA2v')
        assert r.to_dict(put_empty_val=True) == dict(fnAX='',
                                                     fnB0sfnAX='sfA1v', fnB0sfnBX='sfB1v',
                                                     fnB1sfnAX='sfA2v', fnB1sfnBX='sfB2v')
        assert r.to_dict(put_system_val=False) == dict(fnB0sfnAX='sfA1v', fnB0sfnBX='sfB1v',
                                                       fnB1sfnAX='sfA2v', fnB1sfnBX='sfB2v')
        assert r.to_dict(key_type=None) == dict(sfnAX='sfA2v', sfnBX='sfB2v')
        assert r.to_dict(key_type=tuple) == {('fnB', 0, 'sfnAX'): 'sfA1v', ('fnB', 0, 'sfnBX'): 'sfB1v',
                                             ('fnB', 1, 'sfnAX'): 'sfA2v', ('fnB', 1, 'sfnBX'): 'sfB2v'}
        assert r.to_dict(put_system_val=False, key_type=None) == dict(sfnAX='sfA2v', sfnBX='sfB2v')
        assert r.to_dict(put_empty_val=True, key_type=None) == dict(fnAX='', sfnAX='sfA2v', sfnBX='sfB2v')

    def test_update(self):
        r = Record()
        assert r.update() is r


class TestRecords:
    def test_typing(self):
        assert isinstance(Records(), Records)
        assert isinstance(Records(), list)

    def test_repr_eval(self):
        _ = Values      # added for to remove Pycharm warning
        rec_str = repr(Records())
        assert eval(rec_str) == Records()

    def test_get_item(self):
        rs = Records()

        rs.set_val('fnAv1', 0, 'fnA')
        assert isinstance(rs[0], Record)
        assert len(rs) == 1
        assert rs.val(0, 'fnA') == 'fnAv1'

        rs.set_val('fnAv2', 1, 'fnA')
        assert isinstance(rs[1], Record)
        assert len(rs) == 2
        assert rs.val(1, 'fnA') == 'fnAv2'

        assert isinstance(rs[0:1], list)
        assert isinstance(rs[1:2], list)
        assert isinstance(rs[0:2], list)

        with pytest.raises(AssertionError):
            _ = rs[(0, 'fnA', 'Invalid')]

    def test_set_val_flex_sys(self):
        rs = Records()
        rs.set_val('fAv', 0, 'fnA', 0, 'sfnA')
        assert rs.val(0, 'fnA', 0, 'sfnA') == 'fAv'
        rs.set_val('fAvX', 0, 'fnA', 0, 'sfnA', system=SX)
        assert rs.val(0, 'fnA', 0, 'sfnA', system=SX) == 'fAvX'
        assert rs.val(0, 'fnA', 0, 'sfnA') == 'fAvX'

    def test_set_val_exact_sys(self):
        rs = Records()
        rs.set_val('fAv', 0, 'fnA', 0, 'sfnA')
        assert rs.val(0, 'fnA', 0, 'sfnA') == 'fAv'
        rs.set_val('fAvX', 0, 'fnA', 0, 'sfnA', flex_sys_dir=False, system=SX)
        assert rs.val(0, 'fnA', 0, 'sfnA', system=SX) == 'fAvX'
        assert rs.val(0, 'fnA', 0, 'sfnA') == 'fAv'

    def test_set_val_sys_converter(self):
        rs = Records()
        rs.set_val('fAv', 0, 'fnA', 0, 'sfnA')
        assert rs.val(0, 'fnA', 0, 'sfnA') == 'fAv'
        rs.set_val('fAvX', 0, 'fnA', 0, 'sfnA', system=SX, converter=lambda f, v: v)
        assert rs.val(0, 'fnA', 0, 'sfnA', system=SX) == 'fAvX'
        assert rs.val(0, 'fnA', 0, 'sfnA') == 'fAv'

    def test_val_get(self):
        rs = Records()
        assert rs.val() == list()
        assert rs.val(0) is None
        assert rs.val('test') is None
        assert rs.val(12, 'sub_field') is None
        assert rs.val('sub_field', 12, '2nd_sub_field') is None

        rs.append(Record())
        assert rs.val(0) == OrderedDict()

    def test_set_field(self):
        rs = Records()
        rs.set_node_child(12, 4, 'fnA', protect=True)
        assert rs.val(4, 'fnA') == 12
        rs.set_node_child(33, 4, 'fnA')
        assert rs.val(4, 'fnA') == 33

        rs[2].set_val(99, 'sfnA')
        assert rs.val(2, 'sfnA') == 99

    def test_get_value(self):
        rs = Records()
        assert not rs.value()
        assert isinstance(rs.value(), list)
        assert isinstance(rs.value(), Records)
        rs.append(Record())
        assert rs.value()
        assert rs.value() == Records((Record(), ))
        assert len(rs.value()) == 1
        rs.set_node_child(33, 3, 'fnA')
        assert len(rs.value()) == 4
        assert rs.value(3, 'fnA') == Value((33, ))

    def test_set_value(self):
        rs = Records()
        rs.set_node_child(33, 3, 'fnA')
        assert rs.value(3, 'fnA').val() == 33
        rs.set_value(Value().set_val(66), 3, 'fnA')
        assert rs.value(3, 'fnA').val() == 66
        rs.set_value(Value().set_val(99), 3, 'fnA', root_rec=Record(), root_idx=('root_fn',))
        assert rs.value(3, 'fnA').val() == 99

    def test_clear_leafs(self):
        rs = Records()
        assert len(rs) == 0
        rs.clear_leafs()
        assert len(rs) == 0

        rs.set_node_child(33, 3, 'fnA')
        assert len(rs) == 4

        rs.clear_leafs(reset_lists=False)
        assert rs.value(3, 'fnA').val() == ''
        assert len(rs) == 4

        rs.clear_leafs()
        assert rs.val(3, 'fnA') is None
        assert len(rs) == 1

    def test_append_sub_record(self):
        r1 = Record(fields=dict(fnA=1, fnB0sfnA=2, fnB0sfnB=3))
        assert len(r1.value('fnB')) == 1
        assert r1.val('fnB', 0, 'sfnA') == 2
        assert r1.val('fnB', 0, 'sfnB') == 3
        assert r1.val('fnB', 1, 'sfnA') is None
        assert r1.val('fnB', 1, 'sfnB') is None
        assert r1.val('fnB', 2, 'sfnA') is None
        assert r1.val('fnB', 2, 'sfnB') is None

        r1.value('fnB').append_record(root_rec=r1, root_idx=('fnB', ))
        assert len(r1.value('fnB')) == 2
        assert r1.val('fnB', 0, 'sfnA') == 2
        assert r1.val('fnB', 0, 'sfnB') == 3
        assert r1.val('fnB', 1, 'sfnA') == ''
        assert r1.val('fnB', 1, 'sfnB') == ''

        r1.node_child('fnB').append_record(root_rec=r1, root_idx=('fnB', ))
        assert len(r1.value('fnB')) == 3
        assert r1.val('fnB', 0, 'sfnA') == 2
        assert r1.val('fnB', 0, 'sfnB') == 3
        assert r1.val('fnB', 1, 'sfnA') == ''
        assert r1.val('fnB', 1, 'sfnB') == ''
        assert r1.val('fnB', 2, 'sfnA') == ''
        assert r1.val('fnB', 2, 'sfnB') == ''

    def test_append_sub_record_to_foreign_records(self):
        r1 = Record(fields=dict(fnA=1, fnB0sfnA=2, fnB0sfnB=3),
                    field_items=True)
        assert len(r1.value('fnB')) == 1
        assert r1.val('fnB', 0, 'sfnA') == 2
        assert r1.val('fnB', 0, 'sfnB') == 3
        assert r1.val('fnB', 1, 'sfnA') is None
        assert r1.val('fnB', 1, 'sfnB') is None
        assert r1.val('fnB', 2, 'sfnA') is None
        assert r1.val('fnB', 2, 'sfnB') is None

        r2 = Record(fields=dict(fnA=7, fnB1sfnA=8, fnB1sfnB=9),
                    field_items=True)
        assert len(r2.value('fnB')) == 2
        assert r2.val('fnB', 0, 'sfnA') is None
        assert r2.val('fnB', 0, 'sfnB') is None
        assert r2.val('fnB', 1, 'sfnA') == 8
        assert r2.val('fnB', 1, 'sfnB') == 9
        assert r2.val('fnB', 2, 'sfnA') is None
        assert r2.val('fnB', 2, 'sfnB') is None

        r2.value('fnB').append_record(root_rec=r2, root_idx=('fnB', ), from_rec=r1.value('fnB', 0), clear_leafs=False)
        assert r2.val('fnB', 2, 'sfnA') == 2
        assert r2.val('fnB', 2, 'sfnB') == 3
        assert r2['fnB'].root_rec() is r2
        assert r2[('fnB', 2, 'sfnB')].root_rec() is r2
        assert r2['fnB'].root_idx() == ('fnB', )
        assert r2[('fnB', 2, 'sfnB')].root_idx() == ('fnB', 2, 'sfnB')

        r1.value('fnB').append_record(root_rec=r1, root_idx=('fnB', ), from_rec=r2.value('fnB', 1), clear_leafs=False)
        assert r1.val('fnB', 1, 'sfnA') == 8
        assert r1.val('fnB', 1, 'sfnB') == 9
        assert r1['fnB'].root_rec() is r1
        assert r1[('fnB', 1, 'sfnB')].root_rec() is r1
        assert r1['fnB'].root_idx() == ('fnB', )
        assert r1[('fnB', 1, 'sfnB')].root_idx() == ('fnB', 1, 'sfnB')

    def test_compare_records(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete
        rs1 = r.value('fnB').copy(deepness=-1, root_rec=r, root_idx=('fnB',))
        assert len(rs1.compare_records(Records(), ('sfnA', 'sfnB'))) == 2

        rs2 = r.value('fnB').copy(deepness=-1, root_rec=r, root_idx=('fnB',))
        assert len(rs1.compare_records(rs2, ('sfnA', 'sfnB'))) == 0

        rs2.set_val('ChangedVal', 0, 'sfnA')
        assert len(rs1.compare_records(rs2, ('sfnA', 'sfnB'))) == 2

        assert len(rs1.compare_records(rs2, ('sfnA', 'sfnB'), record_comparator=lambda r1, r2: list())) == 3

        assert len(rs1.compare_records(rs2, ('sfnA', 'sfnB'), record_comparator=lambda r1, r2: ['AAA'])) == 9

        assert len(rs1.compare_records(rs2, ('sfnA', 'sfnB'), record_comparator=lambda r1, r2: ['AAA', 'BBB'])) == 17

    def test_merge_records(self, rec_2f_2s_complete):
        rs1 = Records()
        assert len(rs1) == 0
        rs2 = rec_2f_2s_complete.value('fnB').copy(deepness=-1, root_rec=rec_2f_2s_complete, root_idx=('fnB',))

        assert rs1.merge_records(rs2) is rs1
        assert len(rs1) == len(rs2)
        assert rs1 == rs2

        assert rs1.merge_records(rs2, ('sfnA', )) is rs1
        assert len(rs1) == len(rs2)
        assert rs1 == rs2

        old_len = len(rs1)
        rs2.set_val('changed_val', 0, 'sfnA')
        assert rs1.merge_records(rs2, ('sfnA', )) is rs1
        assert len(rs1) == old_len + 1


class TestStructures:
    def test_idx_key(self, rec_2f_2s_incomplete):
        assert isinstance(rec_2f_2s_incomplete['fnB'], list)
        assert isinstance(rec_2f_2s_incomplete[('fnB',)], list)

        assert isinstance(rec_2f_2s_incomplete[('fnB', 1)], dict)

        assert isinstance(rec_2f_2s_incomplete[('fnB', 1, 'sfnB')], str)
        assert isinstance(rec_2f_2s_incomplete['fnB1sfnB'], str)

        assert rec_2f_2s_incomplete.val('fnB', 1, 'sfnB') == 'sfB2v'
        assert rec_2f_2s_incomplete[('fnB', 1, 'sfnB')] == 'sfB2v'
        assert rec_2f_2s_incomplete['fnB1sfnB'] == 'sfB2v'

    def test_idx_key_with_field_items(self, rec_2f_2s_incomplete):
        rec_2f_2s_incomplete.field_items = True
        assert isinstance(rec_2f_2s_incomplete['fnB'].value(), Records)
        assert isinstance(rec_2f_2s_incomplete[('fnB',)].value(), Records)

        assert isinstance(rec_2f_2s_incomplete[('fnB', 1)], Record)
        assert isinstance(rec_2f_2s_incomplete[('fnB',)].value(1), Record)

        assert isinstance(rec_2f_2s_incomplete[('fnB', 1, 'sfnB')].value(), Value)

        assert isinstance(rec_2f_2s_incomplete['fnB'].value(1, 'sfnB'), Value)
        assert isinstance(rec_2f_2s_incomplete[('fnB',)].value(1, 'sfnB'), Value)
        assert isinstance(rec_2f_2s_incomplete['fnB'][1].value('sfnB'), Value)

        rec_2f_2s_incomplete['fnB'][1].field_items = True
        assert isinstance(rec_2f_2s_incomplete['fnB'][1]['sfnB'].value(), Value)

        assert rec_2f_2s_incomplete.val('fnB', 1, 'sfnB') == 'sfB2v'
        assert rec_2f_2s_incomplete['fnB'].value(1, 'sfnB').val() == 'sfB2v'
        assert rec_2f_2s_incomplete[('fnB',)].value(1, 'sfnB').val() == 'sfB2v'
        assert rec_2f_2s_incomplete[('fnB', 1)]['sfnB'].val() == 'sfB2v'
        assert rec_2f_2s_incomplete[('fnB', 1, 'sfnB')].val() == 'sfB2v'
        assert rec_2f_2s_incomplete['fnB', 1, 'sfnB'].val() == 'sfB2v'

        assert rec_2f_2s_incomplete['fnB1sfnB'].val() == 'sfB2v'

    def test_leafs(self, rec_2f_2s_incomplete, rec_2f_2s_complete):
        r = rec_2f_2s_incomplete
        leafs = list(r.leafs())
        assert len(leafs) == 3
        leafs = list(r.leafs(flex_sys_dir=False))
        assert len(leafs) == 3
        leafs = list(r.leafs(system='', direction=''))
        assert len(leafs) == 3
        leafs = list(r.leafs(system='', direction='', flex_sys_dir=False))
        assert len(leafs) == 3
        leafs = list(r.leafs(system=SX, direction=FAD_ONTO))
        assert len(leafs) == 3
        leafs = list(r.leafs(system=SX, direction=FAD_ONTO, flex_sys_dir=False))
        assert len(leafs) == 0

        r.set_env(system=SX, direction=FAD_ONTO)
        leafs = list(r.leafs())
        assert len(leafs) == 3
        leafs = list(r.leafs(flex_sys_dir=False))
        assert len(leafs) == 0
        leafs = list(r.leafs(system='', direction=''))
        assert len(leafs) == 3
        leafs = list(r.leafs(system='', direction='', flex_sys_dir=False))
        assert len(leafs) == 3
        leafs = list(r.leafs(system=SX, direction=FAD_ONTO))
        assert len(leafs) == 3
        leafs = list(r.leafs(system=SX, direction=FAD_ONTO, flex_sys_dir=False))
        assert len(leafs) == 0

        r.add_system_fields((('fnAXx', 'fnA'), ('sfnAXx', 'fnB0sfnA'), ('sfnBXx', 'fnB0sfnB')))
        leafs = list(r.leafs())
        assert len(leafs) == 5
        leafs = list(r.leafs(flex_sys_dir=False))
        assert len(leafs) == 5
        leafs = list(r.leafs(system='', direction=''))
        assert len(leafs) == 5
        leafs = list(r.leafs(system='', direction='', flex_sys_dir=False))
        assert len(leafs) == 5
        leafs = list(r.leafs(system=SX, direction=FAD_ONTO))
        assert len(leafs) == 5
        leafs = list(r.leafs(system=SX, direction=FAD_ONTO, flex_sys_dir=False))
        assert len(leafs) == 5

        r = rec_2f_2s_complete
        leafs = list(r.leafs())
        assert len(leafs) == 5
        leafs = list(r.leafs(flex_sys_dir=False))
        assert len(leafs) == 5
        leafs = list(r.leafs(system='', direction=''))
        assert len(leafs) == 5
        leafs = list(r.leafs(system='', direction='', flex_sys_dir=False))
        assert len(leafs) == 5
        leafs = list(r.leafs(system=SX, direction=FAD_ONTO))
        assert len(leafs) == 5
        leafs = list(r.leafs(system=SX, direction=FAD_ONTO, flex_sys_dir=False))
        assert len(leafs) == 0

        r.set_env(system=SX, direction=FAD_ONTO)
        leafs = list(r.leafs())
        assert len(leafs) == 5
        leafs = list(r.leafs(flex_sys_dir=False))
        assert len(leafs) == 0
        leafs = list(r.leafs(system='', direction=''))
        assert len(leafs) == 5
        leafs = list(r.leafs(system='', direction='', flex_sys_dir=False))
        assert len(leafs) == 5
        leafs = list(r.leafs(system=SX, direction=FAD_ONTO))
        assert len(leafs) == 5
        leafs = list(r.leafs(system=SX, direction=FAD_ONTO, flex_sys_dir=False))
        assert len(leafs) == 0

        r.add_system_fields((('fnAXx', 'fnA'), ('sfnAXx', 'fnB0sfnA'), ('sfnBXx', 'fnB0sfnB')))
        leafs = list(r.leafs())
        assert len(leafs) == 5
        leafs = list(r.leafs(flex_sys_dir=False))
        assert len(leafs) == 5
        leafs = list(r.leafs(system='', direction=''))
        assert len(leafs) == 5
        leafs = list(r.leafs(system='', direction='', flex_sys_dir=False))
        assert len(leafs) == 5
        leafs = list(r.leafs(system=SX, direction=FAD_ONTO))
        assert len(leafs) == 5
        leafs = list(r.leafs(system=SX, direction=FAD_ONTO, flex_sys_dir=False))
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
        assert rec_2f_2s_incomplete.val('fnB', 1, 'sfnB') == 'sfB2v'
        assert r1c.val('fnB', 1, 'sfnB') == 'sfB2v'

        rec_2f_2s_incomplete.value('fnB', 1, 'sfnB').set_val('sfB2v_new')
        assert rec_2f_2s_incomplete.val('fnB', 1, 'sfnB') == 'sfB2v_new'
        assert r1c.val('fnB', 1, 'sfnB') == 'sfB2v_new'

    def test_deep_copy_record(self, rec_2f_2s_incomplete):
        r1c = rec_2f_2s_incomplete.copy(deepness=-1)
        # STRANGE crashing in: assert rec_2f_2s_incomplete == r1c
        assert id(rec_2f_2s_incomplete) != id(r1c)
        assert rec_2f_2s_incomplete is not r1c

        assert id(rec_2f_2s_incomplete['fnA']) != id(r1c.node_child(('fnA', )))
        assert rec_2f_2s_incomplete['fnA'] is not r1c.node_child(('fnA', ))

        assert rec_2f_2s_incomplete.value('fnA') == r1c.value('fnA')
        assert id(rec_2f_2s_incomplete.value('fnA')) != id(r1c.value('fnA'))
        assert rec_2f_2s_incomplete.value('fnA') is not r1c.value('fnA')

        # STRANGE failing until implementation of _Field.__eq__: assert rec_2f_2s_incomplete['fnB'] == r1c['fnB']
        assert id(rec_2f_2s_incomplete['fnB']) != id(r1c.node_child('fnB'))
        assert rec_2f_2s_incomplete['fnB'] is not r1c.node_child(('fnB', ))

        # STRANGE crashing in: assert rec_2f_2s_incomplete['fnB'][1] == r1c['fnB'][1]
        assert id(rec_2f_2s_incomplete['fnB'][1]) != id(r1c.node_child(('fnB', 1, )))
        assert rec_2f_2s_incomplete['fnB'][1] is not r1c.node_child(('fnB', 1))

        assert id(rec_2f_2s_incomplete.value('fnB', 1, 'sfnB')) != id(r1c.value('fnB', 1, 'sfnB'))
        assert rec_2f_2s_incomplete.value('fnB', 1, 'sfnB') is not r1c.value('fnB', 1, 'sfnB')

        assert rec_2f_2s_incomplete.value('fnB', 1, 'sfnB') == r1c.value('fnB', 1, 'sfnB')

        assert rec_2f_2s_incomplete[('fnB', 1, 'sfnB')] == 'sfB2v'
        assert r1c[('fnB', 1, 'sfnB')] == 'sfB2v'

        rec_2f_2s_incomplete.set_val('sfB2v_new', 'fnB', 1, 'sfnB')
        assert rec_2f_2s_incomplete[('fnB', 1, 'sfnB')] == 'sfB2v_new'
        rec_2f_2s_incomplete.node_child(('fnB', 1, )).field_items = False
        assert rec_2f_2s_incomplete[('fnB', 1, 'sfnB')] == 'sfB2v_new'

        r1c.field_items = True      # field_items value currently not copied
        assert r1c[('fnB', 1, 'sfnB')].val() == 'sfB2v'

    def test_flat_copy_record(self, rec_2f_2s_incomplete):
        # test flattening copy into existing record (r2)
        r2 = Record(fields={('fnB', 1, 'sfnB'): 'sfB2v_old'})
        assert r2[('fnB', 1, 'sfnB')] == 'sfB2v_old'
        r3 = r2.copy(onto_rec=rec_2f_2s_incomplete)
        print(r3)
        assert rec_2f_2s_incomplete != r2
        assert rec_2f_2s_incomplete is not r2
        assert rec_2f_2s_incomplete == r3
        assert rec_2f_2s_incomplete is r3
        assert rec_2f_2s_incomplete[('fnB', 1, 'sfnB')] == 'sfB2v'
        assert r2[('fnB', 1, 'sfnB')] == 'sfB2v_old'
        assert r3[('fnB', 1, 'sfnB')] == 'sfB2v'


class TestSystemDirections:
    def test_multi_sys_name_rec(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete
        rX = r.copy().set_env(system=SX, direction=FAD_FROM)
        rX.add_system_fields((('fnAXx', 'fnA'), ('sfnAXx', 'fnB0sfnA'), ('sfnBXx', 'fnB0sfnB')))
        rY = r.copy().set_env(system=SY, direction=FAD_ONTO)
        rY.add_system_fields((('fnAYy', 'fnA'), ('sfnAYy', 'fnB0sfnA'), ('sfnBYy', 'fnB0sfnB')))
        for idx in r.leaf_indexes():
            if len(idx) > 1 and idx[1] > 0:
                continue
            assert r.node_child(idx).name(system=SX) == r.node_child(idx).name() + SX
            assert r.node_child(idx).name(system=SY) == r.node_child(idx).name() + SY

    def test_multi_sys_val_rec(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete
        rX = r.copy().set_env(system=SX, direction=FAD_FROM)
        rX.add_system_fields((('fnAXx', 'fnA', 0),
                              ('sfnAXx', 'fnB0sfnA', 1), ('sfnBXx', 'fnB0sfnB', 2),
                              ('sfnAXx', 'fnB1sfnA', 3), ('sfnBXx', 'fnB1sfnB', 4)))
        for i, idx in enumerate(r.leaf_indexes()):
            assert r[idx] == i
            assert r.val(*idx, system=SX) == i

        rY = r.copy().set_env(system=SY, direction=FAD_ONTO)
        rY.add_system_fields((('fnAXx', 'fnA', 5),
                              ('sfnAXx', 'fnB0sfnA', 6), ('sfnBXx', 'fnB0sfnB', 7),
                              ('sfnAXx', 'fnB1sfnA', 8), ('sfnBXx', 'fnB1sfnB', 9)))
        for i, idx in enumerate(r.leaf_indexes()):
            assert r[idx] == i + 5
            assert r.val(*idx, system=SX) == i + 5
            assert r.val(*idx, system=SY) == i + 5

    def test_multi_sys_converter_rec(self, rec_2f_2s_complete):
        # PyCharm doesn't like assignments of lambda to vars: cnv = lambda f, v: v + 10
        def cnv(_, v):
            return v + 10

        r = rec_2f_2s_complete
        rX = r.copy().set_env(system=SX, direction=FAD_FROM)
        rX.add_system_fields((('fnAXx', 'fnA', 0, cnv),
                              ('sfnAXx', 'fnB0sfnA', 1, cnv), ('sfnBXx', 'fnB0sfnB', 2, cnv),
                              ('sfnAXx', 'fnB1sfnA', 3, cnv), ('sfnBXx', 'fnB1sfnB', 4, cnv)),
                             sys_fld_indexes={FAT_IDX + FAD_FROM: 0, FAT_IDX: 1, FAT_VAL: 2, FAT_CNV: 3})
        for i, idx in enumerate(r.leaf_indexes()):
            assert isinstance(r.val(*idx), str)
            assert r.val(*idx) in ('', 'sfA1v', 'sfA2v', 'sfB1v', 'sfB2v')
            assert r.val(*idx, system=SX) == i
            r.node_child(idx).pull(SX, r, idx)
            assert r.val(*idx) == i + 10
            assert r.val(*idx, system=SX) == i

    def test_multi_sys_dir_converter_rec(self, rec_2f_2s_complete):
        # PyCharm doesn't like assignments of lambda to vars: cnv = lambda f, v: v + 10
        def cnv(_, v):
            return v + 10

        r = rec_2f_2s_complete
        rX = r.copy().set_env(system=SX, direction=FAD_FROM)
        rX.add_system_fields((('fnAXx', 'fnA', 0, cnv),
                              ('sfnAXx', 'fnB0sfnA', 1, cnv), ('sfnBXx', 'fnB0sfnB', 2, cnv),
                              ('sfnAXx', 'fnB1sfnA', 3, cnv), ('sfnBXx', 'fnB1sfnB', 4, cnv)),
                             sys_fld_indexes={FAT_IDX + FAD_FROM: 0, FAT_IDX: 1, FAT_VAL: 2, FAT_CNV + FAD_FROM: 3})
        for i, idx in enumerate(r.leaf_indexes()):
            assert isinstance(r.val(*idx), str)
            assert r.val(*idx) in ('', 'sfA1v', 'sfA2v', 'sfB1v', 'sfB2v')
            assert r.val(*idx, system=SX) == i
            r.node_child(idx).pull(SX, r, idx)
            assert r.val(*idx) == i + 10
            assert r.val(*idx, system=SX) == i

    def test_shorter_sys_idx_path(self, rec_2f_2s_complete):
        r = rec_2f_2s_complete
        str_val = "KEY1=val1,KEY2=val2,RCI=val3"
        rX = r.copy().set_env(system=SX, direction=FAD_FROM)
        rX.add_system_fields((('fnAXx', 'fnA'),
                              ('fnBXx', 'fnB', str_val, lambda f, v: f.string_to_records(v, ['sfnA', 'sfnB']))),
                             sys_fld_indexes={FAT_IDX + FAD_FROM: 0, FAT_IDX: 1, FAT_VAL: 2, FAT_CNV + FAD_FROM: 3})
        r.pull(SX)
        assert r.val('fnB', 0, 'sfnA') == 'KEY1'
        assert r.val('fnB', 0, 'sfnB') == 'val1'
        assert r.val('fnB', 1, 'sfnA') == 'KEY2'
        assert r.val('fnB', 1, 'sfnB') == 'val2'
        assert r.val('fnB', 2, 'sfnA') == 'RCI'
        assert r.val('fnB', 2, 'sfnB') == 'val3'

        rY = r.copy().set_env(system=SY, direction=FAD_ONTO)
        rY.add_system_fields((('fnAXx', 'fnA'),
                              ('fnBXx', 'fnB',
                               lambda _, val: ",".join(k + "=" + v for rec in val for k, v in rec.items()))),
                             sys_fld_indexes={FAT_IDX + FAD_ONTO: 0, FAT_IDX: 1, FAT_CNV + FAD_ONTO: 3})
        r.pull(SX)
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
        rX = r.copy().set_env(system=SX, direction=FAD_FROM)
        rX.add_system_fields((('fnAXx', 'fnA'),
                              ('sfnAXx', 'fnB0sfnA'), ('sfnBXx', 'fnB0sfnB'),
                              ('sfnAXx', 'fnB1sfnA'), ('sfnBXx', 'fnB1sfnB')))

        rX.set_val(1, 'fnA', system=SX, direction=FAD_FROM, flex_sys_dir=False)
        # sys/dir priorities: 1st=sys-name, 2nd=sys-rec, 3rd=system kwarg
        assert r.val('fnA') == ''               # field name idx 'fnA' and non-sys rec DOES NEVER use sys val
        assert r.val('fnAXx') == 1              # sys_name idx 'fnAXx' with non-sys Record DOES ALWAYS use sys val
        assert rX.val('fnA') == 1               # field name idx 'fnA' with sys Record DOES use sys val
        assert rX.val('fnAXx') == 1             # sys_name idx 'fnAXx' with or w/o sys Record DOES use sys val
        assert rX.val('fnAXx', system='N') == 1  # even sys_name with unknown system DOES use sys val
        assert r.val('fnAXx', system='') == 1   # sys_name with system=='' DOES use sys val (overwrites system kwarg)
        assert r.val('fnAXx') == 1
        assert r.val('fnAXx', system=SX) == 1
        assert r.val('fnA', system=SX) == 1

        # check for deep field; sys_name idx 'sfnBXx' will ALWAYS use sys val
        rX.set_val(3, 'fnB', 1, 'sfnB', system=SX, direction=FAD_FROM, flex_sys_dir=False)
        assert r.val('fnB', 1, 'sfnBXx') == 3
        assert r.val('fnB', 1, 'sfnB') == 'sfB2v'
        assert r.val('fnB', 1, 'sfnBXx', system=SX) == 3
        assert r.val('fnB', 1, 'sfnB', system=SX) == 3

        # .. but sys rec (rX) does if not accessed via field - even if using main field name
        assert rX['fnB', 1, 'sfnB'] == 3
        assert rX.val('fnB', 1, 'sfnB') == 3
        assert rX.val('fnB', 1, 'sfnB', system='', direction='') == 'sfB2v'
        assert rX['fnB', 1, 'sfnBXx'] == 3
        assert rX.val('fnB', 1, 'sfnBXx') == 3

        rX.field_items = True               # test with field_items
        assert rX.val('fnA') == 1           # .. sys rec val also use sys val - even if using main field name
        assert rX.val('fnAXx') == 1
        assert rX['fnA'].val() == ''        # .. BUT accessing the field will use the field value
        assert rX['fnA'].val(system=SX) == 1  # .. so to get the sys value the system has to be specified in val()

    def test_values_set_val(self):
        vus = Values()
        assert vus.set_val(9, 3).val(3) == 9
        assert vus.set_val('6', 2).val(2) == '6'
        vus.set_val([3], 1)
        assert vus.val(1) == [3]

    def test_set_complex_val(self):
        rec = Record(system=SX, direction=FAD_FROM)
        rec.add_system_fields((('fnAXx', 'fnA'),
                               ('sfnAXx', 'fnB0sfnBA'), ('sfnBXx', 'fnB0sfnBB'),
                               ('sfnAXx', 'fnB1sfnBA'), ('sfnBXx', 'fnB1sfnBB')))

        # flat field exists (no sub records)
        val = [dict(sfnAA='test', sfnAB=datetime.date(year=2022, month=6, day=3)),
               dict(sfnAA='tst2', sfnAB=datetime.date(year=2040, month=9, day=6))]
        rec.set_val(val, 'fnA', system=SX, direction=FAD_FROM)
        assert isinstance(rec['fnA'], list)
        assert isinstance(rec.val('fnA'), list)
        assert isinstance(rec.value('fnA', flex_sys_dir=True), Value)
        assert rec.val('fnA')[1]['sfnAA'] == 'tst2'
        # .. now overwrite with conversion to value types
        rec.set_val(val, 'fnA', system=SX, direction=FAD_FROM, to_value_type=True)
        assert isinstance(rec['fnA'], list)
        assert isinstance(rec.value('fnA', flex_sys_dir=True), Records)
        assert rec.val('fnA', 1, 'sfnAA') == 'tst2'
        # node field exists
        val = [dict(sfnBA='test', sfnBB=datetime.date(year=2022, month=6, day=3)),
               dict(sfnBA='tst2', sfnBB=datetime.date(year=2040, month=9, day=6))]
        rec.set_val(val, 'fnB', system=SX, direction=FAD_FROM)
        assert isinstance(rec['fnB'], list)
        assert isinstance(rec.val('fnB'), list)
        assert isinstance(rec.value('fnB', flex_sys_dir=True), Records)
        assert rec.val('fnB')[1]['sfnBA'] == 'tst2'
        # .. now overwrite with conversion to value types
        rec.set_val(val, 'fnB', system=SX, direction=FAD_FROM, to_value_type=True)
        assert isinstance(rec['fnB'], list)
        assert isinstance(rec.value('fnB', flex_sys_dir=True), Records)
        assert rec.val('fnB', 1, 'sfnBA') == 'tst2'
        # field not exists
        val = [dict(sfnCA='test', sfnCB=datetime.date(year=2022, month=6, day=3)),
               dict(sfnCA='tst2', sfnCB=datetime.date(year=2040, month=9, day=6))]
        rec.set_val(val, 'fnC', system=SX, direction=FAD_FROM)
        assert isinstance(rec['fnC'], list)
        assert isinstance(rec.val('fnC'), list)
        assert isinstance(rec.value('fnC', flex_sys_dir=True), Value)
        assert rec.val('fnC')[1]['sfnCA'] == 'tst2'
        # .. now overwrite with conversion to value types
        rec.set_val(val, 'fnC', system=SX, direction=FAD_FROM, to_value_type=True)
        assert isinstance(rec['fnC'], list)
        assert isinstance(rec.value('fnC', flex_sys_dir=True), Records)
        assert rec.val('fnC', 1, 'sfnCA') == 'tst2'

    def test_set_complex_node(self):
        rec = Record(system=SX, direction=FAD_FROM)
        rec.add_system_fields((('fnAXx', 'fnA'),
                               ('sfnAXx', 'fnB0sfnBA'), ('sfnBXx', 'fnB0sfnBB'),
                               ('sfnAXx', 'fnB1sfnBA'), ('sfnBXx', 'fnB1sfnBB')))

        # flat field exists (no sub records)
        val = [dict(sfnAA='test', sfnAB=datetime.date(year=2022, month=6, day=3)),
               dict(sfnAA='tst2', sfnAB=datetime.date(year=2040, month=9, day=6))]
        rec.set_node_child(val, 'fnA', system=SX, direction=FAD_FROM)
        assert isinstance(rec['fnA'], list)
        assert isinstance(rec.val('fnA'), list)
        assert isinstance(rec.value('fnA', flex_sys_dir=True), Value)
        assert rec.val('fnA')[1]['sfnAA'] == 'tst2'
        # .. now overwrite with conversion to value types
        rec.set_val(val, 'fnA', system=SX, direction=FAD_FROM, to_value_type=True)
        assert isinstance(rec['fnA'], list)
        assert isinstance(rec.value('fnA', flex_sys_dir=True), Records)
        assert rec.val('fnA', 1, 'sfnAA') == 'tst2'
        # node field exists
        val = [dict(sfnBA='test', sfnBB=datetime.date(year=2022, month=6, day=3)),
               dict(sfnBA='tst2', sfnBB=datetime.date(year=2040, month=9, day=6))]
        rec.set_node_child(val, 'fnB', system=SX, direction=FAD_FROM)
        assert isinstance(rec['fnB'], list)
        assert isinstance(rec.val('fnB'), list)
        assert isinstance(rec.value('fnB', flex_sys_dir=True), Records)
        assert rec.val('fnB')[1]['sfnBA'] == 'tst2'
        # .. now overwrite with conversion to value types
        rec.set_val(val, 'fnB', system=SX, direction=FAD_FROM, to_value_type=True)
        assert isinstance(rec['fnB'], list)
        assert isinstance(rec.value('fnB', flex_sys_dir=True), Records)
        assert rec.val('fnB', 1, 'sfnBA') == 'tst2'
        # field not exists
        val = [dict(sfnCA='test', sfnCB=datetime.date(year=2022, month=6, day=3)),
               dict(sfnCA='tst2', sfnCB=datetime.date(year=2040, month=9, day=6))]
        rec.set_node_child(val, 'fnC', system=SX, direction=FAD_FROM)
        assert isinstance(rec['fnC'], list)
        assert isinstance(rec.val('fnC'), list)
        assert isinstance(rec.value('fnC', flex_sys_dir=True), Value)
        assert rec.val('fnC')[1]['sfnCA'] == 'tst2'
        # .. now overwrite with conversion to value types
        rec.set_val(val, 'fnC', system=SX, direction=FAD_FROM, to_value_type=True)
        assert isinstance(rec['fnC'], list)
        assert isinstance(rec.value('fnC', flex_sys_dir=True), Records)
        assert rec.val('fnC', 1, 'sfnCA') == 'tst2'


class TestSystem:
    sid = SX
    cre = dict(User='test_user')
    fea = ['extra_feature']
    ana = 'test_app_name'
    dlv = 99

    class SystemConnectionSuccessMock:
        def connect(self):
            return not self or ''

        def close(self):
            return not self or ''

        def disconnect(self):
            return not self or ''

    class SystemConnectionFailureMock:
        def connect(self):
            return 'ConnectError' or self

    class SystemDisconnectionFailureMock:
        def connect(self):
            return not self or ''

        def close(self):
            return 'CloseError' or self

        def disconnect(self):
            return 'DisconnectError' or self

    @staticmethod
    def check_connector_args(cre, fea, ana, dlv):
        assert cre == TestSystem.cre
        assert fea == TestSystem.fea
        assert ana == TestSystem.ana
        assert dlv == TestSystem.dlv

    @staticmethod
    def connector_success_mock(credentials, features, app_name, debug_level):
        TestSystem.check_connector_args(credentials, features, app_name, debug_level)
        return TestSystem.SystemConnectionSuccessMock()

    @staticmethod
    def connector_failure_mock(credentials, features, app_name, debug_level):
        TestSystem.check_connector_args(credentials, features, app_name, debug_level)
        return TestSystem.SystemConnectionFailureMock()

    @staticmethod
    def disconnect_failure_mock(credentials, features, app_name, debug_level):
        TestSystem.check_connector_args(credentials, features, app_name, debug_level)
        return TestSystem.SystemDisconnectionFailureMock()

    def test_init(self):
        s = System(self.sid, credentials=self.cre, features=self.fea)
        assert s.sys_id == self.sid
        assert s.credentials == self.cre
        assert s.features == self.fea
        assert s.connection is None
        assert s.conn_error == ''
        assert s.app_name == ''
        # assert s.debug_level == DEBUG_LEVEL_DISABLED



    def test_connect_and_close(self):
        s = System(self.sid, credentials=self.cre, features=self.fea)
        assert s.connect(TestSystem.connector_success_mock, app_name=self.ana, debug_level=self.dlv) == ''
        assert s.disconnect() == ''

        s = System(self.sid, credentials=self.cre, features=self.fea)
        assert s.connect(TestSystem.connector_success_mock, app_name=self.ana, debug_level=self.dlv) == ''
        s.connection.close = None
        assert s.disconnect() == ''

        s = System(self.sid, credentials=self.cre, features=self.fea)
        assert s.connect(TestSystem.connector_failure_mock, app_name=self.ana, debug_level=self.dlv) == 'ConnectError'
        assert s.disconnect() == ''

        s = System(self.sid, credentials=self.cre, features=self.fea)
        assert s.connect(TestSystem.connector_failure_mock, app_name=self.ana, debug_level=self.dlv) == 'ConnectError'
        assert s.disconnect() == ''

        s = System(self.sid, credentials=self.cre, features=self.fea)
        assert s.connect(TestSystem.disconnect_failure_mock, app_name=self.ana, debug_level=self.dlv) == ''
        assert s.disconnect() == 'CloseError'

        s = System(self.sid, credentials=self.cre, features=self.fea)
        assert s.connect(TestSystem.disconnect_failure_mock, app_name=self.ana, debug_level=self.dlv) == ''
        s.connection.close = None
        assert s.disconnect() == 'DisconnectError'
