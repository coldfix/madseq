#! /usr/bin/env python
"""
madseq - MAD-X sequence parser/transformer.

Usage:
    madseq.py [-j|-y] [-s <slice>] [<input>] [<output>]
    madseq.py (--help | --version)

Options:
    -j, --json                      Use JSON as output format
    -y, --yaml                      Use YAML as output format
    -s <slice>, --slice=<slice>     Set slicing definition file
    -h, --help                      Show this help
    -v, --version                   Show version information

Madseq is a MAD-X sequence parser and transformation utility. If called with
only a MAD-X input file, it will look for SEQUENCE..ENDSEQUENCE sections in
the file and update the AT=.. values of all elements.
"""

# enforce float division
from __future__ import division

# standard library
from itertools import chain
from functools import partial
import re
from math import ceil
from decimal import Decimal, InvalidOperation

# 3rd-party
from pydicti import odicti, dicti


#----------------------------------------
# meta data
#----------------------------------------

__version__ = 'madseq 0.3.1'

__all__ = [
    'Element', 'Sequence', 'Document',
    'main'
]


#----------------------------------------
# Utilities
#----------------------------------------

def none_checked(type):
    """Create a simple ``None``-checked constructor."""
    def constructor(value):
        return None if value is None else type(value)
    constructor.cls = type
    return constructor


@none_checked
class stri(str):
    """Case insensitive string."""
    def __eq__(self, other):
        return self.lower() == str(other).lower()
    def __ne__(self, other):
        return not (self == other)


class Re(object):

    """
    Precompiled regular expressions that remembers the expression string.

    Inherits from :class:`re.SRE_Pattern` by delegation.

    :ivar str s: string expression
    :ivar SRE_Pattern r: compiled regex
    """

    def __init__(self, *args):
        """Concat the arguments."""
        self.s = ''.join(map(str, args))
        self.r = re.compile(self.s)

    def __str__(self):
        """Return the expression that was used to create the regex."""
        return self.s

    def __getattr__(self, key):
        """Delegate attribute access to the precompiled regex."""
        return getattr(self.r, key)


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

    #----------------------------------------
    # grouping expressions
    #----------------------------------------

    # match single parameter=value argument and create groups:
    # (argument, assignment, value)
    arg = Re(r',\s*(',identifier,r')\s*(:?=)\s*(',param,')')

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
            raise ValueError("Unknown data type: {!r}".format(value))


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
            raise ValueError("Not a floating point: {!r}".format(text))


@none_checked
def parse_string(text):
    """Parse string from quoted expression."""
    try:
        return regex.is_string.match(str(text)).groups()[0]
    except AttributeError:
        raise ValueError("Invalid string: {!r}".format(text))


class Array(Value):

    """
    Corresponds to MAD-X ARRAY type.
    """

    @classmethod
    def parse(cls, text, assign='='):
        """Parse a MAD-X array."""
        text = text.strip()
        if text[0] != '{':
            raise ValueError("Invalid array: {!r}".format(text))
        if text[-1] != '}':
            raise Exception("Ill-formed ARRAY: {!r}".format(text))
        try:
            return cls([Value.parse(field.strip(), assign)
                        for field in text[1:-1].split(',')],
                       assign)
        except ValueError:
            raise Exception("Ill-formed ARRAY: {!r}".format(text))

    @property
    def expr(self):
        return '{' + ','.join(map(str, self.value)) + '}'


class Symbolic(Value):

    """Base class for identifiers and composed arithmetic expressions."""

    @classmethod
    def parse(cls, text, assign=False):
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
            raise ValueError("Invalid identifier: {!r}".format(text))


class Composed(Symbolic):

    """Composed expression."""

    @classmethod
    def parse(cls, text, assign='='):
        """Allows any expression unchecked."""
        return cls(text, assign)

    @classmethod
    def create(cls, a, x, b):
        """Create a composed expression from two other expressions."""
        return Composed(
            ' '.join((format_safe(a), x, format_safe(b))),
            getattr(a, 'assign', False) or getattr(b, 'assign', False))

    @property
    def safe_expr(self):
        """Add braces for use inside another expression."""
        return '(' + self.expr + ')'


def parse_args(text):
    """Parse argument list into ordered dictionary."""
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

    __slots__ = ['name', 'type', 'args',
                 '_base']

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

    # MutableMapping interface:

    def copy(self):
        """Create a copy of this element that can be safely modified."""
        return self.__class__(self.name, self.type, self.args.copy(),
                              self._base)

    def __contains__(self, key):
        """Check whether key exists as argument in self or base."""
        return key in self.args or (self._base and key in self._base)

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

    def __delitem__(self, key):
        """Delete argument in self."""
        del self.args[key]

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


