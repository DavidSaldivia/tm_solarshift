import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from tm_solarshift.devices import (
    ResistiveSingle, 
    Variable,
    conversion_factor
    )

def tank_0D_two_temps(
        heater: ResistiveSingle = ResistiveSingle(),
        temp_amb: Variable = Variable(25., "degC"),
        temp_mains: Variable = Variable(20., "degC"),
        m_HWD: Variable = Variable(200., "kg/hr"),
        STEP:  Variable = Variable(1., "min"),
        t_sim_max: Variable = Variable(1., "hr"),
        verbose: bool = True,
) -> pd.DataFrame:
    #Inputs
    temp_amb = temp_amb.get_value("degC")
    temp_mains = temp_mains.get_value("degC")
    m_HWD = m_HWD.get_value("kg/hr")
    STEP = STEP.get_value("min")
    t_sim_max = t_sim_max.get_value("hr")

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
    STEP_h = STEP * conversion_factor("min", "hr")
    STEP_s = STEP * conversion_factor("min", "s")

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
    data = []

    while t_sim <= t_sim_max:
        
        #Now the proper thermal model (iniside the loop)
        temp_avg = (vol_C*temp_C + vol_H*temp_H) / vol
        r_vol = vol_H / (vol_H + vol_C)

        text = "\t".join(
            f"{x:.2f}" for x in (
                t_sim,vol_H, vol_C, r_vol,temp_H, temp_C, temp_avg, N_it
                )
            )
        if verbose:
            print(text)

        conv = False
        N_it_max = 100
        N_it = 0
        tol_conv = 1e-6
        while not(conv):
            
            temp_C_new_prev = temp_C
            temp_H_new_prev = temp_H

            #Volume of HW required
            vol_HWD = (m_HWD * STEP_h / rho)                    #[m3]
            #Volume of water that enters the system
            vol_in = vol_HWD * (temp_cons - temp_mains) / (temp_H - temp_mains)   #[m3]

            #Changes in cold and hot water fractions
            vol_C_new = vol_C + vol_in
            vol_H_new = vol_H - vol_in
            r_vol = (vol_H_new + vol_C_new)/vol

            #Energy loss to environment
            Q_loss_mantle = (U_loss * A_mantle * (temp_avg - temp_amb))   # [W]
            Q_loss_top = (U_loss * A_top * (temp_H - temp_amb))           # [W] 
            Q_loss_bot = (U_loss * A_bot * (temp_C - temp_amb))           # [W]
            Q_loss_tot = Q_loss_mantle + Q_loss_top + Q_loss_bot          # [W]
            
            # Q_loss_H = Q_loss_tot * r_vol      #[W]
            # Q_loss_C = Q_loss_tot * (1-r_vol)  #[W]

            Q_loss_H = (Q_loss_mantle * r_vol + Q_loss_top)      #[W]
            Q_loss_C = (Q_loss_mantle * (1-r_vol) + Q_loss_bot)  #[W]

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

            if (((abs(temp_C_new-temp_C_new_prev)<tol_conv and
                abs(temp_H_new-temp_H_new_prev)<tol_conv)) or
                N_it >=N_it_max):
                break
            else:
                N_it += 1
                temp_C_new_prev = temp_C_new
                temp_H_new_prev = temp_H_new

        #Updating values for next timestep and saving data
        (vol_H, vol_C, temp_H, temp_C) = (vol_H_new, vol_C_new, temp_H_new, temp_C_new)

        SOC = vol_H/vol
        data_row = [vol_H, vol_C, temp_H, temp_C, SOC]
        data.append(data_row)

        if t_sim >= t_sim_max:
            break
        else:
            t_sim += STEP_h
    
    COLS_DATA = ["vol_H", "vol_C", "temp_H", "temp_C", "SOC"]
    return pd.DataFrame(data,columns=COLS_DATA)

