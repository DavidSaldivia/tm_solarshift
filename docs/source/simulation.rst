The Simulation Settings
============================

The Simulation() object
-------------------------

Usually this class is used in two steps: setting attributes and running the simulation. The full list of attributes are:

.. autoclass:: tm_solarshift.general.Simulation

Once the settings are defined, you need to run the simulation using the ``Simulation.run_simulation()``. This method is design for the specific DEWH application. 

.. automethod:: tm_solarshift.general.Simulation.run_simulation



The TimeParams() object
-------------------------

This defines the temporal settings. The attributes

.. autoclass:: tm_solarshift.general.TimeParams(type)

    .. autoproperty:: tm_solarshift.general.TimeParams.idx

    .. autoproperty:: tm_solarshift.general.TimeParams.PERIODS

    .. autoproperty:: tm_solarshift.general.TimeParams.DAYS

The Household() object
-------------------------

The ``Household()`` object contain useful information about the household as attributes. You can define its ``location``, ``control_type``, ``tariff_type``, and ``size``.

.. autoclass:: tm_solarshift.general.Household

    .. autoclass:: tm_solarshift.general.Household.DNSP