class Text(str):

    """A text section in a MAD-X document."""

    type = None


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
    def detect(cls, elements):
        """
        Filter SEQUENCE..ENDSEQUENCE groups in an element list.

        :param iterable elements:
        :returns: unmodified elements and generated :class:`Sequence` objects
        :rtype: generator
        """
        it = iter(elements)
        for elem in it:
            if elem.type == 'sequence':
                seq = [elem]
                for elem in it:
                    seq.append(elem)
                    if elem.type == 'endsequence':
                        break
                assert(elem.type == 'endsequence')
                yield Sequence(seq)
            else:
                yield elem


#----------------------------------------
# Transformations
#----------------------------------------

class SequenceTransform(object):

    """
    Sequence transformation constituted of Element transformation rules.

    :ivar list _transforms: list of :class:`ElementTransform`s
    :cvar dicti _offsets: associates numeric offset multipliers to offset names
    """

    _offsets = dicti(entry=0, centre=Decimal(1)/2, exit=1)

    def __init__(self, slicing):
        """
        Create transformation rules from the definition list.

        :param list slicing: list of :class:`ElementTransform` definitions
        """
        self._transforms = [ElementTransform(s) for s in slicing] + []
        self._transforms.append(ElementTransform({}))

    def __call__(self, node, defs):

        """
        Transform :class:`Sequence` according to the rule list.

        :param Sequence node: current sequence to transform
        :param dict defs: element lookup table for base elements

        If the ``node`` is not of type :class:`Sequence`, it will be
        returned unchanged, but may still be added to the ``defs`` lookup
        table.
        """

        if isinstance(node, (Element, Sequence)):
            defs[node.name] = node
        if not isinstance(node, Sequence):
            return node

        head = node.head.copy()
        body = node.body
        tail = node.tail

        refer = self._offsets[str(head.get('refer', 'centre'))]

        def transform(elem, offset):
            if elem.type:
                elem._base = defs.get(elem.type)
            for t in self._transforms:
                if t.match(elem):
                    return t.replace(elem, offset, refer)

        templates = []      # predefined element templates
        elements = []       # actual elements to put in sequence
        position = 0        # current element position

        for elem in body:
            if elem.type:
                optic, elem, elem_len = transform(elem, position)
                templates += optic
                elements += elem
                position += elem_len
            else:
                elements.append(elem)
        head['L'] = position

        if templates:
            templates.insert(0, Text('! Template elements for %s:' % head.get('name')))
            templates.append(Text())

        return Sequence([head] + elements + [tail], templates)


