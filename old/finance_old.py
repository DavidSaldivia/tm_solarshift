import os
import numpy as np
import pandas as pd
from typing import Union, Any, TypeAlias

from tm_solarshift.general import Simulation
from tm_solarshift.constants import SIMULATIONS_IO
from tm_solarshift.utils.units import conversion_factor as CF
FIN_POSTPROC_OUTPUT = SIMULATIONS_IO.FIN_POSTPROC_OUTPUT

from tm_solarshift.models.dewh import (ResistiveSingle, HeatPump)
from tm_solarshift.models.gas_heater import (GasHeaterInstantaneous, GasHeaterStorage)
from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary

Heater: TypeAlias = Union[
    ResistiveSingle,
    HeatPump,
    GasHeaterInstantaneous,
    GasHeaterStorage,
    SolarThermalElecAuxiliary
]

TYPE_HEATERS = {
    "resistive": ResistiveSingle,
    "heat_pump": HeatPump,
    "gas_instant": GasHeaterInstantaneous,
    "gas_storage": GasHeaterStorage,
    "solar_thermal": SolarThermalElecAuxiliary
}


LIST_HOUSEHOLD_SIZES = [1, 2, 3, 4, 5]
LIST_HWDP = [1, 2, 3, 4, 5, 6]
LIST_DNSP = ["Ausgrid"]
RESISTIVE_SUPPLY_STATES = ["NSW", "QLD", "VIC"]

#------------------------
def calculate_household_energy_cost(
        sim: Simulation,
        ts: pd.DataFrame = None,
        df_tm: pd.DataFrame = None,
        ) -> float:

    STEP_h = sim.ts.STEP.get_value("hr")
    if ts  is None:
        ts = sim.create_ts()

    if df_tm  is None:
        df_tm = sim.run_thermal_simulation(ts)

    heater_power = df_tm["heater_power"] * CF("kJ/h", "kW")

    if sim.pv_system == None:
        imported_energy = heater_power.copy()
    else:    
        tz = 'Australia/Brisbane'
        pv_power = sim.pv_system.load_PV_generation(
            ts=ts, tz=tz,  unit="kW"
        )
        imported_energy = np.where(
            pv_power < heater_power, heater_power - pv_power, 0
        )

    energy_cost = ( ts["tariff"] * imported_energy * STEP_h  ).sum()
    return energy_cost

#-----------------------
def calculate_wholesale_energy_cost(
        sim: Simulation,
        ts: pd.DataFrame = None,
        df_tm: pd.DataFrame = None,
        ) -> float:
    
    STEP_h = sim.ts.STEP.get_value("hr")

    if ts is None:
        ts = sim.create_ts()
    if df_tm is None:
        df_tm = sim.run_thermal_simulation(ts)
        
    heater_power = df_tm["heater_power"] * CF("kJ/h", "MW")
    energy_cost = ( ts["wholesale_market"] * heater_power * STEP_h).sum()
    return energy_cost

#------------------------
def calculate_annual_bill(
        sim: Simulation,
        ts: pd.DataFrame = None,
        df_tm: pd.DataFrame = None,
        has_solar: bool = False,
    ) -> float:
    
    # calculate annual energy cost
    annual_bill = calculate_household_energy_cost(sim, ts, df_tm)

    # add other costs (daily/seasonal costs)
    annual_bill = annual_bill + 0.1*365  #(0.1AUD per day, just a random number)
    
    return annual_bill

#-----------------
def calculate_oandm_cost(
        sim: Simulation,
        ts: pd.DataFrame = None,
        df_tm: pd.DataFrame = None,
        has_solar: bool = False,
    ) -> float:
    
    # include operation, maintance, re-purchase, etc.

    oandm_cost = 0.0

    return oandm_cost

#-----------------
def calculate_capital_cost(
        DEWH: Heater,
):
    #include all capital costs: equipment, installation, certification, etc.

    #copy ruby's code here
    try:
        FILE_CAPITAL_COSTS = ""
        capital_cost = pd.read_csv(FILE_CAPITAL_COSTS, index_col=0).loc(
            DEWH.model, "capital_cost"
            )
    except:
        capital_cost = np.nan

    return capital_cost

#-----------------
def financial_analysis(
    sim: Simulation,
    ts: pd.DataFrame,
    out_all: pd.DataFrame,
    out_overall_th: dict = None,
    out_overall_econ: dict = None,
) -> dict:

    from tm_solarshift.models.postprocessing import (
        thermal_postproc,
        economics_postproc,
    )

    #include all capital costs: equipment, installation, certification, etc.
    if out_overall_th == None:
        out_overall_th = thermal_postproc(sim, ts, out_all)
    if out_overall_econ == None:
        out_overall_econ = economics_postproc(sim, ts, out_all)

    energy_annual = out_overall_th["heater_power_acum"]
    energy_cost = out_overall_econ["annual_hw_household_cost"]

    capital_cost = calculate_capital_cost(sim.DEWH)
    oandm_cost = calculate_oandm_cost(sim, ts, out_all)
    
    NPF = 8.
    variable_cost = (energy_cost + oandm_cost)
    net_present_cost = (capital_cost + variable_cost*NPF)
    LCOHW = net_present_cost / (energy_annual*NPF)

    payback_period = np.nan
    fraction_capital = capital_cost / net_present_cost
    fraction_energy = energy_cost / net_present_cost
    fraction_oandm = oandm_cost / net_present_cost
    fraction_others = np.nan

    #Generating the output
    output_finance = {key:np.nan for key in FIN_POSTPROC_OUTPUT}
    output_finance["net_present_cost"] = net_present_cost
    output_finance["payback_period"] = payback_period
    output_finance["LCOHW"] = LCOHW
    output_finance["fraction_capital"] = fraction_capital
    output_finance["fraction_energy"] = fraction_energy
    output_finance["fraction_oandm"] = fraction_oandm
    output_finance["fraction_others"] = fraction_others
    return output_finance

#-----------------
def main():

    sim = Simulation()
    ts = sim.create_ts()

    (out_all, out_overall) = sim.run_thermal_simulation(verbose=True)
    output_finance = financial_analysis(sim, ts, out_all)

    print(out_all)
    print(out_overall)
    print(output_finance)


    return None

if __name__ == "__main__":
    main()