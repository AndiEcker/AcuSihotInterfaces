"""
use and manage external systems, including their provided data fields and configuration settings
"""
import os
import struct
import keyword
from collections import OrderedDict


# dummy field name (not used as data field but as placeholder, e.g. for to put xml groups)
DUMMY_FIELD_NAME = '___'

# field name special characters for to identify list indexes and sub-Records
FN_LIST_IDX_MARKER = '['
FN_SUB_REC_MARKER = '.'

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

# field aspect directions
FAD_FROM = 'From'
FAD_ONTO = 'Onto'


def aspect_key(aspect_type, system='', direction=''):
    key = aspect_type + direction + system
    assert key.isidentifier() and not keyword.iskeyword(), \
        "aspect_key({}, {}, {}): key '{}' contains invalid characters".format(aspect_type, system, direction, key)
    return key


class Value(list):
    def __init__(self, seq=('',)):
        super().__init__(seq)

    def value(self, *_):
        return self[-1]


class Values(list):
    pass


class Records(Values):
    pass


class Field:
    def __init__(self, **aspects):
        self._aspects = dict()
        self.add_aspects(aspects)

    def __getitem__(self, key_or_keys):
        return self.val(key_or_keys)

    @property
    def aspects(self):
        return self._aspects

    @property
    def name(self):
        return self._aspects.get(FAT_NAME)

    @name.setter
    def name(self, name):
        self._aspects[FAT_NAME] = name

    @property
    def rec(self):
        return self._aspects.get(FAT_REC)   # self.aspect_value(FAT_REC)

    @rec.setter
    def rec(self, new_rec):
        self._aspects[FAT_REC] = new_rec

    def idx(self, system='', direction=''):
        return self.aspect_value(FAT_IDX, inherited_aspect=True, system=system, direction=direction)

    def set_idx(self, idx, system='', direction=''):
        self.set_aspect(idx, FAT_IDX, system=system, direction=direction)

    def value(self, system='', direction=''):
        value = None
        key = self.aspect_exists(FAT_VAL, system=system, direction=direction)
        if key:
            value = self._aspects[key]
        else:
            key = self.aspect_exists(FAT_CAL, system=system, direction=direction)
            if key:
                value = self._aspects[key](self)
        return value

    def set_value(self, value, system='', direction=''):
        ori_val = value
        if not isinstance(value, (Value, Values, Records)):
            if not isinstance(value, (tuple, list)):
                value = Value((value, ))
            elif value:
                value = Values(value) if isinstance(value[0], Value) else Records(value)

        val_type = self.aspect_value(FAT_TYPE, inherited_aspect=True, system=system, direction=direction) or Value
        assert isinstance(value, val_type), \
            "set_value({}, {}, {}): value '{}' has wrong type {}".format(ori_val, system, direction, value, type(value))

        # self.set_aspect(value, FAT_VAL, system=system, direction=direction)
        self._aspects[aspect_key(FAT_VAL, system=system, direction=direction)] = value

        return self

    def val(self, *keys, system='', direction=''):
        val = self.value(system=system, direction=direction)
        if val is None:
            asp_val_key = self.find_key(FAT_VAL, system=system, direction=direction) or ''
            asp_cal_key = self.find_key(FAT_CAL, system=system, direction=direction) or ''
            asp_key = asp_val_key if len(asp_val_key) >= len(asp_cal_key) else asp_cal_key
            if not asp_key:
                return None
            val = self._aspects[asp_key]

        key_cnt = len(keys)
        idx = 0
        val_type = type(val)
        while idx < key_cnt and val_type in (Records, Values):
            key = keys[idx]
            assert type(key) in (int, str), \
                "val({}, {}, {}): key has to be of type int or str (not {})".format(keys, system, direction, type(key))
            assert key in val, \
                "val({}, {}, {}): key {} not found in value '{}'".format(keys, system, direction, key, val)
            self.set_idx(key, system=system, direction=direction)
            val = val[key]
            idx += 1
            val_type = type(val)

        return val.value(system=system, direction=direction)

    def convert_and_validate(self, value, system='', direction=''):
        converter = self.aspect_value(FAT_CON, system=system, direction=direction)
        if converter:
            value = converter(self, value)

        validator = self.aspect_value(FAT_CHK, system=system, direction=direction)
        if validator and not validator(self, value):
            return None

        return value

    def pull(self, system=''):
        direction = FAD_FROM
        val = self.value(system=system, direction=direction)

        validator = self.aspect_value(FAT_CHK, system=system, direction=direction)
        if validator and not validator(self, val):
            return None

        converter = self.aspect_value(FAT_CON, system=system, direction=direction)
        if converter:
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

    def find_key(self, aspect_type, system='', direction=''):
        keys = list()
        if direction:
            keys.append(aspect_key(aspect_type, system=system, direction=direction))
        if system:
            keys.append(aspect_key(aspect_type, system=system))
        keys.append(aspect_key(aspect_type))

        for key in keys:
            if key in self._aspects:
                return key

        return None

    def aspect_exists(self, aspect_type, inherited_aspect=False, system='', direction=''):
        if inherited_aspect:
            key = self.find_key(aspect_type, system=system, direction=direction)
        else:
            key = aspect_key(aspect_type, system=system, direction=direction)
        return key if key in self._aspects else None

    def aspect_value(self, aspect_type, inherited_aspect=False, system='', direction=''):
        key = self.aspect_exists(aspect_type, inherited_aspect=inherited_aspect, system=system, direction=direction)
        if key:
            val = self._aspects.get(key)
        else:
            val = None
        return val

    def add_aspects(self, aspects):
        iia_map = (
            (FAT_NAME, self.add_name),
            (FAT_VAL, self.add_value),
            (FAT_CAL, self.add_calculator),
            (FAT_CHK, self.add_validator),
            (FAT_CON, self.add_converter),
            )
        for key, data in aspects.items():
            for fat, met in iia_map:
                if key.startswith(fat):
                    met(key)
                    break
            else:
                # adding any other aspect to instance aspects w/o system/direction from kwargs
                self.add_aspect(key, data)
        return self

    def add_aspect(self, aspect_type, aspect_data, system='', direction=''):
        key = aspect_key(aspect_type, system=system, direction=direction)
        assert key not in self._aspects, "add_aspect({}, {}, {}, {}): key not found in aspects ({})"\
            .format(aspect_type, aspect_data, system, direction, key, self._aspects)
        self._aspects[key] = aspect_data
        return self

    def del_aspect(self, aspect_type, system='', direction=''):
        return self._aspects.pop(aspect_key(aspect_type, system=system, direction=direction))

    def set_aspect(self, aspect_value, aspect_type, system='', direction=''):
        if aspect_type == FAT_VAL:
            self.set_value(aspect_value, system=system, direction=direction)
        else:
            self._aspects[aspect_key(aspect_type, system=system, direction=direction)] = aspect_value
        return self

    def add_name(self, name, system='', direction=''):
        self.add_aspect(FAT_NAME, name, system=system, direction=direction)
        return self

    def del_name(self, system='', direction=''):
        self.del_aspect(FAT_NAME, system=system, direction=direction)
        return self

    def set_name(self, name, system='', direction=''):
        self.set_aspect(name, FAT_NAME, system=system, direction=direction)
        return self

    def full_name(self, *keys, base_name=''):
        key_names = ((FN_LIST_IDX_MARKER if isinstance(k, int) else FN_SUB_REC_MARKER) + k for k in keys)
        return (base_name or self.name) + "".join(key_names)

    def add_value(self, value, system='', direction=''):
        self.add_aspect(FAT_VAL, value, system=system, direction=direction)
        return self

    def append_value(self, value, system='', direction=''):
        if aspect_key(FAT_VAL, system=system, direction=direction) in self._aspects:
            self.value(system=system, direction=direction).append(value)
        else:
            self.add_aspect(FAT_VAL, list((value, )), system=system, direction=direction)
        return self

    def del_value(self, system='', direction=''):
        self.del_aspect(FAT_VAL, system=system, direction=direction)
        return self

    def value_type(self, system='', direction=''):
        return self.aspect_value(FAT_TYPE, system=system, direction=direction) or Value

    def set_value_type(self, value_type, system='', direction=''):
        assert value_type in (Value, Values, Records)
        self.add_aspect(FAT_TYPE, value_type, system=system, direction=direction)
        return self

    def add_calculator(self, calculator, system='', direction=''):
        return self.add_aspect(FAT_CAL, calculator, system=system, direction=direction)

    def add_validator(self, validator, system='', direction=''):
        return self.add_aspect(FAT_CHK, validator, system=system, direction=direction)

    def add_converter(self, converter, system='', direction=''):
        return self.add_aspect(FAT_CON, converter, system=system, direction=direction)

    def add_filter(self, filter_func, system='', direction=''):
        return self.add_aspect(FAT_FLT, filter_func, system=system, direction=direction)

    def set_rec(self, rec, system='', direction=''):
        self.set_aspect(rec, FAT_REC, system=system, direction=direction)

    def string_to_records(self, rec_sep, fld_names, fld_sep, system='', direction=''):
        str_val = self.value(system=system, direction=direction)
        recs = Records()
        for idx, str_rec in enumerate(str_val.split(rec_sep)):
            rec = Record()
            for fld_idx, fld_val in enumerate(str_rec.split(fld_sep)):
                aspects = dict(FAT_NAME=fld_names[fld_idx], FAT_VAL=fld_val)
                fld = Field(**aspects)
                rec.add_field(fld)
            recs.append(rec)
        return recs

    def current_system_val(self, name=''):
        rec = self.rec
        if name == '':
            field = self
        else:
            field = rec[name]
        return field.val(system=rec.current_system or '', direction=rec.current_direction or '')

    csv = current_system_val

    def in_current_actions(self, *actions):
        return self.rec.current_action in actions

    ica = in_current_actions


