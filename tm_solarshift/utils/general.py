import os
import sys
from typing import Optional, List, Dict, Any, Tuple

import pandas as pd
import numpy as np

fileDir = os.path.dirname(os.path.abspath(__file__))
dataDir = os.path.join(
    os.path.dirname(os.path.dirname(fileDir)),
    "data",
    )
DATA_DIR = {
    "weather" : os.path.join(dataDir,"weather"),
    "HWDP" : os.path.join(dataDir,"HWD_Profiles"),
    "SA_processed" : os.path.join(dataDir,"SA_processed"),
    "tariffs" : os.path.join(dataDir,"energy_plans"),
    "emissions" : os.path.join(dataDir,"emissions"),
    "samples" : os.path.join(dataDir,"samples"),
    "layouts" : os.path.join(dataDir,"trnsys_layouts"),
    }
SEASON_DEFINITION = {
    "summer": [12, 1, 2],
    "autumn": [3, 4, 5],
    "winter": [6, 7, 8],
    "spring": [9, 10, 11],
}
DAYOFWEEK_DEFINITION = {
    "weekday": [0, 1, 2, 3, 4],
    "weekend": [5, 6]
}
CLIMATE_ZONE_DEFINITION = {
    1: "Hot humid summer",
    2: "Warm humid summer",
    3: "Hot dry summer, mild winter",
    4: "Hot dry summer, cold winter",
    5: "Warm summer, cool winter",
    6: "Mild warm summer, cold winter",
}
LOCATIONS_NEM_REGION = {
    "Sydney": "NSW1",
    "Melbourne": "VIC1",
    "Brisbane": "QLD1",
    "Adelaide": "SA1",
    "Canberra": "NSW1",
    "Townsville": "QLD1",
}
CONV = {
    "MJ_to_kWh": 1000/3600.,
    "W_to_kJh": 3.6,
    "min_to_s": 60.,
}

class Variable():
    def __init__(self, value: float, unit: str = None, type="scalar"):
        self.value = value
        self.unit = unit
        self.type = type

    def get_value(self, unit=None, check="strict"):
        value = self.value
        if self.unit != unit: #Check units
            raise ValueError(
                f"The variable used have different units: {unit} and {self.unit}"
                )
        return value

##################################################

