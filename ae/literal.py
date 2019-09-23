"""
string literal type detection and evaluation
============================================

Value literals entered e.g. by the users of your application or which are stored in a
:ref:`configuration file <config-files>` representing a value that can be dynamically
detected and evaluated at application run-time.

The :class:`Literal` class provided by this module allows your application to support
the handling of any literals that can be converted via the python functions :func:`eval`
or :func:`exec` (respective :func:`ae.core.exec_with_return`) into a value.

A value literal can be passed either on instantiation through the :paramref:`~Literal.literal_or_value` argument::

    literal_1 = Literal(literal_or_value='datetime.datetime.now()')

or alternatively you could also set the literal string directly via the :attr:`~Literal.value` setter::

    literal_2 = Literal()
    literal_2.value = 'datetime.date.today()'

In all cases as soon as you request the literal value via the :attr:`~Literal.value`
getter the representing/underlying value will be detected an returned::

   literal_value: datetime.date = literal_2.value

For to restrict a value literal to a certain/fixed type you can specify it on instantiation within
the :paramref:`~Literal.value_type` argument::

    int_literal = Literal(value_type=int)
    str_literal = Literal(value_type=str)
    date_literal = Literal(value_type=datetime.date)
    list_literal = Literal(value_type=list)
    dict_literal = Literal(value_type=dict)

The supported formats of a value literal are document at the :attr:`~Literal.value` property.
"""
import datetime
from typing import Any, Optional, Tuple, Type

from ae.core import DATE_TIME_ISO, DATE_ISO, DEF_ENCODE_ERRORS, try_call, try_eval, try_exec


class Literal:
    """ literal representing a value used for example as configuration option. """

    def __init__(self, name: str = 'LiT', literal_or_value: Optional[Any] = None, value_type: Optional[Type] = None):
        """ create new Literal instance.

        :param name:                name of the literal (only used for debugging/error-message).
        :param literal_or_value:    initial literal (evaluable string expression) or value.
        :param value_type:          value type. cannot be changed later. will be determined latest in value getter.
        """
        super().__init__()
        self._name = name
        self._value = None
        self._type = None if value_type is type(None) else value_type
        if literal_or_value is not None:
            self.value = literal_or_value

    @property
    def value(self) -> Any:
        """ property representing the value of this Literal instance.

        :getter:    return the current value of this Literal instance.
        :setter:    to set a new value assign either a value literal string or directly
                    the representing/resulting value.

        If the string literal of this :class:`Literal` instance coincide with one of the following
        formats then this strings gets automatically evaluated and the evaluation result gets returned.
        These special formatted strings starting and ending with special characters like so:

        +-------------+------------+------------------------------+
        | starts with | ends with  | evaluation value type        |
        +=============+============+==============================+
        |     (       |     )      | tuple literal or expression  |
        +-------------+------------+------------------------------+
        |     [       |     ]      | list literal                 |
        +-------------+------------+------------------------------+
        |     {       |     }      | dict literal                 |
        +-------------+------------+------------------------------+
        |     '       |     '      | string literal               |
        +-------------+------------+------------------------------+
        |     \"       |     \"      | string literal               |
        +-------------+------------+------------------------------+
        |    '''      |    '''     | code block with return       |
        +-------------+------------+------------------------------+
        |    \"\"\"      |    \"\"\"     | code block with return       |
        +-------------+------------+------------------------------+

        """
        value = self._value
        try:
            if self._type != type(value):  # late value initialization
                if isinstance(value, bytes):  # convert bytes to string
                    value = value.decode('utf-8', DEF_ENCODE_ERRORS)
                if isinstance(value, str):
                    func, eval_expr = self._evaluable_literal(value)
                    self._value = func(eval_expr) if func else self._literal_value(value)
                elif self._type:
                    val = try_call(self._type, value, ignored_exceptions=(TypeError, ))     # ignore int/bool/...(None)
                    if val is not None:
                        self._value = val
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
        """ add new item to the list value of this Literal instance (lazy/late self.value getter call function pointer).

        :param item_value:  value of the item to be appended to the value of this Literal instance.
        :return:            the value (==list) of this Literal instance.

        This method gets e.g. used by the :class:`~.console_app.ConsoleApp` method
        :meth:`~.console_app.ConsoleApp.add_option` for to have a function pointer to this
        literal value with lazy/late execution of the value getter (value.append cannot be used in this case
        because the list could have be changed before it get finally read/used).
        (only works if the value type is :class:`list`).
        """
        self.value.append(item_value)
        return self.value

    def convert_value(self, value: Any) -> Any:
        """ set/change the literal/value of this :class:`Literal` instance and return the represented value.

        :param value:       the new value to be set.
        :return:            the final/converted value of this Literal instance.

        This method gets e.g. used by the :class:`~.console_app.ConsoleApp` method
        :meth:`~.console_app.ConsoleApp.add_option` for to have a function pointer
        for to let the ArgumentParser convert a configuration option literal into the
        represented value.
        """
        self.value = value
        return self.value  # using self.value instead of value to call getter for evaluation/type-correction

    @staticmethod
    def _evaluable_literal(literal: str) -> Tuple[Optional[callable], Optional[str]]:
        """ check evaluable format of literal and possibly return appropriate evaluation function and stripped literal.

        :param literal:     string to be checked if it can be evaluated and if it has to be stripped.
        :return:            tuple of - evaluation/execution function and stripped value (removed triple high-commas)
                            of expression/code-block - if literal has correct format - else (None, <empty string>).
        """
        func = None
        ret = ''
        if (literal.startswith("'''") and literal.endswith("'''")) \
                or (literal.startswith('"""') and literal.endswith('"""')):
            func = try_exec
            ret = literal[3:-3]                                             # code block
        elif (literal.startswith("[") and literal.endswith("]")) \
                or (literal.startswith("{") and literal.endswith("}")) \
                or (literal.startswith("(") and literal.endswith(")")) \
                or (literal.startswith("'") and literal.endswith("'")) \
                or (literal.startswith('"') and literal.endswith('"')):
            func = try_eval
            ret = literal                                                   # list/dict/tuple/str literal
        return func, ret

    def _literal_value(self, literal: str) -> Any:
        """ convert a simple string literal into its represented value.

        :param literal:     literal of a bool/datetime/date/... value.
        :return:            the bool/date/datetime/... value of the literal.
        """
        dt = datetime.datetime
        val = (bool(try_eval(literal)) if self._type == bool else
               (dt.strptime(literal, DATE_TIME_ISO) if self._type == dt and len(literal) > 10 else
                (dt.strptime(literal, DATE_ISO).date() if self._type in (datetime.date, dt) else
                 (self._type(literal) if self._type else
                  literal
                  ))))
        return val
