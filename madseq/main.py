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

from __future__ import absolute_import
from __future__ import division

import sys

from docopt import docopt

from madseq import __version__
from madseq.io import Json, Yaml
from madseq.transform import SequenceTransform
from madseq.document import Document

__all__ = [
    'Document', 'main'
]


def main(argv=None):

    # parse command line options
    args = docopt(__doc__, argv, version=__version__)

    # perform input
    if args['<input>'] and args['<input>'] != '-':
        with open(args['<input>'], 'rt') as f:
            input_file = list(f)
    else:
        input_file = sys.stdin

    # open output stream
    if args['<output>'] and args['<output>'] != '-':
        output_file = open(args['<output>'], 'wt')
    else:
        output_file = sys.stdout

    # get slicing definition
    if args['--slice']:
        with open(args['--slice']) as f:
            if args['--slice'][-5:].lower() == '.json':
                transforms_doc = Json().load(f)
            else:
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
