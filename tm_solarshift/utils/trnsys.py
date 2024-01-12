import subprocess
import shutil
import time
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, List, Dict, Any, Tuple

from tm_solarshift.utils.general import GeneralSetup
from tm_solarshift.utils.general import DATA_DIR
from tm_solarshift.utils.devices import (ResistiveSingle, HeatPump)

W2kJh = 3.6
TRNSYS_EXECUTABLE = r"C:/TRNSYS18/Exe/TRNExe64.exe"
TRNSYS_TEMPDIR = "C:/SolarShift_TempDir"

FILES_TRNSYS_INPUT = {
    "PV_Gen": "0-Input_PVGen.csv",
    "Import_Grid": "0-Input_Elec.csv",
    "m_HWD": "0-Input_HWD.csv",
    "CS": "0-Input_Control_Signal.csv",
    "weather": "0-Input_Weather.csv",
    "HP": "0-HP_Data.dat"
    }

FILES_TRNSYS_OUTPUT = {
    "RESULTS_DETAILED" : "TRNSYS_Out_Detailed.dat",
    "RESULTS_TANK": "TRNSYS_Out_TankTemps.dat",
    "RESULTS_SIGNAL": "TRNSYS_Out_Signals.dat",
    }

METEONORM_FOLDER = r"C:/TRNSYS18/Weather/Meteonorm/Australia-Oceania"
METEONORM_FILES = {
    "Adelaide": "AU-Adelaide-946720.tm2",
    "Alice_Spring": "AU-Alice-Springs-943260.tm2",
    "Brisbane": "AU-Brisbane-945780.tm2",
    "Canberra": "AU-Canberra-949260.tm2",
    "Darwin": "AU-Darwin-Airport-941200.tm2",
    "Hobart": "AU-Hobart-Airport-949700.tm2",
    "Melbourne": "AU-Melbourne-948660.tm2",
    "Perth": "AU-Perth-946080.tm2",
    "Sydney": "AU-Sydney-947680.tm2",
    "Townsville": "AU-Townsville-942940.tm2",
}

#################################
# DEFINING THE PROBLEM.
# It requires to define the type of layout, general and environmental parameters
# the profile parameters, and

#################################
# DEFINING TYPE OF LAYOUT
# layout_DEWH: Type of DEWH.
#    'RS': Resistive (single);
#    'RD': Resistive (dual);
#    'HPF': Heat Pump (with file data from catalog, interpolator and calculator);
#    'GH': Gas heater;
#    'TH': Solar thermal collector.

# layout_PV: Type of PV System.
#    'PVM': TRNSYS's PV model component;
#    'PVF': Datafile (historical data, the file has to be provided in file_PV, or generated with generic profiles);
#    'PVO': Any Python's PV model (the model has to be provided in model_PV, it requires the weather data file);

# layout_TC: Type of temp control System:
#    'MX': Only max temp control (never Temp > Tank_TempHigh);
#    'MM': Only min temp control (never Temp < Tank_TempLow);
#    'MM': Both max and min temp control (always  Tank_TempLow < Temp < Tank_TempHigh);

# layout_WF: Type of Weather File:
#    'W15': Built-in weather type (Type 15-6);
#    'W9a': Timeseries provided as a CSV-like file. The file has to be created with a Python function from some sources.

# Version of layout:
# This allows to choose a specific version if more than one version is for that specific file
# If there is only one file, then that file is used, regardless of the value here
# If set to -1, then the latest will be used.
# If layour_verson>latest available version, then the latest is used.

########################################
#### DEFINING TRNSYS CLASSES
class TrnsysSetup():
    def __init__(self, general_setup, **kwargs):
        # Directories
        self.tempDir = None

        self.START= general_setup.START   # [hr]
        self.STOP = general_setup.STOP    # [hr]
        self.STEP = general_setup.STEP    # [min]
        self.location = general_setup.location
        self.DEWH = general_setup.DEWH

        # Trnsys Layout configuration
        if self.DEWH.__class__ == ResistiveSingle:
            layout_DEWH = "RS"
        elif self.DEWH.__class__ == HeatPump:
            layout_DEWH = "HPF"
        else:
            raise ValueError("DEWH is not a valid class for TRNSYS simulation")
        self.layout_DEWH = layout_DEWH
        
        self.layout_v = 0
        self.layout_PV = "PVF"
        self.layout_TC = "MX"
        self.layout_WF = "W9a"
        self.weather_source = None

        for key, value in kwargs.items():
            setattr(self, key, value)


