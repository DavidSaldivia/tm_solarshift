import os
import sys
import warnings

import pandas as pd
import numpy as np
from typing import List, Any
from scipy.interpolate import interp1d
from scipy.stats import truncnorm

from tm_solarshift.constants import ( DIRECTORY, DEFINITIONS )
from tm_solarshift.units import ( Variable, conversion_factor as CF 
                                 )
DIR_DATA = DIRECTORY.DIR_DATA
TS_HWD = DEFINITIONS.TS_TYPES["HWDP"]
FILES_HWD_SAMPLES = DIRECTORY.FILES_HWD_SAMPLES
FILE_HWDP_AUSTRALIA = os.path.join( 
        DIR_DATA["HWDP"], "HWDP_Generic_AU_{:0d}.csv",  #expected int
    )
DAILY_DISTRIBUTIONS = [
    "norm", "unif", "truncnorm", "sample", None
]

#------------------------------------
class HWD():
    def __init__(self):
        self.profile_HWD = 1
        self.daily_avg = None
        self.daily_std = None
        self.daily_min = None
        self.daily_max = None
        self.random_seed = None
        self.daily_distribution = None

    #-------------------------
    #Alternative initialiser
    @classmethod
    def standard_case(cls):

        standard_case = cls()
        standard_case.profile_HWD = 1
        (daily_avg, unit_avg) = (200., "L/d")
        standard_case.daily_avg = Variable(daily_avg, unit_avg)
        standard_case.daily_std = Variable(daily_avg / 3.0, unit_avg)
        standard_case.daily_min = Variable(0.0, unit_avg)
        standard_case.daily_max = Variable(2*daily_avg , unit_avg)
        standard_case.random_seed = np.random.SeedSequence().entropy
        standard_case.daily_distribution = "truncnorm"       #Options: (None, "unif", "truncnorm", "sample")
        
        return standard_case
    
    #----------------------
    @staticmethod
    def event_basic():
        event_basic = {
            "name": "custom",  # Event type label
            "basis": "daily",  # To determine number of events
            "N_ev_min": Variable( 1, "-" ),  # minimum N_events in the specific basis
            "N_ev_max": Variable( 4, "-" ),  # maximum N_events in the specific basis
            "t_ini": Variable( 3, "hr" ),  # decimal time for event to start
            "t_fin": Variable( 23, "hr" ),  # decimal time for event finish
            "dt_min": Variable( 3, "min" ),  # minimum duration for event
            "dt_max": Variable( 60, "min" ),  # maximum duration for event
            "factor_a": Variable( 50, "kg" ),  # minimum bound for water consumption
            "factor_b": Variable( 200, "kg" ),  # maximum bound for water consumption
            "DensFunc": "uniform", # type of distribution of water consumption and time
            "profile_HWD": None, # density function of occurrance during the day
        }
        return event_basic
    
    @staticmethod
    def event_file(file_name:str=None, sheet_name="Basic"):
        if file_name is None:
            file_name = FILES_HWD_SAMPLES["HWD_events"]
            warnings.warn("No file path for events is given. Sample file is used.")

        events = pd.read_excel(
            file_name,
            sheet_name=sheet_name,
        )
        return events
    
    #----------------------
    def interday_distribution(
        self,
        list_dates: List|pd.DataFrame|pd.DatetimeIndex,
        sample_file: str = None,
    ) -> pd.DataFrame:
        """
        To create HWDP we need two distribution: an hourly (or instantaneous) distribution (intra-days) and
        an daily distribution (inter-days).
        This function returns a daily distribution of HWD based on a method defined in
        self.daily_distribution
        """

        daily_avg = self.daily_avg.get_value("L/d") 
        daily_std = self.daily_std.get_value("L/d")
        daily_min = self.daily_min.get_value("L/d") 
        daily_max = self.daily_max.get_value("L/d")
        daily_distribution = self.daily_distribution

        rng = np.random.default_rng(self.random_seed)
        truncnorm.random_state = rng

        if daily_distribution not in DAILY_DISTRIBUTIONS:
            raise ValueError(f"daily distribution function not among available options: {DAILY_DISTRIBUTIONS}")

        if type(list_dates) == pd.DatetimeIndex:
            list_dates_unique = np.unique(list_dates.date)
        elif type(list_dates) == pd.DataFrame:
            list_dates_unique = np.unique(list_dates.index.date)
        else:
            list_dates_unique = np.unique(list_dates)
        list_dates_unique = pd.to_datetime(list_dates_unique)
        DAYS = len(list_dates_unique)

        # Including the daily variability, if required
        if daily_distribution == None or not (daily_std > 0.0):
            m_HWD_day = daily_avg * np.ones(DAYS)

        elif daily_distribution == "norm":
            m_HWD_day = rng.normal(
                loc = daily_avg,
                scale = daily_std,
                size = int(np.ceil(DAYS),
                )
            )
            m_HWD_day = np.where(m_HWD_day > daily_min, m_HWD_day, daily_min)

        elif daily_distribution == "unif":
            m_HWD_day = (daily_max - daily_min) * rng.rand(DAYS) + daily_min

        elif daily_distribution == "truncnorm":
            myclip_a = daily_min
            myclip_b = daily_max
            loc = daily_avg
            scale = daily_std
            # This step is counterintuitive (See scipy's documentation for truncnorm)
            a, b = (myclip_a - loc) / scale, (myclip_b - loc) / scale
            m_HWD_day = truncnorm.rvs(
                a, b, loc=loc, scale=scale, size=DAYS
                )
        
        elif daily_distribution == "sample":
            if sample_file is None:
                sample_file = FILES_HWD_SAMPLES["HWD_daily"]
            sample = pd.read_csv(sample_file)['m_HWD_day']
            sample = sample[sample>0].to_list()
            m_HWD_day = rng.choice(sample, size=DAYS)
            
    
        return pd.DataFrame(m_HWD_day, 
                            index=list_dates_unique, 
                            columns=["HWD_day"],)


    #----------------------
    def generator(
        self,
        timeseries: pd.DataFrame,
        method: str = 'standard',
        interday_dist: pd.DataFrame = None,
        intraday_dist: int = None, 
        event_probs: pd.DataFrame = None,
        columns: List[str] = TS_HWD,
    ) -> pd.DataFrame:

        if (method == 'standard'):
            timeseries = self.generator_standard(timeseries, 
                                                 interday_dist, 
                                                 intraday_dist, 
                                                 columns,)
        elif (method == 'events'):
            timeseries = self.generator_events(timeseries,
                                               interday_dist, 
                                               intraday_dist,
                                               event_probs,
                                               columns,)
        else:
            print(f"{method} is not a valid method for HWDP generator")
        
        return timeseries

    #----------------------
    def generator_standard(
        self,
        timeseries: pd.DataFrame,
        interday_dist: pd.DataFrame = None,
        intraday_dist: int = None,
        columns: List[str] = TS_HWD,
    ) -> pd.DataFrame:
        """
        This function generates a HWDP using the six standard profiles defined in this project.
        Each day has the same 'shape' of water consumption on each day.
        The flow magnitude could be changed only by the daily water consumption,
        which is defined by cls().daily_distribution

        """

        #Checks and conversions
        if interday_dist is None:
            interday_dist = self.interday_distribution(timeseries)
        if intraday_dist is None:
            intraday_dist = self.profile_HWD

        STEP_h = timeseries.index.freq.n * CF("min","hr")   # delta t in hours
        PERIODS = len(timeseries)                 # Number of periods to simulate

        # Creating an auxiliar dataframe to populate the drawings
        df_aux = pd.DataFrame(index=timeseries.index, columns=columns)

        match intraday_dist:
            case 0:
                df_aux["P_HWD"] = np.zeros(PERIODS)
                df_aux["m_HWD"] = np.zeros(PERIODS)
            case i if 1 <= i <= 6:
                HWDP_day = pd.read_csv(FILE_HWDP_AUSTRALIA.format(intraday_dist))

                f1D = interp1d(
                    HWDP_day["time"], HWDP_day["HWDP"],
                    kind="linear", fill_value="extrapolate"
                )
                df_aux["P_HWD"] = f1D(
                    df_aux.index.hour
                    + df_aux.index.minute * CF("min","hr")
                    + df_aux.index.second * CF("s","hr")
                    )
            case _ :
                raise ValueError("intraday_distribution is not among the accepted values.")

        # This is to ensure that each day the accumulated hot water profile fraction is 1.
        P_HWD_day = (
            df_aux.groupby(df_aux.index.date)["P_HWD"]
            .transform("sum") 
            * STEP_h
        )
        df_aux["P_HWD"] = np.where(P_HWD_day > 0, 
                                df_aux["P_HWD"] / P_HWD_day, 
                                0.0)
        df_aux["m_HWD_day"] = interday_dist.loc[
            timeseries.index.date
            ]["HWD_day"].values
        df_aux["m_HWD"] = df_aux["P_HWD"] * df_aux["m_HWD_day"]
        
        timeseries[columns] = df_aux[columns]
        return timeseries


    #-------------------
    def generator_events(
        self,
        timeseries: pd.DataFrame,
        interday_dist: pd.DataFrame = None,
        intraday_dist: int = None,
        event_probs: pd.DataFrame = None,
        columns: List[str] = TS_HWD,
    ) -> pd.DataFrame:
        """
        This function generates HWD profiles different for each day, based on daily
        consumption variability (defined by HWD_daily), and event characteristics
        """
        rng = np.random.default_rng(self.random_seed)

        #Checks and some conversions
        if interday_dist is None:
            interday_dist = self.interday_distribution(timeseries)
        if intraday_dist is None:
            intraday_dist = self.profile_HWD
        if event_probs is None:
            event_probs = self.event_file()

        STEP = timeseries.index.freq.n
        STEP_h = STEP * CF("min","hr")
        list_dates = np.unique(timeseries.index.date)
        DAYS = len(list_dates)
        
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

            df_day["N_ev"] = rng.integers(N_ev_min, N_ev_max + 1, size=DAYS)
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
            if intraday_dist == None:
                probs = np.ones(len(list_hours))
            else:
                HWDP_day = pd.read_csv( FILE_HWDP_AUSTRALIA.format(intraday_dist) )
                probs = HWDP_day.loc[list_hours, "HWDP"].values
            probs = probs / probs.sum()

            # Defining the starting and finishing times
            Events["hour"] = rng.choice(
                np.arange(t_ini, t_fin + 1),
                size=N_events_total,
                p=probs
            )
            Events["minute"] = rng.choice(
                np.arange(0, 60, STEP),
                size=N_events_total
            )
            Events["duration"] = rng.choice(
                np.arange(dt_min, dt_max, STEP),
                size=N_events_total
            )
            Events["datetime"] = pd.to_datetime(
                Events[["year", "month", "day", "hour", "minute"]]
            )
            Events["flow"] = rng.uniform(
                factor_a, factor_b, size=N_events_total
            )

            # Obtaining the final time of events
            Events["datetime_o"] = Events["datetime"] + Events["duration"].astype(
                "timedelta64[m]"
            )
            # Deleting events that are outside simulation
            Events = Events.drop(
                Events[Events.datetime_o > timeseries.index.max()].index
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
                interday_dist.loc[Events.index.date]["HWD_day"]
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
            interday_dist.loc[Events_all.index.date]["HWD_day"]
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

        # Generating the final df
        df_aux = pd.DataFrame(index=timeseries.index, columns=columns)
        df_aux["Events"] = 0.0
        df_aux.loc[Events_final.index, "Events"] = Events_final["flow"]
        df_aux["m_HWD"] = df_aux.Events.cumsum()
        df_aux["m_HWD"] = np.where(df_aux["m_HWD"] < 1e-5, 0, df_aux["m_HWD"])
        df_aux["m_HWD_day"] = (
            df_aux.groupby(df_aux.index.date)["m_HWD"].transform("sum") 
            * STEP_h
        )
        timeseries[columns] = df_aux[columns]
        return timeseries

#----------------------------
def main():
    
    from tm_solarshift.general import ThermalSimulation
    simulation = ThermalSimulation()
    
    HWDInfo = HWD.standard_case()
    HWDInfo.daily_distribution = "truncnorm"
    
    #Testing different inputs for dates
    ts = simulation.create_new_profile()
    dates = np.unique(ts.index.date)
    print(HWDInfo.interday_distribution(ts))          #pd.DataFrame with DateTimeIndex
    print(HWDInfo.interday_distribution(dates))       #list of dates
    print(HWDInfo.interday_distribution(ts.index))    #DateTimeIndex

    #There are two types of generators
    print(HWDInfo.generator_standard(ts)[TS_HWD])
    print(HWDInfo.generator_events(ts)[TS_HWD])

    #Same generators, but using the wrapper HWD.generator()
    print(HWDInfo.generator(ts, method="standard")[TS_HWD])
    print(HWDInfo.generator(ts, method="events")[TS_HWD])

    return

if __name__ == "__main__":
    main()