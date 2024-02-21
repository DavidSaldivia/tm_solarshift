# import energy_plan
from energy_plan import (
    FlatPlan,
    ToUPlan,
    DemandPlan,
    StepPlan,
    SeasonalCLPlan,
)

import json, os
from SA_Solarshift_data import DATA_DIRECTORY
from model_constants import SolarShiftConstants
from datetime import datetime
import pandas as pd

CONTROLLED_LOAD_INFO = SolarShiftConstants.CONTROLLED_LOAD_INFO

def find_energy_plan_class(tariff_type: str):
    
    if tariff_type == "flat":
        return FlatPlan
    elif tariff_type == "tou":
        return ToUPlan
    elif tariff_type == "demand":
        return DemandPlan
    elif tariff_type == "step":
        return StepPlan
    else:
        raise ValueError(f"Tariff type {tariff_type} not recognised")


def get_energy_plan_for_dnsp(
    dnsp: str,
    tariff_type: str,
    convert: bool = True,
    controlled_load_num: int = 0,
    switching_cl: bool = False,
):
    """
    get energy plan for dnsp
    Args:
        dnsp: str, dnsp name
        tariff_type: str, tariff type
        convert: bool, whether to convert json tariff to energy plan dict
        controlled_load_num: int, controlled load number
        switching_cl: bool, whether to use switching controlled load
    """
    if " " in dnsp:
        dnsp = dnsp.replace(" ", "")
    energy_plan_path = os.path.join(
        DATA_DIRECTORY.sa_data_dirs["energy_plans"],
        f"{dnsp.lower()}_{tariff_type}_plan.json",
    )
    with open(energy_plan_path, "rb") as f:
        energy_plan = json.load(f)
    if convert:
        plan_class = find_energy_plan_class(tariff_type)
        energy_plan = plan_class.convert_json_tariff(energy_plan)
    if controlled_load_num > 0:
        if switching_cl:
            cl_plan_path = os.path.join(
                DATA_DIRECTORY.sa_data_dirs["energy_plans"],
                f"{dnsp.lower()}_controlled_load_{controlled_load_num}_plan.json",
            )
            if not os.path.exists(cl_plan_path):
                cl_plan_path = os.path.join(
                    DATA_DIRECTORY.sa_data_dirs["energy_plans"],
                    f"ausgrid_controlled_load_{controlled_load_num}_plan.json",
                )
            with open(cl_plan_path, "rb") as f:
                cl_plan = json.load(f)
            energy_plan["daily_charge_CL"] = cl_plan["charges"][
                "service_charges"
            ][0]["rate"]
            energy_plan["CL_rate"] = cl_plan["charges"]["energy_charges"][0][
                "rate_details"
            ][0]["rate"]
            energy_plan["CL_plan"] = cl_plan
        elif dnsp in CONTROLLED_LOAD_INFO and (
            f"controlled_load_{controlled_load_num}"
            in CONTROLLED_LOAD_INFO[dnsp]
        ):
            energy_plan["daily_charge_CL"] = CONTROLLED_LOAD_INFO[dnsp][
                f"controlled_load_{controlled_load_num}"
            ]["service_charges"][0]["rate"]
            energy_plan["CL_rate"] = CONTROLLED_LOAD_INFO[dnsp][
                f"controlled_load_{controlled_load_num}"
            ]["energy_charges"][0]["rate_details"][0]["rate"]

    return energy_plan


def get_energy_breakdown(
    tariff_type,
    tariff_structure,
    raw_data,
    resolution,
    return_raw_data=False,
    include_seasonal_cl=False,
):
    """get energy breakdown for a given tariff type

    Args:
        tariff_type (str): tariff type (tou/flat)
        tariff_structure (dict): tariff structure
        raw_data (pd.DataFrame): raw data
        resolution (int): resolution in seconds
        return_raw_data (bool, optional): whether to return raw data. Defaults to False.
        include_seasonal_cl (bool, optional): whether to include seasonal controlled load. Defaults to False.

    Returns:
        tuple: (energy breakdown, raw data)
    """
    plan_class = find_energy_plan_class(tariff_type)
    if tariff_type == "tou":
        energy_breakdown, raw_data = plan_class.get_energy_breakdown(
            raw_data,
            tariff_structure,
            resolution=resolution,
            return_raw_data=True,
        )
        raw_data = raw_data.drop(columns=["import_energy", "export_energy"])
    else:
        energy_breakdown, raw_data = plan_class.get_energy_breakdown(
            raw_data, resolution=resolution, return_raw_data=True
        )
    if include_seasonal_cl:
        raw_data = SeasonalCLPlan.assign_cl_rate(raw_data, tariff_structure)
        
    if return_raw_data:
        return energy_breakdown, raw_data
    else:
        return energy_breakdown


def add_wholesale_prices(raw_data: pd.DataFrame, state: str = "NSW"):
    """add wholesale prices to raw data
    Args:
        raw_data (pd.DataFrame): raw data
        state (str, optional): state. Defaults to "NSW".
    """
    price_data = pd.read_csv(
        os.path.join(
            DATA_DIRECTORY.price_data_dir,
            DATA_DIRECTORY.price_data_filenames["5min_price_total"],
        ),
        index_col=False,
    )
    state_price_data = price_data.loc[
        price_data["state"] == f"{state}1", :
    ].reset_index(drop=True)
    state_price_data["tstamp"] = pd.to_datetime(state_price_data["tstamp"])
    raw_data = raw_data.merge(
        state_price_data[["tstamp", "RRP"]],
        how="left",
        left_on="t_stamp",
        right_on="tstamp",
    )
    raw_data = raw_data.drop(columns=["tstamp"])
    raw_data["RRP"] = raw_data["RRP"] / 1000.0
    raw_data = raw_data.rename(columns={"RRP": "wholesale_price"})
    return raw_data


if __name__ == "__main__":
    start_run_time = datetime.now()
    dnsp = "Ausgrid"
    print(get_energy_plan_for_dnsp(dnsp, "tou", convert=True))
    print(datetime.now() - start_run_time)
