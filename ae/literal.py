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
will be evaluated and if the result has not the correct type, then the getter tries the
value conversion with the constructor of the type class. If this fails too then it will
raise a ValueError exception::

    date_literal.value = "invalid-date-literal"
    date_value = date_literal.value             # raises ValueError

The supported literal formats for :ref:`evaluable string literals <evaluable-literal-formats>`
are documented at the :attr:`~Literal.value` property.
"""
import datetime
from typing import Any, Optional, Tuple, Type

from ae.core import DEF_ENCODE_ERRORS, parse_date, try_call, try_eval, try_exec


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
        self._literal_or_value = None
        self._type = None if value_type is type(None) else value_type
        if literal_or_value is not None:
            self.value = literal_or_value

    @property
    def value(self) -> Any:
        """ property representing the value of this Literal instance.

        :getter:    return the current value of this Literal instance.
        :setter:    set a new value; assign either a value literal string or directly
                    the represented/resulting value.

        .. _evaluable-literal-formats:

        If the string literal of this :class:`Literal` instance coincide with one of the following
        evaluable formats then the value and the type of the value gets automatically recognized.
        An evaluable formatted literal strings has to start and end with one of the character pairs
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

        String literals with type restriction to a boolean type are evaluated as python expression.
        This way literal strings like 'True', 'False', '0' and '1' will be correctly recognized
        and converted into a boolean value.

        Literal strings that representing a date value (with type restriction to either
        :class:`datetime.datetime` or :class:`datetime.date`) will be converted with the
        :func:`~ae.core.parse_date` function and should be formatted in one of the
        standard date formats (defined by the :mod:`~ae.core` constants
        :data:`~ae.core.DATE_TIME_ISO` and :data:`~ae.core.DATE_ISO`).

        Literals and values that are not in one of the above formats will finally be passed to
        the constructor of the restricted type class for to try to convert them into their
        representing value.
       """
        check_val = self._literal_or_value
        msg = f"Literal {self._name} with value {check_val!r} "
        if self.type_mismatching_with(check_val):     # first or new late real value conversion/initialization
            try:
                check_val = self._determine_value(check_val)
            except Exception as ex:
                raise ValueError(msg + f"throw exception: {ex}")

        self._chk_val_reset_else_set_type(check_val)
        if check_val is not None:
            if self._type and self.type_mismatching_with(check_val):
                raise ValueError(msg + f"type mismatch: {self._type} != {type(check_val)}")
            else:
                self._literal_or_value = check_val

        return self._literal_or_value

    @value.setter
    def value(self, lit_or_val: Any):
        if lit_or_val is not None:
            if isinstance(lit_or_val, bytes) and self._type != bytes:       # if not restricted to bytes
                lit_or_val = lit_or_val.decode('utf-8', DEF_ENCODE_ERRORS)  # ..then convert bytes to string
            self._literal_or_value = lit_or_val     # late evaluation: real value will be checked/converted by getter
            if not self._type and not isinstance(lit_or_val, str):          # set type if unset and no eval
                self._type = type(lit_or_val)

    def append_value(self, item_value: Any) -> Any:
        """ add new item to the list value of this Literal instance (lazy/late self.value getter call function pointer).

        :param item_value:  value of the item to be appended to the value of this Literal instance.
        :return:            the value (==list) of this Literal instance.

        This method gets e.g. used by the :class:`~.console.ConsoleApp` method
        :meth:`~.console.ConsoleApp.add_option` for to have a function pointer to this
        literal value with lazy/late execution of the value getter (value.append cannot be used in this case
        because the list could have be changed before it get finally read/used).
        (only works if the value type is :class:`list`).
        """
        self.value.append(item_value)
        return self.value

    def convert_value(self, lit_or_val: Any) -> Any:
        """ set/change the literal/value of this :class:`Literal` instance and return the represented value.

        :param lit_or_val:  the new value to be set.
        :return:            the final/converted value of this Literal instance.

        This method gets e.g. used by the :class:`~.console.ConsoleApp` method
        :meth:`~.console.ConsoleApp.add_option` for to have a function pointer
        for to let the ArgumentParser convert a configuration option literal into the
        represented value.
        """
        self.value = lit_or_val
        return self.value  # using self.value instead of value to call getter for evaluation/type-

    def type_mismatching_with(self, value: Any) -> bool:
        """ check if this literal instance would reject the passed value because of type mismatch.

        :param value:       new literal value.
        :return:            True if the passed value would have an type mismatch or if literal type is still not set,
                            else False.
        """
        return self._type != type(value)

    def _determine_value(self, lit_or_val: Any) -> Any:
        """ check passed value if it is still a literal determine the represented value.

        :param lit_or_val:  new literal value or the representing string literal.
        :return:            determined/converted value or self._lit_or_val if value could not be recognized/converted.
        """
        if isinstance(lit_or_val, str):
            func, eval_expr = self._evaluable_literal(lit_or_val)
            if func:
                lit_or_val = self._chk_val_reset_else_set_type(func(eval_expr))

        if self._type:
            if self.type_mismatching_with(lit_or_val) and isinstance(lit_or_val, str):
                if self._type == bool:
                    lit_or_val = bool(try_eval(lit_or_val))
                elif self._type in (datetime.date, datetime.datetime):
                    lit_or_val = parse_date(lit_or_val, ret_date=self._type == datetime.date)
                lit_or_val = self._chk_val_reset_else_set_type(lit_or_val)

            if self.type_mismatching_with(lit_or_val):          # finally try type conversion with type constructor
                lit_or_val = self._chk_val_reset_else_set_type(
                    try_call(self._type, lit_or_val, ignored_exceptions=(TypeError,)))  # ignore int(None) exception

        return lit_or_val

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

    def _chk_val_reset_else_set_type(self, value: Any):
        """ reset and return passed value if is None, else determine value type and set type (if not already set).

        :param value:       just converted new literal value for to be checked and if ok used to set an unset type.
        """
        if value is None:
            value = self._literal_or_value  # literal evaluation failed, then reset to try with type conversion
        elif not self._type and value is not None:
            self._type = type(value)
        return value
