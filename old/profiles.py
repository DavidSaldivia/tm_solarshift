import os
import sys
import pandas as pd
import numpy as np
from typing import Optional, List, dict, Any, Union
from scipy.interpolate import interp1d
from scipy.stats import truncnorm

from tm_solarshift.constants import (
    DIRECTORY, DEFINITIONS, PROFILES, UNITS
)
DIR_DATA = DIRECTORY.DIR_DATA
FILE_SAMPLES = DIRECTORY.FILE_SAMPLES
SEASON_DEFINITION = DEFINITIONS.SEASON
LOCATIONS_NEM_REGION = DEFINITIONS.LOCATIONS_NEM_REGION
PROFILES_TYPES = PROFILES.TYPES
PROFILES_COLUMNS = PROFILES.COLUMNS
CF = UNITS.conversion_factor

FILE_WHOLESALE_PRICES = os.path.join(DIR_DATA["energy_market"], 'SP_2017-2023.csv')
#---------------------------------
W2kJh = CF("W", "kJ/h")

#---------------------------------
# DEFINITION OF PROFILES
# In each case 0 means not included (filled with NaN or dummy value)

# profile_PV
# Profile for the PV generation source
#       0: No PV included (generation = 0 all the time)
#       1: Gaussian shape with peak as PV_NomPow

# profile_Elec
# Profile for the electricity load (non-DEHW)
#       0: No Electricity load included (load = 0 all the time)

# profile_HWD
# Profile for the HWD profile
#       0: No water draw profile (HWD = 0 all the time)
#       1: Morning and evening only
#       2: Morning and evening with day time
#       3: Evenly distributed
#       4: Morning
#       5: Evening
#       6: Late night
#       7: Step Profile

# profile_control
# Profile for the control strategy
#   -1: General supply (24hrs)
#   0: No load (to check thermal losses)
#   1: Control load 1 (10pm-7am)
#   2: Control load 2 (at all time, except peak period: 4pm-8pm)
#   3: Ausgrid's Control load 3 (new solar soak) (roughly 10pm-7pm + 9am-3pm)
#   4: Only solar soak (9am-3pm)
#   5: Specific Control strategy (defined by file file_cs)

class TimeSeries():
    def __init__(self,
                 START: int = 0,
                 STOP: int = 8760,
                 STEP: int= 3,
                 YEAR: int = 2022):

        self.START = START              # [hr]
        self.STOP = STOP                # [hr]
        self.STEP = STEP                # [min]
        self.YEAR = YEAR                # [-]
        
        self.STEP_h = self.STEP / 60.0
        self.PERIODS = int(
            np.ceil((self.STOP - self.START) / self.STEP_h)
        )

    @property
    def idx(self):
        start_time = (
            pd.to_datetime(f"{self.YEAR}-01-01 00:00:00") 
            + pd.DateOffset(hours=self.START)
        )
        idx = pd.date_range(
            start=start_time, 
            periods=self.PERIODS,
            freq=f"{self.STEP}min"
        )
        return idx
        
    @property
    def data(self):
        return pd.DataFrame(index=self.idx, columns=PROFILES_COLUMNS)

    @classmethod
    def new_from_gs(cls, general_setup = None):
        ts = cls(
            START = general_setup.START,
            STOP = general_setup.STOP,
            STEP = general_setup.STEP,
            YEAR = general_setup.YEAR,
        )
        return ts

    def load_HWDP(
            self,
            method: str = 'standard',
            HWD_daily_dist: pd.DataFrame = pd.DataFrame(),
            HWD_hourly_dist: int = 0,
            event_probs: pd.DataFrame = pd.DataFrame(),
            columns: list[str] = PROFILES_TYPES['HWDP']
            ):
        
        self.df = HWDP_generator(self,
            method = method,
            HWD_daily_dist = HWD_daily_dist,
            HWD_hourly_dist = HWD_hourly_dist,
            event_probs = event_probs,
            columns = columns)
        return

#---------------------------------
def new_profile(
    general_setup: Any,
    profile_columns: list[str] = PROFILES_COLUMNS,
) -> pd.DataFrame:

    START = general_setup.START
    STEP = general_setup.STEP
    YEAR = general_setup.YEAR
    PERIODS = general_setup.PERIODS

    start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") \
        + pd.DateOffset(hours=START)
    idx = pd.date_range(
        start=start_time, 
        periods=PERIODS, 
        freq=f"{STEP}min"
    )
    Profiles = pd.DataFrame(index=idx, columns=profile_columns)

    return Profiles

#---------------------------------
#### Basic functions for profiles

def profile_gaussian(df, mu1, sig1, A1, base=0):

    aux = df.index.hour + df.index.minute / 60.0
    Amp = A1 * sig1 * (2 * np.pi) ** 0.5
    series = base + (Amp / sig1 / (2 * np.pi) ** 0.5) * np.exp(
        -0.5 * (aux - mu1) ** 2 / sig1**2
    )
    return series

def profile_step(df, t1, t2, A1, A0=0):
    aux = df.index.hour + df.index.minute / 60.0
    series = np.where((aux >= t1) & (aux < t2), A1, A0)
    return series

#---------------------------------
#### Hot Water Profile Generation
def events_basic():

    event1 = {
        "name": "custom",  # Event type label
        "basis": "daily",  # [str] To determine number of events
        "N_ev_min": 1,  # [-] Minimum N_events in the specific basis
        "N_ev_max": 4,  # [-] Maximum N_events in the specific basis
        "t_ini": 3,  # [hr] Decimal time for event start
        "t_fin": 23,  # [hr] Decimal time for event finish
        "dt_min": 3,  # [mins] Minimum duration for event
        "dt_max": 60,  # [mins] Maximum duration for event
        "factor_a": 50,  # [kg]
        "factor_b": 200,  # [kg]
        "DensFunc": "uniform",
        "HWDP_dist": None,
    }

    return event1

#---------------------------------
def events_file(file_name=None, sheet_name=None):

    events = pd.read_excel(
        file_name,
        sheet_name=sheet_name,
    )

    return events

#---------------------------------

def HWD_daily_distribution(
    general_setup: Any,
    Profiles: pd.DataFrame
) -> pd.DataFrame:
    """
    To create HWDP we need two distribution: an hourly distribution (intra-days) and
    an daily distribution (inter-days).
    This function returns a daily distribution of HWD based on a method

    Parameters
    ----------
    general_setup : Any
        DESCRIPTION.
    Profiles : pd.DataFrame
        DESCRIPTION.

    Returns
    -------
    None.

    """
    
    HWD_avg = general_setup.HWD_avg 
    HWD_std = general_setup.HWD_std 
    HWD_min = general_setup.HWD_min 
    HWD_max = general_setup.HWD_max 
    HWD_daily_dist = general_setup.HWD_daily_dist

    list_dates = np.unique(Profiles.index.date)
    DAYS = len(list_dates)

    # Including the daily variability, if required
    if HWD_daily_dist == None or not (HWD_std > 0.0):
        m_HWD_day = HWD_avg * np.ones(DAYS)

    elif HWD_daily_dist == "norm":
        m_HWD_day = np.random.normal(
            loc=HWD_avg,
            scale=HWD_std,
            size=int(np.ceil(DAYS)
            )
        )
        m_HWD_day = np.where(m_HWD_day > HWD_min, m_HWD_day, HWD_min)

    elif HWD_daily_dist == "unif":
        m_HWD_day = (HWD_max - HWD_min) * np.random.rand(DAYS) + HWD_min

    elif HWD_daily_dist == "truncnorm":
        myclip_a = HWD_min
        myclip_b = HWD_max
        loc = HWD_avg
        scale = HWD_std
        # This step is counterintuitive (See scipy's documentation for truncnorm)
        a, b = (myclip_a - loc) / scale, (myclip_b - loc) / scale
        m_HWD_day = truncnorm.rvs(
            a, b, loc=loc, scale=scale, size=DAYS
            )
    
    elif HWD_daily_dist == "sample":
        sample = pd.read_csv( FILE_SAMPLES["HWD_daily"] )['m_HWD_day']
        sample = sample[sample>0].to_list()
        m_HWD_day = np.random.choice(sample, size=DAYS)
        
    list_dates = pd.to_datetime(np.unique(Profiles.index.date))
    HWD_daily = pd.DataFrame(
        m_HWD_day, 
        index=list_dates, 
        columns=["HWD_day"]
        )

    return HWD_daily

