# General imports
import json
import os
import numpy as np
import pandas as pd


from tm_solarshift.general import Simulation
from tm_solarshift.constants import (
    DIRECTORY,
    DEFAULT,
    DEFINITIONS,
    SIMULATIONS_IO
)
from tm_solarshift.utils.units import conversion_factor as CF
from tm_solarshift.models.dewh import (ResistiveSingle, HeatPump)
from tm_solarshift.models.gas_heater import (GasHeaterInstantaneous, GasHeaterStorage)
from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary


#-----------------------------
TYPE_HEATERS = {
    "resistive": ResistiveSingle,
    "heat_pump": HeatPump,
    "gas_instant": GasHeaterInstantaneous,
    "gas_storage": GasHeaterStorage,
    "solar_thermal": SolarThermalElecAuxiliary
}

DIR_TARIFFS = DIRECTORY.DIR_DATA["tariffs"]
DIR_TARIFF_GAS = DIRECTORY.DIR_DATA["gas"]
LOCATIONS_STATE = DEFINITIONS.LOCATIONS_STATE
FILES_MODEL_SPECS = DIRECTORY.FILES_MODEL_SPECS
FIN_POSTPROC_OUTPUT = SIMULATIONS_IO.OUTPUT_ANALYSIS_FIN
OUTPUT_SIM_DEWH = SIMULATIONS_IO.OUTPUT_SIM_DEWH

#--------------------
# List of accepted values
LIST_PARAMS_INPUT = [ "location", "profile_HWD", "household_size",
                     "heater_type", "has_solar", "control_type",
                     "tariff_type", "name", "new_system", "old_heater"]
LIST_LOCATIONS = ["Sydney", "Melbourne", "Adelaide",
                  "Brisbane", "Hobart", "Perth", "Darwin"]
LIST_HEATERS_TYPES = ["resistive", "heat_pump", "gas_instant",
                      "gas_storage", "solar_thermal"]
LIST_CONTROL_TYPES = ["GS", "CL1", "CL2", "CL3",
                      "timer_SS", "timer_OP", "diverter"]
LIST_TARIFF_TYPES = ["CL", "flat", "tou", "gas"]
LIST_HOUSEHOLD_SIZES = [1, 2, 3, 4, 5]
LIST_HWDP = [1, 2, 3, 4, 5, 6]
LIST_DNSP = ["Ausgrid"]
RESISTIVE_SUPPLY_STATES = ["NSW", "QLD", "VIC"]


def calculate_capital_cost(sim: Simulation) -> float:

    heater_type = sim.DEWH.label
    location = sim.household.location
    old_heater = sim.household.old_heater
    type_control = sim.household.control_type
    
    match heater_type:
        case "resistive":
            state = LOCATIONS_STATE[location]
            if state not in RESISTIVE_SUPPLY_STATES:
                state = "supply"
                # if state is in list, capital cost + installation cost
                # if state non is list, just capital cost on technology 
            capital_cost = getattr(sim.DEWH,f'price_{state}').get_value("AUD")
        case "heat_pump":
            capital_cost = getattr(sim.DEWH,'supply_install').get_value("AUD")
            # if in NSW (sydney metropolitan area) call NSW rebate function for dicounted capitl + installation costs
            if old_heater in ['gas_instant', 'gas_storage']:
                new_electric_setup = DEFAULT.NEW_ELEC_SETUP
                capital_cost = capital_cost + new_electric_setup
        case "gas_instant" | "gas_storage" | "solar_thermal":
            capital_cost = getattr(sim.DEWH,'supply_install').get_value("AUD")
        case _:
            raise ValueError("Type of water heater is invalid")
    
    if type_control == 'diverter':
        diverter_cost = DEFAULT.DIVERTER_COST
        capital_cost = capital_cost + diverter_cost

    if type_control == 'timer':
        timer_cost = DEFAULT.TIMER_COST
        capital_cost = capital_cost + timer_cost
    
    return capital_cost


def calculate_disconnection_cost(
        old_heater: str,
        permanent_close: bool = False
) -> float:

    disconnection = 0.
    return disconnection


def calculate_oandm_cost(sim: Simulation,) -> float:
    oandm_cost = 200.
    return oandm_cost


def calculate_npv(cashflows: np.ndarray, discount_rate: float) -> float:
    npv = 0
    for i, cashflow in enumerate(cashflows):
        npv += cashflow / ((1 + discount_rate) ** i)
    return npv


