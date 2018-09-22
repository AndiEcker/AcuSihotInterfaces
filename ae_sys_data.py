"""
use and manage external systems, including their provided data fields and configuration settings
"""
import os
import struct
import keyword
from collections import OrderedDict


# dummy field name (not used as data field but as placeholder, e.g. for to put xml groups)
DUMMY_FIELD_NAME = '___'

# field aspect types/prefixes
FAT_NAME = 'key'
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


class Field:
    def __init__(self, **aspects):
        self._aspects = dict()
        self.list_value_index = self.lvi = None
        self.add_aspects(aspects)

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

    def aspect_value(self, aspect_type, inherited_aspect=False, system='', direction=''):
        if inherited_aspect:
            key = self.find_key(aspect_type, system=system, direction=direction)
        else:
            key = aspect_key(aspect_type, system=system, direction=direction)
        return self._aspects.get(key)

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

    def set_aspect(self, aspect_type, data, system='', direction=''):
        self._aspects[aspect_key(aspect_type, system=system, direction=direction)] = data
        return self

    def add_name(self, name, system='', direction=''):
        self.add_aspect(FAT_NAME, name, system=system, direction=direction)
        return self

    def del_name(self, system='', direction=''):
        self.del_aspect(FAT_NAME, system=system, direction=direction)
        return self

    def set_name(self, name, system='', direction=''):
        self.set_aspect(FAT_NAME, name, system=system, direction=direction)
        return self

    def add_value(self, value, system='', direction=''):
        self.add_aspect(FAT_VAL, value, system=system, direction=direction)
        return self

    def append_value(self, value, system='', direction=''):
        if aspect_key(FAT_VAL, system=system, direction=direction) in self._aspects:
            self.val(system=system, direction=direction).append(value)
        else:
            self.add_aspect(FAT_VAL, list((value, )), system=system, direction=direction)
        return self

    def del_value(self, system='', direction=''):
        self.del_aspect(FAT_VAL, system=system, direction=direction)
        return self

    def set_value(self, value, system='', direction=''):
        self.set_aspect(FAT_VAL, value, system=system, direction=direction)
        return self

    def add_calculator(self, calculator, system='', direction=''):
        return self.add_aspect(FAT_CAL, calculator, system=system, direction=direction)

    def add_validator(self, validator, system='', direction=''):
        return self.add_aspect(FAT_CHK, validator, system=system, direction=direction)

    def add_converter(self, converter, system='', direction=''):
        return self.add_aspect(FAT_CON, converter, system=system, direction=direction)

    def add_filter(self, filter_func, system='', direction=''):
        return self.add_aspect(FAT_FLT, filter_func, system=system, direction=direction)

    def val(self, system='', direction=''):
        value = self.aspect_value(FAT_VAL, system=system, direction=direction)
        if value is None:
            calculator = self.aspect_value(FAT_CAL, system=system, direction=direction)
            if calculator is not None:
                # noinspection PyCallingNonCallable
                value = calculator(self)
        if isinstance(value, Record):
            value = [f.val(system=system, direction=direction) for f in value.fields.values()]
        is_list = isinstance(value, (list, tuple))
        if not is_list:
            value = (value, )
        validator = self.aspect_value(FAT_CHK, system=system, direction=direction)
        converter = self.aspect_value(FAT_CON, system=system, direction=direction)
        new_val = list()
        for idx, list_val in enumerate(value):
            self.list_value_index = self.lvi = idx if is_list else -1
            if validator and not validator(list_val, self):
                list_val = None
            elif converter:
                list_val = converter(list_val, self)
            new_val.append(list_val)
        value = new_val

        return value if is_list else value[0]

    def get(self, system=''):
        return self.val(system=system, direction=FAD_FROM)

    def set(self, system=''):
        return self.val(system=system, direction=FAD_ONTO)

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
    def __init__(self, fields_aspects=None, field_aspect_types=(FAT_NAME, FAT_VAL, FAT_FLT,),
                 current_system=None, current_direction=None, current_action=None):
        self._fields = OrderedDict()
        if isinstance(fields_aspects, (tuple, list,)):
            self.add_fields_aspects(fields_aspects, field_aspect_types, new_fields=True,
                                    system=current_system, direction=current_direction)

        self._current_system = current_system
        self._current_direction = current_direction

        self._current_action = current_action

    def __iter__(self):
        return iter(self._fields)

    def add_field_aspects(self, aspects_data, aspect_types=(FAT_NAME, FAT_VAL, FAT_FLT,), new_field=True,
                          system='', direction=''):
        if system or direction:
            fats = [aspect_key(key, system=system, direction=direction) for key in aspect_types]
        else:
            fats = list(aspect_types)
        if FAT_NAME not in fats:
            fats.insert(0, FAT_NAME)
        key, *aspect_data = aspects_data
        assert len(aspect_data) <= len(fats)
        aspects = dict(zip(fats[:len(aspect_data)], aspect_data))
        aspects[FAT_REC] = self
        if new_field:
            self.add_field(Field(**aspects))
        else:
            self._fields[key].add_aspects(aspects)

    def add_fields_aspects(self, fields_aspects, aspect_types=(FAT_NAME, FAT_VAL, FAT_FLT,), new_fields=False,
                           system='', direction=''):
        for aspects_data in fields_aspects:
            self.add_field_aspects(aspects_data, aspect_types, new_field=new_fields, system=system, direction=direction)

    def add_field(self, field):
        assert isinstance(field, Field)
        name = field.name
        if name == DUMMY_FIELD_NAME:
            name += str(len(self._fields) + 1)
            field.name = name
        assert name not in self._fields
        self._fields[name] = field

    def add_fields(self, fields):
        for name, field in fields.items():
            self.add_field(field)

    def field_count(self):
        return len(self._fields)

    def copy(self):
        fields_aspects = OrderedDict()
        for field_name, field in self._fields.items():
            fields_aspects[field_name] = field.aspects
        return Record(fields_aspects=fields_aspects)

    def filtered_record(self, system='', direction=''):
        filtered_fields_aspects = dict()
        for field in self._fields.values():
            filter_field_validator = field.aspect_value(FAT_FLT, system=system, direction=direction)
            hide = False if filter_field_validator is None else filter_field_validator(field)
            if not hide:
                filtered_fields_aspects[field.name] = field.aspects
        rec = Record(fields_aspects=filtered_fields_aspects,
                     current_system=system or self.current_system,
                     current_direction=direction or self.current_direction)
        for field in filtered_fields_aspects:
            field.rec = rec
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

    @property
    def fields(self):
        return self._fields

    @property
    def current_system(self):
        return self._current_system

    @current_system.setter
    def current_system(self, cs):
        self._current_system = cs

    @property
    def current_direction(self):
        return self._current_direction

    @current_direction.setter
    def current_direction(self, cd):
        self._current_direction = cd

    @property
    def current_action(self):
        return self._current_action

    @current_action.setter
    def current_action(self, ca):
        self._current_action = ca


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
