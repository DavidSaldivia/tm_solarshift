from __future__ import annotations
import json
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Any, TYPE_CHECKING, TypeAlias

from tm_solarshift.general import Simulation
from tm_solarshift.constants import (DIRECTORY, SIMULATIONS_IO)
from tm_solarshift.utils.units import (conversion_factor as CF)
from tm_solarshift.analysis.finance import (
    calculate_household_energy_cost,
    calculate_wholesale_energy_cost,
)

if TYPE_CHECKING:
    from tm_solarshift.general import Simulation
    # from tm_solarshift.models.dewh import ResistiveSingle, HeatPump
    # from tm_solarshift.models.gas_heater import GasHeaterStorage
    # from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary
    # Heater: TypeAlias = ResistiveSingle | HeatPump | GasHeaterStorage | SolarThermalElecAuxiliary


OUTPUT_ANALYSIS_TM = SIMULATIONS_IO.OUTPUT_ANALYSIS_TM
OUTPUT_ANALYSIS_ECON = SIMULATIONS_IO.OUTPUT_ANALYSIS_ECON
OUTPUT_ANALYSIS_FIN = SIMULATIONS_IO.OUTPUT_ANALYSIS_FIN
DIR_TARIFFS = DIRECTORY.DIR_DATA["tariffs"]
POSTPROC_TYPES = ["TM", "ECON"]

#------------------------------
def annual_postproc(
        sim: Simulation,
        ts: pd.DataFrame,
        out_all: pd.DataFrame,
        include: list[str] = POSTPROC_TYPES
        ) -> dict:

    out_overall_th = {}
    out_overall_econ = {}

    if "TM" in include:
        out_overall_th = thermal_analysis(sim, ts, out_all)

    if "ECON" in include:
        out_overall_econ = economics_analysis(sim, ts, out_all)

    return out_overall_th | out_overall_econ

#-------------------
def thermal_analysis(
        sim: Simulation,
        ts: pd.DataFrame,
        df_tm: pd.DataFrame
) -> dict[str, float]:
    
    from tm_solarshift.models.gas_heater import GasHeaterInstantaneous
    
    DEWH = sim.DEWH
    if isinstance(DEWH, GasHeaterInstantaneous):
        overall_th = DEWH.postproc(df_tm)
        return overall_th

    STEP_h = sim.time_params.STEP.get_value("hr")
    DAYS = sim.time_params.DAYS.get_value("d")
    thermal_cap = sim.DEWH.thermal_cap.get_value("kWh")
    cp = sim.DEWH.fluid.cp.get_value("J/kg-K")

    heater_heat = df_tm["heater_heat"]
    heater_power = df_tm["heater_power"]
    tank_flowrate = df_tm["tank_flow_rate"]
    temp_out = df_tm["tank_temp_out"]
    temp_mains = df_tm["temp_mains"]
    SOC = df_tm["SOC"]

    # Calculating overall parameters
    # Accumulated energy values (all in [kWh])
    heater_heat_acum = ( heater_heat * STEP_h  * CF("kJ/h", "kW") ).sum()
    heater_power_acum = ( heater_power * STEP_h  * CF("kJ/h", "kW") ).sum()

    if heater_heat_acum <= 0:
        heater_heat_acum = np.nan
    if heater_power_acum <= 0:
        heater_power_acum = np.nan

    heater_perf_avg = heater_heat_acum / heater_power_acum

    E_HWD_acum = (
        tank_flowrate * STEP_h * cp * (temp_out - temp_mains) * CF("J", "kWh")
    ).sum()

    E_losses_acum = heater_heat_acum - E_HWD_acum
    eta_stg = E_HWD_acum / heater_heat_acum
    cycles_day = heater_heat_acum / thermal_cap / DAYS

    # Risks_params
    SOC_avg = SOC.mean()
    SOC_min = SOC.min()
    (SOC_025, SOC_050) = SOC.quantile( [0.25, 0.50], interpolation="nearest", )
    t_SOC0 = (SOC <= 0.01).sum() * STEP_h

    overall_th = {key:np.nan for key in OUTPUT_ANALYSIS_TM}
    overall_th["heater_heat_acum"] = heater_heat_acum
    overall_th["heater_power_acum"] = heater_power_acum
    overall_th["heater_perf_avg"] = heater_perf_avg
    overall_th["E_HWD_acum"] = E_HWD_acum
    overall_th["E_losses_acum"] = E_losses_acum
    overall_th["eta_stg"] = eta_stg
    overall_th["cycles_day"] = cycles_day
    overall_th["SOC_avg"] = SOC_avg
    overall_th["SOC_min"] = SOC_min
    overall_th["SOC_025"] = SOC_025
    overall_th["SOC_050"] = SOC_050
    overall_th["t_SOC0"] = t_SOC0

    return overall_th


