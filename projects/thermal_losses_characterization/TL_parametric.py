# -*- coding: utf-8 -*-

import pandas as pd

import tm_solarshift.general as general
from tm_solarshift.constants import (DIRECTORY, DEFINITIONS)
from tm_solarshift.utils.units import VariableList
from tm_solarshift.devices import (HeatPump, ResistiveSingle)

from tm_solarshift.analysis.parametric import (
    parametric_settings,
    parametric_run,
)

DIR_DATA = DIRECTORY.DIR_DATA
DIR_RESULTS = DIRECTORY.DIR_RESULTS

PARAMS_OUT = [
    'heater_heat_acum', 'heater_power_acum', 'heater_perf_avg',
    'E_HWD_acum', 'eta_stg', 'cycles_day', 'SOC_avg',
    'm_HWD_avg', 'temp_amb_avg', 'temp_mains_avg',
    'SOC_min', 'SOC_025', 'SOC_050', 't_SOC0',
    'emissions_total','solar_ratio',
]

showfig = False

pd.set_option('display.max_columns', None)


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