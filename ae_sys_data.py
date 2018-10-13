"""
manage data for to interface from and onto other/external systems
"""
import os
import struct
import keyword
from collections import OrderedDict
from typing import Optional


# data actions
ACTION_INSERT = 'INSERT'
ACTION_UPDATE = 'UPDATE'
ACTION_DELETE = 'DELETE'
ACTION_SEARCH = 'SEARCH'

# dummy field name (not used as data field but as placeholder, e.g. for to put xml groups)
DUMMY_FIELD_NAME = '___'

# field name special characters for to identify list indexes and sub-Records
# FN_LIST_IDX_MARKER = '#'
# FN_SUB_REC_MARKER = '.'

# field aspect types/prefixes
FAT_NAME = 'nom'
FAT_IDX = 'idx'
FAT_VAL = 'val'
FAT_TYPE = 'typ'
FAT_CAL = 'cal'
FAT_CHK = 'chk'
FAT_CON = 'con'
FAT_REC = 'rec'
FAT_FLT = 'flt'
FAT_SQE = 'sce'

ALL_FATS = (FAT_NAME, FAT_VAL, FAT_TYPE, FAT_REC, FAT_IDX, FAT_CAL, FAT_CHK, FAT_CON, FAT_FLT, FAT_SQE)

# field aspect directions
FAD_FROM = 'From'
FAD_ONTO = 'Onto'

# aspect key structure
_ASP_TYPE_LEN = 3
_ASP_DIR_LEN = 4
_ASP_SYS_MIN_LEN = 2


def aspect_key(type_or_key, system='', direction=''):
    assert len(type_or_key) >= _ASP_TYPE_LEN, \
        "aspect_key({}, {}, {}): aspect type is too short".format(type_or_key, system, direction)
    assert system == '' or len(system) >= _ASP_SYS_MIN_LEN, \
        "aspect_key({}, {}, {}): aspect type is too short".format(type_or_key, system, direction)
    assert direction == '' or len(direction) == _ASP_DIR_LEN, \
        "aspect_key({}, {}, {}): invalid aspect direction length".format(type_or_key, system, direction)
    assert not type_or_key[0].islower() or type_or_key[:_ASP_TYPE_LEN] in ALL_FATS, \
        "aspect_key({}, {}, {}): invalid aspect type format".format(type_or_key, system, direction)
    assert (system == '' or system[0].isupper()) and (direction == '' or direction[0].isupper()), \
        "aspect_key({}, {}, {}): invalid system or direction format".format(type_or_key, system, direction)

    key = type_or_key + direction + system

    assert key.isidentifier() and not keyword.iskeyword(key), \
        "aspect_key({}, {}, {}): key '{}' contains invalid characters".format(type_or_key, system, direction, key)
    if type_or_key[:_ASP_TYPE_LEN] in ALL_FATS:
        assert key.count(FAD_FROM) <= 1 and key.count(FAD_ONTO) <= 1, \
            "aspect_key({}, {}, {}): direction duplicates".format(type_or_key, system, direction)

    return key


def aspect_key_system(key):
    beg = _ASP_TYPE_LEN
    if len(key) > _ASP_TYPE_LEN + _ASP_DIR_LEN:
        beg += _ASP_DIR_LEN
    return key[beg:]


def aspect_key_direction(key):
    beg = _ASP_TYPE_LEN
    if len(key) > _ASP_TYPE_LEN + _ASP_DIR_LEN:
        beg += _ASP_DIR_LEN
    return key[beg:]


def deeper(deepness, instance):
    """
    check and calculate resulting/remaining deepness for Record/Field/Records.copy() when going one level deeper
    :param deepness:    <0 will be returned unchanged until last level is reached (-1==full deep copy, -2==deep copy
                        until deepest Value, -3==deep copy until deepest Field.
    :param instance:    instance to be copied (if this method is returning != 0/zero).
    :return:            if deepness == 0 then return 0, if deepness < 0 then return 0 if the deepest level is reached,
                        else (deepness > 0) return deepness - 1.
    """
    if deepness > 0:
        remaining = deepness - 1
    elif deepness == -2 and type(instance) == 'Value' \
            or deepness == -3 and type(instance) == 'Field' and type(instance.value()) == 'Value':
        remaining = 0
    else:
        remaining = deepness    # return unchanged if deepness in (0, -1) or == -2/-3 but not reached bottom/last level
    return remaining


