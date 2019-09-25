"""
string literal type detection and evaluation
============================================

Value literals entered e.g. by the users of your application or which are stored in a
:ref:`configuration file <config-files>` representing a value that can be dynamically
detected and evaluated at application run-time.

The :class:`Literal` class provided by this module allows your application to support
the handling of any literals that can be converted via the python functions :func:`eval`
or :func:`exec` (respective :func:`~ae.core.exec_with_return`) into a value.

A :ref:`evaluable literal <evaluable-literal-formats>` can be passed either
on instantiation through the first (the :paramref:`~Literal.literal_or_value`) argument
of the :class:`Literal` class::

    datetime_literal = Literal('(datetime.datetime.now())')

or alternatively you could also set the :ref:`evaluable literal string
<evaluable-literal-formats>` after the instantiation directly via the
:attr:`~Literal.value` property setter::

    date_literal = Literal()
    date_literal.value = '(datetime.date.today())'

The value literal of the last two examples have to be enclosed in round brackets
for to mark it as a :ref:`evaluable string literal <evaluable-literal-formats>`.
If you instead want to specify a date format literal string then you also have
to specify the value type like so:

    date_literal = Literal('2033-12-31', value_type=datetime.date)

As soon as you request the date value from the last three `date_literal` examples via
the :attr:`~Literal.value` property getter, the representing/underlying value will be
evaluated and returned::

   literal_value: datetime.date = date_literal.value

Also for to restrict a :class:`Literal` instance to a certain/fixed type you can specify
this type/class on instantiation within the :paramref:`~Literal.value_type` argument::

    int_literal = Literal(value_type=int)
    str_literal = Literal(value_type=str)
    date_literal = Literal(value_type=datetime.date)

The :attr:`~Literal.value` property getter of a :class:`Literal` instance with an applied
type restricting will try to convert the value literal to this type: string literals
will be evaluated and if the result has not the correct, then the getter tries the
value conversion with the constructor of the type class. If this fails too then it will
raise a ValueError exception::

    date_literal.value = "invalid-date-literal"
    date_value = date_literal.value             # raises ValueError

The supported formats for :ref:`evaluable string literals <evaluable-literal-formats>` are
documented at the :attr:`~Literal.value` property.
"""
import datetime
from typing import Any, Optional, Tuple, Type

from ae.core import DATE_TIME_ISO, DATE_ISO, DEF_ENCODE_ERRORS, try_call, try_eval, try_exec


class Literal:
    """ stores and represents any value, optionally converted from a string literal. """

    def __init__(self, literal_or_value: Optional[Any] = None, value_type: Optional[Type] = None, name: str = 'LiT'):
        """ create new Literal instance.

        :param literal_or_value:    initial string literal (evaluable string expression) or value of this instance.
        :param value_type:          type of the value of this instance (def=determined latest by/in the
                                    :attr:`~Literal.value` property getter).
        :param name:                name of the literal (only used for debugging/error-message).
        """
        super().__init__()
        self._name = name
        self._lit_or_val = None
        self._type = None if value_type is type(None) else value_type
        if literal_or_value is not None:
            self.value = literal_or_value

    @property
    def value(self) -> Any:
        """ property representing the value of this Literal instance.

        :getter:    return the current value of this Literal instance.
        :setter:    to set a new value assign either a value literal string or directly
                    the representing/resulting value.

        .. _evaluable-literal-formats:

        If the string literal of this :class:`Literal` instance coincide with one of the following
        evaluable formats then the value and the type of the value gets automatically recognized.
        An evaluable formatted literal strings has to start and end with the characters
        shown in the following table:

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

        *Other Supported Literals And Values*:

        String literals of a boolean type are evaluated as python expression. This way literal strings
        like 'True', 'False', '0' and '1' will be correctly converted into a boolean value.

        String literals of a :class:`~datetime.datetime` type have to use the date format specified by
        the :mod:`~ae.core` constant :data:`~ae.core.DATE_TIME_ISO`.

        String literals of a :class:`~datetime.date` type have to use the date format specified by
        the :mod:`~ae.core` constant :data:`~ae.core.DATE_ISO`.

        Values of any other type will be passed to the constructor of the type class for to
        convert them into their representing value.
       """
        new_val = self._lit_or_val
        msg = f"Literal {self._name} with value {new_val!r} "
        if self._type != type(new_val):     # first or new late real value conversion/initialization
            try:
                new_val = self._determine_value(new_val)
            except Exception as ex:
                raise ValueError(msg + f"throw exception: {ex}")

        self._set_type(new_val)
        if new_val is not None:
            if self._type and self._type != type(new_val):
                raise ValueError(msg + f"type mismatch: {self._type} != {type(new_val)}")
            else:
                self._lit_or_val = new_val

        return self._lit_or_val

    @value.setter
    def value(self, value: Any):
        if value is not None:
            if not self._type and not isinstance(value, (str, bytes)):
                self._type = type(value)
            self._lit_or_val = value        # late evaluation: real value will be checked/converted by getter

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
        return self.value  # using self.value instead of value to call getter for evaluation/type-

    def _determine_value(self, new_val: Any) -> Any:
        """ determine the represented value.

        :param new_val:     new value or string literal.
        :return:            determined/converted value or self._lit_or_val if value could not be recognized/converted.
        """
        if isinstance(new_val, bytes) and self._type != bytes:                          # if not restricted to bytes
            self._lit_or_val = new_val = new_val.decode('utf-8', DEF_ENCODE_ERRORS)     # then convert bytes to string

        if isinstance(new_val, str):
            func, eval_expr = self._evaluable_literal(new_val)
            if func:
                new_val = func(eval_expr)
                if new_val is None:
                    new_val = self._lit_or_val  # literal evaluation failed, then reset to try with type conversion
                else:
                    self._set_type(new_val)

        if self._type:
            new_type = type(new_val)
            if self._type != new_type and new_type == str:
                if self._type == bool:
                    new_val = bool(try_eval(new_val))
                elif self._type == datetime.datetime and len(new_val) > 10:
                    new_val = datetime.datetime.strptime(new_val, DATE_TIME_ISO)
                elif self._type in (datetime.date, datetime.datetime):
                    new_val = datetime.datetime.strptime(new_val, DATE_ISO)
                    if self._type == datetime.date:
                        new_val = new_val.date()
                if new_val is None:
                    new_val = self._lit_or_val  # literal evaluation failed, then reset to try with type conversion
                else:
                    self._set_type(new_val)

            if self._type != type(new_val):            # finally try type conversion with type constructor
                new_val = try_call(self._type, new_val, ignored_exceptions=(TypeError,))  # ignore int(None) exc
                if new_val is None:
                    new_val = self._lit_or_val

        return new_val

    @staticmethod
    def _evaluable_literal(literal: str) -> Tuple[Optional[callable], Optional[str]]:
        """ check evaluable format of literal and possibly return appropriate evaluation function and stripped literal.

        :param literal:     string to be checked if it is in the
                            :ref:`evaluable literal format <evaluable-literal-formats>` and if
                            it has to be stripped.
        :return:            tuple of evaluation/execution function and the (optionally stripped) literal
                            string (removed triple high-commas on expression/code-blocks) - if
                            :paramref:`~._evaluable_literal.literal` is in one of the supported
                            :ref:`evaluable literal formats <evaluable-literal-formats>` - else the tuple
                            (None, <empty string>).
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
            ret = literal                                                   # list/dict/tuple/str/... literal
        return func, ret

    def _set_type(self, value: Any):
        """ check if literal value type is already set and if not then determine from passed value.

        :param value:
        """
        if not self._type and value is not None:
            self._type = type(value)