#######################################################
#### EDITING DCK FILE FUNCTIONS
def editing_dck_general(
        Sim: TrnsysSetup,
        dck_editing: List[str],
        ) -> List[str]:

    START = Sim.START
    STOP = Sim.STOP
    STEP = Sim.STEP

    DEWH = Sim.DEWH
    nom_power = DEWH.nom_power.get_value("W")
    eta = DEWH.eta.get_value("-")
    temp_max = DEWH.temp_max.get_value("degC")
    temp_min = DEWH.temp_min.get_value("degC")
    temp_consump = DEWH.temp_consump.get_value("degC")
    temp_high_control = DEWH.temp_high_control.get_value("degC")

    # Editing .dck file: general parameters of simulation
    tag = "Control cards"
    for idx, line in enumerate(dck_editing):
        if tag in line:
            dck_editing[idx + 4] = f"START={START}"
            dck_editing[idx + 5] = f"STOP={STOP}"
            dck_editing[idx + 6] = f"STEP={STEP}/60"
            break

    # Editing .dck file: DEWH: resistive single and HP
    gral_params = {
        "Heater_NomCap": nom_power * W2kJh,
        "Heater_F_eta": eta,
        "Tank_TempHigh": temp_max,
        "Tank_TempLow": temp_min,
        "Temp_Consump": temp_consump,
        "Tank_TempHighControl": temp_high_control,
    }

    tag = "!PYTHON_INPUT"
    for idx, line in enumerate(dck_editing):
        if tag in line:
            for key, value in gral_params.items():
                if key in line:
                    new_line = "{:} = {:.5f} !This line was replaced by python script !PYTHON_INPUT".format(
                        key, value
                    )
                    dck_editing[idx] = new_line

    return dck_editing


def editing_dck_weather(
        Sim: TrnsysSetup,
        dck_editing: List[str],
        ) -> List[str]:

    layout_WF = Sim.layout_WF

    # The start and end lines of the component are identified and extracted
    if layout_WF == "W15":
        tag1 = "Type15-6_Weather"  # Component name. It should be only one per file
        weather_path = Sim.weather_path

    if layout_WF == "W9a":
        tag1 = "Type9a_Weather"  # Component name. It should be only one per file
        weather_path = os.path.join(Sim.tempDir, FILES_TRNSYS_INPUT["weather"])

    # Start
    for idx, line in enumerate(dck_editing):
        if tag1 in line:
            idx_start = idx
            comp_lines = dck_editing[idx_start:]
            break
    # End
    tag2 = "*------------"
    for idx, line in enumerate(comp_lines):
        if tag2 in line:
            idx_end = idx + idx_start + 1  # index in the original file
            break
    comp_lines = dck_editing[idx_start:idx_end]

    # Replacing the default line with the weather file
    tag3 = "ASSIGN"
    for idx, line in enumerate(comp_lines):
        if tag3 in line:
            aux = line.split('"')
            new_line = aux[0] + ' "' + f"{weather_path}" + ' "' + aux[-1]
            comp_lines[idx] = new_line
            break

    # Joining the edited lines with the old set
    dck_editing = dck_editing[:idx_start] + comp_lines + dck_editing[idx_end:]

    return dck_editing