#------------------------
def tank_0D_SOC_based(
        heater: ResistiveSingle = ResistiveSingle(),
        temp_amb: Variable = Variable(25., "degC"),
        temp_mains: Variable = Variable(20., "degC"),
        m_HWD: Variable = Variable(200., "kg/hr"),
        CS: bool | float = False,
        STEP:  Variable = Variable(1., "min"),
        t_sim_max: Variable = Variable(1., "hr"),
        verbose: bool = True,
) -> pd.DataFrame:
    
    #Inputs
    temp_amb = temp_amb.get_value("degC")
    temp_mains = temp_mains.get_value("degC")
    m_HWD = m_HWD.get_value("kg/hr")
    STEP = STEP.get_value("min")
    t_sim_max = t_sim_max.get_value("hr")

    # Values from tank and heater specifications
    nom_power = heater.nom_power.get_value("W")
    U_loss = heater.U.get_value("W/m2-K")
    diam = heater.diam.get_value("m")
    height = heater.height.get_value("m")
    vol = heater.vol.get_value("m3")
    temp_cons = heater.temp_consump.get_value("degC")
    temp_max = heater.temp_max.get_value("degC")

    cp = heater.fluid.cp.get_value("J/kg-K")
    rho = heater.fluid.rho.get_value("kg/m3")
    k = heater.fluid.k.get_value("W/m-K")
    
    STEP_h = STEP * conversion_factor("min", "hr")
    STEP_s = STEP * conversion_factor("min", "s")
    hr_TO_s = conversion_factor("hr", "s")
    J_to_kWh = conversion_factor("J", "kWh")

    # Derived values for tank
    A_mantle = np.pi * diam * height
    A_top =  np.pi * diam **2 / 4.
    A_bot = np.pi * diam **2 / 4.

    #Initial values
    temp_0 = temp_max
    energy_0 = rho * vol * cp * (temp_0 - temp_cons) * J_to_kWh  #[kWh]
    vol_H_0 = vol
    vol_C_0 = 0.0
    temp_H_0 = temp_0
    temp_C_0 = temp_mains
    (vol_H, vol_C, temp_H, temp_C, energy) = (
        vol_H_0, vol_C_0, temp_H_0, temp_C_0, energy_0
    )

    t_sim = 0
    data = []
    while t_sim <= t_sim_max:
        
        #Parameters at beginning of step
        temp_avg = (vol_C*temp_C + vol_H*temp_H) / vol
        r_vol = vol_H / vol
        SOC = energy / energy_0
        theta_m = (temp_cons - temp_mains) / (temp_H - temp_mains)
        theta_t = (temp_H - temp_cons) / (temp_max - temp_cons)

        power_th_in = nom_power * CS
        
        #volume of HW required
        vol_HWD = (m_HWD * STEP_h / rho)                    #[m3]
        vol_in = vol_HWD * (temp_cons - temp_mains) / (temp_H - temp_mains)   #[m3]

        #energy losses
        Q_loss_mantle = (U_loss * A_mantle * (temp_H - temp_amb))   # [W]
        Q_loss_top = (U_loss * A_top * (temp_H - temp_amb))           # [W]
        Q_loss = Q_loss_top + Q_loss_mantle * SOC

        Q_HWD = (m_HWD/hr_TO_s) * cp * (temp_cons - temp_mains)                 #[W]

        energy_delta = (power_th_in - Q_HWD - Q_loss) * STEP_s        #[J]
        energy_new = energy + energy_delta * J_to_kWh                 #[kWh]

        #changes in cold and hot water fractions
        vol_H_new = vol_H - vol_in
        vol_C_new = vol_C + vol_in
        
        temp_H_new = energy_delta/(rho*vol_H*cp) + temp_H
        
        temp_C_new = temp_C
        # temp_H_new = temp_H

        data_row = [t_sim, temp_avg, temp_H, temp_C, 
                    SOC, r_vol, energy, theta_m, theta_t,
                    vol_HWD, vol_in, 
                    energy_new, vol_H_new, vol_C_new]
        data.append(data_row)

        if verbose:
            print("\t".join( f"{x:.2f}" for x in data_row ))

        #Updating values for next timestep and saving data
        (energy, vol_H, vol_C, temp_H, temp_C) = (
            energy_new, vol_H_new, vol_C_new, temp_H_new, temp_C_new)

        if t_sim >= t_sim_max:
            break
        else:
            t_sim += STEP_h
    
    COLS_DATA = ["t_sim", "temp_avg", "temp_H", "temp_C", 
                    "SOC", "r_vol", "energy", "theta_m", "theta_t",
                    "vol_HWD", "vol_in", 
                    "energy_new", "vol_H_new", "vol_C_new"]
    
    return pd.DataFrame(data,columns=COLS_DATA)


