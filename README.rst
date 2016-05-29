SeaSnake
========

.. image:: https://travis-ci.org/pybee/seasnake.svg?branch=master
    :target: https://travis-ci.org/pybee/seasnake

A tool to manage conversion of C++ code to Python.

Sometimes you will find a great algorithm, but find that the only
implementation of that algorithm is written in C or C++. In some cases
it might be possible to wrap that C/C++ code in a Python C module.
However, if a C module is not an option, you need to be able to convert
the C/C++ implemention into a Pure Python implementation.

SeaSnake was written to automate the conversion of WebKit_ sources
into a version that could be used by Colosseum_.

Quickstart
----------

In your virtualenv, install SeaSnake, and then run it, passing in
the name of a C++ source file (or files, if you want to provide
the header as well as the cpp file)::

    $ pip install seasnake
    $ seasnake -s path/to/MyClass.cpp

This will output a ``MyClass.py`` Python module to the console.

If your code requires external include files or definitions, you can use
the ``-D`` and ``-I`` options. See ``seasnake --help`` for details.

.. Documentation
.. -------------

.. Documentation for SeaSnake can be found on `Read The Docs`_.

Community
---------

SeaSnake is part of the `BeeWare suite`_. You can talk to the community through:

 * `@pybeeware on Twitter`_

 * The `BeeWare Users Mailing list`_, for questions about how to use the BeeWare suite.

 * The `BeeWare Developers Mailing list`_, for discussing the development of new features in the BeeWare suite, and ideas for new tools for the suite.

Contributing
------------

If you experience problems with SeaSnake, `log them on GitHub`_. If you
want to contribute code, please `fork the code`_ and `submit a pull request`_.

.. _BeeWare suite: http://pybee.org
.. _Read The Docs: https://seasnake.readthedocs.io
.. _@pybeeware on Twitter: https://twitter.com/pybeeware
.. _BeeWare Users Mailing list: https://groups.google.com/forum/#!forum/beeware-users
.. _BeeWare Developers Mailing list: https://groups.google.com/forum/#!forum/beeware-developers
.. _log them on Github: https://github.com/pybee/seasnake/issues
.. _fork the code: https://github.com/pybee/seasnake
.. _submit a pull request: https://github.com/pybee/seasnake/pulls

.. _WebKit: https://webkit.org
.. _Colosseum: http://github.com/pybee/colosseum