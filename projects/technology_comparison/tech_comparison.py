import os
import pandas as pd

from tm_solarshift.general import Simulation
from tm_solarshift.utils.units import VariableList
import tm_solarshift.analysis.parametric as parametric
PARAMS_OUT = parametric.PARAMS_OUT
from tm_solarshift.devices import (
    ResistiveSingle,
    HeatPump,
    GasHeaterInstantaneous,
    GasHeaterStorage,
    SolarThermalElecAuxiliary,
)

DIR_PROJECT = os.path.dirname(os.path.abspath(__file__))

#Initializing all the heaters:
HEATERS = {
    "resistive": ResistiveSingle(),
    "heat_pump": HeatPump(),
    "gas_instant": GasHeaterInstantaneous(),
    "gas_storage": GasHeaterStorage(),
    "STC_auxelec": SolarThermalElecAuxiliary(),
}

HEATERS_COLORS = {
    "resistive": "red",
    "heat_pump": "green",
    "gas_instant": "blue",
    "gas_storage": "navy",
    "STC_auxelec": "mustard",
}

def plot_tech_comparison(
        df: pd.DataFrame,
        savefig: bool = False,
        showfig: bool = False,
        dirfig: str = os.path.join(DIR_PROJECT,"results"),
        ):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 6))
    fs = 16
    width = 0.25
    ax.bar( df.index-width/2, df["emissions_total"],
           width=width, label="total" )
    ax.bar( df.index+width/2, df["emissions_marginal"],
           width=width, label="marginal" )

    ax.set_ylim(0.0,2.5)
    # ax.set_xticks(list_profile_control)
    # ax.set_xticklabels(df["heater"], rotation=45)
    ax.set_xticks(df.index, labels = df["name"], rotation=45, horizontalalignment='right')
    ax.set_xlabel( 'Heater Technology', fontsize=fs)
    ax.set_ylabel( r'Annual accumulated emissions (t-$CO_2$-e)', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)

    ax.legend(loc=0, fontsize=fs-2)
    ax.grid()

    if savefig:
        if not os.path.exists(dirfig):
            os.mkdir(dirfig)
        filefig = os.path.join(dirfig, "tech_comparison.png")
        fig.savefig(filefig, bbox_inches="tight",)
    if showfig:
        plt.show()
    plt.close()
    return None

def plot_city_comparison(
        df: pd.DataFrame,
        savefig: bool = False,
        showfig: bool = False,
        dirfig: str = os.path.join(DIR_PROJECT,"results"),
        ):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1,2,figsize=(14, 8))
    fs = 16
    width = 0.5
    i=0
    for CL in [1,4]:
        CL_names = {1:"CL1", 4:"solar soak"}
        df_aux = df[df["household.control_load"]==CL]
        df_aux.reset_index()
        ax[i].bar( df_aux.index-width/2, df_aux["emissions_total"],
            width=width, label="total" )
        ax[i].bar( df_aux.index+width/2, df_aux["emissions_marginal"],
            width=width, label="marginal" )

        ax[i].set_ylim(0.0,3.0)
        ax[i].set_xticks(df_aux.index, labels = df_aux["name"], rotation=45, horizontalalignment='right')
        ax[i].set_xlabel( f'Different cities with {CL_names[CL]}', fontsize=fs)
        ax[i].set_ylabel( r'Annual accumulated emissions (t-$CO_2$-e)', fontsize=fs)
        ax[i].tick_params(axis='both', which='major', labelsize=fs)

        ax[i].legend(loc=0, fontsize=fs-2)
        ax[i].grid()
        i+=1

    if savefig:
        if not os.path.exists(dirfig):
            os.mkdir(dirfig)
        filefig = os.path.join(dirfig, "city_comparison.png")
        fig.savefig(filefig, bbox_inches="tight",)
    if showfig:
        plt.show()
    plt.close()
    return None

#------------------------------
def run_tech_comparison(
        dir_results: str = None,
        file_results: str = None,
) -> pd.DataFrame:
    """
    Example of a parametric analysis over parameters in the tank.
    """

    GS_base = Simulation()
    cases_in = pd.read_csv(
        os.path.join(DIR_PROJECT, "tech_comparison_input.csv")
    )
    cases_in["heater"] = cases_in["DEWH"]
    units_in = {}
    for (idx,row) in cases_in.iterrows():
        cases_in.loc[idx,"DEWH"] = HEATERS[row["DEWH"]]
    units_in = {col:None for col in cases_in.columns}

    runs = parametric.analysis(
        cases_in, units_in, PARAMS_OUT,
        GS_base = GS_base,
        save_results_detailed = True,
        gen_plots_detailed    = True,
        save_plots_detailed   = True,
        save_results_general  = True,
        fldr_results_detailed = dir_results,
        fldr_results_general  = dir_results,
        file_results_general  = file_results,
        )
    return runs

#------------------------------
def run_city_comparison(
        dir_results: str = None,
        file_results: str = None,
) -> pd.DataFrame:

    GS_base = Simulation()
    cases_in = pd.read_csv(
        os.path.join(DIR_PROJECT, "city_comparison_input.csv")
    )
    cases_in["heater"] = cases_in["DEWH"]
    units_in = {}
    for (idx,row) in cases_in.iterrows():
        cases_in.loc[idx,"DEWH"] = HEATERS[row["DEWH"]]
    units_in = {col:None for col in cases_in.columns}

    runs = parametric.analysis(
        cases_in, units_in, PARAMS_OUT,
        GS_base = GS_base,
        save_results_detailed = True,
        gen_plots_detailed    = True,
        save_plots_detailed   = True,
        save_results_general  = True,
        fldr_results_detailed = dir_results,
        fldr_results_general  = dir_results,
        file_results_general  = file_results,
        )
    return runs

def main():
    runsim = False
    DIR_RESULTS = os.path.join(DIR_PROJECT,"results_tech")
    FILE_RESULTS = os.path.join(DIR_RESULTS, '0-tech_comparison_output.csv')
    if runsim:
        runs = run_tech_comparison(
            file_results=FILE_RESULTS, dir_results=DIR_RESULTS
        )
    else:
        runs = pd.read_csv(FILE_RESULTS)
    print(runs)
    plot_tech_comparison(runs, savefig=True, showfig=True, dirfig=DIR_RESULTS)

    #------------------
    runsim = False
    DIR_RESULTS = os.path.join(DIR_PROJECT, "results_city")
    FILE_RESULTS = os.path.join(DIR_RESULTS, '0-city_comparison_output.csv')
    if runsim:
        runs = run_city_comparison(DIR_RESULTS, FILE_RESULTS)
    else:
        runs = pd.read_csv(FILE_RESULTS)
    print(runs)
    plot_city_comparison(runs, savefig=True, showfig=True,dirfig=DIR_RESULTS)
    return

if __name__=="__main__":
    main()
    
