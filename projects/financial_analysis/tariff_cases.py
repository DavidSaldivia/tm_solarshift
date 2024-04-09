import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Tuple, Dict

import tm_solarshift.general as general
import tm_solarshift.tariffs as tariffs
from tm_solarshift.devices import ResistiveSingle
from tm_solarshift.units import (
    Variable,
    conversion_factor as CF
)

DIR_PROJECT = os.path.dirname(os.path.abspath(__file__))
DIR_RESULTS = os.path.join(DIR_PROJECT,"results")

#--------------
def plot_results_cases(
    results: pd.DataFrame,
    savefig: bool = False,
    showfig: bool = False,
    width: float = 0.1,
)-> None:

    # creating the main objects (fix, ax) and some constants
    fig, ax = plt.subplots(figsize=(9,6))
    fs = 16
    width = 0.25
    N_COLS = 5
    #--------------------------
    #plotting non-solar results
    aux1 = results[~results["has_solar"]]
    
    # main pandas' comparison operators: and is &; or is |, not is ~
    # aux = results[ (results["energy_cost"] > 500.) (results["type_tariff"] == "flat") ]

    lbls = aux1["name"].to_list() + ["diverter w C1", "diverter w flat"]
    aux1["x"] = np.arange(N_COLS) - width/2.

    ax.bar(
        aux1["x"], aux1["energy_cost"], width, alpha=0.8, color="C0", label="No Solar",
    )

    #--------------------------
    #plotting solar results
    aux2 = results[results["has_solar"]]
    aux2.loc[N_COLS,"energy_cost"] = aux1.loc[0,"energy_cost"]
    aux2["x"] = np.arange(7) + width/2.
    ax.bar(
        aux2["x"], aux2["energy_cost"], width, alpha=0.8, color="C1", label="Solar",
    )
    
    # ------------------------
    # adding percentage annotation
    for i in range(5):
        pct_change = (
            aux2.loc[i+N_COLS, "energy_cost"] - aux1.loc[i, "energy_cost"]
            )/aux1.loc[i, "energy_cost"]
        txt = f"{pct_change:.2%}"
        location = ( aux2.loc[i+N_COLS,"x"]-width/2., aux2.loc[i+N_COLS,"energy_cost"] )
        ax.annotate(txt, location )

    #--------------------------
    # formatting the plot
    ax.legend(loc=0, fontsize=fs-2)
    ax.grid()
    # ax.set_ylim(0.5,0.8)
    ax.set_xticks(np.arange(7))
    # ax.set_yticks(numbers)
    ax.set_xticklabels(lbls, rotation=45)
    ax.set_xlabel( 'Cases of interest', fontsize=fs)
    ax.set_ylabel( 'Annual energy cost (AUD)', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)

    #--------------------------
    # saving the plot
    if savefig:
        fig.savefig(
            os.path.join(DIR_RESULTS, '0-energy_cost.png'),
            bbox_inches='tight')
    if showfig:
        plt.show()
    plt.close()

    return

