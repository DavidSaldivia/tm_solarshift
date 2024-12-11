from __future__ import annotations
import subprocess
import shutil
import time
import os
import pandas as pd
import numpy as np
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Optional, TypeAlias

from tm_solarshift.constants import (DIRECTORY, SIMULATIONS_IO)
from tm_solarshift.utils.units import (Variable, conversion_factor as CF)

if TYPE_CHECKING:
    from tm_solarshift.models.dewh import HWTank

# constants
DIR_DATA = DIRECTORY.DIR_DATA
TS_TYPES = SIMULATIONS_IO.TS_TYPES
TRNSYS_EXECUTABLE = DIRECTORY.FILE_TRNSYS_EXEC
TEMPDIR_SIMULATION = DIRECTORY.DIR_TRNSYS_TEMP
DEFAULT_HEATER_DATA = {
    "heat_pump": os.path.join(DIR_DATA["specs"],"HP_data_reclaim.dat"),
    "solar_thermal": os.path.join(DIR_DATA["specs"],"STC_data_ones.dat"),
}

#------------------------------
# layout_DEWH: Type of DEWH.
#    'RS': Resistive (single) and Gas Storage;
#    'HPF': Heat Pump and solar thermal;

#------------------------------
class TrnsysDEWH():
    """Class that set the simulation, creates the trnsys files, run the simulation and return the results dataframe.
    Depending on the technology it uses one of the available .dck templates.

    Parameters:
        DEWH (HWTank): Heater technology. It must be a heater class with tank.
        ts (pd.DataFrame): Timeseries dataframe.

    """

    FILES_OUTPUT = {
    "detailed" : "TRNSYS_out_detailed.dat",
    "tank": "TRNSYS_out_tank_temps.dat",
    "signal": "TRNSYS_out_control.dat",
    }

    def __init__(
            self,
            DEWH: HWTank,
            ts: pd.DataFrame,
        ):
    
        self.DEWH = DEWH
        self.ts = ts
        freq = pd.to_datetime(ts.index).freq
        if freq is None:
            raise IndexError("timeseries ts has not proper index")

        self.START = Variable(0, "hr")
        self.STEP = Variable(freq.n, "min")
        self.STOP = Variable( int(len(ts) * self.STEP.get_value("hr")) ,"hr" )

        # layout
        self.layout_v = 1
        if DEWH.label in ["resistive", "gas_storage"]:
            self.layout_DEWH = "RS"
        elif DEWH.label in ["heat_pump",]:
            self.layout_DEWH = "HPF"
        elif DEWH.label in ["solar_thermal",]:
            self.layout_DEWH = "STC"
        else:
            raise ValueError("DEWH object is not a valid one for TRNSYS simulation")

        if self.layout_v == 0:
            self.dck_name = f"TRNSYS_{self.layout_DEWH}_.dck"
        else:
            self.dck_name = f"TRNSYS_{self.layout_DEWH}_v{self.layout_v}.dck"

        # directories and files
        self.tempDir = ""
        self.file_names = {
            "dck": self.dck_name,
            "hwd": "ts_hwd.csv",
            "control": "ts_control.csv",
            "weather": "ts_weather.csv",
            "heater": "heater_tech_data.dat",
        }
    
    @property
    def dck_path(self) -> str:
        return os.path.join(self.tempDir, self.dck_name)

    @property
    def dck_file(self) -> list[str]:
        dck_name = self.dck_name
        dck_base_path = os.path.join(DIR_DATA["layouts"], dck_name)
        with open(dck_base_path, "r") as file_in:
            dck_original = file_in.read().splitlines()

        dck_file = dck_original.copy()
        dck_file = editing_dck_general(self, dck_file)
        dck_file = editing_dck_weather(self, dck_file)
        dck_file = editing_dck_tank(self, dck_file)
        return dck_file


    def create_simulation_files(self) -> None:
        """This function creates the simulation files with the timeseries required by TRNSYS.
        """
        ts = self.ts
        DEWH = self.DEWH
        tempDir = self.tempDir
        dck_path = os.path.join(tempDir, self.file_names["dck"])
        dck_file = self.dck_file

        weather_path = os.path.join(tempDir, self.file_names["weather"])
        hwd_path = os.path.join(tempDir, self.file_names["hwd"])
        control_path = os.path.join(tempDir, self.file_names["control"])

        # dck file
        with open(dck_path, "w") as dckfile_out:
            for line in dck_file:
                dckfile_out.write(f"{line}\n")
        
        # timeseries
        ts[TS_TYPES['weather']].to_csv( weather_path, index=False )
        ts["m_HWD"].to_csv(hwd_path, index=False )
        ts["CS"].to_csv(control_path, index=False )

        #technical info for heater that needed it
        if DEWH.label in ["heat_pump",]:
            shutil.copyfile(
                DEFAULT_HEATER_DATA[DEWH.label],
                os.path.join(tempDir, self.file_names["heater"]),
            )
        
        if DEWH.label == "solar_thermal":
            FILE_SCT_INPUT = "ts_stc.csv"
            TS_STC_COLS = ["plane_irrad", "FR_ta", "FR_UL", "heat_capacity"]
            ts_stc_path = os.path.join(tempDir, FILE_SCT_INPUT)
            ts[TS_STC_COLS].to_csv(ts_stc_path, index=False)

        return None
    

    #------------------------------
    def postprocessing(self) -> pd.DataFrame:
        """It reads the raw results from the simulations and creates a dataframe

        Returns:
            pd.DataFrame: Dataframe with the thermal simulation results (df_tm)
        """

        tempDir = self.tempDir
        idx = self.ts.index
        FILES_OUTPUT = self.FILES_OUTPUT

        # The processed data is stored into one single df
        out_gen = pd.read_table(
            os.path.join( tempDir, FILES_OUTPUT["detailed"] ), 
            sep=r"\s+", index_col=0,
        )
        out_tank = pd.read_table(
            os.path.join( tempDir, FILES_OUTPUT["tank"] ), 
            sep=r"\s+", index_col=0,
        )
        out_sig = pd.read_table(
            os.path.join( tempDir, FILES_OUTPUT["signal"] ), 
            sep=r"\s+", index_col=0,
        )
        df_tm = out_gen.join(out_tank, how="left")
        df_tm = df_tm.join(
            out_sig[["C_load", "C_temp_max", "C_temp_min", "C_all"]],
            how="left",
        )

        if self.DEWH.label == "solar_thermal":
            out_stc = pd.read_table(
                os.path.join( tempDir, "TRNSYS_out_stc.dat"),
                sep=r"\s+", index_col=0,
            )
            out_stc = out_stc.iloc[1:]
            out_stc.index = idx

        # Calculating additional variables
        DEWH = self.DEWH
        temp_consump = DEWH.temp_consump.get_value("degC")
        temp_max = DEWH.temp_max.get_value("degC")
        temp_min = DEWH.temp_min.get_value("degC")
        tank_cp = DEWH.fluid.cp.get_value("J/kg-K")
        tank_nodes = DEWH.nodes
        temp_mains = df_tm["temp_mains"].mean()

        node_cols = [col for col in df_tm.columns if col.startswith("Node")]
        df_tm2 = df_tm[node_cols]
        df_tm["tank_temp_avg"] = df_tm2.mean(axis=1)
        df_tm["SOC"] = ((
            (df_tm2 - temp_consump)
            * (df_tm2 > temp_consump)).sum(axis=1) 
            / (tank_nodes * (temp_max - temp_consump))
            )
        df_tm["SOC2"] = (
            ((df_tm2 - temp_mains) 
            * (df_tm2 > temp_consump)).sum(axis=1 ) 
            / (tank_nodes * (temp_max - temp_mains))
            )
        df_tm["SOC3"] = (
            (df_tm2.sum(axis=1) - tank_nodes * temp_min)
            / (temp_max - temp_min)
            / tank_nodes
            )
        df_tm["E_HWD"] = df_tm["HW_flow"] * (
            tank_cp * (temp_consump - temp_mains) / 3600.
        )  # [W]
        df_tm["E_level"] = (
            (df_tm2 - temp_consump).sum(axis=1) 
            / (tank_nodes * (temp_max - temp_consump))
            )
        
        # First row is removed. Initial conditions for inputs, dummy values for results
        df_tm = df_tm.iloc[1:]
        df_tm["TIME"] = df_tm.index
        df_tm.index = idx
        
        return df_tm
    
    #------------------------------
    def run_simulation(
            self,
            verbose: bool = False,
            ) -> pd.DataFrame:
        """It creates a temporary directory where the .dck file is created together with the timeseries files. Then it runs the simulation using subprocess.run. After the simulation, the temporary directory is deleted

        Args:
            verbose (bool, optional): Whether print details about the simulation. Defaults to False.

        Returns:
            pd.DataFrame: Simulation results (df_tm)
        """

        stime = time.time()
        if verbose:
            print("Running TRNSYS Simulation")
        
        with TemporaryDirectory(dir=TEMPDIR_SIMULATION) as tmpdir:

            self.tempDir = tmpdir
            if verbose:
                print("Creating the trnsys source code files")
            self.create_simulation_files()

            if verbose:
                print("Calling TRNSYS executable")
            subprocess.run([TRNSYS_EXECUTABLE, self.dck_path, "/h"])
            
            if verbose:
                print("TRNSYS simulation postprocessing.")
            df_tm = self.postprocessing()

            pass
                
        elapsed_time = time.time()-stime
        if verbose:
            print(f"Execution time: {elapsed_time:.4f} seconds.")
        
        return df_tm
    
