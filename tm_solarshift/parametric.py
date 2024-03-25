# -*- coding: utf-8 -*-

import os
import copy
import itertools
import numpy as np
import pandas as pd
from typing import Dict, List

import tm_solarshift.general as general
from tm_solarshift.constants import DIRECTORY
from tm_solarshift.units import (Variable, VariableList)
from tm_solarshift.devices import ResistiveSingle
from  tm_solarshift.thermal_models import (trnsys, postprocessing)

PARAMS_OUT = [
    'heater_heat_acum', 'heater_power_acum', 'heater_perf_avg',
    'E_HWD_acum', 'eta_stg', 'cycles_day', 'SOC_avg',
    'm_HWD_avg', 'temp_amb_avg', 'temp_mains_avg',
    'SOC_min', 'SOC_025', 'SOC_050', 't_SOC0',
    'emissions_total','solar_ratio',
]

DIR_DATA = DIRECTORY.DIR_DATA
DIR_RESULTS = DIRECTORY.DIR_RESULTS
showfig = False

pd.set_option('display.max_columns', None)

#-------------
def settings(
        params_in : Dict[str, VariableList] = {},
        params_out: List[str] = PARAMS_OUT,
        ) -> pd.DataFrame:
    """ 
    This function creates a parametric run. A pandas dataframe with all the runs required.
    The order of running for params_in is "first=outer".

    Args:
        params_in (Dict[str, VariableList], optional): dictionary with (parameter : values). parameters are str (label), values are List (possible values)
        params_out (List[str], optional): List of expected output values. Defaults to PARAMS_OUT.

    Returns:
        pd.DataFrame: set with simulation runs to be performed in the parametric analysis
    """
    cols_in = params_in.keys()
    params_values = []
    for lbl in params_in:
        values = params_in[lbl]
        if type(values)==VariableList:
            values = values.get_values(values.unit)
        params_values.append(values)

    runs = pd.DataFrame(
        list(itertools.product(*params_values)), 
        columns=cols_in,
        )
    for col in params_out:
        runs[col] = np.nan
    return runs


#-----------------------------
def analysis(
    runs_in: pd.DataFrame,
    params_in: Dict,
    params_out: List = PARAMS_OUT,
    GS_base = general.GeneralSetup(),
    save_results_detailed: bool = False,
    fldr_results_detailed: bool = None,
    gen_plots_detailed: bool = False,
    save_plots_detailed: bool = False,
    save_results_general: bool = False,
    file_results_general: str = None,
    fldr_results_general: str = None,
    append_results_general: bool = False,
    verbose: bool = True,
    ) -> pd.DataFrame:
    """parametric_analysis performs a set of simulations changing a set of parameters (params_in).
    The combination of all possible values is performed.

    Args:
        runs_in (pd.DataFrame): a dataframe with all the runs. If not given, it'll be created from params_in and params_out.
        params_in (Dict): dictionary where the keys are the parameter name and values are list of values (see example)
        params_out (List): list of labels of expected output. Defaults to PARAMS_OUT.
        GS_base (_type_, optional): GS object used as base case. Defaults to general.GeneralSetup().
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
    runs = runs_in.copy()
    
    if append_results_general:
        runs_old = pd.read_csv(
            os.path.join(
                DIR_RESULTS, fldr_results_general, file_results_general
                )
            ,index_col=0
            )
      
    for index, row in runs.iterrows():
        
        if verbose:
            print(f'RUNNING SIMULATION {index+1}/{len(runs)}')
        GS = copy.copy(GS_base)

        updating_parameters( GS, row, params_in )
        
        if verbose:
            print("Creating Profiles for Simulation")
        ts = GS.create_ts()

        if verbose:
            print("Executing TRNSYS simulation")
        out_data = trnsys.run_simulation(GS, ts)
        out_overall = postprocessing.annual_simulation(GS, ts, out_data)
        values_out = [out_overall[lbl] for lbl in params_out]
        runs.loc[index, params_out] = values_out
        
        #----------------
        #General results?
        if save_results_general:
            fldr = os.path.join(DIR_RESULTS,fldr_results_general)
            if not os.path.exists(fldr):
                os.mkdir(fldr)
                
            if append_results_general:
                runs_save = pd.concat( [runs_old,runs], ignore_index=True )
                runs_save.to_csv(
                    os.path.join(fldr, file_results_general)
                )
            else:
                runs.to_csv(
                    os.path.join(fldr, file_results_general)
                )
                
        #-----------------
        #Detailed results?
        case = f'case_{index}'
        if save_results_detailed:
            fldr = os.path.join(DIR_RESULTS,fldr_results_detailed)
            if not os.path.exists(fldr):
                os.mkdir(fldr)
            out_data.to_csv(os.path.join(fldr,case+'_results.csv'))
    
        #-----------------
        #Detailed plots?
        if gen_plots_detailed:
            postprocessing.detailed_plots(
                GS, out_data,
                fldr_results_detailed = os.path.join(
                    DIR_RESULTS,
                    fldr_results_detailed
                ),
                save_plots_detailed = save_plots_detailed,
                case = case,
                showfig = showfig
                )
            
        print(runs.loc[index])
        
    return runs

#-------------
def updating_parameters(
        GS: general.GeneralSetup,
        row: pd.Series,
        params_in: Dict,
):
    """updating parameters for those of the specific run.
    This function update the GS object. It takes the string and converts it into GS attributes.

    Args:
        GS (general.GeneralSetup): GS object
        row (pd.Series): values of the specific run (it contains all input and output of the parametric study)
        params_in (Dict): labels of the parameters (input)
    """
    params_row = row[params_in.keys()].to_dict()

    for parameter in params_row:
        
        if '.' in parameter:
            (obj_name, param_name) = parameter.split('.')

            #Retrieving first level attribute (i.e.: DEWH, household, simulation, etc.)
            object = getattr(GS, obj_name)

            # Defining the attribute value and assigning to first level object
            if params_in[parameter].__class__ == VariableList:
                param_value = Variable(params_row[parameter], params_in[parameter].unit)
            else:
                param_value = params_row[parameter]
            setattr(object, param_name, param_value)

            # Reassigning the first level attribute to GS
            setattr(GS, obj_name, object)

        else:
            setattr(
                GS, parameter, params_row[parameter]
            )

    return

#------------------------------
def parametric_run_test():
    
    params_in = {
        'household.location' : ["Sydney",],
        'household.control_load'  : [0,1,2],
        }
    
    GS_base = general.GeneralSetup()
    GS_base.DEWH = ResistiveSingle.from_model_file(model="491315")

    runs = settings(params_in, PARAMS_OUT)

    runs = analysis(
        runs, params_in, PARAMS_OUT,
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

    parametric_run_test()

    return

#------
if __name__ == "__main__":
    main()
    pass