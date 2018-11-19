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
DUMMY_FIELD_NAME = '_f_n_'

# field aspect types/prefixes
FAT_IDX = 'idx'                 # field name within Record or list index within Records/Values
FAT_VAL = 'vle'                 # field value - storing one of the VALUE_TYPES instance
FAT_REC = 'rcd'                 # root Record instance
FAT_RCX = 'rcx'                 # field index path (idx_path) rom root Record instance
FAT_CAL = 'clc'                 # calculator callable
FAT_CHK = 'chk'                 # validator callable
FAT_CNV = 'cnv'                 # system value converter callable
FAT_FLT = 'flt'                 # field filter callable
FAT_SQE = 'sqc'                 # SQL expression for to fetch field value from db

ALL_FATS = (FAT_IDX, FAT_VAL, FAT_REC, FAT_RCX, FAT_CAL, FAT_CHK, FAT_CNV, FAT_FLT, FAT_SQE)

# field aspect directions
FAD_FROM = 'From'
FAD_ONTO = 'Onto'

# aspect key string lengths/structure
_ASP_TYPE_LEN = 3
_ASP_DIR_LEN = 4
_ASP_SYS_MIN_LEN = 2


def aspect_key(type_or_key, system='', direction=''):
    """
    compiles an aspect dict key from the given args
    :param type_or_key:     either FAT_* type or full key (including already the system and direction)-
    :param system:          system id string (if type_or_key is a pure FAT_* constant).
    :param direction:       direction string FAD_* constant (if type_or_key is a pure FAT_* constant).
    :return:                compiled aspect key as string.
    """
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
    """
    determines the system id string from an aspect key.
    :param key:     aspect key string.
    :return:        system id (SDI_* constant).
    """
    beg = _ASP_TYPE_LEN
    if len(key) > _ASP_TYPE_LEN + _ASP_DIR_LEN and key[beg:beg + _ASP_DIR_LEN] in (FAD_FROM, FAD_ONTO):
        beg += _ASP_DIR_LEN
    return key[beg:]


def aspect_key_direction(key):
    """
    determines the direction id string from an aspect key.
    :param key:     aspect key string.
    :return:        direction id (FAD_* constant).
    """
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
    """
    converts a field name path string into an index path tuple.
    :param field_name:  field name or field name path string.
    :return:            index path tuple (idx_path) or None if the field name has no deeper path.
     """
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


def init_current_index(value, idx_path, use_curr_idx):
    idx, *idx2 = use_current_index(value, idx_path, use_curr_idx, check_idx_type=True)

    if value.current_idx is None:
        value.current_idx = idx
    if isinstance(value, (Values, Records)):
        if value.idx_min is None or idx < value.idx_min:
            value.idx_min = idx
        if value.idx_max is None or idx > value.idx_max:
            value.idx_max = idx

    return (idx, ) + tuple(idx2)


def use_current_index(value, idx_path, use_curr_idx, check_idx_type=False):
    msg = "use_current_index() expects "
    assert isinstance(idx_path, (tuple, list)) and len(idx_path), msg + "non-empty idx_path"
    assert isinstance(use_curr_idx, (Value, type(None))), msg + "None/Value in use_curr_idx"

    idx, *idx2 = idx_path

    if isinstance(value, (Values, Records)):
        idx_type = int
    elif isinstance(value, Record):
        idx_type = str
    else:
        assert False, msg + "value type of Values, Records or Record, but got {}".format(type(value))
    if check_idx_type:
        assert isinstance(idx, idx_type), "index type {} in idx_path[0], but got {}".format(idx_type, type(idx))

    if use_curr_idx:
        for level, val in enumerate(use_curr_idx):
            if val == 0 and value.current_idx is not None:
                idx = value.current_idx
            use_curr_idx[level] -= 1

    return (idx, ) + tuple(idx2)


def set_current_index(value, idx=None, add=None):
    allowed_types = (Values, Records, Record)
    msg = "set_current_index() expects "
    assert isinstance(value, allowed_types), msg + "value arg of type, but got {}".format(allowed_types, type(value))
    assert isinstance(idx, (int, str)) ^ isinstance(add, int), msg + "either int/str in idx or int in add"

    if idx is not None:
        value.current_idx = idx
    else:
        value.current_idx += add

    return value.current_idx


