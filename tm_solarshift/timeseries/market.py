import os
import numpy as np
import pandas as pd

from tm_solarshift.constants import (DIRECTORY,DEFINITIONS)
from tm_solarshift.general import Simulation
from tm_solarshift.utils.units import conversion_factor as CF
from tm_solarshift.utils.location import Location
from tm_solarshift.models.gas_heater import GasHeaterInstantaneous
from tm_solarshift.external.energy_plan_utils import (
    get_energy_breakdown,
    get_energy_plan_for_dnsp,
)

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
        ts: pd.DataFrame,
        tariff_type: str = "flat",
        dnsp: str = "Ausgrid",
        return_energy_plan: bool = True,
        control_load: int = 1,

) -> pd.DataFrame:
# ) -> tuple[pd.DataFrame,dict] | pd.DataFrame:

    # Preparing ts to the format required by Rui's code
    ts2 = pd.DataFrame(index=ts.index, columns = [
        "t_stamp",
        "pv_energy", "load_energy",
        "tariff", "rate_type",
        ]
    )
    ts2["t_stamp"] = ts2.index
    ts2["pv_energy"] = 0.       #Not used, defined to avoid error inside Rui's code
    ts2["load_energy"] = 0.     #Not used, defined to avoid error inside Rui's code
    
    match tariff_type:
        case "flat":
            energy_plan = get_energy_plan_for_dnsp(dnsp,
                                                tariff_type = tariff_type,
                                                convert = True,)
            ts2["tariff"] = energy_plan["flat_rate"]
            ts2["rate_type"] = "flat"
        case "tou":
            file_tou = os.path.join(DIR_TARIFFS, "tou_cache.csv")
            
            if os.path.isfile(file_tou):
                energy_plan = get_energy_plan_for_dnsp(dnsp,
                                                    tariff_type = tariff_type,
                                                    convert=True
                )
                ts3 = pd.read_csv(file_tou, index_col=0)
                ts3.index = pd.to_datetime(ts3.index)
            else:
                energy_plan = get_energy_plan_for_dnsp(
                    dnsp, tariff_type=tariff_type, convert=True
                )
                    
                (_, ts3) = get_energy_breakdown(
                    tariff_type=tariff_type,
                    tariff_structure=energy_plan,
                    raw_data=ts2,
                    resolution=180,
                    return_raw_data=True)
                ts3.to_csv(file_tou)

            ts2["tariff"] = ts3["import_rate"]
            ts2["rate_type"] = ts3["rate_type"]
        
        case "CL":
            energy_plan = get_energy_plan_for_dnsp(
                dnsp,
                tariff_type="flat",
                convert=True,
                controlled_load_num = control_load,
                switching_cl = True,
            )
            ts2["tariff"] = energy_plan["CL_rate"]
            ts2["rate_type"] = "CL"
        case "gas":
            
            # values for AGL's Residential Value Saver (standard). Average value is given
            ts2["tariff"] = 0.033 * CF("MJ", "kWh")      #3.3 [cent/MJ]
            ts2["rate_type"] = "gas"
        case _:
            raise ValueError("type tariff not among the available options.")

    #Output
    ts["tariff"] = ts2["tariff"]
    ts["rate_type"] = ts2["rate_type"]
    return ts

    # if return_energy_plan:
    #     return (ts, energy_plan)
    # else:
    #     return ts

#-------------
def load_household_gas_rate(
        ts: pd.DataFrame,
        heater: GasHeaterInstantaneous,
        tariff_type: str = "gas",
        file_path: str = GAS_TARIFF_SAMPLE_FILE,
) -> pd.DataFrame:

    import json

    with open(file_path) as f:
        plan = json.load(f)
    
    #use pandas pd.cut
    rate_details = plan["charges"]["energy_charges"]["rate_details"]
    rates = []
    edges = [0,]
    for bin in rate_details:
        rates.append(bin["rate"])
        edges.append(bin["ceil"])

    nom_power = heater.nom_power.get_value("MJ/hr")
    flow_water = heater.flow_water.get_value("L/min")
    specific_energy = (nom_power / flow_water * CF("min", "hr")) #[MJ/L]

    hw_flow = ts["m_HWD"]
    ts_index = pd.to_datetime(ts.index)
    STEP_h = ts_index.freq.n * CF("min", "hr")

    ts2 = ts.copy()
    ts2["E_HWD"] = specific_energy * hw_flow * STEP_h         #[MJ]
    ts2["E_HWD_cum_day"] = ts2.groupby(ts_index.date)['E_HWD'].cumsum()
    ts2["tariff"] = pd.cut(
        ts2["E_HWD_cum_day"],
        bins = edges, labels = rates, right = False
    ).astype("float")
    ts["rate_type"] = tariff_type

    ts["tariff"] = ts2["tariff"]
    ts["rate_type"] = tariff_type
    return ts

