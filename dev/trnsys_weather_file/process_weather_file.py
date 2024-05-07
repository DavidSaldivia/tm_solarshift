import subprocess
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from tm_solarshift.constants import (DIRECTORY, DEFINITIONS, SIMULATIONS_IO)
from tm_solarshift.utils.units import conversion_factor as  CF
from tm_solarshift.thermal_models.trnsys import (
    METEONORM_FILES,
    METEONORM_FOLDER,
    TRNSYS_EXECUTABLE
)
DIR_MAIN = DIRECTORY.DIR_MAIN
TS_WEATHER = SIMULATIONS_IO.TS_TYPES["weather"]
DIR_PROJECT = os.path.dirname(os.path.abspath(__file__))
DCK_PATH_BASE = os.path.join(DIR_PROJECT, "TRNSYS_weather_processing.dck")
DCK_PATH_RUN = os.path.join(DIR_PROJECT, "TRNSYS_temp.dck")
TRNSYS_OUTPUT_PATH = os.path.join(DIR_PROJECT, "output_meteonorm_temp.dat")
LOCATIONS = DEFINITIONS.LOCATIONS_METEONORM

def main():



    keyword1 = "ASSIGN"
    keyword2 = "Australia-Oceania"

    for location in LOCATIONS:

        df1 = pd.read_csv(
            os.path.join(
                DIRECTORY.DIR_DATA["weather"], "meteonorm_processed",
                "old", f"meteonorm_{location}.csv"
            )
        )
        df2 = pd.read_csv(
            os.path.join(
                DIRECTORY.DIR_DATA["weather"], "meteonorm_processed",
                f"meteonorm_{location}.csv"
            )
        )
        print(location)

        print((df1["GHI"]/df2["GHI"]).mean())
        # plt.plot(df1["GHI"],df2["GHI"])
        # plt.show()

        weather_path = os.path.join(METEONORM_FOLDER, METEONORM_FILES[location])

        with open(DCK_PATH_BASE, "r") as file_in:
            dck_file = file_in.read().splitlines()
        
        for (idx,line) in enumerate(dck_file):

            if keyword1 in line and keyword2 in line:
                aux = line.split('"')
                new_line = aux[0] + ' "' + f"{weather_path}" + ' "' + aux[-1]
                dck_file[idx] = new_line
                print(dck_file[idx])

        with open(DCK_PATH_RUN, "w") as dckfile_out:
            for line in dck_file:
                dckfile_out.write(f"{line}\n")    
        
        subprocess.run([TRNSYS_EXECUTABLE, DCK_PATH_RUN, "/h"])

        df = pd.read_table( TRNSYS_OUTPUT_PATH,  sep=r"\s+",  index_col=0 )
        df = df[TS_WEATHER]
        df = df.iloc[1:]

        # Converting from kJ/hr to W
        df["GHI"] = df["GHI"] * CF("kJ/hr", "W")
        df["DNI"] = df["DNI"] * CF("kJ/hr", "W")
        df["DHI"] = df["DHI"] * CF("kJ/hr", "W")
        print(df["GHI"].describe())
        # print(1/3.6)
        df.to_csv( os.path.join(DIR_PROJECT, f"meteonorm_{location}.csv") )

        print(df["GHI"].sum()*(3./60.)/365.)

    return

if __name__ == "__main__":
    main()