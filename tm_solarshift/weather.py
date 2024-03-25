import os
import sys
import pandas as pd
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy
import cartopy.crs as ccrs                   # import projections
import cartopy.feature as cf                 # import features

from typing import Optional, List, Dict, Union, Any, Tuple

from tm_solarshift.units import Variable
from tm_solarshift.constants import (DIRECTORY, DEFINITIONS)
from tm_solarshift.location import (Location, from_postcode)

DIR_DATA = DIRECTORY.DIR_DATA
TS_WEATHER = DEFINITIONS.TS_TYPES["weather"]
DEFINITION_SEASON = DEFINITIONS.SEASON
LOCATIONS_METEONORM = DEFINITIONS.LOCATIONS_METEONORM
LOCATIONS_STATE = DEFINITIONS.LOCATIONS_STATE
LOCATIONS_COORDINATES = DEFINITIONS.LOCATIONS_COORDINATES

#--------------
DIR_METEONORM = os.path.join(DIR_DATA["weather"], "meteonorm_processed")
DIR_MERRA2 = os.path.join(DIR_DATA["weather"], "merra2_processed")
DIR_NCI = os.path.join(DIR_DATA["weather"], "nci_processed")

FILES_WEATHER = {
    "METEONORM_TEMPLATE" : os.path.join(DIR_METEONORM, "meteonorm_{:}.csv"),  #expected LOCATIONS_METEONORM
    "MERRA2" : os.path.join(DIR_MERRA2, "merra2_processed_all.nc"),
    "NCI": None,
}
VARIABLES_NAMES = {
    "GHI": "Irradiance",
    "temp_amb": "Ambient Temperature",
    "temp_mains": "Mains Temperature",
}
VARIABLE_DEFAULTS = {
    "GHI" : 1000.,
    "temp_amb" : 25.,
    "temp_mains" : 20.,
}
VARIABLE_RANGES = {
    "GHI" : (1000.,1000.),
    "temp_amb" : (10.0,40.0),
    "temp_mains" : (10.0,30.0),
}
TYPES_SIMULATION = [
    "tmy",                      # One year of data. Usually with tmy files.
    "montecarlo",               # Random sample of temporal unit (e.g. days) from set (month, week, day).
    "historical",               # Specific dates for a specific location (SolA, EE, EWS, etc).
    "constant_day",             # Constant values each day
    ]
SIMS_PARAMS = {
    "tmy": {
        "dataset": ['METEONORM',],
        "location": LOCATIONS_METEONORM,
    },
    "montecarlo": {
        "dataset": ['METEONORM', 'MERRA2', 'NCI'],
        "subset": ['all', 'annual', 'season', 'month', 'date'],
        "location": DEFINITIONS.LOCATION_DEFAULT,
        "random": [True, False],
        "value": None,
    },
    "historical": {
        "dataset": ['MERRA2', 'NCI', "local"],
        "list_dates": [pd.DatetimeIndex, pd.Timestamp],
        "location": str,
        "file_path": str,
    },
    "constant_day": {
        "dataset": [],
        "random": True,
        "values": VARIABLE_DEFAULTS,
        "ranges": VARIABLE_RANGES,
    }
}
list_aux = list()
for d in SIMS_PARAMS.keys():
    list_aux.append(SIMS_PARAMS[d]["dataset"])
DATASET_ALL = list(dict.fromkeys( [ x for xs in list_aux for x in xs ] )) #flatten and delete dupl.

#----------
def load_day_constant_random(
    timeseries: pd.DataFrame,
    ranges: Optional[Dict[str,tuple]] = None,
    columns: Optional[List[str]] = TS_WEATHER,
) -> pd.DataFrame:

    if ranges == None:
        ranges = VARIABLE_RANGES
    
    dates = np.unique(timeseries.index.date)
    DAYS = len(dates)

    df_weather_days = pd.DataFrame( index=dates, columns=columns)
    df_weather_days.index = pd.to_datetime(df_weather_days.index)
    for lbl in ranges.keys():
        df_weather_days[lbl] = np.random.uniform(
            ranges[lbl][0],
            ranges[lbl][1],
            size=DAYS,
        )

    df_weather = df_weather_days.loc[timeseries.index.date]
    df_weather.index = timeseries.index
    timeseries[columns] = df_weather[columns]
    return timeseries


#---------------------------------
def random_days_from_dataframe(
    timeseries: pd.DataFrame,
    df_sample: pd.DataFrame,
    columns: Optional[List[str]] = TS_WEATHER,
) -> pd.DataFrame :
    """
    This function randomly assign the weather variables of a set of days
    to the timeseries DataFrame. It returns timeseries updated
        
    Parameters
    ----------
    timeseries : pd.DataFrame
        DESCRIPTION.
    set_days : pd.DataFrame
        DESCRIPTION.
    columns : Optional[List[str]], optional
        DESCRIPTION. The default is TS_WEATHER.
    : TYPE
        DESCRIPTION.

    Returns
    -------
    timeseries.

    """
    
    df_sample = df_sample.copy()
    list_dates = np.unique(df_sample.index.date)
    DAYS = len(np.unique(timeseries.index.date))
    list_picked_dates = np.random.choice( list_dates, size=DAYS )
    df_sample["date"] = df_sample.index.date
    set_picked_days = [
        df_sample[df_sample["date"]==date] for date in list_picked_dates
    ]
    df_final = pd.concat(set_picked_days)
    df_final.index = timeseries.index
    timeseries[columns] = df_final[columns]
    
    return timeseries

