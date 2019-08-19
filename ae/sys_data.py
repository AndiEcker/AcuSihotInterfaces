""" manage data structures for to interface from and onto other/external systems.

Any kind of data structures - like lists, mappings and trees - can be specified by using a combination of the class
instances that are declared within this module:

* A list gets represented by a instance of one of the classes :class:`Records` or :class:`Values`. Each
  :class:`Records` instance is a collection of 0..n :class:`Record` instances. A :class:`Values` instance
  is a collection of 1..n :class:`_Field` instances.
* A mapping get represented by an instance of the class :class:`Record`, whereas each mapping item gets
  represented by an instance of the private class :class:`_Field`.
* A node of a tree structure can be represented by instances of the classes :class:`Records`, :class:`Values` or
  :class:`Record`.

The root of such a data structure can be defined by an instance of either :class:`Records` or :class:`Record`. All the
leafs of such a data structure are instances of the :class:`Value` class. The following diagram is showing
all the possible combinations (of a single system):

.. graphviz::

    digraph {
        node [shape=record]
        rec1 [label="{<rec1>Record (root) | { <A>A | <B>B | <C>C | <D>D } }"]
        "Records (root)" -> rec1 [arrowhead=crow style=tapered penwidth=3]
        rec1:A -> "Value (_Field A)" [minlen=3]
        rec1:B -> "Values"
        "Values" -> "Value (Values)" [minlen=2 arrowhead=crow style=tapered penwidth=3]
        rec2 [label="{<rec2>Record (sub-record) | { <CA>CA | <CB>CB | <CN>... } }"]
        rec1:C -> rec2
        rec2:CA -> "Value (_Field CA)" [minlen=2]
        rec3 [label="{<rec3>Record (sub-records-sub-record) | { <DA>DA | <DB>DB | <DN>... } }"]
        rec1:D -> "Records (sub-records)"
        "Records (sub-records)" -> rec3 [arrowhead=crow style=tapered penwidth=3]
        rec3:DA -> "Value (_Field DA)"
    }

Additionally each :class:`_Field` instance can hold for each system a separate value, which
gets represented by an instance of one of the 4 classes :class:`Records`, :class:`Record`,
:class:`Values` or :class:`Value`.
"""
import datetime
import keyword
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, TypeVar, Union

from ae_validation.validation import correct_email, correct_phone

ACTION_INSERT = 'INSERT'        #: insert action
ACTION_UPDATE = 'UPDATE'        #: update action
ACTION_UPSERT = 'UPSERT'        #: insert or update (if already exists) action
ACTION_DELETE = 'DELETE'        #: delete action
ACTION_SEARCH = 'SEARCH'        #: search action
ACTION_PARSE = 'PARSE'          #: parse action
ACTION_BUILD = 'BUILD'          #: build action
ACTION_PULL = 'PULL'            #: pull-from-system action
ACTION_PUSH = 'PUSH'            #: push-to-system action
ACTION_COMPARE = 'COMPARE'      #: compare action

# field aspect types/prefixes
FAT_IDX = 'idx'                 #: main/system field name within parent Record or list index within Records/Values
FAT_VAL = 'vle'                 #: main/system field value - storing one of the VALUE_TYPES instance
FAT_CLEAR_VAL = 'vwc'           #: field default/clear value (init by _Field.set_clear_val(), used by clear_leafs())
FAT_REC = 'rrd'                 #: root Record instance
FAT_RCX = 'rrx'                 #: field index path (idx_path) from the root Record instance
FAT_CAL = 'clc'                 #: calculator callable
FAT_CHK = 'chk'                 #: validator callable
FAT_CNV = 'cnv'                 #: system value converter callable
FAT_FLT = 'flt'                 #: field filter callable
FAT_SQE = 'sqc'                 #: SQL expression for to fetch field value from db

ALL_FATS = (FAT_IDX, FAT_VAL, FAT_CLEAR_VAL, FAT_REC, FAT_RCX, FAT_CAL, FAT_CHK, FAT_CNV, FAT_FLT, FAT_SQE)
""" tuple of all pre-defined field aspect types/prefixes """

FAD_FROM = 'From'               #: FROM field aspect direction
FAD_ONTO = 'Onto'               #: ONTO field aspect direction

IDX_PATH_SEP = '/'
""" separator character used for idx_path values (especially if field has a Record value).

don't use dot char because this is used e.g. for to separate system field names in xml element name paths.
"""

ALL_FIELDS = '**'
""" special key of fields_patches argument of Record.copy() for to allow aspect value patching for all fields. """

CALLABLE_SUFFIX = '()'          #: suffix for aspect keys - used by _Field.set_aspects()

_ASP_TYPE_LEN = 3               #: aspect key type string length
_ASP_DIR_LEN = 4                #: aspect key direction string length
_ASP_SYS_MIN_LEN = 2            #: aspect key system id string length


IdxItemType = Union[int, str]                                   #: types of idx_path items
IdxPathType = Tuple[IdxItemType, ...]                           #: idx_path type
IdxType = Union[IdxPathType, str]
NodeType = TypeVar('NodeType', 'Record', 'Records')             #: Union['Record', 'Records']
ListType = TypeVar('ListType', 'Values', 'Records')             #: Union['Values', 'Records']
ValueType = TypeVar('ValueType',
                    'Value', 'Values', 'Record', 'Records')     #: Union['Value', 'Values', 'Record', 'Records']
NodeChildType = TypeVar('NodeChildType', '_Field', 'Record')    #: Union['_Field', 'Record']


def aspect_key(type_or_key: str, system: str = '', direction: str = '') -> str:
    """ compiles an aspect dict key from the given args

    :param type_or_key:     either FAT_* type or full key (including already the system and direction)-
    :param system:          system id string (if type_or_key is a pure FAT_* constant).
    :param direction:       direction string FAD_* constant (if type_or_key is a pure FAT_* constant).
    :return:                compiled aspect key as string.
    """
    msg = "aspect_key({}, {}, {}) error: ".format(type_or_key, system, direction)
    assert len(type_or_key) >= _ASP_TYPE_LEN, msg + "aspect type is too short"
    assert system == '' or len(system) >= _ASP_SYS_MIN_LEN, msg + "aspect system id is too short"
    assert direction == '' or len(direction) == _ASP_DIR_LEN, msg + "invalid aspect direction length"
    assert not type_or_key[0].islower() or type_or_key[:_ASP_TYPE_LEN] in ALL_FATS, msg + "invalid aspect type format"
    assert (system == '' or system[0].isupper()) and \
           (direction == '' or direction[0].isupper()), msg + "invalid system or direction format"

    key = type_or_key
    if len(key) == _ASP_TYPE_LEN:
        key += direction
    if len(key) <= _ASP_TYPE_LEN + _ASP_DIR_LEN:
        key += system

    assert key.isidentifier() and not keyword.iskeyword(key), msg + "key '{}' contains invalid characters".format(key)
    if type_or_key[:_ASP_TYPE_LEN] in ALL_FATS:
        assert key.count(FAD_FROM) <= 1 and key.count(FAD_ONTO) <= 1, msg + "direction duplicates"

    return key


def aspect_key_system(key: str) -> str:
    """ determines the system id string from an aspect key.

    :param key:     aspect key string.
    :return:        system id (SDI_* constant).
    """
    beg = _ASP_TYPE_LEN
    if len(key) > _ASP_TYPE_LEN + _ASP_DIR_LEN and key[beg:beg + _ASP_DIR_LEN] in (FAD_FROM, FAD_ONTO):
        beg += _ASP_DIR_LEN
    return key[beg:]


def aspect_key_direction(key: str) -> str:
    """ determines the direction id string from an aspect key.

    :param key:     aspect key string.
    :return:        direction id (FAD_* constant).
    """
    direction = key[_ASP_TYPE_LEN:_ASP_TYPE_LEN + _ASP_DIR_LEN]
    return direction if direction in (FAD_FROM, FAD_ONTO) else ''


def deeper(deepness: int, instance: Any) -> int:
    """ check and calculate resulting/remaining deepness for Record/_Field/Records.copy() when going one level deeper.

    :param deepness:    <0 will be returned unchanged until last level is reached (-1==full deep copy, -2==deep copy
                        until deepest Value, -3==deep copy until deepest _Field.
    :param instance:    instance to be processed/copied (if this method is returning != 0/zero).
    :return:            if deepness == 0 then return 0, if deepness < 0 then return 0 if the deepest level is reached,
                        else (deepness > 0) return deepness - 1.
    """
    if deepness > 0:
        remaining = deepness - 1
    elif deepness == -2 and isinstance(instance, Value) \
            or deepness == -3 and isinstance(instance, _Field) and isinstance(instance.value(), Value):
        remaining = 0
    else:
        remaining = deepness    # return unchanged if deepness in (0, -1) or == -2/-3 but not reached bottom/last level
    return remaining


def field_name_idx_path(field_name: Union[int, str, IdxPathType], return_root_fields: bool = False) -> IdxPathType:
    """ converts a field name path string into an index path tuple.

    :param field_name:          field name str or field name index/path string or field index tuple
                                or int (for Records index).
    :param return_root_fields:  pass True to also return len()==1-tuple for fields with no deeper path (def=False).
    :return:                    index path tuple (idx_path) or empty tuple if the field has no deeper path and
                                return_root_fields==False.
     """
    if isinstance(field_name, int):
        return (field_name, ) if return_root_fields else ()
    elif isinstance(field_name, (tuple, list)):
        return tuple(field_name) if return_root_fields or len(field_name) > 1 else ()

    idx_path = list()
    nam_i = num_i = None
    last_i = len(field_name) - 2    # prevent splitting of 1- or 2-digit-indexed sys names, like e.g. NAME-1 or CD_ADD11
    for ch_i, ch_v in enumerate(field_name):
        if ch_v == IDX_PATH_SEP:
            if nam_i is not None:
                idx_path.append(field_name[nam_i:ch_i])
                nam_i = None
            elif num_i is not None:
                idx_path.append(int(field_name[num_i:ch_i]))
                num_i = None
            continue            # simply ignore leading, trailing and duplicate IDX_PATH_SEP chars

        if str.isdigit(ch_v) and ch_i < last_i:
            if num_i is None:
                num_i = ch_i
                if nam_i is not None:
                    idx_path.append(field_name[nam_i:num_i])
                    nam_i = None
        else:
            if nam_i is None:
                nam_i = ch_i
                if num_i is not None:
                    idx_path.append(int(field_name[num_i:nam_i]))
                    num_i = None

    if idx_path:
        if nam_i is not None:
            idx_path.append(field_name[nam_i:])
    elif return_root_fields:
        idx_path.append(field_name)

    return tuple(idx_path)


def field_names_idx_paths(field_names: Sequence[IdxPathType]) -> List[IdxPathType]:
    """ return list of the full idx paths names for all the fields specified in the field_names argument.

    :param field_names:     sequence/list/tuple of field (main or system) names.
    :return:                list of their idx paths names.
    """
    return [field_name_idx_path(field_name, return_root_fields=True) for field_name in field_names]


def idx_path_field_name(idx_path: IdxPathType, add_sep: bool = False) -> str:
    """ convert index path tuple/list into field name string.

    :param idx_path:    index path to convert.
    :param add_sep:     pass True to always separate index with IDX_PATH_SEP. False/Def will only put a separator char
                        if field value is a Record (for to separate the root field name from the sub field name).
    :return:            field name string.
    """
    assert isinstance(idx_path, (tuple, list)), "idx_field_name(): expects tuple/list, got {}".format(type(idx_path))
    last_nam_idx = False
    field_name = ''
    for idx in idx_path:
        nam_idx = isinstance(idx, str)
        if field_name and (last_nam_idx and nam_idx or add_sep):
            field_name += IDX_PATH_SEP
        field_name += str(idx)
        last_nam_idx = nam_idx
    return field_name


