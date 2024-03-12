import os
import pandas as pd

from tm_solarshift.constants import (DIRECTORY,DEFINITIONS)

DIR_SPOTPRICE = DIRECTORY.DIR_DATA["energy_market"]
DIR_EMISSIONS = DIRECTORY.DIR_DATA["emissions"]

FILES = {
    "WHOLESALE_PRICES": os.path.join(DIR_SPOTPRICE, 'SP_2017-2023.csv'),
    "EMISSIONS_TEMPLATE": os.path.join( DIR_EMISSIONS, "emissions_year_{:}_{:}.csv"),
}

#---------------------------------
# Emissions
def load_emission_index_year(
        timeseries: pd.DataFrame,
        location: str = "Sydney",
        index_type: str = "total",
        year: int = 2022,
        ) -> pd.DataFrame:
    
    columns = {
        "total": "Intensity_Index",
        "marginal": "Marginal_Index",
        # "both": PROFILES.TYPES["emissions"]   #Not working well yet
        }[index_type]
    
    emissions = pd.read_csv(
        FILES["EMISSIONS_TEMPLATE"].format(year, index_type), index_col=0,
    )
    emissions.index = pd.to_datetime(emissions.index)

    timeseries[columns] = emissions[
        emissions["Region"] == DEFINITIONS.LOCATIONS_NEM_REGION[location]
        ][columns].resample(
            f"{timeseries.index.freq.n}T"
        ).interpolate('linear')
    return timeseries

#---------------------------------
# Wholesale prices
def load_wholesale_prices(
        timeseries: pd.DataFrame,
        location: str|tuple|int = "Sydney",
        ) -> pd.DataFrame:
    
    df_SP = pd.read_csv( FILES["WHOLESALE_PRICES"], index_col=0 )
    df_SP.index = pd.to_datetime(df_SP.index).tz_localize(None)

    if type(location) == str:   #city
        nem_region = DEFINITIONS.LOCATIONS_NEM_REGION[location]
    elif type(location) == tuple:     #coordinate
        pass #Check which state the location is
    elif type(location) == int:     #postcode
        pass #Check the NEM region of postcode


    timeseries["Wholesale_Market"] = df_SP[
        nem_region
        ].resample(
            f"{timeseries.index.freq.n}T"
        ).interpolate('linear')

    return timeseries

def main():

    from tm_solarshift.general import GeneralSetup
    GS = GeneralSetup()
    ts = GS.simulation.create_new_profile()
    
    location = GS.household.location
    ts = load_emission_index_year( ts, location, index_type='total', year=2022 )
    ts = load_emission_index_year( ts, location, index_type='marginal', year=2022 )

    ts = load_wholesale_prices(ts, location)

    print(ts.head(20))
    pass

if __name__ == "__main__":
    main()