#---------------------------------
def HWDP_generator_standard(
    Profiles: pd.DataFrame,
    HWD_daily_dist: pd.DataFrame,
    HWD_hourly_dist: int = 0,
    columns: list[str] = PROFILES_TYPES['HWDP'],
) -> pd.DataFrame:
    """
    This function generates a HWDP using the six standard profiles defined in this project.
    Each day has the same 'shape' of water consumption on each day.
    The flow magnitude could be changed only by the daily water consumption,
    which is defined by HWD_Daily

    Parameters
    ----------
    Profiles : pd.DataFrame
        DESCRIPTION.
    HWD_daily_dist : pd.DataFrame
        DESCRIPTION.
    HWD_hourly_dist : int, optional
        DESCRIPTION. The default is 0.
    columns : list[str], optional
        DESCRIPTION. The default is PROFILES_TYPES['HWDP'].
    Returns
    -------
    Profiles : TYPE
        DESCRIPTION.

    """

    # timeseries = Profiles.df
    timeseries = Profiles
    STEP_h = timeseries.index.freq.n / 60.0   # [hr] delta t in hours
    PERIODS = len(timeseries)                 # [-] Number of periods to simulate

    # Creating an auxiliar dataframe to populate the drawings
    df_HWD = pd.DataFrame(index=timeseries.index, columns=columns)

    if HWD_hourly_dist == 0:
        df_HWD["P_HWD"] = np.zeros(PERIODS)
        df_HWD["m_HWD"] = np.zeros(PERIODS)

    elif (HWD_hourly_dist >= 1) & (HWD_hourly_dist <= 6):
        HWDP_day = pd.read_csv(
            os.path.join(
                DIR_DATA["HWDP"],
                f"HWDP_Generic_AU_{HWD_hourly_dist}.csv",
            ),
        )

        f1D = interp1d(
            HWDP_day["time"], HWDP_day["HWDP"],
            kind="linear", fill_value="extrapolate"
        )
        df_HWD["P_HWD"] = f1D(
            df_HWD.index.hour
            + df_HWD.index.minute / 60.0
            + df_HWD.index.second / 3600.0
            )

    else:
        print("HWDP_distribution not valid. The simulation will finish.")
        sys.exit()
    
    # This is to ensure that each day the accumulated hot water profile fraction is 1.
    P_HWD_day = (
        df_HWD.groupby(df_HWD.index.date)["P_HWD"]
        .transform("sum") 
        * STEP_h
    )
    df_HWD["P_HWD"] = np.where(P_HWD_day > 0, 
                               df_HWD["P_HWD"] / P_HWD_day, 
                               0.0)
    df_HWD["m_HWD_day"] = HWD_daily_dist.loc[
        timeseries.index.date
        ]["HWD_day"].values
    df_HWD["m_HWD"] = df_HWD["P_HWD"] * df_HWD["m_HWD_day"]
    
    timeseries[columns] = df_HWD[columns]
    return timeseries


#---------------------------------

