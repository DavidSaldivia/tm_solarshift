Parametric Simulation
=====================

Description
-------------

It is possible to run parametric simulations defining the parameters and values to change. The module :py:mod:`~tm_solarshift.analysis.parametric` offers a couple of functions to set and run these simulations. First, you need to define a dictionary, where the keys are the variables to change, and the values are lists with the expected variable values. Then, you need to define a base case simulation: an instance of :py:class:`~tm_solarshift.general.Simulation` with the fix values defined.

For example, the following code will run simulations for different cities, control strategies, and HWDP. Note that two functions are used from the parametric module. First, :py:func:`~tm_solarshift.analysis.parametric.settings` creates a dataframe (``runs``) with all the simulation runs, then the simulations are run in :py:func:`~tm_solarshift.analysis.parametric.analysis`. This last function accepts several optional parameters to control the behaviour.

.. code-block:: python

    import tm_solarshift.general as general
    from tm_solarshift.constants import (DEFINITIONS, SIMULATIONS_IO)
    from tm_solarshift.utils.units import (Variable, VariableList)
    from tm_solarshift.models.dewh import (HeatPump, ResistiveSingle)

    from tm_solarshift.analysis.parametric import (settings, analysis)

    DIR_PROJECT = os.path.dirname(os.path.abspath(__file__))
    
    params_in = {
        'household.location' : ['Sydney', 'Adelaide', 'Brisbane', 'Melbourne'],
        'HWDInfo.profile_HWD' : [1,2,3,4,5,6],
        'household.control_type' : ["GS","CL1","CL2","CL3","timer_SS"],
        }
    params_out = SIMULATIONS_IO.OUTPUT_ANALYSIS_TM + SIMULATIONS_IO.OUTPUT_ANALYSIS_ECON
    dir_output = os.path.join(DIR_PROJECT, "resistive")

    sim_base = general.Simulation()
    sim_base.DEWH = ResistiveSingle.from_model_file(model="491315")
    sim_base.pv_system = None
    
    (runs, units_in) = settings(params_in)
    runs = analysis(
        cases_in = runs,
        units_in = units_in,
        params_out = params_out,
        sim_base = sim_base,
        save_results_detailed = True,
        gen_plots_detailed    = True,
        save_plots_detailed   = True,
        dir_output  = dir_output,
        path_results  = os.path.join(dir_output, '0-parametric_resistive.csv'),
        )

The ``params_in`` dictionary accepts lists and :py:class:`~tm_solarshift.utils.units.VariableList` instances. The following example shows how to run a parametric analysis for different tank variables.

.. code-block:: python
    
    params_in = {
        'DEWH.nom_power' : VariableList([2400., 3600., 4800.], "W"),
        'DEWH.temp_max'  : VariableList([55., 65., 75.], 'degC'),
        'DEWH.U'  : VariableList([0.5, 1.0, 2.0], 'W/m2-K'),
        'DEWH.vol': VariableList([0.2, 0.3, 0.4], "m3")
        }
    params_out = SIMULATIONS_IO.OUTPUT_ANALYSIS_TM + SIMULATIONS_IO.OUTPUT_ANALYSIS_ECON
    dir_output = os.path.join(DIR_PROJECT, "tank")
    path_results = os.path.join(dir_output, '0-parametric_tank.csv')

    sim_base = general.Simulation()
    sim_base.DEWH = ResistiveSingle.from_model_file(model="491315")
    
    (runs, units_in) = settings(params_in)
    runs = analysis(
        cases_in = runs,
        units_in = units_in,
        params_out = params_out,
        sim_base = sim_base,
        save_results_detailed = True,
        gen_plots_detailed    = True,
        save_plots_detailed   = True,
        dir_output  = dir_output,
        path_results  = path_results,
        )


The functions inside the module are:

.. automodule:: tm_solarshift.analysis.parametric
    :members: