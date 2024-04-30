import pandas as pd
import numpy as np

from tm_solarshift.constants import (DIRECTORY, DEFINITIONS, SIMULATIONS_IO)
from tm_solarshift.devices import SolarSystem
DIR_DATA = DIRECTORY.DIR_DATA
DEFINITION_SEASON = DEFINITIONS.SEASON
TS_TYPES = SIMULATIONS_IO.TS_TYPES


# Basic functions for profiles
def profile_gaussian(df: pd.DataFrame, mu1: float, sig1: float, A1:float, base:float=0) -> pd.DataFrame:
    aux = df.index.hour + df.index.minute / 60.0
    Amp = A1 * sig1 * (2 * np.pi) ** 0.5
    series = base + (Amp / sig1 / (2 * np.pi) ** 0.5) * np.exp(
        -0.5 * (aux - mu1) ** 2 / sig1**2
    )
    return series

def profile_step(df:pd.DataFrame, t1:float, t2:float, A1:float, A0:float=0)-> pd.DataFrame:
    aux = df.index.hour + df.index.minute / 60.0
    series = np.where((aux >= t1) & (aux < t2), A1, A0)
    return series

#---------------
def load_PV_generation(
        timeseries: pd.DataFrame,
        solar_system: SolarSystem,
        columns: list[str] = ["PV_Gen"],
        ) -> pd.DataFrame:
    """Function to create/load simple gaussian profile for PV generation.

    Args:
        timeseries (pd.DataFrame): timeseries dataframe
        solar_system (SolarSystem): devices.SolarSystem object
        columns (list[str], optional): Columns to be replaced in ts. Defaults to ["PV_Gen"].

    Raises:
        ValueError: type of PV profile is not valid

    Returns:
        pd.DataFrame: updated timeseries dataframe
    """
    
    df_PV = pd.DataFrame(index=timeseries.index, columns=columns)
    lbl = columns[0]
    
    if solar_system is None:
        df_PV[lbl] = 0.0
    else:
        profile_PV = solar_system.profile_PV
        nom_power = solar_system.nom_power.get_value("kJ/hr")
        
        if profile_PV == 0:
            df_PV[lbl] = 0.0
        elif profile_PV == 1:
            df_PV[lbl] = profile_gaussian( df_PV, 12.0, 2.0, nom_power )
        else:
            raise ValueError("profile_PV not valid. The simulation will finish.")
    
    timeseries[columns] = df_PV[columns]
    return timeseries

#---------------
def load_elec_consumption(
    timeseries: pd.DataFrame,
    profile_elec: int = 0,
    columns: list[str] = ["Import_Grid"],
) -> pd.DataFrame:

    df_Elec = pd.DataFrame(index=timeseries.index, columns=columns)
    lbl = columns[0]
    
    if profile_elec == 0:
        df_Elec[lbl] = 0.0  # 0 means no appliance load
    else:
        raise ValueError("profile_Elec not valid. The simulation will finish.")

    timeseries[columns] = df_Elec[columns]
    return timeseries

#------------------
def main():

    #Creating a timeseries dataframe
    
    from tm_solarshift.general import GeneralSetup
    GS = GeneralSetup()
    ts = GS.create_ts()
    solar_system = GS.solar_system
    
    COLS = TS_TYPES["electric"]

    ts = load_PV_generation(ts, solar_system = solar_system)
    print(ts[COLS])
    ts = load_elec_consumption(ts, profile_elec = 0)
    print(ts[COLS])

    return


if __name__ == "__main__":
    main()