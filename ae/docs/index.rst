.. application environment for python - documentation master file.

application environment taking care of your python application |version|
========================================================================

* pure python
* no external dependencies
* fully typed (:pep:`526`)
* fully :ref:`documented <ae-modules>`
* 100 % test coverage
* multi thread save
* flexible config options (by bundling :class:`~configparser.ConfigParser` and
  :class:`~argparse.ArgumentParser`)
* highly configurable logging (optionally with log file rotation)
* resulting in much less code (for your console application to write and maintain)


.. _ae-modules:

ae modules
----------

.. autosummary::
    :toctree: _autosummary
    :nosignatures:

    ae.console
    ae.core
    ae.literal
    ae.lockname
    ae.progress
    ae.sys_data
    ae.systems



Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

