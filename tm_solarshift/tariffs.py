import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Tuple, Dict
from functools import lru_cache

import tm_solarshift.general as general
from tm_solarshift.constants import (DIRECTORY, DEFINITIONS)
from tm_solarshift.units import conversion_factor as CF
from tm_solarshift.devices import (
    SolarSystem,
    GasHeaterInstantaneous,
)

from tm_solarshift.external.energy_plan_utils import (
    get_energy_breakdown,
    get_energy_plan_for_dnsp,
)

DIR_TARIFFS = DIRECTORY.DIR_DATA["tariffs"]
GAS_TARIFF_SAMPLE_FILE = os.path.join(DIRECTORY.DIR_DATA["gas"],"energyaustralia_basic.json")

#-----------
def get_import_rate(
        ts: pd.DataFrame,
        tariff_type: str = "flat",
        dnsp: str = "Ausgrid",
        return_energy_plan: bool = True,
        control_load: int = 1,

) -> Tuple[pd.DataFrame,Dict] | pd.DataFrame:

    # Preparing ts to the format required by Rui's code
    ts2 = pd.DataFrame(index=ts.index, columns = [
        "t_stamp",
        "pv_energy", "load_energy",
        "tariff", "rate_type",
        ]
    )
    ts2["t_stamp"] = ts2.index
    ts2["pv_energy"] = 0.       #Not used, defined to avoid error inside Rui's code
    ts2["load_energy"] = 0.     #Not used, defined to avoid error inside Rui's code
    
    match tariff_type:
        case "flat":
            energy_plan = get_energy_plan_for_dnsp(dnsp,
                                                tariff_type = tariff_type,
                                                convert = True,)
            ts2["tariff"] = energy_plan["flat_rate"]
            ts2["rate_type"] = "flat"
        case "tou":
            file_tou = os.path.join(DIR_TARIFFS, "tou_cache.csv")
            
            if os.path.isfile(file_tou):
                energy_plan = get_energy_plan_for_dnsp(dnsp,
                                                    tariff_type = tariff_type,
                                                    convert=True
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

            ts2["tariff"] = ts3["import_rate"]
            ts2["rate_type"] = ts3["rate_type"]
        
        case "CL":
            energy_plan = get_energy_plan_for_dnsp(
                dnsp,
                tariff_type="flat",
                convert=True,
                controlled_load_num = control_load,
                switching_cl = True,
            )
            ts2["tariff"] = energy_plan["CL_rate"]
            ts2["rate_type"] = "CL"
        case "gas":
            
            # values for AGL's Residential Value Saver (standard). Average value is given
            ts2["tariff"] = 0.033 * CF("MJ", "kWh")      #3.3 [cent/MJ]
            ts2["rate_type"] = "gas"
        case _:
            raise ValueError("type tariff not among the available options.")

    #Output
    ts["tariff"] = ts2["tariff"]
    ts["rate_type"] = ts2["rate_type"]

    if return_energy_plan:
        return (ts, energy_plan)
    else:
        return ts

#-------------
def get_gas_rate(
        ts: pd.DataFrame,
        heater: GasHeaterInstantaneous,
        tariff_type: str = "gas",
        file_path: str = GAS_TARIFF_SAMPLE_FILE,
) -> pd.DataFrame:

    import json

    with open(file_path) as f:
        plan = json.load(f)
    
    #use pandas pd.cut
    rate_details = plan["charges"]["energy_charges"]["rate_details"]
    rates = []
    edges = [0,]
    for bin in rate_details:
        rates.append(bin["rate"])
        edges.append(bin["ceil"])

    nom_power = heater.nom_power.get_value("MJ/hr")
    flow_water = heater.flow_water.get_value("L/min")
    specific_energy = (nom_power / flow_water * CF("min", "hr")) #[MJ/L]

    hw_flow = ts["m_HWD"]
    STEP_h = ts.index.freq.n * CF("min", "hr")

    output = ts.copy()
    output["E_HWD"] = specific_energy * hw_flow * STEP_h         #[MJ]
    output["E_HWD_cum_day"] = output.groupby(output.index.date)['E_HWD'].cumsum()
    output["tariff"] = pd.cut(
        output["E_HWD_cum_day"],
        bins = edges, labels = rates, right = False
    ).astype("float")
    output["rate_type"] = tariff_type

    return output

#------------------------
# @lru_cache(maxsize=20)
def calculate_energy_cost(
        row: pd.Series,
        df_tm: pd.DataFrame = None,
        dnsp: str = "Ausgrid",
        ) -> float:

    name = row["name"]
    tariff_type = row["tariff_type"]
    has_solar = row["has_solar"]
    control_type = row["control_type"]
    control_load = row["control_load"]

    if df_tm is None:
        #Run thermal simulation. In the meantime, read from file
        GS = general.GeneralSetup()
        GS.household.tariff_type = tariff_type
        GS.household.control_type = control_type
        GS.household.control_load = control_load
        ts = GS.create_ts()
        GS.run_thermal_simulation(ts)

    else:
        out_all = df_tm.copy()
        STEP_h = 3. * CF("min","hr")         #Change it later
        heater_power = out_all["HeaterPower"] * CF("kJ/h", "kW")

    ts = get_import_rate(
        out_all,
        tariff_type, dnsp,
        return_energy_plan=False,
    )

    if has_solar:
        tz = 'Australia/Brisbane'
        solar_system = general.GeneralSetup().solar_system
        pv_power = solar_system.load_PV_generation(df = out_all, tz=tz,  unit="kW")

        imported_energy = np.where( pv_power < heater_power, heater_power - pv_power, 0 )
        energy_cost = (
            ts["tariff"] * imported_energy * STEP_h  
            ).sum()
        
    else:    
        energy_cost = ( ts["tariff"] * heater_power * STEP_h ).sum()

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

#--------------------
def test_get_import_rate():
    
    COLS = DEFINITIONS.TS_TYPES["economic"]

    GS = general.GeneralSetup()
    GS.household.DNSP = "Ausgrid"
    GS.household.tariff_type = "flat"
    ts = GS.create_ts_empty()
    (ts, energy_plan) = get_import_rate(ts,
                                        tariff_type = GS.household.tariff_type,
                                        dnsp = GS.household.DNSP,
                                        return_energy_plan = True,
                                        )
    print(ts)
    print(ts[COLS], energy_plan)
    #-------------------
    GS = general.GeneralSetup()
    GS.household.DNSP = "Ausgrid"
    GS.household.tariff_type = "tou"
    ts = GS.create_ts_empty()
    (ts, energy_plan) = get_import_rate(ts,
                                        tariff_type = GS.household.tariff_type,
                                        dnsp = GS.household.DNSP,
                                        return_energy_plan = True,
                                        )
    print(ts)
    print(ts[COLS], energy_plan)

    #-------------------
    GS = general.GeneralSetup()
    GS.household.DNSP = "Ausgrid"
    GS.household.tariff_type = "CL"
    GS.household.control_load = 1
    ts = GS.create_ts_empty()
    (ts, energy_plan) = get_import_rate(ts,
                                        tariff_type = GS.household.tariff_type,
                                        dnsp = GS.household.DNSP,
                                        control_load = GS.household.control_load,
                                        return_energy_plan = True,
                                        )
    print(ts)
    print(ts[COLS], energy_plan)
    return

#-------------------
def test_calculate_energy_cost():

    COLS = DEFINITIONS.TS_TYPES["economic"]

    GS = general.GeneralSetup()
    GS.household.DNSP = "Ausgrid"
    GS.household.tariff_type = "CL"
    GS.household.control_load = 1
    ts = GS.create_ts_empty()
    (ts, energy_plan) = get_import_rate(ts,
                                    tariff_type = GS.household.tariff_type,
                                    dnsp = GS.household.DNSP,
                                    control_load = GS.household.control_load,
                                    return_energy_plan = True,
                                    )
    print(ts)
    print(ts[COLS], energy_plan)
    
    return


#------------------------
def test_get_gas_rate():

    COLS = DEFINITIONS.TS_TYPES["economic"]
    GS = general.GeneralSetup()
    GS.DEWH = GasHeaterInstantaneous()
    GS.household.tariff_type = "gas"

    ts = GS.create_ts()

    output = get_gas_rate( ts, heater = GS.DEWH )
    energy_bill = (output["E_HWD"] * output["tariff"]).sum()
    print(output)
    print(energy_bill)

    return

#-------------
if __name__ == "__main__":

    test_get_gas_rate()

    # test_get_import_rate()

    # test_calculate_energy_cost()

    pass