import os
import sys
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Tuple

from tm_solarshift.devices import (
    VariableList,
    ResistiveSingle,
    HeatPump,
    SolarSystem,
)

MAIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fileDir = os.path.dirname(os.path.abspath(__file__))
dataDir = os.path.join(MAIN_DIR, "data")
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
HWDP_NAMES = {
    1:'Mor & Eve Only',
    2:'Mor & Eve w daytime',
    3:'Evenly',
    4:'Morning',
    5:'Evening',
    6:'late Night'
}
CL_NAMES = {
    0:'GS',
    1:'CL1',
    2:'CL2',
    3:'CL3',
    4:'SS'
}

#------------------------------------
## The main object for the simulation
class GeneralSetup():
    def __init__(self, **kwargs):

        self.START = 0                  # [hr]
        self.STOP = 8760                # [hr]
        self.STEP = 3                   # [min]
        self.YEAR = 2022                # [-]
        self.location = "Sydney"
        self.DNSP = "Ausgrid"
        self.tariff_type = "flat"

        self.DEWH = ResistiveSingle()
        self.solar_system = SolarSystem()

        # Profile/Behavioural Parameters
        self.profile_PV = 0  # See above for the meaning of these options
        self.profile_Elec = 0
        self.profile_HWD = 1
        self.profile_control = 0
        self.random_control = True

        # HWD statistics
        self.HWD_avg = 200.0  # [L/d]
        self.HWD_std = self.HWD_avg / 3.0
        # [L/d] (Measure for daily variability. If 0, no variability)
        self.HWD_min = 0.0  # [L/d] Minimum HWD. Default 0
        self.HWD_max = 2 * self.HWD_avg  # [L/d] Maximum HWD. Default 2x HWD_avg
        # [str] Type of variability in daily consumption.
        # Options: None, unif, truncnorm, sample
        self.HWD_daily_dist = None

        for key, value in kwargs.items():
            setattr(self, key, value)
        
    @property
    def DAYS(self):
        return int(self.STOP / 24)
    @property
    def STEP_h(self):
        return self.STEP / 60.0
    @property
    def PERIODS(self):
        return int(np.ceil((self.STOP - self.START) / self.STEP_h))
    @property
    def DAYS_i(self):
        return int(np.ceil(self.STEP_h * self.PERIODS / 24.0))

    def update_params(self, params):
        for key, values in params.items():
            if hasattr(self, key):  # Checking if the params are in GeneralSetup to update them
                setattr(self, key, values)
            else:
                text_error = f"Parameter {key} not in GeneralSetup. Simulation will finish now"
                raise ValueError(text_error)

    def parameters(self):
        return self.__dict__.keys()


#------------------------------------
class Simulation():
    def __init__(self):

        self.location = "Sydney"
        self.START = 0                  # [hr]
        self.STOP = 8760                # [hr]
        self.STEP = 3                   # [min]
        self.YEAR = 2022                # [-]

    @property
    def DAYS(self):
        return int(self.STOP / 24)
    @property
    def STEP_h(self):
        return self.STEP / 60.0
    @property
    def PERIODS(self):
        return int(np.ceil((self.STOP - self.START) / self.STEP_h))
    @property
    def DAYS_i(self):
        return int(np.ceil(self.STEP_h * self.PERIODS / 24.0))


    def create_new_profile(
        self,
        profile_columns: List[str] = None,
    ) -> pd.DataFrame:

        if profile_columns == None:
            from tm_solarshift.profiles import PROFILES_COLUMNS
            profile_columns = PROFILES_COLUMNS
        START = self.START
        STEP = self.STEP
        YEAR = self.YEAR
        PERIODS = self.PERIODS

        start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") \
            + pd.DateOffset(hours=START)
        idx = pd.date_range(
            start=start_time, 
            periods=PERIODS, 
            freq=f"{STEP}min"
        )
        Profiles = pd.DataFrame(index=idx, columns=profile_columns)

        return Profiles

#------------------------------------
class ElectricityInfo():
    def __init__(self):
        self.tariff_type = "flat"
        self.DNSP = "Ausgrid"
        self.control_load = 0
        self.control_random_on = True

#------------------------------------
class HWDInfo():
    def __init__(self):
        self.profile_HWD = 1
        self.HWD_avg = 200.0  # [L/d]
        self.HWD_std = self.HWD_avg / 3.0
        # [L/d] (Measure for daily variability. No variability = 0)
        self.HWD_min = 0.0  # [L/d] Minimum HWD. Default 0
        self.HWD_max = 2 * self.HWD_avg  # [L/d] Maximum HWD. Default 2x HWD_avg
        
        # Options: None, unif, truncnorm, sample
        self.HWD_daily_dist = None # [str] Type of variability in daily consumption.

#------------------------------------
# class Household():
#     def __init__(self):

#         self.simulation = Simulation()
#         self.DEWH = ResistiveSingle()
#         self.solar_system = SolarSystem()
#         self.HWD = HWDInfo()
#         self.elec_plan = ElectricityInfo()

#     def parameters(self):
#         return self.__dict__.keys()

#------------------------------------
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
    import itertools
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

#------------------------------------

if __name__ == '__main__':
    Sim = GeneralSetup()
    # profiles = Profiles(Sim)

    import tm_solarshift.trnsys as trnsys
    Sim2 = trnsys.GeneralSetup()