# -*- coding: utf-8 -*-
"""
Created on Tue Dec 19 05:47:06 2023

@author: z5158936
"""
import numpy as np
import pandas as pd

from tm_solarshift.devices import (ResistiveSingle, CONV)


def main():
    #Inputs
    heater = ResistiveSingle()
    temp_amb = 25.       #[degC]
    temp_mains = 20.     #[degC]
    m_HWD = 200.         #[kg/hr]
    STEP = 1            #[min]
    t_sim_max = 1.       #[hr]

    # Values from tank specifications
    U_loss = heater.U.get_value("W/m2-K")
    diam = heater.diam.get_value("m")
    height = heater.height.get_value("m")
    vol = heater.vol.get_value("m3")
    temp_cons = heater.temp_consump.get_value("degC")
    cp = heater.fluid.cp.get_value("J/kg-K")
    rho = heater.fluid.rho.get_value("kg/m3")
    k = heater.fluid.k.get_value("W/m-K")


    #Constants
    STEP_h = STEP * CONV["min_to_hr"]
    STEP_s = STEP * CONV["min_to_s"]

    # Derived values for tank
    A_mantle = np.pi * diam * height
    A_top =  np.pi * diam **2 / 4.
    A_bot = np.pi * diam **2 / 4.


    #Initial values
    temp_ini = heater.temp_max.get_value("degC")
    vol_H_0 = 0.9*vol
    vol_C_0 = 0.1*vol
    temp_H_0 = temp_ini
    temp_C_0 = temp_mains

    (vol_H, vol_C, temp_H, temp_C) = (
        vol_H_0, vol_C_0, temp_H_0, temp_C_0
    )

    N_it = 0
    t_sim = 0
    while t_sim <= t_sim_max:
        
        #Now the proper thermal model (iniside the loop)
        temp_avg = (vol_C*temp_C + vol_H*temp_H) / vol
        r_vol = vol_H / (vol_H + vol_C)

        text = "\t".join(
            f"{x:.2f}" for x in (
                t_sim,vol_H, vol_C, r_vol,temp_H, temp_C, temp_avg,N_it
                )
            )
        print(text)

        conv = False
        N_it_max = 100
        N_it = 0
        while not(conv):
            
            temp_C_new_prev = temp_C
            temp_H_new_prev = temp_H
            #Energy loss to environment
            Q_loss_mantle = (U_loss * A_mantle * (temp_avg - temp_amb))   # [W]
            Q_loss_top = (U_loss * A_top * (temp_H - temp_amb))           # [W] 
            Q_loss_bot = (U_loss * A_bot * (temp_C - temp_amb))           # [W]
            Q_loss_tot = Q_loss_mantle + Q_loss_top + Q_loss_bot          # [W]
            
            Q_loss_H = Q_loss_tot * r_vol      #[W]
            Q_loss_C = Q_loss_tot * (1-r_vol)  #[W]

            # Q_loss_H = (Q_loss_mantle * r_vol + Q_loss_top)      #[W]
            # Q_loss_C = (Q_loss_mantle * (1-r_vol) + Q_loss_bot)  #[W]

            #Volume of HW required
            vol_HWD = (m_HWD * STEP_h / rho)                    #[m3]
            #Volume of water that enters the system
            vol_in = vol_HWD * (temp_cons - temp_mains) / (temp_H - temp_mains)   #[m3]

            #Changes in cold and hot water fractions
            vol_C_new = vol_C + vol_in
            vol_H_new = vol_H - vol_in

            #Energy loss due to HWD
            Q_HWD = vol_in * cp * (temp_H - temp_mains) * STEP_s     #[J]

            #Updating the temperatures
            r_s = STEP_s / (rho*cp)                     #[K-m3/W]

            vol_C_avg = (vol_C+vol_C_new)/2
            temp_C_avg = temp_C
            temp_C_new = (
                temp_C * vol_C                     #Initial internal energy
                + vol_in*(temp_mains - temp_C)     #Change by HWD
                - Q_loss_C * r_s                   #Change by losses
                ) / vol_C_new

            vol_H_avg = (vol_H+vol_H_new)/2
            temp_H_avg = temp_H        
            temp_H_new = (
                temp_H * vol_H                         #Initial internal energy
                + vol_in*(temp_C - temp_H)             #Change by HWD
                - Q_loss_H * r_s                       #Change by losses
                ) / vol_H_new

            if (((abs(temp_C_new-temp_C_new_prev)<1e-5 and
                abs(temp_H_new-temp_H_new_prev)<1e-5)) or
                N_it >=N_it_max):
                break
            else:
                N_it += 1
                temp_C_new_prev = temp_C_new
                temp_H_new_prev = temp_H_new

        #Updating values for next timestep
        (vol_H, vol_C, temp_H, temp_C) = (
            vol_H_new, vol_C_new, temp_H_new, temp_C_new
        )
        if t_sim >= t_sim_max:
            break
        else:
            t_sim += STEP_h
    return

if __name__=="__main__":
    main()