#--------------------------
def tank_0D_SOC_profiles(
        heater: ResistiveSingle = ResistiveSingle(),
        Profiles: pd.DataFrame = pd.DataFrame,
        verbose: bool = True,
) -> pd.DataFrame:
    
    #Inputs
    temp_mains = Profiles["Temp_Mains"].iloc[0]

    STEP = Profiles.index.freq.n

    # Values from tank and heater specifications
    nom_power = heater.nom_power.get_value("W")
    U_loss = heater.U.get_value("W/m2-K")
    diam = heater.diam.get_value("m")
    height = heater.height.get_value("m")
    vol = heater.vol.get_value("m3")
    temp_cons = heater.temp_consump.get_value("degC")
    cp = heater.fluid.cp.get_value("J/kg-K")
    rho = heater.fluid.rho.get_value("kg/m3")
    k = heater.fluid.k.get_value("W/m-K")
    temp_max = heater.temp_max.get_value("degC")

    #Constants
    STEP_h = STEP * conversion_factor("min", "hr")
    STEP_s = STEP * conversion_factor("min", "s")
    hr_TO_s = conversion_factor("hr", "s")
    J_TO_kWh = conversion_factor("J", "kWh")

    # Derived values for tank
    A_mantle = np.pi * diam * height
    A_top =  np.pi * diam **2 / 4.
    A_bot = np.pi * diam **2 / 4.

    #Initial values
    temp_0 = temp_max
    energy_0 = rho * vol * cp * (temp_0 - temp_cons) * J_TO_kWh  #[kWh]
    vol_H_0 = vol
    vol_C_0 = 0.0
    temp_H_0 = temp_0
    temp_C_0 = temp_mains
    (vol_H, vol_C, temp_H, temp_C, energy) = (
        vol_H_0, vol_C_0, temp_H_0, temp_C_0, energy_0
    )

    t_sim = 0
    data = []
    
    COLS_DATA = ["t_sim", "temp_avg", "temp_H", "temp_C", 
                "SOC", "r_vol", "energy", "theta_m", "theta_t",
                "vol_HWD", "vol_in", 
                "energy_new", "vol_H_new", "vol_C_new"]
    out_all = pd.DataFrame(None, index=Profiles.index, columns=COLS_DATA)

    COLUMNS_PROFILES = ["Temp_Amb","Temp_Mains","m_HWD","CS"]
    for x in COLUMNS_PROFILES:
        out_all[x] = Profiles[x]

    out_all["TIME"] = None
    n_idx = 0
    t_sim = 0
    for (idx,row) in out_all.iterrows():

        temp_amb = row["Temp_Amb"]          #[degC]
        temp_mains = row["Temp_Mains"]      #[degC]
        m_HWD = row["m_HWD"]                #[kg/hr]
        CS = row["CS"]                      #[bool]
        
        #Parameters at beginning of step
        temp_avg = (vol_C*temp_C + vol_H*temp_H) / vol
        r_vol = vol_H / vol
        SOC = energy / energy_0
        theta_m = (temp_cons - temp_mains) / (temp_H - temp_mains)
        theta_t = (temp_H - temp_cons) / (temp_max - temp_cons)

        power_th_in = nom_power * CS
        
        #volume of HW required
        vol_HWD = (m_HWD * STEP_h / rho)                    #[m3]
        vol_in = vol_HWD * (temp_cons - temp_mains) / (temp_H - temp_mains)   #[m3]

        #energy losses
        Q_loss_mantle = (U_loss * A_mantle * (temp_H - temp_amb))     # [W]
        Q_loss_top = (U_loss * A_top * (temp_H - temp_amb))           # [W]
        Q_loss = Q_loss_top + Q_loss_mantle * SOC

        Q_HWD = (m_HWD/hr_TO_s) * cp * (temp_cons - temp_mains)       #[W]

        energy_delta = (power_th_in - Q_HWD - Q_loss) * STEP_s        #[J]
        energy_new = energy + energy_delta * J_TO_kWh                 #[kWh]

        #changes in cold and hot water fractions
        vol_H_new = vol_H - vol_in
        vol_C_new = vol_C + vol_in
        
        temp_H_new = energy_delta/(rho*vol_H_new*cp) + temp_H
        
        temp_C_new = temp_C
        # temp_H_new = temp_H
        
        data_row = [t_sim, temp_avg, temp_H, temp_C, 
                    SOC, r_vol, energy, theta_m, theta_t,
                    vol_HWD, vol_in, 
                    energy_new, vol_H_new, vol_C_new]
        
        for i in range(len(COLS_DATA)):
            lbl = COLS_DATA[i]
            value = data_row[i]
            out_all.loc[idx,lbl] = value
        out_all.loc[idx,"TIME"] = t_sim
        data.append(data_row)

        if verbose and (n_idx%100==0):
            print("\t".join( f"{x:.2f}" for x in data_row ))

        #Updating values for next timestep and saving data
        (energy, vol_H, vol_C, temp_H, temp_C) = (
            energy_new, vol_H_new, vol_C_new, temp_H_new, temp_C_new)

        n_idx += 1
        t_sim += STEP_h
    
    output1 = pd.DataFrame(data, columns=COLS_DATA)
    output2 = out_all
    return output2

#------------------------------
def detailed_plot_0D_based(
    general_setup,
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
    
    from tm_solarshift.general import (GeneralSetup, MAIN_DIR)
    import tm_solarshift.profiles as profiles
    import tm_solarshift.trnsys as trnsys
    from TL_parametric import load_profiles_all

    general_setup = GeneralSetup(
        DEWH = ResistiveSingle(),
        STOP = 100.,
        profile_control=-1,
        random_control=False,
        )

    if False:
        output_state = tank_0D_SOC_based(
            general_setup.DEWH,
            verbose=True,)
        plot_main_vars(output_state)
        print(output_state)
    
    Profiles = load_profiles_all(general_setup)
    fldr_results_detailed = os.path.join(
        MAIN_DIR, "results", 'comparison_trnsys_0D',
    )

    if True:
        out_all_trnsys = trnsys.run_trnsys_simulation(
            general_setup, Profiles, verbose=True
            )
        trnsys.detailed_plots(
            general_setup,
            out_all_trnsys,
            showfig=True,
            case="TRNSYS",
            fldr_results_detailed = fldr_results_detailed,
            save_plots_detailed = True
            )
        print()

    if True:
        out_all_0D = tank_0D_SOC_profiles(general_setup.DEWH, Profiles, verbose=True)
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