#---------------------------------
# emissions
def load_emission_index_year(
        timeseries: pd.DataFrame,
        location: str = "Sydney",
        index_type: str = "total",
        year: int = 2022,
        ) -> pd.DataFrame:
    
    if (type(location) == Location):
        state = location.state
        loc_st = DEFINITIONS.LOCATIONS_STATE
        location = list(loc_st.keys())[list(loc_st.values()).index(state)]
    
    columns = {
        "total": "Intensity_Index",
        "marginal": "Marginal_Index",
        # "both": PROFILES.TYPES["emissions"]   #Not working well yet
        }[index_type]
    
    emissions = pd.read_csv(
        FILES["EMISSIONS_TEMPLATE"].format(year, index_type), index_col=0,
    )
    emissions.index = pd.to_datetime(emissions.index)

    STEP = pd.to_datetime(timeseries.index).freq.n
    timeseries[columns] = emissions[
        emissions["Region"] == DEFINITIONS.LOCATIONS_NEM_REGION[location]
        ][columns].resample(
            f"{STEP}T"
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
    timeseries["Wholesale_Market"] = df_SP[
        nem_region
        ].resample(
            f"{STEP}T"
        ).interpolate('linear')

    return timeseries

#--------------------
def test_load_household_import_rate():
    
    COLS = DEFINITIONS.TS_TYPES["economic"]

    sim = Simulation()
    sim.household.DNSP = "Ausgrid"
    sim.household.tariff_type = "flat"
    ts = sim.create_ts_empty()
    (ts, energy_plan) = load_household_import_rate(ts,
                                        tariff_type = sim.household.tariff_type,
                                        dnsp = sim.household.DNSP,
                                        return_energy_plan = True,
                                        )
    print(ts)
    print(ts[COLS], energy_plan)
    #-------------------
    sim = Simulation()
    sim.household.DNSP = "Ausgrid"
    sim.household.tariff_type = "tou"
    ts = sim.create_ts_empty()
    (ts, energy_plan) = load_household_import_rate(ts,
                                        tariff_type = sim.household.tariff_type,
                                        dnsp = sim.household.DNSP,
                                        return_energy_plan = True,
                                        )
    print(ts)
    print(ts[COLS], energy_plan)

    #-------------------
    sim = Simulation()
    sim.household.DNSP = "Ausgrid"
    sim.household.tariff_type = "CL"
    sim.household.control_load = 1
    ts = sim.create_ts_empty()
    (ts, energy_plan) = load_household_import_rate(ts,
                                        tariff_type = sim.household.tariff_type,
                                        dnsp = sim.household.DNSP,
                                        control_load = sim.household.control_load,
                                        return_energy_plan = True,
                                        )
    print(ts)
    print(ts[COLS], energy_plan)
    return

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

    test_get_gas_rate()

    # test_load_household_import_rate()

    # test_calculate_energy_cost()

    pass
#---------------------------
def main():

    from tm_solarshift.general import Simulation
    sim = Simulation()
    ts = sim.create_ts()
    
    location = Location("Sydney")
    ts = load_emission_index_year( ts, location, index_type='total', year=2022 )
    ts = load_emission_index_year( ts, location, index_type='marginal', year=2022 )

    ts = load_wholesale_prices(ts, location)
    
    ts = load_household_import_rate(
        ts,
        tariff_type="tou",
        return_energy_plan=False
    )

    print(ts.head(20))
    pass

if __name__ == "__main__":
    main()