def calculate_household_energy_cost(
        sim: Simulation,
        imported_energy: pd.Series,         # in [kW]
    ) -> float:

    from tm_solarshift.timeseries import market
    tariff_type = sim.household.tariff_type
    ts_index = sim.time_params.idx
    STEP_h = sim.time_params.STEP.get_value("hr")
    location = sim.household.location

    if tariff_type == "gas":
        file_path = DIRECTORY.FILES_GAS_TARIFF[location]
        ts_mkt =  market.load_household_gas_rate(ts_power=imported_energy, file_path=file_path)
    else:
        ts_mkt = market.load_household_import_rate(
            ts_index,
            tariff_type = tariff_type,
            dnsp = sim.household.DNSP,
            control_type = sim.household.control_type,
        )
    return ((ts_mkt["tariff"] * imported_energy).sum() * STEP_h)


def calculate_wholesale_energy_cost(
        sim: Simulation,
        imported_energy: pd.Series,
    ) -> float:
    from tm_solarshift.timeseries import market
    STEP_h = sim.time_params.STEP.get_value("hr")
    if "df_tm" not in sim.out:
        raise AttributeError("No thermal simulation results found.")
    tariff_type = sim.household.tariff_type
    if tariff_type == "gas":
        ts_mkt = pd.Series(0, index = sim.time_params.idx)
    else:
        ts_index = sim.time_params.idx
        location = sim.household.location
        ts_mkt = market.load_wholesale_prices(ts_index, location=location)
    return ((ts_mkt * imported_energy * CF("kW", "MW")).sum() * STEP_h)


def calculate_daily_supply_cost(sim: Simulation) -> float:
    DAYS = sim.time_params.DAYS.get_value("d")
    dnsp = sim.household.DNSP
    tariff_type = sim.household.tariff_type
    control_type = sim.household.control_type
    suply_charge = {
        "CL": True,
        "flat": False,
        "tou": False,
        "gas": True
    }
    if suply_charge[tariff_type]:
        if tariff_type == "CL":
            tariff_type = control_type if (control_type != "diverter") else "CL1"
        file_path = os.path.join(DIR_TARIFFS, f"{dnsp.lower()}_{tariff_type}_plan.json")
        if tariff_type == "gas":
            file_path = DIRECTORY.FILE_GAS_TARIFF_SAMPLE
        with open(file_path) as f:
            plan = json.load(f)
        daily_supply_charge = plan["charges"]["service_charges"][0]["rate"]
    else:
        daily_supply_charge = 0.
    return (daily_supply_charge * DAYS)


def analysis(
    sim: Simulation,
    N_years: int = DEFAULT.LIFESPAN,
    discount_rate: float = DEFAULT.DISCOUNT_RATE,
    permanent_close: bool = False,
    major_maintance_years: list[int] = [4,8],
    verbose: bool = True,
    save_details: bool = False,
    use_cache: bool = True,
    dir_cache: str = "cache/index.csv"
) -> tuple[dict,np.ndarray]:

    #retrieving data
    # old_heater = row["old_heater"]
    old_heater = None

    sim.run_simulation(verbose=verbose)
    energy_HWD_annual = sim.out["overall_tm"]["E_HWD_acum"]
    annual_energy_cost = sim.out["overall_econ"]["annual_hw_household_cost"]
    annual_fit_opp_cost = sim.out["overall_econ"]["annual_fit_opp_cost"]

    #Calculating fixed and variable costs
    capital_cost = calculate_capital_cost(sim)
    daily_supply_cost = calculate_daily_supply_cost(sim)
    oandm_cost = calculate_oandm_cost(sim)
    rebates = calculate_rebates(sim, capital_cost)
    disconnection_costs = calculate_disconnection_cost(
        old_heater = old_heater,
        permanent_close = permanent_close
    )

    # Generating cashflows
    year_zero_cost = (capital_cost + disconnection_costs - rebates)
    cashflows = np.zeros(N_years+1)
    cashflows[0] = year_zero_cost
    cashflows[1:-1] = annual_energy_cost + daily_supply_cost + oandm_cost    
    cashflows = np.array(cashflows)

    #Calculating financial parameters
    net_present_cost = calculate_npv(cashflows, discount_rate)
    LCOHW = net_present_cost / (energy_HWD_annual*N_years)      #[AUD/kWh]
    payback_period = np.nan

    #Generating the output
    output_finance = {key:np.nan for key in FIN_POSTPROC_OUTPUT}
    output_finance["net_present_cost"] = net_present_cost
    output_finance["payback_period"] = payback_period
    output_finance["LCOHW"] = LCOHW
    output_finance["capital_cost"] = capital_cost
    output_finance["annual_energy_cost"] = annual_energy_cost
    output_finance["daily_supply_cost"] = daily_supply_cost
    output_finance["annual_fit_opp_cost"] = annual_fit_opp_cost
    output_finance["oandm_cost"] = oandm_cost
    output_finance["rebates"] = rebates
    output_finance["disconnection_costs"] = disconnection_costs

    return (output_finance, cashflows)


