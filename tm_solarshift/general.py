import numpy as np
import pandas as pd
from typing import Optional, TypedDict

from tm_solarshift.constants import (DEFINITIONS, SIMULATIONS_IO)
from tm_solarshift.utils.units import Variable

from tm_solarshift.utils.location import Location
from tm_solarshift.models.dewh import (ResistiveSingle, HeatPump)
from tm_solarshift.models.gas_heater import (GasHeaterInstantaneous, GasHeaterStorage)
from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary
from tm_solarshift.models.pv_system import PVSystem
from tm_solarshift.models import control
from tm_solarshift.timeseries.hwd import HWD

TS_TYPES = SIMULATIONS_IO.TS_TYPES
TS_COLUMNS_ALL = SIMULATIONS_IO.TS_COLUMNS_ALL

#---------------------
class Simulation():

    def __init__(self):
        self.id = 1
        self.output_dir = None

        self.location = Location("Sydney")
        self.household = Household()

        self.weather = Weather()
        self.HWDInfo = HWD.standard_case( id=self.id )
        
        self.DEWH = ResistiveSingle()
        self.pv_system = PVSystem()
        self.controller: control.Controller | None = None
        
        self.time_params = TimeParams()
        self.out: Output = {}


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
        START = self.time_params.START.get_value("hr")
        STEP = self.time_params.STEP.get_value("min")
        YEAR = self.time_params.YEAR.get_value("-")
        PERIODS = self.time_params.PERIODS.get_value("-")

        start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") + pd.DateOffset(hours=START)
        idx = pd.date_range( start=start_time, periods=PERIODS, freq=f"{STEP}min")
        return pd.DataFrame(index=idx, columns=ts_columns)


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

        from tm_solarshift.timeseries import ( circuits, control, market, weather )
        
        location = self.household.location
        control_type = self.household.control_type
        control_load = self.household.control_load
        random_control = self.household.control_random_on
        tariff_type = self.household.tariff_type
        dnsp = self.household.DNSP
        
        HWD_method = self.HWDInfo.method
        DEWH = self.DEWH
        pv_system = self.pv_system
        YEAR = self.time_params.YEAR.get_value("-")
        ts = self.create_ts_empty(ts_columns = ts_columns)

        # hwd
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
        
        #control
        if control_type == "diverter" and pv_system is not None:
            #Diverter considers three hours at night plus everything diverted from solar
            tz = 'Australia/Brisbane'
            # pv_power = pv_system.load_PV_generation( ts=ts, tz=tz, unit="kW")
            pv_power = pv_system.sim_generation(ts)["pv_power"]
            ts = control.load_schedule(ts, control_load = control_load, random_ON=False)
            heater_nom_power = DEWH.nom_power.get_value("kW")
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
        
        # market
        ts = market.load_wholesale_prices(ts, location)
        ts = market.load_emission_index_year(
            ts, index_type= 'total', location = location, year = YEAR,
        )
        ts = market.load_emission_index_year(
            ts, index_type= 'marginal', location = location, year = YEAR,
        )
        if tariff_type == "gas":
            ts = market.load_household_gas_rate(ts, DEWH)
        else:
            ts = market.load_household_import_rate(
                ts, tariff_type, dnsp,
                return_energy_plan=False,
                control_load=control_load
            )
        
        # circuits
        ts = circuits.load_PV_generation(ts, pv_system = pv_system)
        ts = circuits.load_elec_consumption(ts, profile_elec = 0)

        return ts[ts_columns]
    

    def create_ts_index(self) -> pd.DatetimeIndex:
        """Create an empty the timeseries index (ts_index) for all ts generators.

        Returns:
            pd.DatetimeIndex: ts_index
        """
        START = self.time_params.START.get_value("hr")
        STEP = self.time_params.STEP.get_value("min")
        YEAR = self.time_params.YEAR.get_value("-")
        PERIODS = self.time_params.PERIODS.get_value("-")

        start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") + pd.DateOffset(hours=START)
        ts_index = pd.date_range( start=start_time, periods=PERIODS, freq=f"{STEP}min")
        return ts_index
    
    
    def load_ts(
        self,
        ts_types: list[str] | str | None = None,
    ) -> pd.DataFrame:
        
        from tm_solarshift.timeseries import ( circuits, market )
        
        if isinstance(ts_types, list):
            list_ts_types = ts_types.copy()
        if isinstance(ts_types, str):
            list_ts_types = [ts_types,]
        if ts_types is None:
            list_ts_types = list(SIMULATIONS_IO.TS_TYPES.keys())
        
        location = self.household.location
        DEWH = self.DEWH
        pv_system = self.pv_system

        ts_index = self.create_ts_index()
        ts_gens: list[pd.DataFrame] = []
        for ts_type in list_ts_types:

            if ts_type == "weather":
                ts_wea = self.weather.load_data(ts_index)
                ts_gens.append(ts_wea)

            elif ts_type == "HWDP":
                HWD_method = self.HWDInfo.method
                ts_hwd = self.HWDInfo.generator(ts_index, method = HWD_method)
                ts_gens.append(ts_hwd)
            
            elif ts_type == "economic":
                tariff_type = self.household.tariff_type
                dnsp = self.household.DNSP
                control_type = self.household.control_type
                ts_econ = pd.DataFrame(index=ts_index, columns=TS_TYPES[ts_type])
                ts_econ = market.load_wholesale_prices(ts_econ, location)
                if tariff_type == "gas":
                    ts_econ = market.load_household_gas_rate(ts_econ, DEWH)
                else:
                    ts_rate = market.load_household_import_rate(
                        ts_econ.index,
                        tariff_type = tariff_type,
                        dnsp = dnsp,
                        control_type = control_type
                    )
                    ts_econ["tariff"] = ts_rate["tariff"]
                    ts_econ["rate_type"] = ts_rate["rate_type"]
                ts_gens.append(ts_econ)
            
            elif ts_type == "emissions":
                YEAR = self.time_params.YEAR.get_value("-")
                ts_emi = pd.DataFrame(index=ts_index, columns=TS_TYPES[ts_type])
                ts_emi = market.load_emission_index_year(
                    ts_emi, index_type= 'total', location = location, year = YEAR,
                )
                ts_emi = market.load_emission_index_year(
                    ts_emi, index_type= 'marginal', location = location, year = YEAR,
                )
                ts_gens.append(ts_emi)

            elif ts_type == "electric":
                ts_elec = pd.DataFrame(index=ts_index, columns=TS_TYPES[ts_type])
                ts_elec = circuits.load_PV_generation(ts_elec, pv_system = pv_system)
                ts_elec = circuits.load_elec_consumption(ts_elec, profile_elec = 0)
                ts_gens.append(ts_elec)

        ts = pd.concat(ts_gens, axis=1)
        return ts

    
    def run_simulation(
        self,
        verbose: bool = False,
    ) -> None:
        """Run a simulation using the data provided in self.

        Args:
            verbose (bool, optional): Print stage of sim. Defaults to False.

        Raises:
            TypeError: DEWH object and thermal model engine are not compatible

        Returns:
            None
        """

        from tm_solarshift.models import postprocessing

        self.out: Output = {}
        ts_index = self.time_params.idx
        ts_wea = self.weather.load_data(ts_index)
        ts_hwd = self.HWDInfo.generator(ts_index, method = self.HWDInfo.method)

        #pv system
        pv_system = self.pv_system
        if pv_system is not None:
            df_pv = pv_system.sim_generation(ts_wea, columns=SIMULATIONS_IO.OUTPUT_SIM_PV)
        else:
            df_pv = pd.DataFrame(0, index=self.time_params.idx, columns=SIMULATIONS_IO.OUTPUT_SIM_PV)
        self.out["df_pv"] = df_pv

        # control
        control_type = self.household.control_type
        if control_type in ["GS", "CL1", "CL2", "CL3"]:
            self.controller = control.CLController(
                CL_type = control_type,
                random_delay = self.household.control_random_on,
                random_seed = self.id
            )
            ts_control = self.controller.create_signal(ts_index)
        elif control_type in ["timer_SS", "timer_OP", "timer"]:
            self.controller = control.Timer(timer_type = control_type)
            ts_control = self.controller.create_signal(ts_index)
        elif control_type == "diverter":
            controller = control.Diverter(
                type = control_type,
                time_start=0.,
                time_stop=4.,
                heater_nom_power = self.DEWH.nom_power.get_value("kW")
            )
            ts_control = controller.create_signal(ts_index, df_pv["pv_power"])

        # thermal model
        ts_tm = pd.concat([ts_wea, ts_hwd, ts_control], axis=1)
        (df_tm, overall_tm) = self.run_thermal_simulation(ts_tm,verbose=verbose)
        self.out["df_tm"] = df_tm
        self.out["overall_tm"] = overall_tm

        # ts_econ = self.load_ts(ts_types=SIMULATIONS_IO.TS_TYPES_ECO)
        self.out["overall_econ"] = postprocessing.economics_analysis(self)
        return None


    def run_thermal_simulation(
            self,
            ts: pd.DataFrame | None = None,
            verbose: bool = False,
    ) -> tuple[pd.DataFrame, dict]:
        """Run a thermal simulation using the data provided in self.

        Args:
            ts (pd.DataFrame, optional): timeseries dataframe. If not given is generated. Defaults to None.
            verbose (bool, optional): Print stage of sim. Defaults to False.

        Raises:
            TypeError: DEWH object and thermal model engine are not compatible

        Returns:
            tuple[pd.DataFrame, dict]: (df_tm, overall_tm) = (detailed results, overall results)
        """

        from tm_solarshift.models import postprocessing
        DEWH = self.DEWH
        if ts is None:
            ts_tm = self.load_ts(ts_types=SIMULATIONS_IO.TS_TYPES_TM+["emissions"])
        else:
            ts_tm = ts.copy()

        
        df_tm = DEWH.run_thermal_model(ts_tm, verbose=verbose)
        overall_tm = postprocessing.thermal_analysis(self, ts_tm, df_tm)
        # if isinstance(DEWH, ResistiveSingle | HeatPump | GasHeaterInstantaneous | GasHeaterStorage):
        #     df_tm = DEWH.run_thermal_model(ts_tm, verbose=verbose)
        #     overall_tm = postprocessing.thermal_analysis(self, ts_tm, df_tm)
        # elif isinstance(DEWH, SolarThermalElecAuxiliary):
        #     from tm_solarshift.models import solar_thermal
        #     (df_tm, overall_tm) = solar_thermal.run_thermal_model(self, ts_tm, verbose=verbose)
        # else:
        #     ValueError("Not a valid type for DEWH")
        return (df_tm, overall_tm)