#------------
def editing_dck_general(
        trnsys_dewh: TrnsysDEWH,
        dck_editing: list[str],
        ) -> list[str]:

    #General settings
    START = trnsys_dewh.START.get_value("hr")
    STOP = trnsys_dewh.STOP.get_value("hr")
    STEP = trnsys_dewh.STEP.get_value("min")

    #DEWH settings
    DEWH = trnsys_dewh.DEWH
    match DEWH.label:
        case "resistive":
            nom_power = DEWH.nom_power.get_value("W")
        case "heat_pump":
            nom_power = DEWH.nom_power_th.get_value("W")
        case "gas_storage":
            nom_power = DEWH.nom_power.get_value("W")
        case "solar_thermal":
            nom_power = DEWH.nom_power.get_value("W")
        case _:
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
        "heater_nom_power": nom_power * CF("W", "kJ/h"),
        "tank_temp_max": temp_max,
        "tank_temp_low": temp_min,
        "temp_consump": temp_consump,
        "tank_temp_high_ctrl": temp_high_control,
        "heater_F_eta": eta,
    }

    from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary
    if isinstance(DEWH, SolarThermalElecAuxiliary):
        gral_params["area"] = DEWH.area.get_value("m2")

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
        trnsys_dewh: TrnsysDEWH,
        dck_editing: list[str],
        ) -> list[str]:

    tag1 = "input_weather"  # Component name
    weather_path = os.path.join(trnsys_dewh.tempDir, trnsys_dewh.file_names["weather"])

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

    # replacing the default line with the weather file
    tag3 = "ASSIGN"
    for idx, line in enumerate(comp_lines):
        if tag3 in line:
            aux = line.split('"')
            new_line = aux[0] + ' "' + f"{weather_path}" + ' "' + aux[-1]
            comp_lines[idx] = new_line
            break

    # Joining the edited lines with the rest of the text
    return dck_editing[:idx_start] + comp_lines + dck_editing[idx_end:]