def HWDP_generator_events(
    timeseries: pd.DataFrame,
    HWD_daily_dist: Optional[pd.DataFrame] = None,
    HWD_hourly_dist: int = 0,
    event_probs: pd.DataFrame = events_basic(),
    columns: list[str] = PROFILES_TYPES['HWDP'],
) -> pd.DataFrame:
    """
    This function generates HWD profiles different for each day, based on daily
    consumption variability (defined by HWD_daily), and event characteristics

    Parameters
    ----------
    Profiles : pd.DataFrame
        DESCRIPTION.
    HWD_daily_dist : Optional[pd.DataFrame], optional
        DESCRIPTION. The default is None.
    HWD_hourly_dist : int, optional
        DESCRIPTION. The default is 0.
    event_probs : pd.DataFrame, optional
        DESCRIPTION. The default is events_basic().
    columns : list[str], optional
        DESCRIPTION. The default is PROFILES_TYPES['HWDP'].

    Returns
    -------
    Profiles : TYPE
        DESCRIPTION.

    """

    # Profiles = timeseries.df
    Profiles = timeseries
    STEP = Profiles.index.freq.n
    STEP_h = STEP / 60.0
    list_dates = np.unique(Profiles.index.date)
    DAYS = len(list_dates)
    if HWD_daily_dist is None:
        HWD_daily_dist = pd.DataFrame(
            np.zeros(DAYS),
            index=list_dates,
            columns=["HWD_day"]
        )
        
    Events_all = []
    for idx, row in event_probs.iterrows():
        name = row["name"]
        N_ev_min = row["N_ev_min"]
        N_ev_max = row["N_ev_max"]
        t_ini = row["t_ini"]
        t_fin = row["t_fin"]
        dt_min = row["dt_min"]
        dt_max = row["dt_max"]
        factor_a = row["factor_a"]
        factor_b = row["factor_b"]

        # Creating the dataframe for the days of simulation
        df_day = pd.DataFrame(
            index=list_dates, columns=["N_ev", "HWD_day", "Temp_Amb", "Temp_Mains"]
        )

        df_day["N_ev"] = np.random.randint(N_ev_min, N_ev_max + 1, size=DAYS)
        Events_dates = list()
        for idx, row in df_day.iterrows():
            Events_dates = Events_dates + [idx for i in range(row["N_ev"])]
        N_events_total = df_day["N_ev"].sum()
        
        # Creating a dataframe with all the events
        Events = pd.DataFrame(
            [],
            columns=[
                "date", "year", "month", "day",
                "hour", "minute", "duration", "flow",
            ],
        )
        Events["date"] = pd.to_datetime(Events_dates)
        Events["year"] = Events["date"].dt.year
        Events["month"] = Events["date"].dt.month
        Events["day"] = Events["date"].dt.day

        # Obtaining the probabilities of events based on HWDP
        list_hours = np.arange(t_ini, t_fin + 1)
        if HWD_hourly_dist == None or HWD_hourly_dist == 0:
            probs = np.ones(len(list_hours))
        else:
            HWDP_day = pd.read_csv(
                os.path.join(
                DIR_DATA["HWDP"], 
                f"HWDP_Generic_AU_{HWD_hourly_dist}.csv"
                )
            )
            probs = HWDP_day.loc[list_hours, "HWDP"].values
        probs = probs / probs.sum()

        # Defining the starting and finishing times
        Events["hour"] = np.random.choice(
            np.arange(t_ini, t_fin + 1),
            size=N_events_total,
            p=probs
        )
        Events["minute"] = np.random.choice(
            np.arange(0, 60, STEP),
            size=N_events_total
        )
        Events["duration"] = np.random.choice(
            np.arange(dt_min, dt_max, STEP),
            size=N_events_total
        )
        Events["datetime"] = pd.to_datetime(
            Events[["year", "month", "day", "hour", "minute"]]
        )
        Events["flow"] = np.random.uniform(
            factor_a, factor_b, size=N_events_total
        )

        # Obtaining the final time of events
        Events["datetime_o"] = Events["datetime"] + Events["duration"].astype(
            "timedelta64[m]"
        )
        # Deleting events that are outside simulation
        Events = Events.drop(
            Events[Events.datetime_o > Profiles.index.max()].index
        )

        Events.index = pd.to_datetime(Events.datetime)
        Events["kg_event"] = Events["flow"] * Events["duration"] / 60
        Events["name"] = name
        
        Events["kg_accum"] = Events.groupby(
            Events.index.date
            )["kg_event"].transform(
                "cumsum"
        )
        Events["kg_max"] = np.array(
            HWD_daily_dist.loc[Events.index.date]["HWD_day"]
        )
        Events = Events[Events["kg_accum"] < Events["kg_max"]].copy()
        
        Events_all.append(Events)
    
    Events_all = pd.concat(Events_all)
    Events_all.sort_values(
        by=["date","name"],
        ascending=[True,False],
        inplace=True
    )
    Events_all["kg_accum"] = Events_all.groupby(
        Events_all.index.date
        )["kg_event"].transform("cumsum")
    Events_all["kg_max"] = np.array(
        HWD_daily_dist.loc[Events_all.index.date]["HWD_day"]
    )
    Events_all = Events_all[
        Events_all["kg_accum"] < Events_all["kg_max"]
        ].copy()
    Events_all["kg_day"] = Events_all.groupby(
        Events_all.index.date
        )["kg_event"].transform("sum")
        
    Events_all["kg_miss"] = Events_all["kg_max"] - Events_all["kg_day"]
    Events_aux = Events_all.copy()
    Events_aux["datetime"] = Events_aux["datetime_o"]
    Events_aux["flow"] = -Events_aux["flow"]

    Events_final = pd.concat([Events_all, Events_aux])[["flow", "datetime"]]
    Events_final = Events_final.groupby(Events_final.datetime).sum()

    # Calculating the daily HWD
    df_HWD = pd.DataFrame(index=Profiles.index, columns=columns)
    df_HWD["Events"] = 0.0
    df_HWD.loc[Events_final.index, "Events"] = Events_final["flow"]
    df_HWD["m_HWD"] = df_HWD.Events.cumsum()
    df_HWD["m_HWD"] = np.where(df_HWD["m_HWD"] < 1e-5, 0, df_HWD["m_HWD"])
    df_HWD["m_HWD_day"] = (
        df_HWD.groupby(df_HWD.index.date)["m_HWD"].transform("sum") 
        * STEP_h
    )
    Profiles[columns] = df_HWD[columns]
    return Profiles

    
#---------------------------------
def HWDP_generator(
    Profiles: pd.DataFrame,
    method: str = 'standard',
    HWD_daily_dist: pd.DataFrame = pd.DataFrame(),
    HWD_hourly_dist: int = 0,
    event_probs: pd.DataFrame = events_basic(),
    columns: list[str] = PROFILES_TYPES['HWDP'],
) -> pd.DataFrame:
    
    if (method == 'standard'):
        Profiles = HWDP_generator_standard(Profiles, 
                                           HWD_daily_dist, 
                                           HWD_hourly_dist, 
                                           columns,)
    elif (method == 'events'):
        Profiles = HWDP_generator_events(Profiles,
                                         HWD_daily_dist, 
                                         HWD_hourly_dist,
                                         event_probs,
                                         columns,)
    else:
        print(f"{method} is not a valid method for HWDP generator")
    
    return Profiles

#---------------------------------
# Weather Functions

def load_weather_day_constant_random(
    Profiles: pd.DataFrame,
    ranges: Optional[dict[str,tuple]] = None,
    columns: Optional[list[str]] = PROFILES_TYPES['weather'],
) -> pd.DataFrame:

    if ranges == None:
        ranges = {
            "GHI" : (1000.,1000.),
            "Temp_Amb" : (10.0,40.0),
            "Temp_Mains" : (10.0,30.0),
        }
    
    dates = np.unique(Profiles.index.date)
    DAYS = len(dates)

    df_weather_days = pd.DataFrame(
        index=dates, columns=columns
    )
    df_weather_days.index = pd.to_datetime(df_weather_days.index)
    for lbl in ranges.keys():
        df_weather_days[lbl] = np.random.uniform(
            ranges[lbl][0],
            ranges[lbl][1],
            size=DAYS,
        )

    df_weather = df_weather_days.loc[Profiles.index.date]
    df_weather.index = Profiles.index
    Profiles[columns] = df_weather[columns]
    return Profiles


