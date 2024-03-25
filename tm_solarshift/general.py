import numpy as np
import pandas as pd
from typing import (List, Tuple, Dict)

from tm_solarshift.constants import DEFINITIONS
from tm_solarshift.units import Variable
from tm_solarshift.hwd import HWD
from tm_solarshift.weather import Location

import tm_solarshift.circuits as circuits
import tm_solarshift.control as control
import tm_solarshift.external_data as external_data
import tm_solarshift.weather as weather

from tm_solarshift.devices import (
    ResistiveSingle,
    HeatPump,
    GasHeaterInstantaneous,
    GasHeaterStorage,
    SolarThermalElecAuxiliary,
    SolarSystem,
)

TS_TYPES = DEFINITIONS.TS_TYPES
TS_COLUMNS_ALL = DEFINITIONS.TS_COLUMNS_ALL

#------------------------------------
class GeneralSetup():

    def __init__(self):
        self.household = Household()
        self.DEWH = ResistiveSingle()
        self.solar_system = SolarSystem()
        self.HWDInfo = HWD.standard_case()
        self.simulation = ThermalSimulation()


    def create_ts_empty(
        self,
        ts_columns: List[str] = TS_COLUMNS_ALL,
    ) -> pd.DataFrame:

        START = self.simulation.START.get_value("hr")
        STEP = self.simulation.STEP.get_value("min")
        YEAR = self.simulation.YEAR.get_value("-")
        PERIODS = self.simulation.PERIODS.get_value("-")
        start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") + pd.DateOffset(hours=START)
        idx = pd.date_range( start=start_time, periods=PERIODS, freq=f"{STEP}min")

        return pd.DataFrame(index=idx, columns=ts_columns)


    def create_ts_default(
        self,
        ts_columns: List[str] = TS_COLUMNS_ALL,
    ) -> pd.DataFrame:
        location = self.household.location
        control_load = self.household.control_load
        random_control = self.household.control_random_on
        solar_system = self.solar_system
        
        YEAR = self.simulation.YEAR.get_value("-")

        ts = self.create_ts_empty(ts_columns = ts_columns)
        ts = self.HWDInfo.generator(ts, method = "standard")
        
        file_path = weather.FILES_WEATHER["METEONORM_TEMPLATE"].format(location)
        ts = weather.from_file( ts, file_path )

        ts = control.load_schedule(ts, control_load = control_load, random_ON = random_control)
        ts = circuits.load_PV_generation(ts, solar_system = solar_system)
        ts = circuits.load_elec_consumption(ts, profile_elec = 0)
        ts = external_data.load_wholesale_prices(ts, location)
        ts = external_data.load_emission_index_year(
            ts, index_type= 'total', location = location, year = YEAR,
        )
        return ts[ts_columns]
    
    #-------------------
    def run_thermal_simulation(
            self,
            ts: pd.DataFrame = None,
            verbose: bool = False,
    ) -> Tuple[pd.DataFrame, Dict]:
        
        if ts is None:
            ts = self.create_ts_default()
        
        DEWH = self.DEWH
        
        if (DEWH.__class__ == ResistiveSingle):
            import tm_solarshift.thermal_models.trnsys as trnsys
            from tm_solarshift.thermal_models import postprocessing
            self.simulation.engine = "trnsys"
            out_all = trnsys.run_simulation(self, ts, verbose=verbose)
            out_overall = postprocessing.annual_simulation(self, ts, out_all)
        
        elif (DEWH.__class__ == HeatPump):
            import tm_solarshift.thermal_models.trnsys as trnsys
            from tm_solarshift.thermal_models import postprocessing
            self.simulation.engine = "trnsys"
            out_all = trnsys.run_simulation(self, ts, verbose=verbose)
            out_overall = postprocessing.annual_simulation(self, ts, out_all)

        elif (DEWH.__class__ == GasHeaterInstantaneous):
            self.simulation.engine = "own"
            import tm_solarshift.thermal_models.gas_heater as gas_heater
            (out_all, out_overall) = gas_heater.instantaneous_fixed_eta(DEWH, ts, verbose=verbose)
        
        elif (DEWH.__class__ == GasHeaterStorage):
            self.simulation.engine = "trnsys"
            import tm_solarshift.thermal_models.gas_heater as gas_heater
            (out_all, out_overall) = gas_heater.storage_fixed_eta(self, ts, verbose=verbose)

        elif self.DEWH.__class__ == SolarThermalElecAuxiliary:
            self.simulation.engine = "trnsys"
            import tm_solarshift.thermal_models.solar_thermal as solar_thermal
            (out_all, out_overall) = solar_thermal.run_thermal_model(self, ts, verbose=verbose)
        
        else:
            raise TypeError("DEWH class is not supported with any engine.")

        return (out_all, out_overall)

#------------------------------------
class Household():
    def __init__(self):

        self.tariff_type = "flat"
        self.DNSP = "Ausgrid"
        self.location = "Sydney"
        self.control_type = "CL"
        self.control_load = 1
        self.control_random_on = True

#------------------------------------
class ThermalSimulation():
    def __init__(self):
        self.location = Location()
        self.engine = "trnsys"
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

    @property
    def data(self) -> pd.DataFrame:

        START = self.START.get_value("hr")
        STEP = self.STEP.get_value("min")
        YEAR = self.YEAR.get_value("-")
        PERIODS = self.PERIODS.get_value("-")
        start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") + pd.DateOffset(hours=START)
        idx = pd.date_range( start=start_time, periods=PERIODS, freq=f"{STEP}min")

        return pd.DataFrame(index=idx, columns=TS_COLUMNS_ALL)
# #-----------------------------
# def load_timeseries_all(
#         GS: GeneralSetup,
# ) -> pd.DataFrame:
    
#     import tm_solarshift.circuits as circuits
#     import tm_solarshift.control as control
#     import tm_solarshift.external_data as external_data
#     import tm_solarshift.weather as weather
    
#     location = GS.household.location
#     control_load = GS.household.control_load
#     random_control = GS.household.control_random_on
#     solar_system = GS.solar_system
    
#     YEAR = GS.simulation.YEAR.get_value("-")

#     ts = GS.simulation.create_new_profile()
#     ts = GS.HWDInfo.generator(ts, method="standard")
    
#     file_path = weather.FILES_WEATHER["METEONORM_TEMPLATE"].format(location)
#     ts = weather.from_file( ts, file_path )

#     ts = control.load_schedule(ts, control_load = control_load, random_ON = random_control)
#     ts = circuits.load_PV_generation(ts, solar_system = solar_system)
#     ts = circuits.load_elec_consumption(ts, profile_elec = 0)
#     ts = external_data.load_wholesale_prices(ts, location)
#     ts = external_data.load_emission_index_year(
#         ts, index_type= 'total', location = location, year=YEAR,
#     )
#     return ts

#-----------
def main():

    GS = GeneralSetup()
    ts = GS.create_ts_empty()
    ts = GS.create_ts_default()

    print(ts.head(20))
    print(ts[TS_TYPES["HWDP"]])
    print(ts[TS_TYPES["weather"]])
    print(ts[TS_TYPES["control"]])

    out_overall = GS.run_thermal_simulation( ts, verbose=True )
    print(out_overall)
    
    return

if __name__ == "__main__":
    main()