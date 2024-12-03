.. _heater:

Heater Technologies
=====================

The ``tm_solarshift.models`` module provides classes to simulate five different heater technologies:

* **Resistive heaters** through ``ResistiveSingle()`` (the default).
* **Heat pumps**  using the ``HeatPump()``.
* **Gas heater instantaneous**  using the ``GasHeaterInstantaneous`` and **with storage** using ``GasHeaterStorage``.
* **Solar thermal** collectors using the ``SolarThermalElecAuxiliary``.


DEWH Models
----------------

*tm_solarshift* is designed to work with different heater technologies. The default heater is a hot water tank with an immersive resistive heater, represented by ``ResistiveSingle``.

Resistive heater
^^^^^^^^^^^^^^^^

The resistive heater model is contained in the object ``ResistiveSingle``.

.. autoclass:: tm_solarshift.models.dewh.ResistiveSingle(type)

    .. automethod:: tm_solarshift.models.dewh.ResistiveSingle.from_model_file

    .. automethod:: tm_solarshift.models.dewh.ResistiveSingle.run_thermal_model


Heat pumps
^^^^^^^^^^^^^^^^

.. autoclass:: tm_solarshift.models.dewh.HeatPump(type)
    :members:


Solar Thermal collectors
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: tm_solarshift.models.solar_thermal.SolarThermalElecAuxiliary(type)
    :members:


Gas heater with storage
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: tm_solarshift.models.gas_heater.GasHeaterStorage(type)
    :members:

Instantaneous gas heater
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: tm_solarshift.models.gas_heater.GasHeaterInstantaneous(type)
    :members:
