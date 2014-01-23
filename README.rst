madseq
------

Description
~~~~~~~~~~~

Script to parse MAD-X_ sequences from a source file and perform simple
transformations on the elements.

.. _MAD-X: http://madx.web.cern.ch/madx

Dependencies
~~~~~~~~~~~~

- docopt_ to parse command line options
- pydicti_ to store and access element attributes

.. _docopt: http://docopt.org/
.. _pydicti: https://github.com/coldfix/pydicti


Installation
~~~~~~~~~~~~

The setup is to be performed as follows

.. code-block:: bash

    python setup.py install


Usage
~~~~~

The command should be called as follows::

    Usage:
        madseq.py [-j <json>] [-o <output] [<input>]
        madseq.py (--help | --version)

    Options:
        -o <output>, --output=<output>  Set output file
        -j <json>, --json=<json>        Set JSON output file
        -h, --help                      Show this help
        -v, --version                   Show version information
        python -m madseq <infile.madx >outfile.madx

If ``<input>`` is not specified the standard input stream will be used to
read the input file. Respectively, the standard output stream will be used
if ``<output>`` is not specified.


Caution
~~~~~~~

- Do not use multi line commands in the input sequences. At the moment
  these are not parsed correctly!

- Do not add any ``at=`` position arguments in the input sequences. The
  madseq script takes care of this responsibility.

