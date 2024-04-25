import os
import sys
import pandas as pd
import numpy as np

from tm_solarshift.devices import (
    Variable,
    VariableList,
    ResistiveSingle,
    HeatPump,
    SolarSystem,
)

from tm_solarshift.constants import PROFILES
PROFILES_COLUMNS = PROFILES.COLUMNS

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
def parametric_settings(
        params_in : dict = {},
        params_out: List = [],
        ) -> pd.DataFrame:

    """_summary_
    This function creates a parametric run.
    It creates a pandas dataframe with all the runs required.
    The order of running is "first=outer".
    It requires a dictionary with keys as Simulation attributes (to be changed)
    and a list of strings with the desired outputs from out_overall.

    Args:
        params_in (dict): dict with (parameter : [values]) structure.
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