def economics_analysis(sim: Simulation) -> dict[str, float]:
    
    #retrieving data
    location = sim.household.location
    DEWH = sim.DEWH
    df_tm = sim.out["df_tm"]
    ts_index = sim.time_params.idx
    STEP_h = sim.time_params.STEP.get_value("hr")
    YEAR = sim.time_params.YEAR.get_value("-")

    # creating output df
    COLS_ECON = ["heater_power", "pv_power", "imported_power", "exported_pv", "pv_to_hw"]
    df_econ = pd.DataFrame(index=ts_index, columns=COLS_ECON)        # all cols in [kWh]
    df_econ["pv_power"] = sim.out["df_pv"]["pv_power"]
    df_econ["heater_power"] = df_tm["heater_power"] * CF("kJ/h", "kW")
    overall_tm = sim.out["overall_tm"]
    heater_heat_acum = overall_tm["heater_heat_acum"]
    heater_power_acum = overall_tm["heater_power_acum"]

    # solar ratio and imported energy
    hour = pd.to_datetime(df_tm.index).hour.astype(float)
    solar_ratio_potential = (
        df_econ["heater_power"][ (hour >= 6.75) & (hour <= 17.01) ].sum() * STEP_h
        / heater_power_acum
    )

    if DEWH.label == "solar_thermal":
        df_econ["imported_power"] = df_econ["heater_power"]
        df_econ["exported_pv"] = 0.
        df_econ["pv_to_hw"] = 0.

        df_econ["solar_power"] = df_tm["heater_power_stc"] * CF("kJ/hr", "kW")
        solar_ratio_real = df_econ["imported_power"].sum() / df_econ["solar_power"].sum()
        imported_power_acum = df_econ["imported_power"].sum() * STEP_h     #[kWh]
        exported_pv_acum = 0.
        pv_to_hw_acum = 0.
        
    else:
        df_econ["imported_power"] = np.where(
            df_econ["heater_power"] > df_econ["pv_power"],
            df_econ["heater_power"] - df_econ["pv_power"],
            0.0
        )
        df_econ["exported_pv"] = np.where(
            df_econ["pv_power"] > df_econ["heater_power"],
            df_econ["pv_power"] - df_econ["heater_power"],
            0.0
        )
        df_econ["pv_to_hw"] = np.where(
            df_econ["pv_power"] < df_econ["heater_power"],
            df_econ["pv_power"],
            df_econ["heater_power"]
        )
        imported_power_acum = df_econ["imported_power"].sum() * STEP_h     #[kWh]
        exported_pv_acum = df_econ["exported_pv"].sum() * STEP_h           #[kWh]
        pv_to_hw_acum = df_econ["pv_to_hw"].sum() * STEP_h                 #[kWh]
        solar_ratio_real = pv_to_hw_acum / heater_power_acum
    
    print(df_econ.groupby(ts_index.hour).sum() * STEP_h)
    print(df_econ.groupby(ts_index.month).sum() * STEP_h)

    # emissions
    from tm_solarshift.timeseries import market
    from tm_solarshift.models.dewh import (ResistiveSingle, HeatPump)
    from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary
    from tm_solarshift.models.gas_heater import (GasHeaterInstantaneous, GasHeaterStorage)
    ts_emi = pd.DataFrame(index=ts_index)
    ts_emi = market.load_emission_index_year(
        ts_emi, index_type= 'total', location = location, year = YEAR,
    )
    ts_emi = market.load_emission_index_year(
        ts_emi, index_type= 'marginal', location = location, year = YEAR,
    )
    if isinstance(DEWH, ResistiveSingle | HeatPump | SolarThermalElecAuxiliary):
        emissions_total = (
            (df_econ["heater_power"] * CF("kW", "MW")) * STEP_h * ts_emi["intensity_index"]
            ).sum()
        emissions_marginal = (
            (df_econ["heater_power"] * CF("kW", "MW")) * STEP_h * ts_emi["marginal_index"]
            ).sum()
    if isinstance(DEWH, GasHeaterInstantaneous | GasHeaterStorage):
        heater_heat_acum = ( df_tm["heater_heat"] * STEP_h  * CF("kJ/h", "kW") ).sum()
        kgCO2_TO_kgCH4 = 44. / 16.                          #assuming pure methane for gas
        heat_value = DEWH.heat_value.get_value("MJ/kg_gas")
        eta = sim.DEWH.eta.get_value("-")
        sp_emissions = (kgCO2_TO_kgCH4 / (heat_value * CF("MJ", "kWh")) / eta ) #[kg_CO2/kWh_thermal]
        emissions_total = heater_heat_acum * sp_emissions * CF("kg", "ton")    #[tonCO2_annual]
        emissions_marginal = emissions_total
    
    # energy costs
    annual_hw_household_cost = calculate_household_energy_cost(sim, df_econ["imported_power"])
    annual_hw_wholesale_cost = calculate_wholesale_energy_cost(sim, df_econ["imported_power"])
    annual_fit_opp_cost = calculate_fit_opp_cost(sim, df_econ["pv_to_hw"])
    annual_fit_revenue = calculate_fit_revenue(sim, df_econ["exported_pv"])

    #output
    # overall_econ = {key:np.nan for key in OUTPUT_ANALYSIS_ECON}
    overall_econ = {}
    overall_econ["annual_hw_household_cost"] = annual_hw_household_cost
    overall_econ["annual_hw_wholesale_cost"] = annual_hw_wholesale_cost
    overall_econ["annual_emissions_total"] = emissions_total
    overall_econ["annual_emissions_marginal"] = emissions_marginal
    overall_econ["solar_ratio_potential"] = solar_ratio_potential
    overall_econ["solar_ratio_real"] = solar_ratio_real
    overall_econ["pv_to_hw"] = pv_to_hw_acum
    overall_econ["imported_power"] = imported_power_acum
    overall_econ["exported_pv"] = exported_pv_acum
    overall_econ["annual_fit_opp_cost"] = annual_fit_opp_cost
    overall_econ["annual_fit_revenue"] = annual_fit_revenue
    
    # for (k,v) in overall_econ.items():
    #     print(f"{k}: {v:.4f}")
    return overall_econ