#---------------------------------
def from_tmy(
        timeseries: pd.DataFrame,
        TMY: pd.DataFrame,
        columns: Optional[List[str]] = TS_WEATHER,
    ) -> pd.DataFrame :
    
    rows_timeseries = len(timeseries)
    rows_tmy = len(TMY)
    
    if rows_tmy <= rows_timeseries:
        N = int( np.ceil( rows_timeseries/rows_tmy ) )
        TMY_extended = pd.concat([TMY]*N, ignore_index=True)
        TMY_final = TMY_extended.iloc[:rows_timeseries]
    else:
        TMY_final = TMY.iloc[:rows_timeseries]

    TMY_final.index = timeseries.index
    timeseries[columns] = TMY_final[columns]
    return timeseries

#---------------------------------
def from_file(
    timeseries: pd.DataFrame,
    file_path: str = None,
    columns: Optional[List[str]] = TS_WEATHER,
    subset_random: Optional[str] = None,
    subset_value: Union[str, int, pd.Timestamp] = None,
) -> pd.DataFrame :
    """
    It returns the dataframe timeseries with the weather loaded from a file.
    It admits optional parameters subset_random and subset_value to select a subset
    from the source and select randomly days from that subset.
    If subset_random is None, load the file as TMY. If the simulation period is longer
    the file is repeated to match it.

    Parameters
    ----------
    timeseries : pd.DataFrame
        The DataFrame defined by profile_new.
    file_path : str
        Path to the file. It is assumed the file is in the correct format.
    columns : Optional[List[str]], optional
        DESCRIPTION. The default is TS_WEATHER.
    subset_random : Optional[str], optional
                    'all': pick from all the dataset,
                    'annual': the year is defined as subset value.
                    'season': the season is defined by subset_value
                                ('summer', 'autumn', 'winter', 'spring')
                    'month': the month is defined by the integer subset_value (1-12),
                    'date': the specific date is defined by a pd.datetime,
                    None: There is not randomization. subset_value is ignored.
                    The default is None.
    subset_value : Optional[str,int], optional. Check previous definition.
                    The default is None.

    Returns
    -------
    timeseries : TYPE
        Returns timeseries with the environmental variables included.

    """
    
    set_days = pd.read_csv(file_path, index_col=0)
    set_days.index = pd.to_datetime(set_days.index)
    if subset_random is None:
        pass
    elif subset_random == 'annual':
        set_days = set_days[
            set_days.index.year==subset_value
            ]
    elif subset_random == 'season':
        set_days = set_days[
            set_days.index.isin(DEFINITION_SEASON[subset_value])
            ]
    elif subset_random == 'month':
        set_days = set_days[
            set_days.index.month==subset_value
            ]  
    elif subset_random == 'date':
        set_days = set_days[
            set_days.index.date==subset_value.date()
            ]  
    
    if subset_random is None:
        timeseries = from_tmy(
            timeseries, set_days, columns=columns
            )
    else:
        timeseries = random_days_from_dataframe(
            timeseries, set_days, columns=columns
            )   
    return timeseries

# -------------
def load_tmy(
    ts: pd.DataFrame,
    params: Dict,
    columns: Optional[List[str]] = TS_WEATHER,
) -> pd.DataFrame:
    
    YEAR = ts.index.year[0]
    if type(params["location"]) == str:
        location = params["location"].lower()
    else:
        location = params["location"]
    dataset = params["dataset"]

    if dataset == "meteonorm":
        df_dataset = load_dataset_meteonorm(location, YEAR)
    elif dataset == "merra2":
        df_dataset = load_dataset_merra2(ts, location, YEAR)
    else:
        raise ValueError(f"dataset: {dataset} is not available.")
    
    return from_tmy( ts, df_dataset, columns=columns )

# -------------
def load_dataset_meteonorm(
        location: str,
        YEAR: int = 2022
) -> pd.DataFrame:

    if location not in DEFINITIONS.LOCATIONS_METEONORM:
        raise ValueError(f"location {location} not in available METEONORM files")
    
    df_dataset = pd.read_csv(
        os.path.join(
            DIR_METEONORM,
            FILES_WEATHER["METEONORM_TEMPLATE"].format(location),
        ),
        index_col=0
    )
    df_dataset.index = pd.to_datetime(df_dataset.index)
    df_dataset["date"] = df_dataset.index
    df_dataset["date"] = df_dataset["date"].apply(lambda x: x.replace(year=YEAR))
    df_dataset.index = df_dataset["date"]
    return df_dataset

