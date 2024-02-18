import os
import sys

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, List, Any

from tm_solarshift.constants import (
    DIRECTORY,
    PROFILES,
    DEFINITIONS,
    UNITS
)
DIR_DATA = DIRECTORY.DIR_DATA
PROFILES_TYPES = PROFILES.TYPES
DEFINITION_SEASON = DEFINITIONS.SEASON
CF = UNITS.conversion_factor

class ControlLoad():
    pass

    @staticmethod
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
    @classmethod
    def create_signal_series(
        cls,
        df_cs_original: pd.DataFrame,
        periods: List[Any],
        STEP: int = 3,
        random_ON: bool = True,
    ) -> pd.DataFrame:

        df_cs = df_cs_original.copy()
        df_cs["CS"] = 0  # Without randomization
        df_cs["CS2"] = 0  # With randomization

        month = df_cs.index.month
        hour = df_cs.index.hour + df_cs.index.minute / 60.0

        for period in periods:

            df_period = df_cs.copy()

            # There are four cases:
            # 1.   (start_month <= stop_month) & (start_time <= stop_time)
            # 2.   (start_month >  stop_month) & (start_time <= stop_time)
            # 3.   (start_month <= stop_month) & (start_time >  stop_time)
            # 4.   (start_month >  stop_month) & (start_time >  stop_time)

            if (period["month_start"] <= period["month_stop"]) and (
                period["time_start"] <= period["time_stop"]
            ):
                # print('Condition 1')
                df_period["CS"] = np.where(
                    (
                        ((month >= period["month_start"]) 
                        & (month <= period["month_stop"])
                        )
                        & ((hour >= period["time_start"]) 
                        & (hour <= period["time_stop"])
                        )
                    ),
                    1,
                    0,
                )

            if (period["month_start"] > period["month_stop"]) and (
                period["time_start"] <= period["time_stop"]
            ):
                # print('Condition 2')
                df_period["CS"] = np.where(
                    (
                        ((month >= period["month_start"]) 
                        | (month <= period["month_stop"])
                        )
                        & ((hour >= period["time_start"]) 
                        & (hour <= period["time_stop"])
                        )
                    ),
                    1,
                    0,
                )

            if (period["month_start"] <= period["month_stop"]) and (
                period["time_start"] > period["time_stop"]
            ):
                # print('Condition 3')
                df_period["CS"] = np.where(
                    (
                        ((month >= period["month_start"]) & (month <= period["month_stop"]))
                        & ((hour >= period["time_start"]) | (hour <= period["time_stop"]))
                    ),
                    1,
                    0,
                )

            if (period["month_start"] > period["month_stop"]) and (
                period["time_start"] > period["time_stop"]
            ):
                # print('Condition 4')
                df_period["CS"] = np.where(
                    (
                        ((month >= period["month_start"]) | (month <= period["month_stop"]))
                        & ((hour >= period["time_start"]) | (hour <= period["time_stop"]))
                    ),
                    1,
                    0,
                )

            # Adding the randomization associated with the period
            if random_ON:
                df_period["CS2"] = cls.add_randomization_delay(
                    df_period,
                    random_delay_on=period["random_on"],
                    random_delay_off=period["random_off"],
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
    @staticmethod
    def loading_period_definitions(profile_control):

        if profile_control == -1:
            # No Connection at all (useful for tests)
            periods = [
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
            periods = [
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
            periods = [
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
            periods = [
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
            periods = [
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
            periods = [
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
            periods = [
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
            periods = [
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
            
        return periods

    #---------------------------------
    @classmethod
    def load_schedule(
        cls,
        profiles: pd.DataFrame,
        profile_control: int = 0,
        columns: List[str] = PROFILES_TYPES["control"],
        random_ON: bool = True,
    ) -> pd.DataFrame:

        
        STEP = profiles.index.freq.n
        idx = profiles.index
        df_cs = pd.DataFrame(index=idx, columns=["CS"])
        
        periods = cls.loading_period_definitions(profile_control)
        
        # Overwritting randomization to avoid error in function
        if profile_control in [-1,0,10]:
            random_ON = False
        
        (df_cs["CS_norand"], df_cs["CS"]) = cls.create_signal_series(
            df_cs, periods, random_ON=random_ON, STEP=STEP
        )
        profiles[columns] = df_cs[columns]
        return profiles


#------------------
def main():

    #Creating a timeseries
    from tm_solarshift.general_dev import (ThermalSimulation, Household)
    simulation = ThermalSimulation()
    household = Household()
    ts = simulation.create_new_profile()

    #Different ways to create weather columns
    ts = ControlLoad.load_schedule(ts, profile_control=household.control_load)
    print(ts[PROFILES_TYPES["control"]])

    return


if __name__ == "__main__":
    main()