import os
import numpy as np
import pandas as pd

from tm_solarshift.general import GeneralSetup

#-------------------

def main():

    #Create a general setup instance. It contains all the settings for the simulation
    GS = GeneralSetup()

    #Create a timeseries dataframe. For now, only with default values
    ts = GS.create_ts_default()

    #Run a thermal simulation with the default case
    #Because TRNSYS is the default engine, it generates two objects
    #out_all contains all the detailed results from the simulations
    #out_overall contain post-processed results
    (out_all, out_overall) = GS.run_thermal_simulation(ts)

    print(out_all)
    print(out_overall)

    return

if __name__ == "__main__":
    main()