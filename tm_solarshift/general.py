"""General module with base Simulation class
"""
from dataclasses import dataclass
from typing import TypedDict

import numpy as np
import pandas as pd

from tm_solarshift.constants import (DEFINITIONS, SIMULATIONS_IO)
from tm_solarshift.utils.units import Variable

from tm_solarshift.utils.location import Location
from tm_solarshift.models.dewh import (DEWH, ResistiveSingle, HeatPump)
from tm_solarshift.models.gas_heater import (GasHeaterInstantaneous, GasHeaterStorage)
from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary
from tm_solarshift.models.pv_system import PVSystem
from tm_solarshift.models import control
from tm_solarshift.timeseries.hwd import HWD
TS_TYPES = SIMULATIONS_IO.TS_TYPES
TS_COLUMNS_ALL = SIMULATIONS_IO.TS_COLUMNS_ALL


class Simulation():
    """
    This is the base class of the repository.
    It has four types of attributes:

    i) Parameters (time_params, location and household),
    ii) Timeseries Generators: Weather and HWDInfo,
    iii) Devices (what is actually simulated, such as DEWH, PV System and Controllers), and
    iv) Output (results of simulation.)
    
    Attributes:

        id (int): Simulation ID. Useful when running multiple simulations.
        time_params (TimeParams): An object containing the temporal variables (START, STOP, STEP, YEAR). It provides some properties such as ``TimeParams.idx`` with the dataframe's DateTimeIndex.
        household (Household): Household() object with information regarding the household.
    
    

    """

    def __init__(self):
        self.id: int = 1

        self.output_dir: str | None = None

        self.time_params: TimeParams = TimeParams()

        self.location: Location = Location("Sydney")
        self.household: Household = Household()

        self.weather: Weather = Weather()
        self.HWDInfo: HWD = HWD.standard_case( _id=self.id )
        
        self.DEWH: DEWH = ResistiveSingle()
        self.pv_system: PVSystem | None = PVSystem()
        self.controller: control.Controller | None = None
        
        self.out: Output = {}


    def __eq__(self, other):
        return self.__dict__ == other.__dict__
    
    
    def load_ts(
        self,
        ts_types: list[str] | str | None = None,
    ) -> pd.DataFrame:
        """It creates a timeseries dataframe with the input of possible simulations. It is useful for timeseries that does not depend on simulation results, such as weather, HWDP, market prices and emissions.

        Args:
            ts_types (list[str] | str | None, optional): timeseries types as defined by DEFINITIONS.TS_TYPES. Defaults to None. If str, it returns only that timeseries. If None, returns all.

        Returns:
            pd.DataFrame: timeseries dataframe.
        """
        
        if isinstance(ts_types, list):
            list_ts_types = ts_types.copy()
        if isinstance(ts_types, str):
            list_ts_types = [ts_types,]
        if ts_types is None:
            list_ts_types = list(SIMULATIONS_IO.TS_TYPES.keys())
        
        location = self.household.location
        ts_index = self.time_params.idx
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
                from tm_solarshift.timeseries import market
                ts_mkt = pd.DataFrame(index=ts_index, columns=TS_TYPES[ts_type])
                ts_mkt = market.load_wholesale_prices(ts_index, location)
                ts_gens.append(ts_mkt)
            
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
        ts = pd.concat(ts_gens, axis=1)
        return ts

    
    def run_simulation(
        self,
        verbose: bool = False,
    ) -> None:
        """Run a simulation using the self containing data.
        
        It update the results into the self.out dictionary (A Output class). The simulation returns *df_pv* (pv simulation results), *df_tm* (DEWH simulation results), *overall_tm* (overall results of thermal parameters), and *overall_econ* (overall results of economic parameters).

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
        self.weather.location = self.household.location         #TODO: define what to do with location
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
            self.controller = control.Timer(timer_type=control_type)
            ts_control = self.controller.create_signal(ts_index)
        elif control_type == "diverter":
            controller = control.Diverter(
                type = control_type,
                time_start=0.,
                time_stop=4.,
                heater_nom_power = self.DEWH.nom_power.get_value("kW")
            )
            ts_control = controller.create_signal(ts_index, df_pv["pv_power"])
        else:
            raise ValueError(f"{control_type=} is not a valid value.")

        # thermal model
        ts_tm = pd.concat([ts_wea, ts_hwd, ts_control], axis=1)
        (df_tm, overall_tm) = self.run_thermal_simulation(ts_tm,verbose=verbose)
        self.out["df_tm"] = df_tm
        self.out["overall_tm"] = overall_tm

        #economic postprocessing
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
        overall_tm = postprocessing.thermal_analysis(self, df_tm)
        return (df_tm, overall_tm)

#------------------------------------
@dataclass
class Household():
    """ Household
    dataclass with information of the household, such as location, tariff_type, size (occupancy) and type of control.

    Parameters:

        tariff_type (str): Tariff type defined by 
        location: City where the simulation is performed.
        control:type: Type of control, the options are: *'CL1'*, *'CL2'*, *'CL1'*, *'GS'*, *'timer'*, and *'diverter'*. If timer or diverter are selected, then the Controller specs need to be defined.
        control_random_on: 

    Property:
        DNSP (str): DNSP associated with the location

    """
    tariff_type: str = "flat"
    location: str = "Sydney"
    control_type: str = "CL1"
    control_random_on: bool = True
    size: int = 4
    old_heater: str | None = None
    new_system: str | None = None

    @property
    def DNSP(self) -> str:
        return DEFINITIONS.LOCATIONS_DNSP[self.location]
    

@dataclass
class Weather():
    """
    Weather generator. It generates weather data for thermal and PV simulations using one of four options depending on the type of simulation. Depending on this options it requires one or more params.
    Check the module timeseries.weather for details.
    """
    type_sim: str = "tmy"
    dataset: str = "meteonorm"
    location: str = "Sydney"
    subset: str | None = None
    random: bool = False
    value: str | int | None = None

    file_path: str | None = None
    list_dates: pd.DatetimeIndex | pd.Timestamp | None = None


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
        """Load data defined by self.params

        Args:
            ts_index (pd.DatetimeIndex): The dataframe's index defined by the simulation.

        Returns:
            pd.DataFrame: A dataframe with the weather timeseries.
        """
        from tm_solarshift.timeseries import weather
        params = self.params()
        ts_wea = weather.load_weather_data(
                    ts_index, type_sim = self.type_sim, params = params
                )
        return ts_wea


#------------------------------------
@dataclass
class TimeParams():
    START = Variable(0, "hr")
    STOP = Variable(8760, "hr")
    STEP = Variable(3, "min")
    YEAR = Variable(2022, "-")

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

    # default case
    sim = Simulation()
    sim.run_simulation()
    print(sim.out)
    
    sim = Simulation()
    sim.HWDInfo.profile_HWD = 1
    sim.household.control_type = "timer_SS"
    sim.DEWH = ResistiveSingle.from_model_file(model = "491315")
    sim.run_simulation()
    print(sim.out)

    sim = Simulation()
    # sim.pv_system = None
    sim.HWDInfo.profile_HWD = 1
    sim.household.control_type = "timer_SS"
    sim.household.tariff_type = "flat"
    sim.DEWH = HeatPump.from_model_file(model = "REHP-CO2-315GL")
    sim.run_simulation()
    print(sim.out)

    sim = Simulation()
    sim.HWDInfo.profile_HWD = 1
    sim.household.control_type = "GS"
    sim.household.tariff_type = "flat"
    sim.DEWH = HeatPump.from_model_file(model = "iStore_270L")
    sim.run_simulation()
    print(sim.out["overall_tm"])
    
    
    sim = Simulation()
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
    print(sim.out["overall_tm"])

    pass



if __name__ == "__main__":
    main()