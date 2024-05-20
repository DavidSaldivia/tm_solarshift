import pandas as pd
import numpy as np

from tm_solarshift.constants import (DIRECTORY, DEFINITIONS, SIMULATIONS_IO)
from tm_solarshift.models.pv_system import PVSystem
DIR_DATA = DIRECTORY.DIR_DATA
DEFINITION_SEASON = DEFINITIONS.SEASON
TS_TYPES = SIMULATIONS_IO.TS_TYPES


# Basic functions for profiles
def profile_gaussian(
        idx: pd.DatetimeIndex,
        mu1: float, sig1: float,
        A1:float, base:float=0
    ) -> pd.Series:
    aux = (idx.hour + idx.minute / 60.0).values
    Amp = A1 * sig1 * (2 * np.pi) ** 0.5
    series = base + (Amp / sig1 / (2 * np.pi) ** 0.5) * np.exp(
        -0.5 * (aux - mu1) ** 2 / sig1**2
    )
    
    return pd.Series(series, index=idx)

def profile_step(
        idx: pd.DatetimeIndex,
        t1: float,
        t2: float,
        A1: float,
        A0: float = 0
    )-> pd.Series:
    aux = (idx.hour + idx.minute / 60.0).values
    series = np.where((aux >= t1) & (aux < t2), A1, A0)
    return pd.Series(series, index=idx)

#---------------
def load_PV_generation(
        timeseries: pd.DataFrame,
        pv_system: PVSystem,
        columns: list[str] = ["PV_gen"],
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
    
    if pv_system is None:
        df_PV[lbl] = 0.0
    else:
        profile_PV = pv_system.profile_PV
        nom_power = pv_system.nom_power.get_value("kJ/hr")
        
        if profile_PV == 0:
            df_PV[lbl] = 0.0
        elif profile_PV == 1:
            idx = pd.DatetimeIndex(df_PV.index)
            df_PV[lbl] = profile_gaussian( idx, 12.0, 2.0, nom_power )
        else:
            raise ValueError("profile_PV not valid. The simulation will finish.")
    
    timeseries[columns] = df_PV[columns]
    return timeseries

#---------------
def load_elec_consumption(
    timeseries: pd.DataFrame,
    profile_elec: int = 0,
    columns: list[str] = ["import_grid"],
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

    profile = profile_step(ts.index, t1=10., t2=14., A1=2.0)
    print(profile)

    pv_system = GS.pv_system
    
    COLS = TS_TYPES["electric"]

    ts = load_PV_generation(ts, pv_system = pv_system)
    print(ts[COLS])
    ts = load_elec_consumption(ts, profile_elec = 0)
    print(ts[COLS])

    return


if __name__ == "__main__":
    main()