#----------------
def calculate_rebates(
    sim: Simulation,
    capital_cost: float,
) -> float: 

    heater_type = sim.DEWH.label
    old_heater = sim.household.old_heater
    new_system = sim.household.new_system
    location = sim.household.location

    if location not in LIST_LOCATIONS:
        raise ValueError(f"Location {location=} is invalid")
        
    state = LOCATIONS_STATE[location]
    match state:
        case "NSW":
            rebate = NSW_rebate(old_heater, new_system)
        case "VIC":
            rebate = VIC_rebate(
                old_heater=old_heater,
                new_heater=heater_type,
                new_system=new_system,
                capital_cost=capital_cost,
            )
        case "SA":
            rebate = SA_rebate()
        case "ACT":
            rebate = ACT_rebate(
                old_heater=old_heater,
                new_heater=heater_type,
                capital_cost=capital_cost
            )
        case "QLD":
            rebate = QLD_rebate()
        case "TAS":
            rebate = TAS_rebate()
        case "WA":
            rebate = WA_rebate()
        case "NT":
            rebate = NT_rebate()
        case _:
            raise ValueError("Location is invalid") 
    return rebate 

#--------------------
def NSW_rebate(
        old_heater: str,
        new_heater: str
):
    # Energy Savingsd Scheme 
    # Not a rebate (its an incentive), provides discounts for installing or ugrading equipment 
    # STC rebate (small-scale renewable energy scheme) included in supply and install cost 
    if (new_heater == "heat_pump"):
        # only rebate avaialble for heat pump 
        # exclude rebates from calculations if not ubgrading water heater
        if old_heater == 'resistive':
            # ESS rebate of 800 for repalcing electric water heater with reclaimed energy heat pump 
            rebate = 800
        else: 
            rebate = 0
    elif (new_heater == "solar_thermal"):
        #some rebates available
        rebate = 0 #set to zero now 
    else:
        rebate = 0
        
    return rebate 
    
    """ if (new_heater != "heat_pump") and (old_heater == 'none'):
        # only rebate avaialble for heat pump 
        # exclude rebates from calculations if not ubgrading water heater
        return 0

    if old_heater == "resisteive":
        # for metropolitan sydney - switching from electric to heat pump eligible for 70% savings for system and installation 
        if household_size >= 4: 
            heater_and_install = 1850 #average of heat pump installations with 270L+ (270 and 280) 
        else: 
            heater_and_install = 900 #average of heat pump installations with 200L-250L (split systems $800 all in one $1100)
        return heater_and_install 
    elif old_heater == "gas_instant" or old_heater == "gas_storage":
        # for metropolitan sydney - switching from gas to heat pump eligible for 50% savings for system and installation 
        heater_and_install = 2100 #SPT black knight 250L all in one completely installed 
        return heater_and_install 
    else:
        return 0 """

def VIC_rebate(
        old_heater: str,
        new_heater: str,
        new_system: str,
        capital_cost: float) -> float:
    
    if (new_heater != "heat_pump") and (new_heater != "solar_thermal") and not (new_system):
        # only rebate avaialble for heat pump and electric boosted solar water heater 
        # exclude rebates from calculations if not upgrading water heater
        return 0
    
    # https://www.energy.vic.gov.au/households/victorian-energy-upgrades-for-households/hot-water-systems
    # Incentives of up to following amounts are available for the average household 
    # Must be replacing an inefficient electric or gas hot water system 
    if old_heater == "resisteive": 
        if new_heater == "heat_pump": 
            heater_and_install = 840 
        elif new_heater == "solar_thermal": 
            heater_and_install = 1190 
        return heater_and_install 
    elif old_heater == "gas_instant" or old_heater == "gas_storage":
        if new_heater == "heat_pump": 
            heater_and_install = 490 
        elif new_heater == "solar_thermal": 
            heater_and_install = 700 
        return heater_and_install 
    else:
        return 0

    """# https://www.solar.vic.gov.au/hot-water-rebate
    # Solar Victoria provides a 50% rebate of up to $1,000 on eligible heat pump hot water systems.
    if new_heater == "heat_pump":
        discount = capital_cost/2
        if discount <= 1000:
            return discount 
        else:
            return 1000"""
        
            
