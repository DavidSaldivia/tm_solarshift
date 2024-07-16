import json
import os
import numpy as np
import pandas as pd

from tm_solarshift.constants import (DIRECTORY, DEFINITIONS, SIMULATIONS_IO)
from tm_solarshift.general import Simulation
from tm_solarshift.utils.units import conversion_factor as CF
from tm_solarshift.utils.location import Location
from tm_solarshift.models.gas_heater import GasHeaterInstantaneous


DIR_SPOTPRICE = DIRECTORY.DIR_DATA["energy_market"]
DIR_EMISSIONS = DIRECTORY.DIR_DATA["emissions"]
DIR_TARIFFS = DIRECTORY.DIR_DATA["tariffs"]

FILES = {
    "WHOLESALE_PRICES": os.path.join(DIR_SPOTPRICE, 'SP_2017-2023.csv'),
    "EMISSIONS_TEMPLATE": os.path.join( DIR_EMISSIONS, "emissions_year_{:}_{:}.csv"),
}
GAS_TARIFF_SAMPLE_FILE = os.path.join(DIRECTORY.DIR_DATA["gas"],"energyaustralia_basic.json")

#-----------
def load_household_import_rate(
        ts_index: pd.DatetimeIndex,
        tariff_type: str = "flat",
        control_type: str = "CL1",
        dnsp: str = "ausgrid",
) -> pd.DataFrame:

    ts2 = pd.DataFrame(index=ts_index, columns = [ "tariff", "rate_type"])
    match tariff_type:
        case "flat":
            file_path = os.path.join(DIR_TARIFFS, f"{dnsp.lower()}_{tariff_type}_plan.json")
            with open(file_path) as f:
                plan = json.load(f)
            tariff_rate = None
            for charge in plan["charges"]["energy_charges"]:
                if charge["tariff_type"] == "flat":
                    tariff_rate = charge["rate_details"][0]["rate"]
            ts2["tariff"] = tariff_rate
            ts2["rate_type"] = "flat"
        
        case "CL":
            file_path = os.path.join(DIR_TARIFFS, f"{dnsp.lower()}_{control_type}_plan.json")
            with open(file_path) as f:
                plan = json.load(f)
            tariff_rate = None
            for charge in plan["charges"]["energy_charges"]:
                if charge["tariff_type"] == "controlled_load":
                    tariff_rate = charge["rate_details"][0]["rate"]
            ts2["tariff"] = tariff_rate
            ts2["rate_type"] = "flat"
        
        case "tou":
            from tm_solarshift.external.energy_plan_utils import (
                get_energy_breakdown,
                get_energy_plan_for_dnsp,
            )
            file_tou = os.path.join(DIR_TARIFFS, f"{dnsp.lower()}_tou_cache.csv")
            if os.path.isfile(file_tou):
                energy_plan = get_energy_plan_for_dnsp(
                    dnsp, tariff_type = tariff_type, convert=True
                )
                ts3 = pd.read_csv(file_tou, index_col=0)
                ts3.index = pd.to_datetime(ts3.index)
            else:
                ts_aux = pd.DataFrame(index=ts_index, columns = [
                    "t_stamp", "pv_energy", "load_energy", "tariff", "rate_type",
                    ]
                )
                ts_aux["t_stamp"] = ts_aux.index
                ts_aux["pv_energy"] = 0.       #Not used, defined to avoid error inside Rui's code
                ts_aux["load_energy"] = 0.     #Not used, defined to avoid error inside Rui's code
                energy_plan = get_energy_plan_for_dnsp(
                    dnsp, tariff_type=tariff_type, convert=True
                )
                (_, ts3) = get_energy_breakdown(
                    tariff_type = tariff_type,
                    tariff_structure = energy_plan,
                    raw_data = ts_aux,
                    resolution = 180,
                    return_raw_data = True
                )
                ts3.to_csv(file_tou)
            ts2["tariff"] = ts3["import_rate"]
            ts2["rate_type"] = ts3["rate_type"]
    
    return ts2