def parametric_settings(
        params_in : Dict = {},
        params_out: List = [],
        ) -> pd.DataFrame:

    """_summary_
    This code creates a parametric run.
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
    import itertools
    cols_in = params_in.keys()
    runs = pd.DataFrame(
        list(itertools.product(*params_in.values())), 
        columns=cols_in,
        )
    for col in params_out:
        runs[col] = np.nan
    return runs

######################################################
######################################################
# GeneralSetup
# START, STOP, STEP, YEAR = Sim.START, Sim.STOP, Sim.STEP, Sim.YEAR

# Profiles
# HWD_avg = Sim.HWD_avg 
# HWD_std = Sim.HWD_std 
# HWD_min = Sim.HWD_min 
# HWD_max = Sim.HWD_max 
# HWD_daily_dist = Sim.HWD_daily_dist
######################################################
######################################################
## The main object for the simulations and models
class GeneralSetup(object):
    def __init__(self, **kwargs):

        # General Simulation Parameters
        self.START = 0  # [hr]
        self.STOP = 8760  # [hr]
        self.STEP = 3  # [min]
        self.YEAR = 2022  # [-]
        self.location = "Sydney"
        self.DNSP = "Ausgrid"
        self.tariff_type = "flat"
         
        # Directories
        self.fileDir = os.path.dirname(__file__)
        self.layoutDir = "TRNSYS_layouts"
        self.tempDir = None
        # Trnsys Layout configuration
        self.layout_v = 0
        self.layout_DEWH = "RS"  # See above for the meaning of these options
        self.layout_PV = "PVF"
        self.layout_TC = "MX"
        self.layout_WF = "W9a"
        self.weather_source = None

        # Environmental parameters
        # (These default values can change if a weather file is defined)
        self.Temp_Amb = 20.0  # [C] Ambient Temperature
        self.Temp_Mains = 20.0  # [C] Mains water temperature
        self.Temp_Consump = 45.0  # [C] Same as TankTemp_Low
        self.GHI_avg = 1000.0  # [W/m2] Global Horizontal Irradiation

        # Profile/Behavioural Parameters
        self.profile_PV = 0  # See above for the meaning of these options
        self.profile_Elec = 0
        self.profile_HWD = 1
        self.profile_control = 0
        self.random_control = True

        # HWD statistics
        self.HWD_avg = 200.0  # [L/d]
        self.HWD_std = (
            self.HWD_avg / 3.0
        )  # [L/d] (Measure for daily variability. If 0, no variability)
        self.HWD_min = 0.0  # [L/d] Minimum HWD. Default 0
        self.HWD_max = 2 * self.HWD_avg  # [L/d] Maximum HWD. Default 2x HWD_avg
        self.HWD_daily_dist = (
            None  # [str] Type of variability in daily consumption. None for nothing
        )

        # Main components nominal capacities
        self.PV_NomPow = 4000.0  # [W]
        self.Heater_NomCap = 3600.0  # [W]
        self.Heater_F_eta = (
            1.0  # [-] Efficiency factor. 1 for resistive; 3-4 for heat pumps
        )
        # Tank parameters
        self.Tank_nodes = (
            10  # Tank nodes. DO NOT CHANGE, unless TRNSYS layout is changed too!
        )
        self.Tank_Vol = 0.315  # [m3]
        self.Tank_Height = 1.3  # [m]
        self.Tank_TempHigh = 65.0  # [C] Maximum temperature in the tank
        self.Tank_TempDeadband = 10.0  # [C] Dead band for max temp control
        self.Tank_TempLow = 45.0  # [C] Minimum temperature in the tank
        self.Tank_U = 0.9  # [W/m2K] Overall heat loss coefficient
        self.Tank_rho = 1000  # [kg/m3] density (water)
        self.Tank_cp = 4180  # [J/kg-K] specific heat (water)
        self.Tank_k = 0.6  # [W/m-K] thermal conductivity (water)
        self.Tank_Temps_Ini = 3  # [-] Initial temperature of the tank. Check Editing_dck_tank() below for the options

        for key, value in kwargs.items():
            setattr(self, key, value)

        # Some derived parameters from defined values
        self.Tank_ThCap = (
            self.Tank_Vol
            * (self.Tank_rho * self.Tank_cp)
            * (self.Tank_TempHigh - self.Tank_TempLow)
            / 3.6e6
        )  # [kWh]
        self.Tank_D = (4 * self.Tank_Vol / np.pi / self.Tank_Height) ** 0.5
        self.Tank_Aloss = np.pi * self.Tank_D * (self.Tank_D / 2 + self.Tank_Height)

        self.Tank_TempHighControl = (
            self.Tank_TempHigh - self.Tank_TempDeadband / 2.0
        )  # [C] Control temperature including deadband

    ##########################################
    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Some derived parameters from defined values
        self.Tank_ThCap = (
            self.Tank_Vol
            * (self.Tank_rho * self.Tank_cp)
            * (self.Tank_TempHigh - self.Tank_TempLow)
            / 3.6e6
        )  # [kWh]
        self.Tank_D = (4 * self.Tank_Vol / np.pi / self.Tank_Height) ** 0.5
        self.Tank_Aloss = np.pi * self.Tank_D * (self.Tank_D / 2 + self.Tank_Height)

        self.Tank_TempHighControl = (
            self.Tank_TempHigh - self.Tank_TempDeadband / 2.0
        )  # [C] Control temperature including deadband

    ##########################################
    def update_params(self, params):
        for key, values in params.items():
            if hasattr(self, key):  # Checking if the params are in Sim to update them
                setattr(self, key, values)
            else:
                print(f"Parameter {key} not in Sim object. Simulation will finish now")
                sys.exit()

        # Some derived parameters from defined values
        self.Tank_ThCap = (
            self.Tank_Vol
            * (self.Tank_rho * self.Tank_cp)
            * (self.Tank_TempHigh - self.Tank_TempLow)
            / 3.6e6
        )  # [kWh]
        self.Tank_D = (4 * self.Tank_Vol / np.pi / self.Tank_Height) ** 0.5
        self.Tank_Aloss = np.pi * self.Tank_D * (self.Tank_D / 2 + self.Tank_Height)

        self.Tank_TempHighControl = (
            self.Tank_TempHigh - self.Tank_TempDeadband / 2.0
        )  # [C] Control temperature including deadband

    def parameters(self):
        return self.__dict__.keys()

###########################################

class Profiles():
    def __init__(self, Sim):
        START, STOP, STEP, YEAR = Sim.START, Sim.STOP, Sim.STEP, Sim.YEAR
        STEP_h = STEP / 60.0
        PERIODS = int(np.ceil((STOP - START) / STEP_h))
        start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") + pd.DateOffset(hours=START)
        idx = pd.date_range(start=start_time, periods=PERIODS, freq=f"{STEP}min")
        
        from tm_solarshift.utils.profiles import PROFILES_COLUMNS
        self.df = pd.DataFrame(index=idx, columns=PROFILES_COLUMNS)

########################################

if __name__ == '__main__':
    Sim = GeneralSetup()
    profiles = Profiles(Sim)

    import tm_solarshift.utils.trnsys as trnsys
    Sim2 = trnsys.GeneralSetup()