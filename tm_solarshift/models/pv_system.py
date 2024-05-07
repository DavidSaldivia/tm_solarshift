import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from tm_solarshift.constants import (DIRECTORY, DEFAULT)

DIR_MAIN = DIRECTORY.DIR_MAIN
DEFAULT_TZ = DEFAULT.TZ
DEFAULT_LAT = DEFAULT.LAT
DEFAULT_LON = DEFAULT.LON
DEFAULT_TILT = DEFAULT.TILT
DEFAULT_ORIENT = DEFAULT.ORIENT
DEFAULT_G_STC = DEFAULT.G_STC
DEFAULT_PV_NOMPOW = DEFAULT.PV_NOMPOW
DEFAULT_ADR_PARAMS = DEFAULT.ADR_PARAMS

#most of these columns are from pbliv
COLS_TMY = [
    "temp_air", "GHI", "DNI", "DHI", "WS"
]
COLS_SOLPOS = [
    "apparent_zenith", "zenith",
    "apparent_elevation", "elevation",
    "azimuth", "equation_of_time"
]
COLS_INCIDENCE = [
    "cosine_aoi",
    "aoi"
]
COLS_IRRADIANCE_PLANE = [
    "poa_global", "poa_direct",
    "poa_diffuse", "poa_sky_diffuse",
    "poa_ground_diffuse"
]

#-------------------
def get_PV_generation(
    df: pd.DataFrame,
    tz: str = DEFAULT_TZ,
    latitude: float = DEFAULT_LAT,
    longitude: float = DEFAULT_LON,
    tilt: float = DEFAULT_TILT,
    orient: float = DEFAULT_ORIENT,
    PV_nompower: float = DEFAULT_PV_NOMPOW,
    G_STC: float = DEFAULT_G_STC,
    adr_params: dict = DEFAULT_ADR_PARAMS,
) -> pd.DataFrame:
    
    import pvlib
    from pvlib.pvarray import pvefficiency_adr
    import tm_solarshift.utils.solar as solar

    plane_irrad = solar.get_plane_irradiance(df, latitude, longitude, tilt, orient)
    df["poa_global"] = plane_irrad["poa_global"]
    # Estimate the expected operating temperature of the PV modules
    df["temp_pv"] = pvlib.temperature.faiman(
        df["poa_global"], df["temp_amb"], df["WS"]
    )
    #Relative efficiency and module power
    df["eta_rel"] = pvefficiency_adr(df['poa_global'], df['temp_pv'], **adr_params)
    df["PVPower"] = PV_nompower * df['eta_rel'] * (df['poa_global'] / G_STC)

    return df


#---------------
def sample_plots(
    df: pd.DataFrame,
    DEMO_DAY:str = '2022-02-07',
):
    plt.figure()
    pc = plt.scatter(df['poa_global'], df['eta_rel'], c=df['temp_pv'], cmap='jet')
    plt.colorbar(label='Temperature [C]', ax=plt.gca())
    pc.set_alpha(0.25)
    plt.grid(alpha=0.5)
    plt.ylim(0.48)
    plt.xlabel('Irradiance [W/m²]')
    plt.ylabel('Relative efficiency [-]')
    plt.show()

    plt.figure()

    pc = plt.scatter(df['poa_global'], df['PVPower'], c=df['temp_pv'], cmap='jet')
    plt.colorbar(label='Temperature [C]', ax=plt.gca())
    pc.set_alpha(0.25)
    plt.grid(alpha=0.5)
    plt.xlabel('Irradiance [W/m²]')
    plt.ylabel('Array power [W]')
    plt.show()

    plt.figure()
    plt.plot(df['PVPower'][DEMO_DAY])
    plt.xticks(rotation=30)
    plt.ylabel('Power [W]')
    plt.show()


def main():
    tz = DEFAULT_TZ
    lat = DEFAULT_LAT
    long = DEFAULT_LON

    tilt = DEFAULT_TILT
    orient = DEFAULT_ORIENT
    
    PV_nompower = DEFAULT_PV_NOMPOW
    G_STC = DEFAULT_G_STC
    adr_params = DEFAULT_ADR_PARAMS

    
    df = get_PV_generation(
        tz=tz, latitude=lat, longitude=long, tilt=tilt, orient=orient,
        PV_nompower=PV_nompower, G_STC = G_STC, adr_params=adr_params
    )
    print(df)
    sample_plots(df)
    return


if __name__ == "__main__":
    main()
    pass