"""
manage data for to interface from and onto other/external systems
"""
import os
import struct
import keyword
from collections import OrderedDict
from typing import Optional, Any, Dict

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
FAT_NAME = 'nme'
FAT_VAL = 'vle'
FAT_TYPE = 'tpe'
FAT_REC = 'rcd'
FAT_IDX = 'idx'
FAT_CAL = 'clc'
FAT_CHK = 'chk'
FAT_CON = 'cnv'
FAT_FLT = 'flt'
FAT_SQE = 'sqc'

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
    if len(key) > _ASP_TYPE_LEN + _ASP_DIR_LEN and key[beg:beg + _ASP_DIR_LEN] in (FAD_FROM, FAD_ONTO):
        beg += _ASP_DIR_LEN
    return key[beg:]


def aspect_key_direction(key):
    direction = key[_ASP_TYPE_LEN:_ASP_TYPE_LEN + _ASP_DIR_LEN]
    return direction if direction in (FAD_FROM, FAD_ONTO) else ''


def deeper(deepness, instance):
    """
    check and calculate resulting/remaining deepness for Record/Field/Records.copy() when going one level deeper
    :param deepness:    <0 will be returned unchanged until last level is reached (-1==full deep copy, -2==deep copy
                        until deepest Value, -3==deep copy until deepest Field.
    :param instance:    instance to be processed/copied (if this method is returning != 0/zero).
    :return:            if deepness == 0 then return 0, if deepness < 0 then return 0 if the deepest level is reached,
                        else (deepness > 0) return deepness - 1.
    """
    if deepness > 0:
        remaining = deepness - 1
    elif deepness == -2 and type(instance) == Value \
            or deepness == -3 and type(instance) == Field and type(instance.value()) == Value:
        remaining = 0
    else:
        remaining = deepness    # return unchanged if deepness in (0, -1) or == -2/-3 but not reached bottom/last level
    return remaining


def field_name_idx_path(field_name):
    idx_path = list()
    nam_i = num_i = None
    for ch_i, ch_v in enumerate(field_name):
        if str.isdigit(ch_v):
            if num_i is None:
                num_i = ch_i
                if nam_i is not None:
                    idx_path.append(field_name[nam_i:num_i])
                    nam_i = None
        else:
            if nam_i is None:
                nam_i = ch_i
                if num_i is not None:
                    idx_path.append(int(field_name[num_i:nam_i]))
                    num_i = None
    if idx_path:
        if nam_i is not None:
            idx_path.append(field_name[nam_i:])
        elif num_i is not None:
            idx_path.append(int(field_name[num_i:]))
    return tuple(idx_path)


class Value(list):
    def __init__(self, seq=('',)):
        super().__init__(seq)

    def __repr__(self):
        return "Value([" + ",".join(repr(v) for v in self) + "])"

    def deeper_item(self, idx_path, **__):
        # adding check_only kwarg for to use in Record.__contains__ for to prevent Assertion error we could add:
        # assert len(idx_path) == 0, "{} has no deeper value requested by idx_path {}".format(self, idx_path)
        return self if len(idx_path) == 0 else None

    def value(self, *idx_path, **__):
        assert isinstance(idx_path, tuple) and len(idx_path) == 0, \
            "Value.value() passed non-empty idx_path list {}".format(idx_path)
        return self

    def set_value(self, value, *idx_path, **__):
        assert isinstance(idx_path, tuple) and len(idx_path) == 0, \
            "Value.set_value({}) passed non-empty idx_path list {}".format(value, idx_path)
        assert isinstance(value, Value), "{}.set_value({}, {}) expecting Value type".format(self, value, __)
        self[-1] = value[-1]
        return self

    def val(self, *idx_path, **__):
        assert isinstance(idx_path, tuple) and len(idx_path) <= 1, \
            "Value.val() passed idx_path list {} with more than one entry".format(idx_path)
        return self[idx_path[0] if isinstance(idx_path, tuple) and len(idx_path) else -1]

    def set_val(self, val, *idx_path, **__):
        assert isinstance(idx_path, tuple) and len(idx_path) <= 1, \
            "Value.set_val({}) idx_path list {} has more than one entry".format(val, idx_path)
        assert not isinstance(val, VALUE_TYPES), "Value.set_val({}) got unexpected value type {}".format(val, type(val))
        self[idx_path[0] if isinstance(idx_path, tuple) and len(idx_path) else -1] = val
        return self

    def copy(self, *_, **__):
        """
        copy the value of this Value instance into a new one
        :return:                new Value instance containing the same immutable value.
        """
        return Value((self[-1], ))

    def clear_val(self, **__):
        self[-1] = ''
        return self


