from __future__ import annotations
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Any, TYPE_CHECKING, TypeAlias

from tm_solarshift.general import Simulation
from tm_solarshift.constants import SIMULATIONS_IO
from tm_solarshift.utils.units import (conversion_factor as CF)
from tm_solarshift.analysis.finance import (
    calculate_household_energy_cost,
    calculate_wholesale_energy_cost,
)

if TYPE_CHECKING:
    from tm_solarshift.general import Simulation
    from tm_solarshift.models.resistive_single import ResistiveSingle
    from tm_solarshift.models.heat_pump import HeatPump
    from tm_solarshift.models.gas_heater import GasHeaterStorage
    from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary
    Heater: TypeAlias = ResistiveSingle | HeatPump | GasHeaterStorage | SolarThermalElecAuxiliary


OUTPUT_ANALYSIS_TM = SIMULATIONS_IO.OUTPUT_ANALYSIS_TM
OUTPUT_ANALYSIS_ECON = SIMULATIONS_IO.OUTPUT_ANALYSIS_ECON
OUTPUT_ANALYSIS_FIN = SIMULATIONS_IO.OUTPUT_ANALYSIS_FIN

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

    out_overall_th = {key:np.nan for key in OUTPUT_ANALYSIS_TM}
    out_overall_th["heater_heat_acum"] = heater_heat_acum
    out_overall_th["heater_power_acum"] = heater_power_acum
    out_overall_th["heater_perf_avg"] = heater_perf_avg
    out_overall_th["E_HWD_acum"] = E_HWD_acum
    out_overall_th["E_losses_acum"] = E_losses_acum
    out_overall_th["eta_stg"] = eta_stg
    out_overall_th["cycles_day"] = cycles_day
    out_overall_th["SOC_avg"] = SOC_avg
    out_overall_th["SOC_min"] = SOC_min
    out_overall_th["SOC_025"] = SOC_025
    out_overall_th["SOC_050"] = SOC_050
    out_overall_th["t_SOC0"] = t_SOC0

    return out_overall_th

#------------------
def economics_analysis(
        sim: Simulation,
        ts: pd.DataFrame,
        df_tm: pd.DataFrame
) -> dict[str, float]:
    
    STEP_h = sim.time_params.STEP.get_value("hr")
    DEWH = sim.DEWH

    hour = pd.to_datetime(df_tm.index).hour.astype(float)

    if DEWH.label == "solar_thermal":
        heater_power = df_tm["heater_power_no_solar"]
    else:
        heater_power = df_tm["heater_power"]
    heater_power_sum = heater_power.sum()
    if heater_power_sum <= 0.0:
        heater_power_sum = np.nan
    
    heater_heat_acum = ( df_tm["heater_heat"] * STEP_h  * CF("kJ/h", "kW") ).sum()

    solar_ratio_potential = (
        heater_power[
            (hour >= 8.75) & (hour <= 17.01)
        ].sum()
        / heater_power_sum
    )
    solar_ratio_real = np.nan   #Not implemented yet. It should calculate it with the pv results

    if DEWH.label in ["resistive", "heat_pump", "solar_thermal"]:
        emissions_total = (
            (heater_power * CF("kJ/h", "MW")) * STEP_h * ts["intensity_index"]
            ).sum()
        emissions_marginal = (
            (heater_power * CF("kJ/h", "MW")) * STEP_h * ts["marginal_index"]
            ).sum()
        
    elif DEWH.label in ["gas_instant", "gas_storage"]:
        kgCO2_TO_kgCH4 = 44. / 16.                          #assuming pure methane for gas
        heat_value = DEWH.heat_value.get_value("MJ/kg_gas")
        eta = sim.DEWH.eta.get_value("-")
        sp_emissions = (kgCO2_TO_kgCH4 / (heat_value * CF("MJ", "kWh")) / eta ) #[kg_CO2/kWh_thermal]
        emissions_total = heater_heat_acum * sp_emissions * CF("kg", "ton")    #[tonCO2_annual]
        emissions_marginal = emissions_total

    
    annual_hw_household_cost = calculate_household_energy_cost(
        sim, ts, df_tm,
    )
    annual_hw_retailer_cost = calculate_wholesale_energy_cost(
        sim, ts, df_tm
    )

    out_overall_econ = {key:np.nan for key in OUTPUT_ANALYSIS_ECON}
    out_overall_econ["annual_emissions_total"] = emissions_total
    out_overall_econ["annual_emissions_marginal"] = emissions_marginal
    out_overall_econ["solar_ratio_potential"] = solar_ratio_potential
    out_overall_econ["solar_ratio_real"] = solar_ratio_real
    out_overall_econ["annual_hw_household_cost"] = annual_hw_household_cost
    out_overall_econ["annual_hw_retailer_cost"] = annual_hw_retailer_cost
    return out_overall_econ