def compose_current_index(node: Union[ListType, NodeType], idx_path: IdxPathType, use_curr_idx: List) -> IdxPathType:
    """ determine tuple with the current indexes.

    :param node:            root node/list (Record or Records/Values instance) to process.
    :param idx_path:        index path relative to root node passed in `node` arg.
    :param use_curr_idx:    list of index counters within `idx_path` where the current index has to be used.
    :return:                tuple of current indexes.
    """
    uci = use_curr_idx.copy()

    curr_idx = ()
    while True:
        idx, *idx2 = use_current_index(node, idx_path, uci, check_idx_type=True)
        curr_idx += (idx, )
        if not idx2:
            break
        elif node.node_child((idx,)) is None:       # if idx not exists then assume sub-path idx2 is correct
            curr_idx += tuple(idx2)
            break

        node = node.value(idx, flex_sys_dir=True)
        idx_path = idx_path[1:]

    return curr_idx


def current_index(node: Union[ListType, NodeType]) -> IdxItemType:
    """ get current index of passed `node`.

    :param node:    instance of Record or Records (real node) or Values (simple list).
    :return:        current index value.
    """
    return node.current_idx


def init_current_index(node: Union[ListType, NodeType], idx_path: IdxPathType, use_curr_idx: List) -> IdxPathType:
    """ determine current index of `node` and if not set the initialize to the first index path item.

    :param node:            root node/list (Record or Records/Values instance) to process.
    :param idx_path:        index path relative to root node passed in `node` arg.
    :param use_curr_idx:    list of index counters within `idx_path` where the current index has to be used.
    :return:                tuple of current indexes.
    """

    idx, *idx2 = use_current_index(node, idx_path, use_curr_idx, check_idx_type=True)

    if node.current_idx is None:
        set_current_index(node, idx)

    return (idx, ) + tuple(idx2)


def set_current_index(node: Union[ListType, NodeType], idx: Optional[IdxItemType] = None,
                      add: Optional[int] = None) -> IdxItemType:
    """ set current index of `node`.

    :param node:            root node/list (Record or Records/Values instance) to process.
    :param idx:             index value to set (str for field name; int for list index); if given `add` will be ignored.
    :param add:             value to add to list index; will be ignored if `idx` arg get passed.
    :return:                the finally set/new index value.
    """
    allowed_types = (Values, Records, Record)
    msg = "set_current_index() expects "
    assert isinstance(node, allowed_types), msg + "node arg of type {}, but got {}".format(allowed_types, type(node))
    assert isinstance(idx, IDX_TYPES) ^ isinstance(add, int), msg + "either int/str in idx or int in add"

    if idx is None:
        idx = node.current_idx + add

    node.current_idx = idx

    if isinstance(node, LIST_TYPES):
        if node.idx_min is None or idx < node.idx_min:
            node.idx_min = idx
        if node.idx_max is None or idx > node.idx_max:
            node.idx_max = idx

    return idx


def use_current_index(node: Union[ListType, NodeType], idx_path: IdxPathType, use_curr_idx: List,
                      check_idx_type: bool = False, delta: int = 1) -> IdxPathType:
    """ determine index path of `node` by using current index of `node` if exists and is enabled by `use_curr_idx` arg.

    :param node:            root node/list (Record or Records/Values instance) to process.
    :param idx_path:        index path relative to root node passed in `node` arg.
    :param use_curr_idx:    list of index counters within `idx_path` where the current index has to be used.
    :param check_idx_type:  pass True to additionally check if the index type is correct (def=False).
    :param delta:           value for to decrease the list index counters within `use_curr_idx` (def=1).
    :return:                tuple of current indexes.
    """
    msg = "use_current_index() expects "
    assert isinstance(idx_path, (tuple, list)) and len(idx_path), msg + "non-empty idx_path"
    assert isinstance(use_curr_idx, (List, type(None))), msg + "None/List type for use_curr_idx"

    idx, *idx2 = idx_path

    if isinstance(node, LIST_TYPES):
        idx_type = int
    elif isinstance(node, Record):
        idx_type = str
    else:
        assert False, msg + "value type of Values, Records or Record, but got {}".format(type(node))
    if check_idx_type:
        assert isinstance(idx, idx_type), "index type {} in idx_path[0], but got {}".format(idx_type, type(idx))

    if use_curr_idx:
        for level, val in enumerate(use_curr_idx):
            if val == 0 and node.current_idx is not None:
                idx = node.current_idx
            use_curr_idx[level] -= delta

    return (idx, ) + tuple(idx2)


def string_to_records(str_val: str, field_names: Sequence, rec_sep: str = ',', fld_sep: str = '=',
                      root_rec: 'Record' = None, root_idx: IdxPathType = ()) -> 'Records':
    """ convert formatted string into a :class:`Records` instance containing several :class:`Record` instances.

    :param str_val:     formatted string to convert.
    :param field_names: list/tuple of field names of each record
    :param rec_sep:     character(s) used in `str_val` for to separate the records.
    :param fld_sep:     character(s) used in `str_val` for to separate the field values of each record.
    :param root_rec:    root to which the returned records will be added.
    :param root_idx:    index path from root where the returned records will be added.
    :return:            converted :class:`Records` instance.
    """
    recs = Records()
    if str_val:
        for rec_idx, rec_str in enumerate(str_val.split(rec_sep)):  # type: (int, str)
            fields = dict()
            for fld_idx, fld_val in enumerate(rec_str.split(fld_sep)):
                fields[field_names[fld_idx]] = fld_val
            recs.append(Record(fields=fields, root_rec=root_rec, root_idx=root_idx + (rec_idx,)))
            set_current_index(recs, idx=rec_idx)
    return recs


def template_idx_path(idx_path: IdxPathType, is_sub_rec: bool = False) -> bool:
    """ check/determine if `idx_path` is referring to template item.

    :param idx_path:    index path to check.
    :param is_sub_rec:  pass True to only check sub-record-fields (will then return always False for root-fields).
    :return:            True if `idx_path` is referencing a template item (with index zero/0), else False.
    """
    if len(idx_path) < 2:
        return not is_sub_rec
    for idx in idx_path:
        if isinstance(idx, int) and idx == 0:
            return True
    return False


def use_rec_default_root_rec_idx(rec: 'Record', root_rec: Optional['Record'], idx: IdxPathType = (),
                                 root_idx: IdxPathType = (), met: str = "") -> Tuple['Record', IdxPathType]:
    """ helper function for to determine resulting root record and root index.

    :param rec:         current :class:`Record` instance.
    :param root_rec:    default root record (def=`rec`).
    :param idx:         current index of `rec`.
    :param root_idx:    default root index.
    :param met:         calling method/function name (used only for assert error message, def='').
    :return:            resulting root record and root index (as tuple).
    """
    if root_rec is None:
        root_rec = rec
        if root_idx is not None:
            assert root_idx == (),  met + ("(): " if met and not met.endswith(": ") else "") \
                                    + "root_idx has to be empty if no root_rec specified"
    if not root_idx and idx is not None:
        root_idx = idx
    return root_rec, root_idx


def use_rec_default_sys_dir(rec: 'Record', system: str, direction: str) -> Tuple[str, str]:
    """ helper function for to determine resulting system/direction.

    :param rec:         current :class:`Record` instance.
    :param system:      default system id.
    :param direction:   default direction (see FAD_* constants).
    :return:            resulting system and direction (as tuple).
    """
    if system is None:
        system = rec.system
    if direction is None:
        direction = rec.direction
    return system, direction


class Value(list):
    """ represents a value.

    This class inherits directly from the Python list class. Each instance can hold either a (single/atomic) value
    (which can be anything: numeric, char/string or any object) or a list of these single/atomic values.
    """
    def __getitem__(self, key: int) -> Any:
        """ determine atomic value.

        :param key:     list index if value is a list.
        :return:        list item value.
        """
        try:
            return super().__getitem__(key)
        except IndexError:
            if not isinstance(key, int) or key not in (-1, 0):
                return None
            return ''

    def __setitem__(self, key: int, value: Any) -> None:
        """ set/initialize list item identified by `key` to the value passed in `value`.

        :param key:     list index if value is a list.
        :param value:   the new value of the list item.
        """
        while True:
            try:
                return super().__setitem__(key, value)
            except (IndexError, TypeError):
                if not isinstance(key, int):
                    raise IndexError("Value() expects key of type int, but got {} of type {}".format(key, type(key)))
                self.append(value)

    def __repr__(self) -> str:
        """ representation which can be used to serialize and re-create :class:`Value` instance.

        :return: Value representation string.
        """
        return "Value([" + ",".join(repr(v) for v in self) + "])"

    @property
    def initialized(self):
        """ flag if this :class:`Value` instance got already initialized.

        :return: True if already set to a value, else False.
        """
        return len(self)

    def node_child(self, idx_path: IdxPathType, moan: bool = False, **__) -> Optional['Value']:
        """ check if `idx_path` is correct (has to be empty) and if yes then return self.

        This method is for to simplify the data structure hierarchy implementation.

        :param idx_path:    this argument has to be an empty tuple/list.
        :param moan:        pass True for to raise AssertionError if `idx_path` is not empty.
        :return:            self or None (if `idx_path` is not empty and `moan` == False).
        """
        if len(idx_path):
            assert not moan, "Value instance has no deeper node, but requesting {}".format(idx_path)
            return None
        return self

    def value(self, *idx_path: IdxItemType, **__) -> Optional['Value']:
        """ check if `idx_path` is correct (has to be empty) and if yes then return self.

        This method is for to simplify the data structure hierarchy implementation.

        :param idx_path:    this argument has to be an empty tuple.
        :return:            self or None (if `idx_path` is not empty and `moan` == False).
        """
        assert isinstance(idx_path, (tuple, list)) and len(idx_path) == 0, \
            "Value.value() expects empty idx_path list, but got {}".format(idx_path)
        return self

    def val(self, *idx_path, **__):
        """ check if `idx_path` is correct (either empty or contain one int) and if yes then return list item.

        This method is for to simplify the data structure hierarchy implementation.

        :param idx_path:    this argument is either empty or contains a list index.
        :return:            atomic/single value or list item value or empty string.
        """
        idx_len = len(idx_path)
        if idx_len == 0 or (idx_len == 1 and isinstance(idx_path[0], int)):
            return self[idx_path[0] if idx_len else -1]
        return ''

    def set_val(self, val: Any, *idx_path: IdxItemType, **__):
        """ set a/the value of this instance.

        :param val:         simple/atomic value to be set.
        :param idx_path:    this argument is either empty or contains a list index.
        :return:            self.
        """
        assert isinstance(idx_path, (tuple, list)) and len(idx_path) <= 1, \
            "Value.set_val({}) idx_path list {} has more than one entry".format(val, idx_path)
        assert not isinstance(val, VALUE_TYPES), "Value.set_val({}) got unexpected value type {}".format(val, type(val))
        self[idx_path[0] if isinstance(idx_path, (tuple, list)) and len(idx_path) else -1] = val
        return self

    def copy(self, *_, **__):
        """ copy the value of this Value instance into a new one.

        :return:                new Value instance containing the same immutable value.
        """
        return Value(super().copy())

    def clear_leafs(self, **__):
        """ clear/reset the value of this instance.

        use self[-1] = '' for to clear only the newest/top val.

        :return:    self.
        """
        self.clear()
        return self