class Value(list):
    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except IndexError:
            if not isinstance(key, int) or key not in (-1, 0):
                return None
            return ''

    def __setitem__(self, key, value):
        while True:
            try:
                return super().__setitem__(key, value)
            except IndexError:
                if not isinstance(key, int):
                    raise IndexError("Value() expects key of type int, but got {} of type {}".format(key, type(key)))
                self.append('')

    def __repr__(self):
        return "Value([" + ",".join(repr(v) for v in self) + "])"

    def deeper_item(self, idx_path, **__):
        # adding check_only kwarg for to use in Record.__contains__ for to prevent Assertion error we could add:
        # assert len(idx_path) == 0, "{} has no deeper value requested by idx_path {}".format(self, idx_path)
        return self if len(idx_path) == 0 else None

    def value(self, *idx_path, **__):
        assert isinstance(idx_path, (tuple, list)) and len(idx_path) == 0, \
            "Value.value() passed non-empty idx_path list {}".format(idx_path)
        return self

    def set_value(self, value, *idx_path, **__):
        assert isinstance(idx_path, (tuple, list)) and len(idx_path) == 0, \
            "Value.set_value({}) passed non-empty idx_path list {}".format(value, idx_path)
        assert isinstance(value, Value), "{}.set_value({}, {}) expecting Value type".format(self, value, __)
        self.append(value[-1])
        return self

    def val(self, *idx_path, **__):
        idx_len = len(idx_path)
        if idx_len == 0 or (idx_len == 1 and isinstance(idx_path[0], int)):
            return self[idx_path[0] if idx_len else -1]
        return None

    def set_val(self, val, *idx_path, **__):
        assert isinstance(idx_path, (tuple, list)) and len(idx_path) <= 1, \
            "Value.set_val({}) idx_path list {} has more than one entry".format(val, idx_path)
        assert not isinstance(val, VALUE_TYPES), "Value.set_val({}) got unexpected val type {}".format(val, type(val))
        self[idx_path[0] if isinstance(idx_path, (tuple, list)) and len(idx_path) else -1] = val
        return self

    def copy(self, *_, **__):
        """
        copy the value of this Value instance into a new one
        :return:                new Value instance containing the same immutable value.
        """
        return Value(super().copy())

    def clear_vals(self, **__):
        # use self[-1] = '' fro to clear only the newest/top val
        self.clear()
        return self


class Values(list):
    def __init__(self, seq=()):
        super().__init__(seq)
        self.current_idx = self.idx_min = self.idx_max = None

    def __repr__(self):
        return ("Values" if type(self) == Values else "Records") + "([" + ",".join(repr(v) for v in self) + "])"

    def value(self, *idx_path, system='', direction='', **kwargs):
        if len(idx_path) == 0:
            return self
        idx, *idx2 = idx_path
        return self[idx].value(*idx2, system=system, direction=direction, **kwargs)

    def set_value(self, value, *idx_path, system='', direction='', protect=False, root_rec=None, root_idx=None,
                  use_curr_idx=None):
        assert len(idx_path), \
            "Values/Records.set_value() idx_path '{}' must be non-empty tuple or list".format(idx_path)

        idx, *idx2 = init_current_index(self, idx_path, use_curr_idx)
        self[idx].set_value(value, *idx2, system=system, direction=direction, protect=protect,
                            root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)
        return self

    def val(self, *idx_path, system='', direction='', flex_sys_dir=True, use_curr_idx=None, **kwargs):
        idx_len = len(idx_path)
        if idx_len == 0:
            val = list(self)
        else:
            idx, *idx2 = use_current_index(self, idx_path, use_curr_idx)
            if isinstance(idx, int) and idx < len(self):
                val = self[idx].val(*idx2, system=system, direction=direction, flex_sys_dir=flex_sys_dir,
                                    use_curr_idx=use_curr_idx, **kwargs)
            else:
                val = None
        return val

    def set_val(self, val, *idx_path, system='', direction='', flex_sys_dir=True,
                protect=False, extend=True, converter=None, root_rec=None, root_idx=None, use_curr_idx=None):
        idx, *idx2 = init_current_index(self, idx_path, use_curr_idx)
        list_len = len(self)
        item_type = Value if type(self) == Values else Record
        if extend and list_len <= idx:
            for _ in range(idx - list_len + 1):
                self.append(item_type())
        if idx2:
            self[idx].set_val(val, *idx2, system=system, direction=direction, flex_sys_dir=flex_sys_dir,
                              protect=protect, extend=extend, converter=converter, root_rec=root_rec, root_idx=root_idx,
                              use_curr_idx=use_curr_idx)
        else:
            self[idx] = val or item_type()
        return self

    def deeper_item(self, idx_path, system='', direction='', flex_sys_dir=True):
        idx_len = len(idx_path)
        assert isinstance(idx_path, (tuple, list)) and idx_len, \
            "Values/Records.deeper_item(): idx_path '{}' must be non-empty tuple or list".format(idx_path)
        lst_len = len(self)
        lst_idx = idx_path[0]
        assert isinstance(lst_idx, int) and lst_len > lst_idx, \
            "Values/Records first item of idx_path '{}' is not integer or its value is less than {}"\
            .format(idx_path, lst_len)
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
        self.current_idx = self.idx_min = self.idx_max = None
        return self


class Records(Values):
    def set_field(self, fld_or_val, *idx_path, system='', direction='', protect=False,
                  root_rec=None, root_idx=None, use_curr_idx=None):
        assert len(idx_path) > 1, "Records.set_field() idx_path {} too short; expected 2 or more items".format(idx_path)
        idx, *idx2 = init_current_index(self, idx_path, use_curr_idx)
        assert isinstance(idx, int), \
            "Records.set_field() 1st item of idx_path {} has to be integer, got {}".format(idx_path, type(idx_path[0]))
        for _ in range(idx - len(self) + 1):
            self.append(Record())
        rec = self[idx]
        rec.set_field(fld_or_val, *idx2, system=system, direction=direction, protect=protect,
                      root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)
        return self

    def leafs(self, system='', direction='', flex_sys_dir=True):
        for item in self:
            yield from item.leafs(system=system, direction=direction, flex_sys_dir=flex_sys_dir)

    def leaf_indexes(self, *idx_path, system='', direction='', flex_sys_dir=True):
        for idx, item in enumerate(self):
            item_idx = idx_path + (idx, )
            yield from item.leaf_indexes(*item_idx, system=system, direction=direction, flex_sys_dir=flex_sys_dir)

    def set_env(self, system='', direction='', root_rec=None, root_idx=None):
        for idx, rec in enumerate(self):
            rec.set_env(system=system, direction=direction, root_rec=root_rec, root_idx=root_idx + (idx, ))
        return self


