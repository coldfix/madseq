from __future__ import absolute_import
from __future__ import division

from decimal import Decimal, InvalidOperation

from madseq.util import Re, stri, dicti, odicti, none_checked


class regex(object):

    """List of various regular expressions used for parsing MAD-X files."""

    #----------------------------------------
    # non-grouping expressions:
    #----------------------------------------

    # numeric int/float expression
    number = Re(r'(?:[+\-]?(?:\d+(?:\.\d*)?|\d*\.\d+)(?:[eE][+\-]?\d+)?)')

    # plain word identifier
    identifier = Re(r'(?:[a-zA-Z][\w\.]*)')

    # string with enclosing quotes: "..."
    string = Re(r'(?:"[^"]*")')

    # MAD-X array type with enclosing curly braces: {...}
    array = Re(r'(?:\{[^\}]*\})')

    # non-standard type parameter. this expression is very free-form to
    # allow arbitrary arithmetic expressions, etc.
    thingy = Re(r'(?:[^\s,;!]+)')

    # any of the above parameters
    param = Re(r'(?:',string,'|',array,'|',thingy,')')

    # MAD-X command: name: type, *args;
    cmd = Re(r'^\s*(?:(',identifier,r')\s*:)?\s*(',identifier,r')\s*(,.*)?;\s*$')

    # MAD-X `LINE` statement:
    line = Re(r'^\s*(?:(',identifier,r')\s*:)?\s*LINE\s*=\s*\(([^()]*)\)\s*;\s*$')

    #----------------------------------------
    # grouping expressions
    #----------------------------------------

    # match single parameter=value argument and create groups:
    # (argument, assignment, value)
    arg = Re(r',\s*(',identifier,r')\s*(:?=)\s*(',param,')\s*')

    # match TEXT!COMMENT and return both parts as groups
    comment_split = Re(r'^([^!]*)(!.*)?$')

    # match+group a string inside quotes
    is_string = Re(r'^\s*(?:"([^"]*)")\s*$')

    # match+group an identifier
    is_identifier = Re(r'^\s*(',identifier,')\s*$')


#----------------------------------------
# Line model + parsing + formatting
#----------------------------------------

def format_argument(key, value):
    """Format value for MAD-X output including the assignment symbol."""
    try:
        return key + value.argument
    except AttributeError:
        if value is None:
            return key
        return key + '=' + format_value(value)


def format_value(value):
    """Format value for MAD-X output."""
    try:
        return value.expr
    except AttributeError:
        if isinstance(value, Decimal):
            return str(value.normalize())
        elif isinstance(value, str):
            return '"' + value + '"'
        elif isinstance(value, (float, int)):
            return str(value)
        elif isinstance(value, (tuple, list)):
            return '{' + ','.join(map(format_value, value)) + '}'
        else:
            raise TypeError("Unknown data type: {0!r}".format(value))


def format_safe(value):
    """
    Format as safe token in a arithmetic expression.

    This adds braces for composed expressions. For atomic types it is the
    same as :func:`format_value`.
    """
    try:
        return value.safe_expr
    except AttributeError:
        return format_value(value)


class Value(object):

    """
    Base class for some types parsed from MAD-X input parameters.

    :ivar value: Actual value. Type depends on the concrete derived class.
    :ivar str _assign: Assignment symbol, either ':=' or '='
    """

    def __init__(self, value, assign='='):
        """Initialize value."""
        self.value = value
        self._assign = assign

    @property
    def argument(self):
        """Format for MAD-X output including assignment symbol"""
        return self._assign + self.expr

    @property
    def expr(self):
        """Get value as string."""
        return str(self.value)

    @property
    def safe_expr(self):
        """Get string that can safely occur inside an arithmetic expression."""
        return self.expr

    def __str__(self):
        """Return formatted value."""
        return self.expr

    def __eq__(self, other):
        """Compare the value."""
        return other == self.value

    @classmethod
    def parse(cls, text, assign='='):
        """Parse MAD-X parameter input as any of the known Value types."""
        try:
            return parse_number(text)
        except ValueError:
            try:
                return parse_string(text)
            except ValueError:
                try:
                    return Array.parse(text, assign)
                except ValueError:
                    return Symbolic.parse(text, assign)


