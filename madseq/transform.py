from __future__ import absolute_import
from __future__ import division

from math import ceil
from decimal import Decimal

from madseq.util import dicti
from madseq.types import Element, Sequence, Identifier, Text

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

        if isinstance(node, Element):
            defs[str(node.name)] = node
            node._base = defs.get(node.type)
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
                    return t.slice(elem, offset, refer)

        templates = []      # predefined element templates
        elements = []       # actual elements to put in sequence
        position = 0        # current element position

        for elem in body:
            if elem.type:
                templ, elem, position = transform(elem, position)
                templates += templ
                elements += elem
            else:
                elements.append(elem)
        head['L'] = position

        if templates:
            templates.insert(0, Text('! Template elements for %s:' % head.name))
            templates.append(Text())

        return Sequence([head] + elements + [tail], templates)


class ElementTransform(object):

    """
    Single Element transformation rule.

    :ivar function match:
    :ivar function _get_position:
    :ivar function _get_slice_num:
    :ivar function _rescale:
    :ivar function _maketempl:
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
            self.match = lambda elem: elem.base_type == type
        else:
            self.match = lambda elem: True

        # whether to use or overwrite manual AT values
        if selector.get('use_at', True):
            # Retrieve the entry (!) position of the element, this value will
            # later be corrected for refer=centre/exit in the _distribution
            # call:
            def _get_position(elem, elem_len, offset, refer):
                try:
                    return elem['at'] - elem_len * refer
                except KeyError:
                    return offset
            self._get_position = _get_position
        else:
            self._get_position = lambda elem, elem_len, offset, refer: offset

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
        if selector.get('template', False):
            self._maketempl = lambda elem: [elem]
            self._stripelem = lambda elem: Element(None, elem.name, {}, elem)
        else:
            self._maketempl = lambda elem: []
            self._stripelem = lambda elem: elem

        # slice distribution style over element length
        style = selector.get('style', 'uniform')
        if style == 'uniform':
            self._distribution = self.uniform_slice_distribution
        elif style == 'loop':
            self._distribution = self.uniform_slice_loop
        else:
            raise ValueError("Unknown slicing style: {0!r}".format(style))

    def slice(self, elem, offset, refer):
        """
        Transform the element at ``offset.

        :param Element elem:
        :param Decimal offset: element entry position
        :param Decimal refer: sequence addressing style
        :returns: template elements, element slices, element length
        :rtype: tuple
        """
        elem_len = elem.get('L', 0)
        offset = self._get_position(elem, elem_len, offset, refer)
        slice_num = self._get_slice_num(elem_len) or 1
        slice_len = Decimal(elem_len) / slice_num
        scaled = self._rescale(elem, 1/Decimal(slice_num))
        templ = self._maketempl(scaled)
        elem = self._stripelem(scaled)
        elems = self._distribution(elem, offset, refer, slice_num, slice_len)
        return templ, elems, offset + elem_len

    def uniform_slice_distribution(self, elem, offset, refer, slice_num, slice_len):
        """
        Slice an element uniformly into short pieces.

        :param Element elem:
        :param Decimal offset: element entry position
        :param Decimal refer: sequence addressing style
        :param Decimal slice_len: element length
        :param int slice_num: number of slices
        :returns: element slices
        :rtype: generator
        """
        for slice_idx in range(slice_num):
            slice = elem.copy()
            slice['at'] = offset + (slice_idx + refer)*slice_len
            if slice.name and slice_num > 1:
                slice.name = elem.name + '..' + str(slice_idx)
            yield slice

    def uniform_slice_loop(self, elem, offset, refer, slice_num, slice_len):
        """
        Slice an element uniformly into short pieces using a loop construct.

        :param Element elem:
        :param Decimal offset: element entry position
        :param Decimal refer: sequence addressing style
        :param Decimal slice_len: element length
        :param int slice_num: number of slices
        :returns: element slices
        :rtype: generator
        """
        slice = elem.copy()
        slice.name = None
        slice['at'] = offset + (Identifier('i') + refer) * slice_len
        yield Text('i = 0;')
        yield Text('while (i < %s) {' % slice_num)
        yield slice
        yield Text('i = i + 1;')
        yield Text('}')


def rescale_thick(elem, ratio):
    """Shrink/grow element size, while leaving the element type 'as is'."""
    # TODO: implement this for all sorts of elements..
    if ratio == 1:
        return elem
    scaled = elem.copy()
    scaled['L'] = elem['L'] * ratio
    if scaled.base_type == 'sbend':
        scaled['angle'] = scaled['angle'] * ratio
    return scaled


def rescale_makethin(elem, ratio):
    """
    Shrink/grow element size, while transforming elements to MULTIPOLEs.

    NOTE: rescale_makethin is currently not recommended!  If you use it,
    you have to make sure, your slice length will be sufficiently small!

    Furthermore, most MAD-X elements and parameters are not dealt with!
    """
    # TODO: handle more elements (sextupole, ...?)
    # TODO: check/modify more parameters
    base_type = elem.base_type
    if base_type not in ('sbend', 'quadrupole', 'solenoid'):
        return elem
    if base_type == 'solenoid':
        elem = elem.copy()
        elem['ksi'] = elem['KS'] * elem['L'] * ratio
        elem['lrad'] = elem['L'] * ratio
        elem['L'] = 0
        return elem
    elem = Element(elem.name, 'multipole', elem.all_args)
    if base_type == 'sbend':
        elem['KNL'] = [elem.pop('angle') * ratio]
        elem.pop('HGAP', None)
    elif base_type == 'quadrupole':
        if 'K1' in elem:
            elem['KNL'] = [0, elem['K1'] * elem['L'] * ratio]
            del elem['K1']
        if 'K1S' in elem:
            elem['KSL'] = [0, elem['K1S'] * elem['L'] * ratio]
            del elem['K1S']
    if 'L' in elem:
        elem['lrad'] = elem.pop('L') * ratio
    return elem


def exclusive(mapping, *keys):
    """Check that at most one of the keys is contained in the mapping."""
    return sum(key in mapping for key in keys) <= 1
