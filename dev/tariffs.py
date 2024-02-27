import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Tuple, Dict

import tm_solarshift.general as general
from tm_solarshift.constants import (DIRECTORY, DEFINITIONS)
from tm_solarshift.constants import UNITS
CF = UNITS.conversion_factor

from tm_solarshift.external.energy_plan_utils import (
    get_energy_breakdown,
    get_energy_plan_for_dnsp,
)

def get_import_rate(
        ts: pd.DataFrame,
        tariff_type: str = "flat",
        dnsp: str = "Ausgrid",
        return_energy_plan: bool = True,
        control_load: int = 1, #only used if tariff_type=="CL"

) -> Tuple[pd.DataFrame,Dict] | pd.DataFrame:

    # Preparing ts to the format required by Rui's code
    ts2 = ts.copy()
    ts2["t_stamp"] = ts2.index
    ts2["pv_energy"] = 0.   #Not used, defined to avoid error inside Rui's code
    ts2["load_energy"] = 0. #Not used, defined to avoid error inside Rui's code
    
    if tariff_type == "flat":
        energy_plan = get_energy_plan_for_dnsp(
            dnsp, tariff_type=tariff_type, convert=True
        )
        ts["tariff"] = energy_plan["flat_rate"]
        ts["rate_type"] = "flat_rate"

    elif tariff_type == "tou":
        file_tou = os.path.join(DIRECTORY.DIR_MAIN, "dev", "tou_cache.csv")
        
        if os.path.isfile(file_tou):
            energy_plan = get_energy_plan_for_dnsp(
                dnsp, tariff_type=tariff_type, convert=True
            )
            ts3 = pd.read_csv(file_tou, index_col=0)
            ts3.index = pd.to_datetime(ts3.index)
        else:
            energy_plan = get_energy_plan_for_dnsp(
                dnsp, tariff_type=tariff_type, convert=True
            )
                
            (_, ts3) = get_energy_breakdown(
                tariff_type=tariff_type,
                tariff_structure=energy_plan,
                raw_data=ts2,
                resolution=180,
                return_raw_data=True)
            ts3.to_csv(file_tou)

        ts["tariff"] = ts3["import_rate"]
        ts["rate_type"] = ts3["rate_type"]
    
    elif tariff_type == "CL":
        energy_plan = get_energy_plan_for_dnsp(
            dnsp, tariff_type="flat", convert=True,
            controlled_load_num=control_load, switching_cl=True,
        )
        ts["tariff"] = energy_plan["CL_rate"]
        ts["rate_type"] = "CL"

    if return_energy_plan:
        return (ts, energy_plan)
    else:
        return ts


def calculate_energy_cost(
        df_all: pd.DataFrame,
        row: pd.Series,
        results_fldr: str = None,
        HWDP: int = 1,
        location: str = "Sydney",
        ):

    control_load = row["control_load"]
    tariff_type = row["tariff_type"]
    dnsp = "Ausgrid"

    case_id = df_all[
        (df_all["household.location"] == location) &
        (df_all["HWDInfo.profile_HWD"] == HWDP) &
        (df_all["household.control_load"] == control_load)].index[0]
    df_detailed = pd.read_csv(
        os.path.join(results_fldr, f"case_{case_id}_results.csv"),
        index_col = 0,
    )
    df_detailed.index = pd.to_datetime(df_detailed.index)

    STEP_h = 0.05  #Change later

    ts = get_import_rate(
        df_detailed,
        tariff_type, dnsp,
        return_energy_plan=False,
    )

    if row["solar"]:
        tz = 'Australia/Brisbane'
        (lat,long) = (-33.86, 151.22)
        (tilt, orient) = (abs(lat), 180.)
        PV_nompower = 5000.   # (W)
        from tm_solarshift.external.pvlib_utils import load_PV_generation
        df_aux = load_PV_generation(
            tz=tz, latitude=lat, longitude=long,
            tilt=tilt, orient=orient, PV_nompower=PV_nompower
        )
        df_aux.index = df_detailed.index
        PVPower =  df_aux["PVPower"] * CF("W", "kW")
        HeaterPower = df_detailed["HeaterPower"] * CF("kJ/h", "kW")
        import_energy = np.where( PVPower < HeaterPower, HeaterPower - PVPower, 0 )
        energy_cost = (
            ts["tariff"] * import_energy * STEP_h  
            ).sum()
        
    else:    
        energy_cost = (
            ts["tariff"] 
            * df_detailed["HeaterPower"] * STEP_h  * CF("kJ/h", "kW")
            ).sum()

    return energy_cost