class Value(list):
    def __init__(self, seq=('',)):
        super().__init__(seq)

    def value(self, *idx_path, **__):
        assert isinstance(idx_path, tuple) and len(idx_path) == 0, \
            "Value.value() passed non-empty idx_path list {}".format(idx_path)
        return self

    def set_value(self, value, *idx_path, **__):
        assert isinstance(idx_path, tuple) and len(idx_path) == 0, \
            "Value.set_value({}) passed non-empty idx_path list {}".format(value, idx_path)
        assert isinstance(value, Value), "{}.set_value({}, {}) expecting Value type".format(self, value, __)
        self[-1] = value[-1]

    def val(self, *idx_path, **__):
        assert isinstance(idx_path, tuple) and len(idx_path) <= 1, \
            "Value.val() passed idx_path list {} with more than one entry".format(idx_path)
        return self[idx_path[0] if isinstance(idx_path, tuple) and len(idx_path) else -1]

    def set_val(self, val, *idx_path, **__):
        assert isinstance(idx_path, tuple) and len(idx_path) <= 1, \
            "Value.set_val({}) idx_path list {} has more than one entry".format(val, idx_path)
        assert not isinstance(val, VALUE_TYPES), "Value.set_val({}) got unexpected value type {}".format(val, type(val))
        self[idx_path[0] if isinstance(idx_path, tuple) and len(idx_path) else -1] = val

    def clear(self, **__):
        self[-1] = ''

    def copy(self, *_, **__):
        """
        copy the value of this Value instance into a new one
        :return:                new Value instance containing the same immutable value.
        """
        return Value((self[-1], ))


class Values(list):
    def value(self, *idx_path, system='', direction='', **kwargs):
        if len(idx_path) == 0:
            return self
        idx, *idx_path = idx_path
        return self[idx].value(*idx_path, system=system, direction=direction, **kwargs)

    def set_value(self, value, *idx_path, system='', direction='', add=False):
        idx, *idx_path = idx_path
        self[idx].set_value(value, *idx_path, system=system, direction=direction, add=add)
        return self

    def val(self, *idx_path, system='', direction='', **kwargs):
        idx, *idx_path = idx_path
        return self[idx].val(*idx_path, system=system, direction=direction, **kwargs)

    def set_val(self, val, *idx_path, system='', direction=''):
        idx, *idx_path = idx_path
        self[idx].set_val(val, *idx_path, system=system, direction=direction)
        return self

    # def clear(self, system='', direction=''):     NOT NEEDED because list has already a clear method

    def copy(self, *idx_path, deepness=0, **kwargs):
        """
        copy the values/records of this list (Values or Records)
        :param idx_path:        path of field names and/or list/Records indexes.
        :param deepness:        deep copy levels: <0==see deeper(), 0==only copy current instance, >0==deep copy
                                to deepness value - please note that Field occupies two deepness: 1st=Field, 2nd=Value).
        :param kwargs           additional arguments (will be passed on - most of them used by Record.copy).
        :return:                new/extended record instance.
        """
        ret = type(self)()      # create new instance of this list/class (Values or Records)
        for idx, rec in enumerate(self):
            idx_path += (idx,)
            if deeper(deepness, rec):
                rec = rec.copy(*idx_path, deepness=deeper(deepness, rec), **kwargs)
            ret.append(rec)
        return ret


class Records(Values):
    pass


