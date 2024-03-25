# -*- coding: utf-8 -*-

import os
import copy
import itertools
import numpy as np
import pandas as pd
from typing import Any, Dict, List

import tm_solarshift.general as general
from tm_solarshift.constants import DIRECTORY
from tm_solarshift.units import VariableList

from tm_solarshift.parametric import (
    parametric_settings,
    parametric_analysis,
    PARAMS_OUT,
)

DIR_DATA = DIRECTORY.DIR_DATA
DIR_RESULTS = DIRECTORY.DIR_RESULTS

showfig = False

pd.set_option('display.max_columns', None)


#------------------------------
def parametric_analysis_tank():
    """
    Example of a parametric analysis over parameters in the tank.
    """
    
    params_in = {
        'DEWH.nom_power' : VariableList([2400., 3600., 4800.], "W"),
        'DEWH.temp_max'  : VariableList([55., 65., 75.], 'degC'),
        'DEWH.U'  : VariableList([0.5, 1.0, 2.0], 'W/m2-K'),
        'DEWH.vol': VariableList([0.2, 0.3, 0.4], "m3")
        }
    
    runs = parametric_settings(params_in, PARAMS_OUT)
    GS_base = general.GeneralSetup()

    runs = parametric_analysis(
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
    
#------
if __name__ == "__main__":

    parametric_analysis_tank()
    
    pass