#------------------------------------
class Household():
    def __init__(
            self,
            location: Location = Location("Sydney"),
        ):

        self.tariff_type = "flat"
        self.location = location.value
        self.control_type = "CL1"
        # self.control_load = 1
        self.control_random_on = True

        # self.heater_type = "resistive"
        self.size = 4
        self.has_solar = False
        self.old_heater = False
        self.new_system = False

    @property
    def DNSP(self) -> str:
        return DEFINITIONS.LOCATIONS_DNSP[self.location]


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
        
        self.file_path: str | None = None
        self.list_dates: pd.DatetimeIndex | pd.Timestamp | None = None
    

    def params(self) -> dict:
        if self.type_sim == "tmy":
            params = {
                "dataset": self.dataset,
                "location": self.location,
            }
        elif self.type_sim == "mc":
            params = {
                "dataset": self.dataset,
                "location": self.location,
                "subset": self.subset,
                "random": self.random,
                "value": self.value,
            }
        elif self.type_sim == "historical":
            params = {
                "dataset": self.dataset,
                "location": self.location,
                "file_path": self.file_path,
                "list_dates": self.list_dates,
            },
        elif self.type_sim == "constant_day":
            params = {
                "dataset": self.dataset,
                "random": self.random,
                "value": self.value,
                "subset": self.subset,
        }
        return params
    

    def load_data(self, ts_index: pd.DatetimeIndex) -> pd.DataFrame:
        from tm_solarshift.timeseries import weather
        ts_wea = weather.load_weather_data(
                    ts_index, type_sim = self.type_sim, params = self.params()
                )
        return ts_wea