def calculate_fit_opp_cost(
        sim: Simulation,
        pv_to_hw: pd.Series,
) -> float:
    
    STEP_h = sim.time_params.STEP.get_value("hr")
    dnsp = sim.household.DNSP
    tariff_type = sim.household.tariff_type
    control_type = sim.household.control_type

    if tariff_type == "gas":
        return 0.

    if tariff_type == "CL":
        tariff_type = control_type if (control_type != "diverter") else "CL1"
    file_path = os.path.join(DIR_TARIFFS, f"{dnsp.lower()}_{tariff_type}_plan.json")
    with open(file_path) as f:
        plan = json.load(f)
    tariff_rate = None
    for charge in plan["charges"]["energy_charges"]:
        if charge["tariff_type"] == "solar_feed_in":
            tariff_rate = charge["rate_details"][0]["rate"]
    
    #if not there, then checking the flat tariff rate for the same DNSP
    if tariff_rate is None:
        file_path = os.path.join(DIR_TARIFFS, f"{dnsp.lower()}_flat_plan.json")
        with open(file_path) as f:
            plan = json.load(f)
        tariff_rate = None
        for charge in plan["charges"]["energy_charges"]:
            if charge["tariff_type"] == "solar_feed_in":
                tariff_rate = charge["rate_details"][0]["rate"]
    #TODO check if this is right

    fit_opp_cost = pv_to_hw.sum() * tariff_rate * STEP_h
    return fit_opp_cost


def calculate_fit_revenue(
        sim: Simulation,
        exported_pv: pd.Series,
) -> float:
    
    STEP_h = sim.time_params.STEP.get_value("hr")
    dnsp = sim.household.DNSP
    tariff_type = sim.household.tariff_type
    control_type = sim.household.control_type
    if tariff_type == "CL":
        tariff_type = control_type if (control_type != "diverter") else "CL1"
    if tariff_type == "gas":
        tariff_type = "flat"
    file_path = os.path.join(DIR_TARIFFS, f"{dnsp.lower()}_{tariff_type}_plan.json")
    with open(file_path) as f:
        plan = json.load(f)
    tariff_rate = None
    for charge in plan["charges"]["energy_charges"]:
        if charge["tariff_type"] == "solar_feed_in":
            tariff_rate = charge["rate_details"][0]["rate"]
    
    #if not there, then checking the flat tariff rate for the same DNSP
    if tariff_rate is None:
        file_path = os.path.join(DIR_TARIFFS, f"{dnsp.lower()}_flat_plan.json")
        with open(file_path) as f:
            plan = json.load(f)
        tariff_rate = None
        for charge in plan["charges"]["energy_charges"]:
            if charge["tariff_type"] == "solar_feed_in":
                tariff_rate = charge["rate_details"][0]["rate"]
    #TODO check if this is right

    fit_opp_cost = exported_pv.sum() * tariff_rate * STEP_h
    return fit_opp_cost