class ElementTransform(object):

    """
    Single Element transformation rule.

    :ivar function match:
    :ivar function _get_slice_num:
    :ivar function _rescale:
    :ivar function _makeoptic:
    :ivar function _stripelem:
    :ivar function _distribution:
    """

    def __init__(self, selector):

        """
        Create transformation rule from the serialized definition.

        :param dict selector:
        """

        # matching criterium
        exclusive(selector, 'name', 'type')
        if 'name' in selector:
            name = selector['name']
            self.match = lambda elem: elem.name == name
        elif 'type' in selector:
            type = selector['type']
            self.match = lambda elem: elem.type == type
        else:
            self.match = lambda elem: True

        # number of slices per element
        exclusive(selector, 'density', 'slice')
        if 'density' in selector:
            density = selector['density']
            self._get_slice_num = lambda L: int(ceil(abs(L * density)))
        else:
            slice_num = selector.get('slice', 1)
            self._get_slice_num = lambda L: slice_num

        # rescale elements
        if selector.get('makethin', False):
            self._rescale = rescale_makethin
        else:
            self._rescale = rescale_thick

        # whether to use separate optics
        if selector.get('use_optics', False):
            # TODO: rename optic => template everywhere
            def make_optic(elem, elem_len, slice_num):
                optic = elem.copy()
                optic['L'] = elem_len / slice_num
                return [optic]
            self._makeoptic = make_optic
            self._stripelem = lambda elem: Element(None, elem.name, {}, self)
        else:
            self._makeoptic = lambda elem, slice_num: []
            self._stripelem = lambda elem: elem

        # slice distribution style over element length
        style = selector.get('style', 'uniform')
        if style == 'uniform':
            self._distribution = self.uniform_slice_distribution
        elif style == 'loop':
            self._distribution = self.uniform_slice_loop
        else:
            raise ValueError("Unknown slicing style: {!r}".format(style))

    def replace(self, elem, offset, refer):
        """
        Transform the element at ``offset.

        :param Element elem:
        :param Decimal offset: element entry position
        :param Decimal refer: sequence addressing style
        :returns: template elements, element slices, element length
        :rtype: tuple
        """
        elem_len = elem.get('L', 0)
        slice_num = self._get_slice_num(elem_len) or 1
        optic = self._makeoptic(elem, slice_num)
        elem = self._stripelem(elem)
        elems = self._distribution(elem, offset, refer, elem_len, slice_num)
        return optic, elems, elem_len

    def uniform_slice_distribution(self, elem, offset, refer, elem_len, slice_num):
        """
        Slice an element uniformly into short pieces.

        :param Element elem:
        :param Decimal offset: element entry position
        :param Decimal refer: sequence addressing style
        :param Element elem_len: element length
        :param int slice_num: number of slices
        :returns: element slices
        :rtype: generator
        """
        slice_len = Decimal(elem_len) / slice_num
        scaled = self._rescale(elem, 1/Decimal(slice_num))
        for slice_idx in range(slice_num):
            slice = scaled.copy()
            slice['at'] = offset + (slice_idx + refer)*slice_len
            yield slice

    def uniform_slice_loop(self, elem, offset, refer, elem_len, slice_num):
        """
        Slice an element uniformly into short pieces using a loop construct.

        :param Element elem:
        :param Decimal offset: element entry position
        :param Decimal refer: sequence addressing style
        :param Element elem_len: element length
        :param int slice_num: number of slices
        :returns: element slices
        :rtype: generator
        """
        slice_len = elem_len / slice_num
        slice = self._rescale(elem, 1/Decimal(slice_num)).copy()
        slice['at'] = offset + (Identifier('i', True) + refer) * slice_len
        yield Text('i = 0;')
        yield Text('while (i < %s) {' % slice_num)
        yield slice
        yield Text('i = i + 1;')
        yield Text('}')


def rescale_thick(elem, ratio):
    """Shrink/grow element size, while leaving the element type 'as is'."""
    if ratio == 1:
        return elem
    scaled = elem.copy()
    scaled['L'] = elem['L'] * ratio
    if scaled.type == 'sbend':
        scaled['angle'] = scaled['angle'] * ratio
    return scaled


def rescale_makethin(elem, ratio):
    """
    Shrink/grow element size, while transforming elements to MULTIPOLEs.

    NOTE: rescale_makethin is currently not recommended!  If you use it,
    you have to make sure, your slice length will be sufficiently small!
    """
    if elem.type not in ('sbend', 'quadrupole', 'solenoid'):
        return elem
    elem = elem.copy()
    if elem.type == 'sbend':
        elem['KNL'] = [elem['angle'] * ratio]
        del elem['angle']
        del elem['HGAP']
    elif elem.type == 'quadrupole':
        elem['KNL'] = [0, elem['K1'] * elem['L']]
        del elem['K1']
    elif elem.type == 'solenoid':
        elem['ksi'] = elem['KS'] * ratio
        elem['lrad'] = elem['L'] * ratio
        elem['L'] = 0
        return
    # set elem_class to multipole
    elem.type = stri('multipole')
    # replace L by LRAD property
    elem['lrad'] = elem.pop('L', None)
    return elem


def exclusive(mapping, *keys):
    """Check that at most one of the keys is contained in the mapping."""
    return sum(key in mapping for key in keys) <= 1


#----------------------------------------
# Serialization
#----------------------------------------

class Json(object):

    """JSON serialization utility."""

    def __init__(self):
        """Import json module for later use."""
        import json
        self.json = json

    def dump(self, data, stream):
        """Dump data with types defined in this module."""
        json = self.json
        class fakefloat(float):
            """Used to serialize Decimal.
            See: http://stackoverflow.com/a/8274307/650222"""
            def __init__(self, value):
                self._value = value
            def __repr__(self):
                return str(self._value)
        class ValueEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, Value):
                    return obj.value
                if isinstance(obj, Decimal):
                    return fakefloat(obj.normalize())
                # Let the base class default method raise the TypeError
                return json.JSONEncoder.default(self, obj)
        json.dump(data, stream,
                  indent=2,
                  separators=(',', ' : '),
                  cls=ValueEncoder)


