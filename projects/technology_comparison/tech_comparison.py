import os
import pandas as pd

from tm_solarshift.constants import DIRECTORY
from tm_solarshift.general import GeneralSetup
from tm_solarshift.devices import (
    ResistiveSingle,
    HeatPump,
    GasHeaterInstantaneous,
    GasHeaterStorage,
    SolarThermalElecAuxiliary,
)

DIR_PROJECT = os.path.dirname(os.path.abspath(__file__))
DIR_RESULTS = os.path.join(DIR_PROJECT,"results")

#Initializing all the heaters:
HEATERS = {
    "resistive (CL1)": ResistiveSingle(),
    "heat pump (CL1)": HeatPump(),
    "gas instantaneous": GasHeaterInstantaneous(),
    "gas with storage": GasHeaterStorage(),
    "solar thermal w elec aux": SolarThermalElecAuxiliary(),
}

HEATERS_COLORS = {
    "resistive": "red",
    "heat_pump": "green",
    "gas_instant": "blue",
    "gas_storage": "navy",
    "solar_thermal": "mustard",
}

def plot_technology_comparison(
        df: pd.DataFrame,
        savefig: bool = False,
        showfig: bool = False,
        ):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 6))
    fs = 16

    ax.bar( df.index, df["emissions"] )

    ax.set_ylim(0.0,2.5)
    # ax.set_xticks(list_profile_control)
    # ax.set_xticklabels(df["heater"], rotation=45)
    ax.set_xticks(df.index, labels = df["heater"], rotation=45, horizontalalignment='right')
    ax.set_xlabel( 'Heater Technology', fontsize=fs)
    ax.set_ylabel( r'Annual accumulated emissions (t-$CO_2$-e)', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)

    # ax.legend(loc=0, fontsize=fs - 2, bbox_to_anchor=(-0.1, 0.9))
    ax.grid()


    if savefig:
        if not os.path.exists(DIR_RESULTS):
            os.mkdir(DIR_RESULTS)
        fig.savefig(
            os.path.join(DIR_RESULTS, "emissions_comparison.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close()

    return None

def get_or_load_results(
        runsim:bool = False,
        file_name: str = "emissions_comparison.csv"
) -> pd.DataFrame:

    COLS = ["heater", "perf", "emissions"]
    GS = GeneralSetup()
    if runsim:
        ts = GS.create_ts()

        data = []
        for heater_name in HEATERS.keys():
            
            print(heater_name)
            GS.DEWH = HEATERS[heater_name]
            (out_all, out_overall) = GS.run_thermal_simulation( ts, verbose=True )

            data.append([
                heater_name,
                out_overall["heater_perf_avg"],
                out_overall["emissions_total"]
            ])
            print(data[-1])
            print()

        df = pd.DataFrame(data, columns=COLS)
        df.to_csv(os.path.join(DIR_RESULTS, file_name))
    else:
        df = pd.read_csv(os.path.join(DIR_RESULTS, file_name), index_col=0)

    return df

def main():


    df = get_or_load_results()
    plot_technology_comparison(df, savefig=True, showfig=True)

    return


if __name__=="__main__":
    main()
    
