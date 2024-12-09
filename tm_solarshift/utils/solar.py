import pandas as pd
import pvlib.location as location
import pvlib.irradiance as irradiance

from tm_solarshift.constants import (DIRECTORY, DEFAULT)

DIR_MAIN = DIRECTORY.DIR_MAIN
DEFAULT_TZ = DEFAULT.TZ
DEFAULT_LAT = DEFAULT.LAT
DEFAULT_LON = DEFAULT.LON
DEFAULT_TILT = DEFAULT.TILT
DEFAULT_ORIENT = DEFAULT.ORIENT

#most of these columns are from pbliv
COLS_TMY = ["temp_aMB", "GHI", "DNI", "DHI", "WS"]
COLS_SOLPOS = ["apparent_zenith", "zenith",
               "apparent_elevation", "elevation",
               "azimuth", "equation_of_time"]
COLS_INCIDENCE = ["cosine_aoi", "aoi"]
COLS_IRRADIANCE_PLANE = ["poa_global", "poa_direct",
                         "poa_diffuse", "poa_sky_diffuse",
                         "poa_ground_diffuse"]

#---------------
# functions using only geometry

#---------------
def get_solar_position(
        idx: pd.DatetimeIndex,
        latitude: float,
        longitude: float,
        tz: str = DEFAULT_TZ,
) -> pd.DataFrame:
    """Function to get the solar position.

    It is a pvlib's get_solarposition method.

    Args:
        idx (pd.DatetimeIndex): Timeseries index to retrieve the solar position.
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        tz (str, optional): Timezone. Defaults to DEFAULT_TZ.

    Returns:
        pd.DataFrame: _description_
    """
    
    # idx_2 = idx.tz_localize(tz)
    loc = location.Location(latitude, longitude, tz)
    solpos = loc.get_solarposition(idx)
    return solpos

#---------------
def get_plane_angles(
        data: pd.DatetimeIndex|pd.DataFrame,
        latitude: float,
        longitude: float,
        tilt: float,
        orient: float,
        tz: str = DEFAULT_TZ,
) -> pd.DataFrame:
    """Get plane angles.

    Args:
        data (pd.DatetimeIndex | pd.DataFrame): A dataframe with the solar position or a timeseries index. In any case, the solar angles are calculated and then the angle of incidence and it's cosine are calculated.
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        tilt (float): Inclination angle.
        orient (float): Orientation. It is the surface azimuth.
        tz (str, optional): Timezone. Defaults to DEFAULT_TZ.

    Returns:
        pd.DataFrame: Dataframe with the angles.
    """
    
    if data.__class__ == pd.DatetimeIndex:
        solpos = get_solar_position(data, latitude, longitude, tz)
    elif data.__class__ == pd.DataFrame:
        solpos = get_solar_position(data.index, latitude, longitude, tz)

    angles = solpos.copy()
    angles["aoi"] = irradiance.aoi(tilt, orient, solpos["apparent_zenith"], solpos["azimuth"])
    angles["cosine_aoi"] = irradiance.aoi_projection(tilt, orient, solpos["apparent_zenith"], solpos["azimuth"])
    return angles

#---------------
# functions using solar_resource
def get_plane_irradiance(
        ts: pd.DataFrame,
        latitude: float,
        longitude: float,
        tilt: float,
        orient: float,
        tz: str = DEFAULT_TZ,
) -> pd.DataFrame:
    """Get the plane irradiance for a given timeseries.

    Args:
        ts (pd.DataFrame): The timeseries with the index to use.
        latitude (float): Latitud of the location
        longitude (float): Longitude of the location
        tilt (float): Inclination angle.
        orient (float): Orientation angle. It is the surface azimuth.
        tz (str, optional): Timezone. Defaults to DEFAULT_TZ.

    Returns:
        pd.DataFrame: A dataframe with the plane irradiance and other quantities.
    """

    solpos = get_solar_position(ts.index, latitude, longitude, tz)
    plane_irrad = irradiance.get_total_irradiance(
        tilt, orient,
        solpos["apparent_zenith"], solpos["azimuth"],
        ts["DNI"], ts["GHI"], ts["DHI"]
    )
    return plane_irrad

#---------------
def test_functions(
    ts: pd.DataFrame,
    latitude: float = DEFAULT_LAT,
    longitude: float = DEFAULT_LON,
    tilt: float = DEFAULT_TILT,
    orient: float = DEFAULT_ORIENT,
    tz: str = DEFAULT_TZ,
) -> pd.DataFrame:
    
    idx = ts.index
    
    solpos = get_solar_position(idx, latitude, longitude, tz)
    plane_angles = get_plane_angles(solpos, latitude, longitude, tilt, orient, tz)

    plane_irrad = get_plane_irradiance(ts, latitude, longitude, tilt, orient, tz)

    df = ts.copy()
    df[COLS_SOLPOS] = solpos[COLS_SOLPOS]
    df[COLS_INCIDENCE] = plane_angles[COLS_INCIDENCE]
    df[COLS_IRRADIANCE_PLANE] = plane_irrad[COLS_IRRADIANCE_PLANE]

    return df


if __name__ == "__main__":

    tz = DEFAULT_TZ
    lat = DEFAULT_LAT
    long = DEFAULT_LON
    tilt = DEFAULT_TILT
    orient = DEFAULT_ORIENT

    from tm_solarshift.general import Simulation
    sim = Simulation()
    ts = sim.create_ts()
    
    df = test_functions( ts=ts, latitude=lat, longitude=long, tilt=tilt, orient=orient, tz=tz,)
    print(df)

    pass