#-------------------
# def thermal_postproc(
#         sim: Simulation,
#         ts: pd.DataFrame,
#         out_all: pd.DataFrame
# ) -> dict[str, float]:
    
#     STEP_h = sim.time_params.STEP.get_value("hr")
#     DAYS = sim.time_params.DAYS.get_value("d")
#     thermal_cap = sim.DEWH.thermal_cap.get_value("kWh")
#     cp = sim.DEWH.fluid.cp.get_value("J/kg-K")

#     heater_heat = out_all["heater_heat"]
#     heater_power = out_all["heater_power"]
#     tank_flowrate = out_all["tank_flow_rate"]
#     temp_out = out_all["tank_temp_out"]
#     temp_mains = out_all["temp_mains"]
#     SOC = out_all["SOC"]

#     # Calculating overall parameters
#     # Accumulated energy values (all in [kWh])
#     heater_heat_acum = ( heater_heat * STEP_h  * CF("kJ/h", "kW") ).sum()
#     heater_power_acum = ( heater_power * STEP_h  * CF("kJ/h", "kW") ).sum()
#     if heater_heat_acum <= 0:
#         heater_heat_acum = np.nan
#     if heater_power_acum <= 0:
#         heater_power_acum = np.nan

#     heater_perf_avg = heater_heat_acum / heater_power_acum

#     E_HWD_acum = (
#         tank_flowrate * STEP_h * cp * (temp_out - temp_mains) * CF("J", "kWh")
#     ).sum()

#     E_losses_acum = heater_heat_acum - E_HWD_acum
#     eta_stg = E_HWD_acum / heater_heat_acum
#     cycles_day = heater_heat_acum / thermal_cap / DAYS

#     # Risks_params
#     SOC_avg = SOC.mean()
#     SOC_min = SOC.min()
#     (SOC_025, SOC_050) = SOC.quantile( [0.25, 0.50], interpolation="nearest", )
#     t_SOC0 = (SOC <= 0.01).sum() * STEP_h

#     out_overall_th = {key:np.nan for key in OUTPUT_ANALYSIS_TM}
#     out_overall_th["heater_heat_acum"] = heater_heat_acum
#     out_overall_th["heater_power_acum"] = heater_power_acum
#     out_overall_th["heater_perf_avg"] = heater_perf_avg
#     out_overall_th["E_HWD_acum"] = E_HWD_acum
#     out_overall_th["E_losses_acum"] = E_losses_acum
#     out_overall_th["eta_stg"] = eta_stg
#     out_overall_th["cycles_day"] = cycles_day
#     out_overall_th["SOC_avg"] = SOC_avg
#     out_overall_th["SOC_min"] = SOC_min
#     out_overall_th["SOC_025"] = SOC_025
#     out_overall_th["SOC_050"] = SOC_050
#     out_overall_th["t_SOC0"] = t_SOC0

#     return out_overall_th

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
    sim.solar_system = None
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