class Values(list):                     # type: List[Union[Value, Record]]
    """ ordered/mutable sequence/list, which contains 0..n instances of the class :class:`Value`.
    """
    def __init__(self, seq: Iterable = ()):
        """ create new :class:`Values` instance.

        :param seq:     Iterable used to initialize the new instance (pass list, tuple or other iterable).
        """
        super().__init__(seq)
        self.current_idx = self.idx_min = self.idx_max = None

    def __repr__(self) -> str:
        return ("Records" if isinstance(self, Records) else "Values") + "([" + ",".join(repr(v) for v in self) + "])"

    def node_child(self, idx_path: IdxPathType, use_curr_idx: list = None, moan: bool = False,
                   selected_sys_dir: Optional[dict] = None) -> Optional[Union[Value, 'Record']]:
        """ determine and return node instance specified by `idx_path` if exists in this instance or underneath.

        :param idx_path:            index path to the node, relative to this instance.
        :param use_curr_idx:        list of counters for to specify if and which current indexes have to be used.
        :param moan:                flag for to check data integrity; pass True to raise AssertionError if not.
        :param selected_sys_dir:    optional dict for to return the currently selected system/direction.
        :return:                    found node instance or None if not found.
        """
        msg = "node_child() of Values/Records instance {} expects ".format(self)
        if isinstance(idx_path, (tuple, list)):
            if len(idx_path) and not isinstance(idx_path[0], int):
                assert not moan, msg + "int type in idx_path[0], got {} in {}".format(type(idx_path), idx_path)
                return None
        elif not isinstance(idx_path, IDX_TYPES):
            assert not moan, msg + "str or int type in idx_path, got {} in {}".format(type(idx_path), idx_path)
            return None
        else:
            idx_path = field_name_idx_path(idx_path, return_root_fields=True)

        if not idx_path:
            assert not moan, msg + "non-empty tuple or list or index string in idx_path {}".format(idx_path)
            return None

        idx, *idx2 = use_current_index(self, idx_path, use_curr_idx)

        lst_len = len(self)
        if not isinstance(idx, int) or lst_len <= idx:
            assert not moan,  "Values/Records idx_path[0] {!r} is no integer or is not less than the list length {}" \
                .format(idx, lst_len)
            return None

        if len(idx_path) == 1:
            ret = super().__getitem__(idx)
            assert ret is not None or not moan, msg + "valid key but got {} from idx_path {}".format(idx, idx_path)
            return ret

        return self[idx].node_child(idx2, use_curr_idx=use_curr_idx, moan=moan, selected_sys_dir=selected_sys_dir)

    def value(self, *idx_path: IdxItemType, system: str = '', direction: str = '', **kwargs) \
            -> Optional[ValueType]:
        """ determine the ValueType instance referenced by `idx_path` of this :class:`Values`/:class:`Records` instance.

        :param idx_path:    index path items.
        :param system:      system id.
        :param direction:   direction id.
        :param kwargs:      extra args (will be passed to underlying data structure).
        :return:            found Value or Values instance, or None if not found.
        """
        if len(idx_path) == 0:
            return self

        idx, *idx2 = idx_path
        return self[idx].value(*idx2, system=system, direction=direction, **kwargs)

    def set_value(self, value: ValueType, *idx_path: IdxItemType, system: str = '', direction: str = '',
                  protect: bool = False, root_rec: Optional['Record'] = None, root_idx: IdxPathType = (),
                  use_curr_idx: list = None) -> Union['Values', 'Records']:
        """ set the ValueType instance referenced by `idx_path` of this :class:`Values`/:class:`Records` instance.

        :param value:           ValueType instance to set/change.
        :param idx_path:        index path items.
        :param system:          system id.
        :param direction:       direction id.
        :param protect:         pass True to prevent replacement of already existing `ValueType`.
        :param root_rec:        root record.
        :param root_idx:        root index.
        :param use_curr_idx:    list of counters for to specify if and which current indexes have to be used.
        :return:                self (this instance of :class:`Values` or :class:`Records`).
        """
        assert len(idx_path), "Values/Records.set_value() idx_path '{}' must be non-empty tuple/list".format(idx_path)

        if isinstance(self, Records):
            idx, *idx2 = init_current_index(self, idx_path, use_curr_idx)
            if root_idx:
                root_idx += (idx,)
            self[idx].set_value(value, *idx2, system=system, direction=direction, protect=protect,
                                root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)
        else:
            idx = idx_path[0]
            assert isinstance(value, Value), "Values.set_value() value must be Value type, got {}".format(type(value))
            assert len(idx_path) == 1, "Values.set_value() idx_path must be single index, got {}".format(idx_path)
            assert isinstance(idx, int), "Values.set_value() idx_path index must be int, got {}".format(idx)
            self[idx] = value
        return self

    def val(self, *idx_path: IdxItemType, system: str = '', direction: str = '', flex_sys_dir: bool = True,
            use_curr_idx: list = None, **kwargs) -> Any:
        """ determine the user/system value referenced by `idx_path` of this :class:`Values`/:class:`Records` instance.

        :param idx_path:        index path items.
        :param system:          system id.
        :param direction:       direction id.
        :param flex_sys_dir:    pass True to allow fallback to system-independent value.
        :param use_curr_idx:    list of counters for to specify if and which current indexes have to be used.
        :param kwargs:          extra args (will be passed to underlying data structure).
        :return:                found user/system value, or None if not found or empty string if value was not set yet.
        """
        idx_len = len(idx_path)
        if idx_len == 0:
            val = list(self)
        else:
            idx, *idx2 = use_current_index(self, idx_path, use_curr_idx)
            if isinstance(idx, int) and idx < len(self):
                val = self[idx].val(*idx2, system=system, direction=direction, flex_sys_dir=flex_sys_dir,
                                    use_curr_idx=use_curr_idx, **kwargs)
            else:
                val = None
        return val

    def set_val(self, val: Any, *idx_path: IdxItemType, protect: bool = False, extend: bool = True,
                use_curr_idx: list = None) -> 'Values':
        """ set the user/system value referenced by `idx_path` of this :class:`Values` instance.

        :param val:             user/system value to set/change.
        :param idx_path:        index path items.
        :param protect:         pass True to prevent replacement of already existing `ValueType`.
        :param extend:          pass True to allow extension of data structure.
        :param use_curr_idx:    list of counters for to specify if and which current indexes have to be used.
        :return:                self (this instance of :class:`Values`).
        """
        idx, *idx2 = init_current_index(self, idx_path, use_curr_idx)
        assert isinstance(idx, int) and len(idx2) == 0, "Values expects one int index, but got {}".format(idx_path)
        value = val if isinstance(val, Value) else Value((val, ))
        list_len = len(self)
        if list_len <= idx:
            assert extend, "extend has to be True for to add Value instances to Values"
            for _ in range(idx - list_len):
                self.append(Value())
            self.append(value)
        else:
            self[idx] = value
        return self

    def copy(self, deepness: int = 0, root_rec: Optional['Record'] = None, root_idx: IdxPathType = (), **kwargs) \
            -> Union['Values', 'Records']:
        """ copy the values/records of this :class:`Values`/:class:`Records` instance.

        :param deepness:        deep copy levels: <0==see deeper(), 0==only copy current instance, >0==deep copy
                                to deepness value - _Field occupies two deepness: 1st=_Field, 2nd=Value).
        :param root_rec:        destination root record.
        :param root_idx:        destination index path (tuple of field names and/or list/Records indexes).
        :param kwargs:          additional arguments (will be passed on - most of them used by Record.copy).
        :return:                new instance of self (which is an instance of :class:`Values` or :class:`Records`).
        """
        ret = type(self)()      # create new instance of this list/class (Values or Records)
        for idx, rec in enumerate(self):
            if deeper(deepness, rec):
                rec = rec.copy(deepness=deeper(deepness, rec), root_rec=root_rec, root_idx=root_idx + (idx, ), **kwargs)
            ret.append(rec)
        return ret

    def clear_leafs(self, system: str = '', direction: str = '', flex_sys_dir: bool = True, reset_lists: bool = True) \
            -> Union['Values', 'Records']:
        """ clear/reset the user/system values of all the leafs of this :class:`Values`/:class:`Records` instance.

        :param system:          system id.
        :param direction:       direction id (FAD_* constants).
        :param flex_sys_dir:    pass False to prevent fallback to system-independent value.
        :param reset_lists:     pass False to prevent the reset of all the underlying lists.
        :return:
        """
        if reset_lists:
            self[1:] = []
        for rec in self:
            rec.clear_leafs(system=system, direction=direction, flex_sys_dir=flex_sys_dir, reset_lists=reset_lists)
        if len(self):
            self.current_idx = self.idx_min = 0
            self.idx_max = len(self) - 1
        else:
            self.current_idx = self.idx_min = self.idx_max = None
        return self


