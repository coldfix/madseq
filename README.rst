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

