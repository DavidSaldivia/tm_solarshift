Time-Series Generators
=======================

Weather
-------------------

The ``tm_solarshift.general`` module provides the ``Weather`` class, that allows to generate weather data using one of the four available options.

.. autoclass:: tm_solarshift.general.Weather
    :members:


Hot water Draw generator
------------------------
The ``HWD`` class provides methods to generate HWD timeseries, using two distribution. An *intra-day distribution* (also known hot water draw profile, HWDP), which define the probability of hot water consumption within a typical day. And an *inter-day distribution* that defines the variability of hot water usage between days.

In addition, it has two methods to generate the HWD, the "standard" and the "events". In the "standard", each day has the same profile (based on the HWD profile), changing only the daily amount given the inter-day distribution. In the "events" method, a set of HWD events are generated using an event description dataframe, where each event time is randomly defined by the HWD profile.

.. autoclass:: tm_solarshift.timeseries.hwd.HWD
    :members:

Market Data
------------
The ``market`` module provides a couple of functions that act as wrappers of external libraries. For example, the :py:meth:`~tm_solarshift.timeseries.market.load_household_import_rate()` function extracts data from `NEMOSIS <https://github.com/UNSW-CEEM/NEMOSIS>`_, while :py:meth:`~tm_solarshift.timeseries.market.load_emission_index_year` uses data from `NEMED <https://github.com/unsw-ceem/nemed>`_.

.. automodule:: tm_solarshift.timeseries.market
    :members:



