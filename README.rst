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

.. code-block:: bash

    python -m madseq <infile.madx >outfile.madx