#--------------
def plot_results_ruby(
    results: pd.DataFrame,
    savefig: bool = False,
    showfig: bool = False,
    width: float = 0.1,
)-> None:

    # creating the main objects (fix, ax) and some constants
    fig, ax = plt.subplots(figsize=(9,6))
    fs = 16
    width = 0.25
    N_COLS = 5
    #--------------------------
    #plotting non-solar results
    aux1 = results[~results["has_solar"]]
    
    # main pandas' comparison operators: and is &; or is |, not is ~
    # aux = results[ (results["energy_cost"] > 500.) (results["type_tariff"] == "flat") ]

    lbls = aux1["name"].to_list() + ["diverter w C1", "diverter w flat"]
    aux1["x"] = np.arange(N_COLS) - width/2.
    ax.bar(
        aux1["x"], aux1["energy_cost"], width, alpha=0.8, color="C0", label="No Solar",
    )

    #--------------------------
    #plotting solar results
    aux2 = results[results["has_solar"]]
    aux2.loc[N_COLS,"energy_cost"] = aux1.loc[0,"energy_cost"]
    aux2["x"] = np.arange(7) + width/2.
    ax.bar(
        aux2["x"], aux2["energy_cost"], width, alpha=0.8, color="C1", label="Solar",
    )
    
    # ------------------------
    # adding percentage annotation
    for i in range(5):
        pct_change = (
            aux2.loc[i+N_COLS, "energy_cost"] - aux1.loc[i, "energy_cost"]
            )/aux1.loc[i, "energy_cost"]
        txt = f"{pct_change:.2%}"
        location = ( aux2.loc[i+N_COLS,"x"]-width/2., aux2.loc[i+N_COLS,"energy_cost"] )
        ax.annotate(txt, location )

    #--------------------------
    # formatting the plot
    ax.legend(loc=0, fontsize=fs-2)
    ax.grid()
    # ax.set_ylim(0.5,0.8)
    ax.set_xticks(np.arange(7))
    # ax.set_yticks(numbers)
    ax.set_xticklabels(lbls, rotation=45)
    ax.set_xlabel( 'Cases of interest', fontsize=fs)
    ax.set_ylabel( 'Annual energy cost (AUD)', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)

    #--------------------------
    # saving the plot
    if savefig:
        fig.savefig(
            os.path.join(DIR_RESULTS, '0-energy_cost.png'),
            bbox_inches='tight')
    if showfig:
        plt.show()
    plt.close()

    return

#--------------
def calculate_annual_bill(
        case: pd.Series,
        verbose: bool = True,
        ) -> float:
    
    #Retriever required data
    type_tariff = case["type_tariff"]
    has_solar = case["has_solar"]
    type_control = case["type_control"]
    model = "491315" if (case["household_size"]==4) else "491160"
    daily_avg = 200. if (case["household_size"]==4) else 100.

    match type_control:
        case "CL1":
            control_load = 1
        case "GS":
            control_load = 0
        case "timer":
            control_load = 4
        case "diverter":
            control_load = 1 if type_tariff == "CL" else (10 if type_tariff == "flat" else None)

    if verbose:
        print("Create an instance of GS and create a ts timeseries")
    GS = general.GeneralSetup()
    GS.household.tariff_type = type_tariff
    GS.household.control_type = type_control
    GS.household.control_load = control_load
    GS.DEWH = ResistiveSingle.from_model_file(model=model)
    GS.HWDInfo.daily_avg = Variable( daily_avg, "L/d")
    GS.HWDInfo.daily_max = Variable( 2*daily_avg, "L/d")
    GS.HWDInfo.daily_std = Variable( daily_avg/3., "L/d")
    
    if verbose:
        print("Get timeseries with import rate")
    ts = GS.create_ts()
    ts = tariffs.get_import_rate(ts,
                                 tariff_type = GS.household.tariff_type,
                                 control_load = GS.household.control_load,
                                 dnsp = GS.household.DNSP,
                                 return_energy_plan = False,
                                 )
    if has_solar:
        if verbose:
            print("Simulate solar")
        pv_power = GS.solar_system.load_PV_generation(df = ts, tz='Australia/Brisbane', unit="kW")
    else:
        pv_power = 0.

    if verbose:
        print(f"Calculate annual bill with {type_tariff}")

    if type_control in ["GS", "CL1", "timer"]:
        ( out_all, _ ) = GS.run_thermal_simulation(ts, verbose=True)
        STEP_h = ts.index.freq.n * CF("min","hr")
        heater_power = out_all["HeaterPower"] * CF("kJ/h", "kW")

        out_all["imported_energy"] = np.where( pv_power < heater_power, heater_power - pv_power, 0 )
        annual_bill = (ts["tariff"] * out_all["imported_energy"] * STEP_h).sum()

    elif type_control == "diverter":
        #It considers three hours at night plus everything diverted from solar
        import tm_solarshift.control as control
        ts = control.load_schedule(ts, control_load = control_load, random_ON=False)
        ts_timer = ts["CS"].copy()

        heater_nom_power = GS.DEWH.nom_power.get_value("kW")
        ts["CS"] = np.where(
            ts["CS"]>=0.99,
            ts["CS"],
            np.where(
                (pv_power > 0) & (pv_power < heater_nom_power),
                pv_power / heater_nom_power,
                np.where(pv_power > heater_nom_power, 1., 0.)
            )
        )
        ( out_all, _ ) = GS.run_thermal_simulation(ts, verbose=verbose)
        STEP_h = ts.index.freq.n * CF("min","hr")
        heater_power = out_all["HeaterPower"] * CF("kJ/h", "kW")
        out_all["imported_energy"] = (ts_timer * heater_power) 
        annual_bill = (ts["tariff"] * out_all["imported_energy"] * STEP_h).sum()
    else:
        annual_bill = None

    return annual_bill