def parse_number(text):
    """Parse numeric value as :class:`int` or :class:`Decimal`."""
    try:
        return int(text)
    except ValueError:
        try:
            return Decimal(text)
        except InvalidOperation:
            raise ValueError("Not a floating point: {0!r}".format(text))


@none_checked
def parse_string(text):
    """Parse string from quoted expression."""
    try:
        return regex.is_string.match(str(text)).groups()[0]
    except AttributeError:
        raise ValueError("Invalid string: {0!r}".format(text))


class Array(Value):

    """
    Corresponds to MAD-X ARRAY type.
    """

    @classmethod
    def parse(cls, text, assign='='):
        """Parse a MAD-X array."""
        text = text.strip()
        if text[0] != '{':
            raise ValueError("Invalid array: {0!r}".format(text))
        if text[-1] != '}':
            raise Exception("Ill-formed ARRAY: {0!r}".format(text))
        try:
            return cls([Value.parse(field.strip(), assign)
                        for field in text[1:-1].split(',')],
                       assign)
        except ValueError:
            raise Exception("Ill-formed ARRAY: {0!r}".format(text))

    @property
    def expr(self):
        return '{' + ','.join(map(str, self.value)) + '}'


class Symbolic(Value):

    """Base class for identifiers and composed arithmetic expressions."""

    @classmethod
    def parse(cls, text, assign='='):
        """Parse either a :class:`Identifier` or a :class:`Composed`."""
        try:
            return Identifier.parse(text, assign)
        except:
            return Composed.parse(text, assign)

    def __binop(op):
        """Internal utility to make a binary operator."""
        return lambda self, other: Composed.create(self, op, other)

    def __rbinop(op):
        """Internal utility to make a binary right hand side operator."""
        return lambda self, other: Composed.create(other, op, self)

    __add__ = __binop('+')
    __sub__ = __binop('-')
    __mul__ = __binop('*')
    __truediv__ = __binop('/')
    __div__ = __truediv__

    __radd__ = __rbinop('+')
    __rsub__ = __rbinop('-')
    __rmul__ = __rbinop('*')
    __rtruediv__ = __rbinop('/')
    __rdiv__ = __rtruediv__


class Identifier(Symbolic):

    """Plain word identifier such as a variable name."""

    @classmethod
    def parse(cls, text, assign='='):
        """Parse identifier."""
        try:
            return cls(regex.is_identifier.match(text).groups()[0], assign)
        except AttributeError:
            raise ValueError("Invalid identifier: {0!r}".format(text))


class Composed(Symbolic):

    """Composed expression."""

    @classmethod
    def parse(cls, text, assign='='):
        """Allows any expression unchecked."""
        return cls(text, assign)

    @classmethod
    def create(cls, a, x, b):
        """Create a composed expression from two other expressions."""
        delayed = (getattr(a, 'assign', '=') == ':=' or
                   getattr(b, 'assign', '=') == ':=')
        return Composed(
            ' '.join((format_safe(a), x, format_safe(b))),
            ':=' if delayed else '=')

    @property
    def safe_expr(self):
        """Add braces for use inside another expression."""
        return '(' + self.expr + ')'


def parse_args(text):
    """Parse argument list into ordered dictionary."""
    # TODO: use .split(',') to make expression simpler
    return odicti((key, Value.parse(val, assign))
                  for key,assign,val in regex.arg.findall(text or ''))


