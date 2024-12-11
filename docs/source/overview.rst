Getting Started
===============

This section presents the installation process, how to run the default simulation, and the main simulation settings.

.. _installation:

Installation
-------------

To use tm_solarshift just clone the repository and create a virtual environment. ``poetry`` is recommended. Install poetry, go the the repository folder and run:

.. code-block:: console

   $ poetry install


After installing, you need to create/edit a ``.dirs`` in your main directory file indicating the locations of your data and trnsys folders. With this structure:

.. code-block::

    {
        "data": "path/to/your/data",
        "team": "path/to/your/team/folder",
        "trnsys": "C:/TRNSYS18/Exe/TRNExe64.exe",
        "trnsys_temp": "C:/SolarShift_TempDir"
    }

Additionally, in order to run thermal simulations, you also need a valid `TRNSYS <https://trnsys.de/web/en/trnsys18/>`_.

Once you finishes these steps, test the installation using `pytest <https://docs.pytest.org/>`_.

.. _simplestusage:

Simplest Usage
---------------

The simplest way to run a simulation is to create a :py:class:`~tm_solarshift.general.Simulation` object and use its :py:meth:`~tm_solarshift.general.Simulation.run_simulation()` method. The following code would run the default case.

.. code-block:: python

    #Create a general setup instance. It contains all the settings for the simulation
    from tm_solarshift.general import Simulation
    sim = Simulation()

    #Run a thermal simulation with the default case
    sim.run_simulation()
    # Retrieve the data from sim.out dictionary
    df_tm = sim.out["df_tm"]
    overall_tm = sim.out["overall_tm"]


Setting the Simulation
-----------------------

The core of the package is the :py:class:`~tm_solarshift.general.Simulation` class. Here you edit the parameters and settings for your thermal simulations. It contains 4 type of objects:

i. Parameters: ``time_params``, ``location`` and ``household``.
ii. Timeseries Generators, such as ``weather`` and ``HWDInfo``.
iii. Devices, what is actually simulated, such as, ``DEWH``, ``pv_system`` and ``controller``.
iv. Output: which is dictionary containing the different outputs (usually, dataframes and dicts).

You can edit all of these objects, according to your needs. The default values are the following.

.. code-block:: python

    from tm_solarshift.general import (Simulation, Household)
    from tm_solarshift.models.dewh import ResistiveSingle
    from tm_solarshift.models.pv_system import PVSystem
    from tm_solarshift.timeseries.hwd import HWD

    # the attributes of GS and their default objects:
    sim = Simulation()
    sim.household = Household()          # Information of energy plans and control strategies
    sim.DEWH = ResistiveSingle()         # Technical specifications of heater
    sim.pv_system = PVSystem()           # Standard PV system
    sim.HWDInfo = HWD.standard_case()    # Information of HWD behaviour

    #Run a thermal simulation with the default case
    sim.run_simulation(verbose=True)
    df_tm = sim.out["df_tm"]
    overall_tm = sim.out["overall_tm"]

Note how the :py:meth:`~tm_solarshift.general.Simulation.run_simulation()` method has ``verbose=True``, to show more details about the process.

You can also edit the household parameters. See more details in 

.. code-block:: python

    # Household() contains information for the energy plans and type of control
    sim.household.tariff_type = "CL"        # used when not in CL. Options ["CL", "flat", "tou"]
    sim.household.location = "Sydney"       # str for cities, int for postcodes, tuple for coordinates
    sim.household.control_type = "CL1"      # Other options: ["GS", timer, diverter]
    sim.household.control_random_on = True  # add randomization to CL schedules?
    

It is also possible to change the technology. In addition, each technology class has a classmethod ``from_model_file()`` to set the heater parameters from an internal catalog. See the data folder.

.. code-block:: python
    
    from tm_solarshift.general import Simulation
    from tm_solarshift.models.dewh import (ResistiveSingle, HeatPump)
    from tm_solarshift.models.gas_heater import (GasHeaterInstantaneous, GasHeaterStorage)
    from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary

    sim = Simulation()
    sim.DEWH = ResistiveSingle.from_model_file(model="491315")   # from catalog file
    sim.DEWH = GasHeaterInstantaneous()
    sim.DEWH = SolarThermalElecAuxiliary()
    sim.DEWH = HeatPump()                                        # default