class Record(OrderedDict):
    # isinstance(..., dict) not working if using MutableMapping instead of OrderedDict
    # dict should not be used because **instance will then not work see the answer of Groxx in the stackoverflow
    # .. question https://stackoverflow.com/questions/3387691/how-to-perfectly-override-a-dict/47361653#47361653
    def __init__(self, fields=None, system='', direction='', action=''):
        """
        ordered collection of Field items.
        :param fields:      OrderedDict/dict of Field instances (field order is not preserved when using dict)
                            or list of (field_name, fld_or_val) tuples.
        :param system:      main/current system of this record,
        :param direction:   interface direction of this record.
        :param action:      current action (see ACTION_INSERT, ACTION_SEARCH, ACTION_DELETE, ...)
        """
        self._fields = self     # using internal store of OrderedDict() while keeping code better readable/maintainable
        self.system = system
        self.direction = direction
        self.action = action
        self.current_idx = None
        if fields:
            self.add_fields(fields)

        super().__init__(*(), **self._fields)   # OrderedDict signature is: *args, **kwargs)

        self.system_fields = dict()    # map system field name as key to Field instance (as value).
        self.collected_system_fields = list()   # system fields found by collect_system_fields()

    def __repr__(self):
        return "Record([" + ", ".join("(" + repr(k) + "," + repr(v) + ")" for k, v in self.items()) + "])"

    def __contains__(self, idx_path):
        item = self.deeper_item(idx_path)
        return bool(item)

    def __getitem__(self, key):
        value = self.deeper_item(key)
        if value is None:
            raise KeyError("There is no item with the idx_path '{}' in this Record/OrderedDict ({})".format(key, self))
        return value

    def __setitem__(self, key, value):
        idx_path = key if isinstance(key, (tuple, list)) else (key, )
        self.set_field(value, *idx_path)

    def deeper_item(self, idx_path, system='', direction='', flex_sys_dir=True):
        if isinstance(idx_path, int) \
                or (isinstance(idx_path, (tuple, list)) and idx_path and isinstance(idx_path[0], int)):
            return None     # RETURN item not found (caller doing deep search with integer idx)

        if isinstance(idx_path, (tuple, list)):
            if len(idx_path) == 1 and isinstance(idx_path[0], (tuple, list)):
                idx_path = idx_path[0]
        else:
            assert isinstance(idx_path, str), \
                "idx_path '{}' is of {}; expected tuple, list, string or int".format(idx_path, type(idx_path))
            idx_path = field_name_idx_path(idx_path) or (idx_path, )
        fld_idx = idx_path[0]

        idx_len = len(idx_path)
        assert idx_len, "Record.deeper_item(): idx_path '{}' must be a non-empty tuple or list".format(idx_path)

        if system is None:
            system = self.system
        if direction is None:
            direction = self.direction

        for fld_nam, field in self._fields.items():
            if fld_nam == fld_idx:
                if idx_len == 1:
                    break
                fld = field.deeper_item(idx_path[1:], system=system, direction=direction, flex_sys_dir=flex_sys_dir)
                if fld is not None:
                    field = fld
                    break
            if idx_len == 1 and field.system_to_main_field_name(fld_idx):
                return field
        else:
            field = None

        return field

    def value(self, *idx_path, system='', direction='', **kwargs):
        if len(idx_path) == 0:
            return self
        idx, *idx2 = idx_path
        return self._fields[idx].value(*idx2, system=system, direction=direction, **kwargs)

    def set_value(self, value, *idx_path, system='', direction='', protect=False, root_rec=None, root_idx=None,
                  use_curr_idx=None):
        idx, *idx2 = init_current_index(self, idx_path, use_curr_idx)
        self[idx].set_value(value, *idx2, system=system, direction=direction, protect=protect,
                            root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)
        return self

    def val(self, *idx_path, system='', direction='', flex_sys_dir=True, use_curr_idx=None, **kwargs):
        idx_len = len(idx_path)
        if idx_len == 0:
            val = OrderedDict()
            for idx, field in self._fields.items():
                val[idx] = field.val(system=system, direction=direction, flex_sys_dir=flex_sys_dir, **kwargs)
        else:
            idx, *idx2 = use_current_index(self, idx_path, use_curr_idx)
            if idx in self._fields:
                field = self._fields[idx]
                val = field.val(*idx2, system=system, direction=direction, flex_sys_dir=flex_sys_dir,
                                use_curr_idx=use_curr_idx, **kwargs)
            else:
                val = None
        return val

    def set_val(self, val, *idx_path, system='', direction='', flex_sys_dir=True,
                protect=False, extend=True, converter=None, root_rec=None, root_idx=None, use_curr_idx=None):
        assert len(idx_path), "Record.set_val() expect 2 or more args - missing field name or index"

        idx, *idx2 = init_current_index(self, idx_path, use_curr_idx)
        if extend and idx not in self:
            field = Field()
            # field.set_system_root_rec_idx(root_rec, root_idx, idx2)
            self.add_field(field, idx)
            protect = False
        self._fields[idx].set_val(val, *idx2, system=system, direction=direction, flex_sys_dir=flex_sys_dir,
                                  protect=protect, extend=extend, converter=converter,
                                  root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)
        return self

    def leafs(self, system='', direction='', flex_sys_dir=True):
        for idx, field in self._fields.items():
            yield from field.leafs(system=system, direction=direction, flex_sys_dir=flex_sys_dir)

    def leaf_indexes(self, *idx_path, system='', direction='', flex_sys_dir=True):
        for idx, field in self._fields.items():
            fld_idx = idx_path + (idx, )
            yield from field.leaf_indexes(*fld_idx, system=system, direction=direction, flex_sys_dir=flex_sys_dir)

    def add_field(self, field, idx=''):
        """
        add Field instance to this Record instance.
        :param field:   Field instance to add.
        :param idx:     key/idx string for to map and identify this field (mostly identical to field.name).
        :return:        self.
        """
        msg = "add_field({}, {}): ".format(field, idx)
        assert isinstance(field, Field), msg + "field arg has to be of type Field (not {})".format(type(field))
        assert isinstance(idx, str), msg + "idx arg has to be of type str (not {})".format(type(idx))

        if not idx:
            idx = field.name
            if idx == DUMMY_FIELD_NAME:
                idx += chr(ord('A') + len(self._fields))
        elif idx and (not field.name or field.name.startswith(DUMMY_FIELD_NAME)):
            field.name = idx

        assert idx not in self._fields, msg + "Record '{}' has already a field with the key '{}'".format(self, idx)

        super().__setitem__(idx, field)     # self._fields[idx] = field
        return self

    def set_field(self, fld_or_val, *idx_path, system=None, direction=None, protect=False,
                  root_rec=None, root_idx=None, use_curr_idx=None):
        idx_len = len(idx_path)
        assert idx_len, "Record.set_field() expect 2 or more args - missing field name/-path"
        assert isinstance(idx_path[0], str), \
            "First item of Record idx_path '{}', specifying the field name, has to be of type string but is {}"\
            .format(idx_path, type(idx_path))
        if idx_len == 1:
            nam_path = field_name_idx_path(idx_path[0])
            if nam_path:
                idx_path = nam_path
                idx_len = len(idx_path)

        if system is None:
            system = self.system
        if direction is None:
            direction = self.direction
        fld_idx, *idx2 = init_current_index(self, idx_path, use_curr_idx)
        if not isinstance(fld_or_val, Field):
            if use_curr_idx:
                use_curr_idx.set_val(use_curr_idx.val() + 1)
            self.set_val(fld_or_val, *idx_path, system=system, direction=direction, protect=protect,
                         root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)
        elif fld_idx in self._fields:
            if idx_len == 1:
                assert not protect, "set_field(): field {} exits already (and protect passed as True)".format(fld_idx)
                fld_or_val.set_system_root_rec_idx(root_rec, root_idx)
                super().__setitem__(fld_idx, fld_or_val)
            else:
                ror = self.value(fld_idx)    # if protect==True then should be of Record or Records
                if not isinstance(ror, (Record, Records)):
                    assert not protect, \
                        "value ({}) of field {} is of {}; expected Record or Records or pass protect arg as False"\
                        .format(ror, idx_path, type(ror))
                    ror = Record() if isinstance(idx2[0], str) else Records()
                    self.set_value(ror, fld_idx, root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)
                ror.set_field(fld_or_val, *idx2, system=system, direction=direction, protect=protect,
                              root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)
        elif idx_len == 1:
            fld_or_val.set_system_root_rec_idx(root_rec, root_idx)
            self.add_field(fld_or_val, fld_idx)
        else:
            if use_curr_idx:
                use_curr_idx.set_val(use_curr_idx.val() + 1)
            *rec_path, deep_fld_name = idx_path
            rec = self.deeper_item(rec_path)
            if not rec:     # if no deeper Record instance exists, then create new Record via empty dict and set_val()
                self.set_val(dict(), *rec_path, protect=protect, use_curr_idx=use_curr_idx)
                rec = self.deeper_item(rec_path)
            if use_curr_idx:
                use_curr_idx.set_val(use_curr_idx.val() - len(rec_path))
            rec.set_field(fld_or_val, deep_fld_name, system=system, direction=direction, protect=protect,
                          root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)

    def add_fields(self, fields):
        """
        adding fields to this Record instance.

        :param fields:  either a dict, a Record or a list with (key/field_name, val/Field) tuples.
                        Key strings that are containing digits/numbers are interpreted as name/idx paths (then also the
                        specified sub-Records/-Fields will be created).
                        Values can be either Field instances or field vals.
        :return:        self
        """
        if isinstance(fields, dict):
            items = fields.items()
        else:
            items = fields
        for name, field in items:
            idx_path = name if isinstance(name, (tuple, list)) else (name, )
            self.set_field(field, *idx_path, protect=True)
        return self

    def add_system_fields(self, system_fields, sys_fld_indexes=None):
        """
        add/set fields from a system field tuple. This Record instance need to have system and direction specified/set.
        :param system_fields:   tuple/list of tuples/lists with generic and system field names and optional field aspect
                                values. The index of field names and aspects within the inner tuples/lists get specified 
                                by sys_fld_indexes.
        :param sys_fld_indexes: mapping/map-item-indexes of the inner tuples of system_fields. Keys are field aspect
                                types (FAT_* constants), optionally extended with a direction (FAD_* constant).
        :return:                self
        """
        assert isinstance(system_fields, (tuple, list)) and len(system_fields), \
            "system_fields must be non-empty list or tuple, got {}".format(system_fields)
        assert self.system and self.direction, "add_system_fields() expects non-empty Record.system/.direction values"
        sys_nam_key = FAT_IDX + self.direction
        if sys_fld_indexes is None:
            sys_fld_indexes = {sys_nam_key: 0, FAT_IDX: 1, FAT_FLT: 2, FAT_VAL: 3,
                               FAT_CNV + FAD_FROM: 4, FAT_CNV + FAD_ONTO: 5}
        else:
            assert isinstance(sys_fld_indexes, dict), "sys_fld_indexes must be an instance of dict, got {} instead"\
                .format(type(sys_fld_indexes))
            assert FAT_IDX in sys_fld_indexes and sys_nam_key in sys_fld_indexes, \
                "add_system_fields(): field and/or system field names missing in system field index map {}"\
                .format(sys_fld_indexes)
        err = [_ for _ in system_fields if sys_fld_indexes[sys_nam_key] >= len(_)]
        assert not err, "system_fields contains entries with missing system name {}: {}".format(sys_nam_key, err)

        for fas in system_fields:
            map_len = len(fas)
            sfi = sys_fld_indexes.copy()    # fresh copy needed because field names and converter get popped from sfi

            fld_nam_i = sfi.pop(FAT_IDX)
            if map_len <= fld_nam_i or fas[fld_nam_i] is None:
                continue
            field_name = fas[fld_nam_i]
            if isinstance(field_name, (tuple, list)):
                idx_path = field_name
                field_name = field_name[-1]
            else:
                idx_path = (field_name, )

            sys_name = fas[sfi.pop(sys_nam_key)].strip('/')

            field = self.deeper_item(idx_path, system=self.system, direction=self.direction)
            if not field:
                field = Field()
                field.name = field_name
                field.set_name(sys_name, system=self.system, direction=self.direction, protect=True)
                field.set_root_rec(self, system=self.system, direction=self.direction)
                # add additional aspects: first always add converter and value (for to create separate system value)
                cnv_func = None
                cnv_key = FAT_CNV + self.direction
                if map_len > sfi.get(cnv_key, map_len):
                    cnv_func = fas[sfi.pop(cnv_key)]
                elif map_len > sfi.get(FAT_CNV, map_len):
                    cnv_func = fas[sfi.pop(FAT_CNV)]
                if cnv_func:
                    field.set_converter(cnv_func, system=self.system, direction=self.direction, extend=True)
                # now add all other field aspects (allowing calculator function specified in FAT_VAL aspect)
                for fa, fi in sfi.items():
                    if fa.startswith(FAT_CNV):
                        continue        # skip converter for other direction
                    if map_len > fi and fa[_ASP_TYPE_LEN:] in ('', self.direction) and fas[fi] is not None:
                        if not fa.startswith(FAT_VAL):
                            field.set_aspect(fas[fi], fa[:_ASP_TYPE_LEN], system=self.system, direction=self.direction,
                                             protect=True)
                        elif callable(fas[fi]):     # is a calculator specified in value/FAT_VAL item
                            field.set_calculator(fas[fi], system=self.system, direction=self.direction, protect=True)
                        else:
                            field.set_val(fas[fi], system=self.system, direction=self.direction, protect=True)
                self.set_field(field, *idx_path, protect=True, root_rec=self, root_idx=idx_path)

            self.system_fields[sys_name] = field

        return self
    
    def collect_system_fields(self, sys_fld_name_path, path_sep):
        self.collected_system_fields = list()

        deep_sys_fld_name = sys_fld_name_path[-1]
        full_path = path_sep.join(sys_fld_name_path)
        for sys_name, field in self.system_fields.items():
            if sys_name == deep_sys_fld_name or sys_name == full_path or full_path.endswith(path_sep + sys_name):
                if field not in self.collected_system_fields:
                    self.collected_system_fields.append(field)

        return self.collected_system_fields

    def copy(self, *idx_path, deepness=0, to_rec=None, filter_func=None, fields_patches=None):
        """
        copy the fields of this record
        :param idx_path:        list of path items of field names and/or indexes.
        :param deepness:        deep copy level: <0==see deeper(), 0==only copy current instance, >0==deep copy
                                to deepness value - please note that Field occupies two deepness: 1st=Field, 2nd=Value).
        :param to_rec:          destination record; pass None to create new Record instance.
        :param filter_func:     method called for each copied field (return True to filter/hide/not-include into copy).
        :param fields_patches:  dict with keys as idx_paths and values as dict of aspect keys and values (for to
                                overwrite aspects in the copied Record instance).
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

            if deeper(deepness, field):
                new_path = (name, ) if new_rec else idx_path + (name, )
                field = field.copy(*new_path,  deepness=deeper(deepness, field),
                                   to_rec=None if new_rec else to_rec,
                                   filter_func=filter_func, fields_patches=fields_patches)
            elif name in to_rec:
                field = to_rec[name]

            if fields_patches and name in fields_patches:
                field.set_aspects(**fields_patches[name])

            if new_rec:
                to_rec.add_field(field, name)
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

    def set_env(self, system='', direction='', action='', root_rec=None, root_idx=()):
        if system is not None:
            self.system = system
        if direction is not None:
            self.direction = direction
        if action is not None:
            self.action = action
        if root_rec is not None:
            for idx, field in self._fields.items():
                field.set_env(system=system, direction=direction, root_rec=root_rec, root_idx=root_idx + (idx, ))
        return self

    def set_current_system_index(self, sys_fld_name_prefix, path_sep, idx_val=None, idx_add=1):
        prefix = sys_fld_name_prefix + path_sep
        for sys_path, field in self.system_fields.items():
            if sys_path.startswith(prefix):
                rec = field.root_rec(system=self.system, direction=self.direction)
                idx_path = field.root_idx(system=self.system, direction=self.direction)
                if idx_path:
                    for off, idx in enumerate(idx_path):
                        if isinstance(idx, int):
                            value = rec.value(*idx_path[:off])
                            set_current_index(value, idx=idx_val, add=idx_add)
                            return self

    def sql_select(self, from_system):
        """
        return list of sql column names/expressions for given system.
        :param from_system: system from which the data will be selected/fetched.
        :return:            list of sql column names/expressions.
        """
        column_expressions = list()
        for field in self._fields.values():
            name = field.aspect_value(FAT_IDX, system=from_system, direction=FAD_FROM)
            if name:
                expr = field.aspect_value(FAT_SQE, system=from_system, direction=FAD_FROM) or ""
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
        if FAT_IDX not in self._aspects:
            self._aspects[FAT_IDX] = DUMMY_FIELD_NAME

    def __repr__(self):
        return "Field(**{" + ", ".join([repr(k) + ": " + repr(v)
                                        for k, v in self._aspects.items() if not k.startswith(FAT_REC)]) + "})"

    def __str__(self):
        return "Field(" + repr(self._aspects) + ")"

    @property
    def name(self):
        return self._aspects.get(FAT_IDX)

    @name.setter
    def name(self, name):
        self._aspects[FAT_IDX] = name

    def __getitem__(self, idx_path):
        if not isinstance(idx_path, (tuple, list)):
            idx_path = (idx_path, )
        return self.value(*idx_path)

    def __setitem__(self, idx_path, value):
        if not isinstance(idx_path, (tuple, list)):
            idx_path = (idx_path, )
        self.set_value(value, *idx_path)

    def deeper_item(self, idx_path, system='', direction='', flex_sys_dir=True):
        idx_len = len(idx_path)
        assert isinstance(idx_path, (tuple, list)) and idx_len, \
            " Field idx_path '{}' must be non-empty tuple or list".format(idx_path)
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
        if value and isinstance(idx_path, (tuple, list)) and len(idx_path) > 0:
            value = value.value(*idx_path)
        return value

    def set_value(self, value, *idx_path, system='', direction='', protect=False, root_rec=None, root_idx=None,
                  use_curr_idx=None):
        assert isinstance(value, VALUE_TYPES), \
            "Field.set_value({}, {}, {}, {}, {}): value has to be of type {}, but got {}"\
            .format(value, idx_path, system, direction, protect, VALUE_TYPES, type(value))

        key = aspect_key(FAT_VAL, system=system, direction=direction)

        if isinstance(idx_path, (tuple, list)) and len(idx_path):
            self._aspects[key].set_value(value, *idx_path, system=system, direction=direction, protect=protect,
                                         root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)
        else:
            assert not protect or key not in self._aspects, \
                "Field.set_value({}, {}, {}, {}, {}): value key {} already exists in aspects ({})"\
                .format(value, idx_path, system, direction, protect, key, self._aspects)
            self.set_system_root_rec_idx(root_rec, root_idx)
            self._aspects[key] = value

        return self

    def val(self, *idx_path, system='', direction='', flex_sys_dir=True, use_curr_idx=None):
        value = self.value(system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        return value.val(*idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir,
                         use_curr_idx=use_curr_idx)

    def set_val(self, val, *idx_path, system='', direction='', flex_sys_dir=True,
                protect=False, extend=True, converter=None, root_rec=None, root_idx=None, use_curr_idx=None):
        idx_len = len(idx_path)
        value = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        if idx_len == 0:
            self.set_system_root_rec_idx(root_rec, root_idx)
            if converter:   # create system value if converter is specified and on leaf idx_path item
                self.set_converter(converter, system=system, direction=direction, extend=extend)
                value = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
            elif extend and (value is None or not isinstance(value, Value)):
                value = Value()
                self.set_value(value, system=system, direction=direction, protect=protect)
        elif isinstance(value, (Value, type(None))) and extend and not protect:
            value = Record() if isinstance(idx_path[0], str) \
                else (Records() if idx_len > 1 or isinstance(val, dict) else Values())
            self.set_value(value, system=system, direction=direction, protect=protect)
        value.set_val(val, *idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir,
                      protect=protect, extend=extend, converter=converter, root_rec=root_rec, root_idx=root_idx,
                      use_curr_idx=use_curr_idx)
        return self

    def leafs(self, system='', direction='', flex_sys_dir=True):
        value = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        if isinstance(value, (Value, Values)) and not isinstance(value, Records):
            yield self
        else:
            yield from value.leafs(system=system, direction=direction, flex_sys_dir=flex_sys_dir)

    def leaf_indexes(self, *idx_path, system='', direction='', flex_sys_dir=True):
        value = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        if isinstance(value, (Value, Values)) and not isinstance(value, Records):
            yield idx_path
        else:
            yield from value.leaf_indexes(*idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir)

    def copy(self, *idx_path, deepness=0, **kwargs):
        """
        copy the values of this field
        :param idx_path:        path of field names and/or list/Records/Values indexes.
        :param deepness:        deep copy level: <0==see deeper(), 0==only copy current instance, >0==deep copy
                                to deepness value - please note that Field occupies two deepness: 1st=Field, 2nd=Value).
        :param kwargs           additional arguments (will be passed on - most of them used by Record.copy).
        :return:                new/extended record instance.
        """
        aspects = self._aspects
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
            assert not direction, "Field.find_aspect_key({}, {}, {}) direction without system not allowed"\
                .format(aspect_types, system, direction)
            if system:
                for aspect_type in aspect_types:
                    for d in (FAD_ONTO, FAD_FROM):
                        keys.append(aspect_key(aspect_type, system=system, direction=d))
        if system:
            for aspect_type in aspect_types:
                keys.append(aspect_key(aspect_type, system=system))
        for aspect_type in aspect_types:
            keys.append(aspect_key(aspect_type))

        for key in keys:
            if key in self._aspects:
                return key

        return None

    def set_env(self, system='', direction='', root_rec=None, root_idx=None):
        value = self.value(system=system, direction=direction, flex_sys_dir=True)
        if isinstance(value, (Value, Values)):
            self.set_system_root_rec_idx(root_rec, root_idx)
        else:
            value.set_env(system=system, direction=direction, root_rec=root_rec, root_idx=root_idx)
        return self

    def set_system_root_rec_idx(self, root_rec, root_idx):
        if root_rec is not None:
            system = root_rec.system
            direction = root_rec.direction
            self.set_root_rec(root_rec, system=system, direction=direction)

            if root_idx is not None:
                self.set_root_idx(root_idx, system=system, direction=direction)
        return self

    def system_to_main_field_name(self, system_field_name):
        for asp_key, asp_val in self._aspects.items():
            if asp_key.startswith(FAT_IDX) and asp_val == system_field_name:
                return self.name

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
            assert key not in self._aspects, "Field.set_aspect({}, {}, {}, {}, {}): {} already exists in aspects ({})"\
                .format(aspect_value, type_or_key, system, direction, protect, key, self._aspects)
        if key.startswith(FAT_VAL):
            self.set_value(aspect_value, system=aspect_key_system(key), direction=aspect_key_direction(key))
        elif aspect_value is None:
            self.del_aspect(key)
        else:
            assert key != FAT_IDX or isinstance(aspect_value, (tuple, list)) or not field_name_idx_path(aspect_value),\
                "Field.set_aspect(): digits cannot be used in system-less/generic field name '{}'".format(aspect_value)
            self._aspects[key] = aspect_value
        return self

    def del_aspect(self, type_or_key, system='', direction=''):
        key = aspect_key(type_or_key, system=system, direction=direction)
        assert not key.startswith(FAT_VAL) and key != FAT_IDX, "Field name, value and system values not deletable"
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
        self.del_aspect(FAT_IDX, system=system, direction=direction)
        return self

    def set_name(self, name, system='', direction='', protect=False):
        self.set_aspect(name, FAT_IDX, system=system, direction=direction, protect=protect)
        return self

    def root_rec(self, system='', direction='') -> Optional[Record]:
        return self.aspect_value(FAT_REC, system=system, direction=direction, flex_sys_dir=True)

    def set_root_rec(self, rec, system='', direction=''):
        self.set_aspect(rec, FAT_REC, system=system, direction=direction)
        return self

    def root_idx(self, system='', direction=''):
        return self.aspect_value(FAT_RCX, system=system, direction=direction, flex_sys_dir=True)

    def set_root_idx(self, idx, system='', direction=''):
        self.set_aspect(idx, FAT_RCX, system=system, direction=direction)
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
        return self.aspect_value(FAT_CNV, system=system, direction=direction)

    def set_converter(self, converter, system='', direction='', extend=False):
        assert system != '', "Field converter can only be set for a given/non-empty system"
        self._ensure_system_value(system, direction=direction)
        return self.set_aspect(converter, FAT_CNV, system=system, direction=direction, protect=extend)

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
        if isinstance(value, Records):
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
                    asp_val.clear_vals()
        else:
            asp_val = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
            if asp_val is not None:
                asp_val.clear_vals()
        return self

    def convert_and_validate(self, val, system='', direction=''):
        converter = self.aspect_value(FAT_CNV, system=system, direction=direction)
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

        converter = self.aspect_value(FAT_CNV, system=from_system, direction=direction)
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
                fld_name = fld_names[fld_idx]
                field = Field().set_name(fld_name).set_val(fld_val)
                root_rec = self.root_rec(system=system, direction=direction)
                root_idx = self.root_idx(system=system, direction=direction)
                field.set_system_root_rec_idx(root_rec, root_idx + (fld_name, ))
                rec.add_field(field)
            recs.append(rec)
        return recs

    def rec_field_val(self, name, system='', direction=''):
        root_rec = self.root_rec(system=system, direction=direction)
        field = root_rec[name]
        return field.val(system=system, direction=direction)

    rfv = rec_field_val

    def system_rec_val(self, name=None, system='', direction=''):
        root_rec = self.root_rec(system=system, direction=direction)
        if name:
            # noinspection PyTypeChecker
            field = root_rec[name]
        else:
            field = self
        return field.val(system=root_rec.system, direction=root_rec.direction)

    srv = system_rec_val

    def in_actions(self, *actions, system='', direction=''):
        root_rec = self.root_rec(system=system, direction=direction)
        if root_rec:
            return root_rec.action in actions

    ina = in_actions

    def parent(self, system='', direction='', types=None):
        root_rec = self.root_rec(system=system, direction=direction)
        root_idx = self.root_idx(system=system, direction=direction)
        while root_rec and root_idx:
            root_idx = root_idx[:-1]
            if root_idx:
                item = root_rec.value(*root_idx, system=system, direction=direction)
                if not types or isinstance(item, types):
                    return item
        return root_rec if not types or isinstance(root_rec, types) else None

    def current_records_idx(self, system='', direction=''):
        item = self.parent(system=system, direction=direction, types=(Records, ))
        if item:
            return item.current_idx

    crx = current_records_idx


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
