# -*- coding: utf-8 -*-
"""
Created on Mon Jun 26 16:17:04 2023

@author: z5158936

"""

import subprocess  # to run the TRNSYS simulation
import shutil  # to duplicate the output txt file
import time  # to measure the computation time
import os
import datetime
import sys
import glob
from typing import Optional, List, Dict, Any, Tuple

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.stats import truncnorm
import itertools

W2kJh = 3.6
TRNSYS_EXECUTABLE = r"C:\TRNSYS18\Exe\TRNExe64.exe"
TRNSYS_TEMPDIR = "C:\SolarShift_TempDir"

FILES_TRNSYS_INPUT = {
    "PV_Gen": "0-Input_PVGen.csv",
    "Elec_Cons": "0-Input_Elec.csv",
    "m_HWD": "0-Input_HWD.csv",
    "CS": "0-Input_Control_Signal.csv",
    "weather": "0-Input_Weather.csv",
    "HP": "0-Reclaim_HP_Data.dat"
    }

FILES_TRNSYS_OUTPUT = {
    "RESULTS_DETAILED" :  "TRNSYS_Out_Detailed.dat",
    "RESULTS_TANK": "TRNSYS_Out_TankTemps.dat",
    "RESULTS_SIGNAL": "TRNSYS_Out_Signals.dat",
    }

METEONORM_FOLDER = "C:\TRNSYS18\Weather\Meteonorm\Australia-Oceania"
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

#######################################
# DEFINITION OF PROFILES
# In each case 0 means not included (profile will be fill with 0 or 1 depending on the case)

# profile_PV
# Profile for the PV generation source
#       0: No PV included (generation = 0 all the time)
#       1: Gaussian shape with peak = PV_NomPow

# profile_Elec
# Profile for the electricity load (non-DEHW)
#       0: No Electricity load included (load = 0 all the time)

# profile_HWD
# Profile for the HWD profile
#       0: No water draw profile (HWD = 0 all the time)
#       1: Morning and evening only
#       2: Morning and evening with day time
#       3: Evenly distributed
#       4: Morning
#       5: Evening
#       6: Late night
#       7: Step Profile

# profile_control
# Profile for the control strategy
#   -1: General supply (24hrs)
#   0: No load (to check thermal losses)
#   1: Control load 1 (10pm-7am)
#   2: Control load 2 (at all time, except peak period: 4pm-8pm)
#   3: Ausgrid's Control load 3 (new solar soak) (roughly 10pm-7pm + 9am-3pm)
#   4: Only solar soak (9am-3pm)
#   5: Specific Control strategy (defined by file file_cs)


########################################
#### DEFINING THE PROBLEM AND SIMULATION

