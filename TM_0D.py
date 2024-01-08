# -*- coding: utf-8 -*-
"""
Created on Tue Dec 19 05:47:06 2023

@author: z5158936
"""
import numpy as np
import pandas as pd

# Properties of water
PROP_WATER = {
    'cp': 4180,  # [J/kg-K] specific heat (water)
    'rho': 1000, # [kg/m3] density (water)
    'k': 0.6, # [W/m-K] thermal conductivity (water)
              }

class Tank_0D():
    def __init__(self, **kwargs):
        self.model = "default"      #[str]
        self.fluid = "water"      #[str]
        self.vol = 0.315            #[m3]
        self.height = 1.3           #[m]
        self.temp_max = 65.         #[C]
        self.temp_deadband = 10.    #[deltaC]
        self.temp_cons = 45.        #[C]
        
        #Initiating the temperatures
        self.temp_H = self.temp_max         #[C]
        self.temp_C = self.temp_max         #[C]
        self.temp_avg = self.temp_max       #[C]
        
        self.diam = (4 * self.vol / np.pi / self.height) ** 0.5
        self.A_mantle = np.pi * self.diam * self.height
        self.A_top = np.pi * self.diam **2 / 4.
        self.A_bot = np.pi * self.diam **2 / 4.
        

#using T_hot and T_cold

cp = PROP_WATER['cp']
rho = PROP_WATER['rho']
k = PROP_WATER['k']

tank = Tank_0D()

temp_amb = 25.       #[degC]
temp_mains = 20.     #[degC]
m_HWD = 10.          #[kg/min]

temp_cons = 45.      #[degC]
dt = 3. #[min]


#Values from tank that are constant
U_tank = tank.U
A_mantle = tank.A_mantle
A_top = tank.A_top
A_bot = tank.A_bot


#Initial values
vol_C = 0.
vol_H = tank.vol
r_vol_C = vol_C / (vol_H + vol_C)

#Values from tank for this step (will change)
temp_H   = tank.temp_H
temp_C   = tank.temp_C
temp_avg = tank.temp_avg

#Energy loss to environment
q_loss_mantle = (U_tank * A_mantle * (temp_avg - temp_amb))   # [W]
q_loss_top = (U_tank * A_top * (temp_H - temp_amb))           # [W] 
q_loss_bot = (U_tank * A_top * (temp_H - temp_amb))           # [W]
q_loss = q_loss_mantle + q_loss_top + q_loss_bot              # [W]

Q_loss_H = (q_loss_mantle * (1 - r_vol_C) + q_loss_top) * dt     #[J]
Q_loss_C = (q_loss_mantle * r_vol_C + q_loss_bot) * dt           #[J]

#Energy loss due to HWD
vol_HWD = (m_HWD * dt / rho)                        #[m3]
Q_HWD = vol_HWD * cp * (temp_cons - temp_mains)     #[J]

#Volume of water that enter the system and that changes top and bottom
vol_in = vol_HWD * (temp_cons - temp_mains) / (temp_H - temp_mains)   #[m3]

vol_C_new = vol_C + vol_in
vol_H_new = vol_H - vol_in

temp_C_new = (
    (vol_C * temp_C + vol_in * temp_mains) / vol_C_new
    - Q_loss_C / (vol_C_new * rho * cp)
    )
temp_H_new = (
    (vol_H * temp_H + vol_in * temp_H) / vol_H_new
    - Q_loss_C / (vol_C_new * rho * cp)
    )