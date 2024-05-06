# -*- coding: utf-8 -*-

import os
import copy
import itertools
import numpy as np
import pandas as pd

import tm_solarshift.general as general
from tm_solarshift.constants import (DIRECTORY, DEFINITIONS)
from tm_solarshift.utils.units import (Variable, VariableList)
from tm_solarshift.devices import (ResistiveSingle, GasHeaterInstantaneous)
from  tm_solarshift.thermal_models import postprocessing

PARAMS_OUT = DEFINITIONS.PARAMS_OUT
DIR_DATA = DIRECTORY.DIR_DATA
DIR_RESULTS = DIRECTORY.DIR_RESULTS
showfig = False

pd.set_option('display.max_columns', None)

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
        cases_in (pd.DataFrame): a dataframe with all the inputss.
        units_in (dict): list of units with params_units[lbl] = unit
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

    params_in = cases_in.columns
    runs_out = cases_in.copy()
    for col in params_out:
        runs_out[col] = np.nan
    
    if append_results_general:
        runs_old = pd.read_csv(
            os.path.join(
                fldr_results_general, file_results_general
                )
            ,index_col=0
            )
      
    for index, row in runs_out.iterrows():
        
        if verbose:
            print(f'RUNNING SIMULATION {index+1}/{len(runs_out)}')
        GS = copy.copy(GS_base)

        updating_parameters( GS, row[params_in], units_in )
        
        if verbose:
            print("Creating Timeseries for simulation")
        ts = GS.create_ts()

        if verbose:
            print("Executing thermal simulation")
        (out_data,out_overall) = GS.run_thermal_simulation(ts, verbose=verbose)
        # out_data = trnsys.run_simulation(GS, ts)
        # out_overall = postprocessing.annual_simulation(GS, ts, out_data)
        values_out = [out_overall[lbl] for lbl in params_out]
        runs_out.loc[index, params_out] = values_out
        
        #----------------
        #General results?
        if save_results_general:
            fldr = os.path.join(DIR_RESULTS,fldr_results_general)
            if not os.path.exists(fldr):
                os.mkdir(fldr)
                
            if append_results_general:
                runs_save = pd.concat( [runs_old, runs_out], ignore_index=True )
                runs_save.to_csv(
                    os.path.join(fldr, file_results_general)
                )
            else:
                runs_out.to_csv(
                    os.path.join(fldr, file_results_general)
                )
                
        #-----------------
        #Detailed results?
        if out_data is None:
            continue
        
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
            
        print(runs_out.loc[index])
        
    return runs_out

#-------------
def updating_parameters(
        GS: general.GeneralSetup,
        row_in: pd.Series,
        units_in: list = [],
) -> None:
    """updating parameters for those of the specific run.
    This function update the GS object. It takes the string and converts it into GS attributes.

    Args:
        GS (general.GeneralSetup): GS object
        row (pd.Series): values of the specific run (it contains all input and output of the parametric study)
        params_in (dict): labels of the parameters (input)
    """

    for (key, value) in row_in.items():
        if '.' in key:
            (obj_name, param_name) = key.split('.')

            #Retrieving first level attribute (i.e.: DEWH, household, simulation, etc.)
            object = getattr(GS, obj_name)
            
            unit = units_in[key]
            if unit is not None:
                param_value = Variable(value, unit)
            else:
                param_value = value
            setattr(object, param_name, param_value)

            # Reassigning the first level attribute to GS
            setattr(GS, obj_name, object)

        else:
            setattr(GS, key, value)
    return None

    # params_row = row_in.to_dict()

    # for parameter in params_row:
        
    #     if '.' in parameter:
    #         (obj_name, param_name) = parameter.split('.')

    #         #Retrieving first level attribute (i.e.: DEWH, household, simulation, etc.)
    #         object = getattr(GS, obj_name)

    #         # Defining the attribute value and assigning to first level object
    #         if params_in[parameter].__class__ == VariableList:
    #             param_value = Variable(params_row[parameter], params_in[parameter].unit)
    #         else:
    #             param_value = params_row[parameter]
    #         setattr(object, param_name, param_value)

    #         # Reassigning the first level attribute to GS
    #         setattr(GS, obj_name, object)

    #     else:
    #         setattr(
    #             GS, parameter, params_row[parameter]
    #         )

#------------------------------
def parametric_run_test():
    
    GS_base = general.GeneralSetup()
    GS_base.DEWH = ResistiveSingle.from_model_file(model="491315")

    params_in = {
        'household.location' : ["Sydney",],
        'household.control_load'  : [0,1,2],
        }
    (runs, params_units) = settings(params_in)

    runs = analysis(
        runs, params_units, PARAMS_OUT,
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