def editing_dck_tank(
        Sim: TrnsysSetup,
        dck_editing: List[str],
        ) -> List[str]:

    DEWH = Sim.DEWH
    vol = DEWH.vol.get_value("m3")
    height = DEWH.height.get_value("m")
    U = DEWH.U.get_value("W/m2-K")
    temp_max = DEWH.temp_max.get_value("degC")
    temp_min = DEWH.temp_min.get_value("degC")

    temps_ini = DEWH.temps_ini
    nodes = DEWH.nodes

    # The start and end lines of the component are identified and extracted
    # Start
    tag1 = "HotWaterTank_1"  # Component name (Two tags are used in case there is more than one tank)
    tag2 = "158"  # Component Type
    for idx, line in enumerate(dck_editing):
        if tag1 in line and tag2 in line:
            idx_start = idx
            comp_lines = dck_editing[idx_start:]
            break

    # End
    tag3 = "*------------"
    for idx, line in enumerate(comp_lines):
        if tag3 in line:
            idx_end = idx + idx_start + 1  # index in the original file
            break

    comp_lines = dck_editing[idx_start:idx_end]

    # Finding the Initial Parameters to change
    tank_params = {
        "1 Tank volume": vol,
        "2 Tank height": height,
        "4 Top loss coefficient": U * W2kJh,
        "5 Edge loss coefficient": U * W2kJh,
        "6 Bottom loss coefficient": U * W2kJh,
    }

    for idx, line in enumerate(comp_lines):
        for key, value in tank_params.items():
            if key in line:
                new_line = "{:}   !  {:}".format(value, key)
                comp_lines[idx] = new_line

    # Defining the Initial temperature (DERIVATIVE PARAMETERS)
    # Linear stratification
    if temps_ini == 1:
        tank_node_temps = np.linspace(temp_max, temp_min, nodes)
    # Linear inverted stratification
    elif temps_ini == 2:
        tank_node_temps = np.linspace(temp_min, temp_max, nodes)
    # Full Charged
    elif temps_ini == 3:
        tank_node_temps = temp_max * np.ones(nodes)
    # Full Discharged
    elif temps_ini == 4:
        tank_node_temps = temp_min * np.ones(nodes)
    # Random
    elif temps_ini == 5:
        tank_node_temps = np.random.uniform(
            low=temp_min, high=temp_max, size=(nodes,)
        )
    else:
        raise ValueError("Value for temp_ini is not valid [0-5]")

    tag4 = "DERIVATIVES"  # There should be only one on lines_tank
    for idx, line in enumerate(comp_lines):
        if tag4 in line:
            for i in range(nodes):
                idx_aux = idx + i + 1
                comp_lines[idx_aux] = (
                    str(tank_node_temps[i]) 
                    + "   !" 
                    + comp_lines[idx_aux].split("!")[1]
                )
            break

    # Joining the edited lines with the old set
    dck_editing = (dck_editing[:idx_start] 
                   + comp_lines 
                   + dck_editing[idx_end:])

    return dck_editing


def editing_dck_file(Sim: TrnsysSetup):

    layout_DEWH = Sim.layout_DEWH
    layout_PV = Sim.layout_PV
    layout_TC = Sim.layout_TC
    layout_WF = Sim.layout_WF
    layout_v = Sim.layout_v
    tempDir = Sim.tempDir

    if layout_v == 0:
        file_trnsys = f"TRNSYS_{layout_DEWH}_{layout_PV}_{layout_TC}_{layout_WF}.dck"
    else:
        file_trnsys = (
            f"TRNSYS_{layout_DEWH}_{layout_PV}_{layout_TC}_{layout_WF}_v{layout_v}.dck"
        )

    # The original .dck file. It is in layoutDir
    dck_path = os.path.join(DATA_DIR["layouts"], file_trnsys)

    # Loading the original TRNSYS (.dck) file
    with open(dck_path, "r") as file_in:
        dck_original = file_in.read().splitlines()

    # Making the edits
    dck_editing = dck_original.copy()
    # General parameters for simulation and devices
    dck_editing = editing_dck_general(Sim, dck_editing)
    # Defining weather file
    dck_editing = editing_dck_weather(Sim, dck_editing)
    # Defining tank parameters
    dck_editing = editing_dck_tank(Sim, dck_editing)

    # Saving the edits into a new .dck file that will be read
    trnsys_dck_path = os.path.join(tempDir, file_trnsys)
    with open(trnsys_dck_path, "w") as dckfile_out:
        for line in dck_editing:
            dckfile_out.write(f"{line}\n")
    
    return trnsys_dck_path

########################################################
#### SETTING AND RUNNING SIMULATION
########################################################