class Values(list):
    def __repr__(self):
        return ("Values" if type(self) == Values else "Records") + "([" + ",".join(repr(v) for v in self) + "])"

    def value(self, *idx_path, system='', direction='', **kwargs):
        if len(idx_path) == 0:
            return self
        idx, *idx_path = idx_path
        return self[idx].value(*idx_path, system=system, direction=direction, **kwargs)

    def set_value(self, value, *idx_path, system='', direction='', protect=False):
        idx, *idx_path = idx_path
        self[idx].set_value(value, *idx_path, system=system, direction=direction, protect=protect)
        return self

    def val(self, *idx_path, system='', direction='', flex_sys_dir=True, **kwargs):
        idx, *idx_path = idx_path
        return self[idx].val(*idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir, **kwargs)

    def set_val(self, val, *idx_path, system='', direction='', flex_sys_dir=True, extend=True, converter=None):
        idx, *idx_path = idx_path
        list_len = len(self)
        item_type = Value if type(self) == Values else Record
        if extend and list_len <= idx:
            for _ in range(idx - list_len + 1):
                self.append(item_type())
        self[idx].set_val(val, *idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir, extend=extend,
                          converter=converter)
        return self

    def deeper_item(self, idx_path, system='', direction='', flex_sys_dir=True):
        idx_len = len(idx_path)
        assert isinstance(idx_path, tuple) and idx_len, \
            "Values/Records idx_path '{}' is no tuple or an empty tuple".format(idx_path)
        lst_len = len(self)
        lst_idx = idx_path[0]
        assert isinstance(lst_idx, int) and lst_len > lst_idx, \
            "Values/Records idx_path '{}' not has an integer value less than {} in first item".format(idx_path, lst_len)
        if idx_len == 1:
            return self[lst_idx]
        return self[lst_idx].deeper_item(idx_path[1:], system=system, direction=direction, flex_sys_dir=flex_sys_dir)

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

    def clear_vals(self, system='', direction=''):
        for rec in self:
            rec.clear_vals(system=system, direction=direction)
        return self


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

    def __repr__(self):
        return "Record([" + ", ".join("(" + repr(k) + "," + repr(v) + ")" for k, v in self.items()) + "])"

    @property
    def fields(self):
        return self._fields

    def __iter__(self):
        return iter(self._fields)

    def deeper_item(self, idx_path, system='', direction='', flex_sys_dir=True):
        if isinstance(idx_path, tuple):
            field_idx = idx_path[0]
        else:
            field_idx = idx_path
            idx_path = (idx_path, )
        if system is None:
            system = self.system
        if direction is None:
            direction = self.direction
        idx_len = len(idx_path)
        assert idx_len, "idx_path '{}' must be a non-empty tuple".format(idx_path)
        for fld_nam, field in self._fields.items():
            if fld_nam == idx_path:
                break
            elif fld_nam == field_idx:
                if idx_len == 1:
                    break
                else:
                    fld = field.deeper_item(idx_path[1:], system=system, direction=direction, flex_sys_dir=flex_sys_dir)
                    if fld:
                        field = fld
                        break
            for asp_key, asp_val in field.aspects.items():
                # if asp_key.startswith(FAT_NAME) and asp_val in (idx_path, field_idx):
                if asp_key.startswith(FAT_NAME) and (asp_val == idx_path or (asp_val == field_idx and idx_len == 1)):
                    return field
            if idx_len == 1 and not isinstance(fld_nam, tuple) and field_idx.startswith(fld_nam):
                idx_tuple = field_name_idx_path(field_idx)
                if idx_tuple:
                    field = field.deeper_item(idx_tuple[1:], system=system, direction=direction,
                                              flex_sys_dir=flex_sys_dir)
                    if field:
                        break
        else:
            field = None
        return field

    def __contains__(self, idx_path):
        item = self.deeper_item(idx_path)
        return bool(item)

    def __getitem__(self, key):
        value = self.deeper_item(key)
        if not value:
            raise KeyError("There is no item with the idx_path '{}' in this Record/OrderedDict ({})".format(key, self))
        return value

    def value(self, *idx_path, system='', direction='', **kwargs):
        if len(idx_path) == 0:
            return self
        idx, *idx_path = idx_path
        return self._fields[idx].value(*idx_path, system=system, direction=direction, **kwargs)

    def set_value(self, value, *idx_path, system='', direction='', protect=False):
        idx, *idx_path = idx_path
        self[idx].set_value(value, *idx_path, system=system, direction=direction, protect=protect)
        return self

    def set_values(self, values, system='', direction='', flex_sys_dir=False):
        for field in self._fields.values():
            key = field.aspect_exists(FAT_NAME, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
            if key and field.aspects[key] in values:
                field.set_value(values[field.aspects[key]], system=system, direction=direction)
        return self

    def val(self, *idx_path, system='', direction='', flex_sys_dir=True, **kwargs):
        idx, *idx_path = idx_path
        # return self._fields[idx].val(*idx_path, system=system, direction=direction, **kwargs)
        # field_or_val = self._fields[idx]
        # return field_or_val.val(*idx_path, system=system, direction=direction, **kwargs) if idx_path else field_or_val
        return self._fields[idx].val(*idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir, **kwargs)

    def set_val(self, val, *idx_path, system='', direction='', flex_sys_dir=True, extend=True, converter=None):
        idx, *idx_path = idx_path
        if extend and idx not in self:
            self.add_field(Field(), idx=idx)
        self[idx].set_val(val, *idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir, extend=extend,
                          converter=converter)
        return self

    def add_field(self, field, idx=''):
        """
        add Field instance to this Record instance.
        :param field:   Field instance to add.
        :param idx:    key/idx string for to map and identify this field (mostly identical to field.name).
        :return:        self.
        """
        ori_idx = idx
        assert isinstance(field, Field), \
            "add_field({}, {}): field has to be of type Field (not {})".format(field, idx, type(field))
        if not idx:
            idx = field.name
            if idx == DUMMY_FIELD_NAME:
                idx += chr(ord('A') + len(self._fields))
        elif idx and (not field.name or field.name.startswitch(DUMMY_FIELD_NAME)):
            field.name = idx
        assert idx not in self._fields, \
            "add_field({}, {}): Record '{}' has already a field with the key '{}'".format(field, ori_idx, self, idx)
        self._fields[idx] = field
        return self

    def add_fields(self, fields):
        if isinstance(fields, dict):
            items = fields.items()
        else:
            items = fields
        for name, field in items:
            self.add_field(field, idx=name)
        return self

    def field_count(self):
        return len(self._fields)

    def names(self, system='', direction=''):
        names = list()
        for field in self._fields.values():
            name = field.aspect_value(FAT_NAME, system=system, direction=direction)
            if name:
                names.append(name)
        return names

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
                new_path = (name, ) if new_rec else idx_path + (name, )
                field = field.copy(*new_path,  deepness=deeper(deepness, field),
                                   to_rec=None if new_rec else to_rec,
                                   filter_func=filter_func, fields_patches=fields_patches)
            elif name in to_rec:
                field = to_rec[name]

            if patches:
                field.set_aspects(**patches)

            if new_rec:
                to_rec.add_field(field, idx=name)
            else:
                to_rec[name] = field

        return to_rec

    def clear_vals(self, system='', direction=''):
        for field in self._fields.values():
            field.clear_vals(system=system, direction=direction)

    def pull(self, from_system):
        assert from_system, "Record.pull() with empty value in from_system is not allowed"
        for field in self._fields.values():
            field.pull(from_system=from_system)
        return self

    def push(self, onto_system):
        assert onto_system, "Record.push() with empty value in onto_system is not allowed"
        for field in self._fields.values():
            field.push(onto_system=onto_system)
        return self

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
    # following type hint is for instance (not class) variable - see https://stackoverflow.com/.
    # .. questions/47532472/can-python-class-variables-become-instance-variables-when-altered-in-init
    _aspects = ...  # type: Dict[str, Any]

    def __init__(self, **aspects):
        self._aspects = dict()
        self.add_aspects(**aspects)
        if FAT_VAL not in self._aspects:
            self._aspects[FAT_VAL] = Value()
        if FAT_NAME not in self._aspects:
            self._aspects[FAT_NAME] = DUMMY_FIELD_NAME

    def __repr__(self):
        return "Field(**{" + ", ".join([repr(k) + ": " + repr(v)
                                        for k, v in self._aspects.items() if not k.startswith(FAT_REC)]) + "})"

    def __str__(self):
        return "Field(" + repr(self._aspects) + ")"

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
        return self.value(idx_path)

    def __setitem__(self, idx_path, value):
        self.set_value(value, idx_path)

    def deeper_item(self, idx_path, system='', direction='', flex_sys_dir=True):
        idx_len = len(idx_path)
        assert isinstance(idx_path, tuple) and idx_len, "idx_path '{}' is no tuple or an empty tuple".format(idx_path)
        value = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        assert isinstance(value, VALUE_TYPES), "Field value type '{}' not of {}".format(type(value), VALUE_TYPES)
        return value.deeper_item(idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir)

    def value(self, *idx_path, system='', direction='', flex_sys_dir=False):
        value = None
        val_or_cal = self.aspect_value(FAT_VAL, FAT_CAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        if val_or_cal is not None:
            if callable(val_or_cal):
                value = val_or_cal(self)
                if value is not None and not isinstance(value, VALUE_TYPES):
                    value = Value((value, ))
            else:
                value = val_or_cal
        assert not flex_sys_dir and value is None or isinstance(value, VALUE_TYPES), \
            "Field.value({}, {}, {}, {}): value '{}'/'{}' has to be of type {}"\
            .format(idx_path, system, direction, flex_sys_dir, val_or_cal, value, VALUE_TYPES)
        if value and isinstance(idx_path, tuple) and len(idx_path) > 0:
            value = value.value(*idx_path)
        return value

    def set_value(self, value, *idx_path, system='', direction='', protect=False):
        assert isinstance(value, VALUE_TYPES), \
            "Field.set_value({}, {}, {}, {}, {}): value has to be of type {}"\
            .format(value, idx_path, system, direction, protect, VALUE_TYPES)

        key = aspect_key(FAT_VAL, system=system, direction=direction)

        if isinstance(idx_path, tuple) and len(idx_path):
            self._aspects[key].set_value(value, *idx_path, system=system, direction=direction, protect=protect)
        else:
            if protect:
                assert key not in self._aspects, \
                    "Field.set_value({}, {}, {}, {}, {}): value key {} already exists in aspects ({})"\
                    .format(value, idx_path, system, direction, protect, key, self._aspects)
            else:
                val_typ = self.aspect_value(FAT_TYPE, system=system, direction=direction)
                # noinspection PyTypeChecker
                assert not val_typ or isinstance(value, val_typ), \
                    "Field.set_value({}, {}, {}, {}, {}): value '{}' has wrong type {} (declared as {})" \
                    .format(value, idx_path, system, direction, protect, value, type(value), val_typ)
            self._aspects[key] = value

        return self

    def val(self, *idx_path, flex_sys_dir=True, system='', direction=''):
        value = self.value(system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        assert idx_path or isinstance(value, Value), \
            "Field.val() without idx_path ({}) has to point to Value instance (but got {})".format(idx_path, value)
        return value.val(*idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir)

    def set_val(self, val, *idx_path, system='', direction='', flex_sys_dir=True, extend=True, converter=None):
        idx_len = len(idx_path)
        value = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        if idx_len == 0:
            if converter:   # create system value if converter is specified and on last idx_path item
                self.set_converter(converter, system=system, direction=direction, extend=extend)
                value = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
            elif value is None and extend:
                value = Value()
                self.set_value(value, system=system, direction=direction)
        elif isinstance(value, (Value, type(None))) and extend:
            value = Record() if isinstance(idx_path[0], str) else (Records() if idx_len > 1 else Values())
            self.set_value(value, system=system, direction=direction)
        value.set_val(val, *idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir, extend=extend,
                      converter=converter)
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
            copied = dict()
            for asp_key, asp_val in aspects.items():  # type: (str, Any)
                if asp_key.startswith(FAT_VAL) and deeper(deepness, asp_val):
                    # FAT_VAL.asp_val is field value of VALUE_TYPES (Value, Records, ...)
                    copied[asp_key] = asp_val.copy(*idx_path, deepness=deeper(deepness, asp_val), **kwargs)
                else:
                    copied[asp_key] = asp_val
            aspects = copied
        return Field(**aspects)

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

    def aspect_exists(self, *aspect_types, system='', direction='', flex_sys_dir=False):
        if flex_sys_dir:
            key = self.find_aspect_key(*aspect_types, system=system, direction=direction)
        else:
            for aspect_type in aspect_types:
                key = aspect_key(aspect_type, system=system, direction=direction)
                if key in self._aspects:
                    break
            else:
                key = None
        return key

    def aspect_value(self, *aspect_types, system='', direction='', flex_sys_dir=False):
        key = self.aspect_exists(*aspect_types, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        if key:
            val = self._aspects.get(key)
        else:
            val = None
        return val

    def set_aspect(self, aspect_value, type_or_key, system='', direction='', protect=False):
        key = aspect_key(type_or_key, system=system, direction=direction)
        if protect:
            assert key not in self._aspects, "Field.set_aspect({}, {}, {}, {}, {}): key already exists in aspects ({})"\
                .format(type_or_key, aspect_value, system, protect, direction, key, self._aspects)
        if key.startswith(FAT_VAL):
            self.set_value(aspect_value, system=aspect_key_system(key), direction=aspect_key_direction(key))
        elif aspect_value is None:
            self.del_aspect(key)
        else:
            assert key != FAT_NAME or isinstance(aspect_value, tuple) or not field_name_idx_path(aspect_value), \
                "Field.set_aspect(): digits cannot be used in the system-less/main field name '{}'".format(aspect_value)
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
            self.set_aspect(data, key, protect=True)
        return self

    def del_name(self, system='', direction=''):
        self.del_aspect(FAT_NAME, system=system, direction=direction)
        return self

    def set_name(self, name, system='', direction='', protect=False):
        self.set_aspect(name, FAT_NAME, system=system, direction=direction, protect=protect)
        return self

    def rec(self, system='', direction='') -> Optional[Record]:
        return self.aspect_value(FAT_REC, system=system, direction=direction, flex_sys_dir=True)

    def set_rec(self, rec, system='', direction=''):
        self.set_aspect(rec, FAT_REC, system=system, direction=direction)
        return self

    def idx(self, system='', direction=''):
        return self.aspect_value(FAT_IDX, system=system, direction=direction, flex_sys_dir=True)

    def set_idx(self, idx, system='', direction=''):
        self.set_aspect(idx, FAT_IDX, system=system, direction=direction)
        return self

    def value_type(self, system='', direction=''):
        return self.aspect_value(FAT_TYPE, flex_sys_dir=True, system=system, direction=direction) or Value

    def set_value_type(self, value_type, system='', direction='', protect=False):
        assert value_type in VALUE_TYPES, "Invalid value type {} (allowed are only {})".format(value_type, VALUE_TYPES)
        if not self.aspect_exists(FAT_VAL, system=system, direction=direction, flex_sys_dir=False):
            system = direction = ''     # don't create separate system value type if no system value exists
        self.set_aspect(value_type, FAT_TYPE, system=system, direction=direction, protect=protect)
        return self

    def calculator(self, system='', direction=''):
        return self.aspect_value(FAT_CAL, system=system, direction=direction)

    def set_calculator(self, calculator, system='', direction='', protect=False):
        return self.set_aspect(calculator, FAT_CAL, system=system, direction=direction, protect=protect)

    def _ensure_system_value(self, system, direction=''):
        if not self.aspect_exists(FAT_VAL, system=system, direction=direction):
            self.set_value(Value(), system=system, direction=direction)

    def validator(self, system='', direction=''):
        return self.aspect_value(FAT_CHK, system=system, direction=direction)

    def set_validator(self, validator, system='', direction='', protect=False):
        assert system != '', "Field validator can only be set for a given/non-empty system"
        self._ensure_system_value(system, direction=direction)
        return self.set_aspect(validator, FAT_CHK, system=system, direction=direction, protect=protect)

    def converter(self, system='', direction=''):
        return self.aspect_value(FAT_CON, system=system, direction=direction)

    def set_converter(self, converter, system='', direction='', extend=False):
        assert system != '', "Field converter can only be set for a given/non-empty system"
        self._ensure_system_value(system, direction=direction)
        return self.set_aspect(converter, FAT_CON, system=system, direction=direction, protect=extend)

    def filter(self, system='', direction=''):
        return self.aspect_value(FAT_FLT, system=system, direction=direction)

    def set_filter(self, filter_func, system='', direction='', protect=False):
        return self.set_aspect(filter_func, FAT_FLT, system=system, direction=direction, protect=protect)

    def sql_expression(self, system='', direction=''):
        return self.aspect_value(FAT_SQE, system=system, direction=direction)

    def set_sql_expression(self, sql_expression, system='', direction='', protect=False):
        return self.set_aspect(sql_expression, FAT_SQE, system=system, direction=direction, protect=protect)

    def append_record(self, system='', direction=''):
        value = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=True)
        if isinstance(value, Records) or self.value_type(system=system, direction=direction) == Records:
            if not isinstance(value, Records):
                value = Records()
                self.set_value(value, system=system, direction=direction)
            rec = Record(system=system, direction=direction)
            value.append(rec)
            return True
        return False

    def clear_vals(self, system='', direction='', flex_sys_dir=True):
        """
        clear/reset field values
        :param system:          system of the field value to clear, pass None for to clear all field values.
        :param direction:       direction of the field value to clear.
        :param flex_sys_dir:    if True then also clear field value if system is given and field has no system value.
        :return:                self (this Field instance).
        """
        if system is None:
            for asp_key, asp_val in self._aspects:
                if asp_key.startswith(FAT_VAL):
                    asp_val.clear_val()
        else:
            asp_val = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
            if asp_val is not None:
                asp_val.clear_val()
        return self

    def convert_and_validate(self, val, system='', direction=''):
        converter = self.aspect_value(FAT_CON, system=system, direction=direction)
        if converter:
            assert callable(converter)
            val = converter(self, val)

        validator = self.aspect_value(FAT_CHK, system=system, direction=direction)
        if validator:
            assert callable(validator)
            if not validator(self, val):
                return None

        return val

    def pull(self, from_system):
        assert from_system, "Field.pull() with empty value in from_system is not allowed"
        direction = FAD_FROM
        val = self.val(system=from_system, direction=direction)

        validator = self.aspect_value(FAT_CHK, system=from_system, direction=direction)
        if validator:
            assert callable(validator)
            if not validator(self, val):
                return None

        converter = self.aspect_value(FAT_CON, system=from_system, direction=direction)
        if converter:
            assert callable(converter)
            val = converter(self, val)

        self.set_val(val)

        return self

    def push(self, onto_system):
        assert onto_system, "Field.push() with empty value in onto_system is not allowed"
        direction = FAD_ONTO
        val = self.convert_and_validate(self.val(), system=onto_system, direction=direction)
        if val is not None:
            self.set_val(val, system=onto_system, direction=direction)
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

    def rec_field_val(self, name, system='', direction=''):
        rec = self.rec(system=system, direction=direction)
        field = rec[name]
        return field.val(system=system, direction=direction)

    rfv = rec_field_val

    def system_rec_val(self, name=None, system='', direction=''):
        rec = self.rec(system=system, direction=direction)
        if name:
            # noinspection PyTypeChecker
            field = rec[name]
        else:
            field = self
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