#---------------------------------

def weather_random_days_from_dataframe(
    Profiles: pd.DataFrame,
    Set_Days: pd.DataFrame,
    columns: Optional[list[str]] = PROFILES_TYPES['weather'],
) -> pd.DataFrame :
    """
    This function randomly assign the weather variables of a set of days
    to the Profiles DataFrame. It returns Profiles updated
        
    Parameters
    ----------
    Profiles : pd.DataFrame
        DESCRIPTION.
    Set_Days : pd.DataFrame
        DESCRIPTION.
    columns : Optional[list[str]], optional
        DESCRIPTION. The default is PROFILES_TYPES['weather'].
     : TYPE
        DESCRIPTION.

    Returns
    -------
    Profiles.

    """
    dates = np.unique(Set_Days.index.date)
    DAYS = len(np.unique(Profiles.index.date))
    picked_dates = np.random.choice(
        dates, size=DAYS
    )
    Set_Days["date"] = Set_Days.index.date
    Days_All = [
        Set_Days[Set_Days["date"]==date] for date in picked_dates
    ]
    Picked_Days = pd.concat(Days_All)
    Picked_Days.index = Profiles.index
    print
    Profiles[columns] = Picked_Days[columns]
    
    return Profiles

#---------------------------------
def load_weather_from_tmy(
        Profiles: pd.DataFrame,
        TMY: pd.DataFrame,
        columns: Optional[list[str]] = PROFILES_TYPES['weather'],
    ) -> pd.DataFrame :
    
    rows_profiles = len(Profiles)
    rows_tmy = len(TMY)
    
    if rows_tmy <= rows_profiles:
        N = int(np.ceil(rows_profiles/rows_tmy))
        TMY_extended = pd.concat([TMY]*N, ignore_index=True)
        TMY_final = TMY_extended.iloc[:rows_profiles]
    else:
        TMY_final = TMY.iloc[:rows_profiles]
    TMY_final.index = Profiles.index
    Profiles[columns] = TMY_final[columns]
    return Profiles

#---------------------------------
def load_weather_from_file(
    Profiles: pd.DataFrame,
    file_path: str,
    columns: Optional[list[str]] = PROFILES_TYPES['weather'],
    subset_random: Optional[str] = None,
    subset_value: Union[str, int, pd.Timestamp] = None,
) -> pd.DataFrame :
    """
    It returns the dataframe Profiles with the weather loaded from a file.
    It admits optional parameters subset_random and subset_value to select a subset
    from the source and select randomly days from that subset.
    If subset_random is None, load the file as TMY. If the simulation period is longer
    the file is repeated to match it.

    Parameters
    ----------
    Profiles : pd.DataFrame
        The DataFrame defined by profile_new.
    file_path : str
        Path to the file. It is assumed the file is in the correct format.
    columns : Optional[list[str]], optional
        DESCRIPTION. The default is PROFILES_TYPES['weather'].
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
    Profiles : TYPE
        Returns Profiles with the environmental variables included.

    """
    
    Set_Days = pd.read_csv(file_path, index_col=0)
    Set_Days.index = pd.to_datetime(Set_Days.index)
    if subset_random is None:
        pass
    elif subset_random == 'annual':
        Set_Days = Set_Days[
            Set_Days.index.year==subset_value
            ]
    elif subset_random == 'season':
        Set_Days = Set_Days[
            Set_Days.index.isin(SEASON_DEFINITION[subset_value])
            ]
    elif subset_random == 'month':
        Set_Days = Set_Days[
            Set_Days.index.month==subset_value
            ]  
    elif subset_random == 'date':
        Set_Days = Set_Days[
            Set_Days.index.date==subset_value.date()
            ]  
    
    if subset_random is None:
        Profiles = load_weather_from_tmy(
            Profiles,
            Set_Days,
            columns=columns
        )
    else:
        Profiles = weather_random_days_from_dataframe(
            Profiles,
            Set_Days,
            columns=columns
        )
    return Profiles