def creating_trnsys_files(
        Sim: TrnsysSetup,
        timeseries: pd.DataFrame,
        ) -> None:

    from tm_solarshift.utils.profiles import PROFILES_TYPES
    layout_WF = Sim.layout_WF
    layout_DEWH = Sim.layout_DEWH
    weather_source = Sim.weather_source
    location = Sim.location
    tempDir = Sim.tempDir
    
    # Creating temporary folder
    # This is done to assign a new temporal folder where the simulation will be run.
    # temp_i = 1
    # while True:
    #     tempDir = os.path.join(TRNSYS_TEMPDIR, f"temp{temp_i}")
    #     if not os.path.isdir(tempDir):
    #         os.makedirs(tempDir)
    #         break
    #     else:
    #         temp_i += 1
    # Sim.tempDir = tempDir
    
    # Creating files from Profiles
    #Saving Files
    lbls = ["PV_Gen","m_HWD","CS","Import_Grid"]
    for lbl in lbls:
        timeseries[lbl].to_csv(
            os.path.join(tempDir, FILES_TRNSYS_INPUT[lbl]), index=False
        )
        
    timeseries[PROFILES_TYPES['weather']].to_csv(
        os.path.join(tempDir, FILES_TRNSYS_INPUT["weather"]), index=False
    )
    
    #Adding information for specific components
    if layout_DEWH == "HPF":
        file_HP_data = FILES_TRNSYS_INPUT["HP"]
        shutil.copyfile(
            os.path.join(DATA_DIR["samples"], file_HP_data),
            os.path.join(tempDir, file_HP_data)
        )

    if layout_WF == "W15":
        if weather_source == None:
            weather_source = "Meteonorm"

        if weather_source == "Meteonorm":
            Sim.weather_path = os.path.join(
                METEONORM_FOLDER,
                METEONORM_FILES[location]
            )

    return

###########################################
def postprocessing_detailed(
        Sim: TrnsysSetup,
        timeseries: pd.DataFrame,
        verbose: str=False
        ):
    
    #Reading output files
    tempDir = Sim.tempDir
    # The files with simulation data exported by TRNSYS are loaded here
    # The processed data is stored into one single file
    out_gen = pd.read_table(
        os.path.join(
            Sim.tempDir, 
            FILES_TRNSYS_OUTPUT["RESULTS_DETAILED"]
        ), 
        sep=r"\s+", 
        index_col=0
    )
    out_tank = pd.read_table(
        os.path.join(
            tempDir, 
            FILES_TRNSYS_OUTPUT["RESULTS_TANK"]
        ), 
        sep=r"\s+", 
        index_col=0
    )
    out_sig = pd.read_table(
        os.path.join(
            tempDir, 
            FILES_TRNSYS_OUTPUT["RESULTS_SIGNAL"]
        ), 
        sep=r"\s+", 
        index_col=0
    )
    out_all = out_gen.join(out_tank, how="left")
    out_all = out_all.join(
        out_sig[["C_Load", "C_Tmax", "C_Tmin", "C_All"]],
        how="left"
    )


    # Calculating additional variables
    DEWH = Sim.DEWH
    temp_consump = DEWH.temp_consump.get_value("degC")
    temp_max = DEWH.temp_high.get_value("degC")
    temp_min = DEWH.temp_min.get_value("degC")
    tank_cp = DEWH.fluid.cp.get_value("J/kg-K")
    tank_nodes = DEWH.nodes

    temp_mains = out_all["T_mains"].mean()

    node_cols = [col for col in out_all if col.startswith("Node")]
    out_all2 = out_all[node_cols]
    out_all["T_avg"] = out_all2.mean(axis=1)
    out_all["SOC"] = ((out_all2 - temp_consump) * (out_all2 > temp_consump)).sum(
        axis=1
    ) / (tank_nodes * (temp_max - temp_consump))
    out_all["SOC2"] = ((out_all2 - temp_mains) * (out_all2 > temp_consump)).sum(
        axis=1
    ) / (tank_nodes * (temp_max - temp_mains))
    out_all["SOC3"] = (
        (out_all2.sum(axis=1) - tank_nodes * temp_min)
        / (temp_max - temp_min)
        / tank_nodes
    )

    out_all["E_HWD"] = out_all["HW_Flow"] * (
        tank_cp * (temp_consump - temp_mains) / 3600.
    )  # [W]

    out_all["E_Level"] = (out_all2 - temp_consump).sum(axis=1) / (
        tank_nodes * (temp_max - temp_consump)
    )

    out_all["TIME"] = out_all.index
    out_all = out_all.iloc[1:]
    out_all.index = timeseries.index
    # First row are initial conditions, but are dummy values for results. They can be removed

    return out_all

##########################################


