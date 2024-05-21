# -*- coding: utf-8 -*-
import pandas as pd
import tm_solarshift.general as general
import tm_solarshift.analysis.parametric as parametric
from tm_solarshift.utils.units import VariableList

PARAMS_OUT = parametric.PARAMS_OUT

#------------------------------
def parametric_analysis_tank() -> pd.DataFrame:
    """
    Example of a parametric analysis over parameters in the tank.
    """

    GS_base = general.Simulation()
    params_in = {
        'DEWH.nom_power' : VariableList([2400., 3600., 4800.], "W"),
        'DEWH.temp_max'  : VariableList([55., 65., 75.], 'degC'),
        'DEWH.U'  : VariableList([0.5, 1.0, 2.0], 'W/m2-K'),
        'DEWH.vol': VariableList([0.2, 0.3, 0.4], "m3")
        }
    (runs, params_units) = parametric.settings(params_in)
    runs = parametric.analysis(
        runs, params_units, PARAMS_OUT,
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
    return runs

#------------------------
def parametric_analysis_HP() -> pd.DataFrame:
    """
    Example of a parametric analysis using a heat pump heater
    """

    from tm_solarshift.models.dewh import HeatPump
    GS_base = general.Simulation()
    GS_base.DEWH = HeatPump()
    
    params_in = {
        'household.location' : ['Sydney', 'Adelaide', 'Brisbane', 'Melbourne'],
        'HWDInfo.profile_HWD' : [1,2,3,4,5,6],
        'household.control_load' : [0,1,2,3,4],
    }
    (runs, params_units) = parametric.settings(params_in)
    runs = parametric.analysis(
        runs, params_units, PARAMS_OUT,
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
    return runs

#------
if __name__ == "__main__":

    # runs = parametric_analysis_tank()

    runs = parametric_analysis_HP()
    
    pass