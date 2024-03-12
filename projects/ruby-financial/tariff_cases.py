import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Tuple, Dict

import tm_solarshift.general as general
from tm_solarshift.constants import (DIRECTORY, DEFINITIONS)
from tm_solarshift.units import conversion_factor as CF
import tm_solarshift.tariffs as tariffs


DIR_PROJECT = os.path.dirname(os.path.abspath(__file__))

#--------------
def plot_results(
    results: pd.DataFrame,
    savefig: bool = False,
    showfig: bool = False,
    width: float = 0.1,
)-> None:

    fig, ax = plt.subplots(figsize=(9,6))
    fs = 16
    width = 0.25
    aux1 = results[~results["has_solar"]]
    lbls = aux1["name"].to_list() + ["diverter w C1", "diverter w flat"]
    aux1["x"] = np.arange(5) - width/2.
    ax.bar(
        aux1["x"], aux1["energy_cost"], width, alpha=0.8, color="C0", label="No Solar",
    )
    
    aux2 = results[results["has_solar"]]
    aux2.loc[5,"energy_cost"] = aux1.loc[0,"energy_cost"]
    aux2["x"] = np.arange(7) + width/2.
    ax.bar(
        aux2["x"], aux2["energy_cost"], width, alpha=0.8, color="C1", label="Solar",
    )
    
    for i in range(5):
        pct_change = (
            aux2.loc[i+5, "energy_cost"] - aux1.loc[i, "energy_cost"]
            )/aux1.loc[i, "energy_cost"]
        txt = f"{pct_change:.2%}"
        ax.annotate(txt, (aux2.loc[i+5,"x"]-width/2.,aux2.loc[i+5,"energy_cost"]))

    ax.legend(fontsize=fs-2)
    ax.grid()
    
    # ax.set_ylim(0.5,0.8)
    ax.set_xticks(np.arange(7))
    ax.set_xticklabels(lbls, rotation=45)
    ax.set_xlabel( 'Cases of interest', fontsize=fs)
    ax.set_ylabel( 'Annual energy cost (AUD)', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    if savefig:
        fig.savefig(
            os.path.join(DIR_PROJECT, '0-energy_cost.png'),
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
    tariff_type = case["tariff_type"]
    has_solar = case["has_solar"]
    control_type = case["control_type"]
    control_load = case["control_load"]

    if verbose:
        print("Create an instance of GS and create a ts timeseries")
    GS = general.GeneralSetup()
    GS.household.tariff_type = tariff_type
    GS.household.control_type = control_type
    GS.household.control_load = control_load
    ts = GS.create_ts_default()

    if verbose:
        print("Get timeseries with import rate")
    ts = tariffs.get_import_rate(ts,
                                 tariff_type = GS.household.tariff_type,
                                 control_load = GS.household.control_load,
                                 dnsp = GS.household.DNSP,
                                 return_energy_plan = False,
                                 )

    if has_solar:
        if verbose:
            print("Simulate solar if needed")
            
        tz = 'Australia/Brisbane'
        solar_system = GS.solar_system
        pv_power = solar_system.load_PV_generation(df = ts, tz=tz,  unit="kW")
    else:
        pv_power = 0.

    if verbose:
        print(f"Calculate annual bill with {tariff_type}")

    if control_type in ["CL", "GS", "timer"]:
        ( out_all, _ ) = GS.run_thermal_simulation(ts, verbose=True)
        STEP_h = ts.index.freq.n * CF("min","hr")
        heater_power = out_all["HeaterPower"] * CF("kJ/h", "kW")

        imported_energy = np.where( pv_power < heater_power, heater_power - pv_power, 0 )
        annual_bill = (ts["tariff"] * imported_energy * STEP_h).sum()

    elif control_type == "diverter":

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

        imported_energy = (ts_timer * heater_power) 
        annual_bill = (ts["tariff"] * imported_energy * STEP_h).sum()

    else:

        annual_bill = None

    return annual_bill

def run_simulations():

    #General parameters (do not change in this analysis)
    location = "Sydney"
    HWDP = 1
    
    cases = pd.read_csv(os.path.join(DIR_PROJECT,"cases.csv"), index_col=0)
    cases["energy_cost"] = None

    file_cases = os.path.join(DIR_PROJECT, "energy_cost_cases.csv")
    for (idx,case) in cases.iterrows():
        annual_bill = calculate_annual_bill(case, verbose = True)
        cases.loc[idx, "energy_cost"] = annual_bill
        cases.to_csv(file_cases)

        print(cases.loc[idx])

        if idx == 11:
            break

    print(cases)
    plot_results(cases, savefig=True, showfig=True)
    return

if __name__ == "__main__":
    
    # run_simulations()

    file_cases = os.path.join(DIR_PROJECT, "energy_cost_cases.csv")
    cases = pd.read_csv(os.path.join(DIR_PROJECT,file_cases), index_col=0)
    plot_results(cases, savefig=True, showfig=True)

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

