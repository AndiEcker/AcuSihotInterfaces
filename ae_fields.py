from collections import OrderedDict


# field aspect types/prefixes
FAT_COL_NAME = 'colName'
FAT_COL_VAL = 'colVal'
FAT_CAL_VAL = 'calVal'
FAT_CHK_VAL = 'chkVal'
FAT_CON_VAL = 'conVal'
FAT_COL_LIST = 'colLst'
# FAT_CAL_LIST = 'calLst'
FAT_REC = 'rec'
FAT_ROW = 'row'
FAT_FILTER = 'flt'

# field aspect directions
FAD_FROM = 'From'
FAD_ONTO = 'Onto'


class Field:
    def __init__(self, name, **aspects):
        assert name and isinstance(name, str)
        self.name = name
        self._aspects = dict()
        self.update_aspects(**aspects)

    def update_aspects(self, **aspects):
        self._aspects.update(aspects)
        return self

    def add_aspect(self, aspect_data, aspect_type, system='', direction=''):
        key = aspect_type + direction + system
        assert key not in self._aspects
        self._aspects[key] = aspect_data
        return self

    def add_column(self, value, system='', direction=''):
        return self.add_aspect(value, FAT_COL_VAL, system=system, direction=direction)

    def add_calculator(self, calculator, system='', direction=''):
        return self.add_aspect(calculator, FAT_CAL_VAL, system=system, direction=direction)

    def add_list(self, column_names, system='', direction=''):
        return self.add_aspect(column_names, FAT_COL_LIST, system=system, direction=direction)

    def add_validator(self, validator, system='', direction=''):
        return self.add_aspect(validator, FAT_CHK_VAL, system=system, direction=direction)

    def add_converter(self, converter, system='', direction=''):
        return self.add_aspect(converter, FAT_CON_VAL, system=system, direction=direction)

    def add_filter(self, filter, system='', direction=''):
        return self.add_aspect(filter, FAT_FILTER, system=system, direction=direction)

    def aspect_key(self, aspect_type, system='', direction=''):
        keys = list()
        if direction:
            keys.append(aspect_type + direction + system)
        if system:
            keys.append(aspect_type + system)
        keys.append(aspect_type)

        for key in keys:
            if key in self._aspects:
                return key

        return None

    def aspect_value(self, aspect_type, system='', direction='', cache_value=True):
        key = self.aspect_key(aspect_type, system=system, direction=direction)
        value = self._aspects.get(key)
        validator = self.aspect_value(FAT_CHK_VAL, system=system, direction=direction)
        converter = self.aspect_value(FAT_CON_VAL, system=system, direction=direction)
        if isinstance(value, list):
            new_val = list()
            for list_val in value:
                if validator and not validator(list_val, self):
                    continue
                if converter:
                    list_val = converter(list_val, self)
                new_val.append(list_val)
            value = new_val
        else:
            if not validator or validator(value, self):
                if converter:
                    value = converter(value, self)

        if cache_value and (not direction or direction == FAD_FROM):
            self.add_aspect(value, FAT_COL_VAL)

        return value

    def val(self, system='', direction=''):
        value = self.aspect_value(FAT_COL_LIST, system=system, direction=direction)
        if value is None:
            value = self.aspect_value(FAT_COL_VAL, system=system, direction=direction)
            if value is None:
                calculator = self.aspect_value(FAT_CAL_VAL, system=system, direction=direction)
                if calculator is not None:
                    # noinspection PyCallingNonCallable
                    value = calculator(self)
        return value

    def get(self, system=''):
        return self.val(system=system, direction=FAD_ONTO)

    def set(self, system=''):
        return self.val(system=system, direction=FAD_FROM)

    @property
    def rec(self):
        return self._aspects.get(FAT_REC)   # self.aspect_value(FAT_REC)

    @rec.setter
    def rec(self, new_rec):
        self._aspects[FAT_REC] = new_rec

    def row(self, system, direction=FAD_FROM):
        return self.aspect_value(FAT_ROW, system=system, direction=direction)

    def add_row(self, row_dict, system, direction=FAD_FROM):
        return self.add_aspect(row_dict, FAT_ROW, system=system, direction=direction)


class Record:
    def __init__(self, fields=None):
        self._fields = OrderedDict()
        if fields:
            self.set_fields(fields)

    def set_fields(self, fields):
        self._fields.update(fields)

    def add_field(self, field):
        assert isinstance(field, Field) and field.name not in self._fields
        self._fields[field.name] = field

    def add_fields(self, fields):
        for name, field in fields.items():
            self.add_field(field)

    def field_count(self):
        return len(self._fields)

    def filter_fields(self, system='', direction=''):
        filtered_fields = list()
        for field in self._fields:
            filter_field_validator = field.aspect_value(FAT_FILTER, system=system, direction=direction)
            if filter_field_validator is not None:
                hide = filter_field_validator(field)
                if not hide:
                    filtered_fields.append(field)
        rec = Record(filtered_fields)
        for field in filtered_fields:
            field.rec = rec
        return rec
