import numpy as np
import pandas as pd
from typing import List

from tm_solarshift.constants import PROFILES
from tm_solarshift.devices import (
    Variable,
    VariableList,
    ResistiveSingle,
    HeatPump,
    SolarSystem,
)

from tm_solarshift.hwd import HWD

#------------------------------------
class GeneralSetup():
    def __init__(self):

        self.household = Household()
        self.DEWH = ResistiveSingle()
        self.solar_system = SolarSystem()
        self.HWD = HWD.standard_case()
        self.simulation = ThermalSimulation()

#------------------------------------
class Household():
    def __init__(self):

        self.tariff_type = "flat"
        self.DNSP = "Ausgrid"
        self.location = "Sydney"
        self.control_load = 1
        self.control_random_on = True

    @classmethod
    def from_postcode(cls, postcode: int):
        
        output = cls()
        return output

#------------------------------------
class ThermalSimulation():
    def __init__(self):
        self.START = Variable(0, "hr")
        self.STOP = Variable(8760, "hr")
        self.STEP = Variable(3, "min")
        self.YEAR = Variable(2022, "-")

    @property
    def DAYS(self):
        START = self.START.get_value("hr")
        STOP = self.STOP.get_value("hr")
        return Variable( int((STOP-START)/24), "d")
    @property
    def PERIODS(self):
        START = self.START.get_value("hr")
        STOP = self.STOP.get_value("hr")
        STEP_h = self.STEP.get_value("hr")
        return Variable( int(np.ceil((STOP - START)/STEP_h)), "-")
    
    def create_new_profile(
        self,
        profile_columns: List[str] = PROFILES.COLUMNS,
    ) -> pd.DataFrame:

        START = self.START.get_value("hr")
        STEP = self.STEP.get_value("min")
        YEAR = self.YEAR.get_value("-")
        PERIODS = self.PERIODS.get_value("-")

        start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") \
            + pd.DateOffset(hours=START)
        idx = pd.date_range(
            start=start_time, 
            periods=PERIODS, 
            freq=f"{STEP}min"
        )
        return pd.DataFrame(index=idx, columns=profile_columns)