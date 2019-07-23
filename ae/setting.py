import datetime

from ae import DATE_TIME_ISO, DATE_ISO


class Setting:
    def __init__(self, name='Unnamed', value=None, value_type=None):
        """ create new Setting instance

        :param name: optional name of the setting (only used for debugging/error-message).
        :param value: optional initial value or evaluable string expression.
        :param value_type: optional value type. cannot be changed later. will be determined latest in value getter.
        """
        super().__init__()
        self._name = name
        self._value = None
        self._type = None if value_type is type(None) else value_type
        if value is not None:
            self.value = value

    @property
    def value(self):
        value = self._value
        try:
            if self._type != type(value):
                if isinstance(value, bytes):    # convert bytes to string?
                    value = str(value, encoding='utf-8')  # value.decode('utf-8', 'replace') -> shows warning in PyCharm
                if isinstance(value, str):
                    eval_expr = self._eval_str(value)
                    self._value = eval(eval_expr) if eval_expr else \
                        (bool(eval(value)) if self._type == bool else
                         (datetime.datetime.strptime(value, DATE_TIME_ISO)
                          if self._type == datetime.datetime and len(value) > 10 else
                          (datetime.datetime.strptime(value, DATE_ISO).date()
                           if self._type in (datetime.date, datetime.datetime) else
                           (self._type(value) if self._type else value))))
                elif self._type:
                    try:  # catch type conversion errors, e.g. for datetime.date(None) while bool(None) works (->False)
                        self._value = self._type(value)
                    except TypeError:
                        pass
            # the value type gets only once initialized, but after _eval_str() for to auto-detect complex types
            if not self._type and self._value is not None:
                self._type = type(self._value)
        except Exception as ex:
            raise ValueError("Setting.value exception '{}' on evaluating the setting {} with value: {!r}"
                             .format(ex, self._name, value))
        return self._value

    @value.setter
    def value(self, value):
        if not self._type and not isinstance(value, str) and value is not None:
            self._type = type(value)
        self._value = value

    def append_value(self, value):
        self.value.append(value)
        return self.value

    def convert_value(self, value):
        self.value = value
        return self.value       # using self.value instead of value to call getter for evaluation/type-correction

    @staticmethod
    def _eval_str(str_val):
        """ check str_val if needs to be evaluated and return non-empty-and-stripped-eval-string if yes else '' """
        if (str_val.startswith("'''") and str_val.endswith("'''")) \
                or (str_val.startswith('"""') and str_val.endswith('"""')):
            ret = str_val[3:-3]
        elif (str_val.startswith("[") and str_val.endswith("]")) \
                or (str_val.startswith("{") and str_val.endswith("}")) \
                or (str_val.startswith("(") and str_val.endswith(")")) \
                or (str_val.startswith("'") and str_val.endswith("'")) \
                or (str_val.startswith('"') and str_val.endswith('"')):
            ret = str_val
        else:
            ret = ''
        return ret
