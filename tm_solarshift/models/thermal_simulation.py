import numpy as np
import pandas as pd

from tm_solarshift.constants import SIMULATIONS_IO
from tm_solarshift.utils.location import Location
from tm_solarshift.utils.units import Variable

#------------------------------------
class ThermalSimulation():
    def __init__(self):

        #general
        self.type_sim = "annual"
        self.location = Location()
        self.engine = "trnsys"
        self.START = Variable(0, "hr")
        self.STOP = Variable(8760, "hr")
        self.STEP = Variable(3, "min")
        self.YEAR = Variable(2022, "-")

        #weather
        self.params_weather = {
            "dataset": "meteonorm",
            "location": None,
            "subset" : None,
            "random" : False,
            "value" : np.nan,
        }

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

    @property
    def data(self) -> pd.DataFrame:

        START = self.START.get_value("hr")
        STEP = self.STEP.get_value("min")
        YEAR = self.YEAR.get_value("-")
        PERIODS = self.PERIODS.get_value("-")
        start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") + pd.DateOffset(hours=START)
        idx = pd.date_range( start=start_time, periods=PERIODS, freq=f"{STEP}min")

        return pd.DataFrame(index=idx, columns=SIMULATIONS_IO.TS_COLUMNS_ALL)