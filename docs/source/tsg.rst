Time-Series Generators
=======================

Weather
-------------------

The ``tm_solarshift.general`` module provides the ``Weather`` class, that allows to generate weather data using one of the four available options.

.. autoclass:: tm_solarshift.general.Weather

    .. automethod:: tm_solarshift.general.Weather.load_data


Hot water Draw generator
------------------------
The ``HWD`` class provides methods to generate weather timeseries, either from historical data (TMY files, for example). There are four options 

.. autoclass:: tm_solarshift.timeseries.hwd.HWD

    .. automethod:: tm_solarshift.timeseries.hwd.HWD.generator

    .. automethod:: tm_solarshift.timeseries.hwd.HWD.generator_standard

    .. automethod:: tm_solarshift.timeseries.hwd.HWD.generator_events

    .. automethod:: tm_solarshift.timeseries.hwd.HWD.interday_distribution


Market Data
------------
The ``market`` module provides a couple of functions that act as wrappers of external libraries. For example, the ``load_household_import_rate()`` function extracts data from ``nemosis``.

.. automodule:: tm_solarshift.timeseries.market
    :members:



