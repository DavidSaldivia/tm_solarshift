import os
import pandas as pd
import matplotlib.pyplot as plt

from tm_solarshift.general import Simulation
from tm_solarshift.utils.units import Variable
from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary
from tm_solarshift.models.postprocessing import detailed_plots
from tm_solarshift.constants import DIRECTORY


def plot_temp_SOC(
        df_tm: pd.DataFrame,
        sim: Simulation,
        t_min: float = 0.,
        t_max: float = 120.,
        savefig: bool = False,
        showfig: bool = False,
        dir_results: str = "test",
        case: str = "test",
        ):
    df_tm_idx = pd.to_datetime(df_tm.index)
    fig, ax = plt.subplots(figsize=(9, 6))
    fs = 16
    xmax = t_max

    DEWH = sim.DEWH
    temp_min = 20.
    temp_max = DEWH.temp_max.get_value("degC")
    for i in range(1, DEWH.nodes + 1):
        lbl = f"Node{i}"
        ax.plot(df_tm["TIME"], df_tm[lbl], lw=2, label=lbl)
    ax.legend(loc=0, fontsize=fs - 2, bbox_to_anchor=(-0.1, 0.9))
    ax.grid()
    ax.set_xlim(0, xmax)
    ax.set_ylim(temp_min, temp_max + 5)
    ax.set_xlabel("Time of Simulation (hr)", fontsize=fs)
    ax.set_ylabel("Temperature (C)", fontsize=fs)
    ax.tick_params(axis="both", which="major", labelsize=fs - 2)

    ax2 = ax.twinx()
    ax2.plot(df_tm["TIME"], df_tm["SOC"],
             lw=3, ls="--", c="C3",
             label="SOC")
    ax2.legend(loc=1, fontsize=fs - 2)
    ax2.set_ylim(-0.05, 1.05)
    ax2.set_ylabel("State of Charge (-)", fontsize=fs)
    ax2.tick_params(axis="both", which="major", labelsize=fs - 2)

    if savefig:
        if not os.path.exists(dir_results):
            os.mkdir(dir_results)
        fig.savefig(
            os.path.join(dir_results, case + "_Temps_SOC.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close()
    pass


def plot_input(
        df_tm: pd.DataFrame,
        sim: Simulation,
        t_min: float = 0.,
        t_max: float = 120.,
        savefig: bool = False,
        showfig: bool = False,
        dir_results: str = "test",
        case: str = "test",
        ):
    df_tm_idx = pd.to_datetime(df_tm.index)
    fig, ax = plt.subplots(figsize=(9, 6))
    fs = 16
    xmax = t_max

    DEWH = sim.DEWH
    temp_min = 20.
    temp_max = DEWH.temp_max.get_value("degC")
    for i in range(1, DEWH.nodes + 1):
        lbl = f"Node{i}"
        ax.plot(df_tm["TIME"], df_tm[lbl], lw=2, label=lbl)
    ax.legend(loc=0, fontsize=fs - 2, bbox_to_anchor=(-0.1, 0.9))
    ax.grid()
    ax.set_xlim(0, xmax)
    ax.set_ylim(temp_min, temp_max + 5)
    ax.set_xlabel("Time of Simulation (hr)", fontsize=fs)
    ax.set_ylabel("Temperature (C)", fontsize=fs)
    ax.tick_params(axis="both", which="major", labelsize=fs - 2)

    ax2 = ax.twinx()
    ax2.plot(df_tm["TIME"], df_tm["SOC"],
             lw=3, ls="--", c="C3",
             label="SOC")
    ax2.legend(loc=1, fontsize=fs - 2)
    ax2.set_ylim(-0.05, 1.05)
    ax2.set_ylabel("State of Charge (-)", fontsize=fs)
    ax2.tick_params(axis="both", which="major", labelsize=fs - 2)

    if savefig:
        if not os.path.exists(dir_results):
            os.mkdir(dir_results)
        fig.savefig(
            os.path.join(dir_results, case + "_input.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close()
    pass

def main():
    sim = Simulation()
    sim.DEWH = SolarThermalElecAuxiliary()
    sim.time_params.STOP = Variable(720, "hr")
    sim.HWDInfo.profile_HWD = 1

    sim.run_simulation()
    df_tm = sim.out["df_tm"]


    plot_temp_SOC(df_tm=df_tm, sim=sim,
                  t_min=0.0, t_max=120.,
                  savefig=True, showfig=False,
                  )



    pass

if __name__ == "__main__":
    main()
    pass