class Record(OrderedDict):
    # isinstance(..., dict) not working if using MutableMapping instead of OrderedDict
    # dict should not be used because **instance will then not work see the answer of Groxx in the stackoverflow
    # .. question https://stackoverflow.com/questions/3387691/how-to-perfectly-override-a-dict/47361653#47361653
    def __init__(self, fields=None, system='', direction='', action=None):
        """
        ordered collection of Field items.
        :param fields:      OrderedDict/dict of Field instances (field order is not preserved when using dict).
        :param system:      main/current system of this record,
        :param direction:   interface direction of this record.
        :param action:      current action (see ACTION_INSERT, ACTION_SEARCH, ACTION_DELETE, ...)
        """
        self._fields = self     # using internal store of OrderedDict() while keeping code more readable
        self.system = self.direction = self.action = ''
        if fields:
            self.add_fields(fields)
        # super().__init__(*self._fields.items(), {})        # OrderedDict signature is: *args, **kwargs)
        super().__init__(*(), **self._fields)
        self.set_env(system=system, direction=direction, action=action)

    @property
    def fields(self):
        return self._fields

    def __iter__(self):
        return iter(self._fields)

    def _find_field(self, idx_path):
        for fld_nam, field in self._fields.items():
            if fld_nam == idx_path:
                return fld_nam, field
            for asp_key, asp_val in field.aspects.items():
                if asp_key.startswith(FAT_NAME) and asp_val == idx_path:
                    return fld_nam, field
            idx_len = len(idx_path)
            if isinstance(idx_path, tuple) and idx_len and fld_nam == idx_path[0]:
                if idx_len == 1:
                    return fld_nam, field
                elif field.__contains__(idx_path[1:]):
                    return idx_path, None

        return '', None

    def __contains__(self, idx_path):
        return self._find_field(idx_path)[0] != ''

    def __getitem__(self, key):
        idx_path, field = self._find_field(key)
        if not idx_path:
            raise KeyError("There is no field with the name/idx_path '{}' in this Record/OrderedDict ({})"
                           .format(idx_path, self))
        if field is None:  # isinstance(idx_path, tuple):
            field = self._fields.get(idx_path[0])
            return field.value(*idx_path[1:])
        else:
            return self._fields.get(idx_path)

    def __setitem__(self, key, value):
        idx_path, field = self._find_field(key)
        if idx_path and field is None:  # and isinstance(idx_path, tuple):
            field = self._fields.get(idx_path[0])
            field.set_value(value, *idx_path[1:])
        else:
            super().__setitem__(key, value)

    def value(self, *idx_path, system='', direction='', **kwargs):
        if len(idx_path) == 0:
            return self
        idx, *idx_path = idx_path
        return self._fields[idx].value(*idx_path, system=system, direction=direction, **kwargs)

    def set_value(self, value, *idx_path, system='', direction='', add=False):
        idx, *idx_path = idx_path
        self[idx].set_value(value, *idx_path, system=system, direction=direction, add=add)
        return self

    def set_values(self, values, fuzzy_aspect=False, system='', direction=''):
        for field in self._fields.values():
            key = field.aspect_exists(FAT_NAME, fuzzy_aspect=fuzzy_aspect, system=system, direction=direction)
            if key and field.aspects[key] in values:
                field.set_value(values[field.aspects[key]], system=system, direction=direction)

    def val(self, *idx_path, system='', direction='', **kwargs):
        idx, *idx_path = idx_path
        # return self._fields[idx].val(*idx_path, system=system, direction=direction, **kwargs)
        # field_or_val = self._fields[idx]
        # return field_or_val.val(*idx_path, system=system, direction=direction, **kwargs) if idx_path else field_or_val
        return self._fields[idx].val(*idx_path, system=system, direction=direction, **kwargs)

    def set_val(self, val, *idx_path, system='', direction=''):
        idx, *idx_path = idx_path
        self[idx].set_val(val, *idx_path, system=system, direction=direction)
        return self

    def add_field(self, field, name=''):
        ori_name = name
        assert isinstance(field, Field), \
            "add_field({}, {}): field has to be of type Field (not {})".format(field, name, type(field))
        if not name:
            name = field.name
            if name == DUMMY_FIELD_NAME:
                name += str(len(self._fields) + 1)
        field.name = name
        assert name not in self._fields, \
            "add_field({}, {}): field name {} already exists in Record".format(field, ori_name, name)
        self._fields[name] = field

    def add_fields(self, fields):
        for name, field in fields.items():
            self.add_field(field, name=name)

    def field_count(self):
        return len(self._fields)

    def names(self, system='', direction=''):
        names = list()
        for field in self._fields.values():
            name = field.aspect_value(FAT_NAME, system=system, direction=direction)
            if name:
                names.append(name)
        return names

    def clear(self, system='', direction=''):
        for field in self._fields.values():
            field.clear(system=system, direction=direction)

    def copy(self, *idx_path, deepness=0, to_rec=None, filter_func=None, fields_patches=None):
        """
        copy the fields of this record
        :param idx_path:        list of path items of field names and/or indexes.
        :param deepness:        deep copy level: <0==see deeper(), 0==only copy current instance, >0==deep copy
                                to deepness value - please note that Field occupies two deepness: 1st=Field, 2nd=Value).
        :param to_rec:          destination record; pass None to create new Record instance.
        :param filter_func:     method called for each copied field (return True to filter/hide/not-include into copy).
        :param fields_patches:  restrict fields to the idx_path in this dict and use dict values as override aspects.
        :return:                new/extended record instance.
        """
        new_rec = to_rec is None
        if new_rec:
            to_rec = Record()
        elif not fields_patches:
            assert to_rec is not self, "copy() cannot copy to self (same Record instance) without patches"

        for name, field in self._fields.items():
            if filter_func:
                assert callable(filter_func)
                if not filter_func(field):
                    continue

            patches = None
            if fields_patches:
                if name in fields_patches:
                    patches = fields_patches[name]
                else:
                    continue

            if deeper(deepness, field):
                name = idx_path + (name, )
                field = field.copy(*name,  deepness=deeper(deepness, field),
                                   to_rec=to_rec, filter_func=filter_func, fields_patches=fields_patches)
            elif name in to_rec:
                field = to_rec[name]

            if patches:
                field.set_aspects(**patches)

            if new_rec:
                to_rec.add_field(field, name=name)
            else:
                to_rec[name] = field

        return to_rec

    def pull(self, system=''):
        assert self.system == '' and self.direction == '', "{}{}.pull() not allowed".format(self.direction, self.system)
        for field in self._fields.values():
            field.pull(system=system)

    def push(self, system=''):
        assert self.system == '' and self.direction == '', "{}{}.push() not allowed".format(self.direction, self.system)
        for field in self._fields.values():
            field.push(system=system)

    def set_env(self, system='', direction='', action=''):
        if system:
            self.system = system
        if direction:
            self.direction = direction
        if action:
            self.action = action
        for field in self._fields.values():
            field.set_rec(self, system=system, direction=direction)

    def sql_select(self, system):
        """
        return list of sql column names/expressions for given system.
        :param system:              system from which the data will be selected/fetched.
        :return:                    list of sql column names/expressions.
        """
        column_expressions = list()
        for field in self._fields.values():
            name = field.aspect_value(FAT_NAME, system=system, direction=FAD_FROM)
            if name:
                expr = field.aspect_value(FAT_SQE, system=system, direction=FAD_FROM) or ""
                if expr:
                    expr += " AS "
                column_expressions.append(expr + name)
        return column_expressions

    def xml_build(self, system):
        pass


