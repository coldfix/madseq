#! /usr/bin/env python
"""
madseq - MAD-X sequence parser/transformer.

Usage:
    madseq.py [-j|-y] [-s <slice>] [-m] [-o <output>] [<input>]
    madseq.py (--help | --version)

Options:
    -o <output>, --output=<output>  Set output file
    -j, --json                      Use JSON as output format
    -y, --yaml                      Use YAML as output format
    -s <slice>, --slice=<slice>     Select slicing
    -m, --makethin                  Apply a MAKETHIN like transformation
    -h, --help                      Show this help
    -v, --version                   Show version information

"""
from __future__ import division

__all__ = [
    'Element', 'Sequence', 'File',
    'main'
]

from pydicti import odicti, dicti
from itertools import chain
from functools import partial
import json
import re
from math import ceil
from copy import copy
import decimal


#----------------------------------------
# utilities
#----------------------------------------
def disp(v):
    print("%s(%s)" % (v.__class__.__name__, v))

def cast(type):
    """
    Create a simple non-checked constructor.

    >>> tostr = cast(str)
    >>> tostr(None) is None
    True
    >>> tostr(2) == '2'
    True
    >>> isinstance(tostr(2), str)
    True

    """
    def constructor(value):
        return None if value is None else type(value)
    constructor.cls = type
    return constructor

@cast
class stri(str):
    """
    String with case insensitive comparison.

    >>> stri("HeLLo") == "helLO" and "HeLLo" == stri("helLO")
    True
    >>> stri("wOrLd") != "WOrld" or "wOrLd" != stri("WOrld")
    False
    >>> stri("HeLLo") == "WOrld" or "HeLLo" == stri("WOrld")
    False
    >>> stri("wOrLd") != "helLO" and "wOrLd" != stri("helLO")
    True
    >>> stri("HEllO wORld")
    HEllO wORld

    """
    def __eq__(self, other):
        return self.lower() == str(other).lower()
    def __ne__(self, other):
        return not (self == other)

class Re(object):
    """
    Precompiled regular expressions.

    >>> r1 = Re('hello')
    >>> r2 = Re(r1, 'world')
    >>> assert(r1.search(' helloworld '))
    >>> assert(not r1.search('yelloworld'))
    >>> assert(r2.match('helloworld anything'))
    >>> assert(not r2.match(' helloworld anything'))

    """
    def __init__(self, *args):
        """Concat the arguments."""
        self.s = ''.join(map(str, args))
        self.r = re.compile(self.s)

    def __str__(self):
        """Display as the expression that was used to create the regex."""
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

    slice_per_m = Re(r'^(',number,r')\/m$')

    is_string = Re(r'^\s*(?:"([^"]*)")\s*$')
    is_identifier = Re(r'^\s*(',identifier,')\s*$')

#----------------------------------------
# Line model + parsing + formatting
#----------------------------------------
class fakefloat(float):
    """Used to serialize decimal.Decimal.
    See: http://stackoverflow.com/a/8274307/650222"""
    def __init__(self, value):
        self._value = value
    def __repr__(self):
        return str(self._value)
class ValueEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Value):
            return obj.value
        if isinstance(obj, decimal.Decimal):
            return fakefloat(obj.normalize())
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def fmtArg(value):
    if isinstance(value, decimal.Decimal):
        return '=' + str(value.normalize())
    elif isinstance(value, str):
        return '="%s"' % value
    elif isinstance(value, (float, int)):
        return '=' + str(value)
    else:
        return value.fmtArg()

def fmtInner(value):
    if isinstance(value, decimal.Decimal):
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
        return self.assign + str(self.value)

    @classmethod
    def parse(cls, text, assign='='):
        try:
            return Number.parse(text)
        except ValueError:
            try:
                return String.parse(text)
            except ValueError:
                return Symbolic.parse(text, assign)

class Number(object):
    """
    Used to parse numberic values.
    """
    @classmethod
    def parse(cls, text):
        """
        Parse numeric value.

        >>> disp(Number.parse('-13'))
        int(-13)
        >>> disp(Number.parse('12.'))
        float(12.0)
        >>> disp(Number.parse('1.2e1'))
        float(12.0)

        """
        try:
            return int(text)
        except ValueError:
            try:
                return decimal.Decimal(text)
            except decimal.InvalidOperation:
                raise ValueError("Not a floating point: %s" % text)

class String(object):
    """Used to parse string values."""
    @classmethod
    def parse(cls, text):
        if text is None:
            return None
        try:
            return regex.is_string.match(str(text)).groups()[0]
        except AttributeError:
            raise ValueError("Invalid string: %s" % (text,))


class Symbolic(Value):
    """
    Symbolic value.

    >>> i = Number.parse('-13')
    >>> f = Number.parse('12.')
    >>> s = Symbolic.parse('pi')

    >>> disp(f + s)
    Composed(12.0 + pi)
    >>> disp(s - f)
    Composed(pi - 12.0)
    >>> disp(i + f * s)
    Composed(-13 + (12.0 * pi))
    >>> disp(s / s)
    Composed(pi / pi)

    """
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
    # TODO: json
    __slots__ = ['name', 'type', 'args', 'slice', 'slice_len', 'slice_num']

    def __init__(self, name, type, args):
        """
        Initialize an Element object.

        :param str name: name of the element (colon prefix)
        :param str type: command name or element type
        :param dict args: command arguments

        """
        self.name = stri(name)
        self.type = stri(type)
        self.args = args

    @classmethod
    def parse(cls, text):
        """
        Parse element from string.

        >>> mad = "name: type, a=97, b=98, c=99, d=100, e=101;"
        >>> el = Element.parse(mad)
        >>> str(mad) == mad
        True
        >>> el.c, el.E
        (99, 101)

        """
        name, type, args = regex.cmd.match(text).groups()
        return Element(name, type, parse_args(args))

    def __getattr__(self, key):
        return self.args[key]

    def __setattr__(self, key, val):
        if key in self.__slots__:
            self.__class__.__dict__[key].__set__(self, val)
        else:
            self.args[key] = val

    def __contains__(self, key):
        return key in self.args

    def __delattr__(self, key):
        del self.args[key]

    def get(self, key, default=None):
        return self.args.get(key, default)

    def pop(self, key, *default):
        return self.args.pop(key, *default)

    def __str__(self):
        """
        Output element in MAD-X format.

        >>> str(Element('name', 'type', odicti(zip("abcde", range(5)))))
        'name: type, a=0, b=1, c=2, d=3, e=4;'

        """
        def _fmt_arg(k, v):
            return ', %s' % k if v is None else ', %s%s' % (k,fmtArg(v))
        return '%s%s%s;' % ('%s: ' % self.name if self.name else '',
                            self.type,
                            ''.join(_fmt_arg(k, v)
                                    for k,v in self.args.items()))

    def __repr__(self):
        """
        Representation, mainly used to write tests.

        >>> repr(Element('name', 'type', odicti(zip("abcde", range(5)))))
        "Element('name', 'type', a=0, b=1, c=2, d=3, e=4)"

        """
        def _fmt_arg(k, v):
            return ', %s' % k if v is None else ', %s%s' % (k,fmtArg(v))
        return '%s(%r, %r%s)' % (
            self.__class__.__name__,
            self.name,
            self.type,
            ''.join(_fmt_arg(k, v) for k,v in self.args.items()))

class Text(str):
    type = None

class Sequence(object):
    """MadX sequence."""
    def __init__(self, seq, opt=None, name=None):
        self.name = name
        self.opt = opt
        self.seq = seq

    def __str__(self, code):
        """Format sequence to MadX format."""
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

def filter_default(offset, refer, elem):
    elem.at = offset + refer*elem.get('L', 0)
    return [elem]

def detect_slicing(elem, default_slicing):
    # fall through for elements without explicit slice attribute
    slicing = elem.pop('slice', default_slicing)
    if not slicing:
        return None
    elem_len = elem.get('L', 0)
    if elem_len == 0:
        return None

    # determine slice number, length
    if isinstance(slicing, int):
        elem.slice_num = slicing
        elem.slice_len = elem_len / slicing
    else:
        m = regex.slice_per_m.match(slicing)
        if not m:
            raise ValueError("Invalid slicing: %s" % slicing)
        slice_per_m = decimal.Decimal(m.groups()[0])
        elem.slice_num = int(ceil(abs(elem_len * slice_per_m)))
        elem.slice_len = elem_len / elem.slice_num

    # replace L property
    elem.L = elem.slice_len
    return elem