#---------------------------------
# Controlled Loads
def add_randomization_delay(
    df_in: pd.DataFrame,
    random_delay_on: int = 0,
    random_delay_off: int = 0,
    STEP: int = 3,
) -> pd.DataFrame:

    """
    This function adds randomization to starting and stopping times in Control Signals
    This function only works if the control signal is integers (1=ON, 0=OFF)
    This function is useful for the TRNSYS Simulations as it is designed to work with the same STEP
    """

    df = df_in.copy()
    df["Switch_no_rand"] = df["CS"].diff()  # Values 1=ON, -1=OFF

    # Defining starting times
    df_starts = df[df["Switch_no_rand"] == 1].copy()
    df_starts["start_no_rand"] = df_starts.index
    df_starts["delays_on"] = np.random.choice(
        np.arange(0, random_delay_on + 1, STEP),
        size=len(df_starts),
    )
    # The last randomization is set to 0 to avoid get outside indexes
    df_starts.iloc[-1, df_starts.columns.get_loc("delays_on")] = 0

    df_starts["start_with_rand"] = df_starts.apply(
        lambda aux: aux["start_no_rand"] 
        + pd.offsets.Minute(aux["delays_on"]),
        axis=1
    )

    # Defining stoping times
    df_stops = df[df["Switch_no_rand"] == -1].copy()
    df_stops["stop_no_rand"] = df_stops.index
    df_stops["delays_off"] = np.random.choice(
        np.arange(0, random_delay_off + 1, STEP),
        size=len(df_stops)
    )
    # The last randomization is set to 0 to avoid get outside indexes
    df_stops.iloc[-1, df_stops.columns.get_loc("delays_off")] = 0

    df_stops["stop_with_rand"] = df_stops.apply(
        lambda aux: aux["stop_no_rand"] 
        + pd.offsets.Minute(aux["delays_off"]),
        axis=1,
    )

    # Applying the randomization into the final
    df["Switch_rand"] = 0
    df.loc[df_starts["start_with_rand"], "Switch_rand"] = 1
    df.loc[df_stops["stop_with_rand"], "Switch_rand"] = -1

    output = (df.iloc[0]["CS"] + df["Switch_rand"].cumsum())
    return output

#---------------------------------

def defining_control_signals(
    df_cs_original: pd.DataFrame,
    Periods: list[Any],
    STEP: int = 3,
    random_ON: bool = False
) -> pd.DataFrame:

    df_cs = df_cs_original.copy()
    df_cs["CS"] = 0  # Without randomization
    df_cs["CS2"] = 0  # With randomization

    month = df_cs.index.month
    hour = df_cs.index.hour + df_cs.index.minute / 60.0

    for Period in Periods:

        df_period = df_cs.copy()

        # There are four cases:
        # 1.   (start_month <= stop_month) & (start_time <= stop_time)
        # 2.   (start_month >  stop_month) & (start_time <= stop_time)
        # 3.   (start_month <= stop_month) & (start_time >  stop_time)
        # 4.   (start_month >  stop_month) & (start_time >  stop_time)

        if (Period["month_start"] <= Period["month_stop"]) and (
            Period["time_start"] <= Period["time_stop"]
        ):
            # print('Condition 1')
            df_period["CS"] = np.where(
                (
                    ((month >= Period["month_start"]) 
                     & (month <= Period["month_stop"])
                     )
                    & ((hour >= Period["time_start"]) 
                       & (hour <= Period["time_stop"])
                       )
                ),
                1,
                0,
            )

        if (Period["month_start"] > Period["month_stop"]) and (
            Period["time_start"] <= Period["time_stop"]
        ):
            # print('Condition 2')
            df_period["CS"] = np.where(
                (
                    ((month >= Period["month_start"]) 
                     | (month <= Period["month_stop"])
                     )
                    & ((hour >= Period["time_start"]) 
                       & (hour <= Period["time_stop"])
                    )
                ),
                1,
                0,
            )

        if (Period["month_start"] <= Period["month_stop"]) and (
            Period["time_start"] > Period["time_stop"]
        ):
            # print('Condition 3')
            df_period["CS"] = np.where(
                (
                    ((month >= Period["month_start"]) & (month <= Period["month_stop"]))
                    & ((hour >= Period["time_start"]) | (hour <= Period["time_stop"]))
                ),
                1,
                0,
            )

        if (Period["month_start"] > Period["month_stop"]) and (
            Period["time_start"] > Period["time_stop"]
        ):
            # print('Condition 4')
            df_period["CS"] = np.where(
                (
                    ((month >= Period["month_start"]) | (month <= Period["month_stop"]))
                    & ((hour >= Period["time_start"]) | (hour <= Period["time_stop"]))
                ),
                1,
                0,
            )

        # Adding the randomization associated with the period
        if random_ON:
            df_period["CS2"] = add_randomization_delay(
                df_period,
                random_delay_on=Period["random_on"],
                random_delay_off=Period["random_off"],
                STEP=STEP,
            )
        else:
            df_period["CS2"] = df_period["CS"]

        # Joining the different periods
        df_cs["CS"] = np.where(((df_cs["CS"] == 1) | (df_period["CS"] == 1)), 1, 0)

        # Joining the different periods
        df_cs["CS2"] = np.where(((df_cs["CS2"] == 1) | (df_period["CS2"] == 1)), 1, 0)

    return [df_cs["CS"], df_cs["CS2"]]

