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

    """Precompiled regular expressions."""

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

    """List of regular expressions used in this script."""

    integer = Re(r'(?:\d+)')
    number = Re(r'(?:[+\-]?(?:\d+(?:\.\d*)?|\d*\.\d+)(?:[eE][+\-]?\d+)?)')
    thingy = Re(r'(?:[^\s,;!]+)')
    identifier = Re(r'(?:[a-zA-Z][\w\.]*)')
    string = Re(r'(?:"[^"]*")')
    array = Re(r'(?:\{[^\}]*\})')
    param = Re(r'(?:',string,'|',array,'|',thingy,')')
    cmd = Re(r'^\s*(?:(',identifier,r')\s*:)?\s*(',identifier,r')\s*(,.*)?;\s*$')
    arg = Re(r',\s*(',identifier,r')\s*(:?=)\s*(',param,')')

    comment_split = Re(r'^([^!]*)(!.*)?$')

    is_string = Re(r'^\s*(?:"([^"]*)")\s*$')
    is_identifier = Re(r'^\s*(',identifier,')\s*$')


#----------------------------------------
# Line model + parsing + formatting
#----------------------------------------


def fmtArg(value):
    if isinstance(value, Decimal):
        return '=' + str(value.normalize())
    elif isinstance(value, str):
        return '="%s"' % value
    elif isinstance(value, (float, int)):
        return '=' + str(value)
    elif isinstance(value, (tuple, list)):
        return '={%s}' % ','.join(map(fmtInner, value))
    else:
        return value.fmtArg()


def fmtInner(value):
    if isinstance(value, Decimal):
        return str(value.normalize())
    try:
        return value.fmtInner()
    except AttributeError:
        return str(value)


class Value(object):

    def __init__(self, value, assign='='):
        self.value = value
        self.assign = assign

    def __str__(self):
        return str(self.value)

    def fmtArg(self):
        return self.assign + str(self)

    @classmethod
    def parse(cls, text, assign='='):
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
            raise ValueError("Not a floating point: %s" % text)


@none_checked
def parse_string(text):
    """Used to parse string values."""
    try:
        return regex.is_string.match(str(text)).groups()[0]
    except AttributeError:
        raise ValueError("Invalid string: %s" % (text,))


class Array(Value):

    @classmethod
    def parse(cls, text, assign=False):
        """Parse a MAD-X array."""
        if text[0] != '{':
            raise ValueError("Invalid array: %s" % (text,))
        if text[-1] != '}':
            raise Exception("Array not terminated correctly: %s" % (text,))
        try:
            return cls([Value.parse(field.strip(), assign)
                        for field in text[1:-1].split(',')],
                       assign)
        except ValueError:
            raise Exception("Array not well-formed: %s" % (text,))

    def __str__(self):
        return '{' + ','.join(map(str, self.value)) + '}'


class Symbolic(Value):

    """Base class for identifiers and composed arithmetic expressions."""

    @classmethod
    def parse(cls, text, assign=False):
        try:
            return Identifier.parse(text, assign)
        except:
            return Composed.parse(text, assign)

    def __binop(op):
        return lambda self, other: Composed.create(self, op, other)

    def __rbinop(op):
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
    """Identifier."""
    @classmethod
    def parse(cls, text, assign='='):
        try:
            return cls(regex.is_identifier.match(text).groups()[0], assign)
        except AttributeError:
            raise ValueError("Invalid identifier: %s" % (text,))


class Composed(Symbolic):

    """Composed value."""

    @classmethod
    def parse(cls, text, assign='='):
        return cls(text, assign)

    @classmethod
    def create(cls, a, x, b):
        return Composed('%s %s %s'%(fmtInner(a),x,fmtInner(b)),
                        (getattr(a, 'assign', False) or
                         getattr(b, 'assign', False)))

    def fmtInner(self):
        return '(' + str(self.value) + ')'


def parse_args(text):
    """Parse argument list into ordered dictionary."""
    return odicti((key, Value.parse(val, assign))
                  for key,assign,val in regex.arg.findall(text or ''))