def run_simulations():


    cases = pd.read_csv(os.path.join(DIR_PROJECT,"cases.csv"), index_col=0)
    cases["energy_cost"] = None

    file_cases = os.path.join(DIR_RESULTS, "energy_cost_cases.csv")
    for (idx,case) in cases.iterrows():
        annual_bill = calculate_annual_bill(case, verbose = True)
        cases.loc[idx, "energy_cost"] = annual_bill
        cases.to_csv(file_cases)

        print(cases.loc[idx])

    print(cases)
    plot_results_cases(cases, savefig=True, showfig=True)
    return

#------------------
def run_simulations_ruby(file_path: str = "test_case_one.csv"):

    #General parameters (do not change in this analysis)
    cases = pd.read_csv(os.path.join(DIR_PROJECT,file_path), index_col=0)
    cases["energy_cost"] = None

    file_output = os.path.join(DIR_PROJECT, file_path[:-4]+"_annual_bill.csv")
    for (idx,case) in cases.iterrows():
        annual_bill = calculate_annual_bill(case, verbose = True)
        cases.loc[idx, "energy_cost"] = annual_bill
        cases.to_csv(file_output)

        print(cases.loc[idx])

    print(cases)
    plot_results_ruby(cases, savefig=True, showfig=True)
    return
#------------------------

if __name__ == "__main__":
    
    run_simulations_ruby()

    # file_cases = os.path.join(DIR_PROJECT, "energy_cost_cases.csv")
    # cases = pd.read_csv(os.path.join(DIR_PROJECT,file_cases), index_col=0)
    # plot_results(cases, savefig=True, showfig=True)

    pass

# #-------------------------
# def main():
    
#     #General parameters (not changed)
#     location = "Sydney"
#     HWDP = 1
    
#     cases = pd.read_csv(os.path.join(DIR_PROJECT,"cases.csv"), index_col=0)
#     cases["energy_cost"] = None
    
#     results_fldr = os.path.join(DIRECTORY.DIR_RESULTS, "parametric_ResistiveSingle")
#     results_file = "0-parametric_ResistiveSingle.csv"
#     results = pd.read_csv(
#         os.path.join(results_fldr, results_file),
#         index_col=0
#         )

#     file_cases = os.path.join(DIR_PROJECT, "energy_cost_cases.csv")
#     for (idx,case) in cases.iterrows():

#         calculate_annual_bill(case)
#         control_load = case["control_load"]

#         #Check if there is a results file
#         case_id = results[
#             (results["household.location"] == location) &
#             (results["HWDInfo.profile_HWD"] == HWDP) &
#             (results["household.control_load"] == control_load)
#         ].index[0]
#         out_all = pd.read_csv(
#             os.path.join(results_fldr, f"case_{case_id}_results.csv"),
#             index_col = 0,
#         )
#         out_all.index = pd.to_datetime(out_all.index)

#         energy_cost = tariffs.calculate_energy_cost(case, df_tm = out_all)
#         cases.loc[idx, "energy_cost"] = energy_cost
#         cases.to_csv(file_cases)

#     print(cases)
#     plot_results(cases, savefig=True, showfig=True)

#     return

