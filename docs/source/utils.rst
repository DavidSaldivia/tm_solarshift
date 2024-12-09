Utility modules
================

A couple of modules are used to help with some calculations and functionality.

Units
-------
It contains two classes to represent physical quantities with units (:py:class:`~tm_solarshift.utils.units.Variable` and :py:class:`~tm_solarshift.utils.units.VariableList`), as well as a function to convert between units (:py:func:`~tm_solarshift.utils.units.conversion_factor`)

.. autoclass:: tm_solarshift.utils.units.Variable
    :members:

.. autoclass:: tm_solarshift.utils.units.VariableList
    :members:

.. autofunction:: tm_solarshift.utils.units.conversion_factor

Solar
------

Some functions to calculate solar variables useful for solar thermal collectors and PV Systems. It is a wrapper of the corresponding pvlib's functions.

.. automodule:: tm_solarshift.utils.solar
    :members: