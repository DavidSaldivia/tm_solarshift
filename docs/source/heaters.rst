.. _heater:

Heater Technologies
=====================

*tm_solarshift* is designed to work with different heater technologies. The ``tm_solarshift.models`` module provides classes to simulate five different heater technologies:

* **Resistive heaters** through :py:class:`~tm_solarshift.models.dewh.ResistiveSingle` (the default).
* **Heat pumps**  using the :py:class:`~tm_solarshift.models.dewh.HeatPump`.
* **Gas heater instantaneous**  using the :py:class:`~tm_solarshift.models.gas_heater.GasHeaterInstantaneous` and **with storage** using :py:class:`~tm_solarshift.models.gas_heater.GasHeaterStorage`.
* **Solar thermal** collectors using the :py:class:`~tm_solarshift.models.solar_thermal.SolarThermalElecAuxiliary`.


Resistive heater
----------------

.. autoclass:: tm_solarshift.models.dewh.ResistiveSingle
    :members:


Heat pumps
----------------

.. autoclass:: tm_solarshift.models.dewh.HeatPump
    :members:


Solar Thermal collectors
-------------------------

.. autoclass:: tm_solarshift.models.solar_thermal.SolarThermalElecAuxiliary
    :members:


Gas heater with storage
-------------------------

.. autoclass:: tm_solarshift.models.gas_heater.GasHeaterStorage
    :members:

Instantaneous gas heater
-------------------------

.. autoclass:: tm_solarshift.models.gas_heater.GasHeaterInstantaneous
    :members:


TrnsysDEWH class
---------------------

All the heaters with tanks are based on the class :py:class:`~tm_solarshift.models.dewh.HWTank`. These heaters have the method run_simulation, that creates a :py:class:`~tm_solarshift.models.trnsys.TrnsysDEWH` that set and call the TRNSYS models.

.. autoclass:: tm_solarshift.models.dewh.HWTank

.. autoclass:: tm_solarshift.models.trnsys.TrnsysDEWH