#------------------------------------
class TimeParams():
    def __init__(self):
        self.START = Variable(0, "hr")
        self.STOP = Variable(8760, "hr")
        self.STEP = Variable(3, "min")
        self.YEAR = Variable(2022, "-")

    @property
    def DAYS(self) -> Variable:
        START = self.START.get_value("hr")
        STOP = self.STOP.get_value("hr")
        return Variable( int((STOP-START)/24), "d")
    
    @property
    def PERIODS(self) -> Variable:
        START = self.START.get_value("hr")
        STOP = self.STOP.get_value("hr")
        STEP_h = self.STEP.get_value("hr")
        return Variable( int(np.ceil((STOP - START)/STEP_h)), "-")

    @property
    def idx(self) -> pd.DatetimeIndex:
        START = self.START.get_value("hr")
        STEP = self.STEP.get_value("min")
        YEAR = self.YEAR.get_value("-")
        PERIODS = self.PERIODS.get_value("-")
        start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") + pd.DateOffset(hours=START)
        idx = pd.date_range( start=start_time, periods=PERIODS, freq=f"{STEP}min")
        return idx


class Output(TypedDict, total=False):
    df_pv: pd.DataFrame
    df_tm: pd.DataFrame
    overall_tm: dict[str,float]
    overall_econ: dict[str,float]


