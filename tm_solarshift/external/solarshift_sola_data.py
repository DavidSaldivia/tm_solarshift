
import os
import glob
import re
from datetime import (
    datetime,
    timedelta,
)
import zipfile
from typing import Optional, Any

from tm_solarshift.constants import DIRECTORY
# from tm_solarshift.external.model_constants import SolarShiftConstants
import numpy as np
import pandas as pd

pd.options.mode.chained_assignment = None  # default='warn'

NUM_TSTAMP_IN_DAY = 288
MINUTES_PER_HOUR = 60
MISSING_DATA_THRESHOLD = {
    300: 276,
    900: 92,
}

# fileDir = os.path.dirname(__file__)

r"""
Data directory and file names.
Overall there are two main datasets:
    1. Site energy data
    Where each site has 3 data types:
        a. PV data (Wh)
        b. Load data (Wh)
        c. Hot water data (Wh)
    Energy data is stored in a .dat file which is a 2D array of floats.
    Each row is a day and each column is a 5 minute interval,
    so there are 288 columns in total.
    In order to select data for a particular site, 
    we use a date_list file which is a csv storing the date and site id.
    Their indices match up with the rows in the energy data file.

    Data with the same data type is aggregated into one channel 
    (i.e a three-phase PV system would just have one channel of PV data).
    2. Circuit data
    Where each circuit has 6 data types:
        a. Energy (Wh)
        b. Energy reactive (VARh)
        c. Current max (A)
        d. Current min (A)
        e. Voltage max (V)
        f. Voltage min (V)
    These cicuits include all different types of circuits in the site,
    including PV, load, hot water, battery, other subloads etc.
    Otherwise data is stored in the same way as site energy data,
    with a date_list file and a .dat file.
"""

class DATA_DIRECTORY(object):
    sa_data_dirs = {
        "raw_data": DIRECTORY.DIR_DATA["SA_raw"],
        "processed_data": DIRECTORY.DIR_DATA["SA_processed"],
        "energy_plans": DIRECTORY.DIR_DATA["tariffs"]
        }
    solar_hot_water_dir = "solar_hot_water/"
    sa_file_names = {
        # raw data
        "site_list": "SolA_site_list.csv",
        "site_circuit_list": "SolA_site_circuit_list.csv",
        "site_pv_data": "site_pv_data.dat",
        "site_load_data": "site_load_data.dat",
        "site_hot_water_data": "site_hot_water_data.dat",
        "site_date_list": "SolA_site_date_list.csv",
        "all_circuit_data": "all_circuit_data.dat",
        "all_circuit_date_list": "SolA_all_circuit_date_list.csv",
        # processed data
        # sites with electric hot waters
        "site_basic_stats": "site_basic_stats.csv",
        "site_hot_water_data_processed": "site_hot_water_data_processed.dat",
        "site_date_list_processed": "SolA_site_date_list_processed.csv",
        "site_hot_water_stats": "site_hot_water_stats.csv",
        "site_hot_water_classification": "site_hot_water_classification.csv",
        "site_controlled_load_info": "site_controlled_load_info.csv",
        # sites with solar hot water
        "site_basic_stats_SHW": "site_basic_stats_SHW.csv",
        "site_hot_water_data_processed_SHW": "site_hot_water_data_processed_SHW.dat",
        "site_date_list_processed_SHW": "SolA_site_date_list_processed_SHW.csv",
        "site_hot_water_stats_SHW": "site_hot_water_stats_SHW.csv",
        # climate zone grid file
        "climate_zone_grid": "clim-zones.tif",
        # hot water control
    }
    ee_data_dirs = {
        "EE_data": "data/raw/EE_data/",
        "CL_data": "data/raw/EE_data/CL/",
        "VPP_data": "data/raw/EE_data/VPP/",
        "processed_data": "data/processed/EE_data/",
    }
    ee_file_names = {
        "site_list": "Customer List_unsw_updated.csv",
        "site_hot_water_stats_300": "site_hot_water_stats_5_min.csv",
        "site_hot_water_stats_900": "site_hot_water_stats_15_min.csv",
        "site_hot_water_classification_300": "site_hot_water_classification_5_min.csv",
        "site_hot_water_classification_900": "site_hot_water_classification_15_min.csv",
    }
    site_data_types = ["pv", "load", "hot_water"]
    circuit_data_types = [
        "energy",
        "energy_reactive",
        "current_max",
        "current_min",
        "voltage_max",
        "voltage_min",
    ]
    fig_dir = "data/processed/figures/"
    price_data_dir = "data/raw/NEM_price_data/"
    price_data_filenames = {
        "5min_price_total": "5min_price_total.csv",
    }


