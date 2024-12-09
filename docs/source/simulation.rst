The Simulation Settings
============================

The Simulation() object
-------------------------

Usually this class is used in two steps: setting attributes and running the simulation. The full list of attributes are:

.. autoclass:: tm_solarshift.general.Simulation

Once the settings are defined, you can to run the simulation using the :py:meth:`~tm_solarshift.general.Simulation.run_simulation()`. This method is design for the specific DEWH application. 

.. automethod:: tm_solarshift.general.Simulation.run_simulation


.. _time-params:

The TimeParams() object
-------------------------

This defines the temporal settings. The attributes are:

.. autoclass:: tm_solarshift.general.TimeParams()

    .. autoproperty:: tm_solarshift.general.TimeParams.idx

    .. autoproperty:: tm_solarshift.general.TimeParams.PERIODS

    .. autoproperty:: tm_solarshift.general.TimeParams.DAYS


.. _household-object:

The Household() object
-------------------------

The ``Household()`` object contain useful information about the household as attributes. You can define its ``location``, ``control_type``, ``tariff_type``, and ``size``.

.. autoclass:: tm_solarshift.general.Household

    .. autoproperty:: tm_solarshift.general.Household.DNSP