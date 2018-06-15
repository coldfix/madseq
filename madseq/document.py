from __future__ import absolute_import
from __future__ import division

from itertools import chain

from madseq.io import Json, Yaml
from madseq.util import odicti, dicti
from madseq.types import Element, Sequence, Text, regex


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
            raise ValueError("Invalid format code: {0!r}".format(fmt))