######################################################


def get_site_data(
    site_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    data_types: list[str] = [],
    data_dir: str = DATA_DIRECTORY.sa_data_dirs["raw_data"],
) -> dict[str, Any]:
    """
    get a single site's data
    Args:
        site_id: site id
        start_date: start date, inclusive
        end_date: end date, exclusive
        data_types: data types to return (pv, load, hot_water)
    returns:
        a dictionary containing the date_list and the data array
    """
    
    returned_data = {}
    # find the indices of the site in the date list, with the correct date range
    all_date_list = pd.read_csv(
        os.path.join(data_dir, DATA_DIRECTORY.sa_file_names["site_date_list"]),
        index_col=False,
    )
    site_date_list = all_date_list.loc[all_date_list["site_id"] == site_id, :]
    site_dates = site_date_list["date"].copy()
    site_date_list["date"] = pd.to_datetime(site_dates)
    if start_date is not None:
        site_date_list = site_date_list.loc[
            site_date_list["date"] >= start_date, :
        ]
    if end_date is not None:
        site_date_list = site_date_list.loc[
            site_date_list["date"] <= end_date, :
        ]
    site_index = site_date_list.index
    if data_types == []:
        data_types = ["pv", "load", "hot_water"]
    returned_data["date_list"] = site_date_list.reset_index(drop=True)
    # load the data then select the rows corresponding to the site based on the indices
    for data_type in data_types:
        site_data_memmap = np.memmap(
            os.path.join(
                data_dir,
                DATA_DIRECTORY.sa_file_names[f"site_{data_type}_data"],
            ),
            dtype="float32",
            mode="r",
        ).reshape(-1, NUM_TSTAMP_IN_DAY)
        returned_data[data_type] = site_data_memmap[site_index]
    return returned_data


def get_circuit_data(
    circuit_id,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    data_types: list[str] = [],
    secondary_data_types: list[str] = [],
    data_dir: str = DATA_DIRECTORY.sa_data_dirs["raw_data"],
) -> dict[str, Any]:
    """
    Get a single circuit's data
    Args:
        circuit_id: circuit id
        start_date: start date, inclusive
        end_date: end date, inclusive
        data_types: data types to return (energy, voltage_max, voltage_min, current_max, current_min)
    returns:
        a dictionary containing the date_list and the data array
    """
    returned_data = {}
    all_date_list = pd.read_csv(
        os.path.join(
            data_dir,
            DATA_DIRECTORY.sa_file_names["all_circuit_date_list"],
        ),
        index_col=False,
    )
    circuit_date_list = all_date_list.loc[
        all_date_list["c_id"] == circuit_id, :
    ]
    circuit_date_list["date"] = pd.to_datetime(circuit_date_list["date"])
    if start_date is not None:
        circuit_date_list = circuit_date_list.loc[
            circuit_date_list["date"] >= start_date, :
        ]
    if end_date is not None:
        circuit_date_list = circuit_date_list.loc[
            circuit_date_list["date"] <= end_date, :
        ]

    circuit_data_memmap = np.memmap(
        os.path.join(
            data_dir,
            DATA_DIRECTORY.sa_file_names[f"all_circuit_data"],
        ),
        dtype="float32",
        mode="r+",
    ).reshape(-1, NUM_TSTAMP_IN_DAY)

    if data_types == []:
        data_types = DATA_DIRECTORY.circuit_data_types

    for data_type in data_types:
        circuit_date_list_one_column = circuit_date_list.loc[
            circuit_date_list["data_type"] == data_type, :
        ]
        returned_data[
            f"{data_type}_date_list"
        ] = circuit_date_list_one_column.reset_index(drop=True)
        circuit_index = circuit_date_list_one_column.index
        returned_data[data_type] = circuit_data_memmap[circuit_index]
    if "power_factor" in secondary_data_types:
        for data_type in ["energy", "energy_reactive"]:
            if data_type not in data_types:
                circuit_date_list_one_column = circuit_date_list.loc[
                    circuit_date_list["data_type"] == data_type, :
                ]
                circuit_index = circuit_date_list_one_column.index
                returned_data[data_type] = circuit_data_memmap[circuit_index]
                
        returned_data["power_factor"] = returned_data["energy"] / np.sqrt(
            np.square(returned_data["energy_reactive"])
            + np.square(returned_data["energy"])
        )
    return returned_data


