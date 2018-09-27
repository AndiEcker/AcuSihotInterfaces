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
    assert key.isidentifier() and not keyword.iskeyword()
    return key


class Value(list):
    def __init__(self, seq=('',)):
        super().__init__(seq)

    def value(self, *_):
        return self[-1]


class Values(list):
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
        if type(value) not in (Value, Values, list):
            value = Value((value, ))
        # self.set_aspect(value, FAT_VAL, system=system, direction=direction)
        self._aspects[aspect_key(FAT_VAL, system=system, direction=direction)] = value
        return self

    def convert_and_validate(self, value, system='', direction=''):
        converter = self.aspect_value(FAT_CON, system=system, direction=direction)
        if converter:
            value = converter(self, value)

        validator = self.aspect_value(FAT_CHK, system=system, direction=direction)
        if validator and not validator(self, value):
            return None

        return value

    def val(self, *keys, system='', direction=''):
        val = self.value(system=system, direction=direction)
        if val is None:
            asp_key = self.find_key(FAT_VAL, system=system, direction=direction)
            if asp_key is None:
                return None
            val = self._aspects[asp_key]

        key = next(keys)
        val_type = type(val)
        while val_type in (Record, Values):
            if type(key) in (int, str) and key in val:
                k = key
                key = next(keys)
            elif val_type == Record:
                k = next(val.fields.keys())
            elif val_type == Values:
                k = -1
                self.set_idx(k, system=system, direction=direction)
            else:
                break
            val = val[k].value(system=system, direction=direction)
            val_type = type(val)

        while key:
            val = val[key]
            key = next(keys)

        return val

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

    def set_rec(self, rec, system='', direction=''):
        self.set_aspect(rec, FAT_REC, system=system, direction=direction)

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
        assert key not in self._aspects
        self._aspects[key] = aspect_data
        return self

    def del_aspect(self, aspect_type, system='', direction=''):
        return self._aspects.pop(aspect_key(aspect_type, system=system, direction=direction))

    def set_aspect(self, aspect_value, aspect_type, system='', direction=''):
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

    def add_calculator(self, calculator, system='', direction=''):
        return self.add_aspect(FAT_CAL, calculator, system=system, direction=direction)

    def add_validator(self, validator, system='', direction=''):
        return self.add_aspect(FAT_CHK, validator, system=system, direction=direction)

    def add_converter(self, converter, system='', direction=''):
        return self.add_aspect(FAT_CON, converter, system=system, direction=direction)

    def add_filter(self, filter_func, system='', direction=''):
        return self.add_aspect(FAT_FLT, filter_func, system=system, direction=direction)

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
        assert isinstance(field, Field)
        if not name:
            name = field.name
            if not name:
                name = DUMMY_FIELD_NAME + str(len(self._fields) + 1)
        field.name = name
        assert name not in self._fields
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

    def filtered_record(self, system='', direction=''):
        filtered_fields = dict()
        for field in self._fields.values():
            filter_field_validator = field.aspect_value(FAT_FLT, system=system, direction=direction)
            hide = False if filter_field_validator is None else filter_field_validator(field)
            if not hide:
                filtered_fields[field.name] = field.aspects
        rec = Record(fields=filtered_fields,
                     current_system=system or self.current_system,
                     current_direction=direction or self.current_direction)
        return rec

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
