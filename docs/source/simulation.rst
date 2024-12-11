The Simulation Settings
============================

The Simulation() object
-------------------------

Usually this class is used in two steps: setting attributes and running the simulation. Once the settings are defined, you can to run the simulation using the :py:meth:`~tm_solarshift.general.Simulation.run_simulation()`. This method is design for the specific DEWH application. 

.. autoclass:: tm_solarshift.general.Simulation

.. automethod:: tm_solarshift.general.Simulation.run_simulation

The results are stored in the attribute ``out``, which is an :py:class:`~tm_solarshift.general.Output` dictionary.

.. autoclass:: tm_solarshift.general.Output

.. _time-params:

The TimeParams() object
-------------------------

This defines the temporal settings. The attributes are:

.. autoclass:: tm_solarshift.general.TimeParams()
    :members:

.. _household-object:

The Household() object
-------------------------

The ``Household()`` object contain useful information about the household as attributes. You can define its ``location``, ``control_type``, ``tariff_type``, and ``size``.

.. autoclass:: tm_solarshift.general.Household

    .. autoproperty:: tm_solarshift.general.Household.DNSP