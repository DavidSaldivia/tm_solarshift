import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from tm_solarshift.general import GeneralSetup
from tm_solarshift.constants import SIMULATIONS_IO
from tm_solarshift.utils.units import conversion_factor as CF
from tm_solarshift.utils.finance_old import (
    calculate_household_energy_cost,
    calculate_wholesale_energy_cost,
    financial_analysis,
)

TM_POSTPROC_OUTPUT = SIMULATIONS_IO.TM_POSTPROC_OUTPUT
ECON_POSTPROC_OUTPUT = SIMULATIONS_IO.ECON_POSTPROC_OUTPUT
FIN_POSTPROC_OUTPUT = SIMULATIONS_IO.FIN_POSTPROC_OUTPUT

POSTPROC_TYPES = ["TM", "ECON"]

#------------------------------
def annual_postproc(
        GS: GeneralSetup,
        ts: pd.DataFrame,
        out_all: pd.DataFrame,
        include: list[str] = POSTPROC_TYPES
        ) -> dict:

    out_overall_th = {}
    out_overall_econ = {}
    out_overall_fin = {}

    if "TM" in include:
        out_overall_th = thermal_postproc(GS, ts, out_all)

    if "ECON" in include:
        out_overall_econ = economics_postproc(GS, ts, out_all)

    return out_overall_th | out_overall_econ | out_overall_fin

#-------------------
def thermal_postproc(
        GS: GeneralSetup,
        ts: pd.DataFrame,
        out_all: pd.DataFrame
) -> dict[str, float]:
    
    STEP_h = GS.simulation.STEP.get_value("hr")
    DAYS = GS.simulation.DAYS.get_value("d")
    thermal_cap = GS.DEWH.thermal_cap.get_value("kWh")
    cp = GS.DEWH.fluid.cp.get_value("J/kg-K")

    heater_heat = out_all["HeaterHeat"]
    heater_power = out_all["HeaterPower"]
    tank_flowrate = out_all["Tank_FlowRate"]
    temp_top = out_all["TempTop"]
    temp_amb = out_all["T_amb"]
    temp_mains = out_all["T_mains"]
    hw_flowrate = out_all["HW_Flow"]
    SOC = out_all["SOC"]

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
        tank_flowrate * STEP_h * cp * (temp_top - temp_mains) * CF("J", "kWh")
    ).sum()

    E_losses_acum = heater_heat_acum - E_HWD_acum
    eta_stg = E_HWD_acum / heater_heat_acum
    cycles_day = heater_heat_acum / thermal_cap / DAYS

    # Risks_params
    SOC_avg = SOC.mean()
    SOC_min = SOC.min()
    (SOC_025, SOC_050) = SOC.quantile( [0.25, 0.50], interpolation="nearest", )
    t_SOC0 = (SOC <= 0.01).sum() * STEP_h

    out_overall_th = {key:None for key in TM_POSTPROC_OUTPUT}
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
def economics_postproc(
        GS: GeneralSetup,
        ts: pd.DataFrame,
        out_all: pd.DataFrame
) -> dict[str, float]:
    
    STEP_h = GS.simulation.STEP.get_value("hr")

    heater_power = out_all["HeaterPower"]
    heater_power_sum = heater_power.sum()
    if heater_power_sum <= 0.0:
        heater_power_sum = np.nan

    solar_ratio_potential = (
        heater_power[
            (heater_power.index.hour >= 8.75) & (heater_power.index.hour <= 17.01)
        ].sum()
        / heater_power_sum
    )
    solar_ratio_real = np.nan   #Not implemented yet. It should calculate as

    emissions_total = (
        (heater_power * CF("kJ/h", "MW")) * STEP_h
        * ts["Intensity_Index"]
        ).sum()
    emissions_marginal = (
        (heater_power * CF("kJ/h", "MW")) * STEP_h
        * ts["Marginal_Index"]
        ).sum()
    
    annual_hw_household_cost = calculate_household_energy_cost(
        GS, ts, out_all
    )
    annual_hw_retailer_cost = calculate_wholesale_energy_cost(
        GS, ts, out_all
    )

    out_overall_econ = {key:None for key in ECON_POSTPROC_OUTPUT}
    out_overall_econ["annual_emissions_total"] = emissions_total
    out_overall_econ["annual_emissions_marginal"] = emissions_marginal
    out_overall_econ["solar_ratio_potential"] = solar_ratio_potential
    out_overall_econ["solar_ratio_real"] = solar_ratio_real
    out_overall_econ["annual_hw_household_cost"] = annual_hw_household_cost
    out_overall_econ["annual_hw_retailer_cost"] = annual_hw_retailer_cost
    return out_overall_econ

#-----------------
def financial_postproc(
    GS: GeneralSetup,
    ts: pd.DataFrame,
    out_all: pd.DataFrame,
    out_overall_th: dict = None,
    out_overall_econ: dict = None,
) -> dict:

    out_overall_fin = financial_analysis(
        GS, ts, out_all, out_overall_th, out_overall_econ
    )
    return out_overall_fin

#------------------------------
def events_simulation(
        GS: GeneralSetup, 
        ts: pd.DataFrame,
        out_data: pd.DataFrame,
    ) -> pd.DataFrame:
    
    STEP_h = GS.simulation.STEP.get_value("hr")
    cp = GS.DEWH.fluid.cp.get_value("J/kg-K")

    df = ts.groupby(ts.index.date)[
        ["m_HWD_day", "Temp_Amb", "Temp_Mains"]
    ].mean()
    idx = np.unique(ts.index.date)
    df_aux = out_data.groupby(out_data.index.date)
    df.loc[df.index == idx, "SOC_end"] = df_aux.tail(1)["SOC"].values
    df.loc[df.index == idx,"TempTh_end"] = df_aux.tail(1)["TempBottom"].values
    df.loc[df.index == idx,"EL_end"] = df_aux.tail(1)["E_Level"].values

    E_HWD_acum = (
        (out_data["Tank_FlowRate"] * STEP_h * cp
         * (out_data["TempTop"] - out_data["T_mains"])
         * CF("J", "kWh")
         ).groupby(out_data.index.date)
        .sum()
    )
    df.loc[df.index == idx, "E_HWD_day"] = E_HWD_acum
    df.loc[df.index == idx, "SOC_ini"] = df_aux.head(1)["SOC"].values
    return df

#------------------------------
def detailed_plots(
    GS: GeneralSetup, 
    out_all: pd.DataFrame,
    fldr_results_detailed: str = None,
    case: str = None,
    save_plots_detailed: bool = False,
    tmax: float = 72.0,
    showfig: bool = True,
):

    ### Temperatures and SOC
    fig, ax = plt.subplots(figsize=(9, 6))
    fs = 16
    xmax = tmax

    DEWH = GS.DEWH
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
        (out_all.index.dayofyear - 1) * CF("d", "hr")
        + out_all.index.hour
        + out_all.index.minute * CF("min", "hr")
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
    
    GS = GeneralSetup()
    GS.solar_system = None
    ts = GS.create_ts()
    
    (out_all, out_overall) = GS.run_thermal_simulation(ts, verbose=True)
    out_overall2 = annual_postproc(GS, ts, out_all)

    print(out_overall)
    print(out_overall2)

    return None

#-------------
if __name__ == "__main__":
    main()

    pass