class Field:
    def __init__(self, **aspects):
        self._aspects = dict()
        self.add_aspects(**aspects)
        if FAT_VAL not in self._aspects:
            self._aspects[FAT_VAL] = Value()
        if FAT_NAME not in self._aspects:
            self._aspects[FAT_NAME] = DUMMY_FIELD_NAME

    @property
    def aspects(self):
        return self._aspects

    @property
    def name(self):
        return self._aspects.get(FAT_NAME)

    @name.setter
    def name(self, name):
        self._aspects[FAT_NAME] = name

    def __getitem__(self, idx_path):
        return self.value(*idx_path)

    def __setitem__(self, idx_path, value):
        self.set_value(value, *idx_path)

    def __contains__(self, idx_path):
        idx_len = len(idx_path)
        value = self._aspects[FAT_VAL]
        if isinstance(idx_path, tuple) and idx_len and isinstance(value, Records) and len(value) > idx_path[0]:
            if idx_len == 1:
                return idx_path[0]
            else:
                return value[idx_path[0]].__contains__(idx_path[1:])

    def __repr__(self):
        return "Field(" + repr(self._aspects) + ")"
    # __repr__ = __str__

    def value(self, *idx_path, fuzzy_aspect=False, system='', direction=''):
        value = None
        val_or_cal = self.aspect_value(FAT_VAL, FAT_CAL, fuzzy_aspect=fuzzy_aspect, system=system, direction=direction)
        if val_or_cal:
            if callable(val_or_cal):
                value = val_or_cal(self)
            else:
                value = val_or_cal
        assert isinstance(value, VALUE_TYPES), \
            "Field.value({}, {}, {}, {}): value '{}' has to be of type {}"\
            .format(idx_path, fuzzy_aspect, system, direction, value, VALUE_TYPES)
        if value and isinstance(idx_path, tuple):
            value = value.value(*idx_path)
        return value

    def set_value(self, value, *idx_path, system='', direction='', add=False):
        assert isinstance(value, VALUE_TYPES), \
            "Field.set_value({}, {}, {}, {}, {}): value has to be of type {}"\
            .format(value, idx_path, system, direction, add, VALUE_TYPES)

        key = aspect_key(FAT_VAL, system=system, direction=direction)

        if isinstance(idx_path, tuple) and len(idx_path):
            self._aspects[key].set_value(value, *idx_path, system=system, direction=direction, add=add)
        else:
            if add:
                assert key not in self._aspects, \
                    "Field.set_value({}, {}, {}, {}, {}): value key {} already exists in aspects ({})"\
                    .format(value, idx_path, system, direction, add, key, self._aspects)
            else:
                val_typ = self.aspect_value(FAT_TYPE, system=system, direction=direction)
                # noinspection PyTypeChecker
                assert not val_typ or isinstance(value, val_typ), \
                    "Field.set_value({}, {}, {}, {}, {}): value '{}' has wrong type {} (declared as {})" \
                    .format(value, idx_path, system, direction, add, value, type(value), val_typ)
            self._aspects[key] = value

        return self

    def val(self, *idx_path, fuzzy_aspect=True, system='', direction=''):
        value = self.value(fuzzy_aspect=fuzzy_aspect, system=system, direction=direction)
        assert idx_path or isinstance(value, Value), \
            "Field.val() without idx_path ({}) has to point to Value instance (but got {})".format(idx_path, value)
        return value.val(*idx_path, fuzzy_aspect=fuzzy_aspect, system=system, direction=direction)

    def set_val(self, val, *idx_path, system='', direction=''):
        value = self.aspect_value(FAT_VAL, system=system, direction=direction)
        value.set_val(val, *idx_path, system=system, direction=direction)
        return self

    def find_aspect_key(self, *aspect_types, system='', direction=''):
        keys = list()
        if direction and system:
            for aspect_type in aspect_types:
                keys.append(aspect_key(aspect_type, system=system, direction=direction))
        else:
            assert direction == '', "Field.find_aspect_key({}, {}, {}) direction without system not allowed"\
                .format(aspect_types, system, direction)
        if system:
            for aspect_type in aspect_types:
                keys.append(aspect_key(aspect_type, system=system))
        for aspect_type in aspect_types:
            keys.append(aspect_key(aspect_type))

        for key in keys:
            if key in self._aspects:
                return key

        return None

    def aspect_exists(self, *aspect_types, fuzzy_aspect=False, system='', direction=''):
        key = None
        if fuzzy_aspect:
            key = self.find_aspect_key(*aspect_types, system=system, direction=direction)
        else:
            for aspect_type in aspect_types:
                key = aspect_key(aspect_type, system=system, direction=direction)
                if key:
                    break
        return key if key in self._aspects else None

    def aspect_value(self, *aspect_types, fuzzy_aspect=False, system='', direction=''):
        key = self.aspect_exists(*aspect_types, fuzzy_aspect=fuzzy_aspect, system=system, direction=direction)
        if key:
            val = self._aspects.get(key)
        else:
            val = None
        return val

    def set_aspect(self, aspect_value, type_or_key, system='', direction='', add=False):
        key = aspect_key(type_or_key, system=system, direction=direction)
        if add:
            assert key not in self._aspects, "Field.set_aspect({}, {}, {}, {}, {}): key already exists in aspects ({})"\
                .format(type_or_key, aspect_value, system, add, direction, key, self._aspects)
        if key.startswith(FAT_VAL):
            self.set_value(aspect_value, system=aspect_key_system(key), direction=aspect_key_direction(key))
        elif aspect_value is None:
            self.del_aspect(key)
        else:
            self._aspects[key] = aspect_value
        return self

    def del_aspect(self, type_or_key, system='', direction=''):
        key = aspect_key(type_or_key, system=system, direction=direction)
        assert not key.startswith(FAT_VAL) and key != FAT_NAME, "Field name, value and system values not deletable"
        return self._aspects.pop(key)

    def set_aspects(self, **aspects):
        for key, data in aspects.items():
            self.set_aspect(data, key)
        return self

    def add_aspects(self, **aspects):
        for key, data in aspects.items():
            # adding any other aspect to instance aspects w/o system/direction from kwargs
            self.set_aspect(data, key, add=True)
        return self

    def del_name(self, system='', direction=''):
        self.del_aspect(FAT_NAME, system=system, direction=direction)
        return self

    def set_name(self, name, system='', direction='', add=False):
        self.set_aspect(name, FAT_NAME, system=system, direction=direction, add=add)
        return self

    def rec(self, system='', direction='') -> Optional[Record]:
        return self.aspect_value(FAT_REC, fuzzy_aspect=True, system=system, direction=direction)

    def set_rec(self, rec, system='', direction=''):
        self.set_aspect(rec, FAT_REC, system=system, direction=direction)

    def idx(self, system='', direction=''):
        return self.aspect_value(FAT_IDX, fuzzy_aspect=True, system=system, direction=direction)

    def set_idx(self, idx, system='', direction=''):
        self.set_aspect(idx, FAT_IDX, system=system, direction=direction)

    def value_type(self, system='', direction=''):
        return self.aspect_value(FAT_TYPE, system=system, direction=direction) or Value

    def set_value_type(self, value_type, system='', direction='', add=False):
        assert value_type in VALUE_TYPES, "Invalid value type {} (allowed are only {})".format(value_type, VALUE_TYPES)
        self.set_aspect(value_type, FAT_TYPE, system=system, direction=direction, add=add)
        return self

    def set_calculator(self, calculator, system='', direction='', add=False):
        return self.set_aspect(calculator, FAT_CAL, system=system, direction=direction, add=add)

    def set_validator(self, validator, system='', direction='', add=False):
        return self.set_aspect(validator, FAT_CHK, system=system, direction=direction, add=add)

    def set_converter(self, converter, system='', direction='', add=False):
        return self.set_aspect(converter, FAT_CON, system=system, direction=direction, add=add)

    def set_filter(self, filter_func, system='', direction='', add=False):
        return self.set_aspect(filter_func, FAT_FLT, system=system, direction=direction, add=add)

    def set_sql_expression(self, sql_expression, system='', direction='', add=False):
        return self.set_aspect(sql_expression, FAT_SQE, system=system, direction=direction, add=add)

    def convert_and_validate(self, value, system='', direction=''):
        converter = self.aspect_value(FAT_CON, system=system, direction=direction)
        if converter:
            assert callable(converter)
            value = converter(self, value)

        validator = self.aspect_value(FAT_CHK, system=system, direction=direction)
        if validator:
            assert callable(validator)
            if not validator(self, value):
                return None

        return value

    def clear(self, system='', direction=''):
        self.value(system=system, direction=direction).clear(system=system, direction=direction)
        return self

    def copy(self, *idx_path, deepness=0, **kwargs):
        """
        copy the values of this field
        :param idx_path:        path of field names and/or list/Records/Values indexes.
        :param deepness:        deep copy level: <0==see deeper(), 0==only copy current instance, >0==deep copy
                                to deepness value - please note that Field occupies two deepness: 1st=Field, 2nd=Value).
        :param kwargs           additional arguments (will be passed on - most of them used by Record.copy).
        :return:                new/extended record instance.
        """
        aspects = self.aspects
        if deepness:
            for asp_key, asp_val in aspects:        # asp_val is of VALUE_TYPES (Value, Records, ...)
                if asp_key.startswith(FAT_VAL) and deeper(deepness, asp_val):
                    aspects[asp_key] = asp_val.copy(*idx_path, deepness=deeper(deepness, asp_val), **kwargs)
        return Field(**aspects)

    def pull(self, system=''):
        direction = FAD_FROM
        val = self.value(system=system, direction=direction)

        validator = self.aspect_value(FAT_CHK, system=system, direction=direction)
        if validator:
            assert callable(validator)
            if not validator(self, val):
                return None

        converter = self.aspect_value(FAT_CON, system=system, direction=direction)
        if converter:
            assert callable(converter)
            val = converter(self, val)

        self.set_value(val)

        return self

    def push(self, system=''):
        direction = FAD_ONTO
        val = self.convert_and_validate(self.value(), system=system, direction=direction)
        if val is None:
            return None

        self.set_value(val, system=system, direction=direction)

        return self

    def string_to_records(self, rec_sep, fld_names, fld_sep, system='', direction=''):
        str_val = self.val(system=system, direction=direction)
        recs = Records()
        for idx, str_rec in enumerate(str_val.split(rec_sep)):
            rec = Record()
            for fld_idx, fld_val in enumerate(str_rec.split(fld_sep)):
                aspects = dict(FAT_NAME=fld_names[fld_idx], FAT_VAL=fld_val)
                fld = Field(**aspects)
                rec.add_field(fld)
            recs.append(rec)
        return recs

    def system_rec_val(self, name='', system='', direction=''):
        rec = self.rec(system=system, direction=direction)
        if name == '':
            field = self
        else:
            # noinspection PyTypeChecker
            field = rec[name]
        return field.val(system=rec.system or '', direction=rec.direction or '')

    srv = system_rec_val

    def in_actions(self, *actions, system='', direction=''):
        rec = self.rec(system=system, direction=direction)
        if rec:
            return rec.action in actions

    ina = in_actions