#------------
# Editing dck tank file
def editing_dck_tank(
        trnsys_dewh: TrnsysDEWH,
        dck_editing: list[str],
        ) -> list[str]:


    #Defining tank_params
    DEWH = trnsys_dewh.DEWH

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
    if DEWH.label in ["resistive", "gas_storage"]:
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

    elif DEWH.label in ["heat_pump",]:
        params_specific = {
            "10 Height fraction of inlet 1": 1.0, # HP inlet, not implemented yet
            "11 Height fraction of outlet 1": 0.0, #HP outlet, not implemented yet
            "12 Height fraction of inlet 2" : 0.0, #water inlet, not implemented yet
            "13 Height fraction of outlet 2" : 1.0, #water outlet, not implemented yet
            "16 Height fraction of thermostat-2" : 0.33, #thermostat HP, not implemented yet
        }
    elif DEWH.label in ["solar_thermal",]:
        params_specific = {
            "10 Height fraction of inlet 1": 1.0,
            "11 Height fraction of outlet 1": 0.0,
            "12 Height fraction of inlet 2" : 0.0,
            "13 Height fraction of outlet 2" : 1.0,
            "16 Height fraction of thermostat-2" : 0.75,
        }
    else:
        raise ValueError("DEWH type is not among accepted classes.")
    
    #Merging both dictionaries (params_specific has priority over params_common)
    tank_params = params_common | params_specific

    # Replacing into the dck file
    # The start line of the component is identified with tag1 and tag2
    tag1 = "hw_tank_1"  # Component name 
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

    tag4 = "DERIVATIVES"  # There should be only one on comp_lines
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

    return dck_editing[:idx_start] + comp_lines + dck_editing[idx_end:]

#------------------------------
def main():
    from tm_solarshift.general import Simulation
    sim = Simulation()
    trnsys_dewh = TrnsysDEWH(
        DEWH = sim.DEWH,
        ts = sim.create_ts()
    )
    df_tm = trnsys_dewh.run_simulation(verbose=True)
    print(df_tm)

if __name__=="__main__":
    main()
