import numpy as np
import pandas as pd
from typing import Optional

from tm_solarshift.constants import SIMULATIONS_IO
from tm_solarshift.utils.units import Variable

from tm_solarshift.utils.location import Location
from tm_solarshift.models.dewh import (ResistiveSingle, HeatPump)
from tm_solarshift.models.gas_heater import (GasHeaterInstantaneous, GasHeaterStorage)
from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary
from tm_solarshift.models.pv_system import PVSystem
from tm_solarshift.timeseries.hwd import HWD

TS_TYPES = SIMULATIONS_IO.TS_TYPES
TS_COLUMNS_ALL = SIMULATIONS_IO.TS_COLUMNS_ALL

#---------------------
class Simulation():

    def __init__(self):
        self.id = 1
        self.seed = None
        self.location = Location("Sydney")
        self.household = Household()
        self.DEWH = ResistiveSingle()
        self.pv_system = PVSystem()
        self.HWDInfo = HWD.standard_case( id=self.id )
        self.thermal_sim = ThermalSim()
        self.weather = Weather()

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
    
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
        START = self.thermal_sim.START.get_value("hr")
        STEP = self.thermal_sim.STEP.get_value("min")
        YEAR = self.thermal_sim.YEAR.get_value("-")
        PERIODS = self.thermal_sim.PERIODS.get_value("-")

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

        from tm_solarshift.timeseries import (
            circuits,
            control,
            market,
            weather,
        )
        
        location = self.household.location
        control_type = self.household.control_type
        control_load = self.household.control_load
        random_control = self.household.control_random_on
        tariff_type = self.household.tariff_type
        dnsp = self.household.DNSP
        
        pv_system = self.pv_system
        YEAR = self.thermal_sim.YEAR.get_value("-")

        # hwd
        HWD_method = self.HWDInfo.method
        ts = self.create_ts_empty(ts_columns = ts_columns)
        ts = self.HWDInfo.generator(ts, method = HWD_method)
        
        # weather
        type_sim = self.weather.type_sim
        params_weather = {
                "dataset": self.weather.dataset,
                "location": self.weather.location,
                "subset": self.weather.subset,
                "random": self.weather.random,
                "value": self.weather.value,
        }
        ts = weather.load_weather_data(ts, type_sim = type_sim, params = params_weather)
        
        # market
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
        
        # circuits
        ts = circuits.load_PV_generation(ts, pv_system = pv_system)
        ts = circuits.load_elec_consumption(ts, profile_elec = 0)
        if control_type == "diverter" and pv_system is not None:
            #Diverter considers three hours at night plus everything diverted from solar
            tz = 'Australia/Brisbane'
            # pv_power = pv_system.load_PV_generation( ts=ts, tz=tz, unit="kW")
            pv_power = pv_system.sim_generation(ts)["pv_power"]
            ts = control.load_schedule(ts, control_load = control_load, random_ON=False)
            heater_nom_power = self.DEWH.nom_power.get_value("kW")
            ts["CS"] = np.where(
                ts["CS"]>=0.99,
                ts["CS"],
                np.where(
                    (pv_power > 0) & (pv_power < heater_nom_power),
                    pv_power / heater_nom_power,
                    np.where(pv_power > heater_nom_power, 1., 0.)
                )
            )
        else:
            ts = control.load_schedule(ts, control_load = control_load, random_ON = random_control)

        return ts[ts_columns]
    
    #-------------------
    def run_thermal_simulation(
            self,
            ts: Optional[pd.DataFrame] = None,
            verbose: bool = False,
    ) -> tuple[pd.DataFrame, dict]:
        """Run a thermal simulation using the data provided in self.

        Args:
            ts (pd.DataFrame, optional): timeseries dataframe. If not given is calculated with self. Defaults to None.
            verbose (bool, optional): Print stage of sim. Defaults to False.

        Raises:
            TypeError: DEWH object and thermal model engine are not compatible

        Returns:
            tuple[pd.DataFrame, dict]: (out_all, out_overall) = (detailed results, overall results)
        """

        from tm_solarshift.models import postprocessing

        if ts is None:
            ts = self.create_ts()

        DEWH = self.DEWH
        match DEWH.label:
            case "resistive":
                out_all = DEWH.run_thermal_model(ts, verbose=verbose)
                out_overall = postprocessing.annual_postproc(self, ts, out_all)
            case "heat_pump":
                out_all = DEWH.run_thermal_model(ts, verbose=verbose)
                out_overall = postprocessing.annual_postproc(self, ts, out_all)
            case "gas_instant":
                (out_all, out_overall) = DEWH.run_thermal_model(ts, verbose=verbose)
            case "solar_thermal":
                from tm_solarshift.models import solar_thermal
                (out_all, out_overall) = solar_thermal.run_thermal_model(self, verbose=verbose)
            case "gas_storage":
                from tm_solarshift.models import gas_heater
                (out_all, out_overall) = gas_heater.storage_fixed_eta(self,ts=ts, verbose=verbose)
            case _:
                raise ValueError("Not a valid type for DEWH.")

        return (out_all, out_overall)

#------------------------------------
class Household():
    def __init__(
            self,
            location: Location = Location("Sydney"),
        ):

        self.tariff_type = "flat"
        self.DNSP = "Ausgrid"
        self.location = "Sydney"
        self.control_type = "CL"
        self.control_load = 1
        self.control_random_on = True

        self.heater_type = "resistive"
        self.size = 4
        self.has_solar = False
        self.old_heater = False
        self.new_system = False

class Weather():
    def __init__(
            self,
            location: Location = Location("Sydney")
    ):
        self.type_sim = "tmy"
        self.dataset = "meteonorm"
        self.location = location.value
        self.subset = None
        self.random = False
        self.value = None

#------------------------------------
class ThermalSim():
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

    @property
    def df(self) -> pd.DataFrame:
        START = self.START.get_value("hr")
        STEP = self.STEP.get_value("min")
        YEAR = self.YEAR.get_value("-")
        PERIODS = self.PERIODS.get_value("-")
        start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") + pd.DateOffset(hours=START)
        idx = pd.date_range( start=start_time, periods=PERIODS, freq=f"{STEP}min")

        return pd.DataFrame(index=idx, columns=TS_COLUMNS_ALL)

#-----------
#-----------
def main():

    sim = Simulation()
    ts = sim.create_ts_empty()
    ts = sim.create_ts()

    # print(ts.head(20))
    # print(ts[TS_TYPES["HWDP"]])
    # print(ts[TS_TYPES["weather"]])
    # print(ts[TS_TYPES["control"]])

    sim.DEWH = SolarThermalElecAuxiliary()
    sim.DEWH = ResistiveSingle()
    (out_all, out_overall) = sim.run_thermal_simulation( verbose=True )
    print(out_all)
    print(out_overall)
    
    return

if __name__ == "__main__":
    main()