def SA_rebate():
    #Retailer Energy Productivity Scheme (REPS)
    # https://www.escosa.sa.gov.au/industry/reps/obliged-retailers-activity-providers
    #Eligible for residential households to connect a new or existing electrci heat pump water heater to an approved DR Aggregator 

    #Replae or Upgrade Water Heater to - gas,  solar electric, solar gas, heat pump 
    pass
    return 0

def ACT_rebate(old_heater, new_heater, capital_cost):
    
    #water_heater_price = find_water_heater_price(water_heater_type)
    #installation = calculate_installation_cost(water_heater_type)

    #initial_costs = water_heater_price + installation

    # Home Energy Support Program 
    if new_heater == 'heat_pump':
        if (capital_cost/2) <= 2500: #AUD
            # one rebate of 50% of the total installastion price for hot water heat pumps 
            ACT_rebate = (capital_cost/2)
        elif (capital_cost/2) > 2500:
            ACT_rebate = 2500 #AUD
    else:
        ACT_rebate = 0

    ''' 
    max_rebate = 2500
    ACT_rebate = min(initial_costs/2. , max_rebate)
    ______
    max_rebate = 2500
    pct_off = 0.5
    ACT_rebate = min(0.5 * initial_costs , max_rebate)
    '''
    #Energy-efficient electric water heater upgrade
    if old_heater in ['resistive', 'gas_instant', 'gas_storage']:
        if new_heater == 'heat_pump' and ACT_rebate < 500:
            #capital_cost = capital_cost - 500
            # 500 off initial costs 
            ACT_rebate = 500

    #Taking the rebte that returns the most 
    return ACT_rebate

def QLD_rebate():
    pass
    return 0

def TAS_rebate(
) -> float:
    #Energy saver loan scheme 
    # provides a 0% interest loan - how to integrate into calculations 

        #rebate possible up to $10,000 - will depend on household needs and desired water heater 
    TAS_rebate = 0

    return TAS_rebate

def WA_rebate():
    # no WA specifc rebates and incentives, only SRES
    WA_rebate = 0
    return WA_rebate

def NT_rebate():
    pass
    return 0

# def cache_financial_tm(
#         row: pd.Series|dict,
#         dir_cache: str,
#         verbose: bool = False,
# ) -> tuple[Simulation,pd.DataFrame,dict[str,float]]:

#     COLS_FIN_CACHE_TM = [
#         "location", "profile_HWD", "household_size", "heater_type", "has_solar", "control_type",
#     ]
#     row_to_check = row[COLS_FIN_CACHE_TM]

#     file_cache = os.path.join(dir_cache,"index.csv")
    
#     cache_index = pd.read_csv(file_cache, index_col=0)
#     idx_cached = cache_index[(cache_index == row_to_check).all(axis=1)].index

#     if len(idx_cached) == 0:
#         # call simulation and save into cache
#         sim = get_simulation_instance(row, verbose=verbose)
#         ts = sim.create_ts()
#         (out_all, out_overall) = sim.run_thermal_simulation(ts, verbose=verbose)
#         df_tm = out_all[OUTPUT_SIM_DEWH]
#         # getting a new id and saving into .plk file
#         new_id = 1 if (len(cache_index) == 0) else (cache_index.index.max() + 1)
#         file_path = os.path.join(dir_cache,f"sim_{new_id}.plk")
#         try:
#             #saving results
#             with open(file_path, "wb") as file:
#                 sim_output = [sim,df_tm,out_overall]
#                 pickle.dump(sim_output, file, protocol=pickle.HIGHEST_PROTOCOL)
#             #updating index
#             cache_index.loc[new_id,:] = row_to_check
#             cache_index.to_csv(file_cache)
#         except Exception as ex:
#             print("Error during pickling object (Possibly unsupported):", ex)

#     else:
#         # retrieve the saved data
#         file_path = os.path.join( dir_cache, f"sim_{idx_cached.values[0]}.plk" )
#         try:
#             with open(file_path, "rb") as f:
#                 (sim, df_tm, out_overall) = pickle.load(f)
#             df_tm = df_tm[OUTPUT_SIM_DEWH]
#         except Exception as ex:
#             print("Error during unpickling object (Possibly unsupported):", ex)

#     return (sim, df_tm, out_overall)