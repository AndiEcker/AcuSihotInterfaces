"""
manage data for to interface from and onto other/external systems
"""
import os
import struct
import keyword
from collections import OrderedDict
from typing import Optional


# dummy field name (not used as data field but as placeholder, e.g. for to put xml groups)
DUMMY_FIELD_NAME = '___'

# field name special characters for to identify list indexes and sub-Records
FN_LIST_IDX_MARKER = '#'
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
FAT_SQE = 'sce'

ALL_FATS = (FAT_NAME, FAT_VAL, FAT_TYPE, FAT_REC, FAT_IDX, FAT_CAL, FAT_CHK, FAT_CON, FAT_FLT, FAT_SQE)

# field aspect directions
FAD_FROM = 'From'
FAD_ONTO = 'Onto'

# Record.copy() field/value linking modes
REC_COPY_LINK_NONE = ''
REC_COPY_LINK_FIELD = 'Field'
REC_COPY_LINK_VALUE = 'Value'

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


class Value(list):
    def __init__(self, seq=('',)):
        super().__init__(seq)

    def value(self, *_, **__):
        return self[-1]

    def clear(self):
        super().clear()
        self[-1] = ''


class Values(list):
    pass


class Record:
    def __init__(self, fields=None, system=None, direction=None, action=None):
        self._fields = OrderedDict()
        self.system = self.direction = self.action = ''
        self.add_fields(fields)
        self.set_env(system=system, direction=direction, action=action)

    def __iter__(self):
        return iter(self._fields)

    def __getitem__(self, item):
        return self._fields[item]

    @property
    def fields(self):
        return self._fields

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
            self.add_field(field)

    def set_env(self, system='', direction='', action=''):
        if system:
            self.system = system
        if direction:
            self.direction = direction
        if action:
            self.action = action
        for field in self._fields.values():
            field.set_rec(self, system=system, direction=direction)

    def field_count(self):
        return len(self._fields)

    def pull(self, system=''):
        assert self.system == '' and self.direction == '', "{}{}.pull() not allowed".format(self.direction, self.system)
        for field in self._fields.values():
            field.pull(system=system)

    def push(self, system=''):
        assert self.system == '' and self.direction == '', "{}{}.push() not allowed".format(self.direction, self.system)
        for field in self._fields.values():
            field.push(system=system)

    def names(self, system='', direction=''):
        names = list()
        for field in self._fields.values():
            name = field.aspect_value(FAT_NAME, system=system, direction=direction)
            if name:
                names.append(name)
        return names

    def set_values(self, values, inherited_aspect=False, system='', direction=''):
        for field in self._fields.values():
            key = field.aspect_exists(FAT_NAME, inherited_aspect=inherited_aspect, system=system, direction=direction)
            if key and field.aspects[key] in values:
                field.set_value(values[field.aspects[key]], system=system, direction=direction)

    def clear_values(self, system='', direction=''):
        for field in self._fields.values():
            value = field.aspect_value(FAT_VAL, system=system, direction=direction)
            if value:
                value.clear()

    def copy(self, *keys, to_rec=None, filter_fields=False, link_mode=REC_COPY_LINK_NONE, fields_patches=None,
             system='', direction=''):
        """
        copy the fields of this record
        :param keys:            path of field names and/or indexes.
        :param to_rec:          destination record; pass None to create new Record instance.
        :param filter_fields:   pass True to filter fields by FAT_FLT aspect callable.
        :param link_mode:       pass REC_COPY_LINK_VALUE/REC_COPY_LINK_FIELD for to use same Value/Field instance.
        :param fields_patches:  restrict fields to the keys in this dict and use dict values as override aspects.
        :param system:          system id.
        :param direction:       direction id.
        :return:                new/extended record instance.
        """
        if to_rec is None:
            to_rec = Record(system=system, direction=direction)
        elif not fields_patches:
            assert to_rec is not self, "copy() cannot copy to self without patches"

        for name, field in self._fields.items():
            keys += (name, )
            full_name = field.full_name(keys)
            patches = None
            if fields_patches:
                if full_name in fields_patches:
                    patches = fields_patches[full_name]
                elif name in fields_patches:
                    patches = fields_patches[name]
                else:
                    continue

            if filter_fields:
                filter_field_validator = field.aspect_value(FAT_FLT, system=system, direction=direction)
                if filter_field_validator and not filter_field_validator(field):
                    continue

            val = field.value(system=system, direction=direction)
            if isinstance(val, Records):
                for idx, rec in enumerate(val):
                    field.set_idx(idx, system=system, direction=direction)
                    rec.copy(*(keys + (idx, )), to_rec=to_rec, filter_fields=filter_fields,
                             link_mode=link_mode, fields_patches=fields_patches, system=system, direction=direction)
            else:
                if link_mode != REC_COPY_LINK_FIELD:
                    field = Field(**field.aspects)
                    if link_mode != REC_COPY_LINK_VALUE:
                        if isinstance(val, Values):
                            val = Values((Value(v) for v in val))
                        field.set_value(type(val)(val))
                if patches:
                    field.set_aspects(**patches)
                to_rec.add_field(field, name=full_name)

        return to_rec

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


