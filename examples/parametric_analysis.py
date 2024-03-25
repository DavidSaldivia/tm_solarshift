# -*- coding: utf-8 -*-

import pandas as pd
import tm_solarshift.general as general
from tm_solarshift.units import VariableList

import tm_solarshift.parametric as parametric
PARAMS_OUT = parametric.PARAMS_OUT

#------------------------------
def parametric_analysis_tank():
    """
    Example of a parametric analysis over parameters in the tank.
    """
    
    GS_base = general.GeneralSetup()

    params_in = {
        'DEWH.nom_power' : VariableList([2400., 3600., 4800.], "W"),
        'DEWH.temp_max'  : VariableList([55., 65., 75.], 'degC'),
        'DEWH.U'  : VariableList([0.5, 1.0, 2.0], 'W/m2-K'),
        'DEWH.vol': VariableList([0.2, 0.3, 0.4], "m3")
        }
    runs = parametric.settings(params_in, PARAMS_OUT)
    runs = parametric.analysis(
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

#------------------------
def parametric_analysis_HP():
    """
    Example of a parametric analysis using a heat pump heater
    """

    from tm_solarshift.devices import HeatPump
    GS_base = general.GeneralSetup()
    GS_base.DEWH = HeatPump()
    
    params_in = {
        'household.location' : ['Sydney', 'Adelaide', 'Brisbane', 'Melbourne'],
        'HWDInfo.profile_HWD' : [1,2,3,4,5,6],
        'household.control_load' : [0,1,2,3,4],
        }
    runs = parametric.settings(params_in, PARAMS_OUT)
    runs = parametric.analysis(
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

#------
if __name__ == "__main__":

    parametric_analysis_tank()

    # parametric_analysis_HP()
    
    pass