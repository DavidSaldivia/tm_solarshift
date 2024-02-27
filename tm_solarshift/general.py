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
from tm_solarshift.weather import Location

#------------------------------------
class GeneralSetup():
    def __init__(self):

        self.household = Household()
        self.DEWH = ResistiveSingle()
        self.solar_system = SolarSystem()
        self.HWDInfo = HWD.standard_case()
        self.simulation = ThermalSimulation()

#------------------------------------
class Household():
    def __init__(self):

        self.tariff_type = "flat"
        self.DNSP = "Ausgrid"
        self.location = "Sydney"
        self.control_load = 1
        self.control_random_on = True

#------------------------------------
class ThermalSimulation():
    def __init__(self):
        self.location = Location()
        self.engine = "TRNSYS",
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

#-----------------------------
def load_timeseries_all(
        GS: GeneralSetup,
) -> pd.DataFrame:
    
    import tm_solarshift.circuits as circuits
    import tm_solarshift.external_data as external_data
    import tm_solarshift.weather as weather
    Weather = weather.Weather
    
    from tm_solarshift.circuits import (ControlledLoad, Circuits)
    ControlledLoad = circuits.ControlledLoad

    location = GS.household.location
    control_load = GS.household.control_load
    random_control = GS.household.control_random_on
    YEAR = GS.simulation.YEAR.get_value("-")

    ts = GS.simulation.create_new_profile()
    ts = GS.HWDInfo.generator(ts, method="standard")
    
    file_path = Weather.FILES["METEONORM_TEMPLATE"].format(location)
    ts = weather.from_file( ts, file_path )

    ts = external_data.load_emission_index_year(
        ts, 
        index_type= 'total',
        location = location,
        year=YEAR,
    )
    ts = external_data.load_wholesale_prices(ts, location)

    ts = ControlledLoad.load_schedule(ts, profile_control = control_load, random_ON = random_control)
    ts = Circuits.load_PV_generation(ts, GS.solar_system)
    ts = Circuits.load_elec_consumption(ts)

    return ts

#-----------
def main():

    from tm_solarshift.thermal_models import trnsys

    GS = GeneralSetup()
    GS.household.control_load = 4

    ts = GS.simulation.create_new_profile()
    ts = load_timeseries_all(GS)
    print(ts.head(20))
    print(ts[PROFILES.TYPES["HWDP"]])
    print(ts[PROFILES.TYPES["weather"]])
    print(ts[PROFILES.TYPES["control"]])

    out_all = trnsys.run_simulation(GS, ts, verbose=True)
    print(out_all)
    out_overall = trnsys.postprocessing_annual_simulation(GS, ts, out_all)
    print(out_overall)
    
    return

if __name__ == "__main__":
    main()