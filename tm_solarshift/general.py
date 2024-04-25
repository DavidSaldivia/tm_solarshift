import numpy as np
import pandas as pd

from tm_solarshift.constants import (DEFINITIONS, SIMULATIONS_IO)

from tm_solarshift.utils.units import Variable
from tm_solarshift.utils.location import Location

from tm_solarshift.timeseries.hwd import HWD

from tm_solarshift.devices import (
    ResistiveSingle,
    HeatPump,
    GasHeaterInstantaneous,
    GasHeaterStorage,
    SolarThermalElecAuxiliary,
    SolarSystem,
)

TS_TYPES = SIMULATIONS_IO.TS_TYPES
TS_COLUMNS_ALL = SIMULATIONS_IO.TS_COLUMNS_ALL

#------------------------------------
class GeneralSetup():

    def __init__(self):
        self.id = np.random.SeedSequence().entropy
        self.household = Household()
        self.DEWH = ResistiveSingle()
        self.solar_system = SolarSystem()
        self.HWDInfo = HWD.standard_case( id=self.id )
        self.simulation = ThermalSimulation()

    #---------------
    def create_ts_empty(
        self,
        ts_columns: list[str] = TS_COLUMNS_ALL,
    ) -> pd.DataFrame:
        """Create an empty timeseries dataframe (ts).
        Useful to populate ts manually

        Args:
            ts_columns (list[str], optional): columns to include. Defaults to TS_COLUMNS_ALL.

        Returns:
            pd.DataFrame: ts (timeseries dataframe)
        """
        START = self.simulation.START.get_value("hr")
        STEP = self.simulation.STEP.get_value("min")
        YEAR = self.simulation.YEAR.get_value("-")
        PERIODS = self.simulation.PERIODS.get_value("-")

        start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") + pd.DateOffset(hours=START)
        idx = pd.date_range( start=start_time, periods=PERIODS, freq=f"{STEP}min")
        return pd.DataFrame(index=idx, columns=ts_columns)


    #---------------
    def create_ts(
        self,
        ts_columns: list[str] = TS_COLUMNS_ALL,
    ) -> pd.DataFrame:
        """
        Create a timeseries dataframe (ts) using the information in self.
        Check the specific functions to get more information about definition process.

        Args:
            ts_columns (list[str], optional): columns to show in ts. Defaults to TS_COLUMNS_ALL.

        Returns:
            pd.DataFrame: ts, the timeseries dataframe.
        """

        import tm_solarshift.timeseries.circuits as circuits
        import tm_solarshift.timeseries.control as control
        import tm_solarshift.timeseries.market as market
        import tm_solarshift.timeseries.weather as weather
        
        location = self.household.location
        control_load = self.household.control_load
        random_control = self.household.control_random_on
        tariff_type = self.household.tariff_type
        dnsp = self.household.DNSP

        solar_system = self.solar_system
        type_sim = self.simulation.type_sim
        YEAR = self.simulation.YEAR.get_value("-")
        HWD_method = self.HWDInfo.method

        self.simulation.params_weather["location"] = location
        type_sim_weather = DEFINITIONS.WEATHER_SIMULATIONS[type_sim]
        params_weather = self.simulation.params_weather

        ts = self.create_ts_empty(ts_columns = ts_columns)

        ts = self.HWDInfo.generator(ts, method = HWD_method)
        ts = weather.load_weather_data( ts, type_sim = type_sim_weather, params = params_weather )
        ts = control.load_schedule(ts, control_load = control_load, random_ON = random_control)
        
        ts = circuits.load_PV_generation(ts, solar_system = solar_system)
        ts = circuits.load_elec_consumption(ts, profile_elec = 0)

        ts = market.load_wholesale_prices(ts, location)
        ts = market.load_emission_index_year(
            ts, index_type= 'total', location = location, year = YEAR,
        )
        ts = market.load_emission_index_year(
            ts, index_type= 'marginal', location = location, year = YEAR,
        )

        if tariff_type == "gas":
            ts = market.load_household_gas_rate(ts, self.DEWH)
        else:
            ts = market.load_household_import_rate(
                ts, tariff_type, dnsp,
                return_energy_plan=False,
                control_load=control_load
            )
            
        return ts[ts_columns]
    
    #-------------------
    def run_thermal_simulation(
            self,
            ts: pd.DataFrame = None,
            verbose: bool = False,
    ) -> tuple[pd.DataFrame, dict]:
        """Run a thermal simulation using the data provided in self.

        Args:
            ts (pd.DataFrame, optional): timeseries dataframe. If not given is calculated with self. Defaults to None.
            verbose (bool, optional): Print stage of simulation. Defaults to False.

        Raises:
            TypeError: DEWH object and thermal model engine are not compatible

        Returns:
            tuple[pd.DataFrame, dict]: (out_all, out_overall) = (detailed results, overall results)
        """
        
        if ts is None:
            ts = self.create_ts()
        
        DEWH = self.DEWH
        
        if (DEWH.__class__ == ResistiveSingle):
            from tm_solarshift.thermal_models import trnsys
            from tm_solarshift.utils import postprocessing
            self.simulation.engine = "trnsys"
            out_all = trnsys.run_simulation(self, ts, verbose=verbose)
            out_overall = postprocessing.annual_simulation(self, ts, out_all)
        
        elif (DEWH.__class__ == HeatPump):
            from tm_solarshift.thermal_models import trnsys
            from tm_solarshift.utils import postprocessing 
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

        return pd.DataFrame(index=idx, columns=TS_COLUMNS_ALL)

#-----------
def main():

    GS = GeneralSetup()
    ts = GS.create_ts_empty()
    ts = GS.create_ts()

    print(ts.head(20))
    print(ts[TS_TYPES["HWDP"]])
    print(ts[TS_TYPES["weather"]])
    print(ts[TS_TYPES["control"]])

    out_overall = GS.run_thermal_simulation( ts, verbose=True )
    print(out_overall)
    
    return

if __name__ == "__main__":
    main()