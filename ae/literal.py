"""
typed config options
===========================

"""
import datetime
from typing import Any, Optional, Type

from ae.core import DATE_TIME_ISO, DATE_ISO


class Literal:
    """ literal representing a value used e.g. as configuration option. """
    def __init__(self, name: str = 'Unnamed', literal: Optional[Any] = None, value_type: Optional[Type] = None):
        """ create new Literal instance

        :param name:        name of the literal (only used for debugging/error-message).
        :param literal:     initial literal (evaluable string expression) or value.
        :param value_type:  value type. cannot be changed later. will be determined latest in value getter.
        """
        super().__init__()
        self._name = name
        self._value = None
        self._type = None if value_type is type(None) else value_type
        if literal is not None:
            self.value = literal

    @property
    def value(self) -> Any:
        """ property representing the value of this Literal instance.

        :return:    the current value of this Literal instance.

        If the getter of this property is recognizing the current value as a special formatted strings
        then this strings gets automatically evaluated and the evaluation result gets returned. These
        special formatted strings starting and ending with special characters like so:

        +-------------+------------+-------------------------+
        | starts with | ends with  | evaluation value type   |
        +=============+============+=========================+
        |     (       |     )      | tuple literal           |
        +-------------+------------+-------------------------+
        |     [       |     ]      | list literal            |
        +-------------+------------+-------------------------+
        |     {       |     }      | dict literal            |
        +-------------+------------+-------------------------+
        |     '       |     '      | string literal          |
        +-------------+------------+-------------------------+
        |     \"       |     \"      | string literal          |
        +-------------+------------+-------------------------+
        |    '''      |    '''     | code block              |
        +-------------+------------+-------------------------+
        |    \"\"\"      |    \"\"\"     | code block              |
        +-------------+------------+-------------------------+

        """
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
            raise ValueError("Literal.value exception '{}' on evaluating the literal {} with value: {!r}"
                             .format(ex, self._name, value))
        return self._value

    @value.setter
    def value(self, value: Any):
        if not self._type and not isinstance(value, str) and value is not None:
            self._type = type(value)
        self._value = value

    def append_value(self, item_value: Any) -> Any:
        """ add new item to the list value of this Literal instance (only works if the value is of type list).

        :param item_value:  value of the item to be appended to the value of this Literal instance.
        :return:            the value (==list) of this Literal instance.
        """
        self.value.append(item_value)
        return self.value

    def convert_value(self, value: Any) -> Any:
        """ set/change the value (and possibly also the type) of this Literal instance

        :param value:       the new value to be set.
        :return:            the final/converted value of this Literal instance.
        """
        self.value = value
        return self.value       # using self.value instead of value to call getter for evaluation/type-correction

    @staticmethod
    def _eval_str(str_val: str) -> str:
        """ check `str_val` if needs to be evaluated and return non-empty-and-stripped-eval-string if yes else ''

        :param str_val:     string to be checked if it can be evaluated and if it need to be stripped.
        :return:            stripped value (removed triple high-commas) of code block or list/dict/tuple/str literal
                            if need to be evaluated, else empty string.
        """
        if (str_val.startswith("'''") and str_val.endswith("'''")) \
                or (str_val.startswith('"""') and str_val.endswith('"""')):
            ret = str_val[3:-3]     # code block
        elif (str_val.startswith("[") and str_val.endswith("]")) \
                or (str_val.startswith("{") and str_val.endswith("}")) \
                or (str_val.startswith("(") and str_val.endswith(")")) \
                or (str_val.startswith("'") and str_val.endswith("'")) \
                or (str_val.startswith('"') and str_val.endswith('"')):
            ret = str_val           # list/dict/tuple/str literal
        else:
            ret = ''
        return ret