def postprocessing_annual_simulation(
        Sim: TrnsysSetup,
        Profiles: pd.DataFrame,
        out_all: pd.DataFrame
        ) -> Dict:

    START = Sim.START
    STOP = Sim.STOP
    STEP = Sim.STEP
    thermal_cap = Sim.DEWH.thermal_cap.get_value("kWh")
    tank_cp = Sim.DEWH.fluid.cp.get_value("J/kg-K")
    
    # Derivated parameters
    STEP_h = STEP / 60.0  # [hr] delta t in hours
    PERIODS = int(np.ceil((STOP - START) / STEP_h))  # [-] Number of periods to simulate
    DAYS = STEP_h * PERIODS / 24.0

    # Calculating overall parameters
    # Accumulated energy values (all in [kWh])
    heater_heat_acum = (out_all["HeaterHeat"] * STEP_h / W2kJh / 1000.0).sum()
    heater_power_acum = (out_all["HeaterPower"] * STEP_h / W2kJh / 1000.0).sum()

    if heater_heat_acum <= 0:
        heater_heat_acum = np.nan
    if heater_power_acum <= 0:
        heater_power_acum = np.nan

    heater_perf_avg = heater_heat_acum / heater_power_acum

    E_HWD_acum = (
        out_all["Tank_FlowRate"]
        * STEP_h
        * tank_cp
        * (out_all["TempTop"] - out_all["T_mains"])
        / W2kJh
        / 1e6
    ).sum()

    E_losses = heater_heat_acum - E_HWD_acum
    eta_stg = E_HWD_acum / heater_heat_acum
    cycles_day = heater_heat_acum / thermal_cap / DAYS

    # Average values
    m_HWD_avg = out_all["HW_Flow"].sum() * STEP_h / DAYS
    out_avg = out_all.mean()
    SOC_avg = out_avg["SOC"]
    temp_amb_avg = out_avg["T_amb"]
    temp_mains_avg = out_avg["T_mains"]

    # Risks_params
    SOC_min = out_all["SOC"].min()
    (SOC_025, SOC_050) = out_all["SOC"].quantile(
        [0.25, 0.50],
        interpolation="nearest",
        )
    t_SOC0 = (out_all["SOC"] <= 0.01).sum() * STEP_h

    # Emissions and Solar Fraction
    heater_power_sum = out_all["HeaterPower"].sum()
    if heater_power_sum <= 0.0:
        heater_power_sum = np.nan
    solar_ratio = (
        out_all[
            (out_all.index.hour >= 8.75) & (out_all.index.hour <= 17.01)
        ]["HeaterPower"].sum()
        / heater_power_sum
    )
    
    emissions_total = ((out_all["HeaterPower"] / 1e6 / 3.6 * STEP_h)
                       * Profiles["Intensity_Index"]).sum()

    out_overall = {
        "heater_heat_acum": heater_heat_acum,
        "heater_power_acum": heater_power_acum,
        "heater_perf_avg": heater_perf_avg,
        "E_HWD_acum": E_HWD_acum,
        "E_losses": E_losses,
        "eta_stg": eta_stg,
        "cycles_day": cycles_day,
        "m_HWD_avg": m_HWD_avg,
        "SOC_avg": SOC_avg,
        "temp_amb_avg": temp_amb_avg,
        "temp_mains_avg": temp_mains_avg,
        "SOC_min": SOC_min,
        "SOC_025": SOC_025,
        "SOC_050": SOC_050,
        "t_SOC0": t_SOC0,
        "emissions_total": emissions_total,
        "solar_ratio": solar_ratio,
    }

    return out_overall

############################################

def postprocessing_events_simulation(
        Sim: TrnsysSetup, 
        Profiles: pd.DataFrame,
        out_data: pd.DataFrame,
    ) -> pd.DataFrame:
    
    STEP_h = Sim.STEP_h
    tank_cp = Sim.DEWH.fluid.cp.get_value("J/kg-K")

    df = Profiles.groupby(Profiles.index.date)[
        ["m_HWD_day", "Temp_Amb", "Temp_Mains"]
    ].mean()
    idx = np.unique(Profiles.index.date)
    df_aux = out_data.groupby(out_data.index.date)
    df.loc[
        df.index == idx, 
        "SOC_end"
    ] = df_aux.tail(1)["SOC"].values
    df.loc[
        df.index == idx,
        "TempTh_end"
    ] = df_aux.tail(1)["TempBottom"].values
    df.loc[
        df.index == idx,
        "EL_end"
    ] = df_aux.tail(1)["E_Level"].values

    E_HWD_acum = (
        (
            out_data["Tank_FlowRate"]
            * STEP_h
            * tank_cp
            * (out_data["TempTop"] - out_data["T_mains"])
            / W2kJh
            / 1e6
        )
        .groupby(out_data.index.date)
        .sum()
    )
    df.loc[
        df.index == idx, 
        "E_HWD_day"
    ] = E_HWD_acum
    df.loc[
        df.index == idx, 
        "SOC_ini"
    ] = df_aux.head(1)["SOC"].values
    return df