#------------------------------
def events_simulation(
        sim: Simulation, 
        ts: pd.DataFrame,
        out_data: pd.DataFrame,
    ) -> pd.DataFrame:
    
    STEP_h = sim.time_params.STEP.get_value("hr")
    cp = sim.DEWH.fluid.cp.get_value("J/kg-K")

    idx = pd.to_datetime(ts.index)
    df = ts.groupby(idx.date)[
        ["m_HWD_day", "temp_amb", "temp_mains"]
    ].mean()
    idx = np.unique(idx.date)
    out_data_idx = pd.to_datetime(out_data.index)
    df_aux = out_data.groupby(out_data_idx.date)
    df.loc[df.index == idx, "SOC_end"] = df_aux.tail(1)["SOC"].values
    df.loc[df.index == idx,"temp_tstat_end"] = df_aux.tail(1)["TempBottom"].values
    df.loc[df.index == idx,"EL_end"] = df_aux.tail(1)["E_Level"].values

    E_HWD_acum = (
        (out_data["tank_flow_rate"] * STEP_h * cp
         * (out_data["temp_top"] - out_data["temp_mains"])
         * CF("J", "kWh")
         ).groupby(out_data_idx.date)
        .sum()
    )
    df.loc[df.index == idx, "E_HWD_day"] = E_HWD_acum
    df.loc[df.index == idx, "SOC_ini"] = df_aux.head(1)["SOC"].values
    return df

#------------------------------
def detailed_plots(
    sim: Simulation, 
    out_all: pd.DataFrame,
    fldr_results_detailed: str = "",
    case: str = "",
    save_plots_detailed: bool = False,
    tmax: float = 72.0,
    showfig: bool = True,
):

    out_all_idx = pd.to_datetime(out_all.index)
    ### Temperatures and SOC
    fig, ax = plt.subplots(figsize=(9, 6))
    fs = 16
    xmax = tmax

    DEWH = sim.DEWH
    temp_min = 20.
    temp_max = DEWH.temp_max.get_value("degC")

    for i in range(1, DEWH.nodes + 1):
        lbl = f"Node{i}"
        ax.plot(out_all.TIME, out_all[lbl], lw=2, label=lbl)
    ax.legend(loc=0, fontsize=fs - 2, bbox_to_anchor=(-0.1, 0.9))
    ax.grid()
    ax.set_xlim(0, xmax)
    ax.set_ylim(temp_min, temp_max + 5)
    ax.set_xlabel("Time of Simulation (hr)", fontsize=fs)
    ax.set_ylabel("Temperature (C)", fontsize=fs)
    ax.tick_params(axis="both", which="major", labelsize=fs - 2)

    ax2 = ax.twinx()
    ax2.plot(out_all["TIME"], out_all["SOC"],
             lw=3, ls="--", c="C3",
             label="SOC")
    ax2.legend(loc=1, fontsize=fs - 2)
    ax2.set_ylim(-0.05, 1.05)
    ax2.set_ylabel("State of Charge (-)", fontsize=fs)
    ax2.tick_params(axis="both", which="major", labelsize=fs - 2)

    if save_plots_detailed:
        if not os.path.exists(fldr_results_detailed):
            os.mkdir(fldr_results_detailed)
        fig.savefig(
            os.path.join(fldr_results_detailed, case + "_Temps_SOC.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close()
    
    # Stored Energy and SOC
    fig, ax = plt.subplots(figsize=(9, 6))
    fs = 16
    ax2 = ax.twinx()
    aux = (
        (out_all_idx.dayofyear - 1) * CF("d", "hr")
        + out_all_idx.hour
        + out_all_idx.minute * CF("min", "hr")
    )

    # ax.plot( aux, out_all.PVPower/W_TO_kJh, label='E_PV', c='C0',ls='-',lw=2)
    ax.plot(aux, out_all.E_HWD, label="E_HWD", c="C1", ls="-", lw=2)
    ax2.plot(aux, out_all.C_Load, label="Control Sig", c="C2", ls="-", lw=2)
    ax2.plot(aux, out_all.SOC, c="C3", ls="-", lw=2, label="SOC")
    ax.grid()
    ax.legend(loc=2)
    ax.set_xlim(0, xmax)
    ax2.legend(loc=1)
    ax2.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Time of Simulation (hr)", fontsize=fs)
    ax.set_ylabel("Power (W) profiles", fontsize=fs)
    ax2.set_ylabel("State of Charge (SOC)", fontsize=fs)
    ax.tick_params(axis="both", which="major", labelsize=fs - 2)
    ax2.tick_params(axis="both", which="major", labelsize=fs - 2)
    if save_plots_detailed:
        fig.savefig(
            os.path.join(fldr_results_detailed, case + "_Energy.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close()
    return

#-------------
def main():
    
    sim = Simulation()
    sim.pv_system = None
    ts = sim.create_ts()
    
    (out_all, out_overall) = sim.run_thermal_simulation(ts, verbose=True)
    out_overall2 = annual_postproc(sim, ts, out_all)

    print(out_overall)
    print(out_overall2)

    return None

#-------------
if __name__ == "__main__":
    main()

    pass