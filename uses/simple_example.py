import os
import numpy as np
import pandas as pd

import tm_solarshift.general as general
from tm_solarshift.devices import ResistiveSingle
import tm_solarshift.profiles as profiles
import tm_solarshift.trnsys as trnsys


#-----------------------------
def load_profiles_all(
        general_setup: general.GeneralSetup,
) -> pd.DataFrame:
    """ This function is an example of how to load different profiles.
    It is used in the main code below.

    """
    #Parameters from general_setup:
    location = general_setup.location
    profile_HWD = general_setup.profile_HWD
    profile_control = general_setup.profile_control
    random_control = general_setup.random_control
    YEAR = general_setup.YEAR

    Profiles = profiles.new_profile(general_setup)

    #The HWDP is generated:
    Profiles = profiles.HWDP_generator_standard(
        Profiles,
        HWD_daily_dist = profiles.HWD_daily_distribution(general_setup, Profiles),
        HWD_hourly_dist = profile_HWD
    )

    #Weather
    #There are several options for the weather file. Here the TRNSYS files are used:
    file_weather = os.path.join(
        general.DATA_DIR["weather"], "meteonorm_processed",
        f"meteonorm_{location}.csv",
    )
    Profiles = profiles.load_weather_from_file(
        Profiles, file_weather
    )

    #Controlled load. See tm_solarshift.profiles for details
    Profiles = profiles.load_controlled_load(
        Profiles, 
        profile_control = profile_control, 
        random_ON = random_control
    )

    #Emissions (if needed). It uses data from nemed, which is already processed
    Profiles = profiles.load_emission_index_year(
        Profiles, 
        index_type= 'total',
        location = location,
        year=YEAR,
    )

    #PV generation and Electricity consumption.
    # They are required by TRNSYS, but they are not used, so dummy series are provided here.
    Profiles = profiles.load_PV_generation(Profiles)
    Profiles = profiles.load_elec_consumption(Profiles)

    return Profiles

#-------------------

def main():

    #Create a general setup object
    general_setup = general.GeneralSetup()

    #By default, DEWH=ResistiveSingle(). It can also be defined directly
    general_setup.DEWH = ResistiveSingle()

    #The Profiles is a dataframe, that can be initialised from general_setup
    # The different profiles are loaded using general_setup information and other options
    # Each profile (HWD, weather, CL, emissions, PV generation, Electricity) has its own function
    # and some options.
    # An example of this is grouped in one function load_profiles_all (see above).
    Profiles = load_profiles_all( general_setup )

    #Now it is possible to run the simulation
    out_data = trnsys.run_trnsys_simulation(general_setup, Profiles)
    
    #The postprocessing can be done with:
    out_overall = trnsys.postprocessing_annual_simulation(
            general_setup, Profiles, out_data
        )

    print(out_overall)

    return

if __name__ == "__main__":
    main()