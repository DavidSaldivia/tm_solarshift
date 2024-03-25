import subprocess
import shutil
import time
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, List, Dict, Any, Tuple
from tempfile import TemporaryDirectory

from tm_solarshift.constants import (DIRECTORY, DEFINITIONS)
from tm_solarshift.units import conversion_factor as CF
from tm_solarshift.general import GeneralSetup
from tm_solarshift.devices import (
    ResistiveSingle, 
    HeatPump,
    GasHeaterStorage,
    SolarThermalElecAuxiliary,
    SolarSystem,
)

DIR_DATA = DIRECTORY.DIR_DATA
TS_TYPES = DEFINITIONS.TS_TYPES
TRNSYS_EXECUTABLE = r"C:/TRNSYS18/Exe/TRNExe64.exe"
TEMPDIR_SIMULATION = "C:/SolarShift_TempDir"
FILES_TRNSYS_INPUT = {
    "PV_Gen": "0-Input_PVGen.csv",
    "Import_Grid": "0-Input_Elec.csv",
    "m_HWD": "0-Input_HWD.csv",
    "CS": "0-Input_Control_Signal.csv",
    "weather": "0-Input_Weather.csv",
    "HP": "0-Reclaim_HP_Data.dat",
    "TH": "0-SolarThermal_Data_ones.dat",
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

#------------------------------
# DEFINING THE PROBLEM.
# It requires to define the type of layout, general and environmental parameters
# the profile parameters, and

#------------------------------
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

#------------------------------
#### DEFINING TRNSYS CLASSES
class TrnsysSetup():
    def __init__(self, GS: GeneralSetup, **kwargs):
        # Directories
        self.tempDir = None

        self.START= GS.simulation.START
        self.STOP = GS.simulation.STOP
        self.STEP = GS.simulation.STEP

        self.location = GS.simulation.location
        self.DEWH = GS.DEWH
        self.solar_system = GS.solar_system

        # Trnsys layout configurations
        if self.DEWH.__class__ in [ResistiveSingle, GasHeaterStorage]:
            self.layout_DEWH = "RS"
        elif self.DEWH.__class__ in [HeatPump, SolarThermalElecAuxiliary]:
            self.layout_DEWH = "HPF"
        else:
            raise ValueError("DEWH object is not a valid one for TRNSYS simulation")

        if GS.solar_system.__class__ == SolarSystem:
            self.layout_PV = "PVF"
        else:
            raise ValueError("Solar system object is not a valid one for TRNSYS simulation")

        self.layout_v = 0
        self.layout_TC = "MX"
        self.layout_WF = "W9a"
        # self.layout_WF = "W15"
        self.weather_source = None

        for key, value in kwargs.items():
            setattr(self, key, value)


#------------
def editing_dck_general(
        trnsys_setup: TrnsysSetup,
        dck_editing: List[str],
        ) -> List[str]:

    #General settings
    START = trnsys_setup.START.get_value("hr")
    STOP = trnsys_setup.STOP.get_value("hr")
    STEP = trnsys_setup.STEP.get_value("min")

    #DEWH settings
    DEWH = trnsys_setup.DEWH
    if DEWH.__class__ == ResistiveSingle:
        nom_power = DEWH.nom_power.get_value("W")
    elif DEWH.__class__ == HeatPump:
        nom_power = DEWH.nom_power_th.get_value("W")
    elif DEWH.__class__ == GasHeaterStorage:
        nom_power = DEWH.nom_power.get_value("W")
    elif DEWH.__class__ == SolarThermalElecAuxiliary:
        nom_power = DEWH.nom_power.get_value("W")
    else:
        raise ValueError("DEWH type is not among accepted classes.")
    
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
        "Heater_NomCap": nom_power * CF("W", "kJ/h"),
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
                    new_line = f"{key} = {value:.5f} !This line was replaced by python script !PYTHON_INPUT"
                    dck_editing[idx] = new_line

    return dck_editing


#------------
def editing_dck_weather(
        trnsys_setup: TrnsysSetup,
        dck_editing: List[str],
        ) -> List[str]:

    layout_WF = trnsys_setup.layout_WF

    # The start and end lines of the component are identified and extracted
    if layout_WF == "W15":
        tag1 = "Type15-6_Weather"  # Component name. It should be only one per file
        weather_path = trnsys_setup.weather_path

    if layout_WF == "W9a":
        tag1 = "Type9a_Weather"  # Component name. It should be only one per file
        weather_path = os.path.join(trnsys_setup.tempDir, FILES_TRNSYS_INPUT["weather"])

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

    # Joining the edited lines with the rest of the text
    dck_editing = dck_editing[:idx_start] + comp_lines + dck_editing[idx_end:]

    return dck_editing

#------------
# Editing dck tank file
def editing_dck_tank(
        trnsys_setup: TrnsysSetup,
        dck_editing: List[str],
        ) -> List[str]:


    #Defining tank_params
    DEWH = trnsys_setup.DEWH

    # Common parameters
    params_common = {
        "1 Tank volume" : DEWH.vol.get_value("m3"),
        "2 Tank height" : DEWH.height.get_value("m"),
        "4 Top loss coefficient" : DEWH.U.get_value("W/m2-K") * CF("W", "kJ/h"),
        "5 Edge loss coefficient" : DEWH.U.get_value("W/m2-K") * CF("W", "kJ/h"),
        "6 Bottom loss coefficient" : DEWH.U.get_value("W/m2-K") * CF("W", "kJ/h"),
        "7 Fluid specific heat" : DEWH.fluid.cp.get_value("kJ/kg-K"),
        "8 Fluid density" : DEWH.fluid.rho.get_value("kg/m3"),
        "9 Fluid thermal conductivity" : DEWH.fluid.k.get_value("W/m-K") * CF("W", "kJ/h"),
    }

    #Defining specific parameters for each type of heater
    if DEWH.__class__ in [ResistiveSingle, GasHeaterStorage]:
        height = DEWH.height.get_value("m")
        f_inlet = DEWH.height_inlet.get_value("m") / height
        f_outlet = DEWH.height_outlet.get_value("m") / height
        f_thermostat = DEWH.height_thermostat.get_value("m") / height
        f_heater = DEWH.height_heater.get_value("m") / height
        
        params_specific = {
            "12 Height fraction of inlet 2" : f_inlet,
            "13 Height fraction of outlet 2" : f_outlet,
            "16 Height fraction of thermostat-2": f_thermostat,
            "18 Height fraction of auxiliary input": f_heater,
        }

    elif DEWH.__class__ in [HeatPump, SolarThermalElecAuxiliary]:
        params_specific = {
            "10 Height fraction of inlet 1": 1.0, # HP inlet, not implemented yet
            "11 Height fraction of outlet 1": 0.0, #HP outlet, not implemented yet
            "12 Height fraction of inlet 2" : 0.0, #water inlet, not implemented yet
            "13 Height fraction of outlet 2" : 1.0, #water outlet, not implemented yet
            "16 Height fraction of thermostat-2" : 0.33, #thermostat HP, not implemented yet
        }
    else:
        raise ValueError("DEWH type is not among accepted classes.")
    
    #Merging both dictionaries (params_specific has priority over params_common)
    tank_params = params_common | params_specific

    # Replacing into the dck file
    # The start line of the component is identified with tag1 and tag2
    tag1 = "HotWaterTank_1"  # Component name 
    tag2 = "158"  # Component Type
    for idx, line in enumerate(dck_editing):
        if tag1 in line and tag2 in line:
            idx_start = idx
            comp_lines = dck_editing[idx_start:]
            break

    # The end line is identified with tag3
    tag3 = "*------------"
    for idx, line in enumerate(comp_lines):
        if tag3 in line:
            idx_end = idx + idx_start + 1  # index in the original file
            break

    comp_lines = dck_editing[idx_start:idx_end]
    for idx, line in enumerate(comp_lines):
        for key, value in tank_params.items():
            if key in line:
                new_line = "{:}   !  {:}".format(value, key)
                comp_lines[idx] = new_line

    #(DERIVATIVE PARAMETERS) Defining the initial temperature
    temp_max = DEWH.temp_max.get_value("degC")
    temp_min = DEWH.temp_min.get_value("degC")
    temps_ini = DEWH.temps_ini
    nodes = DEWH.nodes
    match temps_ini:
        case 1:
            tank_node_temps = np.linspace(temp_max, temp_min, nodes)
        case 2:
            tank_node_temps = np.linspace(temp_min, temp_max, nodes)
        case 3:
            tank_node_temps = temp_max * np.ones(nodes)
        case 4:
            tank_node_temps = temp_min * np.ones(nodes)
        case 5:
            tank_node_temps = np.random.uniform(
                low=temp_min, high=temp_max, size=(nodes,)
            )
        case _:
            raise ValueError(f"Value for temp_ini ({temps_ini}) is not valid [0-5]")

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

#------------
def editing_dck_file(trnsys_setup: TrnsysSetup) -> str:

    layout_DEWH = trnsys_setup.layout_DEWH
    layout_PV = trnsys_setup.layout_PV
    layout_TC = trnsys_setup.layout_TC
    layout_WF = trnsys_setup.layout_WF
    layout_v = trnsys_setup.layout_v
    tempDir = trnsys_setup.tempDir

    if layout_v == 0:
        file_trnsys = f"TRNSYS_{layout_DEWH}_{layout_PV}_{layout_TC}_{layout_WF}.dck"
    else:
        file_trnsys = (
            f"TRNSYS_{layout_DEWH}_{layout_PV}_{layout_TC}_{layout_WF}_v{layout_v}.dck"
        )

    # The original .dck file. It is in DATA_DIR["layouts"]
    dck_path = os.path.join(DIR_DATA["layouts"], file_trnsys)

    # Loading the original TRNSYS (.dck) file
    with open(dck_path, "r") as file_in:
        dck_original = file_in.read().splitlines()

    # Making the edits
    dck_editing = dck_original.copy()
    dck_editing = editing_dck_general(trnsys_setup, dck_editing)
    dck_editing = editing_dck_weather(trnsys_setup, dck_editing)
    dck_editing = editing_dck_tank(trnsys_setup, dck_editing)

    # Saving the edits into a new .dck file that will be read by trnsys.exe
    trnsys_dck_path = os.path.join(tempDir, file_trnsys)
    with open(trnsys_dck_path, "w") as dckfile_out:
        for line in dck_editing:
            dckfile_out.write(f"{line}\n")
    
    return trnsys_dck_path

#------------
def creating_timeseries_files(
        trnsys_setup: TrnsysSetup,
        timeseries: pd.DataFrame,
        ) -> None:

    layout_WF = trnsys_setup.layout_WF
    layout_DEWH = trnsys_setup.layout_DEWH
    weather_source = trnsys_setup.weather_source
    location = trnsys_setup.location
    tempDir = trnsys_setup.tempDir
        
    #Saving files for other than weather
    lbls = ["PV_Gen", "m_HWD", "CS", "Import_Grid"]
    for lbl in lbls:
        timeseries[lbl].to_csv(
            os.path.join(tempDir, FILES_TRNSYS_INPUT[lbl]), index=False
        )
        
    #Saving file for weather
    timeseries[TS_TYPES['weather']].to_csv(
        os.path.join(tempDir, FILES_TRNSYS_INPUT["weather"]), index=False
    )
    
    #Adding information for specific components
    if layout_DEWH == "HPF":
        if trnsys_setup.DEWH.__class__ == HeatPump:
            lbl = "HP"
        elif trnsys_setup.DEWH.__class__ == SolarThermalElecAuxiliary:
            lbl = "TH"
        file_lbl_data = FILES_TRNSYS_INPUT[lbl]
        shutil.copyfile(
            os.path.join(DIR_DATA["specs"], file_lbl_data),
            os.path.join(tempDir, FILES_TRNSYS_INPUT["HP"])
        )

    if layout_WF == "W15":
        if weather_source == None:
            weather_source = "Meteonorm"

        if weather_source == "Meteonorm":
            trnsys_setup.weather_path = os.path.join(
                METEONORM_FOLDER,
                METEONORM_FILES[location]
            )

    return

#------------------------------
def postprocessing_detailed(
        trnsys_setup: TrnsysSetup,
        timeseries: pd.DataFrame,
        )-> pd.DataFrame:
    
    #Reading output files
    tempDir = trnsys_setup.tempDir

    # The processed data is stored into one single file
    out_gen = pd.read_table(
        os.path.join(
            trnsys_setup.tempDir, 
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
    DEWH = trnsys_setup.DEWH
    temp_consump = DEWH.temp_consump.get_value("degC")
    temp_max = DEWH.temp_max.get_value("degC")
    temp_min = DEWH.temp_min.get_value("degC")
    tank_cp = DEWH.fluid.cp.get_value("J/kg-K")
    tank_nodes = DEWH.nodes
    temp_mains = out_all["T_mains"].mean()

    node_cols = [col for col in out_all if col.startswith("Node")]
    out_all2 = out_all[node_cols]
    out_all["T_avg"] = out_all2.mean(axis=1)
    out_all["SOC"] = ((
        (out_all2 - temp_consump)
        * (out_all2 > temp_consump)).sum(axis=1) 
        / (tank_nodes * (temp_max - temp_consump))
        )
    out_all["SOC2"] = (
        ((out_all2 - temp_mains) 
        * (out_all2 > temp_consump)).sum(axis=1 ) 
        / (tank_nodes * (temp_max - temp_mains))
        )
    out_all["SOC3"] = (
        (out_all2.sum(axis=1) - tank_nodes * temp_min)
        / (temp_max - temp_min)
        / tank_nodes
        )
    out_all["E_HWD"] = out_all["HW_Flow"] * (
        tank_cp * (temp_consump - temp_mains) / 3600.
    )  # [W]
    out_all["E_Level"] = (
        (out_all2 - temp_consump).sum(axis=1) 
        / (tank_nodes * (temp_max - temp_consump))
        )
    
    # First row are initial conditions, but are dummy values for results. They can be removed
    out_all = out_all.iloc[1:]
    out_all["TIME"] = out_all.index
    out_all.index = timeseries.index
    
    return out_all

#------------------------------
def run_simulation(
        GS: GeneralSetup,
        timeseries: pd.DataFrame,
        verbose: bool = False,
        ) -> pd.DataFrame:

    if verbose:
        print("Running TRNSYS Simulation")
    
    with TemporaryDirectory(dir=TEMPDIR_SIMULATION) as tmpdir:
        trnsys_setup = TrnsysSetup(GS)
        trnsys_setup.tempDir = tmpdir

        stime = time.time()
        if verbose:
            print("Creating the temporary folder with files")
        creating_timeseries_files(trnsys_setup, timeseries)
        
        if verbose:
            print("Creating the trnsys source code (dck file)")
        trnsys_dck_path = editing_dck_file(trnsys_setup)
        
        if verbose:
            print("Calling TRNSYS executable")
        subprocess.run([TRNSYS_EXECUTABLE, trnsys_dck_path, "/h"])
        
        if verbose:
            print("TRNSYS simulation finished. Starting postprocessing.")
        out_all = postprocessing_detailed(trnsys_setup, timeseries)
            
        elapsed_time = time.time()-stime
        if verbose:
            print(f"Execution time: {elapsed_time:.4f} seconds.")
    
    return out_all

#------------------------------
def main():

    GS = GeneralSetup()
    ts = GS.create_ts_default()
    out_all = run_simulation(GS, ts, verbose=True)
    print(out_all)

if __name__=="__main__":
    main()