#---------------------------------
def loading_periods_control_load(profile_control):
    if profile_control == -1:
        # No Connection at all (useful for tests)
        Periods = [
            {
                "label": "annual",  # only used as reference
                "month_start": 0,  # inclusive
                "month_stop": 0,  # inclusive
                "time_start": 0,  # inclusive
                "time_stop": 0,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            }
        ]
    
    if profile_control == 0:
        # 24/7 General Supply
        Periods = [
            {
                "label": "annual",  # only used as reference
                "month_start": 1,  # inclusive
                "month_stop": 12,  # inclusive
                "time_start": 0.0,  # inclusive
                "time_stop": 25.0,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            }
        ]
    
    if profile_control == 1:
        # Ausgrid's Controlled Load 1 (Legacy)
        Periods = [
            {
                "label": "winter",  # only used as reference
                "month_start": 4,  # inclusive
                "month_stop": 9,  # inclusive
                "time_start": 22.0,  # inclusive
                "time_stop": 7.0,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 0,  # [mins]
            },
            {
                "label": "summer",  # only used as reference
                "month_start": 10,  # inclusive
                "month_stop": 3,  # inclusive
                "time_start": 21.0,  # inclusive
                "time_stop": 6.0,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 0,  # [mins]
            },
        ]
    
    if profile_control == 2:
        # Ausgrid's Controlled Load 2 (Legacy - Option A)
        Periods = [
            {
                "label": "winter",  # only used as reference
                "month_start": 4,  # inclusive
                "month_stop": 9,  # inclusive
                "time_start": 20.0,  # inclusive
                "time_stop": 17.0,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 0,  # [mins]
            },
            {
                "label": "spring",  # only used as reference
                "month_start": 10,  # inclusive
                "month_stop": 10,  # inclusive
                "time_start": 19.0,  # inclusive
                "time_stop": 16.0,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 0,  # [mins]
            },
            {
                "label": "summer",  # only used as reference
                "month_start": 11,  # inclusive
                "month_stop": 3,  # inclusive
                "time_start": 19.0,  # inclusive
                "time_stop": 14.0,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 0,  # [mins]
            },
        ]
    
    if profile_control == 3:
        # Ausgrid's new Controlled Load 1 (Solar Soak - Option B)
        # Here is called CL3
        Periods = [
            {
                "label": "winter_night",  # only used as reference
                "month_start": 4,  # inclusive
                "month_stop": 9,  # inclusive
                "time_start": 22.0,  # inclusive
                "time_stop": 6.75,  # inclusive
                "random_on": 210,  # [mins]
                "random_off": 15,  # [mins]
            },
            {
                "label": "winter_day",  # only used as reference
                "month_start": 4,  # inclusive
                "month_stop": 9,  # inclusive
                "time_start": 10.0,  # inclusive
                "time_stop": 16.75,  # inclusive
                "random_on": 210,  # [mins]
                "random_off": 15,  # [mins]
            },
            {
                "label": "spring_night",  # only used as reference
                "month_start": 10,  # inclusive
                "month_stop": 10,  # inclusive
                "time_start": 21.0,  # inclusive
                "time_stop": 4.25,  # inclusive
                "random_on": 210,  # [mins]
                "random_off": 15,  # [mins]
            },
            {
                "label": "spring_day",  # only used as reference
                "month_start": 10,  # inclusive
                "month_stop": 10,  # inclusive
                "time_start": 9.0,  # inclusive
                "time_stop": 15.75,  # inclusive
                "random_on": 210,  # [mins]
                "random_off": 15,  # [mins]
            },
            {
                "label": "summer_night",  # only used as reference
                "month_start": 11,  # inclusive
                "month_stop": 3,  # inclusive
                "time_start": 21.0,  # inclusive
                "time_stop": 5.75,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 15,  # [mins]
            },
            {
                "label": "summer_day",  # only used as reference
                "month_start": 11,  # inclusive
                "month_stop": 3,  # inclusive
                "time_start": 9.0,  # inclusive
                "time_stop": 13.50,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 15,  # [mins]
            },
        ]
    
    if profile_control == 4:
        # Solar soak, no randomization, only solar time
        Periods = [
            {
                "label": "year",  # only used as reference
                "month_start": 1,  # inclusive
                "month_stop": 12,  # inclusive
                "time_start": 9.0,  # inclusive
                "time_stop": 15.0,  # inclusive
                "random_on": 0.0,  # [mins]
                "random_off": 0.0,  # [mins]
            }
        ]
    
    if profile_control == 5:
        # Old control load 3 (CL1 + Solar time). No randomization
        Periods = [
            {
                "label": "year_night",  # only used as reference
                "month_start": 1,  # inclusive
                "month_stop": 12,  # inclusive
                "time_start": 22.0,  # inclusive
                "time_stop": 7.0,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            },
            {
                "label": "year_day",  # only used as reference
                "month_start": 1,  # inclusive
                "month_stop": 12,  # inclusive
                "time_start": 9.0,  # inclusive
                "time_stop": 15.0,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            },
        ]
    
    if profile_control == 10:
        # Only 3 hours at beginning of day (for Event's analysis)
        Periods = [
            {
                "label": "annual",  # only used as reference
                "month_start": 1,  # inclusive
                "month_stop": 12,  # inclusive
                "time_start": 0.0,  # inclusive
                "time_stop": 3.0,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            }
        ]
        
    return Periods