class Yaml(object):

    """YAML serialization utility."""

    def __init__(self):
        """Import yaml module for later use."""
        import yaml
        import pydicti
        self.yaml = yaml
        self.dict = pydicti.odicti

    def dump(self, data, stream=None):
        """Dump data with types defined in this module."""
        yaml = self.yaml
        class Dumper(yaml.SafeDumper):
            pass
        def _dict_representer(dumper, data):
            return dumper.represent_mapping(
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                data.items())
        def _stri_representer(dumper, data):
            return dumper.represent_str(data)
        def _Value_representer(dumper, data):
            return dumper.represent_str(data.value)
        def _Decimal_representer(dumper, data):
            return dumper.represent_scalar(u'tag:yaml.org,2002:float',
                                           str(data).lower())
        Dumper.add_representer(self.dict, _dict_representer)
        Dumper.add_representer(stri.cls, _stri_representer)
        Dumper.add_representer(Symbolic, _Value_representer)
        Dumper.add_representer(Identifier, _Value_representer)
        Dumper.add_representer(Composed, _Value_representer)
        Dumper.add_representer(Array, _Value_representer)
        Dumper.add_representer(Decimal, _Decimal_representer)
        return yaml.dump(data, stream, Dumper, default_flow_style=False)

    def load(self, stream):
        """Load data from, using ordered case insensitive dictionaries."""
        yaml = self.yaml
        class OrderedLoader(yaml.SafeLoader):
            pass
        OrderedLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            lambda loader, node: self.dict(loader.construct_pairs(node)))
        return yaml.load(stream, OrderedLoader)


#----------------------------------------
# main
#----------------------------------------

class Document(list):

    """
    MAD-X document representation.

    :ivar list _nodes: list of Text/Element/Sequence nodes
    """

    def __init__(self, nodes):
        """Store the list of nodes."""
        self._nodes = list(nodes)

    def transform(self, node_transform):
        """Create a new transformed document using the node_transform."""
        defs = dicti()
        return Document(node_transform(node, defs)
                        for node in self._nodes)

    @classmethod
    def parse(cls, lines):
        """Parse sequence from line iteratable."""
        return cls(Sequence.detect(chain.from_iterable(map(cls.parse_line, lines))))

    @classmethod
    def parse_line(cls, line):
        """
        Parse a single-line MAD-X input statement.

        Return an iterable that iterates over parsed elements.

        TODO: Does not support multi-line commands yet!
        """
        code, comment = regex.comment_split.match(line).groups()
        if comment:
            yield Text(comment)
        commands = list(code.strip().split(';'))
        if commands[-1]:
            raise ValueError(
                "Not accepting multi-line commands: %s" % commands[-1])
        for command in commands[:-1]:
            try:
                yield Element.parse(command + ';')
            except AttributeError:
                yield Text(command + ';')
        if len(commands) == 1 and not comment:
            yield Text('')

    def _getstate(self):
        """Get a serializeable state for :class:`Json` and :class:`Yaml`."""
        return odicti(
            (seq.name, odicti(
                list(seq.head.args.items()) +
                [('elements', [elem._getstate()
                               for elem in seq.body
                               if elem.type])]
            ))
            for seq in self._nodes
            if isinstance(seq, Sequence))

    def dump(self, stream, fmt='madx'):
        """
        Serialize to the stream.

        :param stream: file object
        :param str fmt: either 'madx', 'yaml' or 'json'
        """
        if fmt == 'json':
            Json().dump(self._getstate(), stream)
        elif fmt == 'yaml':
            Yaml().dump(self._getstate(), stream)
        elif fmt == 'madx':
            stream.write("\n".join(map(str, self._nodes)))
        else:
            raise ValueError("Invalid format code: {!r}".format(fmt))


def main(argv=None):

    # parse command line options
    from docopt import docopt
    args = docopt(__doc__, argv, version=__version__)

    # perform input
    if args['<input>'] and args['<input>'] != '-':
        with open(args['<input>'], 'rt') as f:
            input_file = list(f)
    else:
        from sys import stdin as input_file

    # open output stream
    if args['<output>'] and args['<output>'] != '-':
        output_file = open(args['<output>'], 'wt')
    else:
        from sys import stdout as output_file

    # get slicing definition
    if args['--slice']:
        with open(args['--slice']) as f:
            transforms_doc = Yaml().load(f)
    else:
        transforms_doc = []
    node_transform = SequenceTransform(transforms_doc)

    # output format
    if args['--json']:
        fmt = 'json'
    elif args['--yaml']:
        fmt = 'yaml'
    else:
        fmt = 'madx'

    # one line to do it all:
    Document.parse(input_file).transform(node_transform).dump(output_file, fmt)
main.__doc__ = __doc__


if __name__ == '__main__':
    main()