def get_site_hot_water_circuit_data(
    site_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    data_types: list[str] = [],
    secondary_data_types: list[str] = [],
    data_dir: str = DATA_DIRECTORY.sa_data_dirs["raw_data"],
) -> dict[str, Any]:
    
    site_circuit_list = pd.read_csv(
        os.path.join(
            data_dir,
            DATA_DIRECTORY.sa_file_names["site_circuit_list"],
        ),
        index_col=False,
    )

    hot_water_circuits = site_circuit_list.loc[
        (site_circuit_list["site_id"] == site_id)
        & (site_circuit_list["con_type"] == "load_hot_water"),
        "c_id",
    ].to_list()

    returned_data = {}
    if "energy" not in data_types:
        data_types.append("energy")
    if len(hot_water_circuits) > 1:
        max_energy = None
        selected_circuit_id = None
        for circuit_id in hot_water_circuits:
            energy_data = get_circuit_data(
                circuit_id,
                start_date=start_date,
                end_date=end_date,
                data_types=["energy"],
                data_dir=data_dir,
            )
            if max_energy is None:
                max_energy = energy_data["energy"].sum()
                selected_circuit_id = circuit_id
            elif max_energy < energy_data["energy"].sum():
                max_energy = energy_data["energy"].sum()
                selected_circuit_id = circuit_id
    else:
        selected_circuit_id = hot_water_circuits[0]

    circuit_data = get_circuit_data(
        selected_circuit_id,
        start_date=start_date,
        end_date=end_date,
        data_types=data_types,
        secondary_data_types=secondary_data_types,
        data_dir=data_dir,
    )
    for data_key in circuit_data.keys():
        returned_data[data_key] = circuit_data[data_key]
        # else:
        #     if data_key in data_types or data_key in secondary_data_types:
        #         if (
        #             circuit_data[data_key].shape[0]
        #             != returned_data[data_key].shape[0]
        #         ):
        #             if (
        #                 circuit_data[data_key].shape[0]
        #                 > returned_data[data_key].shape[0]
        #             ):
        #                 returned_data[data_key] = circuit_data[data_key]
        #             else:
        #                 continue
        #         else:
        #             if (
        #                 circuit_data[data_key].flatten().sum()
        #                 > returned_data[data_key].flatten().sum()
        #             ):
        #                 returned_data[data_key] = circuit_data[data_key]

    return returned_data


def prepare_site_data_in_df(
    site_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    data_types: list[str] = [],
    data_dir: str = DATA_DIRECTORY.sa_data_dirs["raw_data"],
) -> pd.DataFrame:
    """Prepare site data in dataframe

    Args:
        site_id (int): site id
        start_date (Optional[datetime], optional): start date (inclusive). Defaults to None.
        end_date (Optional[datetime], optional): end date (exclusive). Defaults to None.
        data_types (list[str], optional): data types to include. Defaults to [].
        data_dir (str, optional): data dir. Defaults to DATA_DIRECTORY.sa_data_dirs["raw_data"].

    Returns:
        pd.DataFrame: returned df
    """
    site_data = get_site_data(
        site_id,
        start_date=start_date,
        end_date=end_date,
        data_types=data_types,
        data_dir=data_dir,
    )
    site_data_df = pd.DataFrame()
    for data_type in data_types:
        site_data_df[data_type] = site_data[data_type].flatten()
    datetime_index = None
    for i in range(len(site_data["date_list"])):
        date = site_data["date_list"].loc[i, "date"]
        if datetime_index is None:
            datetime_index = pd.date_range(
                start=date,
                end=date + pd.Timedelta(days=1),
                freq="5T",
                inclusive="right",
            )
        else:
            datetime_index = datetime_index.union(
                pd.date_range(
                    start=date,
                    end=date + pd.Timedelta(days=1),
                    freq="5T",
                    inclusive="right",
                )
            )
    site_data_df["t_stamp"] = datetime_index
    return site_data_df