class Element(object):

    """
    Single MAD-X element.
    """

    __slots__ = ['name', 'type', 'args']

    def __init__(self, name, type, args, base=None):
        """
        Initialize an Element object.

        :param str name: name of the element (colon prefix)
        :param str type: command name or element type
        :param dict args: command arguments
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

    def copy(self):
        return self.__class__(self.name, self.type, self.args.copy())

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, val):
        if key in self.__slots__:
            self.__class__.__dict__[key].__set__(self, val)
        else:
            self.args[key] = val

    def __contains__(self, key):
        return key in self.args

    def __delattr__(self, key):
        del self.args[key]

    def __getitem__(self, key):
        try:
            return self.args[key]
        except KeyError:
            if self._base:
                return self._base[key]
            raise

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, *default):
        try:
            return self.args.pop(key)
        except KeyError:
            try:
                return self._base[key]
            except (KeyError, TypeError):
                if default:
                    return default[0]
                raise

    def __str__(self):
        """Output element in MAD-X format."""
        def _fmt_arg(k, v):
            return ', %s' % k if v is None else ', %s%s' % (k,fmtArg(v))
        return '%s%s%s;' % ('%s: ' % self.name if self.name else '',
                            self.type,
                            ''.join(_fmt_arg(k, v)
                                    for k,v in self.args.items()))

    def __eq__(self, other):
        return (self.name == other.name and
                self.type == other.type and
                self.args == other.args)


class Text(str):
    type = None


class Sequence(object):

    """MAD-X sequence."""

    def __init__(self, seq, opt=None, name=None):
        self.name = name
        self.opt = opt
        self.seq = seq

    def __str__(self):
        """Format sequence to MAD-X format."""
        return '\n'.join(map(str, (self.opt or []) + self.seq))

    @classmethod
    def detect(cls, elements):
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

    """Transform sequence."""

    offsets = dicti(entry=0, centre=Decimal(1)/2, exit=1)

    def __init__(self, slicing):
        # create slicer
        self.transforms = [ElementTransform(s) for s in slicing] + []
        self.transforms.append(ElementTransform({}))

    def __call__(self, node, defs):
        if isinstance(node, (Element, Sequence)):
            defs[node.name] = node

        if not isinstance(node, Sequence):
            return node
        seq = node
        first = seq.seq[0]
        last = seq.seq[-1]

        refer = self.offsets[str(first.get('refer', 'centre'))]

        def transform(elem, offset):
            if elem.type:
                elem._base = defs.get(elem.type)
            for t in self.transforms:
                if t.match(elem):
                    return t.replace(elem, offset, refer)

        templates = []      # predefined element templates
        elements = []       # actual elements to put in sequence
        position = 0        # current element position

        for elem in seq.seq[1:-1]:
            if elem.type:
                optic, elem, elem_len = transform(elem, position)
                templates += optic
                elements += elem
                position += elem_len
            else:
                elements.append(elem)
        first.L = position

        if templates:
            templates.insert(0, Text('! Template elements for %s:' % first.get('name')))
            templates.append(Text())

        return Sequence([first] + elements + [last], templates, first.name)


class ElementTransform(object):

    def __init__(self, selector):

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
                optic.L = elem_len / slice_num
                return [optic]
            self._makeoptic = make_optic
            self._stripelem = lambda elem: Element(None, elem.name, {})
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
        elem_len = elem.get('L', 0)
        slice_num = self._get_slice_num(elem_len) or 1
        optic = self._makeoptic(elem, slice_num)
        elem = self._stripelem(elem)
        elems = self._distribution(elem, offset, refer, elem_len, slice_num)
        return optic, elems, elem_len

    def uniform_slice_distribution(self, elem, offset, refer, elem_len, slice_num):
        slice_len = Decimal(elem_len) / slice_num
        scaled = self._rescale(elem, 1/Decimal(slice_num))
        for slice_idx in range(slice_num):
            slice = scaled.copy()
            slice.at = offset + (slice_idx + refer)*slice_len
            yield slice

    def uniform_slice_loop(self, elem, offset, refer, elem_len, slice_num):
        slice_len = elem_len / slice_num
        slice = self._rescale(elem, 1/Decimal(slice_num)).copy()
        slice.at = offset + (Identifier('i', True) + refer) * slice_len
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
    scaled.L = elem.L * ratio
    if scaled.type == 'sbend':
        scaled.angle = scaled.angle * ratio
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
        elem.KNL = [elem.angle * ratio]
        del elem.angle
        del elem.HGAP
    elif elem.type == 'quadrupole':
        elem.KNL = [0, elem.K1 * elem.L]
        del elem.K1
    elif elem.type == 'solenoid':
        elem.ksi = elem.KS * ratio
        elem.lrad = elem.L * ratio
        elem.L = 0
        return
    # set elem_class to multipole
    elem.type = stri('multipole')
    # replace L by LRAD property
    elem.lrad = elem.pop('L', None)
    return elem


def exclusive(mapping, *keys):
    return sum(key in mapping for key in keys) <= 1


#----------------------------------------
# JSON/YAML serialization
#----------------------------------------

def _adjust_element(elem):
    if not elem.type:
        return ()
    return odicti([('name', elem.name),
                   ('type', elem.type)] +
                  [(k,v) for k,v in elem.args.items() if v is not None]),


class Json(object):

    def __init__(self):
        import json
        self.json = json

    def dump(self, data, stream):

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

        self.json.dump(data, stream,
                       indent=2,
                       separators=(',', ' : '),
                       cls=ValueEncoder)


class Yaml(object):

    def __init__(self):
        import yaml
        import pydicti
        self.yaml = yaml
        self.dict = pydicti.odicti

    def dump(self, data, stream=None):
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
        Dumper.add_representer(Decimal, _Decimal_representer)
        return yaml.dump(data, stream, Dumper, default_flow_style=False)

    def load(self, stream):
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

    def __init__(self, nodes):
        self._nodes = list(nodes)
        # TODO: lookup table for template elements

    def transform(self, node_transform):
        return Document(node_transform(node, self, dicti())
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

    def _getstate(self, output_data):
        return odicti(
            (seq.name, odicti(
                list(seq.seq[0].args.items()) +
                [('elements', list(chain.from_iterable(map(_adjust_element,
                                                           seq.seq[1:-1])))),]
            ))
            for seq in self._nodes
            if isinstance(seq, Sequence))

    def dump(self, stream, fmt='madx'):
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
