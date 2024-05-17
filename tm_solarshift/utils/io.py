import os
import sys
import pickle
import pandas as pd
from typing import Optional, Any

from tm_solarshift.general import   GeneralSetup
from tm_solarshift.models.trnsys import Trnsys_DEWH
from tm_solarshift.constants import (
    DIRECTORY,
    DEFINITIONS,
    SIMULATIONS_IO,
    DEFAULT,
)

DIR_PROJECT = os.path.dirname(__file__)
FORMAT_SIM_INPUT = 'sim_{}_input.plk'

def get_filepath_input(
        identifier: int|pd.Series|dict[str,Any],
        ts: Optional[pd.DataFrame] = None,
) -> str:
    id_sim: str
    if identifier.__class__ == int:
        id_sim = str(identifier)
    elif identifier.__class__ == pd.Series:
        id_sim = identifier["id"]
    elif identifier.__class__ == dict:
        id_sim = identifier["id"]

    file_name = FORMAT_SIM_INPUT.format(id_sim)
    file_path = os.path.join(
        DIR_PROJECT,
        file_name
    )
    return file_path
 

def save_simulation_input(
        GS: GeneralSetup,
        ts: Optional[pd.DataFrame] = None,
        file_path: Optional[str] = None,
) -> None:
    
    id_sim = GS.id
    if file_path is None:
        file_path = FORMAT_SIM_INPUT.format(id_sim)

    try:
        with open(file_path, "wb") as file:
            pickle.dump(GS, file, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as ex:
        print("Error during pickling object (Possibly unsupported):", ex)
    
    return None

def save_simulation_output(
        out_tm: pd.DataFrame,
        ts: Optional[pd.DataFrame] = None,
) -> None:
    
    return None

def load_simulation_input(
        file_path: str,
) -> GeneralSetup:
    try:
        with open(file_path, "rb") as f:
            GS = pickle.load(f)
    except Exception as ex:
        print("Error during unpickling object (Possibly unsupported):", ex)
    return GS

def load_simulation_output(
        file_path: str,
) -> GeneralSetup:
    df_tm = pickle.load(file_path)
    return df_tm


def main():
    pass

if __name__ == "__main__":
    main()