#--------------
def plot_results(
    results,
    savefig=False,
    showfig=False,
    width=0.1,
    ):

    lbls = ["CL1", "GS-flat", "GS-tou", "SS-flat", "SS-tou"]

    fig, ax = plt.subplots(figsize=(9,6))
    # ax2 = ax.twinx()
    fs = 16
    width = 0.25
    aux1 = results[~results["solar"]]
    aux1["x"] = np.arange(5) - width/2.
    ax.bar(aux1["x"], aux1["energy_cost"],
            width, alpha=0.8, color="C0",
            label="No Solar")
    
    aux2 = results[results["solar"]]
    aux2.loc[5,"energy_cost"] = aux1.loc[0,"energy_cost"]

    aux2["x"] = np.arange(5) + width/2.
    ax.bar(aux2["x"], aux2["energy_cost"],
            0.25, alpha=0.8, color="C1",
            label="Solar")
    
    for i in range(len(lbls)):
        pct_change = (
            aux2.loc[i+5, "energy_cost"]-aux1.loc[i, "energy_cost"]
            )/aux1.loc[i, "energy_cost"]
        txt = f"{pct_change:.2%}"
        ax.annotate(txt, (aux2.loc[i+5,"x"]-width/2.,aux2.loc[i+5,"energy_cost"]))

    
    # ax2.bar([],[], alpha=0.8, color="C0", label=" No solar")
    # ax2.bar([],[], alpha=0.8, color="C1", label="Solar")
    
    ax.legend(fontsize=fs-2)
    ax.grid()
    # ax2.legend(fontsize=fs-2)
    
    # ax.set_ylim(0.5,0.8)
    ax.set_xticks(np.arange(5))
    ax.set_xticklabels(lbls, rotation=45)
    ax.set_xlabel( 'Cases of interest', fontsize=fs)
    ax.set_ylabel( 'Annual energy cost (AUD)', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    # ax.set_ylim(-0.0002,0.0)
    if savefig:
        fig.savefig(
            os.path.join(DIRECTORY.DIR_MAIN, "dev", '0-energy_cost.png'),
            bbox_inches='tight')
    if showfig:
        plt.show()
    plt.close()
    return
    return

#-------------------------
def main2():
    
    results_fldr = os.path.join(DIRECTORY.DIR_RESULTS, "parametric_ResistiveSingle")
    results_file = "0-parametric_ResistiveSingle.csv"
    results = pd.read_csv(
        os.path.join(results_fldr, results_file),
        index_col=0
        )
    cases_d = [
        {"control_load": 1, "tariff_type": "CL",  "solar": False},
        {"control_load": 0, "tariff_type": "flat",  "solar": False},
        {"control_load": 0, "tariff_type": "tou",  "solar": False},
        {"control_load": 4, "tariff_type": "flat",  "solar": False},
        {"control_load": 4, "tariff_type": "tou",  "solar": False},
        {"control_load": 1, "tariff_type": "CL",  "solar": True},
        {"control_load": 0, "tariff_type": "flat",  "solar": True},
        {"control_load": 0, "tariff_type": "tou",  "solar": True},
        {"control_load": 4, "tariff_type": "flat",  "solar": True},
        {"control_load": 4, "tariff_type": "tou",  "solar": True},   
    ]

    cases = pd.DataFrame(cases_d)
    cases["energy_cost"] = None
    
    file_cases = os.path.join(DIRECTORY.DIR_MAIN, "dev", "energy_cost_cases.csv")
    if os.path.isfile(file_cases):
        cases = pd.read_csv(file_cases, index_col=0)
    
    else:
        for (idx,case) in cases.iterrows():
            energy_cost = calculate_energy_cost(results, case, results_fldr)
            cases.loc[idx, "energy_cost"] = energy_cost
        
        cases.to_csv(file_cases)

    print(cases)
    plot_results(cases, savefig=True, showfig=True)

if __name__ == "__main__":
    # main()
    main2()
    pass

#--------------------
def main():
    
    dnsp = "Ausgrid"
    tariff_type = "CL"
    control_load = 1

    GS = general.GeneralSetup()
    GS.household.DNSP = dnsp
    GS.household.tariff_type = tariff_type
    GS.household.control_load = control_load
    ts = GS.simulation.create_new_profile()
    (ts, energy_plan) = get_import_rate(
        ts, tariff_type=tariff_type, dnsp=dnsp,
        control_load=control_load,
        return_energy_plan=True, 
    )
    print(ts, energy_plan)
    
    #-------------------
    dnsp = "Ausgrid"
    tariff_type = "tou"

    GS = general.GeneralSetup()
    GS.household.DNSP = dnsp
    GS.household.tariff_type = tariff_type
    ts = GS.simulation.create_new_profile()
    (ts, energy_plan) = get_import_rate(
        ts, tariff_type=tariff_type, dnsp=dnsp, return_energy_plan=True
    )
    print(ts, energy_plan)

    #-------------------
    dnsp = "Ausgrid"
    tariff_type = "flat"
    GS = general.GeneralSetup()
    GS.household.DNSP = dnsp
    GS.household.tariff_type = tariff_type
    ts = GS.simulation.create_new_profile()
    (ts, energy_plan) = get_import_rate(
        ts, tariff_type=tariff_type, dnsp=dnsp, return_energy_plan=True
    )
    print(ts, energy_plan)

    return