class Element(object):

    """
    Single MAD-X element.

    :ivar str name: element name or ``None``
    :ivar str type: element type name
    :ivar odicti args: element arguments
    :ivar _base: base element, if available

    :class:`Element` a :class:`dict`-like interface to access arguments.
    Argument access is defaulted to base elements if available.
    """

    __slots__ = ('name', 'type', 'args', '_base')

    def __init__(self, name, type, args, base=None):
        """
        Initialize an Element object.

        :param str name: name of the element (colon prefix)
        :param str type: command name or element type
        :param dict args: command arguments
        :param base: base element
        """
        self.name = stri(name)
        self.type = stri(type)
        self.args = args
        self._base = base

    @classmethod
    def parse(cls, text):
        """Parse element from MAD-X string."""
        name, type, args = regex.cmd.match(text).groups()
        return Element(name, type, parse_args(args))

    def __str__(self):
        """Format element in MAD-X format."""
        return ''.join((
            self.name + ': ' if self.name else '',
            ', '.join(
                [self.type] +
                [format_argument(k, v) for k,v in self.args.items()]),
            ';'))

    def _getstate(self):
        """Get a serializeable state for :class:`Json` and :class:`Yaml`."""
        return odicti([('name', self.name),
                       ('type', self.type)] + list(self.args.items()))

    @property
    def base_type(self):
        """Return the base type name."""
        if self._base:
            return self._base.base_type
        return self.type

    @property
    def all_args(self):
        """Return merged arguments of self and bases."""
        if self._base:
            args = self._base.all_args
        else:
            args = odicti()
        args.update(self.args)
        return args

    # MutableMapping interface:

    def copy(self):
        """Create a copy of this element that can be safely modified."""
        return self.__class__(self.name, self.type, self.args.copy(),
                              self._base)

    def __contains__(self, key):
        """Check whether key exists as argument in self or base."""
        return key in self.args or (self._base and key in self._base)

    def __delitem__(self, key):
        """Delete argument in self."""
        del self.args[key]

    def __getitem__(self, key):
        """Get argument value from self or base."""
        try:
            return self.args[key]
        except KeyError:
            if self._base:
                return self._base[key]
            raise

    def __setitem__(self, key, val):
        """Set argument value in self."""
        self.args[key] = val

    def get(self, key, default=None):
        """Get argument value or default from self or base."""
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, *default):
        """Get argument value from self, base or default and remove it from self."""
        try:
            return self.args.pop(key)
        except KeyError:
            try:
                return self._base[key]
            except (KeyError, TypeError):
                if default:
                    return default[0]
                raise

    def __eq__(self, other):
        """Check if some other element is the same."""
        return (self.name == other.name and
                self.type == other.type and
                self.args == other.args)


class Line(object):

    def __init__(self, name, elems):
        self.name = name
        self.elems = elems
        self.type = 'line'

    @classmethod
    def parse(cls, text):
        """Parse element from MAD-X string."""
        name, elems = regex.line.match(text).groups()
        return cls(name, [el.strip() for el in elems.split(',')])

    def __str__(self):
        """Format element in MAD-X format."""
        return '{}: LINE=({});'.format(self.name, ','.join(self.elems))


class Text(str):

    """A text section in a MAD-X document."""

    type = None
    name = None


class Sequence(object):

    """
    MAD-X sequence.
    """

    def __init__(self, elements, preface=None):
        self._preface = preface or []
        self._elements = elements

    @property
    def name(self):
        """Get sequence name."""
        return self.head.name

    @property
    def head(self):
        """Get sequence head element (the one with type SEQUENCE)."""
        return self._elements[0]

    @property
    def body(self):
        """Get sequence body (all elements inside)."""
        return self._elements[1:-1]

    @property
    def tail(self):
        """Get sequence tail element (the one with type ENDSEQUENCE)."""
        return self._elements[-1]

    def __str__(self):
        """Format sequence to MAD-X format."""
        return '\n'.join(map(str, self._preface + self._elements))

    @classmethod
    def detect(cls, elements, inline=False):
        """
        Filter SEQUENCE..ENDSEQUENCE groups in an element list.

        :param iterable elements:
        :returns: unmodified elements and generated :class:`Sequence` objects
        :rtype: generator
        """
        elements = list(elements)
        by_name = dicti((str(el.name), el) for el in elements if el.name)
        it = iter(elements)
        for elem in it:
            if elem.type == 'sequence':
                elem.args.setdefault('refer', 'entry')
                seq = [elem]
                for elem in it:
                    seq.append(elem)
                    if elem.type == 'endsequence':
                        break
                assert(elem.type == 'endsequence')
                yield Sequence(seq)
            elif elem.type == 'line':
                seq = [Element(elem.name, 'sequence', {'refer': 'entry'})]
                if inline:
                    seq.extend(by_name[el_name] for el_name in elem.elems)
                else:
                    seq.extend(Element(None, el_name, {}, by_name[el_name])
                               for el_name in elem.elems)
                seq.append(Element(None, 'endsequence', {}))
                yield Sequence(seq)
            else:
                yield elem