############################################

def thermal_simulation_run(
        general_setup: GeneralSetup,
        timeseries: pd.DataFrame,
        verbose: bool = False,
        engine: str = 'TRNSYS',
        keep_tempDir: bool = False,
        ):

    if verbose:
        print("RUNNING TRNSYS SIMULATION")
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(dir=TRNSYS_TEMPDIR) as tmpdir:
    # if engine == 'TRNSYS':
        Sim = TrnsysSetup(general_setup)
        Sim.tempDir = tmpdir

        stime = time.time()
        if verbose:
            print("Creating the temporary folder with files")
        creating_trnsys_files(Sim, timeseries)
        
        if verbose:
            print("Creating the trnsys source code (dck file)")
        trnsys_dck_path = editing_dck_file(Sim)
        
        if verbose:
            print("Calling TRNSYS executable")
        subprocess.run([TRNSYS_EXECUTABLE, trnsys_dck_path, "/h"])
        
        if verbose:
            print("TRNSYS simulation finished. Starting postprocessing.")
        out_all = postprocessing_detailed(Sim, timeseries)
        
        # if keep_tempDir:
        #     if verbose:
        #         print(f"End of simulation. The temporary folder {Sim.tempDir} was not deleted.")
        # else:
        #     shutil.rmtree(Sim.tempDir)
        #     if verbose:
        #         print("End of simulation. The temporary folder is deleted.")
            
        elapsed_time = time.time()-stime
        if verbose:
            print(f"Execution time: {elapsed_time:.4f} seconds.")
    
        return out_all
    
    print("Thermal simulation was not executed properly.")
    return None
    
    
############################################
def detailed_plots(
    Sim,
    out_all,
    fldr_results_detailed=None,
    case=None,
    save_plots_detailed=False,
    tmax=72.0,
):

    ### PLOTTING TEMPERATURES AND SOC
    fig, ax = plt.subplots(figsize=(9, 6))
    fs = 16
    xmax = tmax

    for i in range(1, Sim.Tank_nodes + 1):
        lbl = f"Node{i}"
        ax.plot(out_all.TIME, out_all[lbl], lw=2, label=lbl)
    ax.legend(loc=0, fontsize=fs - 2, bbox_to_anchor=(-0.1, 0.9))
    ax.grid()
    ax.set_xlim(0, xmax)
    ax.set_ylim(Sim.Temp_Mains, Sim.Tank_TempHigh + 5)
    ax.set_xlabel("Time of Simulation (hr)", fontsize=fs)
    ax.set_ylabel("Temperature (C)", fontsize=fs)
    ax.tick_params(axis="both", which="major", labelsize=fs - 2)

    ax2 = ax.twinx()
    ax2.plot(out_all.TIME, out_all.SOC, lw=3, ls="--", c="C3", label="SOC")
    ax2.legend(loc=1, fontsize=fs - 2)
    ax2.set_ylim(-0.05, 1.05)
    ax2.set_ylabel("State of Charge (-)", fontsize=fs)
    ax2.tick_params(axis="both", which="major", labelsize=fs - 2)

    if save_plots_detailed:
        fldr = os.path.join(Sim.fileDir, fldr_results_detailed)
        if not os.path.exists(fldr):
            os.mkdir(fldr)
        fig.savefig(
            os.path.join(fldr_results_detailed, case + "_Temps_SOC.png"),
            bbox_inches="tight",
        )
    plt.show()

    ####################################
    # STORED ENERGY AND SOC

    fig, ax = plt.subplots(figsize=(9, 6))
    fs = 16
    ax2 = ax.twinx()
    aux = (
        (out_all.index.dayofyear - 1) * 24
        + out_all.index.hour
        + out_all.index.minute / 60.0
    )

    # ax.plot( aux, out_all.PVPower/W2kJh, label='E_PV', c='C0',ls='-',lw=2)
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
    plt.show()
    return

if __name__=="__main__":

    general_setup = GeneralSetup()
    from tm_solarshift.utils.profiles import new_profile
    timeseries = new_profile(general_setup)
    thermal_simulation_run(general_setup, timeseries, verbose=True)