class Typecast(object):
    """
    Namespace for MAKETHIN-like transformations.
    """
    @staticmethod
    def preserve(elem):
        """
        Leave the elements 'as is'.

        Leave their type unchanged for later transformation in
        MADX.MAKETHIN.

        >>> el = Element(None, 'SBEND', {'angle': 3.14, 'slice_num': 2})
        >>> Typecast.preserve(el)
        >>> el.angle
        1.57
        >>> el.type
        'SBEND'

        """
        if elem.type == 'sbend' and elem.slice_num > 1:
            elem.angle = elem.angle / elem.slice_num

    @staticmethod
    def multipole(elem):
        """
        Transform the elements to MULTIPOLE elements.

        NOTE: Typecast.multipole is currently not recommended!  If you use
        it, you have to make sure, your slice length will be sufficiently
        small!  You should use Mad-X' MAKETHIN or not use it at all!

        >>> sbend = Element(None, 'SBEND', dicti(angle=3.14, slice_num=2,
        ...                                      hgap=1, L=3.5))
        >>> Typecast.multipole(sbend)
        >>> sbend.KNL
        '{1.57}'
        >>> sbend.get('angle')
        >>> sbend.get('hgap')      #TODO: HGAP is just dropped ATM!
        >>> sbend.type
        'multipole'

        >>> quad = Element(None, 'QUADRUPOLE', dicti(K1=3, slice_num=2,
        ...                                          L=2.5))
        >>> Typecast.multipole(quad)
        >>> quad.KNL
        '{0, 7.5}'
        >>> quad.get('K1')
        >>> quad.type
        'multipole'

        """
        if elem.type == 'sbend':
            elem.KNL = '{%s}' % (elem.angle / elem.slice_num,)
            del elem.angle
            del elem.HGAP
        elif elem.type == 'quadrupole':
            elem.KNL = '{0, %s}' % (elem.K1 * elem.L,)
            del elem.K1
        elif elem.type == 'solenoid':
            elem.ksi = elem.KS / elem.slice_num
            elem.lrad = elem.L / elem.slice_num
            elem.L = 0
            return
        else:
            return

        # set elem_class to multipole
        elem.type = stri('multipole')
        # replace L by LRAD property
        elem.lrad = elem.pop('L', None)



class Slice(object):

    @staticmethod
    def simple(offset, refer, elem):
        elems = []
        for slice_idx in range(elem.slice_num):
            slice = Element(None, elem.type, copy(elem.args))
            if elem.name:
                slice.name = "%s..%s" % (elem.name, slice_idx)
            slice.at = offset + (slice_idx + refer)*elem.slice_len
            elems.append(slice)
        return None, elems

    @staticmethod
    def optics(offset, refer, elem):
        return elem, [
            Element("%s..%s" % (elem.name, slice_idx),
                    elem.name,
                    odicti(at=offset + (slice_idx + refer)*elem.slice_len))
            for slice_idx in range(elem.slice_num) ]

    @staticmethod
    def optics_short(offset, refer, elem):
        return elem, [
            Element(
                None,
                elem.name,
                odicti(at=offset + (slice_idx + refer)*elem.slice_len))
            for slice_idx in range(elem.slice_num) ]

    @staticmethod
    def loops(offset, refer, elem):
        return elem, [
            Text('i = 0;'),
            Text('while (i < %s) {' % elem.slice_num),
            Element(
                None,
                elem.name,
                odicti(
                    at=(offset +
                        (Identifier('i',True) + refer) *
                           elem.get('L', elem.get('lrad')))
                )),
            Text('i = i + 1;'),
            Text('}'), ]


#----------------------------------------
# json output
#----------------------------------------

def coeffs_quadrupole(elem):
    return (getattr(elem, coeff)
            for coeff in ('K1', 'K1S')
            if isinstance(elem.get(coeff), Identifier))

def get_variables(elem):
    coeffs = dicti(quadrupole=coeffs_quadrupole)

    if not (elem.type and elem.at and
            elem.type in coeffs):
        return []

    return [('vary', [
        odicti([
            ('name', str(coeff)),
            ('step', 1e-6)])
        for coeff in coeffs.get(elem.type)(elem) ]
    )]


def json_adjust_element(elem):
    if not elem.type:
        return ()
    return odicti([('name', elem.name),
                   ('type', elem.type)] +
                  get_variables(elem) +
                  [(k,v) for k,v in elem.args.items() if v is not None]),


