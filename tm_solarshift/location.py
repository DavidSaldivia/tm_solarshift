import warnings
import pandas as pd
import cartopy
import cartopy.crs as ccrs                   # import projections
import cartopy.feature as cf                 # import features

from typing import List, Dict, Any, Tuple

from tm_solarshift.constants import ( DIRECTORY, DEFINITIONS)
DIR_DATA = DIRECTORY.DIR_DATA
FILE_POSTCODES = DIRECTORY.FILE_POSTCODES

TS_WEATHER = DEFINITIONS.TS_TYPES["weather"]
DEFINITION_SEASON = DEFINITIONS.SEASON
LOCATIONS_METEONORM = DEFINITIONS.LOCATIONS_METEONORM
LOCATIONS_STATE = DEFINITIONS.LOCATIONS_STATE
LOCATIONS_COORDINATES = DEFINITIONS.LOCATIONS_COORDINATES

#------------------
class Location():
    def __init__(self, value: str|int|Tuple[float,float] = "Sydney",):
        self.value = value
        
        if type(value) == str:
            self.input_type = "city"
        elif type(value) == int:
            self.input_type = "postcode"
        elif type(value) == tuple:
            self.input_type = "coords"
        else:
            raise TypeError(f"{type(self.value)} is not a valid type for Location")

    @property
    def coords(self) -> Tuple[float,float]:
        if self.input_type == "city":
            return LOCATIONS_COORDINATES[self.value]
        elif self.input_type == "postcode":
            return from_postcode(self.value, get = "coords")
        elif self.input_type == "coords":
            return self.value
        else:
            raise TypeError(f"{type(self.value)} is not a valid type for Location")

    @property
    def postcode(self) -> int:
        if self.input_type == "city":
            coords = self.coords
            return from_coords(coords, get="postcode")
        elif self.input_type == "postcode":
            return self.value
        elif self.input_type == "coords":
            return from_coords(self.value, get="postcode")
        else:
            raise TypeError(f"{type(self.value)} is not a valid type for Location")
        
    @property
    def state(self) -> str:
        if self.input_type == "city":
            if self.value in LOCATIONS_STATE:
                return LOCATIONS_STATE[self.value]
            else:
                warnings.warn(f"location {self.value} has not a state associated. Check constants.DEFINITIONS.LOCATIONS_STATE. return None")
                return None
        elif self.input_type == "postcode":
            return from_postcode(self.value, get = "state")
        elif self.input_type == "coords":
            return from_coords(self.value, get="state")
        else:
            raise TypeError(f"{type(self.value)} is not a valid type for Location")
        
    @property
    def lon(self) -> float:
        return self.coords[0]
    
    @property
    def lat(self) -> float:
        return self.coords[1]

#---------------
def from_postcode(
    postcode: int = 2035,
    get: str = "state",
) -> str| Tuple[float, float]:
    """It returns the state, coords, lon, or lat from a postcode, using the australian_postcodes.csv set.

    Args:
        postcode (int, optional): _description_. Defaults to 2035.
        get (str, optional): _description_. Defaults to "state".

    Raises:
        ValueError: _description_

    Returns:
        str| Tuple[float, float]: _description_
    """
    
    df_raw = pd.read_csv(FILE_POSTCODES)
    cols = ["id","postcode","locality","state","long","lat","dc","type","status","region"]
    if get == "state":
        df = df_raw.groupby("postcode")["state"].agg(pd.Series.mode)
    elif get =="coords":
        df = df_raw.groupby("postcode")[["long","lat"]].mean()
    elif get =="lon":
        df = df_raw.groupby("postcode")[["long"]].mean()
    elif get =="lat":
        df = df_raw.groupby("postcode")[["lat"]].mean()
    else:
        raise ValueError(f"{get} is not a valid value for get.")

    return df[df.index == postcode].values[0]

def from_coords(
        coords: Tuple[float, float],
        get : str = "postcode",
) -> int|str:
    """It return the postcode or state closest to coords (a distance function is used). It uses australian_postcodes coordinates.

    Args:
        coords (Tuple[float, float]): coordinates: (long, lat)
        get (str, optional): Any column from australian_postcods.csv. Although for now only [postcode,state] are accepted. Defaults to "postcode".

    Returns:
        int|str: the value according to get.
    """
    if get in ["postcode", "state"]:
        (lon, lat) = coords
        df = pd.read_csv(FILE_POSTCODES)
        df["d2"] = (df["long"]-lon)**2 + (df["lat"]-lat)**2
        return df.loc[df["d2"].idxmin()][get]
    else:
        warnings.warn(f"{get} is not a valid value for 'get'. Returning None")
        return None

#------------------
def main():
    
    # location = Location("Sydney")
    location = Location("Sydney")
    print(location.value)
    print(location.coords)
    print(location.state)
    print(location.postcode)
    print()

    # location = Postcode(2035)
    location = Location(2035)
    print(location.value)
    print(location.coords)
    print(location.state)
    print(location.postcode)
    print()

    # location = Coords(value=DEFINITIONS.LOCATIONS_COORDINATES["Sydney"])
    location = Location(DEFINITIONS.LOCATIONS_COORDINATES["Sydney"])
    print(location.value)
    print(location.coords)
    print(location.state)
    print(location.postcode)

    return

if __name__ == "__main__":
    main()
    pass