#-----------
def main():

    sim = Simulation()
    # sim.pv_system = None
    sim.HWDInfo.profile_HWD = 1
    sim.household.control_type = "GS"
    sim.household.tariff_type = "flat"
    sim.DEWH = SolarThermalElecAuxiliary()
    sim.run_simulation()
    print(sim.out["overall_tm"])
    print(sim.out["overall_econ"])

    sim = Simulation()
    # sim.pv_system = None
    sim.HWDInfo.profile_HWD = 1
    sim.household.control_type = "GS"
    sim.household.tariff_type = "flat"
    sim.DEWH = GasHeaterInstantaneous()
    sim.run_simulation()
    sim.DEWH.postproc(df_tm=sim.out["df_tm"])
    print(sim.out["overall_tm"])

    sim = Simulation()
    # sim.pv_system = None
    sim.HWDInfo.profile_HWD = 1
    sim.household.control_type = "GS"
    sim.household.tariff_type = "flat"
    sim.DEWH = HeatPump.from_model_file(model = "iStore_270L")
    sim.run_simulation()
    print(sim.out["overall_tm"])
    
    sim = Simulation()
    # sim.pv_system = None
    sim.HWDInfo.profile_HWD = 1
    sim.household.control_type = "GS"
    sim.household.tariff_type = "flat"
    sim.DEWH = HeatPump.from_model_file(model = "REHP-CO2-315GL")
    sim.run_simulation()
    print(sim.out)

    pass

    # sim.DEWH = ResistiveSingle()
    # sim.DEWH = GasHeaterStorage()
    # sim.DEWH = SolarThermalElecAuxiliary()
    # (out_all, out_overall) = sim.run_thermal_simulation( verbose=True )
    # print(out_all)
    # print(out_overall)
    
    return

if __name__ == "__main__":
    main()