class Record(OrderedDict):
    """ instances of this mapping class are used to represent record-like data structures.

    isinstance(..., dict) not working if using MutableMapping instead of OrderedDict as super class. And dict
    cannot be used as super class because instance as kwarg will then not work: see the Groxx's answer in stackoverflow
    question at https://stackoverflow.com/questions/3387691/how-to-perfectly-override-a-dict/47361653#47361653.
    """
    def __init__(self, template: Optional['Records'] = None, fields: Optional[dict] = None,
                 system: str = '', direction: str = '', action: str = '',
                 root_rec: Optional['Record'] = None, root_idx: IdxPathType = (),
                 field_items: bool = False):
        """ Create new Record instance, which is an ordered collection of _Field items.

        :param template:    pass Records instance to use first item/[0] as template (after deep copy and vals cleared).
        :param fields:      OrderedDict/dict of _Field instances (field order is not preserved when using dict)
                            or Record instance (fields will be referenced, not copied!)
                            or list of (field_name, fld_or_val) tuples.
        :param system:      main/current system of this record,
        :param direction:   interface direction of this record.
        :param action:      current action (see ACTION_INSERT, ACTION_SEARCH, ACTION_DELETE, ...)
        :param root_rec:    root record of this record (def=self will be a root record).
        :param root_idx:    root index of this record (def=()).
        :param field_items: pass True to get Record items - using __getitem__() - as of type _Field (not as val()).
        """
        super().__init__()
        self._fields = self     # using internal store of OrderedDict() while keeping code better readable/maintainable
        self.system = system
        self.direction = direction
        self.action = action
        root_rec, root_idx = use_rec_default_root_rec_idx(self, root_rec, root_idx=root_idx, met="Record.__init__")
        self.field_items = field_items

        self.current_idx = None

        if template and len(template):
            template = template[0].copy(deepness=-1, root_rec=root_rec, root_idx=root_idx).clear_leafs()
            for idx in template.keys():
                self._add_field(template.node_child((idx, )))
        if fields:
            self.add_fields(fields, root_rec=root_rec, root_idx=root_idx)

        self.sys_name_field_map = dict()    # map system field name as key to _Field instance (as value).
        self.collected_system_fields = list()   # system fields found by collect_system_fields()

    def __repr__(self) -> str:
        return "Record({})".format(", ".join(repr(self._fields.val(*k)) for k in self.leaf_indexes()))

    def __str__(self) -> str:
        return "Record({})".format(", ".join(k for k in self.keys()))

    def __contains__(self, idx_path: IdxPathType) -> bool:
        item = self.node_child(idx_path)
        ''' on executing self.pop() no __delitem__ will be called instead python OrderedDict first pops the item
            then is calling this method, although super().__contains__() still returns True but then calls __getitem__()
            (again with this instance where the item got already removed from). So next two lines are not helping:
        
        if not item:
            item = super().__contains__(idx_path)
            
            So finally had to over-ride the Record.pop() method.
        '''
        return bool(item)

    def __getitem__(self, key: IdxPathType) -> Any:
        ssd = dict()
        child = self.node_child(key, moan=True, selected_sys_dir=ssd)
        ''' should actually not happen because with moan=True node_child() will raise AssertionError
        if child is None:
            raise KeyError("There is no item with the key '{}' in this Record/OrderedDict ({})".format(key, self))
        '''
        return child if self.field_items or not isinstance(child, _Field) \
            else child.val(system=ssd.get('system', self.system), direction=ssd.get('direction', self.direction))

    def __setitem__(self, key: IdxPathType, value: Any):
        idx_path = field_name_idx_path(key, return_root_fields=True)
        self.set_node_child(value, *idx_path)

    def node_child(self, idx_path: IdxType, use_curr_idx: Optional[list] = None, moan: bool = False,
                   selected_sys_dir: Optional[dict] = None) -> Optional[ValueType]:
        """ get the node child specified by `idx_path` relative to this :class:`Record` instance.

        :param idx_path:            index path or field name index string.
        :param use_curr_idx:        list of counters for to specify if and which current indexes have to be used.
        :param moan:                flag for to check data integrity; pass True to raise AssertionError if not.
        :param selected_sys_dir:    optional dict for to return the currently selected system/direction.
        :return:                    found node instance or None if not found.
        """
        msg = "Record.node_child() expects "
        if not isinstance(idx_path, (tuple, list)):
            if not isinstance(idx_path, str):
                assert not moan, msg + "str type in idx_path[0], got {} in {}".format(type(idx_path), idx_path)
                return None
            idx_path = field_name_idx_path(idx_path, return_root_fields=True)

        if not idx_path:
            assert not moan, msg + "non-empty tuple or list in idx_path {}".format(idx_path)
            return None

        idx, *idx2 = use_current_index(self, idx_path, use_curr_idx=use_curr_idx)
        if isinstance(idx, int):
            assert not moan, msg + "str (not int) type in 1st idx_path {} item, got {}".format(idx_path, type(idx_path))
            return None     # RETURN item not found (caller doing deep search with integer idx)

        # defensive programming: using self._fields.keys() although self._fields.items() gets item via get() in 3.5, for
        # .. to ensure _Field instances independent from self.field_items value (having py-tests for get() not items())
        for fld_nam in self._fields.keys():
            field = self._fields.get(fld_nam)   # type: Union[_Field, None]
            if fld_nam == idx:
                if not idx2:
                    break
                fld = field.node_child(idx2, use_curr_idx=use_curr_idx, moan=moan, selected_sys_dir=selected_sys_dir)
                if fld is not None:
                    field = fld
                    break
            if not idx2 and field.has_name(idx, selected_sys_dir=selected_sys_dir):
                return field
        else:
            assert not moan, msg + "valid key but got {} from idx_path {}".format(idx, idx_path)
            field = None

        return field

    def set_node_child(self, fld_or_val, *idx_path, system=None, direction=None, protect=False,
                       root_rec=None, root_idx=(), use_curr_idx=None, to_value_type=False):
        idx_len = len(idx_path)
        assert idx_len, "Record.set_node_child() expect 2 or more args - missing field name/-path"
        assert isinstance(idx_path[0], str), \
            "First item of Record idx_path '{}', specifying the field name, has to be of type string but is {}"\
            .format(idx_path, type(idx_path[0]))
        if idx_len == 1:
            nam_path = field_name_idx_path(idx_path[0])
            if nam_path:
                idx_path = nam_path
                idx_len = len(idx_path)

        system, direction = use_rec_default_sys_dir(self, system, direction)
        root_rec, root_idx = use_rec_default_root_rec_idx(self, root_rec, root_idx=root_idx,
                                                          met="Record.set_node_child")

        fld_idx, *idx2 = init_current_index(self, idx_path, use_curr_idx)
        root_idx += (fld_idx, )
        if not isinstance(fld_or_val, NODE_CHILD_TYPES):
            use_current_index(self, idx_path, use_curr_idx, delta=-1)
            self.set_val(fld_or_val, *idx_path, system=system, direction=direction, protect=protect,
                         root_rec=root_rec, root_idx=root_idx[:-1], use_curr_idx=use_curr_idx,
                         to_value_type=to_value_type)

        elif fld_idx in self._fields:
            if idx_len == 1:
                assert not protect, "set_node_child(): field {} exists; pass protect=False to overwrite".format(fld_idx)
                super().__setitem__(fld_idx, fld_or_val)
                fld_or_val.set_env(system=system, direction=direction, root_rec=root_rec, root_idx=root_idx)

            else:
                ror = self.value(fld_idx, flex_sys_dir=True)    # if protect==True then should be of Record or Records
                if not isinstance(ror, NODE_TYPES):
                    assert not protect, \
                        "value ({}) of field {} is of {}; expected {} or pass protect arg as False"\
                        .format(ror, idx_path, type(ror), NODE_TYPES)
                    ror = Record() if isinstance(idx2[0], str) else Records()
                    init_current_index(ror, idx2, use_curr_idx)
                    self.set_value(ror, fld_idx, root_rec=root_rec, root_idx=root_idx[:-1], use_curr_idx=use_curr_idx)
                ror.set_node_child(fld_or_val, *idx2, system=system, direction=direction, protect=protect,
                                   root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)

        elif idx_len == 1:
            self._add_field(fld_or_val, fld_idx)
            fld_or_val.set_env(system=system, direction=direction, root_rec=root_rec, root_idx=root_idx)

        else:
            use_current_index(self, idx_path, use_curr_idx, delta=-1)
            *rec_path, deep_fld_name = idx_path
            rec = self.node_child(rec_path, use_curr_idx=use_curr_idx)
            if not rec:     # if no deeper Record instance exists, then create new Record via empty dict and set_val()
                self.set_val(dict(), *rec_path, protect=protect, root_rec=root_rec, root_idx=root_idx[:-1],
                             use_curr_idx=use_curr_idx, to_value_type=to_value_type)
                rec = self.node_child(rec_path, use_curr_idx=use_curr_idx)
            use_current_index(self, idx_path, use_curr_idx, delta=len(rec_path))
            rec.set_node_child(fld_or_val, deep_fld_name, system=system, direction=direction, protect=protect,
                               root_rec=root_rec, root_idx=idx_path[:-1], use_curr_idx=use_curr_idx)

    def value(self, *idx_path, system=None, direction=None, **kwargs):
        if len(idx_path) == 0:
            return self

        system, direction = use_rec_default_sys_dir(self, system, direction)
        idx, *idx2 = idx_path

        field = self.node_child((idx, ))
        if field:
            return field.value(*idx2, system=system, direction=direction, **kwargs)

    def set_value(self, value, *idx_path, system=None, direction=None, protect=False, root_rec=None, root_idx=(),
                  use_curr_idx=None):
        system, direction = use_rec_default_sys_dir(self, system, direction)
        root_rec, root_idx = use_rec_default_root_rec_idx(self, root_rec, root_idx=root_idx, met="Record.set_value")
        idx, *idx2 = init_current_index(self, idx_path, use_curr_idx)
        root_idx += (idx, )
        field = self.node_child((idx, ))
        field.set_value(value, *idx2, system=system, direction=direction, protect=protect,
                        root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)
        return self

    def val(self, *idx_path, system=None, direction=None, flex_sys_dir=True, use_curr_idx=None, **kwargs):
        system, direction = use_rec_default_sys_dir(self, system, direction)

        idx_len = len(idx_path)
        if idx_len == 0:
            val = OrderedDict()
            for idx in self._fields.keys():
                field = self._fields.get(idx)
                val[idx] = field.val(system=system, direction=direction, flex_sys_dir=flex_sys_dir, **kwargs)
        else:
            idx, *idx2 = use_current_index(self, idx_path, use_curr_idx)
            if idx in self._fields:     # don't use _fields.keys() to also detect system field names
                # field = self._fields[idx]  ->  field = self._fields.get(idx)   # get() doesn't find sys fld names  ->
                ssd = dict()
                field = self.node_child(idx, selected_sys_dir=ssd)
                val = field.val(*idx2, system=ssd.get('system', system), direction=ssd.get('direction', direction),
                                flex_sys_dir=flex_sys_dir, use_curr_idx=use_curr_idx, **kwargs)
            else:
                val = None
        return val

    def set_val(self, val, *idx_path, system=None, direction=None, flex_sys_dir=True,
                protect=False, extend=True, converter=None, root_rec=None, root_idx=(), use_curr_idx=None,
                to_value_type=False):
        if len(idx_path) == 0:
            return self.add_fields(val)         # RETURN

        system, direction = use_rec_default_sys_dir(self, system, direction)
        root_rec, root_idx = use_rec_default_root_rec_idx(self, root_rec, root_idx=root_idx, met="Record.set_val")

        idx, *idx2 = init_current_index(self, idx_path, use_curr_idx)
        root_idx += (idx, )
        if idx in self._fields:
            ssd = dict()
            field = self.node_child(idx, selected_sys_dir=ssd)
            system, direction = ssd.get('system', system), ssd.get('direction', direction)
        else:
            assert extend, "Record.set_val() expects extend=True for to add new fields"
            field = _Field(root_rec=root_rec or self, root_idx=root_idx)
            self._add_field(field, idx)
            protect = False

        field.set_val(val, *idx2, system=system, direction=direction, flex_sys_dir=flex_sys_dir,
                      protect=protect, extend=extend, converter=converter,
                      root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx, to_value_type=to_value_type)
        return self

    def leafs(self, system=None, direction=None, flex_sys_dir=True):
        system, direction = use_rec_default_sys_dir(self, system, direction)
        for idx in self._fields.keys():
            field = self._fields.get(idx)
            yield from field.leafs(system=system, direction=direction, flex_sys_dir=flex_sys_dir)

    def leaf_indexes(self, *idx_path, system=None, direction=None, flex_sys_dir=True):
        system, direction = use_rec_default_sys_dir(self, system, direction)
        for idx in self._fields.keys():
            field = self._fields.get(idx)
            fld_idx = idx_path + (idx, )
            yield from field.leaf_indexes(*fld_idx, system=system, direction=direction, flex_sys_dir=flex_sys_dir)

    def _add_field(self, field, idx=''):
        """ add _Field instance to this Record instance.

        :param field:   _Field instance to add.
        :param idx:     name/key/idx string for to map and identify this field (mostly identical to field.name()).
        :return:        self.
        """
        msg = "_add_field({}, {}): ".format(field, idx)
        assert isinstance(field, _Field), msg + "field arg has to be of type _Field (not {})".format(type(field))
        assert isinstance(idx, str), msg + "idx arg has to be of type str (not {})".format(type(idx))

        if idx:
            field.set_name(idx)
        else:
            idx = field.name()

        assert idx not in self._fields, msg + "Record '{}' has already a field with the name '{}'".format(self, idx)

        super().__setitem__(idx, field)     # self._fields[idx] = field
        return self

    def add_fields(self, fields, root_rec=None, root_idx=()):
        """ adding fields to this Record instance.

        :param fields:      either a dict, a Record or a list with (key/field_name, val/_Field) tuples.
                            Key strings that are containing digits/numbers are interpreted as name/idx paths (then also
                            the specified sub-Records/-Fields will be created).
                            Values can be either _Field instances or field vals.
        :param root_rec:    root record of this record (def=self will be a root record).
        :param root_idx:    root index of this record (def=()).
        :return:            self
        """
        if isinstance(fields, dict):
            items = fields.items()
        else:
            items = fields
        root_rec, root_idx = use_rec_default_root_rec_idx(self, root_rec, root_idx=root_idx, met="Record.add_fields")

        for name, fld_or_val in items:
            idx_path = field_name_idx_path(name, return_root_fields=True)
            if not root_idx and isinstance(fld_or_val, _Field):
                root_idx = fld_or_val.root_idx()

            self.set_node_child(fld_or_val, *idx_path, protect=True, root_rec=root_rec, root_idx=root_idx)
        return self

    def add_system_fields(self, system_fields: Iterable[Iterable[Any]], sys_fld_indexes=None,
                          system=None, direction=None, extend=True):
        """ add/set fields from a system field tuple. This Record instance need to have system and direction
        specified/set.

        :param system_fields:   tuple/list of tuples/lists with system and main field names and optional field aspects.
                                The index of the field names and aspects within the inner tuples/lists get specified
                                by sys_fld_indexes.
        :param sys_fld_indexes: mapping/map-item-indexes of the inner tuples of system_fields. Keys are field aspect
                                types (FAT_* constants), optionally extended with a direction (FAD_* constant) and a
                                system (SDI_* constant). If the value aspect key (FAT_VAL) contains a callable then
                                it will be set as the calculator (FAT_CAL) aspect; if contains a field value then also
                                the clear_val of this field will be set to the specified value.
        :param system:          system of the fields to be added - if not passed self.system will be used.
        :param direction:       direction (FAD constants) of the fields to be added - if not passed used self.direction.
        :param extend:          True=add not existing fields, False=apply new system aspects only on existing fields.
        :return:                self
        """
        msg = "add_system_fields() expects "
        assert isinstance(system_fields, (tuple, list)) and len(system_fields), \
            msg + "non-empty list or tuple in system_fields arg, got {}".format(system_fields)
        system, direction = use_rec_default_sys_dir(self, system, direction)
        assert system and direction, msg + "non-empty system/direction values (either from args or self)"
        sys_nam_key = aspect_key(FAT_IDX, system=system, direction=direction)
        if sys_fld_indexes is None:
            sys_fld_indexes = {sys_nam_key: 0,
                               FAT_IDX: 1,
                               FAT_VAL: 2,
                               FAT_FLT + FAD_ONTO: 3,
                               FAT_CNV + FAD_FROM: 4,
                               FAT_CNV + FAD_ONTO: 5}
        else:
            assert isinstance(sys_fld_indexes, dict), "sys_fld_indexes must be an instance of dict, got {} instead"\
                .format(type(sys_fld_indexes))
            if sys_nam_key not in sys_fld_indexes:  # check if sys name key is specified without self.system
                sys_nam_key = aspect_key(FAT_IDX, direction=direction)
            assert FAT_IDX in sys_fld_indexes and sys_nam_key in sys_fld_indexes, \
                msg + "field and system field name aspects in sys_fld_indexes arg {}".format(sys_fld_indexes)
        err = [_ for _ in system_fields if sys_nam_key not in sys_fld_indexes or sys_fld_indexes[sys_nam_key] >= len(_)]
        assert not err, msg + "system field name/{} in each system_fields item; missing in {}".format(sys_nam_key, err)

        for fas in system_fields:
            map_len = len(fas)
            sfi = sys_fld_indexes.copy()    # fresh copy needed because field names and converter get popped from sfi

            fld_nam_i = sfi.pop(FAT_IDX)
            if map_len <= fld_nam_i or fas[fld_nam_i] is None:
                continue
            field_name = fas[fld_nam_i]
            if isinstance(field_name, (tuple, list)):
                idx_path = field_name
                field_name = field_name[-1]
            else:
                idx_path = field_name_idx_path(field_name, return_root_fields=True)
                field_name = idx_path[-1]

            sys_name = fas[sfi.pop(sys_nam_key)].strip('/')     # strip needed for Sihot elem names only

            records = self.value(idx_path[0], system='', direction='')
            if template_idx_path(idx_path, is_sub_rec=True) and records:
                # if template sub-record then also add sys name/converter/calculator/filter/... to each sub Record
                idx_paths = [(idx_path[0], idx, ) + idx_path[2:] for idx in range(len(records))]
            else:
                idx_paths = (idx_path, )
            for path_idx, idx_path in enumerate(idx_paths):
                field = self.node_child(idx_path)
                field_created = not bool(field)
                if not field:
                    if not extend:
                        continue
                    field = _Field(root_rec=self, root_idx=idx_path)
                    field.set_name(field_name)

                # add additional aspects: first always add converter and value (for to create separate system value)
                cnv_func = None
                cnv_key = FAT_CNV + direction
                if map_len > sfi.get(cnv_key, map_len):
                    cnv_func = fas[sfi.pop(cnv_key)]
                elif map_len > sfi.get(FAT_CNV, map_len):
                    cnv_func = fas[sfi.pop(FAT_CNV)]
                if cnv_func:
                    field.set_converter(cnv_func, system=system, direction=direction, extend=True,
                                        root_rec=self, root_idx=idx_path)
                # now add all other field aspects (allowing calculator function specified in FAT_VAL aspect)
                for fa, fi in sfi.items():
                    if fa.startswith(FAT_CNV):
                        continue                    # skip converter for other direction
                    if map_len > fi and fas[fi] is not None \
                            and fa[_ASP_TYPE_LEN:] in ('', direction, system, direction + system):
                        if not fa.startswith(FAT_VAL):
                            field.set_aspect(fas[fi], fa, system=system, direction=direction, protect=True)
                        elif callable(fas[fi]):     # is a calculator specified in value/FAT_VAL item
                            field.set_calculator(fas[fi], system=system, direction=direction, protect=True)
                        else:                       # init field and clear val
                            val = fas[fi]
                            if path_idx == 0:
                                field.set_val(val, system=system, direction=direction, protect=True,
                                              root_rec=self, root_idx=idx_path)
                            field.set_clear_val(val, system=system, direction=direction)

                self.set_node_child(field, *idx_path, protect=field_created, root_rec=self, root_idx=())
                # set sys field name and root_idx (after set_node_child() which is resetting sys root_idx to field name)
                # multiple sys names for the same field - only use the first one (for parsing but allow for building)
                if not field.name(system=system, direction=direction, flex_sys_dir=False):
                    field.set_name(sys_name, system=system, direction=direction, protect=True)

                if sys_name not in self.sys_name_field_map:
                    self.sys_name_field_map[sys_name] = field   # on sub-Records only put first row's field

        return self
    
    def collect_system_fields(self, sys_fld_name_path, path_sep):
        self.collected_system_fields = list()

        deep_sys_fld_name = sys_fld_name_path[-1]
        full_path = path_sep.join(sys_fld_name_path)
        for sys_name, field in self.sys_name_field_map.items():
            if sys_name == deep_sys_fld_name or sys_name == full_path or full_path.endswith(path_sep + sys_name):
                if field not in self.collected_system_fields:
                    self.collected_system_fields.append(field)

        return self.collected_system_fields

    def compare_leafs(self, rec, field_names=(), exclude_fields=()):
        def _excluded():
            return (field_names and idx_path[0] not in field_names and idx_path[-1] not in field_names) \
                                or (idx_path[0] in exclude_fields or idx_path[-1] in exclude_fields)
        dif = list()
        found_idx = list()
        for idx_path in self.leaf_indexes(system='', direction=''):
            if _excluded():
                continue
            found_idx.append(idx_path)
            this_val = self.compare_val(*idx_path)
            if idx_path in rec:
                that_val = rec.compare_val(*idx_path)
                if this_val != that_val:
                    dif.append("Different values in Field {}: {}:{!r} != {}:{!r}"
                               .format(idx_path, self.system, this_val, rec.system, that_val))
            elif this_val:  # silently skip/ignore fields with empty value in this record if field doesn't exist in rec
                dif.append("Field {}:{}={} does not exist in the other Record"
                           .format(self.system, idx_path, self.val(*idx_path)))

        for idx_path in rec.leaf_indexes(system='', direction=''):
            if _excluded():
                continue
            if idx_path not in found_idx:
                dif.append("Field {}:{}={} does not exist in this Record"
                           .format(rec.system, idx_path, rec.val(*idx_path)))

        return dif

    def compare_val(self, *idx_path):
        idx = self.node_child(idx_path).name()
        val = self.val(*idx_path, system='', direction='')

        if isinstance(val, str):
            if idx == 'SfId':
                val = val[:15]
            elif 'name' in idx.lower():
                val = val.capitalize()
            elif 'Email' in idx:
                val, _ = correct_email(val.lower())
            elif 'Phone' in idx:
                val, _ = correct_phone(val)
            val = val.strip()
            if len(val) > 39:
                val = val[:39].strip()
            if val == '':
                val = None
        elif isinstance(val, (datetime.date, datetime.datetime)):
            val = val.toordinal()

        return val

    def copy(self, deepness=0, root_rec=None, root_idx=(), onto_rec=None, filter_fields=None, fields_patches=None):
        """ copy the fields of this record

        :param deepness:        deep copy level: <0==see deeper(), 0==only copy this record instance, >0==deep copy
                                to deepness value - _Field occupies two deepness: 1st=_Field, 2nd=Value).
        :param root_rec:        destination root record - using onto_rec/new record if not specified.
        :param root_idx:        destination root index (tuple/list with index path items: field names, list indexes).
        :param onto_rec:        destination record; pass None to create new Record instance.
        :param filter_fields:   method called for each copied field (return True to filter/hide/not-include into copy).
        :param fields_patches:  dict[field_name_or_ALL_FIELDS:dict[aspect_key:val_or_callable]] for to overwrite
                                aspect values in each copied _Field instance). The keys of the outer dict are either
                                field names or the ALL_FIELDS value; aspect keys ending with the CALLABLE_SUFFIX
                                have a callable in the dict item that will be called for each field with the field
                                instance as argument; the return value of the callable will then be used as the (new)
                                aspect value.
        :return:                new/extended record instance.
        """
        new_rec = onto_rec is None
        if new_rec:
            onto_rec = Record()
        if root_rec is None:
            root_rec = onto_rec
        assert onto_rec is not self, "copy() cannot copy to self (same Record instance)"

        for idx in self._fields.keys():
            field = self._fields.get(idx)
            if filter_fields:
                assert callable(filter_fields)
                if filter_fields(field):
                    continue

            if deeper(deepness, field):
                field = field.copy(deepness=deeper(deepness, field), onto_rec=None if new_rec else onto_rec,
                                   root_rec=root_rec, root_idx=root_idx + (idx, ),
                                   filter_fields=filter_fields, fields_patches=fields_patches)
            elif idx in onto_rec:
                field = onto_rec.node_child((idx, ))

            if fields_patches:
                if ALL_FIELDS in fields_patches:
                    field.set_aspects(allow_values=True, **fields_patches[ALL_FIELDS])
                if idx in fields_patches:
                    field.set_aspects(allow_values=True, **fields_patches[idx])
                idx = field.name()      # update field name and root rec ref and idx if changed by field_patches
                field.set_system_root_rec_idx(root_rec=root_rec, root_idx=root_idx + (idx, ))

            if new_rec:
                onto_rec._add_field(field, idx)
            else:
                onto_rec.set_node_child(field, idx)

        return onto_rec

    def clear_leafs(self, system='', direction='', flex_sys_dir=True, reset_lists=True):
        for idx in self._fields.keys():
            field = self._fields.get(idx)
            field.clear_leafs(system=system, direction=direction, flex_sys_dir=flex_sys_dir, reset_lists=reset_lists)
        return self

    def leaf_names(self, system='', direction='', col_names=(), field_names=(), exclude_fields=(), name_type=None):
        names = list()
        for field in self.leafs(system=system, direction=direction, flex_sys_dir=False):
            idx_path = field.root_idx(system=system, direction=direction)
            if not template_idx_path(idx_path):
                continue
            sys_name = field.name(system=system or self.system, direction=direction or self.direction,
                                  flex_sys_dir=False)
            if not sys_name or (col_names and sys_name not in col_names):
                continue
            fld_name = field.name()
            root_name = idx_path_field_name(idx_path)
            if not (field_names and fld_name not in field_names and root_name not in field_names
                    or fld_name in exclude_fields or root_name in exclude_fields):
                if name_type == 's':
                    ret_name = sys_name
                elif name_type == 'f':
                    ret_name = fld_name
                elif name_type == 'r':
                    ret_name = root_name
                elif name_type == 'S':
                    ret_name = tuple(idx_path[:-1]) + (sys_name, )
                elif name_type == 'F':
                    ret_name = idx_path
                else:
                    ret_name = root_name if len(idx_path) > 1 and idx_path[0] == fld_name \
                        else (sys_name if system else fld_name)
                if ret_name:
                    names.append(ret_name)

        return tuple(names)

    def merge_leafs(self, rec, system='', direction='', flex_sys_dir=True, extend=True):
        for idx_path in rec.leaf_indexes(system=system, direction=direction, flex_sys_dir=flex_sys_dir):
            dst_field = self.node_child(idx_path)
            if extend or dst_field:
                src_field = rec.node_child(idx_path)
                if dst_field:
                    # noinspection PyProtectedMember
                    dst_field.set_aspects(allow_values=True, **src_field._aspects)
                elif extend:
                    self.set_node_child(src_field, *idx_path, system='', direction='')
        return self

    def match_key(self, match_fields):
        return tuple([self.val(fn) for fn in match_fields])

    def merge_vals(self, rec, system='', direction='', flex_sys_dir=True, extend=True):
        for idx_path in rec.leaf_indexes(system=system, direction=direction, flex_sys_dir=flex_sys_dir):
            if not extend and idx_path[0] not in self._fields:
                continue
            val = rec.val(*idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
            if val is not None:
                self.set_val(val, *idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        return self

    def missing_fields(self, required_fields=()):
        missing = list()
        for alt in required_fields:
            if not isinstance(alt, tuple):
                alt = (alt, )
            for idx in alt:
                if self.val(idx, system='', direction=''):
                    break
            else:
                missing.append(alt)
        return missing

    def pop(self, key):
        item = self.get(key)
        if item:
            super().__delitem__(key)
        return item

    def pull(self, from_system):
        assert from_system, "Record.pull() with empty value in from_system is not allowed"
        for idx_path in self.leaf_indexes(system=from_system, direction=FAD_FROM):    # _fields.values():
            if len(idx_path) >= 3 and isinstance(idx_path[1], int):
                set_current_index(self.value(idx_path[0], system=from_system, direction=FAD_FROM, flex_sys_dir=True),
                                  idx=idx_path[1])
            field = self.node_child(idx_path)
            field.pull(from_system, self, idx_path)
        return self

    def push(self, onto_system):
        assert onto_system, "Record.push() with empty value in onto_system is not allowed"
        for idx_path in self.leaf_indexes(system=onto_system, direction=FAD_ONTO):
            field = self.node_child(idx_path)
            field.push(onto_system, self, idx_path)
        return self

    def set_current_system_index(self, sys_fld_name_prefix, path_sep, idx_val=None, idx_add=1):
        prefix = sys_fld_name_prefix + path_sep
        for sys_path, field in self.sys_name_field_map.items():
            if sys_path.startswith(prefix):
                rec = field.root_rec(system=self.system, direction=self.direction)
                idx_path = field.root_idx(system=self.system, direction=self.direction)
                for off, idx in enumerate(idx_path):
                    if isinstance(idx, int):
                        value = rec.value(*idx_path[:off], flex_sys_dir=True)
                        set_current_index(value, idx=idx_val, add=idx_add)
                        return self

    def set_env(self, system=None, direction=None, action=None, root_rec=None, root_idx=()):
        if system is not None:
            self.system = system
        if direction is not None:
            self.direction = direction
        if action is not None:
            self.action = action
        root_rec, root_idx = use_rec_default_root_rec_idx(self, root_rec, root_idx=root_idx, met="Record.set_env")

        # for idx in self._fields.keys():
        #    field = self._fields.get(idx)
        #    field.set_env(system=system, direction=direction, root_rec=root_rec, root_idx=root_idx + (idx,))
        for idx_path in self.leaf_indexes(system=system, direction=direction):
            field = self.node_child(idx_path)
            field.set_env(system=system, direction=direction, root_rec=root_rec, root_idx=root_idx + idx_path)

        return self

    def sql_columns(self, from_system, col_names=()):
        """ return list of sql column names for given system.

        :param from_system: system from which the data will be selected/fetched.
        :param col_names:   optionally restrict to select columns to names given in this list.
        :return:            list of sql column names.
        """
        column_names = list()
        for idx in self._fields.keys():
            field = self._fields.get(idx)
            if len(field.root_idx(system=from_system, direction=FAD_FROM)) == 1:
                name = field.aspect_value(FAT_IDX, system=from_system, direction=FAD_FROM)
                if name and (not col_names or name in col_names):
                    column_names.append(name)
        return column_names

    def sql_select(self, from_system, col_names=()):
        """ return list of sql column names/expressions for given system.

        :param from_system: system from which the data will be selected/fetched.
        :param col_names:   optionally restrict to select columns to names given in this list.
        :return:            list of sql column names/expressions.
        """
        column_expressions = list()
        for idx in self._fields.keys():
            field = self._fields.get(idx)
            if len(field.root_idx(system=from_system, direction=FAD_FROM)) == 1:
                name = field.aspect_value(FAT_IDX, system=from_system, direction=FAD_FROM)
                if name and (not col_names or name in col_names):
                    expr = field.aspect_value(FAT_SQE, system=from_system, direction=FAD_FROM) or ""
                    if expr:
                        expr += " AS "
                    column_expressions.append(expr + name)
        return column_expressions

    def to_dict(self, filter_fields=None, key_type=str, push_onto=True,
                use_system_key=True, put_system_val=True, put_empty_val=False,
                system=None, direction=None):
        """ copy Record leaf values into a dict.

        :param filter_fields:   callable returning True for each field that need to be excluded in returned dict, pass
                                None to include all fields (if put_empty_val == True).
        :param key_type:        type of dict keys: None=field name, tuple=index path tuple, str=index path string (def).
        :param push_onto:       pass False to prevent self.push(system).
        :param use_system_key:  pass False to put leaf field name/index; def=True for to use system field name/keys,
                                specified by the system/direction args.
        :param put_system_val:  pass False to include/use main field val; def=True for to include system val specified
                                by the system/direction args.
        :param put_empty_val:   pass True to also include fields with an empty value (None/'').
        :param system:          system id for to determine included leaf and field val (if put_system_val == True).
        :param direction:       direction id for to determine included leaf and field val (if put_system_val == True).
        :return:                dict of filtered leafs, having (sys) field names/idx_path-tuples as their key.
        """
        system, direction = use_rec_default_sys_dir(self, system, direction)
        if push_onto and system:
            self.push(system)

        ret = dict()
        for idx_path in self.leaf_indexes(system=system, direction=direction):
            field = self.node_child(idx_path)
            key = field.name(system=system, direction=direction, flex_sys_dir=False)
            if key and (not filter_fields or not filter_fields(field)):
                key_path = tuple(idx_path[:-1] + (key,)) if system and use_system_key else idx_path
                if key_type == tuple:
                    key = key_path
                elif key_type == str:
                    key = idx_path_field_name(key_path)
                if put_system_val:
                    val = self.val(idx_path, system=system, direction=direction)
                else:
                    val = self.val(idx_path, system='', direction='')
                if put_empty_val or val not in (None, ''):
                    ret[key] = val
        return ret

    def update(self, mapping=(), **kwargs):
        super().update(mapping, **kwargs)
        return self     # implemented only for to get self as return value


class Records(Values):              # type: List[Record]
    def __init__(self, seq=()):
        super().__init__(seq)
        self.match_index = dict()   # type: Dict[Tuple, List[Record]]

    def __getitem__(self, key: Union[int, str, tuple]) -> Union[Record, list]:
        if isinstance(key, slice):
            return super().__getitem__(key)
        child = self.node_child(key, moan=True)
        ''' should actually not happen because with moan=True node_child() will raise AssertionError
        if child is None:
            raise KeyError("There is no item with the idx_path '{}' in this Records instance ({})".format(key, self))
        '''
        return child

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            super().__setitem__(key, value)
        else:
            idx_path = field_name_idx_path(key, return_root_fields=True)
            self.set_node_child(value, *idx_path)

    def set_node_child(self, rec_or_fld_or_val, *idx_path, system='', direction='', protect=False,
                       root_rec=None, root_idx=(), use_curr_idx=None):
        idx_len = len(idx_path)
        assert idx_len, "Records.set_node_child() idx_path {} too short; expected one or more items".format(idx_path)

        idx, *idx2 = init_current_index(self, idx_path, use_curr_idx)
        assert isinstance(idx, int), \
            "Records.set_node_child() 1st item of idx_path {} has to be integer, got {}".format(idx_path, type(idx))

        for _ in range(idx - len(self) + 1):
            self.append(Record(template=self, root_rec=root_rec, root_idx=root_idx))
            protect = False

        if root_idx:
            root_idx += (idx, )
        if idx_len == 1:
            assert not protect, "protect has to be False to overwrite Record"
            if not isinstance(rec_or_fld_or_val, Record):
                rec_or_fld_or_val = Record(template=self, fields=rec_or_fld_or_val,
                                           system='' if root_idx else system, direction='' if root_idx else direction,
                                           root_rec=root_rec, root_idx=root_idx)
            super().__setitem__(idx, rec_or_fld_or_val)
        else:
            rec = self[idx]  # type: Record
            rec.set_node_child(rec_or_fld_or_val, *idx2, system=system, direction=direction, protect=protect,
                               root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)
        return self

    def set_val(self, val, *idx_path, system='', direction='', flex_sys_dir=True,
                protect=False, extend=True, converter=None, root_rec=None, root_idx=(), use_curr_idx=None):
        if len(idx_path) == 0:
            for idx, row in enumerate(val):
                self.set_node_child(row, idx, system=system, direction=direction,
                                    protect=protect, root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)
            return self                                 # RETURN

        idx, *idx2 = init_current_index(self, idx_path, use_curr_idx)  # type: (int, list)
        assert isinstance(idx, int), "Records expects first index of type int, but got {}".format(idx)

        list_len = len(self)
        if root_idx:
            root_idx += (idx, )
        if list_len <= idx:
            assert extend, "extend has to be True for to add Value instances to Values"
            for _ in range(idx - list_len + 1):
                self.append(Record(template=self, root_rec=root_rec, root_idx=root_idx))
                protect = False

        if not idx2:
            assert not protect, "Records.set_val() pass protect=False to overwrite {}".format(idx)
            # noinspection PyTypeChecker
            # without above: strange PyCharm type hint warning: Type 'int' doesn't have expected attribute '__len__'
            self[idx] = val if isinstance(val, Record) else Record(template=self, fields=val,
                                                                   root_rec=root_rec, root_idx=root_idx)

        else:
            rec = self[idx]  # type: Record
            assert isinstance(rec, Record), "Records can only contain Record instances, got {}".format(type(rec))
            rec.set_val(val, *idx2, system=system, direction=direction, flex_sys_dir=flex_sys_dir,
                        protect=protect, extend=extend, converter=converter, root_rec=root_rec, root_idx=root_idx,
                        use_curr_idx=use_curr_idx)

        return self

    def leafs(self, system='', direction='', flex_sys_dir=True):
        for item in self:
            yield from item.leafs(system=system, direction=direction, flex_sys_dir=flex_sys_dir)

    def leaf_indexes(self, *idx_path, system='', direction='', flex_sys_dir=True):
        for idx, rec in enumerate(self):
            item_idx = idx_path + (idx, )
            yield from rec.leaf_indexes(*item_idx, system=system, direction=direction, flex_sys_dir=flex_sys_dir)

    def append_record(self, root_rec, root_idx=(), from_rec=None, clear_leafs=True):
        assert isinstance(root_rec, Record), "Records.append_record() expects Record instance in the root_rec arg"
        recs_len = len(self)
        if from_rec is None:
            from_rec = self[0] if recs_len else Record(root_rec=root_rec, root_idx=root_idx)

        new_rec = from_rec.copy(deepness=-1, root_rec=root_rec, root_idx=root_idx + (recs_len,))
        self.append(new_rec)

        if clear_leafs:
            new_rec.clear_leafs()       # clear fields and set init/default values

        return new_rec

    def compare_records(self, records, match_fields, field_names=(), exclude_fields=(), record_comparator=None):
        records.index_match_fields(match_fields)
        processed_match_keys = list()

        dif = list()
        for idx, rec in enumerate(self):
            match_key = rec.match_key(match_fields)
            if match_key in records.match_index:
                for p_rec in records.match_index[match_key]:
                    dif.extend(rec.compare_leafs(p_rec, field_names=field_names, exclude_fields=exclude_fields))
                    if callable(record_comparator):
                        dif.extend(record_comparator(rec, p_rec))
                processed_match_keys.append(match_key)
            else:
                dif.append("Record {} of this Records instance not found via {}; rec={}".format(idx, match_key, rec))

        for match_key, p_recs in records.match_index.items():
            if match_key in processed_match_keys:
                continue
            for p_rec in p_recs:
                dif.append("Pulled Record not found in this Records instance via {}; rec={}".format(match_key, p_rec))

        return dif

    def index_match_fields(self, match_fields):
        for idx, rec in enumerate(self):
            match_key = rec.match_key(match_fields)
            if match_key in self.match_index:
                self.match_index[match_key].append(self[idx])
            else:
                self.match_index[match_key] = [self[idx]]
        return self

    def merge_records(self, records, match_fields=()):
        if len(self) == 0 or not match_fields:
            self.extend(records)
        else:
            if not self.match_index:
                self.index_match_fields(match_fields)
            for rec in records:
                match_key = rec.match_key(match_fields)
                if match_key in self.match_index:
                    for this_rec in self.match_index[match_key]:
                        this_rec.update(rec)
                else:
                    self.append(rec)
        return self

    def set_env(self, system='', direction='', root_rec=None, root_idx=()):
        for idx, rec in enumerate(self):
            rec.set_env(system=system, direction=direction, root_rec=root_rec,
                        # only extend with Records/list index if there is a Record above this Records instance
                        root_idx=root_idx + (idx, ) if root_idx else ())
        return self


class _Field:
    """ Internal/Private class for to create record field instances.

    System-specific representations of the value of a :class:`_Field` instance can be (automatically) converted
    by specifying a converter callable.

    """
    def __init__(self, root_rec=None, root_idx=(), allow_values=False, **aspects):
        self._aspects = dict()
        self.add_aspects(allow_values=allow_values, **aspects)
        if root_rec is not None:
            self.set_root_rec(root_rec)
        if root_idx:
            self.set_root_idx(root_idx)

        assert FAT_REC in self._aspects, "_Field need to have a root Record instance"
        assert FAT_RCX in self._aspects, "_Field need to have an index path from the root Record instance"

        if FAT_VAL not in self._aspects and FAT_CAL not in self._aspects:
            self._aspects[FAT_VAL] = Value()
        if FAT_IDX not in self._aspects:
            self._aspects[FAT_IDX] = self.root_idx()[0]

    def __repr__(self):
        names = self.name()
        vals = repr(self.val())
        sys_dir_names = list()
        for idx_key, name in self._aspects.items():
            if idx_key.startswith(FAT_IDX) and len(idx_key) > _ASP_TYPE_LEN:
                sys_dir_names.append((idx_key, name))
        for idx_key, name in sys_dir_names:
            val_key = self.aspect_exists(FAT_VAL,
                                         system=aspect_key_system(idx_key), direction=aspect_key_direction(idx_key))
            if val_key and len(val_key) > _ASP_TYPE_LEN:
                vals += "|" + "{}={}".format(name, self._aspects.get(val_key))
            else:
                names += "|" + name

        return "{}=={}".format(names, vals)

    def __str__(self):
        # return "_Field(" + repr(self._aspects) + ")"
        return "_Field(" + ", ".join([str(k) + ": " + str(v)
                                      for k, v in self._aspects.items() if not k.startswith(FAT_REC)]) + ")"

    def __getitem__(self, key):
        child = self.node_child(key, moan=True)
        ''' should actually not happen because with moan=True node_child() will raise AssertionError
        if child is None:
            raise KeyError("There is no item with the idx_path '{}' in this _Field ({})".format(key, self))
        '''
        return child

    def node_child(self, idx_path, use_curr_idx=None, moan=False, selected_sys_dir=None):
        msg = "node_child() of _Field {} expects ".format(self)
        if isinstance(idx_path, (tuple, list)):
            if len(idx_path) and not isinstance(idx_path[0], IDX_TYPES):
                assert not moan, msg + "str or int in idx_path[0], got {} ({})".format(type(idx_path[0]), idx_path[0])
                return None
        elif not isinstance(idx_path, IDX_TYPES):
            assert not moan, msg + "str or int type in idx_path, but got {} (idx={})".format(type(idx_path), idx_path)
            return None
        else:
            idx_path = field_name_idx_path(idx_path, return_root_fields=True)

        if not idx_path:
            assert not moan, msg + "non-empty tuple or list or index string in idx_path {}".format(idx_path)
            return None

        value = self.aspect_value(FAT_VAL)
        if not isinstance(value, VALUE_TYPES):
            assert not moan, msg + " value types {} but got {}".format(VALUE_TYPES, type(value))
            return None

        return value.node_child(idx_path, use_curr_idx=use_curr_idx, moan=moan, selected_sys_dir=selected_sys_dir)

    def value(self, *idx_path, system='', direction='', flex_sys_dir=False):
        value = None
        val_or_cal = self.aspect_value(FAT_VAL, FAT_CAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        if val_or_cal is not None:
            if callable(val_or_cal):
                value = val_or_cal(self)
                if value is not None and not isinstance(value, VALUE_TYPES):
                    value = Value((value, ))
            else:
                value = val_or_cal
        assert not flex_sys_dir and value is None or isinstance(value, VALUE_TYPES), \
            "_Field.value({}, {}, {}, {}): value '{}'/'{}' has to be of type {}"\
            .format(idx_path, system, direction, flex_sys_dir, val_or_cal, value, VALUE_TYPES)
        if value and len(idx_path) > 0:
            value = value.value(*idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        return value

    def set_value(self, value, *idx_path, system='', direction='', protect=False, root_rec=None, root_idx=(),
                  use_curr_idx=None):
        msg = "_Field.set_value({}, {}, {}, {}, {}): ".format(value, idx_path, system, direction, protect)
        assert isinstance(value, VALUE_TYPES), msg + "expects value types {}, got {}".format(VALUE_TYPES, type(value))

        if isinstance(value, NODE_TYPES) and not idx_path and (system != '' or direction != ''):
            fld_sys = fld_dir = ''
        else:
            fld_sys, fld_dir = system, direction

        root_rec, root_idx = use_rec_default_root_rec_idx(self.root_rec(system=fld_sys, direction=fld_dir), root_rec,
                                                          idx=self.root_idx(system=fld_sys, direction=fld_dir),
                                                          root_idx=root_idx,
                                                          met=msg)
        assert root_rec is not None and root_idx, msg + "root Record {} or index {} missing".format(root_rec, root_idx)

        key = aspect_key(FAT_VAL, system=fld_sys, direction=fld_dir)

        if not idx_path:
            assert not protect or key not in self._aspects, \
                msg + "value key {} already exists as aspect ({})".format(key, self._aspects[key])
            self._aspects[key] = value
            self.set_env(system=system, direction=direction, root_rec=root_rec, root_idx=root_idx)
        else:
            self._aspects[key].set_value(value, *idx_path, system=system, direction=direction, protect=protect,
                                         root_rec=root_rec, root_idx=root_idx, use_curr_idx=use_curr_idx)

        return self

    def val(self, *idx_path, system='', direction='', flex_sys_dir=True, use_curr_idx=None, **kwargs):
        value = self.value(system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        return value.val(*idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir,
                         use_curr_idx=use_curr_idx, **kwargs)

    def set_val(self, val, *idx_path, system='', direction='', flex_sys_dir=True,
                protect=False, extend=True, converter=None, root_rec=None, root_idx=(), use_curr_idx=None,
                to_value_type=False):
        idx_len = len(idx_path)
        value = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir or idx_len)

        if idx_len == 0:
            if converter:   # create system value if converter is specified and on leaf idx_path item
                self.set_converter(converter, system=system, direction=direction, extend=extend,
                                   root_rec=root_rec, root_idx=root_idx)
                value = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)

            val_is_value = isinstance(val, VALUE_TYPES)
            if val_is_value \
                    or isinstance(val, (list, dict)) and to_value_type \
                    or value is None \
                    or not isinstance(value, Value):
                assert extend and not protect, "_Field.set_val({}): value {} exists - pass extend={}/protect={}" \
                                .format(val, value, extend, protect)
                value = val if val_is_value \
                    else (Record() if isinstance(val, dict)
                          else ((Records() if isinstance(val[0], dict) else Values()) if isinstance(val, list)
                                else Value())
                          )
                self.set_value(value, system=system, direction=direction,
                               protect=protect, root_rec=root_rec, root_idx=root_idx)
            self.set_env(system=system, direction=direction, root_rec=root_rec, root_idx=root_idx)

            if val_is_value:
                return self             # RETURN

        elif isinstance(value, (Value, type(None))):
            assert extend and not protect, "_Field.set_val({}, {}): value {} exists - change extend={}/protect={}" \
                .format(val, idx_path, value, extend, protect)
            value = Record() if isinstance(idx_path[0], str) \
                else (Records() if idx_len > 1 or isinstance(val, dict) else Values())
            init_current_index(value, idx_path, use_curr_idx)
            self.set_value(value, protect=protect, root_rec=root_rec, root_idx=root_idx)

        value.set_val(val, *idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir,
                      protect=protect, extend=extend, converter=converter, root_rec=root_rec, root_idx=root_idx,
                      use_curr_idx=use_curr_idx)
        return self

    def leaf_value(self, system='', direction='', flex_sys_dir=False):
        # return field node value for to allow the caller to check if possibly exists a deeper located sys field
        value = self.value(system=system, direction=direction, flex_sys_dir=True)
        if not flex_sys_dir and not isinstance(value, NODE_TYPES) \
                and not self.aspect_value(FAT_IDX, system=system, direction=direction, flex_sys_dir=flex_sys_dir):
            value = None
        return value

    def leafs(self, system='', direction='', flex_sys_dir=True):
        value = self.leaf_value(system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        if isinstance(value, NODE_TYPES):
            yield from value.leafs(system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        elif value is not None:
            yield self

    def leaf_indexes(self, *idx_path, system='', direction='', flex_sys_dir=True):
        value = self.leaf_value(system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        if isinstance(value, NODE_TYPES):
            yield from value.leaf_indexes(*idx_path, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        elif value is not None:
            yield idx_path

    def find_aspect_key(self, *aspect_types, system='', direction=''):
        keys = list()
        if direction and system:
            for aspect_type in aspect_types:
                keys.append(aspect_key(aspect_type, system=system, direction=direction))
        else:
            assert not direction, "_Field.find_aspect_key({}, {}, {}) direction without system not allowed" \
                .format(aspect_types, system, direction)
            if system:
                for aspect_type in aspect_types:
                    for d in (FAD_ONTO, FAD_FROM):
                        keys.append(aspect_key(aspect_type, system=system, direction=d))
        if system:
            for aspect_type in aspect_types:
                keys.append(aspect_key(aspect_type, system=system))
        for aspect_type in aspect_types:
            keys.append(aspect_key(aspect_type))

        for key in keys:
            if key in self._aspects:
                return key

        return None

    def set_env(self, system='', direction='', root_rec=None, root_idx=None):
        # we cannot use self.value() for calculator fields because the rec structure might not be complete
        # value = self.value(system=system, direction=direction, flex_sys_dir=True)
        value = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=True)
        if isinstance(value, NODE_TYPES):
            value.set_env(system=system, direction=direction, root_rec=root_rec, root_idx=root_idx)
        else:
            self.set_system_root_rec_idx(system=system, direction=direction, root_rec=root_rec, root_idx=root_idx)
        return self

    def set_system_root_rec_idx(self, system=None, direction=None, root_rec=None, root_idx=None):
        root_rec, root_idx = use_rec_default_root_rec_idx(self.root_rec(), root_rec,
                                                          idx=self.root_idx(), root_idx=root_idx,
                                                          met="_Field.set_system_root_rec")
        system, direction = use_rec_default_sys_dir(root_rec, system, direction)

        self.set_root_rec(root_rec, system=system, direction=direction)
        if FAT_REC not in self._aspects or system or direction:
            self.set_root_rec(root_rec)     # ensure also root_rec for main/non-sys field value

        if root_idx:
            self.set_root_idx(root_idx, system=system, direction=direction)
            if FAT_RCX not in self._aspects or system or direction:
                self.set_root_idx(root_idx)

        return self

    def aspect_exists(self, *aspect_types, system='', direction='', flex_sys_dir=False):
        if flex_sys_dir:
            key = self.find_aspect_key(*aspect_types, system=system, direction=direction)
        else:
            for aspect_type in aspect_types:
                key = aspect_key(aspect_type, system=system, direction=direction)
                if key in self._aspects:
                    break
            else:
                key = None
        return key

    def aspect_value(self, *aspect_types, system='', direction='', flex_sys_dir=False):
        key = self.aspect_exists(*aspect_types, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        if key:
            val = self._aspects.get(key)
        else:
            val = None
        return val

    def set_aspect(self, aspect_value, type_or_key, system='', direction='', protect=False, allow_values=False):
        key = aspect_key(type_or_key, system=system, direction=direction)
        msg = "_Field.set_aspect({}, {}, {}, {}, {}, {}): ".format(
            aspect_value, type_or_key, system, direction, protect, allow_values)
        assert not protect or key not in self._aspects, \
            msg + "{} already exists as {}, pass protect=True to overwrite".format(key, self._aspects[key])
        assert allow_values or not key.startswith(FAT_VAL), \
            msg + "pass allow_values=True or set values of _Field instances with the methods set_value() or set_val()"

        if aspect_value is None:
            self.del_aspect(key)
        else:
            assert key != FAT_IDX or isinstance(aspect_value, (tuple, list)) or not field_name_idx_path(aspect_value), \
                msg + "digits cannot be used in system-less/generic field name '{}'".format(aspect_value)
            self._aspects[key] = aspect_value
        return self

    def del_aspect(self, type_or_key, system='', direction=''):
        key = aspect_key(type_or_key, system=system, direction=direction)
        assert key not in (FAT_IDX, FAT_REC, FAT_RCX), "_Field main name and root Record/index cannot be removed"
        assert key != FAT_VAL or FAT_CAL in self._aspects, "_Field main value only deletable when calculator exists"
        return self._aspects.pop(key)

    def set_aspects(self, allow_values=False, **aspects):
        for key, data in aspects.items():
            if key.endswith(CALLABLE_SUFFIX):
                assert callable(data), "_Field.set_aspects() expects callable for aspect {} with the {}-suffix"\
                    .format(key, CALLABLE_SUFFIX)
                key = key[:-len(CALLABLE_SUFFIX)]
                data = data(self)
            self.set_aspect(data, key, allow_values=allow_values)
        return self

    def add_aspects(self, allow_values=False, **aspects):
        for key, data in aspects.items():
            # adding any other aspect to instance aspects w/o system/direction from kwargs
            self.set_aspect(data, key, protect=True, allow_values=allow_values)
        return self

    def name(self, system='', direction='', flex_sys_dir=True):
        return self.aspect_value(FAT_IDX, system=system, direction=direction, flex_sys_dir=flex_sys_dir)

    def del_name(self, system='', direction=''):
        assert system, "_Field.del_name() expects to pass at least a non-empty system"
        self.del_aspect(FAT_IDX, system=system, direction=direction)
        return self

    def has_name(self, name, selected_sys_dir=None):
        for asp_key, asp_val in self._aspects.items():
            if asp_key.startswith(FAT_IDX) and asp_val == name:
                if selected_sys_dir is not None:
                    selected_sys_dir['system'] = aspect_key_system(asp_key)
                    selected_sys_dir['direction'] = aspect_key_direction(asp_key)
                return asp_key

    def set_name(self, name, system='', direction='', protect=False):
        self.set_aspect(name, FAT_IDX, system=system, direction=direction, protect=protect)
        if system:
            root_idx = self.root_idx(system=system, direction=direction)
            if root_idx and root_idx[-1] != name:
                self.set_root_idx(root_idx[:-1] + (name, ), system=system, direction=direction)
        return self

    def root_rec(self, system='', direction='') -> Optional[Record]:
        return self.aspect_value(FAT_REC, system=system, direction=direction, flex_sys_dir=True)

    def set_root_rec(self, rec, system='', direction=''):
        self.set_aspect(rec, FAT_REC, system=system, direction=direction)
        return self

    def root_idx(self, system='', direction='') -> tuple:
        return self.aspect_value(FAT_RCX, system=system, direction=direction, flex_sys_dir=True)

    def set_root_idx(self, idx_path, system='', direction=''):
        self.set_aspect(idx_path, FAT_RCX, system=system, direction=direction)
        return self

    def calculator(self, system='', direction=''):
        return self.aspect_value(FAT_CAL, system=system, direction=direction)

    def set_calculator(self, calculator, system='', direction='', protect=False):
        self.set_aspect(calculator, FAT_CAL, system=system, direction=direction, protect=protect)
        if aspect_key(FAT_VAL, system=system, direction=direction) in self._aspects:
            self.del_aspect(FAT_VAL, system=system, direction=direction)
        return self

    def clear_val(self, system='', direction=''):
        return self.aspect_value(FAT_CLEAR_VAL, system=system, direction=direction)

    def set_clear_val(self, val, system='', direction=''):
        return self.set_aspect(val, FAT_CLEAR_VAL, system=system, direction=direction)

    def _ensure_system_value(self, system, direction='', root_rec=None, root_idx=()):
        if not self.aspect_exists(FAT_VAL, system=system, direction=direction):
            self.set_value(Value(), system=system, direction=direction, root_rec=root_rec, root_idx=root_idx)

    def converter(self, system='', direction=''):
        return self.aspect_value(FAT_CNV, system=system, direction=direction)

    def set_converter(self, converter, system='', direction='', extend=False, root_rec=None, root_idx=()):
        assert system != '', "_Field converter can only be set for a given/non-empty system"
        self._ensure_system_value(system, direction=direction, root_rec=root_rec, root_idx=root_idx)
        return self.set_aspect(converter, FAT_CNV, system=system, direction=direction, protect=not extend)

    def convert(self, val, system, direction):
        converter = self.converter(system=system, direction=direction)
        if converter:
            assert callable(converter), "converter of Field {} for {}{} is not callable".format(self, direction, system)
            val = converter(self, val)
        return val

    def filter(self, system='', direction=''):
        return self.aspect_value(FAT_FLT, system=system, direction=direction)

    def set_filter(self, filter_fields, system='', direction='', protect=False):
        return self.set_aspect(filter_fields, FAT_FLT, system=system, direction=direction, protect=protect)

    def sql_expression(self, system='', direction=''):
        return self.aspect_value(FAT_SQE, system=system, direction=direction)

    def set_sql_expression(self, sql_expression, system='', direction='', protect=False):
        return self.set_aspect(sql_expression, FAT_SQE, system=system, direction=direction, protect=protect)

    def validator(self, system='', direction=''):
        return self.aspect_value(FAT_CHK, system=system, direction=direction)

    def set_validator(self, validator, system='', direction='', protect=False, root_rec=None, root_idx=()):
        assert callable(validator), "validator of Field {} for {}{} has to be callable".format(self, direction, system)
        self._ensure_system_value(system, direction=direction, root_rec=root_rec, root_idx=root_idx)
        return self.set_aspect(validator, FAT_CHK, system=system, direction=direction, protect=protect)

    def validate(self, val, system='', direction=''):
        validator = self.validator(system=system, direction=direction)
        return not callable(validator) or validator(self, val)

    def append_record(self, system='', direction='', flex_sys_dir=True, root_rec=None, root_idx=()):
        value = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
        assert isinstance(value, Records), "append_record() expects Records type but got {}".format(type(value))
        root_rec, root_idx = use_rec_default_root_rec_idx(self.root_rec(system=system, direction=direction), root_rec,
                                                          idx=self.root_idx(system=system, direction=direction),
                                                          root_idx=root_idx,
                                                          met="_Fields.append_record")
        return value.append_record(root_rec=root_rec, root_idx=root_idx)

    def clear_leafs(self, system='', direction='', flex_sys_dir=True, reset_lists=True):
        """ clear/reset field values and if reset_lists == True also Records/Values lists to one item.

        :param system:          system of the field value to clear, pass None for to clear all field values.
        :param direction:       direction of the field value to clear.
        :param flex_sys_dir:    if True then also clear field value if system is given and field has no system value.
        :param reset_lists:     if True/def then also clear Records/lists to one item.
        :return:                self (this _Field instance).
        """
        def _clr_val(_sys, _dir, _fsd):
            asp_val.clear_leafs(system=_sys, direction=_dir, flex_sys_dir=_fsd, reset_lists=reset_lists)
            clr_val = self.clear_val(system=_sys, direction=_dir)
            if clr_val is not None:
                self.set_val(clr_val, system=_sys, direction=_dir, flex_sys_dir=False)
                init_sys_dir.append((_sys, _dir))

        init_sys_dir = list()
        if system is None and direction is None:
            for asp_key, asp_val in self._aspects.items():
                if asp_key.startswith(FAT_VAL):
                    _clr_val(aspect_key_system(asp_key), aspect_key_direction(asp_key), False)
        else:
            asp_val = self.aspect_value(FAT_VAL, system=system, direction=direction, flex_sys_dir=flex_sys_dir)
            if asp_val is not None:
                _clr_val(system, direction, flex_sys_dir)

        # finally set clear val for field value if field has no explicit value for the system of the clear val
        for asp_key, asp_val in self._aspects.items():
            if asp_key.startswith(FAT_CLEAR_VAL):
                system = aspect_key_system(asp_key)
                direction = aspect_key_direction(asp_key)
                if (system, direction) not in init_sys_dir:
                    self.set_val(asp_val, flex_sys_dir=False)

        return self

    def copy(self, deepness=0, root_rec=None, root_idx=(), **kwargs):
        """ copy the aspects (names, indexes, values, ...) of this field.

        :param deepness:        deep copy level: <0==see deeper(), 0==only copy current instance, >0==deep copy
                                to deepness value - _Field occupies two deepness: 1st=_Field, 2nd=Value).
        :param root_rec:        destination root record.
        :param root_idx:        destination index path (tuple of field names and/or list/Records/Values indexes).
        :param kwargs:          additional arguments (will be passed on - most of them used by Record.copy).
        :return:                new/extended record instance.
        """
        aspects = self._aspects
        if deepness:
            copied = dict()
            for asp_key, asp_val in aspects.items():  # type: (str, Any)
                if asp_key.startswith(FAT_VAL) and deeper(deepness, asp_val):
                    # FAT_VAL.asp_val is field value of VALUE_TYPES (Value, Records, ...)
                    copied[asp_key] = asp_val.copy(deepness=deeper(deepness, asp_val),
                                                   root_rec=root_rec, root_idx=root_idx, **kwargs)
                elif asp_key not in (FAT_REC, FAT_RCX):
                    copied[asp_key] = asp_val
            aspects = copied
        return _Field(root_rec=root_rec, root_idx=root_idx, allow_values=True, **aspects)

    def pull(self, from_system, root_rec, root_idx):
        assert from_system, "_Field.pull() with empty value in from_system is not allowed"
        direction = FAD_FROM

        val = self.val(system=from_system, direction=direction)
        if val is None:
            val = ''
        if self.validate(val, from_system, direction):
            val = self.convert(val, from_system, direction)
            if val is not None:
                self.set_val(val, root_rec=root_rec, root_idx=root_idx)

        return self

    def push(self, onto_system, root_rec, root_idx):
        assert onto_system, "_Field.push() with empty value in onto_system is not allowed"
        direction = FAD_ONTO

        val = self.val()
        if val is None:
            val = ''
        val = self.convert(val, onto_system, direction)
        if val is not None and self.validate(val, onto_system, direction):
            self.set_val(val, system=onto_system, direction=direction, root_rec=root_rec, root_idx=root_idx)

        return self

    def string_to_records(self, str_val, field_names, rec_sep=',', fld_sep='=', system='', direction=''):
        fld_root_rec = self.root_rec(system=system, direction=direction)
        fld_root_idx = self.root_idx(system=system, direction=direction)

        return string_to_records(str_val, field_names, rec_sep=rec_sep, fld_sep=fld_sep,
                                 root_rec=fld_root_rec, root_idx=fld_root_idx)

    def record_field_val(self, *idx_path, system='', direction=''):
        root_rec = self.root_rec(system=system, direction=direction)
        assert root_rec and idx_path, "rfv() expects non-empty root_rec {} and idx_path {}".format(root_rec, idx_path)
        val = root_rec.val(*idx_path, system=system, direction=direction)
        return val

    rfv = record_field_val

    def system_record_val(self, *idx_path, system='', direction='', use_curr_idx=None):
        root_rec = self.root_rec(system=system, direction=direction)
        assert root_rec, "srv() expects existing root_rec for system {} and direction {}".format(system, direction)
        if idx_path:
            field = root_rec.node_child(idx_path, use_curr_idx=use_curr_idx)
        else:
            field = self
        val = field.val(system=root_rec.system, direction=root_rec.direction) if field else None
        return val

    srv = system_record_val

    def in_actions(self, *actions, system='', direction=''):
        root_rec = self.root_rec(system=system, direction=direction)
        is_in = root_rec and root_rec.action in actions
        return is_in

    ina = in_actions

    def parent(self, system='', direction='', value_types=None):
        root_rec = self.root_rec(system=system, direction=direction)
        root_idx = self.root_idx(system=system, direction=direction)
        while root_rec and root_idx:
            root_idx = root_idx[:-1]
            if root_idx:
                item = root_rec.value(*root_idx, system=system, direction=direction)
                if not value_types or isinstance(item, value_types):
                    return item
        return root_rec if not value_types or isinstance(root_rec, value_types) else None

    def current_records_idx(self, system='', direction=''):
        item = self.parent(system=system, direction=direction, value_types=(Records,))
        if item:
            return current_index(item)

    crx = current_records_idx


# type tuples
VALUE_TYPES = (Value, Values, Record, Records)
NODE_TYPES = (Record, Records)
NODE_CHILD_TYPES = (_Field, Record)
LIST_TYPES = (Values, Records)
IDX_TYPES = (int, str)
