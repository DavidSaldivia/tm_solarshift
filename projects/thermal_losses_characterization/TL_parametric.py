# -*- coding: utf-8 -*-

import os
import copy
import itertools
import numpy as np
import pandas as pd
from typing import Any, Dict, List

import tm_solarshift.general as general
from tm_solarshift.constants import (DIRECTORY, DEFINITIONS)
from tm_solarshift.units import (Variable, VariableList)
from tm_solarshift.devices import (HeatPump, ResistiveSingle)
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
def parametric_settings(
        params_in : Dict = {},
        params_out: List = [],
        ) -> pd.DataFrame:

    """_summary_
    This function creates a parametric run.
    It creates a pandas dataframe with all the runs required.
    The order of running is "first=outer".
    It requires a dictionary with keys as Simulation attributes (to be changed)
    and a list of strings with the desired outputs from out_overall.

    Args:
        params_in (Dict): Dict with (parameter : [values]) structure.
        params_out (List): List with expected output from simulations.

    Returns:
        pd.DataFrame: Dataframe with all the runs
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

#-------------
def updating_parameters(
        general_setup: general.GeneralSetup,
        row: pd.Series,
        params_in: Dict,
):
    params_row = row[params_in.keys()].to_dict()

    for parameter in params_row:
        
        if '.' in parameter:
            (obj_name, param_name) = parameter.split('.')

            #Retrieving first level attribute (i.e.: DEWH, household, simulation, etc.)
            object = getattr(general_setup, obj_name)

            # Defining the attribute value and assigning to first level object
            if params_in[parameter].__class__ == VariableList:
                param_value = Variable(params_row[parameter], params_in[parameter].unit)
            else:
                param_value = params_row[parameter]
            setattr(object, param_name, param_value)

            # Reassigning the first level attribute to general_setup
            setattr(general_setup, obj_name, object)

        else:
            setattr(
                general_setup, parameter, params_row[parameter]
            )

    return

#-----------------------------
def parametric_run(
    runs_in: pd.DataFrame,
    params_in: Dict,
    params_out: List,
    GS_base = general.GeneralSetup(),
    save_results_detailed: bool = False,
    fldr_results_detailed: bool = None,
    gen_plots_detailed: bool = False,
    save_plots_detailed: bool = False,
    save_results_general: bool = False,
    file_results_general: bool = None,
    fldr_results_general: bool = None,
    append_results_general: bool = False,       #If false, create new file
    verbose: bool = True,
    ):
    
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
        ts = general.load_timeseries_all(GS)

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

#------------------------------
def parametric_run_tank():
    
    params_in = {
        'DEWH.nom_power' : VariableList([2400., 3600., 4800.], "W"),
        'DEWH.temp_max'  : VariableList([55., 65., 75.], 'degC'),
        'DEWH.U'  : VariableList([0.5, 1.0, 2.0], 'W/m2-K'),
        'DEWH.vol': VariableList([0.2, 0.3, 0.4], "m3")
        }
    
    runs = parametric_settings(params_in, PARAMS_OUT)
    GS_base = general.GeneralSetup()

    runs = parametric_run(
        runs, params_in, PARAMS_OUT,
        GS_base = GS_base,
        save_results_detailed = True,
        gen_plots_detailed    = True,
        save_plots_detailed   = True,
        save_results_general  = True,
        fldr_results_detailed = 'parametric_tank',
        fldr_results_general  = 'parametric_tank',
        file_results_general  = '0-parametric_tank.csv',
        append_results_general = False       #If false, create new file
        )

#----------------------------------
def parametric_run_RS():

    LOCATIONS_ALL = DEFINITIONS.LOCATIONS_METEONORM
    LOCATIONS_FEW = ['Sydney', 'Adelaide', 'Brisbane', 'Melbourne']
    params_in = {
        'household.location' : LOCATIONS_FEW,
        'HWDInfo.profile_HWD' : [1,2,3,4,5,6],
        'household.control_load' : [0,1,2,3,4],
        }
    runs = parametric_settings(params_in, PARAMS_OUT)
    GS_base = general.GeneralSetup()
    GS_base.DEWH = ResistiveSingle()

    runs = parametric_run(
        runs, params_in, PARAMS_OUT,
        GS_base = GS_base,
        save_results_detailed = True,
        gen_plots_detailed    = True,
        save_plots_detailed   = True,
        save_results_general  = True,
        fldr_results_detailed = 'parametric_ResistiveSingle',
        fldr_results_general  = 'parametric_ResistiveSingle',
        file_results_general  = '0-parametric_ResistiveSingle.csv',
        append_results_general = False       #If false, create new file
        )

#----------------------------------
def parametric_run_HP():

    LOCATIONS_ALL = DEFINITIONS.LOCATIONS_METEONORM
    LOCATIONS_FEW = ['Sydney', 'Adelaide', 'Brisbane', 'Melbourne']
    params_in = {
        'household.location' : LOCATIONS_FEW,
        'HWDInfo.profile_HWD' : [1,2,3,4,5,6],
        'household.control_load' : [0,1,2,3,4],
        }
    runs = parametric_settings(params_in, PARAMS_OUT)
    
    GS_base = general.GeneralSetup()
    GS_base.DEWH = HeatPump()
    
    runs = parametric_run(
        runs, params_in, PARAMS_OUT,
        GS_base = GS_base,
        save_results_detailed = True,
        gen_plots_detailed    = True,
        save_plots_detailed   = True,
        save_results_general  = True,
        fldr_results_detailed = 'parametric_HeatPump',
        fldr_results_general  = 'parametric_HeatPump',
        file_results_general  = '0-parametric_HeatPump.csv',
        append_results_general = False      #If false, create new file
        )

#----------------------------
# Include tariffs
def parametric_run_tariffs():

    list_profile_HWD     = [1,2,3,4,5,6]
    LIST_DNSP = ["Actewagl", "Ausgrid", "Ausnet", "CitiPower", "Endeavour",
                  "Essential","Energex","Ergon","Horizon","Jemena","Powercor",
                  "Powerwater","SAPN","TasNetworks","Unitedenergy","Western",]
    
    list_tariff_type = ['flat','tou']
    
    params_in = {
        'household.profile_HWD'  : list_profile_HWD,
        'household.DNSP'         : LIST_DNSP,
        'household.tariff_type'  : list_tariff_type
        }
    
    runs = parametric_settings(params_in, PARAMS_OUT)
    
    GS_base = general.GeneralSetup()
    GS_base.DEWH = HeatPump()
    GS_base.household.location = "Sydney"
    GS_base.household.control_load = 0
    GS_base.household.DNSP = "Ausgrid"
    GS_base.household.tariff_type = "flat"
    
    runs = parametric_run(
        runs, params_in, PARAMS_OUT,
        GS_base = GS_base,
        save_results_detailed = True,
        gen_plots_detailed    = True,
        save_plots_detailed   = True,
        save_results_general  = True,
        fldr_results_detailed = 'tariffs',
        fldr_results_general  = 'tariffs',
        file_results_general  = '0-HP_tariffs.csv',
        append_results_general = False      #If false, create new file
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

    runs = parametric_settings(params_in, PARAMS_OUT)

    runs = parametric_run(
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
    
#-------
def main():

    parametric_run_test()

    # parametric_run_tank()
    
    # parametric_run_RS()

    # parametric_run_HP()
    return

#------
if __name__ == "__main__":
    main()
    pass