class Records(list):
    pass


class Field:
    def __init__(self, **aspects):
        self._aspects = dict()
        self.add_aspects(**aspects)
        if FAT_VAL not in self._aspects:
            self._aspects[FAT_VAL] = Value()
        if FAT_NAME not in self._aspects:
            self._aspects[FAT_NAME] = DUMMY_FIELD_NAME

    def __getitem__(self, key_or_keys):
        return self.val(key_or_keys)

    @property
    def aspects(self):
        return self._aspects

    def find_aspect_key(self, aspect_type, system='', direction=''):
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
            key = self.find_aspect_key(aspect_type, system=system, direction=direction)
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

    def set_aspect(self, aspect_value, type_or_key, system='', direction='', add=False):
        key = aspect_key(type_or_key, system=system, direction=direction)
        if add:
            assert key not in self._aspects, "set_aspect({}, {}, {}, {}, {}): key already exists in aspects ({})"\
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

    @property
    def name(self):
        return self._aspects.get(FAT_NAME)

    @name.setter
    def name(self, name):
        self._aspects[FAT_NAME] = name

    def del_name(self, system='', direction=''):
        self.del_aspect(FAT_NAME, system=system, direction=direction)
        return self

    def set_name(self, name, system='', direction='', add=False):
        self.set_aspect(name, FAT_NAME, system=system, direction=direction, add=add)
        return self

    def full_name(self, *keys, base_name=''):
        key_names = ((FN_LIST_IDX_MARKER if isinstance(k, int) else FN_SUB_REC_MARKER) + k for k in keys)
        return (base_name or self.name) + "".join(key_names)

    def rec(self, system='', direction='') -> Optional[Record]:
        return self.aspect_value(FAT_REC, inherited_aspect=True, system=system, direction=direction)

    def set_rec(self, rec, system='', direction=''):
        self.set_aspect(rec, FAT_REC, system=system, direction=direction)

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
                calculator = self._aspects[key]
                assert callable(calculator)
                value = calculator(self)
        return value

    def set_value(self, value, system='', direction='', add=False):
        ori_val = value
        val_typ = self.aspect_value(FAT_TYPE, system=system, direction=direction)
        if not isinstance(value, (Value, Values, Records)):
            cur_val = self.value(system=system, direction=direction)
            if isinstance(cur_val, Value):
                cur_val[-1] = value
                value = cur_val
            elif not isinstance(value, (tuple, list)):
                value = Value((value, ))
            elif value:
                value = Records(value) if val_typ == Records or isinstance(value[0], Record) else Values(value)
            else:
                value = Values()

        key = aspect_key(FAT_VAL, system=system, direction=direction)

        # noinspection PyTypeChecker
        assert isinstance(value, (Value, Values, Records)) and (not val_typ or isinstance(value, val_typ)), \
            "set_value({}, {}, {}, {}): value '{}' has wrong type {} (declared as {})"\
            .format(ori_val, system, direction, add, value, type(value), val_typ)
        if add:
            assert key not in self._aspects, "set_value({}, {}, {}, {}): value key {} already exists in aspects ({})"\
                .format(ori_val, system, direction, add, key, self._aspects)

        self._aspects[key] = value

        return self

    def val(self, *keys, system='', direction=''):
        val = self.value(system=system, direction=direction)
        if val is None:
            asp_val_key = self.find_aspect_key(FAT_VAL, system=system, direction=direction) or ''
            asp_cal_key = self.find_aspect_key(FAT_CAL, system=system, direction=direction) or ''
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

    def del_value(self, system='', direction=''):
        self.del_aspect(FAT_VAL, system=system, direction=direction)
        return self

    def value_type(self, system='', direction=''):
        return self.aspect_value(FAT_TYPE, system=system, direction=direction) or Value

    def set_value_type(self, value_type, system='', direction='', add=False):
        assert value_type in (Value, Values, Records)
        self.set_aspect(FAT_TYPE, value_type, system=system, direction=direction, add=add)
        return self

    def set_calculator(self, calculator, system='', direction='', add=False):
        return self.set_aspect(FAT_CAL, calculator, system=system, direction=direction, add=add)

    def set_validator(self, validator, system='', direction='', add=False):
        return self.set_aspect(FAT_CHK, validator, system=system, direction=direction, add=add)

    def set_converter(self, converter, system='', direction='', add=False):
        return self.set_aspect(FAT_CON, converter, system=system, direction=direction, add=add)

    def set_filter(self, filter_func, system='', direction='', add=False):
        return self.set_aspect(FAT_FLT, filter_func, system=system, direction=direction, add=add)

    def set_sql_expression(self, sql_expression, system='', direction='', add=False):
        return self.set_aspect(FAT_SQE, sql_expression, system=system, direction=direction, add=add)

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
