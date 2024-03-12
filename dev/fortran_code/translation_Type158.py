"""
Translation of Type158.f90 (Cylindrical Storage Tank) available in TRNSYS's Types catalog.
This is an own manual translation of the code.
From the FORTRAN's file only the numerical method was translated.
The other sections (see below) are build from scratch to meet the original project requirements.

The goal of the translation is to have a full-python module to simulate a hot water tank for domestic use.
This was developed as part of tm_solarshift repository.

The module is divided in four sections:
    - Preparation and error checking (built from scratch)
    - Precalculations (adapted from Type158.f90 to own requirements)
    - Iterative Loop (translated from Type158.f90)
    - Final calculations and correct temperature inversion (adapted from Type158.f90 to own requirements)

"""

import numpy as np
import pandas as pd
from typing import List, Any, Dict
import tm_solarshift.devices as devices
from tm_solarshift.general import (
    GeneralSetup,
    load_timeseries_all
    )


class HotWaterTank():

    def __init__(self, DEWH):

        self.vol = self.DEWH
        ...

    


def preparation_error_checking(
        heater: HotWaterTank,
) -> None:
    
    pass
    return None

#-----------------------
def precalculations(
        heater: HotWaterTank,
) -> None:
    
    pass
    return None


#-----------------------
def iterative_loop(
        heater: HotWaterTank,
) -> None:
    
    pass
    return None


#-----------------------
def temperature_inversion_check(
        heater: HotWaterTank,
) -> None:
    
    pass
    return None

#-----------------------
def generate_output(
        heater: HotWaterTank,
) -> None:
    
    pass
    return None



def main():

    GS = GeneralSetup()
    ts = load_timeseries_all(GS)
    GS.DEWH = devices.ResistiveSingle()

    tank = HotWaterTank(GS.DEWH)

    for (idx, row) in ts.iterrows():

        preparation_error_checking(tank)
        precalculations(tank)
        iterative_loop(tank)
        temperature_inversion_check(tank)
        generate_output(tank)

    return

if __name__ == "__main__":
    main()


