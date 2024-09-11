# -*- coding: utf-8 -*-

import os
import copy
import itertools
import pickle
import numpy as np
import pandas as pd

import tm_solarshift.general as general
from tm_solarshift.models import postprocessing
from tm_solarshift.constants import (DIRECTORY, SIMULATIONS_IO)
from tm_solarshift.utils.units import (Variable, VariableList)
from tm_solarshift.models.dewh import ResistiveSingle
from tm_solarshift.models.gas_heater import GasHeaterInstantaneous

PARAMS_OUT = SIMULATIONS_IO.OUTPUT_ANALYSIS_TM
showfig = False

#-------------
def settings(
        params_in : dict[str, VariableList] = {},
        ) -> tuple[pd.DataFrame, dict]:
    """ 
    This function creates a parametric run. A pandas dataframe with all the runs required.
    The order of running for params_in is "first=outer".

    Args:
        params_in (dict[str, VariableList], optional): dictionary with (parameter : values). parameters are str (label), values are List (possible values)
        params_out (list[str], optional): List of expected output values. Defaults to PARAMS_OUT.

    Returns:
        pd.DataFrame: set with simulation runs to be performed in the parametric analysis
        dict: dictionary with units for each parameter

    """
    cols_in = params_in.keys()
    params_values = []
    params_units = {}
    for lbl in params_in:
        values = params_in[lbl]
        if type(values)==VariableList:
            params_units[lbl] = values.unit
            values = values.get_values(values.unit)
        else:
            params_units[lbl] = None
        params_values.append(values)

    runs = pd.DataFrame(
        list(itertools.product(*params_values)), 
        columns=cols_in,
        )
    return (runs, params_units)

#-----------------------------
def analysis(
    cases_in: pd.DataFrame,
    units_in: dict[str,str],
    params_out: list = PARAMS_OUT,
    sim_base = general.Simulation(),
    save_results_detailed: bool = False,
    gen_plots_detailed: bool = False,
    save_plots_detailed: bool = False,
    dir_output: str | None = None,
    path_results: str | None = None,
    verbose: bool = True,
    ) -> pd.DataFrame:
    """parametric_analysis performs a set of simulations changing a set of parameters (params_in).
    The combination of all possible values is performed.

    Args:
        cases_in (pd.DataFrame): a dataframe with all the inputss.
        units_in (dict): list of units with params_units[key] = unit
        params_out (List): list of labels of expected output. Defaults to PARAMS_OUT.
        sim_base (_type_, optional): Simulation instance used as base case. Defaults to general.Simulation().
        save_results_detailed (bool, optional): Defaults to False.
        fldr_results_detailed (bool, optional): Defaults to None.
        gen_plots_detailed (bool, optional): Defaults to False.
        save_plots_detailed (bool, optional): Defaults to False.
        save_results_general (bool, optional): Defaults to False.
        file_results_general (str, optional): Defaults to None.
        fldr_results_general (str, optional): Defaults to None.
        append_results_general (bool, optional): Defaults to False.
        verbose (bool, optional): Defaults to True.

    Returns:
        pd.DataFrame: An updated version of the runs_in dataframe, with the output values.
    """

    params_in = cases_in.columns
    runs_out = cases_in.copy()
    for col in params_out:
        runs_out[col] = np.nan
      
    for (index, row) in runs_out.iterrows():
        
        if verbose:
            print(f'RUNNING SIMULATION {index+1}/{len(runs_out)}')
        sim = copy.copy(sim_base)
        updating_parameters( simulation=sim, row_in = row[params_in], units_in = units_in )
        sim.run_simulation(verbose=verbose)
        df_tm = sim.out['df_tm']
        overall_tm = sim.out["overall_tm"]
        overall_econ = sim.out["overall_econ"]
        overall_all = overall_tm | overall_econ

        values_out = [overall_all[lbl] for lbl in params_out]
        runs_out.loc[index, params_out] = values_out
        
        #----------------
        #General results?
        if dir_output is not None:
            if not os.path.exists(dir_output):
                os.mkdir(dir_output)
            runs_out.to_csv(path_results)
                
        #-----------------
        #Detailed results?
        if df_tm is None:
            continue
        
        if save_results_detailed:
            pickle_path = os.path.join(dir_output, f'sim_{index}.plk')
            with open(pickle_path, "wb") as file:
                pickle.dump(sim, file, protocol=pickle.HIGHEST_PROTOCOL)
    
        # if gen_plots_detailed:
        #     postprocessing.detailed_plots(
        #         sim, df_tm,
        #         fldr_results_detailed = os.path.join(
        #             DIR_RESULTS,
        #             fldr_results_detailed
        #         ),
        #         save_plots_detailed = save_plots_detailed,
        #         case = case,
        #         showfig = showfig
        #         )
            
        print(runs_out.loc[index])
        
    return runs_out

#-------------
def updating_parameters(
        simulation: general.Simulation,
        row_in: pd.Series,
        units_in: dict = {},
) -> None:
    """updating parameters for those of the specific run.
    This function update the GS object. It takes the string and converts it into GS attributes.

    Args:
        GS (general.Simulation): GS object
        row (pd.Series): values of the specific run (it contains all input and output of the parametric study)
        params_in (dict): labels of the parameters (input)
    """

    for (key, value) in row_in.items():
        if '.' in key:
            (obj_name, param_name) = key.split('.')

            #Retrieving first level attribute (i.e.: DEWH, household, sim, etc.)
            object = getattr(simulation, obj_name)
            
            unit = units_in[key]
            if unit is not None:
                param_value = Variable(value, unit)
            else:
                param_value = value
            setattr(object, param_name, param_value)

            # Reassigning the first level attribute to GS
            setattr(simulation, obj_name, object)

        else:
            setattr(simulation, key, value)
    return None

#------------------------------
def test_parametric_run():
    
    GS_base = general.Simulation()
    GS_base.DEWH = ResistiveSingle.from_model_file(model="491315")

    params_in = {
        'household.location' : ["Sydney",],
        'household.control_load'  : [0,1,2],
        }
    params_out = SIMULATIONS_IO.OUTPUT_ANALYSIS_TM
    (runs, params_units) = settings(params_in)

    runs = analysis(
        cases_in = runs,
        params_in = params_units,
        params_out = params_out,
        GS_base = GS_base,
        save_results_detailed = True,
        gen_plots_detailed    = True,
        save_plots_detailed   = True,
        save_results_general  = True,
        fldr_results_detailed = 'parametric_test',
        fldr_results_general  = 'parametric_test',
        file_results_general  = '0-parametric_test.csv',
        append_results_general = False       #If false, create new file
        )
    
    print(runs)
    
#-------
def main():

    test_parametric_run()

    return

#------
if __name__ == "__main__":
    main()
    pass