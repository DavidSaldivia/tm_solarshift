import os
import pandas as pd
from typing import Dict, Optional, List, Any

from tm_solarshift.constants import DIRECTORY
from tm_solarshift.general import GeneralSetup
from tm_solarshift.devices import (
    ResistiveSingle,
    HeatPump,
    GasHeaterInstantaneous,
    GasHeaterStorage,
    SolarThermalElecAuxiliary,
)

#Initializing all the heaters:
HEATERS = {
    "solar_thermal": SolarThermalElecAuxiliary(),
    "gas_storage": GasHeaterStorage(),
    "gas_instant": GasHeaterInstantaneous(),
    "resistive": ResistiveSingle(),
    "heat_pump": HeatPump(),
}

HEATERS_COLORS = {
    "resistive": "red",
    "heat_pump": "green",
    "gas_instant": "blue",
    "gas_storage": "navy",
    "solar_thermal": "mustard",
}

def main():

    # Defining default parameters
    GS = GeneralSetup()
    ts = GS.create_ts_default()

    for heater_name in HEATERS.keys():
        
        print(heater_name)
        GS.DEWH = HEATERS[heater_name]
        (out_all, out_overall) = GS.run_thermal_simulation( ts, verbose=True )

        print(out_overall)
        print()

    return


if __name__=="__main__":
    main()
    
