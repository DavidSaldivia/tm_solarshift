Other Devices
===============

PV System
---------------

The repository also allows to include an optional PV System using the `pvlib <https://pvlib-python.readthedocs.io/en/stable/>`_ library.

.. autoclass:: tm_solarshift.models.pv_system.PVSystem()
    :members:

Controllers
---------------
The different control strategies are represented by different classes. Three different controllers are implemented so far: :py:class:`~tm_solarshift.models.control.CLController`, :py:class:`~tm_solarshift.models.control.Timer`, and :py:class:`~tm_solarshift.models.control.Diverter`.

All the controllers are based on the Protocol class :py:class:`~tm_solarshift.models.control.Controller`, that includes a ``create_signal`` method that receives a DatetimeIndex and return the controller signal.

.. autoclass:: tm_solarshift.models.control.Controller
    :members:

.. autoclass:: tm_solarshift.models.control.CLController()
    :members:

.. autoclass:: tm_solarshift.models.control.Timer()
    :members:

.. autoclass:: tm_solarshift.models.control.Diverter()
    :members: