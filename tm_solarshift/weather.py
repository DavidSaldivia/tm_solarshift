import os
import sys
import warnings

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, List, Dict, Union

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

FILE_WEATHER_DEFAULT = os.path.join(
    DIR_DATA["weather"], "meteonorm_processed", "meteonorm_{:}.csv",
    )

class Weather():

    @staticmethod
    def load_day_constant_random(
        timeseries: pd.DataFrame,
        ranges: Optional[Dict[str,tuple]] = None,
        columns: Optional[List[str]] = PROFILES_TYPES['weather'],
    ) -> pd.DataFrame:

        if ranges == None:
            ranges = {
                "GHI" : (1000.,1000.),
                "Temp_Amb" : (10.0,40.0),
                "Temp_Mains" : (10.0,30.0),
            }
        
        dates = np.unique(timeseries.index.date)
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

        df_weather = df_weather_days.loc[timeseries.index.date]
        df_weather.index = timeseries.index
        timeseries[columns] = df_weather[columns]
        return timeseries


    #---------------------------------
    @staticmethod
    def random_days_from_dataframe(
        timeseries: pd.DataFrame,
        set_days: pd.DataFrame,
        columns: Optional[List[str]] = PROFILES_TYPES['weather'],
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
            DESCRIPTION. The default is PROFILES_TYPES['weather'].
        : TYPE
            DESCRIPTION.

        Returns
        -------
        timeseries.

        """
        dates = np.unique(set_days.index.date)
        DAYS = len(np.unique(timeseries.index.date))
        picked_dates = np.random.choice(
            dates, size=DAYS
        )
        set_days["date"] = set_days.index.date
        Days_All = [
            set_days[set_days["date"]==date] for date in picked_dates
        ]
        Picked_Days = pd.concat(Days_All)
        Picked_Days.index = timeseries.index
        print
        timeseries[columns] = Picked_Days[columns]
        
        return timeseries

    #---------------------------------
    @staticmethod
    def from_tmy(
            timeseries: pd.DataFrame,
            TMY: pd.DataFrame,
            columns: Optional[List[str]] = PROFILES_TYPES['weather'],
        ) -> pd.DataFrame :
        
        rows_profiles = len(timeseries)
        rows_tmy = len(TMY)
        
        if rows_tmy <= rows_profiles:
            N = int(np.ceil(rows_profiles/rows_tmy))
            TMY_extended = pd.concat([TMY]*N, ignore_index=True)
            TMY_final = TMY_extended.iloc[:rows_profiles]
        else:
            TMY_final = TMY.iloc[:rows_profiles]

        TMY_final.index = timeseries.index
        timeseries[columns] = TMY_final[columns]
        return timeseries

    #---------------------------------
    @classmethod
    def from_file(
        cls,
        timeseries: pd.DataFrame,
        file_path: str = None,
        columns: Optional[List[str]] = PROFILES_TYPES['weather'],
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
            timeseries = cls.from_tmy(
                timeseries, set_days, columns=columns
                )
        else:
            timeseries = cls.random_days_from_dataframe(
                timeseries, set_days, columns=columns
                )
        return timeseries
    
#-------------------
def main():

    #Creating a timeseries
    from tm_solarshift.general_dev import (ThermalSimulation, Household)
    simulation = ThermalSimulation()
    household = Household()
    ts = simulation.create_new_profile()

    #Different ways to create weather columns
    ts = Weather.load_day_constant_random(ts)
    print(ts[PROFILES_TYPES["weather"]])

    file_path = FILE_WEATHER_DEFAULT.format(household.location)
    ts = Weather.from_file(ts,file_path)
    print(ts[PROFILES_TYPES["weather"]])

    ts = Weather.from_file(ts,file_path, subset_random="month", subset_value=1)    
    print(ts[PROFILES_TYPES["weather"]])
    return


if __name__ == "__main__":
    main()