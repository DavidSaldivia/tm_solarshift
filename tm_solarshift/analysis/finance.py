# General imports
import os
import numpy as np
import pandas as pd
from typing import Union, Any

# Internal Solarshift imports
from tm_solarshift.general import GeneralSetup
from tm_solarshift.constants import (
    DIRECTORY,
    DEFINITIONS,
    SIMULATIONS_IO
)
from tm_solarshift.utils.units import (
    conversion_factor as CF,
    Variable
)
from tm_solarshift.devices import (
    ResistiveSingle,
    HeatPump,
    GasHeaterInstantaneous,
    GasHeaterStorage,
    SolarThermalElecAuxiliary,
)

#-----------------------------
# Constants for this module
Heater = Union[
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
FILE_MODEL_HOUSEHOLDSIZES = os.path.join(
    DIRECTORY.DIR_DATA["specs"],
    "models_householdsize.csv"
)
LOCATIONS_STATE = DEFINITIONS.LOCATIONS_STATE
FILES_MODEL_SPECS = DIRECTORY.FILES_MODEL_SPECS
FIN_POSTPROC_OUTPUT = SIMULATIONS_IO.FIN_POSTPROC_OUTPUT

#--------------------
#Default values
DEFAULT_CAPITAL_COST = 1000.    #[AUD]
DEFAULT_DIVERTER_COST = 1100.   #[AUD]
DEFAULT_TIMER_COST = 250.       #[AUD]
DEFAULT_PERM_CLOSE_COST = 1250  #[AUD]
DEFAULT_TEMP_CLOSE_COST = 200   #[AUD]
DEFAULT_NEW_ELEC_SETUP = 500.   #[AUD]

DEFAULT_REBATES = 0             # [AUD]
DEFAULT_DISCOUNT_RATE = 0.08    # 8%
DEFAULT_LIFESPAN = 10           # [years]
DEFAULT_MAJOR_MAINTANCE = 200.  # AUD
DEFAULT_HOUSEHOLD_SIZE = 4      # [people]
DEFAULT_DAILY_HWD = 200.        # [L/day]

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
LIST_TARIFF_TYPES = ["CL", "flat", "tou"]
LIST_HOUSEHOLD_SIZES = [1, 2, 3, 4, 5]
LIST_HWDP = [1, 2, 3, 4, 5, 6]
LIST_DNSP = ["Ausgrid"]
RESISTIVE_SUPPLY_STATES = ["NSW", "QLD", "VIC"]

#--------------------
# Helper functions
#--------------------
def get_model_number(
        household_size: int,
        heater_type: str,
) -> float:
    df = pd.read_csv(FILE_MODEL_HOUSEHOLDSIZES)
    model = df[
        (df["heater_type"] == heater_type) &
        (df["household_size"] == household_size)
    ]["model"].iloc[0]
    return model

#--------------------
def get_heater_object(
    heater_type: str,
    model: str
) -> Heater:

    match heater_type:
        case "resistive":
            DEWH = ResistiveSingle.from_model_file(model=model)
        case "heat_pump":
            DEWH = HeatPump.from_model_file(model=model)
        case "gas_instant":
            DEWH = GasHeaterInstantaneous.from_model_file(model=model)
        case "gas_storage":
            DEWH = GasHeaterStorage.from_model_file(model=model)
        case "solar_thermal":
            DEWH = SolarThermalElecAuxiliary.from_model_file(model=model)
        case _:
            raise ValueError("heater_type not among accepted DEWH.")
        
    return DEWH
#-------------------
def get_control_load(
        control_type: str,
        tariff_type: str
)-> int:
    
    match control_type:
        case "GS":
            control_load = 0
        case "CL1":
            control_load = 1
        case "CL2":
            control_load = 2
        case "CL3":
            control_load = 3
        case "timer_SS" | "SS":
            control_load = 4
        case "timer_OP":
            control_load = 6
        case "diverter":
            if tariff_type == "CL":
                control_load = 1
            elif tariff_type == "flat":
                control_load = 10
            elif tariff_type == "tou":
                control_load = 6
            else:
                control_load = -1
        case _:
            raise ValueError("wrong control_type.")
    return control_load

def get_daily_hwd(
        household_size: int = DEFAULT_HOUSEHOLD_SIZE
) -> float:
    return DEFAULT_DAILY_HWD * household_size / DEFAULT_HOUSEHOLD_SIZE

#-------------------
def calculate_capital_cost(GS: GeneralSetup) -> float:

    # if not looking to buy new system, there will be no capital costs
    # if not row["new_system"]:
    #     return 0 

    heater_type = GS.household.heater_type
    location = GS.household.location
    old_heater = GS.household.old_heater
    type_control = GS.household.control_type
    household_size = GS.household.size

    model_number = get_model_number(household_size, heater_type)
    df_heaters = pd.read_csv( FILES_MODEL_SPECS[heater_type], index_col=0 )

    match heater_type:

        case "resistive":
            state = LOCATIONS_STATE[location]
            if state not in RESISTIVE_SUPPLY_STATES:
                state = "supply"
                # if state is in list, capital cost + installation cost
                # if state non is list, just capital cost on technology 
            capital_cost = df_heaters.loc[model_number, f'price_{state}']
        
        case "heat_pump":
            capital_cost = df_heaters.loc[model_number, 'supply_install']
            # if in NSW (sydney metropolitan area) call NSW rebate function for dicounted capitl + installation costs
            if old_heater in ['gas_instant', 'gas_storage']:
                new_electric_setup = DEFAULT_NEW_ELEC_SETUP
                capital_cost = capital_cost + new_electric_setup

        case "gas_instant" | "gas_storage" | "solar_thermal":
            capital_cost = df_heaters.loc[model_number, 'supply_install']

        case _:
            raise ValueError("Type of water heater is invalid")

    capital_cost = float(capital_cost)
    
    if type_control == 'diverter':
        #if getting new diverter (range between $800-$1500) with installation
        diverter_cost = DEFAULT_DIVERTER_COST
        capital_cost = capital_cost + diverter_cost

    if type_control == 'timer':
        #if getting new diverter (range between $800-$1500) with installation
        timer_cost = DEFAULT_TIMER_COST
        capital_cost = capital_cost + timer_cost
    
    return capital_cost


#----------------
def calculate_rebates(
    GS: GeneralSetup,
    capital_cost: float,
) -> float: 

    old_heater = GS.household.old_heater
    heater_type = GS.household.heater_type
    new_system = GS.household.new_system
    location = GS.household.location

    if location not in LIST_LOCATIONS:
        raise ValueError("Location is invalid")
        
    state = LOCATIONS_STATE[location]
    match state:
        case "NSW":
            rebate = NSW_rebate(old_heater, new_system)
        case "VIC":
            rebate = VIC_rebate(
                old_heater,
                new_heater=heater_type,
                new_system=new_system
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
def calculate_disconnection_cost(
        old_heater: str,
        permanent_close: bool = False
) -> float:

    disconnection = 0.
    # no old heater to disconnect
    # if (old_heater == "none"): 
    #     disconnection = 0 

    if old_heater not in LIST_HEATERS_TYPES:
        raise ValueError("Water heater is invalid")

    if (old_heater in ['gas_instant', 'gas_storage']):
        if permanent_close:
            # in this gas the daily gas supply charge will not be considerred either 
            disconnection = DEFAULT_PERM_CLOSE_COST
        else:
            # in this case the gas daily supply charge is still charged to the housheold 
            disconnection = DEFAULT_TEMP_CLOSE_COST

    elif old_heater == 'resistive':
        #read disconecction costs from file?
        disconnection = 250

    return disconnection

#-----------------
def calculate_oandm_cost(
        GS: GeneralSetup,
        out_all: pd.DataFrame = None,
        has_solar: bool = False,
    ) -> float:
    
    # annual oandm cost
    # include operation, maintance, re-purchase, etc.
    oandm_cost = 0.
    return oandm_cost

#-----------------------
def calculate_npv(
        cashflows: list,
        discount_rate: float
    ) -> float:

    npv = 0
    for i, cashflow in enumerate(cashflows):
        npv += cashflow / ((1 + discount_rate) ** i)
    return npv

#------------------------
def calculate_household_energy_cost(
        GS: GeneralSetup,
        ts: pd.DataFrame = None,
        df_tm: pd.DataFrame = None,
        ) -> float:

    control_type = GS.household.control_type
    STEP_h = GS.simulation.STEP.get_value("hr")
    if ts is None:
        ts = GS.create_ts()

    if df_tm is None:
        (df_tm, _) = GS.run_thermal_simulation(ts, verbose = True)

    heater_power = df_tm["HeaterPower"] * CF("kJ/h", "kW")

    if GS.solar_system == None:
        imported_energy = heater_power.copy()
    else:
        tz = 'Australia/Brisbane'
        pv_power = GS.solar_system.load_PV_generation(
            df = df_tm, tz=tz,  unit="kW"
        )
        if control_type == "diverter":
            #Diverter considers three hours at night plus everything diverted from solar
            control_load = GS.household.control_load
            import tm_solarshift.timeseries.control as control
            CS_timer = control.load_schedule(
                ts, control_load = control_load, random_ON=False
            )["CS"]
            imported_energy = (CS_timer * heater_power)
        else:
            imported_energy = np.where(
                pv_power < heater_power, heater_power - pv_power, 0
            )

    energy_cost = ( ts["tariff"] * imported_energy * STEP_h  ).sum()
    return energy_cost

#-----------------------
def calculate_wholesale_energy_cost(
        GS: GeneralSetup,
        ts: pd.DataFrame = None,
        df_tm: pd.DataFrame = None,
        ) -> float:
    
    STEP_h = GS.simulation.STEP.get_value("hr")

    if ts is None:
        ts = GS.create_ts()
    if df_tm is None:
        df_tm = GS.run_thermal_simulation(ts)
        
    heater_power = df_tm["HeaterPower"] * CF("kJ/h", "MW")
    energy_cost = ( ts["Wholesale_Market"] * heater_power * STEP_h).sum()
    return energy_cost

#------------------------
def calculate_annual_bill(
        GS: GeneralSetup,
        ts: pd.DataFrame = None,
        out_all: pd.DataFrame = None,
        has_solar: bool = False,
    ) -> float:
    
    # calculate annual energy cost
    if ts is None:
        ts = GS.create_ts()
    energy_cost = calculate_household_energy_cost(GS, ts, out_all)
    DAYS = GS.simulation.DAYS.get_value("d")
    DAILY_CHARGE = 1.0  #AUD (just an average value for now, read tariff instead)
    fix_cost = DAYS*DAILY_CHARGE

    # add other costs (daily/seasonal costs)
    annual_bill = energy_cost + fix_cost
    
    return annual_bill

#------------------------
def get_GS_instance(
        row: pd.Series,
        verbose: bool = True,
        ) -> GeneralSetup:

    if verbose:
        print("Creating a GeneralSetup instance using csv file's row")    

    #Retriever required data
    location = row["location"]
    profile_HWD = row["profile_HWD"]
    household_size = row["household_size"]
    heater_type = row["heater_type"]
    has_solar = row["has_solar"]
    control_type = row["control_type"]
    tariff_type = row["tariff_type"]
    new_system = row["new_system"]
    old_heater = row["old_heater"]

    #Obtaining all the derived parameters
    model = get_model_number(household_size, heater_type)
    DEWH = get_heater_object(heater_type, model)
    control_load = get_control_load(control_type, tariff_type)
    daily_avg = get_daily_hwd(household_size)

    #Creating a GS's instance
    GS = GeneralSetup()
    GS.household.location = location
    GS.household.tariff_type = tariff_type
    GS.household.control_type = control_type
    GS.household.control_load = control_load
    GS.DEWH = DEWH
    GS.HWDInfo.profile_HWD = profile_HWD
    GS.HWDInfo.daily_avg = Variable( daily_avg, "L/d")
    GS.HWDInfo.daily_max = Variable( 2*daily_avg, "L/d")
    GS.HWDInfo.daily_std = Variable( daily_avg/3., "L/d")

    if not has_solar:
        GS.solar_system = None

    return GS

def save_and_cache(GS, output_finance, cashflows ):

        
        

    return

#------------------
def financial_analysis(
    row: pd.Series,
    N_years: int = DEFAULT_LIFESPAN,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    permanent_close: bool = False,
    major_maintance_years: list[int] = [4, 8],
    verbose: bool = True,
    save_details: bool = False,
    create_cache: bool = True,
) -> tuple[dict,np.array]:


    #retrieving data
    heater_type = row["heater_type"]

    # creating and instance of GS
    GS = get_GS_instance(row, verbose=verbose)

    #running thermal simulation
    ts = GS.create_ts()
    (out_all, out_overall) = GS.run_thermal_simulation(ts, verbose=verbose)
    energy_HWD_annual = out_overall["E_HWD_acum"]

    #Calculating fixed and variable costs
    capital_cost = calculate_capital_cost(GS)
    annual_bill = calculate_annual_bill(GS = GS, ts = ts, out_all = out_all)
    oandm_cost = calculate_oandm_cost(GS, out_all)
    rebates = calculate_rebates(GS, capital_cost)
    disconnection_costs = calculate_disconnection_cost(
        old_heater = heater_type,
        permanent_close = permanent_close
    )

    # Generating cashflows
    year_zero_cost = (capital_cost + disconnection_costs - rebates)
    cashflows = np.zeros(N_years+1)
    cashflows[0] = year_zero_cost
    cashflows[1:-1] = annual_bill + oandm_cost
    
    if heater_type == 'resistive':
        major_maintenance = DEFAULT_MAJOR_MAINTANCE
        for i in major_maintance_years:
            cashflows[i] = cashflows[i] + major_maintenance

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
    output_finance["annual_bill"] = annual_bill
    output_finance["oandm_cost"] = oandm_cost
    output_finance["rebates"] = rebates
    output_finance["disconnection_costs"] = disconnection_costs

    return (output_finance, cashflows)

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
    return None

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
    return None

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
    return

#-----------------
def main():

    GS = GeneralSetup()
    ts = GS.create_ts()

    # (out_all, out_overall) = GS.run_thermal_simulation(verbose=True)
    # output_finance = financial_analysis(GS, ts, out_all)

    # print(out_all)
    # print(out_overall)
    # print(output_finance)


    return None

if __name__ == "__main__":
    main()