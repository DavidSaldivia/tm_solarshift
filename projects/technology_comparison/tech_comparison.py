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
    SolarThermalGasAuxiliary
    )

#Initializing all the heaters:
HEATERS = {
    "resistive": ResistiveSingle(),
    "heat_pump": HeatPump(),
    "gas_instant": GasHeaterInstantaneous(),
    "gas_storage": GasHeaterStorage(),
    "solar_thermal": SolarThermalGasAuxiliary(),        
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
        
        GS.DEWH = HEATERS[heater_name]
        output = GS.run_thermal_simulation( ts, verbose=True )
        
        import tm_solarshift.thermal_models.postprocessing as postprocessing
        overall = postprocessing.annual_simulation(GS, ts, output)

        print(heater_name)
        print(output)
        print(overall)
        print()

        if heater_name == "gas_instant":
            break

    return


if __name__=="__main__":
    main()
    
