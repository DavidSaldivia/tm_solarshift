"""
Simulating PV system DC output using the ADR module efficiency model
====================================================================

Time series processing with the ADR model is really easy.

This example reads a TMY3 weather file, and runs a basic simulation
on a fixed latitude-tilt system.
Efficiency is independent of system size, so adjusting the system
capacity is just a matter of setting the desired value, e.g. P_STC = 5000.

Author: Anton Driesse
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Tuple, Dict
import pvlib
from pvlib import iotools, location
from pvlib.irradiance import get_total_irradiance
from pvlib.pvarray import pvefficiency_adr

from tm_solarshift.constants import DIRECTORY
DIR_MAIN = DIRECTORY.DIR_MAIN

#---------------
def load_trnsys_weather(
    YEAR: int = 2022,
    START: int = 0,
    STOP: int = 8760,
    STEP: int = 3,
    tz: str = 'Australia/Brisbane',
):
    STEP_h = STEP / 60.
    PERIODS = int(np.ceil((STOP - START)/STEP_h))

    df = pd.read_table(
    os.path.join(
        DIR_MAIN,
        "dev",
        "trnsys_weather_file", 
        "TRNSYS_Out_Detailed.dat",
    ), 
    sep=r"\s+", 
    index_col=0
    )
    df = df[["T_amb","GHI", "DNI", "DHI", "WS"]]
    df.rename(columns = {"T_amb":"temp_air", "GHI":"ghi", "DNI":"dni", "DHI":"dhi", "WS":"wind_speed"}, inplace=True)
    df = df.iloc[1:]

    # Converting from kJ/hr to W
    # df["HeaterPower"] = df["HeaterPower"]
    # df["HeaterHeat"] = df["HeaterHeat"]
    df["ghi"] = df["ghi"] / 3.6
    df["dni"] = df["dni"] / 3.6
    df["dhi"] = df["dhi"] / 3.6

    start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") \
            + pd.DateOffset(hours=START)
    idx = pd.date_range(
            start=start_time, 
            periods=PERIODS, 
            freq=f"{STEP}min"
        )
    idx = idx.tz_localize(tz)

    df.index = idx

    return df

#---------------
def plots(
    DEMO_DAY = '2022-02-07'
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
    pc = plt.scatter(df['poa_global'], df['p_mp'], c=df['temp_pv'], cmap='jet')
    plt.colorbar(label='Temperature [C]', ax=plt.gca())
    pc.set_alpha(0.25)
    plt.grid(alpha=0.5)
    plt.xlabel('Irradiance [W/m²]')
    plt.ylabel('Array power [W]')
    plt.show()

    plt.figure()
    plt.plot(df['p_mp'][DEMO_DAY])
    plt.xticks(rotation=30)
    plt.ylabel('Power [W]')
    plt.show()

#---------------
def load_PV_generation(
    tz: str = 'Australia/Brisbane',
    latitude: float = -33.86,
    longitude: float = 151.21,
    tilt: float = None,
    orient: float = 180.,
    PV_nompower: float = 5000.,
    G_STC: float = 1000.,
    adr_params: Dict = {},
):
    
    df = load_trnsys_weather(tz=tz)

    if tilt is None:
        tilt = abs(latitude)

    if adr_params == {}:    
        adr_params = {
            'k_a': 0.99924,
            'k_d': -5.49097,
            'tc_d': 0.01918,
            'k_rs': 0.06999,
            'k_rsh': 0.26144,
        }

    loc = location.Location(latitude, longitude, tz)
    solpos =loc.get_solarposition(df.index)
    total_irrad = get_total_irradiance(
        tilt, orient,
        solpos.apparent_zenith, solpos.azimuth,
        df.dni, df.ghi, df.dhi
    )
    df['poa_global'] = total_irrad.poa_global

    # Estimate the expected operating temperature of the PV modules
    df['temp_pv'] = pvlib.temperature.faiman(
        df.poa_global, df.temp_air, df.wind_speed
    )

    #Relative efficiency and module power
    df['eta_rel'] = pvefficiency_adr(df['poa_global'], df['temp_pv'], **adr_params)
    df["PVPower"] = PV_nompower * df['eta_rel'] * (df['poa_global'] / G_STC)

    return df


if __name__ == "__main__":

    # (df, metadata) = retrieve_tmy()

    tz = 'Australia/Brisbane'
    lat: float = -33.86
    long: float = 151.21

    tilt = abs(lat)
    orient = 180.
    
    PV_nompower = 5000.   # (W)
    G_STC = 1000.   # (W/m2)

    
    df = load_PV_generation(
        tz=tz, latitude=lat, longitude=long, tilt=tilt, orient=orient,
        PV_nompower=PV_nompower
    )


    pass