## The main object for the simulation
class General_Setup(object):
    def __init__(self, **kwargs):
        # Directories
        self.fileDir = os.path.dirname(__file__)
        self.layoutDir = "TRNSYS_layouts"
        self.tempDir = None

        # General Simulation Parameters
        self.START = 0  # [hr]
        self.STOP = 8760  # [hr]
        self.STEP = 3  # [min]
        self.YEAR = 2022  # [-]
        self.location = "Sydney"
        self.DNSP = "Ausgrid"
        self.tariff_type = "flat"
         
        # Trnsys Layout configuration
        self.layout_v = 0
        self.layout_DEWH = "RS"  # See above for the meaning of these options
        self.layout_PV = "PVF"
        self.layout_TC = "MX"
        self.layout_WF = "W9a"
        self.weather_source = None
        
        # Environmental parameters
        # (These default values can change if a weather file is defined)
        self.Temp_Amb = 20.0  # [C] Ambient Temperature
        self.Temp_Mains = 20.0  # [C] Mains water temperature
        self.Temp_Consump = 45.0  # [C] Same as TankTemp_Low
        self.GHI_avg = 1000.0  # [W/m2] Global Horizontal Irradiation

        # Profile/Behavioural Parameters
        self.profile_PV = 0  # See above for the meaning of these options
        self.profile_Elec = 0
        self.profile_HWD = 1
        self.profile_control = 0
        self.random_control = True

        # HWD statistics
        self.HWD_avg = 200.0  # [L/d]
        self.HWD_std = (
            self.HWD_avg / 3.0
        )  # [L/d] (Measure for daily variability. If 0, no variability)
        self.HWD_min = 0.0  # [L/d] Minimum HWD. Default 0
        self.HWD_max = 2 * self.HWD_avg  # [L/d] Maximum HWD. Default 2x HWD_avg
        self.HWD_daily_dist = (
            None  # [str] Type of variability in daily consumption. None for nothing
        )
        self.HWD_daily_source = 'sample',
        # Main components nominal capacities
        self.PV_NomPow = 4000.0  # [W]
        self.Heater_NomCap = 3600.0  # [W]
        self.Heater_F_eta = (
            1.0  # [-] Efficiency factor. 1 for resistive; 3-4 for heat pumps
        )
        # Tank parameters
        self.Tank_nodes = (
            10  # Tank nodes. DO NOT CHANGE, unless TRNSYS layout is changed too!
        )
        self.Tank_Vol = 0.315  # [m3]
        self.Tank_Height = 1.3  # [m]
        self.Tank_TempHigh = 65.0  # [C] Maximum temperature in the tank
        self.Tank_TempDeadband = 10.0  # [C] Dead band for max temp control
        self.Tank_TempLow = 45.0  # [C] Minimum temperature in the tank
        self.Tank_U = 0.9  # [W/m2K] Overall heat loss coefficient
        self.Tank_rho = 1000  # [kg/m3] density (water)
        self.Tank_cp = 4180  # [J/kg-K] specific heat (water)
        self.Tank_k = 0.6  # [W/m-K] thermal conductivity (water)
        self.Tank_Temps_Ini = 3  # [-] Initial temperature of the tank. Check Editing_dck_tank() below for the options

        for key, value in kwargs.items():
            setattr(self, key, value)

        self.DAYS = int(self.STOP / 24)
        self.STEP_h = self.STEP / 60.0
        self.PERIODS = int(np.ceil((self.STOP - self.START) / self.STEP_h))
        self.DAYS_i = int(np.ceil(self.STEP_h * self.PERIODS / 24.0))

        # Some derived parameters from defined values
        self.Tank_ThCap = (
            self.Tank_Vol
            * (self.Tank_rho * self.Tank_cp)
            * (self.Tank_TempHigh - self.Tank_TempLow)
            / 3.6e6
        )  # [kWh]
        self.Tank_D = (4 * self.Tank_Vol / np.pi / self.Tank_Height) ** 0.5
        self.Tank_Aloss = np.pi * self.Tank_D * (self.Tank_D / 2 + self.Tank_Height)

        self.Tank_TempHighControl = (
            self.Tank_TempHigh - self.Tank_TempDeadband / 2.0
        )  # [C] Control temperature including deadband

    ##########################################
    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Some derived parameters from defined values
        self.Tank_ThCap = (
            self.Tank_Vol
            * (self.Tank_rho * self.Tank_cp)
            * (self.Tank_TempHigh - self.Tank_TempLow)
            / 3.6e6
        )  # [kWh]
        self.Tank_D = (4 * self.Tank_Vol / np.pi / self.Tank_Height) ** 0.5
        self.Tank_Aloss = np.pi * self.Tank_D * (self.Tank_D / 2 + self.Tank_Height)

        self.Tank_TempHighControl = (
            self.Tank_TempHigh - self.Tank_TempDeadband / 2.0
        )  # [C] Control temperature including deadband

    ##########################################
    def update_params(self, params):
        for key, values in params.items():
            if hasattr(self, key):  # Checking if the params are in Sim to update them
                setattr(self, key, values)
            else:
                print(f"Parameter {key} not in Sim object. Simulation will finish now")
                sys.exit()

        # Some derived parameters from defined values
        self.Tank_ThCap = (
            self.Tank_Vol
            * (self.Tank_rho * self.Tank_cp)
            * (self.Tank_TempHigh - self.Tank_TempLow)
            / 3.6e6
        )  # [kWh]
        self.Tank_D = (4 * self.Tank_Vol / np.pi / self.Tank_Height) ** 0.5
        self.Tank_Aloss = np.pi * self.Tank_D * (self.Tank_D / 2 + self.Tank_Height)

        self.Tank_TempHighControl = (
            self.Tank_TempHigh - self.Tank_TempDeadband / 2.0
        )  # [C] Control temperature including deadband

    def parameters(self):
        return self.__dict__.keys()

#######################################################
#### EDITING DCK FILE FUNCTIONS

