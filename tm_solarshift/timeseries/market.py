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
FILE_GAS_TARIFF_SAMPLE = DIRECTORY.FILE_GAS_TARIFF_SAMPLE


def load_household_import_rate(
        ts_index: pd.DatetimeIndex,
        tariff_type: str = "flat",
        control_type: str = "CL1",
        dnsp: str = "ausgrid",
) -> pd.DataFrame:
    """It receives a ts_index (from a simulation for example) and returns a dataframe with "tariff" (the tariff rate in AUD/kWh) and "rate_type" (str as label of rate applied) columns.

    Args:
        ts_index (pd.DatetimeIndex): ts_index from a simulation.
        tariff_type (str, optional): the tariff type. see DEFAULT.TARIFF_TYPES. Defaults to "flat".
        control_type (str, optional): the control type used. see DEFAULT.CONTROL_TYPES. Defaults to "CL1".
        dnsp (str, optional): The DNSP defined from the location. Defaults to "ausgrid".

    Returns:
        pd.DataFrame: Dataframe with "tariff" in (AUD/kWh) and "rate_type" (str)
    """

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
            control_type_ = "CL1" if control_type == "diverter" else control_type
            file_path = os.path.join(DIR_TARIFFS, f"{dnsp.lower()}_{control_type_}_plan.json")
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


def load_household_gas_rate(
        ts_power: pd.Series,
        file_path: str = FILE_GAS_TARIFF_SAMPLE,
) -> pd.DataFrame:
    """It receives a ts_power and applies a tariff defined by file_path. It receives a ts_power series containing the heater_power (as defined in df_econ), which is in kW. It converts it into energy consumption and generates a tariff timeseries defined by gas tariffs (acummulated energy during a day has different rate). It assumes hot water is all energy consumption in the gas bill. This is a conservative approach, as tariff is lower by consumption.

    Args:
        ts_power (pd.Series): heater_power series from a simulation (in kW).
        file_path (str, optional): file_path to the gas_tariff. Defaults to FILE_GAS_TARIFF_SAMPLE.

    Returns:
        pd.DataFrame: A dataframe with the columns "tariff" (in AUD/kWh) and "rate_type" = "gas"
    """

    #importing the energy plan
    with open(file_path) as f:
        plan = json.load(f)
    rate_details = plan["charges"]["energy_charges"]["rate_details"]
    rates = []
    edges = [0,]
    for bin in rate_details:
        rates.append(bin["rate"])
        edges.append(bin["ceil"])

    #getting the tariff rate
    ts_index = pd.to_datetime(ts_power.index)
    ts_tariff = pd.DataFrame(index=ts_index)
    freq = ts_index.freq
    if freq is not None:
        STEP_h = freq.n * CF("min", "hr")

    ts_tariff["heater_power"] = ts_power * CF("kW", "MJ/hr") * STEP_h
    ts_tariff["power_cum_sum"] = ts_tariff.groupby(ts_index.date)['heater_power'].cumsum()
    ts_tariff["tariff"] = pd.cut(
        ts_tariff["power_cum_sum"],
        bins = edges, labels = rates, right = False
    ).astype("float")
    ts_tariff["tariff"] = ts_tariff["tariff"] / CF("MJ","kWh")
    ts_tariff["rate_type"] = "gas"

    return ts_tariff


def load_emission_index_year(
        timeseries: pd.DataFrame,
        location: str|Location = "Sydney",
        index_type: str = "total",
        year: int = 2022,
        ) -> pd.DataFrame:
    """It returns the emissions for a given year and location (based on state). The emissions are obtained by nemed. It returns either the marginal or total emission index (in ton_eq_CO2/MWh)

    Args:
        timeseries (pd.DataFrame): The dataframe containing the index.
        location (str | Location, optional): Defaults to "Sydney".
        index_type (str, optional): "marginal" or "total" as defined by NEMED. Defaults to "total".
        year (int, optional): Year to check the emissions. Defaults to 2022.

    Returns:
        pd.DataFrame: A dataframe with the emissions in the same timestep than the initial timeseries
    """
    
    if (type(location) == Location):
        state = location.state
        loc_st = DEFINITIONS.LOCATIONS_STATE
        location = list(loc_st.keys())[list(loc_st.values()).index(state)]
    
    columns = {
        "total": "intensity_index",
        "marginal": "marginal_index",
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


def load_wholesale_prices(
        ts_index: pd.DatetimeIndex,
        location: Location|str = Location(),
        ) -> pd.Series:
    """It returns the wholesale prices (in AUD/MWh) for a ts_index (from a simulation) based on NEMOSIS data.

    Args:
        ts_index (pd.DatetimeIndex): index from a simulation dataframe (for example Simulation.time_params.idx).
        location (Location, optional): The location where the wholesale prices are calculated. It corresponds to the state wholesale price.

    Returns:
        pd.Series: timeseries with the wholesale price (in AUD/MWh)
    """
    
    df_SP = pd.read_csv( FILES["WHOLESALE_PRICES"], index_col=0 )
    df_SP.index = pd.to_datetime(df_SP.index).tz_localize(None)

    if type(location) == str:   #city
        nem_region = DEFINITIONS.LOCATIONS_NEM_REGION[location]
    elif type(location) == Location:
        nem_region = DEFINITIONS.STATES_NEM_REGION[location.state]

    STEP = pd.to_datetime(ts_index).freq.n
    ts = pd.Series(
        df_SP[nem_region].resample(f"{STEP}min").interpolate('linear')
    ).loc[ts_index]
    return ts