VALUE_TYPES = (Value, Values, Record, Records)


class System:
    def __init__(self, sys_id: str, credentials: dict):
        """
        define new system

        :param sys_id:              unique str for to identify a system (also used as prefix/suffix).
        :param credentials:         dict for to access system, containing e.g. user name, password, token, dsn
        """
        self.sys_id = sys_id
        self.credentials = credentials


class ConfigurationOption:
    pass


class UsedSystems:
    def __init__(self):
        self.systems = list()

    def add_system(self, system: System):
        self.systems.append(system)


def executable_architecture(executable_file):
    """
    function for to determine the internal architecture of an DLL/EXE (and if it is 32 bit or 64 bit).

    :param executable_file:     file name (and opt. file path) of a DLL/EXE.
    :return:                    'i386' for 32 bit, 'IA64' or 'x64' for 64 bit, 'unknown' if DLL/EXE architecture is
                                unknown  or  None if passed file is no executable (or cannot be opened).

    copied from https://github.com/tgandor/meats/blob/master/missing/arch_of.py and refactored.
    """
    ret = None
    with open(executable_file, 'rb') as file_handle:
        dos_hdr = file_handle.read(64)
        magic, padding, offset = struct.unpack('2s58si', dos_hdr)
        if magic == b'MZ':
            file_handle.seek(offset, os.SEEK_SET)
            pe_hdr = file_handle.read(6)
            # careful! H == unsigned short, x64 is negative with signed
            magic, padding, machine = struct.unpack('2s2sH', pe_hdr)
            if magic == b'PE':
                if machine == 0x014c:
                    ret = 'i386'
                elif machine == 0x0200:
                    ret = 'IA64'
                elif machine == 0x8664:
                    ret = 'x64'
                else:
                    ret = 'unknown'
    return ret