def editing_dck_general(
        Sim: Any,
        dck_editing: List[str],
        ) -> List[str]:

    START = Sim.START
    STOP = Sim.STOP
    STEP = Sim.STEP
    heater_nom_cap = Sim.Heater_NomCap
    heater_F_eta = Sim.Heater_F_eta
    tank_temp_high = Sim.Tank_TempHigh
    tank_temp_low = Sim.Tank_TempLow
    temp_consump = Sim.Temp_Consump
    tank_temp_high_control = Sim.Tank_TempHighControl
    # Editing .dck file: general parameters of simulation
    tag = "Control cards"
    for idx, line in enumerate(dck_editing):
        if tag in line:
            dck_editing[idx + 4] = f"START={START}"
            dck_editing[idx + 5] = f"STOP={STOP}"
            dck_editing[idx + 6] = f"STEP={STEP}/60"
            break

    ############################################
    # Editing .dck file: DEWH resistive single parameters
    gral_params = {
        "Heater_NomCap": heater_nom_cap * W2kJh,
        "Heater_F_eta": heater_F_eta,
        "Tank_TempHigh": tank_temp_high,
        "Tank_TempLow": tank_temp_low,
        "Temp_Consump": temp_consump,
        "Tank_TempHighControl": tank_temp_high_control,  # This is used for a 10°C deadband in HT controller.
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


#######################################################
def editing_dck_weather(
        Sim: Any,
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


##############################################
# Editing .dck file: Tank parameters
def editing_dck_tank(
        Sim: Any,
        dck_editing: List[str],
        ) -> List[str]:

    tank_vol = Sim.Tank_Vol
    tank_height = Sim.Tank_Height
    tank_U = Sim.Tank_U
    tank_temps_ini = Sim.Tank_Temps_Ini
    tank_temp_high = Sim.Tank_TempHigh 
    tank_temp_low = Sim.Tank_TempLow
    tank_nodes = Sim.Tank_nodes

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

    #############
    # Finding the Initial Parameters to change
    tank_params = {
        "1 Tank volume": tank_vol,
        "2 Tank height": tank_height,
        "4 Top loss coefficient": tank_U * W2kJh,
        "5 Edge loss coefficient": tank_U * W2kJh,
        "6 Bottom loss coefficient": tank_U * W2kJh,
    }

    for idx, line in enumerate(comp_lines):
        for key, value in tank_params.items():
            if key in line:
                new_line = "{:}   !  {:}".format(value, key)
                comp_lines[idx] = new_line

    ##############
    # Defining the Initial temperature (DERIVATIVE PARAMETERS)

    # Linear stratification
    if tank_temps_ini == 1:
        tank_node_temps = np.linspace(tank_temp_high, tank_temp_low, tank_nodes)
    # Linear inverted stratification
    if tank_temps_ini == 2:
        tank_node_temps = np.linspace(tank_temp_low, tank_temp_high, tank_nodes)
    # Full Charged
    if tank_temps_ini == 3:
        tank_node_temps = tank_temp_high * np.ones(tank_nodes)
    # Full Discharged
    if tank_temps_ini == 4:
        tank_node_temps = tank_temp_low * np.ones(tank_nodes)
    # Random
    if tank_temps_ini == 5:
        tank_node_temps = np.random.uniform(
            low=tank_temp_low, high=tank_temp_high, size=(tank_nodes,)
        )

    tag4 = "DERIVATIVES"  # There should be only one on lines_tank
    for idx, line in enumerate(comp_lines):
        if tag4 in line:
            for i in range(tank_nodes):
                idx_aux = idx + i + 1
                comp_lines[idx_aux] = (
                    str(tank_node_temps[i]) + "   !" + comp_lines[idx_aux].split("!")[1]
                )
            break

    # Joining the edited lines with the old set
    dck_editing = dck_editing[:idx_start] + comp_lines + dck_editing[idx_end:]

    return dck_editing

###############################################

def editing_dck_file(Sim):

    layout_DEWH = Sim.layout_DEWH
    layout_PV = Sim.layout_PV
    layout_TC = Sim.layout_TC
    layout_WF = Sim.layout_WF
    layout_v = Sim.layout_v
    fileDir = Sim.fileDir
    layoutDir = Sim.layoutDir
    tempDir = Sim.tempDir

    if layout_v == 0:
        file_trnsys = f"TRNSYS_{layout_DEWH}_{layout_PV}_{layout_TC}_{layout_WF}.dck"
    else:
        file_trnsys = (
            f"TRNSYS_{layout_DEWH}_{layout_PV}_{layout_TC}_{layout_WF}_v{layout_v}.dck"
        )

    # The original .dck file. It is in layoutDir
    dck_path = os.path.join(fileDir, layoutDir, file_trnsys)
    # The edited .dck file. It is in tempDir
    Sim.trnsys_dck_path = os.path.join(tempDir, file_trnsys)

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
    with open(Sim.trnsys_dck_path, "w") as dckfile_out:
        for line in dck_editing:
            dckfile_out.write(f"{line}\n")

    return


################################################

########################################################
#### SETTING AND RUNNING SIMULATION
########################################################

def creating_trnsys_files(
        Sim,
        Profiles: pd.DataFrame,
        engine: str = 'TRNSYS',
        ) -> None:

    from tm_solarshift.Profiles_utils import PROFILES_TYPES
    layoutDir = Sim.layoutDir
    layout_WF = Sim.layout_WF
    weather_source = Sim.weather_source
    
    # Creating temporary folder
    # This is done to assign a new temporal folder where the simulation will be run.
    temp_i = 1
    while True:
        tempDir = os.path.join(TRNSYS_TEMPDIR, f"temp{temp_i}")
        if not os.path.isdir(tempDir):
            os.makedirs(tempDir)
            break
        else:
            temp_i += 1

    Sim.tempDir = tempDir
    
    # Creating files from Profiles
    #Saving Files
    lbls = ["PV_Gen","m_HWD","CS","Elec_Cons"]
    for lbl in lbls:
        Profiles[lbl].to_csv(
            os.path.join(tempDir,  FILES_TRNSYS_INPUT[lbl]), index=False
        )
        
    Profiles[PROFILES_TYPES['weather']].to_csv(
        os.path.join(tempDir, FILES_TRNSYS_INPUT["weather"]), index=False
    )
    
    #Adding information for specific components
    if Sim.layout_DEWH == "HPF":
        file_HP_data = FILES_TRNSYS_INPUT["HP"]
        shutil.copyfile(
            os.path.join(layoutDir, file_HP_data),
            os.path.join(tempDir, file_HP_data)
        )

    #Adding the information for weather if it is TRNSYS native (W15)
    if layout_WF == "W15" and weather_source == None:
        weather_source = "Meteonorm"

    if Sim.layout_WF == "W15":
        if weather_source == "Meteonorm":
            Sim.weather_path = os.path.join(
                METEONORM_FOLDER,
                METEONORM_FILES[Sim.location]
            )

    return

###########################################
def postprocessing_detailed(
        Sim: Any,
        Profiles: pd.DataFrame,
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
        sep="\s+", 
        index_col=0
    )
    out_tank = pd.read_table(
        os.path.join(
            tempDir, 
            FILES_TRNSYS_OUTPUT["RESULTS_TANK"]
        ), 
        sep="\s+", 
        index_col=0
    )
    out_sig = pd.read_table(
        os.path.join(
            tempDir, 
            FILES_TRNSYS_OUTPUT["RESULTS_SIGNAL"]
        ), 
        sep="\s+", 
        index_col=0
    )
    out_all = out_gen.join(out_tank, how="left")
    out_all = out_all.join(
        out_sig[["C_Load", "C_Tmax", "C_Tmin", "C_All"]],
        how="left"
    )


    # Calculating additional variables
    temp_consump = Sim.Temp_Consump
    tank_nodes = Sim.Tank_nodes
    tank_temp_high = Sim.Tank_TempHigh
    tank_temp_low = Sim.Tank_TempLow
    temp_mains = Sim.Temp_Mains
    tank_cp = Sim.Tank_cp

    node_cols = [col for col in out_all if col.startswith("Node")]
    out_all2 = out_all[node_cols]
    out_all["T_avg"] = out_all2.mean(axis=1)
    out_all["SOC"] = ((out_all2 - temp_consump) * (out_all2 > temp_consump)).sum(
        axis=1
    ) / (tank_nodes * (tank_temp_high - temp_consump))
    out_all["SOC2"] = ((out_all2 - temp_mains) * (out_all2 > temp_consump)).sum(
        axis=1
    ) / (tank_nodes * (tank_temp_high - temp_mains))
    out_all["SOC3"] = (
        (out_all2.sum(axis=1) - tank_nodes * tank_temp_low)
        / (tank_temp_high - tank_temp_low)
        / tank_nodes
    )

    out_all["E_HWD"] = out_all["HW_Flow"] * (
        tank_cp * (temp_consump - temp_mains) / 3600.
    )  # [W]

    out_all["E_Level"] = (out_all2 - temp_consump).sum(axis=1) / (
        tank_nodes * (tank_temp_high - temp_consump)
    )

    out_all["TIME"] = out_all.index
    out_all = out_all.iloc[1:]
    out_all.index = Profiles.index
    # First row are initial conditions, but are dummy values for results. They can be removed

    return out_all

##########################################


def postprocessing_annual_simulation(
        Sim: Any,
        Profiles: pd.DataFrame,
        out_all: pd.DataFrame
        ) -> Dict:

    START = Sim.START
    STOP = Sim.STOP
    STEP = Sim.STEP
    tank_thermal_cap = Sim.Tank_ThCap
    tank_cp = Sim.Tank_cp
    
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
    cycles_day = heater_heat_acum / tank_thermal_cap / DAYS

    # Average values
    m_HWD_avg = out_all["HW_Flow"].sum() * STEP_h / DAYS
    out_avg = out_all.mean()
    SOC_avg = out_avg["SOC"]
    temp_amb_avg = out_avg["T_amb"]
    temp_mains_avg = out_avg["T_mains"]

    # The environmental variables are updated in Simulation Settings
    # (this should've been done before the simulation, but read the Meteonorm weather data is not that simple due to formats. If constant values are used, this shouldn't be a problem)
    Sim.Temp_Amb = temp_amb_avg
    Sim.Temp_Mains = temp_mains_avg

    # Risks_params
    SOC_min = out_all["SOC"].min()
    (SOC_025, SOC_050) = out_all["SOC"].quantile([0.25, 0.50], interpolation="nearest")
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
        Sim, Profiles, out_data
    ) -> pd.DataFrame:
    
    STEP_h = Sim.STEP_h
    tank_cp = Sim.Tank_cp

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
        Sim: Any,
        Profiles: pd.DataFrame,
        verbose: bool = False,
        engine: str = 'TRNSYS',
        keep_tempDir: bool = False,
        ):

    if engine == 'TRNSYS':
        
        stime = time.time()
        if verbose:
            print("RUNNING TRNSYS SIMULATION")
            print("Creating the temporary folder with files")
        creating_trnsys_files(Sim, Profiles)
        
        if verbose:
            print("Creating the trnsys source code (dck file)")
        editing_dck_file(Sim)
        
        if verbose:
            print("Calling TRNSYS executable")
        subprocess.run([TRNSYS_EXECUTABLE, Sim.trnsys_dck_path, "/h"])
        
        if verbose:
            print("TRNSYS simulation finished. Starting postprocessing.")
        out_all = postprocessing_detailed(Sim, Profiles)
        
        if keep_tempDir:
            if verbose:
                print(f"End of simulation. The temporary folder {Sim.tempDir} was not deleted.")
        else:
            shutil.rmtree(Sim.tempDir)
            if verbose:
                print("End of simulation. The temporary folder is deleted.")
            
        elapsed_time = time.time()-stime
        if verbose:
            print(f"Execution time: {elapsed_time:.4f} seconds.")
    
        return out_all
    
    else:
        print("Engine not valid. Thermal simulation was not executed.")
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