class Record:
    def __init__(self, fields=None, current_system=None, current_direction=None, current_action=None):
        self._fields = OrderedDict()
        self._current_system = self._current_direction = self._current_action = ''
        self.add_fields(fields)
        self.set_current_env(system=current_system, direction=current_direction, action=current_action)

    def __iter__(self):
        return iter(self._fields)

    def __getitem__(self, item):
        return self._fields[item]

    @property
    def fields(self):
        return self._fields

    @property
    def current_system(self):
        return self._current_system

    @property
    def current_direction(self):
        return self._current_direction

    @property
    def current_action(self):
        return self._current_action

    def add_field(self, field, name=''):
        ori_name = name
        assert isinstance(field, Field), \
            "add_field({}, {}): field has to be of type Field (not {})".format(field, name, type(field))
        if not name:
            name = field.name
            if not name:
                name = DUMMY_FIELD_NAME + str(len(self._fields) + 1)
        field.name = name
        assert name not in self._fields, \
            "add_field({}, {}): field name {} already exists in Record".format(field, ori_name, name)
        self._fields[name] = field

    def add_fields(self, fields):
        for name, field in fields.items():
            self.add_field(field)

    def set_current_env(self, system='', direction='', action=''):
        if system:
            self._current_system = system
        if direction:
            self._current_direction = direction
        if action:
            self._current_action = action
        for field in self.fields.values():
            field.set_rec(self, system=system, direction=direction)

    def field_count(self):
        return len(self._fields)

    def pull(self, system=''):
        for field in self.fields.values():
            field.pull(system=system)

    def push(self, system=''):
        for field in self.fields.values():
            field.push(system=system)

    def copy(self, *keys, to_rec=None, filter_fields=False, link_fields=False, link_values=False,
             system='', direction=''):
        if to_rec is None:
            to_rec = Record(current_system=system, current_direction=direction)
        for name, field in self._fields.items():
            keys += (name, )
            if filter_fields:
                filter_field_validator = field.aspect_value(FAT_FLT, system=system, direction=direction)
                if filter_field_validator and not filter_field_validator(field):
                    continue
            val = field.value(system=system, direction=direction)
            if isinstance(val, Records):
                for idx, rec in enumerate(val):
                    field.set_idx(idx, system=system, direction=direction)
                    rec.clone_fields(*(keys + (idx, )), to_rec=to_rec, filter_fields=filter_fields,
                                     link_values=link_values, system=system, direction=direction)
            else:
                assert not link_fields or not link_values, "copy(): there can be only one link mode (2 given)"
                if not link_fields:
                    field = Field(**field.aspects)
                    if not link_values:
                        if isinstance(val, Values):
                            val = Values((Value(v) for v in val))
                        field.set_value(type(val)(val))
                to_rec.add_field(field, name=field.full_name(keys))

        return to_rec

    def sql_select(self, system, direction=''):
        col_expr = list()
        for field in self.fields.values():
            expr = field.aspect_value(FAT_CAL, system=system, direction=direction) or ""
            if expr:
                expr += " AS "
            col_expr.append(expr + field.aspect_value(FAT_NAME, system=system, direction=direction))
        return ", ".join(col_expr)

    def xml_build(self, system):
        pass


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
