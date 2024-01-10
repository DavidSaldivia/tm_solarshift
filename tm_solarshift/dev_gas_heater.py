# -*- coding: utf-8 -*-
"""
Created on Wed Dec  6 07:56:23 2023

@author: z5158936
"""

import subprocess           # to run the TRNSYS simulation
import shutil               # to duplicate the output txt file
import time                 # to measure the computation time
import os
import datetime
import sys 
import glob
import copy
import pickle

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

import tm_solarshift.trnsys_utils as TRP
import tm_solarshift.Profiles_utils as profiles

MJ_to_kWh = 1000./3600.

# https://www.rheem.com.au/rheem/products/Residential/Gas-Continuous-Flow/Continuous-Flow-%2812---27L%29/Rheem-12L-Gas-Continuous-Flow-Water-Heater-%3A-50%C2%B0C-preset/p/876812PF#collapse-1-2-1
# Data from model Rheim 20
heater_gas_power = 157.                       # [MJ/hr]
heater_water_flow = 20.                       # [L/min]
deltaT_rise = 25.                             #[dgrC]

gas_heat_value = 47                           #[MJ/kg_gas]
HW_daily_cons = 200.                          #[L/day]
HW_annual_energy = 2000.                      #[kWh/year]
#Assuming pure methane
kgCO2_to_kgCH4 = 44. / 16.

heater_gas_flow = heater_gas_power / gas_heat_value #[kg/hr]

cp_water = 4.18 #[kJ/kgK]
rho_water = 1. #[kg/L]

heater_HW_energy = ((heater_water_flow*60.) 
                    * rho_water * cp_water 
                    * deltaT_rise
                    / 1000.)  #[MJ/hr]

heater_eta = heater_HW_energy / heater_gas_power
heater_sp_energy = heater_gas_power / (heater_water_flow*60.) * MJ_to_kWh #[kWh/L]

gas_CO2_emissions = ( kgCO2_to_kgCH4 
                     / (gas_heat_value * MJ_to_kWh)
                     / heater_eta
                     )  #[kg_CO2/kWh_thermal]

heater_daily_energy = heater_sp_energy * HW_daily_cons #[kWh]
heater_annual_emissions = HW_annual_energy * gas_CO2_emissions/1000. #[tonCO2/year]

print(heater_eta)
print(heater_daily_energy)
print(gas_CO2_emissions)
print(heater_annual_emissions)
