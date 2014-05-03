madseq
------
|Build Status| |Coverage| |Version| |Downloads| |License|

Description
~~~~~~~~~~~

Script to parse MAD-X_ sequences from a source file and perform simple
transformations on the elements.

.. _MAD-X: http://madx.web.cern.ch/madx

Dependencies
~~~~~~~~~~~~

- docopt_ to parse command line options
- pydicti_ to store and access element attributes
- pyyaml_ to parse slicing definition and use YAML output format

.. _docopt: http://docopt.org/
.. _pydicti: https://github.com/coldfix/pydicti
.. _pyyaml: https://pypi.python.org/pypi/PyYAML/


Installation
~~~~~~~~~~~~

The setup is to be performed as follows

.. code-block:: bash

    python setup.py install


Usage
~~~~~

The command should be called as follows::

    Usage:
        madseq.py [-j|-y] [-s <slice>] [<input>] [<output>]
        madseq.py (--help | --version)

    Options:
        -j, --json                      Use JSON as output format
        -y, --yaml                      Use YAML as output format
        -s <slice>, --slice=<slice>     Set slicing definition file
        -h, --help                      Show this help
        -v, --version                   Show version information

If ``<input>`` is not specified the standard input stream will be used to
read the input file. Respectively, the standard output stream will be used
if ``<output>`` is not specified.

The slicing definition defines a list of slicing instructions where each
entry is a dictionary with the following groups of mutually exclusive keys::

    str type: match only elements with the specified type
    str name: match only elements with the specified name

    float density: slice element with the specified number of slices per meter
    int slice: slice element using a fixed count, default=1

    bool makethin: whether to convert the slices  to MULTIPOLE

    bool use_optics: whether to put a template for the element in front

    str style: slicing style, either 'uniform' or 'loop', defaults to 'uniform'


Example file:

.. code-block:: yaml

    - type: drift
      density: 10
    - name: B1DK1
      slice: 10
      makethin: true
      style: uniform

Note, that even if an element is matched by multiple rules, only the first
one will be used.


Caution
~~~~~~~

- Do not use multi line commands in the input sequences. At the moment
  these are not parsed correctly!

- Do not add any ``at=`` position arguments in the input sequences. The
  madseq script takes care of this responsibility.


.. |Build Status| image:: https://api.travis-ci.org/coldfix/madseq.png?branch=master
   :target: https://travis-ci.org/coldfix/madseq
   :alt: Build Status

.. |Coverage| image:: https://coveralls.io/repos/coldfix/madseq/badge.png?branch=master
   :target: https://coveralls.io/r/coldfix/madseq
   :alt: Coverage

.. |Version| image:: https://pypip.in/v/madseq/badge.png
   :target: https://pypi.python.org/pypi/madseq/
   :alt: Latest Version

.. |Downloads| image:: https://pypip.in/d/madseq/badge.png
   :target: https://pypi.python.org/pypi/madseq/
   :alt: Downloads

.. |License| image:: https://pypip.in/license/madseq/badge.png
   :target: https://pypi.python.org/pypi/madseq/
   :alt: License

