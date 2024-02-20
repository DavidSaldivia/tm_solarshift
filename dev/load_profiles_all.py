import numpy as np
import pandas as pd
import os
from typing import Any

from tm_solarshift.general import GeneralSetup
from tm_solarshift.constants import DIRECTORY
import tm_solarshift.profiles as profiles

DIR_DATA = DIRECTORY.DIR_DATA
PROFILES_TYPES = profiles.PROFILES_TYPES

#-------------------------
def load_timeseries_all_event_simulations(
    general_setup = GeneralSetup(),
    timeseries: pd.DataFrame = None,
    HWD_generator_method: str = 'events',
    HWDP_dist: int = 0,
    weather_type: str = 'day_constant'
    ) -> pd.DataFrame:

    #Getting the required data from GeneralSetup
    location = general_setup.location
    profile_control = general_setup.profile_control
    random_control = general_setup.random_control

    # creating and loading timeseries

    timeseries = profiles.new_profile(general_setup)
    
    #Hot water draw daily distribution
    HWD_daily_dist = profiles.HWD_daily_distribution(
        general_setup, 
        timeseries
    )
    if HWD_generator_method == 'events':
        event_probs = profiles.events_file(
            file_name = os.path.join(
                DIR_DATA["samples"], "HWD_events.xlsx",
                ),
            sheet_name="Custom"
            )
    else:
        event_probs = None
    timeseries = profiles.HWDP_generator(
            timeseries,
            method = HWD_generator_method,
            HWD_daily_dist = HWD_daily_dist,
            HWD_hourly_dist = HWDP_dist,
            event_probs = event_probs,
        )
    
    #Weather
    weather_subsets = {
        'meteonorm_random': ('all', None),
        'meteonorm_season': ('season', 'summer'),
        'meteonorm_month' : ('month', 1),
        'meteonorm_date' : ('date', pd.Timestamp("2022/02/07")),
        'day_constant': (None, None)
    }
    (subset_random, subset_value) = weather_subsets[weather_type]
    
    if weather_type == 'day_constant':
        timeseries = profiles.load_weather_day_constant_random(
            timeseries,
        )
    else:
        file_weather = os.path.join(
            DIR_DATA["weather"],
            "meteonorm_processed",
            f"meteonorm_{location}.csv",
        )
        timeseries = profiles.load_weather_from_file(
            timeseries,
            file_weather,
            columns = PROFILES_TYPES['weather'],
            subset_random = subset_random,
            subset_value = subset_value,
        )
    
    #Electric
    timeseries = profiles.load_PV_generation(timeseries)
    timeseries = profiles.load_elec_consumption(timeseries)
    
    #Control Load
    timeseries = profiles.load_controlled_load(
        timeseries, 
        profile_control = profile_control, 
        random_ON = random_control
    )
    return timeseries


#-----------------------------
def load_timeseries_all_parametric(
        general_setup: GeneralSetup,
) -> pd.DataFrame:
    
    location = general_setup.location
    profile_HWD = general_setup.profile_HWD
    profile_control = general_setup.profile_control
    random_control = general_setup.random_control
    YEAR = general_setup.YEAR

    Profiles = profiles.new_profile(general_setup)
    Profiles = profiles.HWDP_generator_standard(
        Profiles,
        HWD_daily_dist = profiles.HWD_daily_distribution(general_setup, Profiles),
        HWD_hourly_dist = profile_HWD
    )
    file_weather = os.path.join(
        DIR_DATA["weather"], "meteonorm_processed",
        f"meteonorm_{location}.csv",
    )
    Profiles = profiles.load_weather_from_file(
        Profiles, file_weather
    )
    Profiles = profiles.load_controlled_load(
        Profiles, 
        profile_control = profile_control, 
        random_ON = random_control
    )
    Profiles = profiles.load_emission_index_year(
        Profiles, 
        index_type= 'total',
        location = location,
        year=YEAR,
    )
    Profiles = profiles.load_PV_generation(Profiles)
    Profiles = profiles.load_elec_consumption(Profiles)
    return Profiles

#-----------------------------
def load_timeseries_all_dev(
        GS: Any,
) -> pd.DataFrame:
    
    import tm_solarshift.circuits as circuits
    import tm_solarshift.external_data as external_data
    from tm_solarshift.weather import Weather
    
    from tm_solarshift.circuits import (ControlledLoad, Circuits)
    ControlledLoad = circuits.ControlledLoad

    location = GS.household.location
    control_load = GS.household.control_load
    random_control = GS.household.control_random_on
    YEAR = GS.simulation.YEAR.get_value("-")

    ts = GS.simulation.create_new_profile()
    ts = GS.HWDInfo.generator(ts, method="standard")
    
    file_path = Weather.FILE_METEONORM_TEMPLATE.format(location)
    ts = Weather.from_file( ts, file_path )

    ts = external_data.load_emission_index_year(
        ts, 
        index_type= 'both',
        location = location,
        year=YEAR,
    )
    ts = external_data.load_wholesale_prices(ts, location)

    ts = ControlledLoad.load_schedule(ts, profile_control = control_load, random_ON = random_control)
    ts = Circuits.load_PV_generation(ts, GS.solar_system)
    ts = Circuits.load_elec_consumption(ts)

    return ts

#----------------------
def main():
    
    GS = GeneralSetup()
    ts_1 = load_timeseries_all_event_simulations(GS)
    print(ts_1.head())
    #Option 2
    ts_2 = load_timeseries_all_parametric(GS)
    print(ts_2.head())

    #Option 3 (dev)
    from tm_solarshift.general_dev import GeneralSetup as GeneralSetup_new
    GS = GeneralSetup_new()
    ts_3 = load_timeseries_all_dev(GS)
    print(ts_3.head(20))
    return

#------------------------
if __name__ == "__main__":
    main()