#-------------
def load_household_gas_rate(
        ts: pd.DataFrame,
        heater: GasHeaterInstantaneous,
        tariff_type: str = "gas",
        file_path: str = GAS_TARIFF_SAMPLE_FILE,
) -> pd.DataFrame:

    #importing the energy plan
    with open(file_path) as f:
        plan = json.load(f)
    rate_details = plan["charges"]["energy_charges"]["rate_details"]
    rates = []
    edges = [0,]
    for bin in rate_details:
        rates.append(bin["rate"])
        edges.append(bin["ceil"])

    #importing data from heater
    nom_power = heater.nom_power.get_value("MJ/hr")
    flow_water = heater.flow_water.get_value("L/min")
    specific_energy = (nom_power / flow_water * CF("min", "hr"))        #[MJ/L]

    #getting the tariff
    ts2 = ts.copy()
    ts2_index = pd.to_datetime(ts2.index)
    hw_flow = ts2["m_HWD"]
    STEP_h = ts2_index.freq.n * CF("min", "hr")
    ts2["E_HWD"] = specific_energy * hw_flow * STEP_h         #[MJ]
    ts2["E_HWD_cum_day"] = ts2.groupby(ts2_index.date)['E_HWD'].cumsum()
    ts2["tariff"] = pd.cut(
        ts2["E_HWD_cum_day"],
        bins = edges, labels = rates, right = False
    ).astype("float")

    #output
    ts["tariff"] = ts2["tariff"]
    ts["rate_type"] = tariff_type
    return ts

#---------------------------------
# emissions
def load_emission_index_year(
        timeseries: pd.DataFrame,
        location: str|Location = "Sydney",
        index_type: str = "total",
        year: int = 2022,
        ) -> pd.DataFrame:
    
    if (type(location) == Location):
        state = location.state
        loc_st = DEFINITIONS.LOCATIONS_STATE
        location = list(loc_st.keys())[list(loc_st.values()).index(state)]
    
    columns = {
        "total": "intensity_index",
        "marginal": "marginal_index",
        # "both": PROFILES.TYPES["emissions"]   #Not working well yet
        }[index_type]
    
    emissions = pd.read_csv(
        FILES["EMISSIONS_TEMPLATE"].format(year, index_type), index_col=0,
    )
    emissions.index = pd.to_datetime(emissions.index)
    emissions.columns = [x.lower() for x in emissions.columns]

    STEP = pd.to_datetime(timeseries.index).freq.n
    timeseries[columns] = emissions[
        emissions["region"] == DEFINITIONS.LOCATIONS_NEM_REGION[location]
        ][columns].resample(
            f"{STEP}min"
        ).interpolate('linear')
    return timeseries

#---------------------------------
# wholesale prices
def load_wholesale_prices(
        timeseries: pd.DataFrame,
        location: Location = Location(),
        ) -> pd.DataFrame:
    
    df_SP = pd.read_csv( FILES["WHOLESALE_PRICES"], index_col=0 )
    df_SP.index = pd.to_datetime(df_SP.index).tz_localize(None)

    if type(location) == str:   #city
        nem_region = DEFINITIONS.LOCATIONS_NEM_REGION[location]
    elif type(location) == tuple:     #coordinate
        pass #Check which state the location is
    elif type(location) == int:     #postcode
        pass #Check the NEM region of postcode
    elif type(location) == Location:
        nem_region = DEFINITIONS.STATES_NEM_REGION[location.state]

    STEP = pd.to_datetime(timeseries.index).freq.n
    timeseries["wholesale_market"] = df_SP[
        nem_region
        ].resample(
            f"{STEP}min"
        ).interpolate('linear')

    return timeseries

#------------------------
def test_get_gas_rate():

    COLS = DEFINITIONS.TS_TYPES["economic"]
    sim = Simulation()
    sim.DEWH = GasHeaterInstantaneous()
    sim.household.tariff_type = "gas"

    ts = sim.create_ts()

    output = load_household_gas_rate( ts, heater = sim.DEWH )
    energy_bill = (output["E_HWD"] * output["tariff"]).sum()
    print(output)
    print(energy_bill)

    return

#-------------
if __name__ == "__main__":

    # test_get_gas_rate()

    # test_load_household_import_rate()

    # test_calculate_energy_cost()

    pass
#---------------------------
# def main():

#     from tm_solarshift.general import Simulation
#     sim = Simulation()
#     ts = sim.create_ts()
    
#     location = Location("Sydney")
#     ts = load_emission_index_year( ts, location, index_type='total', year=2022 )
#     ts = load_emission_index_year( ts, location, index_type='marginal', year=2022 )

#     ts = load_wholesale_prices(ts, location)
    
#     ts = load_household_import_rate(
#         ts,
#         tariff_type="tou",
#         return_energy_plan=False
#     )

#     print(ts.head(20))
#     pass

# if __name__ == "__main__":
#     main()