##################################################

# Creating_parametric_simulation
# This code is to create a parametric run. It creates a pandas dataframe with all the runs required. The order of running is "first=outer".
# It requires a dictionary with keys as Simulation attributes (to be changed)
# and a list of strings with the desired outputs from out_overall.

def parametric_settings(params_in, params_out):

    cols_in = params_in.keys()
    runs = pd.DataFrame(list(itertools.product(*params_in.values())), columns=cols_in)
    for col in params_out:
        runs[col] = np.nan
    return runs



# def emission_estimation(Sim, out_all):

#     STEP_H = Sim.STEP / 60.0
#     YEAR = Sim.YEAR
#     location = Sim.location
    
#     CacheDir = os.path.join(os.path.dirname(Sim.fileDir), "TEMPCACHE_nemed_demo")
#     file_emissions = os.path.join(CacheDir, f"emissions_year_{YEAR}.csv")
#     emissions = pd.read_csv(file_emissions, index_col=0)
#     emissions.index = pd.to_datetime(emissions.index)

#     LOCATIONS_NEM_REGION = {
#         "Sydney": "NSW1",
#         "Melbourne": "VIC1",
#         "Brisbane": "QLD1",
#         "Adelaide": "SA1",
#         "Canberra": "NSW1",
#         "Townsville": "QLD1",
#     }

#     emi_aux = emissions[
#         emissions.Region == LOCATIONS_NEM_REGION[location]
#         ][
#         ["Intensity_Index"]
#     ]

#     data2 = (
#         pd.concat([out_all, emi_aux]).sort_index().interpolate().loc[out_all.index]
#     )
#     data2 = data2[~data2.index.duplicated(keep="first")].copy()
#     emissions_total = (data2["HeaterPower"] / 1e6 / 3.6 * STEP_H) \
#         * data2["Intensity_Index"]

#     return emissions_total.sum()