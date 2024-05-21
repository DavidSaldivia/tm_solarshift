# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 15:20:46 2023

@author: z5158936
"""

import time
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from sklearn import linear_model

from typing import List, Dict, Union

from tm_solarshift.constants import ( DIRECTORY, SIMULATIONS_IO)
from tm_solarshift.general import Simulation
from tm_solarshift.utils.units import Variable
from tm_solarshift.models import (trnsys, postprocessing)

PROFILES_TYPES = SIMULATIONS_IO.TS_TYPES
TS_COLUMNS_ALL = SIMULATIONS_IO.TS_COLUMNS_ALL
WEATHER_TYPES = [
    'day_constant', 
    'meteonorm_random', 
    'meteonorm_month', 
    'meteonorm_date'
    ]
DIR_DATA = DIRECTORY.DIR_DATA
DIR_PROJECT = os.path.join(DIRECTORY.DIR_PROJECTS,os.path.dirname(__file__))
DIR_RESULTS = os.path.join(DIR_PROJECT, "results")

def loading_timeseries(
    simulation: Simulation,
    params_weather: Dict,
    HWDG_method: str = "events",
    ts_columns: List[str] = TS_COLUMNS_ALL,
) -> pd.DataFrame:
    
    import tm_solarshift.timeseries.weather as weather
    import tm_solarshift.timeseries.circuits as circuits
    import tm_solarshift.timeseries.control as control
    import tm_solarshift.timeseries.market as market
    
    location = simulation.household.location
    control_load = simulation.household.control_load
    random_control = simulation.household.control_random_on
    solar_system = simulation.pv_system
    
    YEAR = simulation.ts.YEAR.get_value("-")

    ts = simulation.create_ts_empty(ts_columns = ts_columns)
    ts = simulation.HWDInfo.generator( ts, method = HWDG_method,)
    ts = weather.load_montecarlo(ts, params = params_weather)
    ts = control.load_schedule(ts, control_load = control_load, random_ON = random_control)
    ts = circuits.load_PV_generation(ts, solar_system = solar_system)
    ts = circuits.load_elec_consumption(ts, profile_elec = 0)
    ts = market.load_wholesale_prices(ts, location)
    ts = market.load_emission_index_year(
        ts, index_type= 'total', location = location, year = YEAR,
    )
    return ts[ts_columns]

#-------------------------
def run_or_load_simulation(
        simulation: Simulation,
        ts: pd.DataFrame,
        runsim: bool = True,
        savefile: bool = True
        ):
    
    HWD_profile = simulation.HWDInfo.profile_HWD

    if runsim:
        out_data = trnsys.run_simulation( simulation, ts, verbose=False )
        df = postprocessing.events_simulation( simulation, ts, out_data)
    else:
        pass
        # df = pd.read_csv(
        #     os.path.join(DIR_RESULTS, f"0-Results_HWDP_dist_{HWD_profile}.csv"),
        #     index_col=0,
        # )
        # out_data = pd.read_csv(
        #     os.path.join( DIR_RESULTS, f"0-Results_HWDP_dist_{HWD_profile}_detailed.csv",),
        #     index_col=0,
        # )
        # df.index = [pd.to_datetime(i).date() for i in df.index]
        # out_data.index = pd.to_datetime(out_data.index)
    
    #Saving the results if needed
    if not os.path.exists(DIR_RESULTS):
        os.mkdir(DIR_RESULTS)
    if savefile:
        df.to_csv(
            os.path.join( DIR_RESULTS, f"0-Results_HWDP_dist_{HWD_profile}.csv",)
            )
        out_data.to_csv(
            os.path.join( DIR_RESULTS, f"0-Results_HWDP_dist_{HWD_profile}_detailed.csv",)
            )

    return (out_data, df)

#-------------------------
def plot_histogram_end_of_day(
        values: pd.DataFrame,
        xlim: tuple = (0,1),
        xlbl: str = None,
        ylbl: str = None,
        file_name: str = None,
        fldr_rslt: str = DIR_RESULTS,
        savefig: bool = False,
        showfig: bool = False,
):
    fs = 16
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.hist(values, bins=10, range=xlim, density=True)
    ax.set_xlabel(xlbl, fontsize=fs)
    ax.set_ylabel(ylbl, fontsize=fs)
    ax.tick_params(axis="both", which="major", labelsize=fs)
    ax.set_xlim(xlim)
    # ax.set_xticks(np.arange(0, 1.01, 0.1))
    ax.grid()
    if savefig:
        fig.savefig(
            os.path.join(fldr_rslt, file_name),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close()
    return

#-------------------------
def plots_histogram_end_of_days(
        df: pd.DataFrame,
        include: List,
        case: Union[int, str],
        savefig: bool = False,
        showfig: bool = False,
):
    for lbl in include:
        if lbl == "SOC_end":
            xlim = (0,1)
            xlbl = "State of Charge (-)"
            ylbl = "Frequency (-)"
            file_name = f"Case_{case}_hist_SOC.png"
        if lbl == "TempTh_end":
            xlim = (20,65)
            xlbl = "Thermostat Temperature (degC)"
            ylbl = "Frequency (-)"
            file_name = f"Case_{case}_hist_TempTh.png"
        if lbl=="E_HWD_day":
            xlim = (0, 12)
            xlbl = "Daily Hot Water Draw (kWh)"
            ylbl = "Frequency (-)"
            file_name = f"Case_{case}_hist_HWD_Energy.png"
        if lbl=="m_HWD_day":
            xlim = (0, 400)
            xlbl = "Daily Hot Water Draw (L/day)"
            ylbl = "Frequency (-)"
            file_name = f"Case_{case}_hist_HWD_Flow.png"

        plot_histogram_end_of_day(
            df[lbl],
            xlim = xlim,
            xlbl = xlbl,
            ylbl = ylbl,
            file_name = file_name,
            savefig = savefig,
            showfig = showfig,
            )
    return

#-------------------------
def additional_plots(
        df : pd.DataFrame,
        case: Union[int, str] = None,
        savefig: bool = False,
        showfig: bool = False,
):

    #Plot of distribution function of daily HWD
    fs = 16
    HWD_day = df["m_HWD_day"].copy()
    HWD_day.sort_values(ascending=True, inplace=True)
    HWD_day = HWD_day.reset_index()
    if True:
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.plot(HWD_day.index, HWD_day["m_HWD_day"], lw=2.0)
        ax.set_xlabel("Days of simulation", fontsize=fs)
        ax.set_ylabel("Daily Hot Water Draw (L/day)", fontsize=fs)
        ax.tick_params(axis="both", which="major", labelsize=fs)
        # ax.set_xlim(0,12)
        ax.grid()
        if savefig:
            fig.savefig(
                os.path.join(DIR_RESULTS, f"Case_{case}_HWD_Flow_ascending.png"),
                bbox_inches="tight",
            )
        if showfig:
            plt.show()
    plt.close()

    # SOC as function of Daily HWD
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(df["m_HWD_day"], df["SOC_end"], c=df["Temp_Amb"], s=10)
    ax.set_xlabel("Daily HWD (L/day)", fontsize=fs)
    ax.set_ylabel("SOC (-)", fontsize=fs)
    ax.tick_params(axis="both", which="major", labelsize=fs)
    ax.grid()
    if savefig:
        fig.savefig(
            os.path.join(DIR_RESULTS, f"Case_{case}_HWD_SOC.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close()

    # SOC as function of Thermostat Temp
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(df["TempTh_end"], df["SOC_end"], c=df["m_HWD_day"], s=10)
    ax.set_xlabel("Thermostat temperature (C)", fontsize=fs)
    ax.set_ylabel("SOC (-)", fontsize=fs)
    ax.tick_params(axis="both", which="major", labelsize=fs)
    ax.grid()
    if savefig:
        fig.savefig(
            os.path.join(DIR_RESULTS, f"Case_{case}_TempTh_SOC.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close()
    
    return

#-------------------------
def plot_histogram_2D(
    simulation: Simulation,
    df : pd.DataFrame,
    out_data: pd.DataFrame,
    case: Union[int, str] = None,
    savefig: bool = False,
    showfig: bool = False,
):
    
    STEP = simulation.ts.STEP.get_value("min")
    DAYS = simulation.ts.DAYS.get_value("d")
    
    # Probabilities of SOC through the day
    Nx = 96
    Ny = 20
    xmin = 0
    xmax = 24
    ymin = 0.0
    ymax = 1.0
    vmin = 0
    vmax = 0.25
    
    dx = (xmax-xmin)/Nx
    F_bin = (60*dx/STEP)*DAYS
    out_data['hour'] = out_data.index.hour + out_data.index.minute/60.
    SOC_2D, X, Y = np.histogram2d(
        out_data['hour'], out_data['SOC'],
        bins = [Nx,Ny], range = [[xmin, xmax],[ymin, ymax]], density=False
    )
    SOC_2D = SOC_2D/F_bin
    fig = plt.figure(figsize=(14, 8))
    fs = 16
    ax = fig.add_subplot(111)
    X, Y = np.meshgrid(X, Y)
    surf = ax.pcolormesh(
        X, Y, SOC_2D.transpose(),
        cmap=cm.YlOrRd, vmin=vmin, vmax=vmax
    )
    ax.set_xlabel('time (hr)',fontsize=fs)
    ax.set_ylabel('SOC (-)',fontsize=fs)
    cb = fig.colorbar(surf, shrink=0.5, aspect=4)
    cb.ax.tick_params(labelsize=fs-2)
    ax.tick_params(axis="both", which="major", labelsize=fs)
    ax.grid()
    if savefig:
        fig.savefig(
            os.path.join(DIR_RESULTS, f"Case_{case}_SOC_map.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close(fig)
    return

#-------------------------
def plots_sample_simulations(
    simulation: Simulation,
    out_data : pd.DataFrame,
    df: pd.DataFrame,
    case: Union[int, str],
    savefig: bool = False,
    showfig: bool = False,
    t_ini: float = 3
):
    DAYS = simulation.ts.DAYS.get_value("d")

    # Plot with a sample of 10% of days

    #SOC
    df_sample = df.sample(max(DAYS // 10, 10))
    fig, ax = plt.subplots(figsize=(9, 6))
    fs=16
    for date in df_sample.index:
        df_day = out_data[out_data.index.date == date]
        time_day = df_day.index.hour + df_day.index.minute / 60.0
        ax.plot(time_day, df_day.SOC, lw=0.5)

    ax.set_xlabel("Time of the Day (hr)", fontsize=fs)
    ax.set_ylabel("SOC (-)", fontsize=fs)
    ax.tick_params(axis="both", which="major", labelsize=fs)
    ax.grid()
    ax.set_xlim(0, 24)
    ax.set_xticks(np.arange(0, 25, 4))
    if savefig:
        fig.savefig(
            os.path.join(DIR_RESULTS, f"Case_{case}_sample_SOC.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close()

    # Thermostat temperature
    fig, ax = plt.subplots(figsize=(9, 6))
    ax2 = ax.twinx()
    ax2.plot(time_day, df_day["C_Load"], c="blue", lw=2, label="C_Load")

    out_data_first = out_data[(out_data.C_Tmax < 1) & (out_data.index.hour >= t_ini)]
    out_data_first = out_data_first.groupby(out_data_first.index.date).first()
    out_data_first["C_Tmax_first"] = out_data_first["TIME"] - 24 * (
        pd.to_datetime(out_data_first.index).dayofyear - 1
    )
    out_data_first.index = pd.to_datetime(out_data_first.index)

    for date in df_sample.index:
        df_day = out_data[out_data.index.date == date]
        time_day = df_day.index.hour + df_day.index.minute / 60.0
        ax.plot(time_day, df_day.TempBottom, lw=0.5)
        aux2 = out_data_first[out_data_first.index.date == date]
        ax.scatter(
            aux2["C_Tmax_first"], aux2["TempBottom"],
            s=50, marker="*",
            label="C_Tmax" if (date == df_sample.index[0]) else None,
        )
    ax2.legend()
    ax.set_xlabel("Time of the Day (hr)", fontsize=fs)
    ax.set_ylabel("Thermostat Temperature (-)", fontsize=fs)
    ax.tick_params(axis="both", which="major", labelsize=fs)
    ax.grid()
    ax.set_xlim(0, 24)
    ax.set_xticks(np.arange(0, 25, 4))
    if savefig:
        fig.savefig(
            os.path.join(DIR_RESULTS, f"Case_{case}_sample_TempTh.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close()

#-------------------------
def regression_analysis_and_plots(
    simulation: Simulation,
    ts : pd.DataFrame,
    df : pd.DataFrame,
    case: Union[int, str] = None,
    savefig: bool = False,
    showfig: bool = False,
):
    
    HWDP_dist = simulation.HWDInfo.profile_HWD
    
    # Histogram of generated HWDP
    HWDP_generated = ts.groupby(
        ts.index.hour
        )["m_HWD"].sum()
    HWDP_generated = HWDP_generated / HWDP_generated.sum()
    list_hours = np.arange(0, 23 + 1)
    if HWDP_dist is not None:
        HWD_file = os.path.join(
            DIR_DATA["HWDP"], f"HWDP_Generic_AU_{HWDP_dist}.csv"
        )
        HWDP_day = pd.read_csv(HWD_file)
        probs = HWDP_day.loc[list_hours, "HWDP"].values
        probs = probs / probs.sum()
        HWDP_template = probs
    
        from scipy.stats import linregress
        (slope, intercept, R2, p_value, std_err) = linregress(
            HWDP_template, 
            HWDP_generated,
            )
        RSME = ((HWDP_template - HWDP_generated) ** 2).mean() ** 0.5
    
        fig, ax = plt.subplots(figsize=(9, 6))
        fs = 16
        ax.scatter(HWDP_template, HWDP_generated, s=20)
        Ymax = HWDP_template.max()
        ax.plot([0, Ymax], [0, Ymax], c="k")
        ax.set_xlim(0, Ymax * 1.05)
        ax.set_ylim(0, Ymax * 1.05)
        ax.grid()
        ax.tick_params(axis="both", which="major", labelsize=fs)
        if savefig:
            fig.savefig(
                os.path.join(DIR_RESULTS, f"Case_{case}_HWDP_methods_comparison.png"),
                bbox_inches="tight",
            )
        if showfig:
            plt.show()
        plt.close()
    
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.bar(HWDP_generated.index, HWDP_template,
                width=0.4, align="edge",)
        ax.bar(HWDP_generated.index, HWDP_generated,
                width=-0.4, align="edge",)
        ax.grid()
        ax.tick_params(axis="both", which="major", labelsize=fs)
        if showfig:
            plt.show()
        plt.close()

    #Regresion
    for lbl in ["SOC_end", "TempTh_end"]:
        cols = ["SOC_ini", "Temp_Amb", "Temp_Mains", "m_HWD_day"]
        df2 = df[cols + [lbl]].copy()
        df2.dropna(inplace=True)
        X = df2[cols]
        Y = df2[lbl]
        regr = linear_model.LinearRegression()
        regr.fit(X, Y)
        R2 = regr.score(X, Y)
        if lbl == "SOC_end":
            R2_SOC = R2
        if lbl == "TempTh_end":
            R2_TempTh = R2

        Y_pred = regr.predict(X)

        if showfig:
            fig, ax = plt.subplots(figsize=(9, 6))
            ax.scatter(Y, Y_pred, s=2)
            Ymax = Y.max()
            ax.plot([0, Ymax], [0, Ymax], c="k")

            ax.set_xlim(0, Ymax * 1.05)
            ax.set_ylim(0, Ymax * 1.05)
            ax.grid()
            ax.set_xlabel(f"Simulated {lbl}", fontsize=fs)
            ax.set_ylabel(f"Predicted {lbl}", fontsize=fs)
            # ax.set_title(f'CL={row.profile_control}. HWDP={row.profile_HWD}. Timestep={t}mins ahead',fontsize=fs)
            ax.tick_params(axis="both", which="major", labelsize=fs)
            plt.show()

    return [R2_SOC, R2_TempTh]

#---------------------
def influence_sample_size():
    runsim = True
    savefig = True
    showfig = False
    savefile = True
    DAYS = 100
    control_load = 10
    random_control = False
    HWD_profile = 1
    HWD_generator_method = 'events'
    HWD_daily_dist = 'sample'
    COLS_OUTPUT = ["DAYS", "time_presim", "time_sim", "time_total",
                   "E_HWD_day", "m_HWD_day", "SOC_end_avg"]
    data = pd.DataFrame( columns = COLS_OUTPUT )
    data["DAYS"] = [10, 100, 500, 1000, 5000, 10000]

    for (idx, row) in data.iterrows():

        DAYS = row["DAYS"]

        start_time = time.time()

        simulation = Simulation()
        simulation.household.control_load = control_load
        simulation.household.control_random_on = random_control
        simulation.HWDInfo.profile_HWD = HWD_profile
        simulation.HWDInfo.daily_distribution = HWD_daily_dist
        simulation.ts.STOP = Variable(int(24 * DAYS), "hr")

        params_weather = {
            "dataset":"meteonorm",
            "location": simulation.household.location,
            "subset": "month",
            "value": 1,
        }
        ts = loading_timeseries(
            simulation = GS,
            params_weather = params_weather,
            HWDG_method = HWD_generator_method,
        )

        time_presim = time.time() - start_time
        
        start_time = time.time()
        (out_data, df) = run_or_load_simulation(
            simulation, ts, runsim = runsim, savefile=savefile
        )
        time_sim = time.time() - start_time

        time_total = time_presim + time_sim

        data.loc[idx,"time_presim"] = time_presim
        data.loc[idx,"time_sim"] = time_sim
        data.loc[idx,"time_total"] = time_total
        data.loc[idx,"E_HWD_day"] = df["E_HWD_day"].mean()
        data.loc[idx,"m_HWD_day"] = df["m_HWD_day"].mean()
        data.loc[idx,"SOC_end_avg"] = df["SOC_end"].mean()
        print(data)

    return data

def plotting_sample_size(data: pd.DataFrame,
                         savefig: bool = False,
                         showfig: bool = False):
        #-----------------
    fs = 16
    fig, ax = plt.subplots(figsize=(9, 6))
    ax2 = ax.twinx()

    ax.plot(data["DAYS"], data["SOC_end_avg"], marker="s")
    ax2.plot(data["DAYS"], data["time_total"], marker="o")
    ax.set_xlabel("Number of simulated days", fontsize=fs)
    ax.set_ylabel("Average SOC end of day.", fontsize=fs)
    ax2.set_ylabel("Total simulation time.", fontsize=fs)
    ax.set_xlim(0,10000)
    ax.set_ylim(0,60)
    ax.tick_params(axis="both", which="major", labelsize=fs)
    # ax.set_xticks(np.arange(0, 1.01, 0.1))
    ax.grid()
    if savefig:
        fig.savefig(
            os.path.join(DIR_PROJECT, "sample_size.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()

    plt.close()
    return None

#-------------------------
def function_with_all(case: int) -> List:


    s_time = time.time()
    runsim = True
    savefig = False
    showfig = False
    savefile = False
    verbose = False

    t_start = 0.0
    t_reset = 3.0

    DAYS = 365
    control_load = 10
    random_control = False
    HWD_profile = 1
    HWD_generator_method = 'events'
    HWD_daily_dist = 'sample'

    simulation = Simulation()
    simulation.HWDInfo.profile_HWD = case

    simulation.household.control_load = control_load
    simulation.household.control_random_on = random_control
    simulation.HWDInfo.daily_distribution = HWD_daily_dist

    simulation.ts.STOP = Variable(int(24 * DAYS), "hr")
    simulation.ts.STEP = Variable(3, "min")
    simulation.ts.YEAR = Variable(2022, "-")

    params_weather = {
        "dataset":"meteonorm",
        "location": simulation.household.location,
        "subset": "month",
        "value": 1,
    }

    ts = loading_timeseries(
        simulation = GS,
        params_weather = params_weather,
        HWDG_method = HWD_generator_method,
    )
    (out_data, df) = run_or_load_simulation(
        simulation, ts, runsim = runsim, savefile=savefile
    )
    postprocessing.detailed_plots(
            simulation, out_data,
            fldr_results_detailed = DIR_RESULTS,
            case = f'case_{case}',
            save_plots_detailed = False,
            showfig = False,
            tmax = 120.
    )
    time_simulation = time.time() - s_time
    # print(f"Time spent in thermal simulation={time_simulation}")

    #Different plottings
    plots_histogram_end_of_days(
        df,
        ["SOC_end", "TempTh_end", "E_HWD_day", "m_HWD_day"],
        case, savefig, showfig
    )        
    additional_plots(df, case, savefig, showfig)
    plot_histogram_2D( simulation, df, out_data, case, savefig, showfig )
    plots_sample_simulations(simulation, out_data, df, case, savefig, showfig)
    R2_SOC, R2_TempTh = regression_analysis_and_plots(
        simulation, ts, df, case, savefig, showfig
    )
    
    Risk_Shortage01 = len(df[df["SOC_end"] <= 0.1]) / len(df)
    if verbose:
        print(f"Fraction with SOC<0.1 at the end of the day: {Risk_Shortage01*100}%")
    Risk_Shortage02 = len(df[df["SOC_end"] <= 0.2]) / len(df)
    if verbose:
        print(f"Fraction with SOC<0.2 at the end of the day: {Risk_Shortage02*100}%")

    elapsed_time = time.time() - s_time
    data_row = [HWD_profile, Risk_Shortage01, Risk_Shortage02, R2_SOC, R2_TempTh, elapsed_time]
    return data_row




#-------------------------
def main_linear():

    CASES = [1,2,3,4,5,6]
    data = []
    for case in CASES:
        data_row = function_with_all(case)
        data = data.append(data_row)
    columns = ["HWDP_dist", "Risk_Shortage01",
                    "Risk_Shortage02", "R2_SOC", "R2_TempTh",]
    df_data = pd.DataFrame(data, columns=columns,)
    print(df_data)
    return df_data


#-------------------------
def main_multiprocessing(processes:int = 4):

    from multiprocessing import Pool

    t_start = time.time()
    CASES = [1,2,3,4,5,6]
    with Pool(processes) as p:
        data = p.map(function_with_all, CASES)
    
    columns = [
        "HWDP_dist",
        "Risk_Shortage01", "Risk_Shortage02",
        "R2_SOC", "R2_TempTh",
        "sim_time",
    ]
    df_data = pd.DataFrame(data, columns=columns,)
    print(df_data)
    return (time.time()-t_start)


def plot_simulation_times(
        savefig : bool = False,
        showfig: bool = False
):

    df = pd.read_csv(
        os.path.join(DIR_PROJECT,"multiprocessing_times.csv"),
        columns=["proc","time_sim"]
        )
    df["time_one_year"] = df["time_sim"] / 12

    fs = 16
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(df["proc"], df["time_one_year"], marker="s")
    ax.set_xlabel("Number of paralel processes", fontsize=fs)
    ax.set_ylabel("Avg. comp. time for 1-year simulation (secs).", fontsize=fs)
    ax.tick_params(axis="both", which="major", labelsize=fs)
    ax.set_xlim(0,7)
    ax.set_ylim(0,60)
    # ax.set_xticks(np.arange(0, 1.01, 0.1))
    ax.grid()
    if savefig:
        fig.savefig(
            os.path.join(DIR_PROJECT, "multiprocessing_times.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    plt.close()

    return

if __name__ == '__main__':

    influence_sample_size()

    # main_linear()

    # plot_simulation_times(savefig=True)

    # sim_times = []
    # for processes in [6,4,3,2,1]:
    #     sim_time = main_multiprocessing(processes=processes)
    #     sim_times.append([processes,sim_time])
    #     print(sim_times[-1])
    pass