#---------------------------------
def load_controlled_load(
    Profiles: pd.DataFrame,
    profile_control: int = 0,
    columns: list[str] = PROFILES_TYPES["control"],
    random_ON: bool = True,
) -> pd.DataFrame:

    
    STEP = Profiles.index.freq.n
    idx = Profiles.index
    df_cs = pd.DataFrame(index=idx, columns=["CS"])
    
    Periods = loading_periods_control_load(profile_control)
    
    # Overwritting randomization to avoid error in function
    if profile_control in [-1,0,10]:
        random_ON = False
    
    (df_cs["CS_norand"], df_cs["CS"]) = defining_control_signals(
        df_cs, Periods, random_ON=random_ON, STEP=STEP
    )
    Profiles[columns] = df_cs[columns]
    return Profiles

#---------------------------------
# Electric Profiles
def load_PV_generation(
        Profiles: pd.DataFrame,
        profile_PV: int = 0,
        PV_NomPow: float = 4000.,
        columns: list[str] = ["PV_Gen"],
        ) -> pd.DataFrame:

    df_PV = pd.DataFrame(index=Profiles.index, columns=columns)
    lbl = columns[0]

    if profile_PV == 0:
        df_PV[lbl] = 0.0
    elif profile_PV == 1:
        df_PV[lbl] = profile_gaussian(df_PV, 12.0, 2.0, PV_NomPow * W2kJh)
    else:
        raise ValueError("profile_PV not valid. The simulation will finish.")
    
    Profiles[columns] = df_PV[columns]
    return Profiles


#---------------------------------
def load_elec_consumption(
    Profiles: pd.DataFrame,
    profile_elec: int = 0,
    columns: list[str] = ["Import_Grid"],
) -> pd.DataFrame:

    df_Elec = pd.DataFrame(index=Profiles.index, columns=columns)
    lbl = columns[0]
    
    if profile_elec == 0:
        df_Elec[lbl] = 0.0  # 0 means no appliance load
    else:
        raise ValueError("profile_Elec not valid. The simulation will finish.")

    Profiles[columns] = df_Elec[columns]
    return Profiles


#---------------------------------
# Emissions
def load_emission_index_year(
        Profiles: pd.DataFrame,
        location: str = "Sydney",
        index_type: str = "total",
        year: int = 2022,
        ) -> pd.DataFrame:
    
    columns = {
        "total": "Intensity_Index",
        "marginal": "Marginal_Emission",
        "both": PROFILES_TYPES["emissions"]
        }[index_type]
    
    emissions = pd.read_csv(
        os.path.join(
            DIR_DATA["emissions"], f"emissions_year_{year}_{index_type}.csv"
            ),
        index_col=0,
    )
    emissions.index = pd.to_datetime(emissions.index)

    Profiles[columns] = emissions[
        emissions["Region"] == LOCATIONS_NEM_REGION[location]
        ][columns].resample(
            f"{Profiles.index.freq.n}T"
        ).interpolate('linear')
    return Profiles

#---------------------------------
# Wholesale prices
def load_wholesale_prices(
        Profiles: pd.DataFrame,
        location: str = "Sydney",
        ) -> pd.DataFrame:
    
    df_SP = pd.read_csv(
        FILE_WHOLESALE_PRICES,
        index_col=0
        )
    df_SP.index = pd.to_datetime(df_SP.index).tz_localize(None)

    Profiles["Wholesale_Market"] = df_SP[
        LOCATIONS_NEM_REGION[location]
        ].resample(
            f"{Profiles.index.freq.n}T"
        ).interpolate('linear')

    return Profiles

#---------------------------------
def main():

    import tm_solarshift.general as general
    
    gs = general.GeneralSetup()
    ts = TimeSeries()

    ts2 = TimeSeries.new_from_gs(gs)

    HWD_daily_dist = HWD_daily_distribution(
        gs, ts2.data
    )
    event_probs = events_file(
            file_name = FILE_SAMPLES["HWD_events"],
            sheet_name = "Custom",
            )
    ts.load_HWDP(
        method='events',
        HWD_daily_dist=HWD_daily_dist,
        HWD_hourly_dist=1,
        event_probs=event_probs
    )

    ts = load_wholesale_prices(ts.data, gs.location)
    ts = load_emission_index_year(ts, gs.location)

    pass

#---------------------------------
if __name__=="__main__":
    main()