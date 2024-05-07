import os
import matplotlib.pyplot as plt

import tm_solarshift.general as general
from tm_solarshift.constants import DIRECTORY
from tm_solarshift.general import GeneralSetup
from tm_solarshift.devices import (Variable, ResistiveSingle)
from tm_solarshift.models import (tank_0D, trnsys)


#------------------------------
def detailed_plot_0D_based(
    GS,
    out_all,
    fldr_results_detailed=None,
    case=None,
    save_plots_detailed=False,
    tmax=72.0,
    showfig: bool = True,
) -> None:
    
    # Stored Energy and SOC
    fig, ax = plt.subplots(figsize=(9, 6))
    fs = 16
    ax2 = ax.twinx()
    aux = (
        (out_all.index.dayofyear - 1) * 24
        + out_all.index.hour
        + out_all.index.minute / 60.0
    )

    ax2.plot(aux, out_all.CS, label="Control Sig", c="C2", ls="-", lw=2)
    ax2.plot(aux, out_all.SOC, c="C3", ls="-", lw=2, label="SOC")
    ax.grid()
    ax.legend(loc=2)
    ax.set_xlim(0, tmax)
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

#------------------------------
def detailed_plot_comparison(
    out_all_trnsys,
    out_all_0D,
    fldr_results_detailed=None,
    case=None,
    save_plots_detailed=False,
    tmax=72.0,
    showfig: bool = True,
) -> None:
    
    # SOC
    fig, ax = plt.subplots(figsize=(9, 6))
    fs = 16
    ax2 = ax.twinx()
    aux = (
        (out_all_trnsys.index.dayofyear - 1) * 24
        + out_all_trnsys.index.hour
        + out_all_trnsys.index.minute / 60.0
    )

    # ax.plot( aux, out_all.PVPower/W_TO_kJh, label='E_PV', c='C0',ls='-',lw=2)
    ax.plot(aux, out_all_trnsys.E_HWD, label="E_HWD", c="C1", ls="-", lw=2)
    ax2.plot(aux, out_all_trnsys.C_Load, label="Control Sig", c="C2", ls="-", lw=2)
    ax2.plot(aux, out_all_trnsys.SOC, c="C3", ls="-", lw=2, label="SOC_TRNSYS")
    ax2.plot(aux, out_all_0D.SOC, c="C4", ls="-", lw=2, label="SOC_0D")
    # ax2.plot(aux, out_all_0D.theta_t, c="C5", ls="-", lw=2, label="theta_t_0D")

    ax.grid()
    ax.legend(loc=2)
    ax.set_xlim(0, tmax)
    ax2.legend(loc=1)
    ax2.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Time of Simulation (hr)", fontsize=fs)
    ax.set_ylabel("Power (W) profiles", fontsize=fs)
    ax2.set_ylabel("State of Charge (SOC)", fontsize=fs)
    ax.tick_params(axis="both", which="major", labelsize=fs - 2)
    ax2.tick_params(axis="both", which="major", labelsize=fs - 2)
    if save_plots_detailed:
        fig.savefig(
            os.path.join(fldr_results_detailed, case + "_SOC.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close()

    # Temperature Average
    fig, ax = plt.subplots(figsize=(9, 6))
    fs = 16
    ax2 = ax.twinx()
    aux = (
        (out_all_trnsys.index.dayofyear - 1) * 24
        + out_all_trnsys.index.hour
        + out_all_trnsys.index.minute / 60.0
    )
    # ax.plot( aux, out_all.PVPower/W_TO_kJh, label='E_PV', c='C0',ls='-',lw=2)
    ax.plot(aux, out_all_trnsys.E_HWD, label="E_HWD", c="C1", ls="-", lw=2)
    ax2.plot(aux, out_all_trnsys.C_Load, label="Control Sig", c="C2", ls="-", lw=2)
    ax2.plot(aux, out_all_trnsys.T_avg, c="C3", ls="-", lw=2, label="T_avg_TRNSYS")
    ax2.plot(aux, out_all_0D.temp_avg, c="C4", ls="-", lw=2, label="T_avg_0D")

    ax.grid()
    ax.legend(loc=2)
    ax.set_xlim(0, tmax)
    ax2.legend(loc=1)
    ax2.set_ylim(10, 65)
    ax.set_xlabel("Time of Simulation (hr)", fontsize=fs)
    ax.set_ylabel("Power (W) profiles", fontsize=fs)
    ax2.set_ylabel("Temperature (degC)", fontsize=fs)
    ax.tick_params(axis="both", which="major", labelsize=fs - 2)
    ax2.tick_params(axis="both", which="major", labelsize=fs - 2)
    if save_plots_detailed:
        fig.savefig(
            os.path.join(fldr_results_detailed, case + "_Temperature.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close()


    return

#------------------------
def main():
    
    GS = GeneralSetup()
    GS.DEWH = ResistiveSingle()
    GS.simulation.STOP = Variable(100., "hr")
    GS.household.control_load = -1
    GS.household.control_random_on = False

    if False:
        output_state = tank_0D.SOC_based(
            GS.DEWH,
            verbose=True,)
        plot_main_vars(output_state)
        print(output_state)
    
    ts = general.load_timeseries_all(GS)

    fldr_results_detailed = os.path.join(
        DIRECTORY.DIR_RESULTS, 'comparison_trnsys_0D',
    )

    if True:
        out_all_trnsys = trnsys.run_simulation(
            GS, ts, verbose=True
            )
        trnsys.detailed_plots(
            GS,
            out_all_trnsys,
            showfig=True,
            case="TRNSYS",
            fldr_results_detailed = fldr_results_detailed,
            save_plots_detailed = True
            )
        print()

    if True:
        out_all_0D = tank_0D.SOC_profiles(GS.DEWH, ts, verbose=True)
        print(out_all_0D)
        
        detailed_plot_comparison(
            out_all_trnsys,
            out_all_0D,
            case="Comparison",
            fldr_results_detailed = fldr_results_detailed,
            save_plots_detailed = True
            )

    return

#------------------------
if __name__=="__main__":
    main()