def load_dataset_merra2(
        ts: pd.DataFrame,
        location: Location,
        YEAR: int,
        STEP:int = 5,
        file_dataset:str = FILES_WEATHER["MERRA2"],
        ) -> pd.DataFrame:

    if type(location) == int:   #postcode
        (lon,lat) = from_postcode(location, get="coords")
    elif type(location) == str:   #city
        loc = Location(location)
        (lon,lat) = (loc.lon, loc.lat)
    elif type(location) == tuple: #(longitude, latitude) tuple
        (lon,lat) = (location)

    data_weather = xr.open_dataset(file_dataset)
    lons = np.array(data_weather.lon)
    lats = np.array(data_weather.lat)
    lon_a = lons[(abs(lons-lon)).argmin()]
    lat_a = lats[(abs(lats-lat)).argmin()]
    df_w = data_weather.sel(lon=lon_a,lat=lat_a).to_dataframe()

    df_w.index = df_w.index.tz_localize('UTC')
    tz = 'Australia/Brisbane'
    df_w.index = df_w.index.tz_convert(tz)
    df_w.index = df_w.index.tz_localize(None)
    df_w.rename(columns={'SWGDN':'GHI','T2M':'Temp_Amb'},inplace=True)
    df_w = df_w[['GHI','Temp_Amb']].copy()
    df_w = df_w.resample(f"{STEP}T").interpolate()       #Getting the data in half hours
    
    ts["GHI"] = df_w["GHI"]
    ts["Temp_Amb"] = df_w["Temp_Amb"] - 273.15
    
    #########################################
    #Replace later for the closest city
    df_aux = load_dataset_meteonorm("Sydney", YEAR)
    df_aux = df_aux.resample(f"{STEP}T").interpolate()       #Getting the data in half hours
    ts["Temp_Mains"] = df_aux["Temp_Mains"]
    #########################################

    return ts

#----------
def load_montecarlo(
    ts: pd.DataFrame,
    params: Dict,
    columns: Optional[List[str]] = TS_WEATHER,
) -> pd.DataFrame:
    
    dataset = params["dataset"]
    location = params["location"]
    subset = params["subset"]
    value = params["value"]
    
    if dataset == "meteonorm":
        df_dataset = load_dataset_meteonorm(location)
    elif dataset == "merra2":
        df_dataset = load_dataset_merra2(ts, location, ts.index.year[0])
    else:
        raise ValueError(f"dataset: {dataset} is not available.")
    
    if subset is None:
        pass
    elif subset == 'annual':
        df_sample = df_dataset[
            df_dataset.index.year==value
            ]
    elif subset == 'season':
        df_sample = df_dataset[
            df_dataset.index.isin(DEFINITION_SEASON[value])
            ]
    elif subset == 'month':
        df_sample = df_dataset[
            df_dataset.index.month==value
            ]  
    elif subset == 'date':
        df_sample = df_dataset[
            df_dataset.index.date==value.date()
            ]  
    return random_days_from_dataframe( ts, df_sample, columns=columns )

#----------------
def load_historical(
    ts: pd.DataFrame,
    params: Dict,
    columns: Optional[List[str]] = TS_WEATHER,
) -> pd.DataFrame:
    
    pass

    return None

#----------
def add_to_timeseries(
        ts: pd.DataFrame,
        type_sim: str,
        params: Dict = {},
        columns: Optional[List[str]] = TS_WEATHER,
) -> pd.DataFrame:
    
    #Checking
    if type_sim in TYPES_SIMULATION:
        ... #Check if minimum params are in kwargs.
    else:
        raise ValueError(f"{type_sim} not in {TYPES_SIMULATION}")
    
    if type_sim == "tmy":
        return load_tmy(ts, params, columns)
    
    if type_sim == "montecarlo":
        return load_montecarlo(ts, params, columns)

    if type_sim == "historical":
        return load_historical(ts, params, columns)

    if type_sim == "constant_day":
        return load_day_constant_random(ts)
    

def main():
    #Creating a timeseries
    from tm_solarshift.general import GeneralSetup
    from tm_solarshift.units import Variable

    GS = GeneralSetup()
    ts = GS.simulation.create_new_profile()

    #----------------
    type_sim = "tmy"
    params = {
        "dataset": "meteonorm",
        "location": GS.household.location
    }
    ts = add_to_timeseries(ts, type_sim, params)
    print(ts[TS_WEATHER])

    #----------------
    type_sim = "tmy"
    GS.simulation.YEAR = Variable(2020,"-")
    GS.simulation.location = Location(2035)
    ts = GS.simulation.create_new_profile()
    params = {
        "dataset": "merra2",
        "location": Location(2035)
    }
    ts = add_to_timeseries(ts, type_sim, params)
    print(ts[TS_WEATHER])

    #----------------
    type_sim = "montecarlo"
    params = {
        "dataset": "meteonorm",
        "location": GS.household.location,
        "subset": "month",
        "value": 5
    }
    ts = add_to_timeseries(ts, type_sim, params)
    print(ts[TS_WEATHER])

    #----------------
    type_sim = "constant_day"
    ts = add_to_timeseries(ts, type_sim)
    print(ts[TS_WEATHER])

    return


if __name__ == "__main__":
    main()
    pass