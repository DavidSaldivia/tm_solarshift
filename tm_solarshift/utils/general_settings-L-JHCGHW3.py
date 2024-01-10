# -*- coding: utf-8 -*-
"""
Created on Sat Dec  2 00:42:44 2023

@author: z5158936
"""

import shutil  # to duplicate the output txt file
import time  # to measure the computation time
import os
import datetime
import sys
from typing import Optional, List, Dict, Any, Tuple

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


import tm_solarshift.utils.trnsys as trnsys
import tm_solarshift.utils.profiles as profiles

PROFILES_TYPES = profiles.PROFILES_TYPES
PROFILES_COLUMNS = profiles.PROFILES_COLUMNS

## The main object for the simulation
class GeneralSetup(object):
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

###########################################

class Profiles(object):
    def __init__(self, Sim):
        START, STOP, STEP, YEAR = Sim.START, Sim.STOP, Sim.STEP, Sim.YEAR
        STEP_h = STEP / 60.0
        PERIODS = int(np.ceil((STOP - START) / STEP_h))
        start_time = pd.to_datetime(f"{YEAR}-01-01 00:00:00") + pd.DateOffset(hours=START)
        idx = pd.date_range(start=start_time, periods=PERIODS, freq=f"{STEP}min")
        self.df = pd.DataFrame(index=idx, columns=PROFILES_COLUMNS)

########################################
Sim = GeneralSetup()
profiles = Profiles(Sim)

Sim2 = trnsys.General_Setup()