#----------------------------------------
# YAML serialization utility:
#----------------------------------------

class Yaml(object):

    def __init__(self):
        import yaml
        import pydicti
        self.yaml = yaml
        self.dict = pydicti.odicti

    def dump(self, data, stream=None, **kwds):
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
        Dumper.add_representer(decimal.Decimal, _Decimal_representer)
        return yaml.dump(data, stream, Dumper,
                         default_flow_style=False, **kwds)

    def load(self, stream, **kwds):
        class OrderedLoader(Loader):
            pass
        OrderedLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            lambda loader, node: self.dict(loader.construct_pairs(node)))
        return yaml.load(stream, OrderedLoader)

#----------------------------------------
# main
#----------------------------------------

def transform(elem,
              typecast=Typecast.preserve,
              slicing=None):
    """Transform sequence."""
    if not isinstance(elem, Sequence):
        return (elem,)
    seq = elem
    first = seq.seq[0]
    last = seq.seq[-1]

    offsets = dicti(entry=0, centre=decimal.Decimal(0.5), exit=1)
    refer = offsets[str(first.get('refer', 'centre'))]

    # TODO: when to slice: explicit/always/never/{select classes}


    # output method
    slice_method = getattr(Slice, first.pop('method', 'simple').lower())

    # iterate through sequence
    elems = []
    optics = []
    length = 0
    for elem in seq.seq[1:-1]:
        if elem.type:
            elem_len = elem.get('L', 0)
            if detect_slicing(elem, slicing):
                typecast(elem)
                optic, elem = slice_method(length, refer, elem)
                if optic:
                    optics.append(optic)
                elems += elem
            else:
                elems += filter_default(length, refer, elem)
            length += elem_len
        else:
            elems.append(elem)
    first.L = length

    if optics:
        optics.insert(0, Text('! Optics definition for %s:' % first.get('name')))
        optics.append(Text())

    return Sequence([first] + elems + [last], optics, first.get('name'))

class File(list):

    @classmethod
    def parse(cls, lines):
        """Parse sequence from line iteratable."""
        return cls(list(chain.from_iterable(map(cls.parse_line, lines))))

    @classmethod
    def parse_line(cls, line):
        """
        Parse a single-line MAD-X statement.

        Return an iterable that iterates over parsed elements.

        TODO: multi-line commands!

        >>> list(File.parse_line(' \t '))
        ['']

        >>> list(File.parse_line(' \t ! a comment; ! '))
        ['! a comment; ! ']

        >>> list(File.parse_line(' use, hello=world, z=23.23e2; k: z;  !'))
        ['!', Element(None, 'use', hello=world, z=2323.0), Element('k', 'z')]

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

    def __str__(self, code):
        """Format sequence to MadX format."""
        pass

def main(argv=None):
    # parse command line options
    from docopt import docopt
    args = docopt(__doc__, argv, version='madseq.py 0.1')

    # prepare filters
    typecast = Typecast.multipole if args['--makethin'] else Typecast.preserve
    transformation = partial(transform,
                             typecast=typecast,
                             slicing=args['--slice'])

    # perform input
    if args['<input>'] and args['<input>'] != '-':
        with open(args['<input>'], 'rt') as f:
            input_file = list(f)
    else:
        from sys import stdin as input_file

    # open output stream
    if args['--output'] and args['--output'] != '-':
        output_file = open(args['--output'], 'wt')
    else:
        from sys import stdout as output_file

    def load(file):
        return Sequence.detect(File.parse(file))

    def transform(input_data):
        return (transformation(el)
                for el in input_data)

    def serialize(output_data):
        return odicti(
            (seq.name,
             list(chain.from_iterable(map(json_adjust_element, seq.seq))))
            for seq in output_data
            if isinstance(seq, Sequence))

    if args['--json']:
        import json
        def dump(output_data):
            json.dump(
                serialize(output_data),
                output_file,
                indent=3,
                separators=(',', ' : '),
                cls=ValueEncoder)

    elif args['--yaml']:
        yaml = Yaml()
        def dump(output_data):
            yaml.dump(
                serialize(output_data),
                output_file)

    else:
        def dump(output_data):
            output_file.write("\n".join(map(str, output_data)))

    # one line to do it all:
    dump(transform(load(input_file)))

main.__doc__ = __doc__

if __name__ == '__main__':
    main()

